# 183 · Hay dos formatos de vector de interrupción en amdgpu, con los campos en sitios distintos, y el que decide cuál es la versión del bloque IH

```
CLASSIFICATION=DOCUMENTATION+CORRECTION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · rx550-upstream-7.2.8
HARDWARE_SCOPE=NONE · WORK_CLASS=READ_ONLY/EVIDENCE · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

Para el eslabón `interrupciones` de la cadena —que es el que gobierna los fences,
y con ellos dos de los cuatro `NOT_PROVEN` del estado— faltaba el contrato del
vector de interrupción. Está cerrado, y sale con una advertencia que importa:
**no hay un formato, hay dos, y los campos ocupan sitios distintos.**

```
IH v3.0    tonga_ih_decode_iv         16 bytes, 4 dwords
           vi.c:2111  ->  tonga_ih_ip_block { major=3, minor=0 }   ESTA GPU

IH v5.0+   amdgpu_ih_decode_iv_helper  32 bytes, 8 dwords
           navi10_ih (5.0), vega10_ih, ih_v6_0 (6.0), ih_v6_1, ih_v7_0
```

Confundirlos **no falla**: no hay comprobación que lo rechace. Se decodifica
basura con autoridad de campo.

## 1 · Los dos formatos, campo a campo

| | v3.0, 16 bytes | v5.0+, 32 bytes |
|---|---|---|
| `client_id` | **fijo** a `AMDGPU_IRQ_CLIENTID_LEGACY`, no se lee | leído: `dw[0] & 0xff` |
| `src_id` | `dw[0] & 0xff` | `dw[0] >> 8 & 0xff` |
| `ring_id` | `dw[2] & 0xff` | `dw[0] >> 16 & 0xff` |
| `vmid` | `dw[2] >> 8 & 0xff` — **8 bits** | `dw[0] >> 24 & 0xf` — **4 bits** |
| `pasid` | `dw[2] >> 16 & 0xffff` | `dw[3] & 0xffff` |
| `timestamp` | **no existe** | `dw[1] | (dw[2] & 0xffff) << 32` |
| `node_id` | **no existe** | `dw[3] >> 16 & 0xff` |
| `src_data` | 1 palabra, `dw[1] & 0xfffffff` — **28 bits** | 4 palabras, `dw[4..7]` |
| avance | `ih->rptr += 16` | `ih->rptr += 32` |

**`vmid` pasa de 8 bits a 4** y `src_data` de una palabra de 28 bits a cuatro
palabras completas. No es una extensión: es otro formato. Y el `client_id` fijo es
lo que hace que en GFX8 **un IV no pueda distinguir clientes** — eso ya lo decía
`findings/051` y queda corroborado con el formato contrario al lado.

## 2 · La cadena que decide, verificada entera

```
vi.c:2107            case CHIP_POLARIS12:
vi.c:2111              amdgpu_device_ip_block_add(adev, &tonga_ih_ip_block);
tonga_ih.c:503-509     tonga_ih_ip_block = { type=IH, major=3, minor=0, rev=0 }
tonga_ih.c:492-496     tonga_ih_funcs = { decode_iv = tonga_ih_decode_iv }
amdgpu_ih.h:118       .decode_iv  ->  se llama ahi
```

Y el otro lado, para que se vea que la elección no es arbitraria:

```
navi10_ih.c:712     .decode_iv = amdgpu_ih_decode_iv_helper    (major=5, minor=0)
vega10_ih.c:642     .decode_iv = amdgpu_ih_decode_iv_helper
ih_v6_0.c:801       .decode_iv = amdgpu_ih_decode_iv_helper    (major=6, minor=0)
ih_v6_1.c:780  ih_v7_0.c:857   .decode_iv = amdgpu_ih_decode_iv_helper
```

**El discriminante es la versión mayor del bloque IH, y 3.0 usa el de 16 bytes.**

Un detalle de la misma medición, y es una observación independiente de que la
versión importa: **`tonga_ih` y `cz_ih` son bloques distintos**. Polaris12 toma el
de Tonga (`vi.c:2111`); Carrizo toma `cz_ih_ip_block` (`vi.c:2127`). Y los 2 GiB
de VRAM de esta GPU los sirve el bloque GMC de 8.1 (`vi.c:2110 gmc_v8_1_ip_block`),
no el de 8.0 que usa Carrizo. Polaris12 es, en dos bloques de golpe, **un Polaris12
y no un Carrizo**: misma familia GFX8, revisión distinta.

## 3 · Mi hipótesis era falsa, y por poco la escribía

Encontré `amdgpu_ih.c:301 iv_size = 32` y monté la explicación de que el `wptr` del
IH va en dwords y no en bytes, que sería una trampa de arquitectura silently
distinta de la del anillo PM4. **Es falso**, y el propio fuente lo desmiente dos
líneas más abajo del 32:

```c
amdgpu_ih.c:294    /* wptr/rptr are in bytes! */
amdgpu_ih.c:295    ih->rptr += 32;
```

El `>> 2` de la línea 153 no es una conversión de unidad: es el paso de índice de
`uint32_t *` a bytes. `wptr = *wptr_cpu >> 2` es «bytes → índice de dword»,
`wptr <<= 2` es la vuelta, y lo que se guarda en `wptr_cpu` son **bytes**, igual
que en el anillo PM4.

Lo que quedaba del hallazgo correcto es más pequeño y más útil: **el `>> 2` es
un índice, no una unidad**, y es la clase exacta de error que este proyecto ha
cometido siete veces con tablas de opcodes. Se comprobó antes de escribir porque
`drvchain.py` ya había dado un número falso plausible en la misma sesión.

## 4 · La geometría del anillo, que tampoco estaba

`amdgpu_ih.c:71-74` da la disposición completa:

```c
ih->wptr_addr = dma_addr + ih->ring_size;          /* los punteros están
ih->wptr_cpu  = &ih->ring[ih->ring_size / 4];      /* DENTRO del propio anillo,
ih->rptr_addr = dma_addr + ih->ring_size + 4;      /* justo detrás de las    */
ih->rptr_cpu  = &ih->ring[(ih->ring_size / 4) + 1];/* entradas               */
```

Tres consecuencias para el driver, y las tres son `PROVEN_DERIVED`:

1. **El anillo del IH vive en VRAM**, es un BO, y la CPU lo mapea. No está en
   MMIO.
2. **WPTR y RPTR no son registros que se escriban**: los registros
   `ih_rb_wptr_addr_lo/hi` guardan la **dirección** de esas dos posiciones, y el
   puntero se mantiene por indirección. Escribir `ih_rb_wptr` no avanza nada.
3. **El puntero se avanza en la memoria del anillo, por la CPU**, y el hardware
   hace lo propio con el RPTR. `amdgpu_ih_ring_write` escribe el WPTR sólo si no
   desborda, y avisa con `retry_cam_enabled` si lo hace.

El punto 2 es el que más engaña por su apariencia; quien escriba un anillo de IH
tomando el patrón de un anillo PM4 tendrá un anillo que no avanza, en silencio.

## Lo que queda abierto, con su causa

```
PENDIENTE=que el HARDWARE de esta GPU produzca IV de 16 bytes y no de 32
  | HALLAZGO=183-dos-formatos-de-iv-y-la-version-del-bloque-que-decide.md
  | ESTADO=NOT_PROVEN
  | NECESITA=emitir un IV y leer el ring por el host; un RREG32 sobre el bloque
  |          IH solo, con las escrituras de PTBA+invalidate delante, que es lo
  |          que findings/115..120 ya encadenaron para el otro extremo
  | ALCANZABLE_SIN_ROOT=no
```

La clasificación importa y no es un matiz: lo que está `PROVEN` es **qué
decodificador liga amdgpu a este ASIC**, que es software. Lo que está `NOT_PROVEN`
es que el hardware escriba con ese formato —y sólo un registro **lee** eso—. Un
`RREG32` de una palabra no prueba el layout de un vector de ocho.

## Procedencia

```
vi.c:2107, :2110, :2111, :2127       cases de POLARIS12 y CARRIZO, y sus bloques
tonga_ih.c:492-496, :503-509         tonga_ih_funcs y tonga_ih_ip_block v3.0
tonga_ih.c:248-270                   decode_iv de 16 bytes: rptr += 16
amdgpu_ih.c:263-296                  decode_iv de 32 bytes: rptr += 32
amdgpu_ih.c:294                      el comentario "wptr/rptr are in bytes!"
amdgpu_ih.c:71-74                    wptr/rptr viven dentro del propio anillo
amdgpu_ih.h:36-49                    struct amdgpu_ih_regs, nueve registros
sid.h                                IH_RB_CNTL 0xF80, IH_RB_BASE 0xF81,
                                     IH_RB_RPTR 0xF82, IH_RB_WPTR_ADDR_LO 0xF85
navi10_ih.c:712, vega10_ih.c:642, ih_v6_0.c:801, ih_v6_1.c:780, ih_v7_0.c:857
findings/051                         CORROBORADO: el layout de 16 bytes
findings/031                         CORROBORADO: los dominios de wptr/rptr
findings/171                         por que esto es lo que fija la prioridad
```

## CORRECCION POSTERIOR

Ninguna sobre lo afirmado. Dos correcciones **a mí mismo** dentro de esta misma
ronda, y por eso van aquí y no en el cuerpo:

1. **`iv_size` no es el paso del IV.** Leí `amdgpu_ih.c:301 iv_size = 32` en
   `amdgpu_ih_decode_iv_ts_helper` —un *auxiliar* de lectura de timestamp— y lo
   tomé por el formato del vector. El vector de esta GPU lo decodifica
   `tonga_ih_decode_iv`, que avanza 16.
2. **El `>> 2` no es una diferencia de unidad.** Es conversión de índice de array.
   El comentario de la línea 294 lo dice literalmente, y yo estaba a una línea de
   escribir un hallazgo que lo contradijera.

Las dos se evitaron por lo mismo: comprobar el emisor antes de afirmar. La segunda
era exactamente el error de `147` con la tabla de opcodes, y otra vez lo paró el
fichero y no una hipótesis.
