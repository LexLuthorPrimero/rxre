# 020 · El presupuesto de dwords del vm-flush GFX8 excede en 5 lo que se escribe

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `CORPUS=RESEARCH/working/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

## CUDA principal

`ring_funcs_gfx` y `ring_funcs_compute` reservan **5 dwords más** de los que
`emit_vm_flush` escribe. La causa está localizada: `VI_FLUSH_GPU_TLB_NUM_WREG = 3`
(`vi.h:27`) pero `gmc_v8_0_emit_flush_gpu_tlb()` hace **2** llamadas a `emit_wreg`.

```
declarado - real = (3 - 2) * 5 dw = 5 dw = exactamente un PACKET3_WRITE_DATA
```

`ring_funcs_kiq` declara `17` a mano y **coincide exacto**: la misma función, misma
aritmética, sin la constante. Eso confirma que el excess viene de la constante y no
de una lectura mia del codigo.

## Alcance exacto

1. Contar los dwords que el path GFX8 de vm-flush escribe, por ring.
2. Comparar con `emit_frame_size` de los tres `ring_funcs`.
3. Localizar la causa exacta del residual y comprobar si es seguro.

## Criterio de terminacion (cumplido)

Residual medido en los tres rings y su causa identificada en una linea de fuente.
Agotado.

---

## 1 · Regla de conteo, y por que importa

Cada llamada `amdgpu_ring_write()` escribe **exactamente un dword**. `PACKET3(op, n)`
no anade nada: sus `n` payload son las llamadas siguientes, que ya se cuentan.

Mi primer intento uso `1 + n` y produjo `-8` en los tres rings, es decir "se escribe
mas de lo reservado". Eso es un resultado imposible en el hardware: el ring tiene
espacio de sobra por construccion (`emit_frame_size` se usa para reservar, no para
limitar). Un residual negativo grande es la senal de que la regla de conteo estaba
mal, no de que el driver se desborde. Queda registrado porque el error era plausible
y produzca un numero seemingly-solid.

## 2 · Lo que se escribe, medido

Herramienta: `/tmp/opencode/rx550/count_vmflush_dw.py`. Lee fuente, no ejecuta
nada contra la GPU.

```
gfx_v8_0_ring_emit_wreg      = 5 dw por llamada   (PACKET3_WRITE_DATA,3 + cmd + reg + 0 + val)
gmc_v8_0_emit_flush_gpu_tlb  = 2 llamadas a emit_wreg = 10 dw
  WAIT_REG_MEM               = 7 dw   (PACKET3,5 -> 1 header + 5 payload, + 1 config)
  PFP_SYNC_ME                = 2 dw   (solo ring GFX, usepfp)
```

| RING | declarado | real | residual | origen |
|---|---|---|---|---|
| `GFX` | **24** | 19 | **+5** | `ring_funcs_gfx:6881` `N*5 + 9` |
| `COMPUTE` | **22** | 17 | **+5** | `ring_funcs_compute:6929` `N*5 + 7` |
| `KIQ` | **17** | 17 | **0** | `ring_funcs_kiq:6964` literal |

`N = VI_FLUSH_GPU_TLB_NUM_WREG = 3` (`vi.h:27`).

## 3 · La causa, aislada

`gmc_v8_0_emit_flush_gpu_tlb` (`gmc_v8_0.c:668-681`) tiene exactamente dos
`amdgpu_ring_emit_wreg`:

1. `PTBA(vmid) = pd_addr >> 12`
2. `VM_INVALIDATE_REQUEST = 1 << vmid`

Ningun otro emisor del arbol hace un tercero:

```
gmc_v6_0  emit_wreg reales = 2
gmc_v7_0  emit_wreg reales = 2
gmc_v8_0  emit_wreg reales = 2
```

El `9` de `ring_funcs_gfx` y el `7` de `ring_funcs_compute` reproducen exactamente
`7 (WAIT_REG_MEM) + 2 (PFP_SYNC_ME)`. La unica discrepancia esta en el termino `N*5`.

## 4 · Por que esto es una buena noticia y no un defecto

`emit_frame_size` es una **reserva**, no un limite. Sobrar es correcto; quedarse corto
seria un desbordamiento de buffer de ring. El residual es `+5` en dos rings y `0` en
el tercero: **ningun ring esta infra-reservado**.

Lo relevante para el driver propio es el otro lado de la misma cuenta:

```
GFX      = 19 dw = 76 bytes por vm-flush
COMPUTE  = 17 dw = 68 bytes
```

Ese es el tamano real que hay que reservar, y el valor de `vi.h` no lo describe. Un
driver propio que copie `N*5 + 9` copria una reserva 26% mayor de lo necesario en el
ring GFX; uno que copie el `17` literal de KIQ acertaria por otra razon y sin saber
por que.

## 5 · La herramienta discrimina

Un test que no se ha visto fallar no prueba que detecte. Mutante: `emit_wreg` de 5 a 6
dwords.

```
$ python3 mut.py
GFX      declarado=24  real=21  residual=+3
COMPUTE  declarado=22  real=19  residual=+3
KIQ      declarado=17  real=19  residual=-2      <-- infra-reserva
rc=1
```

El mutante produce `KIQ` infra-reservado y la herramienta sale con `rc=1`. Es
capaz de distinguir el caso que importa.

## 6 · Lo que NO es

Este hallazgo **no dice nada** sobre la semántica hardware del invalidate. El
`WAIT_REG_MEM` sigue sin comparar nada (`finding 017`, `PROVEN` a nivel de encoding).
Contar dwords mide **cuanto se emite**, no **que efecto tiene**.

| Afirmacion | Estado |
|---|---|
| `emit_frame_size` de GFX/COMPUTE reserva 5 dw de mas | `PROVEN` (medido) |
| La causa es `VI_FLUSH_GPU_TLB_NUM_WREG=3` con 2 `emit_wreg` reales | `PROVEN` (aislado) |
| Ningun ring GFX8 esta infra-reservado en este path | `PROVEN` (medido) |
| El tamano real del vm-flush es 19/17/17 dw | `PROVEN` (medido) |
| Que el hardware execute 19 dw | `NOT_DETERMINED` — requiere RUNTIME |
| Si el ring tiene espacio para 19 dw en esta RX550 | `NOT_DETERMINED` — `emit_frame_size` es cota superior teorica, el anillo real se mide |
| Semantica de `FUNCTION=always` | `NOT_DETERMINED`, sin cambios respecto a `017` |

## 7 · Confounders

Ninguno relevante para una cuenta de dwords: es aritmetica sobre fuente. Los
confounders de `017` (VMID reuse, TLB preexistente, power state) aplican a cualquier
discriminante **runtime** de este path, no a este conteo.

Matiz que si queda: la fuente es `RESEARCH/working/linux-7.1.3`, y ese arbol es
byte-identico a `RESEARCH/baseline/linux-7.1.3` para `gfx_v8_0.c`, `gmc_v8_0.c` y
`sid.h` (`diff` vacio en los tres). No es el arbol que corre en esta host
(`7.1.3-200.nobara.fc44`), pero el codigo es el mismo.

## 8 · UNLOCKS

- El driver propio tiene ya el **tamano exacto** que debe reservar para un vm-flush
  en cada tipo de ring. No hay que deducirlo de una constante compartida con seis
  familias de ASIC.
- `017` y `018` dejamos abierto que mecanismo de completion usar, y `018` concluyo que
  con los registros de GFX8 **no hay ninguno**: no existe par REQ/ACK. Este documento
  **no resuelve** esa pregunta, pero acota el presupuesto: hoy sobran 5 dw en dos de
  los tres rings, de modo que un mecanismo anadido por software cabe sin recalcular la
  reserva. Eso es `MODEL_CHOICE` con un limite cuantificado, no con uno supuesto.
- - Complementario de `018` §4, con una discrepancia de conteo registrada y **no
  resuelta**: `018` cuenta `6 dw` para el `WAIT_REG_MEM`, este documento cuenta `7`.
  Medido en ambos casos contra el codigo, cada llamada `amdgpu_ring_write()` = 1 dw.
  La ambiguedad esta en si `PACKET3(op, n)` tiene `n` como payload *ademas* del
  header o `n` payload *incluyendo* el config. Este documento cuenta llamadas
  individuales, que es lo unico que no depende de esa convencion: son 7 llamadas.
  `CONFLICT` de lectura, no de hardware. No promediado.

## 9 · Criterio de falsificacion

Se refutaria si: (a) `gfx_v8_0_ring_emit_wreg` escribiera mas de 5 dwords por llamada
en alguna variante no vista —implicaria que el conteo de `emit_wreg` como funcion pura
no vale para todos los anillos; (b) `emit_frame_size` no se usara como reserva sino
como limite duro, lo que convertiria el `+5` en un defecto de buffer; (c) `PACKET3(op,n)`
tuviera una semantica de escritura multi-dword que no se modela como `n` llamadas
siguientes. Ninguna se puede comprobar leyendo este corpus. (a) y (b) quedan
`NOT_DETERMINED` y se marcan `PROVISIONAL`.

## 10 · Evidencia

```
arbol:     RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/
gfx_v8_0.c:      6035-6061 (hdp_flush, contraste: FUNCTION=3 compara),
                 6191-6221 (emit_vm_flush), 6870-6916 (ring_funcs_gfx),
                 6916-6950 (compute), 6951-6978 (kiq)
gmc_v8_0.c:      668-681 (emit_flush_gpu_tlb), 1731-1741 (gmc_funcs),
                 1768-1772 (gmc_v8_1_ip_block = Polaris12)
vi.h:            27      VI_FLUSH_GPU_TLB_NUM_WREG 3
sdma_v3_0.c:     1058-1067 (POLL_REGMEM FUNC=0; contraste: SDMA no tiene PACKET3,
                              usa otro opcode con el mismo efecto)
herramienta: /tmp/opencode/rx550/count_vmflush_dw.py  (y mut.py)
```

Ningun registro obtenido de MMIO. Ninguna operacion runtime. `GPU INTACTA`.