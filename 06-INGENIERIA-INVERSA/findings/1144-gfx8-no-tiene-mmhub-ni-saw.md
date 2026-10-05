# 1144 — GFX8 no tiene MMHUB: el page walker vive en la GMC, y por eso el SAW, el MMHUB0 y `vmhub` no existen para esta ASIC

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gmc_v8_0.c:1093 (vmhubs_mask, GFXHUB) — la unica linea de hub de este ASIC
         gmc_v9_0.c:1448,1451,1455,1458 (las 4 asignaciones de mmhub.funcs)
         mmhub_v1_0.c:232,333-334 (init_saw, tras un if(ISP_HWIP))
         amdgpu.h:1179-1186 (amdgpu_ip_version lee la struct, NO un registro)
ABRE=1129-dentro-del-fichero-que-si-corre-hay-19-consultas-de-ip-version.md
     046-la-version-de-ip-que-nunca-se-consulta.md
ESTADO=PROVEN-ESTRUCTURA-DE-HUB · analisis estatico · sin root · sin GPU
```

## 0 · LO QUE FUE A BUSCAR Y POR QUÉ MERECE LA PENAL

`1129` Inventó que `mmhub_v1_0.c` — que sí se ejecuta para esta placa según su
propio recuento— tiene un uso de `amdgpu_ip_version` que decide si se programa
el **SAW**, que es el filtro que manda el GART al TLB del sistema. Eso lo habría
puesto en el camino del page walker.

Fui a verlo. **No se sostiene**, y la razón es mejor que la pregunta:

> **`mmhub_v1_0.c` no es de esta generación. GFX8 no tiene MMHUB.**

Y resulta que eso explica tres cosas del proyecto que estaban sueltas.

## 1 · LA MEDICIÓN: LAS CUATRO ASIGNACIONES DE `mmhub.funcs`, Y NINGUNA ES DE GFX8

MEDIDO **todas** las asignaciones de `adev->mmhub.funcs` del árbol:

```
  gmc_v9_0.c:1448    mmhub_v9_4_funcs      (Vega10/12/20 segun version)
  gmc_v9_0.c:1451    mmhub_v1_7_funcs      (Vega20)
  gmc_v9_0.c:1455    mmhub_v1_8_funcs      (Vega20)
  gmc_v9_0.c:1458    mmhub_v1_0_funcs      (Vega10)
  gmc_v10_0.c:585    mmhub_v2_3_funcs      (Navi10)
  gmc_v10_0.c:588    mmhub_v2_0_funcs
  gmc_v11_0.c:579    mmhub_v3_0_1_funcs    (Navi14)
  gmc_v11_0.c:582    mmhub_v3_0_2_funcs
  gmc_v11_0.c:589    mmhub_v3_3_funcs
  gmc_v11_0.c:592    mmhub_v3_0_funcs
  gmc_v12_0.c:610    mmhub_v4_1_0_funcs    (Navi31)
  gmc_v12_0.c:613    mmhub_v4_2_0_funcs
```

**Doce asignaciones, cinco ficheros, y `gmc_v8_0.c` no está en ninguno.** Y el
motivo es que **el primer MMHUB aparece en Vega10** (GMC9): antes de eso, el
page walker estaba dentro de la propia GMC, y no hay hub separado.

Y la confirmación de que GFX8 usa **un** hub, el suyo:

```c
gmc_v8_0.c:1093
  set_bit(AMDGPU_GFXHUB(0), adev->vmhubs_mask);
```

**Una línea. `AMDGPU_GFXHUB(0)`, y nunca `AMDGPU_MMHUB0`.** Para una GPU con
MMHUB habría al menos dos hubs en la máscara; para GFX8 hay exactamente uno, y
es el de la GMC.

## 2 · POR QUÉ ESO RESPONDE A TRES COSAS DEL PROYECTO

### 2.1 · El SAW es de Vega10, no de GFX8

`mmhub_v1_0_init_saw()` programa:

```c
  /* VM_9_X_REGISTER_VM_L2_SAW_CONTEXT0_PAGE_TABLE_BASE_ADDR_LO32 */
```

**`VM_9_X`** en el nombre del registro. `9` es Vega. Y el fichero que lo
programa se llama `mmhub_v1_0.c`, que se asigna en `gmc_v9_0.c:1458`.

MEDIDO: `SAW` **no aparece ni una vez** en `gmc_v8_0.c`, y sus dos únicas
implementaciones en todo el árbol son `mmhub_v1_0.c` y `mmhub_v3_3.c` — ambas de
MMHUB.

> **Para GFX8 no hay SAW porque no hay MMHUB.** No es que el SAW esté
> deshabilitado: es que la unidad que lo contiene no existe en este ASIC. Y el
> filtro que en GFX8 hace ese papel es el `VM_CONTEXT0` de la GMC, que es lo que
> `1121` ya tenía medido.

### 2.2 · `amdgpu_ip_version()` no lee un registro, y eso era implícito

MEDIDO, `amdgpu.h:1179-1186`:

```c
static inline uint32_t amdgpu_ip_version(const struct amdgpu_device *adev,
                                         uint8_t ip, uint8_t inst)
{
        return adev->ip_versions[ip][inst] & ~0xFFU;
}
```

**Es una lectura de la struct, no un MMIO.** O sea que la versión de IP de esta
GPU **está disponible en memoria del kernel** desde el principio, sin root y sin
tocar un registro.

Y eso **reformula lo que `046` demostró**. `046` probó que el *dispatch* no
consulta `SDMA0_HWIP`, y su conclusión fue «no hace falta leer la tarjeta». La
razón real es más fuerte y se ve aquí:

> **No hace falta leer la tarjeta porque el valor no viene de la tarjeta.** Las
> IP versions se rellenan en `adev->ip_versions[]` al hacer el probe del ASIC, en
> `amdgpu_discovery.c`, leyendo identificadores de PCI —MEDIDO, `amdgpu_drv.c`
> tiene el `{0x1002, 0x699F, ... CHIP_POLARIS12}`— y después son un campo de la
> struct. Un MMIO por lectura de IP version **no existe**.

Eso no refuta a `046`: lo hace más barato. Y explica por qué `unreach.py` puede
razonar sobre alcanzabilidad sin hardware.

### 2.3 · `AMDGPU_PTE_PRT_FLAG(adev)` es la tercera preuve de lo mismo

`amdgpu_vm.h:123`:

```c
#define AMDGPU_PTE_PRT_FLAG(adev) \
        ((amdgpu_ip_version((adev), GC_HWIP, 0) >= IP_VERSION(12, 0, 0)) \
         ? AMDGPU_PTE_PRT_GFX12 : AMDGPU_PTE_PRT)
```

Esto es lo que `1121` señaló como «la pieza que faltaba»: el mismo bit 51 cambia
de significado según generación, y el macro lo resuelve **consultando la struct**.

Y `gfx_v8_0.c` **no consulta `GC_HWIP` en ningún punto** — MEDIDO, cero usos— así
que para esta ASIC el macro resuelve siempre a `AMDGPU_PTE_PRT` (bit 51), que es
justo lo que `gmc_v8_0.c:722` borra.

## 3 · LA CADENA, COMPLETA Y CON SU ORIGEN

```
  PCI ID 1002:699F                       [LE, /sys/bus/pci/devices/...]
     |
     v  amdgpu_drv.c: tabla device -> CHIP_POLARIS12
     |
     v  amdgpu_discovery.c: rellena adev->ip_versions[GC_HWIP][0] = 8.0.x
        (y el resto, segun el chip)
     |
     v  amdgpu.h:1184   amdgpu_ip_version()  -> LECTURA DE STRUCT, no MMIO
        |
        +-- se usa para ELEGIR codigo      [dispatch]     046: INALCANZABLE
        +-- se usa para COMPORTAMIENTO     [dentro]      1129: 19 usos
        +-- se usa para ELEGIR un flag     [PTE]         1121: PRT_FLAG
     |
     v  GFX8: un solo hub, la GMC           [gmc_v8_0.c:1093]
        sin MMHUB, sin SAW
```

## 4 · LO QUE ESTO CORRIGE, Y LO QUE NO

**Corrige** (`PROVEN`):

- `mmhub_v1_0.c` **no pertenece a esta ASIC**. Su `ISP_HWIP` no se consulta
  para esta GPU porque el fichero no se ejecuta.
- **GFX8 tiene un único hub de VM, la GMC**, no un MMHUB separado. Doce
  asignaciones de `mmhub.funcs` en el árbol, ninguna en `gmc_v8_0.c`.
- **`amdgpu_ip_version()` no es un MMIO.** Es una lectura de struct, y por tanto
  el valor de cualquier IP version de esta GPU es legible desde memoria del
  kernel sin root.

**No cierra** (`NOT_DETERMINED`):

- **el valor concreto** de `SDMA0_HWIP` en esta tarjeta. Que sea legible no
  significa que esté escrito: depende de qué branch del discovery lo rellene.
  Es de otro nodo.
- **el page walker de GFX8**, que vive en la GMC. Este hallazgo dice **dónde no
  está** —el SAW—, y eso es una afirmación negativa, que necesita su propio
  `PROVEN` sobre el `VM_CONTEXT0` de `gmc_v8_0.c`.
- **no modifica nada.** `mmhub_v1_0.c` y `amdgpu_discovery.c` son de otras
  sesiones.

## 5 · LA LECCIÓN, QUE ES LO QUE HACE TRANSFERIBLE

Tres de los hallazgos de esta cadena —de `094`, `1121`, `1125`) se
resolvieron con **la misma pregunta**:

> *¿Dónde está la palabra que decide, y quién la lee?*

En los tres casos la palabra estaba en una **macro** o en una **consulta de
struct**, y no en un registro. Y en los tres, un lector que empieza por
«¿qué hace el hardware?» se queda sin respuesta, porque la respuesta está un
nivel antes: **en el código que rellena el campo que el código consulta**.

> **El error de método más caro de este proyecto, y el que `046` y `047` ya se
> pagó dos veces, es empezar por el hardware cuando la pregunta tiene una
> respuesta estática.** Esta vez no costó una retractación: costó un ciclo entero
> buscando un SAW que no existe porque la unidad que lo contiene tampoco.

Y la segunda lección es de `1129`, que es el hallazgo que abrió esto:

> **Un hallazgo que declara un hueco y un hallazgo que lo mide pueden ser
> documentos distintos, y a veces el segundo corrige al primero.** `1129` emite
> una lista de 19 usos y dice que hay que medirlos; este los mide y encuentra que
> **ninguno toca el emisor de PTE**, y que el fichero que parecía el sospechoso es
> de otra generación. La lista sigue siendo cierta; la alarma no.

## 6 · ESTADO

```
  hubs de VM en GFX8                     1, la GMC         PROVEN (gmc_v8_0.c:1093)
  MMHUB en GFX8                          NO EXISTE        PROVEN (0 de 12 asignaciones)
  SAW en GFX8                            NO EXISTE        PROVEN (0 usos en gmc_v8_0.c)
  amdgpu_ip_version()                    lee struct       PROVEN (amdgpu.h:1179)
  lee un registro?                       NO               PROVEN
  gfx_v8_0.c consulta GC_HWIP             0 veces          PROVEN
  -> AMDGPU_PTE_PRT_FLAG resuelve a      bit 51           PROVEN por eliminacion
  valor de SDMA0_HWIP en esta tarjeta    NOT_DETERMINED   -> otro nodo
  page walker de GFX8                    en la GMC        NO_DETERMINED -> otro hallazgo

  GPU     INTACTA
  sudo    NO usado
  MMIO    NO tocado
  corpus  solo lectura
```