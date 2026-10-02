# 192 · UVD 6.3 y VCE 3.4 no tienen código propio: los implementa `uvd_v6_0.c` y `vce_v3_0.c`

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC_BINARY+STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` + `/tmp/amdgpu_loaded.ko`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=los bloques UVD/VCE que 190 destapo y 191 inventario`

## Cuestión principal

`198` destapó que esta placa registra `uvd_v6_3` y `vce_v3_4`, y `191` revelo que sus
tablas de función tienen 17 y 16 campos. El nombre del bloque sugiere un fichero
`uvd_v6_3.c` y `vce_v3_4.c`.

**Esos ficheros no están en el corpus.** Lo lógico era pensar que faltaban.

## Criterio de terminación

Determinar si esos bloques tienen implementación propia o aliasan a una versión
anterior, y si el código que realmente se ejecuta es legible. **Cumplido: los dos
aliasan, y el código real sí está en el corpus.**

## No faltan: nunca existieron

`ip_surface --bloque uvd_v6_3_ip_block` devuelve los **17** punteros, y **los 17
son `uvd_v6_0_*`**:

```
sw_init               uvd_v6_0_sw_init
sw_fini               uvd_v6_0_sw_fini
hw_init               uvd_v6_0_hw_init
hw_fini               uvd_v6_0_hw_fini
prepare_suspend       uvd_v6_0_prepare_suspend
suspend               uvd_v6_0_suspend
resume                uvd_v6_0_resume
is_idle               uvd_v6_0_is_idle
wait_for_idle         uvd_v6_0_wait_for_idle
check_soft_reset      uvd_v6_0_check_soft_reset
pre_soft_reset        uvd_v6_0_pre_soft_reset
soft_reset            uvd_v6_0_soft_reset
post_soft_reset       uvd_v6_0_post_soft_reset
set_clockgating_state uvd_v6_0_set_clockgating_state
set_powergating_state uvd_v6_0_set_powergating_state
get_clockgating_state uvd_v6_0_get_clockgating_state
```

Y `vce_v3_4_ip_block`: los **16** punteros son **todos `vce_v3_0_*`**.

Confirmado en el fuente:

```c
/* uvd_v6_0.c:1686 */
const struct amdgpu_ip_block_version uvd_v6_3_ip_block =
{
		.type = AMD_IP_BLOCK_TYPE_UVD,
		.major = 6,
		.minor = 3,
		.rev = 0,
		.funcs = &uvd_v6_0_ip_funcs,
};

/* vce_v3_0.c:1018 */
const struct amdgpu_ip_block_version vce_v3_4_ip_block = {
		.type = AMD_IP_BLOCK_TYPE_VCE,
		.major = 3,
		.minor = 4,
		.rev = 0,
		.funcs = &vce_v3_0_ip_funcs,
};
```

**`uvd_v6_3_ip_block` está declarado dentro de `uvd_v6_0.c`.** No hay
`uvd_v6_3.c`. No hay `vce_v3_4.c`. **Nunca los hubo.**

## Por qué esto importa: el "bloque ausente" no está ausente

| lo que se busca | resultado |
|---|---|
| `uvd_v6_3.c` | **no existe** — el bloque vive en `uvd_v6_0.c` |
| `vce_v3_4.c` | **no existe** — el bloque vive en `vce_v3_0.c` |
| `uvd_v6_0.c` | **presente en el corpus** |
| `vce_v3_0.c` | **presente en el corpus** |

**La implementación de la decodificación y la codificación de vídeo de esta placa
es completamente legible.** Los "ficheros que faltan" eran el Equivalente de buscar
`gfx_v8_1.c` en una placa donde el bloque se llama `gfx_v8_0`.

Esto es la misma lección de `231` y `232`, aplicada a un caso nuevo: **un grep sobre
un nombre de fichero no prueba que una capacidad esté ausente.** La capacidad se
busca por el mecanismo, y aquí el mecanismo dice "alias".

## Y el corpus sí está incompleto en otro sitio

Donde sí hay un hueco real es **display**: `dc/` está **vacío** en el corpus, y
`dm_v1_0.c` no existe como fichero. `dm_ip_funcs` sí resuelve sus 15 punteros
contra el `.ko` (`dm_sw_init`, `amdgpu_dm_early_fini`, ...), así que el código está
**en el binario y no en el snapshot**.

| bloque | tabla | implementación | en el corpus |
|---|---|---|---|
| UVD | `uvd_v6_3_ip_funcs` | `uvd_v6_0.c` | **sí** |
| VCE | `vce_v3_4_ip_funcs` | `vce_v3_0.c` | **sí** |
| DM | `dm_ip_funcs` | `dc/dm/` | **no** |

**Asimetría real**: media es legible en el corpus, display no.

## Por qué la versión no coincide con el código

El campo `major/minor/rev` de la tabla describe **la versión del IP en el
hardware**. El campo `funcs` describe **el código del driver**. No tienen por qué
coincidir, y en GCN3 no coinciden:

- Polaris12 reporta UVD **6.3**, y lo ejecuta el driver escrito para UVD **6.0**.
- Polaris12 reporta VCE **3.4**, y lo ejecuta el driver escrito para VCE **3.0**.

El hardware evolucionó el número de revisión; el driver no necesitó código nuevo.

**Consecuencia práctica para el driver propio**: el número de versión del log
(`<uvd_v6_3_0>`, `<vce_v3_4_0>`) **no identifica el código que corre**. Cualquier
herramienta que resuelva "qué fuente corresponde a este bloque" por el número de
versión **se equivocará**, y se equivocará de forma systematicamente invisible:
devolverá un nombre de fichero plausible.

## Clasificación

| afirmación | estado |
|---|---|
| Los 17 punteros de `uvd_v6_3_ip_funcs` son `uvd_v6_0_*` | `PROVEN` — binario |
| Los 16 punteros de `vce_v3_4_ip_funcs` son `vce_v3_0_*` | `PROVEN` — binario |
| `uvd_v6_3_ip_block` se declara en `uvd_v6_0.c` | `PROVEN` — `uvd_v6_0.c:1686` |
| `vce_v3_4_ip_block` se declara en `vce_v3_0.c` | `PROVEN` — `vce_v3_0.c:1018` |
| No existen `uvd_v6_3.c` ni `vce_v3_4.c` | `PROVEN` — búsqueda en el corpus |
| `uvd_v6_0.c` y `vce_v3_0.c` sí están | `PROVEN` |
| `dc/` vacío: el código de DM no está | `PROVEN` |
| La versión es hardware y `funcs` es software | `DERIVATION` — del par de definiciones |
| Que resolver por versión dé un nombre plausible y equivocado | `DERIVATION` |
| Que UVD 6.3 no necesite functionally más que 6.0 | `HYPOTHESIS` — no verificado |

## Confounders

- **Que los 17 punteros apunten a `uvd_v6_0_*` no demuestra que el hardware 6.3 sea
  idéntico a 6.0.** Demuestra que el driver decidió reutilizarlo. Puede haber
  diferencias de hardware que el driver ignorar o que nunca se ejerciten. Lo que
  es `PROVEN` es lo que hace el driver, no lo que puede hacer el silicio.
- **No he comparado `uvd_v6_0.c` con el código real de Fiji/Tonga**, así que no
  sé si `uvd_v6_0.c` tiene ramas `if (version >= 6.3)`. **Si las tiene, entonces
  el mismo código sirve a 6.0 y a 6.3 y la reutilización es más interesante todavía.**
  No lo he comprobado.
- **`prepare_suspend` solo existe en UVD** (de los 9). VCE y DM no lo tienen. No
  sé si es que no lo necesitan o que no está implementado; el binario solo me dice
  que no está implementado.
- **El hash del `.ko` no está en el hallazgo.** Si el módulo se recompila, hay que
  volver a correr `ip_surface`.
- **`dm_ip_funcs` resuelve 15 punteros, pero no sé qué hacen** porque `dc/` no está
  en el corpus y no desensamblo.

## Desfalsificación

- **(a)** Los 17 son `uvd_v6_0_*` → refutable con `ip_surface --bloque uvd_v6_3_ip_block`.
- **(b)** `uvd_v6_3_ip_block` vive en `uvd_v6_0.c` → refutable con la línea 1686.
- **(c)** `vce_v3_4_ip_block` vive en `vce_v3_0.c` → refutable con la línea 1018.
- **(d)** No existen los ficheros → refutable con una búsqueda en el corpus.
- **(e)** `dc/` vacío → refutable con `ls dc/`.
- **(f)** Que no haya ramas por versión dentro de `uvd_v6_0.c` → **no comprobado**, y
  lo dejo declarado como pendiente, no como conclusión.

## UNLOCKS

- **La decodificación (UVD) y la codificación (VCE) de esta placa son
  completamente legibles en el corpus**, en `uvd_v6_0.c` y `vce_v3_0.c`. §A tiene
  su implementación a la vista.
- **Un segundo bloque ausente de verdad**: display (`dc/` vacío, `dm_v1_0.c`
  inexistente). El código está en el `.ko` pero no en el snapshot. **Asimetría
  entre media (legible) y display (no).**
- **Advertencia metodológica reutilizable**: el número de versión del log identifica
  el hardware, **no** el fichero de código. Resolver por versión devuelve un
  nombre plausible y equivocado, que es la forma de error más difícil de detectar.
- **Confirma por cuarta vez la lección de `231`/`232`**: la capacidad se busca por
  el mecanismo. `uvd_v6_3` no tiene fichero porque su código se llama `uvd_v6_0`.

## Evidencia

```
08-ARQUITECTURA/tools/ip_surface.py --bloque uvd_v6_3_ip_block   17 punteros
08-ARQUITECTURA/tools/ip_surface.py --bloque vce_v3_4_ip_block   16 punteros
08-ARQUITECTURA/tools/ip_surface.py --bloque dm_ip_block          15 punteros

uvd_v6_0.c:1668-1694    uvd_v6_0_ip_block y uvd_v6_3_ip_block, misma funcs
vce_v3_0.c:1018-1024    vce_v3_4_ip_block con .funcs = &vce_v3_0_ip_funcs
vi.c:2121-2122          las dos llamadas de registro para POLARIS10/11/12/VEGAM
ls dc/                  vacio en el snapshot
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.