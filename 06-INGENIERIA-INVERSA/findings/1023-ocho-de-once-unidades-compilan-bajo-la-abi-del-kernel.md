# 1023 · Ocho de once unidades de traducción ya compilan bajo la ABI del kernel; el módulo pasó de 3 objetos a 8

`CLASSIFICATION=MEASUREMENT` · `TRACK=BOTH` · `CORPUS=RESEARCH/kernelbuild/linux-7.1.3`
`WORK_CLASS=REPAIR/CONTROLLED` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=5`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## La medida de partida

`tools/tu_compila.sh` clasifica cada `.c` del componente en dos contextos, con
las opciones **reales** de kbuild extraídas de `.rx550_target.o.cmd`:

```
$ ./tools/tu_compila.sh
TU                  KERNEL  USERSPACE  CLASE
pci_resource.c      SI      NO          SOLO_KERNEL
rx550_gart_write.c  NO      SI          SOLO_HOST
rx550_ib_bridge.c   NO      NO          ROTA
rx550_ib_composer.c NO      SI          SOLO_HOST
rx550_mmio_access.c SI      SI          DUAL
rx550_pdb0.c        SI      SI          DUAL
rx550_submission.c  NO      SI          SOLO_HOST
rx550_target.c      SI      NO          SOLO_KERNEL
rx550_vmid0_gart.c  NO      SI          SOLO_HOST
rx550_vmid1_pgt_backing.c NO  SI         SOLO_HOST
rx550_vmid1_pgt.c   NO      SI          SOLO_HOST
# TOTAL  TU=11  K_SI=4  K_NO=7  U_SI=8  U_NO=3
```

Siete de once no compilaban bajo la API del kernel, y por eso no estaban en
`obj-m`. Eso son **2189 líneas**, de las cuales 1683 son la capa de GPUVM
(`vmid1_pgt` 646, `vmid1_pgt_backing` 543, `vmid0_gart` 269, `pdb0` 225).

## Por qué no compilaban: cuatro causas, tres mecánicas

Los errores exactos, con las opciones reales de kbuild:

| causa | sitios | mecanico? |
|---|---|---|
| `#include <string.h>` | `vmid1_pgt.c:31`, `vmid0_gart.c:11`, `vmid1_pgt_backing.c:26` | sí |
| `#include <stdint.h>` | `vmid1_pgt.h:96`, `submission.h:40` | sí |
| `UINT32_C` sin proveedor | `vmid0_gart.h:305` | sí |
| `UINT64_MAX` sin proveedor | `vmid1_pgt.c:169` | sí |
| `pm4.h` en otro componente | `ib_bridge.c:6` | **no es un include** |

El kernel no tiene `<string.h>` ni `<stdint.h>`: tiene `<linux/string.h>` y
`<linux/types.h>`. Y `UINT32_C`/`UINT64_C`/`UINT64_MAX` no existen en
`<linux/types.h>`; sus equivalentes de kernel son `U32_C`, `U64_C` y `U64_MAX`.

**Esto ya estaba resuelto en el componente**, en `rx550_spaces.h:34-41`, con un
split `__KERNEL__` y tres `#define`. El trabajo no fue inventar una solución:
fue extender a cuatro ficheros más la convención que el propio componente ya
tenía, con el mismo nombre y el mismo orden.

## La afirmación del comentario de `vmid1_pgt.c`, y por qué era inexacta

El fichero decía, en su cabecera:

```
 *   · ningun header del kernel  para que la aritmetica sea testeable en
 *                         userspace y para no acoplar un constructor puro a un
 *                         entorno de compilacion que no necesita.
 *
 * T10 y T11 verifican estaticamente las dos primeras ausencias.
```

Dos mitades, una exacta y otra no:

- **«para que la aritmetica sea testeable en userspace»** sigue siendo cierto, y
  el split lo preserva: la rama de userspace no toca el kernel.
- **«T10 y T11 verifican estaticamente»** es falso. Leyendo
  `test_vmid1_pgt.c:496-522`, T10 comprueba que no se incluya `rx550_pdb0.h` ni
  se use su encoder; T11, que no se incluya `rx550_vmid0_gart.h` ni se reutilice
  `rx550_pte_encode`. Ninguno de los dos mira cabeceras del kernel.

La lectura equivocada tenía consecuencia práctica: alguien que leyera el
comentario concluiría que añadir el split rompe T10/T11, y no lo rompería.
Queda escrito en el sitio.

## Lo que NO se cambió, y por qué no

`rx550_vmid1_pgt_backing.c` sigue sin compilar bajo kbuild, y **no se tocó**:

```
251:  calloc(b->leaf_count, sizeof(*b->leaves));
253:  calloc(b->leaf_count, sizeof(*b->leaf_dma));
254:  b->leaf_owned = (uint8_t *)calloc(b->leaf_count, 1u);
400:  free(b->leaves);
```

El backing **asigna memoria él mismo**, con `calloc`/`free`. No es un problema de
includes: es arquitectura. Un módulo del kernel no puede llamar a `calloc`.

Las dos alternativas que habría son las dos malas:

- Cambiar `calloc` por `kmalloc` **cambia lo que el test mide**. El código
  depende de que `calloc` ponga a cero (líneas 251-254 asignan y luego relyan
  asumiendo cero). `kmalloc` no lo hace; haría falta `kzalloc`, que es otra
  llamada, y el modelo pasaría a medir otra cosa.
- Poner un `shim` de `calloc`/`free` sobre `kmalloc`/`kfree` detrás de
  `__KERNEL__`. Eso fabricaría una equivalencia que no existe: `calloc` da
  memoria de proceso, `kmalloc` memoria del kernel, y una capa ficticia que los
  iguala por macro es exactamente el tipo de `magic default` que §65 prohíbe.

Un fichero queda visiblemente fuera del kernel, y esa visibilidad es
información. Un fichero que parece del kernel y no lo es, no lo es.

`rx550_ib_bridge.c` tampoco se tocó: `pm4.h` vive en el componente hermano
`04-IMPLEMENTACION/rx550-pm4/`, y el `Makefile` de tests ya lleva `-I` para él
cuando compila en userspace. Eso es una decisión de frontera de componente que
no se resuelve volviendo a compilar más.

## La medida, después

```
$ ./tools/tu_compila.sh
# TOTAL  TU=11  K_SI=8  K_NO=3  U_SI=8  U_NO=3
```

Las tres que quedan:

| TU | clase | por qué |
|---|---|---|
| `rx550_target.c` | SOLO_KERNEL | es código de kernel, como debe ser |
| `rx550_vmid1_pgt_backing.c` | SOLO_HOST | asigna con `calloc`/`free` |
| `rx550_ib_bridge.c` | ROTA | `pm4.h` está en otro componente |

## Y el módulo

`obj-m` pasa de 3 objetos a 8:

```
rx550_drv-objs := rx550_target.o pci_resource.o rx550_mmio_access.o rx550_pdb0.o \
                 rx550_vmid0_gart.o rx550_vmid1_pgt.o rx550_submission.o \
                 rx550_gart_write.o
```

Medido, no supuesto:

- compila con las opciones reales de kbuild (no con las de un `gcc` suelto),
- `rx550_drv.ko` enlaza y genera BTF,
- **728912 bytes**, antes 663832 con 4 objetos y 641208 con 3,
- los 20 símbolos sin resolver **están todos exportados por el vmlinux que está
  corriendo**, comprobado uno a uno contra
  `/lib/modules/7.1.3-200.nobara.fc44.x86_64/build/Module.symvers`. Los dos
  nuevos respecto al `.ko` de 3 objetos son `memset` y
  `__x86_indirect_thunk_rax`, ambos `EXPORT_SYMBOL`.

## El discriminante: la rama de userspace no cambió

Es el riesgo real de un split `__KERNEL__`: que el «arreglo» para el kernel
mude el comportamiento del host. Se mide por los **recuentos de aserciones**,
que deben ser idénticos antes y después:

```
rx550_gart_write.c           59 PASS      rx550_ib_bridge.c    59 PASS
rx550_ib_composer.c          74 PASS      rx550_pdb0.c         75 PASS
rx550_submission.c           59 PASS      rx550_vmid0_gart.c  119 PASS
rx550_vmid1_pgt.c           610 passed    rx550_vmid1_pgt_backing.c 1238 passed
```

Idénticos a los de antes del cambio. Y la puerta entera, con `make` desde cero
y `tests clean` previo:

```
17 suites, con_problema=0,   make EXIT=0
resumen estático: 34 PASS, 0 FAIL
T1-T14 + auditorías: OK
```

Un detalle que sale de paso y conviene tener anotado: la salida de `nm` pasó de
3945 B a **8395 B**. Es exactamente el umbral que apagaba T13 y T14 antes del
finding 1022. Sin esa reparación, este mismo commit habría vuelto a callar dos
comprobaciones sin decirlo. La dependencia entre las dos cosas no era
obvia, y por eso se anota.

## Lo que este hallazgo no dice

- **No dice que el módulo cargue.** No se intentó. `amdgpu` posee `0000:01:00.0`
  (`target_res_claim_regions` devolvería `-EBUSY`), y tomar la GPU es una
  decisión con precondiciones propias (§90), no un efecto secundario de un
  commit.
- **No dice que estas cuatro TUs estén en el camino de `probe()`.** Sigue sin
  haber una sola llamada desde `rx550_target.c`. Estar en el binario y estar en
  el flujo son dos cosas distintas y la segunda no se ha tocado.
- **No dice que `vmid1_pgt_backing.c` se pueda portar.** Se ha clasificado por
  qué no, que es lo que se podía medir sin decidir nada.

## Trazabilidad

- Medida: `tools/tu_compila.sh`, antes 4/11 y después 8/11 bajo kbuild
- Verificación de contratos: `tools/contratos.sh`, 17 invocadas, 0 problemas
- Convención replicada: `rx550_spaces.h:34-41`, `rx550_mmio_access.h:107`
- Hallazgo relacionado: 1022 (el mismo commit habría vuelto a apagar T13/T14)
- Prefijo de numeración: 1023, reservado antes de escribir