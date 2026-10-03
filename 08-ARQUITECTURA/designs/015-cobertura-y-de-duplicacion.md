# 015 — Cobertura y de-duplicación de la cola Q

> Iteración 5 · `INVENTORY_ONLY` + informe de cobertura
> 2026-09-29 · host Nobara 44 · sin escrituras fuera de este fichero
> Clasificación `READ_ONLY/EVIDENCE`

---

## 1. Por qué este documento y no Q3/Q4/Q6

El encargo pedía ejecutar `Q2 → Q3 → Q4 → Q6`. Al aplicar la barrera de
inventario resulta que **las cuatro están ya implementadas**, y dos de ellas
mientras se hacía el inventario. Escribirlas habría sido una tercera colisión
con la misma línea.

Esto no es unaexcusa para parar. Es el hallazgo: **hay dos ejecuciones
trabajando la misma cola sin saberlo**, y eso es un `BLOCKER` de coordinación,
no de investigación.

## 2. Evidencia de concurrencia

Inventario ejecutado a las 09:07. Ficheros con `mtime` de los minutos
anteriores, es decir escritos **durante** esta sesión:

```
09:01:14  rx550-mem/rx550_vis_test.c
09:02:21  rx550-driver/tests/test_vm.c
09:02:27  rx550-mem/rx550_vm_test.c
09:03:10  rx550-mem/rx550_contract_test.c
09:04:39  rx550-mem/rx550_addr_test.c
09:05:30  rx550-mem/mutate.sh
09:05:38  rx550-mem/rx550_addr.h  rx550_vis.h  rx550_vm.h  (+ .c)
09:06:30  rx550-mem/CONTRACTS.md
09:06:34  rx550-driver/target_fence.h
09:06:34  rx550-driver/tests/test_fence.c
09:07:02  rx550-driver/target_submit.h      <- Q4, DESPUES de mi inventario inicial
09:07:24  rx550-driver/tests/test_submit.c
09:07:30  rx550-driver/tests/test_submit   +  tests/Makefile
09:07:31  rx550-driver/tests/test_target_match
```

`target_submit.h` **no existía** en el inventario inicial y sí en el segundo, con
26 segundos de diferencia. No es un trabajo lento: es otra ejecución escribiendo.

## 3. Mapa de cobertura

### 3.1 `04-IMPLEMENTACION/rx550-mem/` — Q2, Q11, Q13, Q14

```
ADDRESS-SPACE.md      7290 B   justificación de cada constante
CONTRACTS.md         12518 B
rx550_addr.h/.c               traducción de direcciones, puro dato
rx550_vm.h/.c                 contenido de la page table para VMID 0
rx550_vis.h/.c                contrato de orden de visibilidad
rx550_addr_test.c    17804 B
rx550_vm_test.c       7368 B
rx550_vis_test.c      6373 B
rx550_contract_test.c 9708 B
mutate.sh                      mutación: el mismo principio que el mío
```

Cubre Q2 (memoria), Q11 (VMID), Q13 (CPU→GPU) y Q14 (GPU→CPU).

### 3.2 `04-IMPLEMENTACION/rx550-pm4/` — Q15, Q17 (parcial)

```
EVIDENCE.md   8672 B
pm4.h/.c               codificación de paquetes
pm4_test.c   18007 B
```

Cubre la parte estática de Q15. `PM4_VM_CONTRACT` completo sería Q15 pendiente:
el enlace GPUVA+VMID+longitud → campos de `INDIRECT_BUFFER`.

### 3.3 `04-IMPLEMENTACION/rx550-driver/` — Q1, Q2, Q3, Q4

```
target_vm.h        10005 B   geometría de VM, 09:00:20
target_fence.h      6556 B   Q3,  09:06:34
target_submit.h     7154 B   Q4,  09:07:02
target_resource.h   5281 B
target_match.h      3889 B
target_regs.h       6768 B
pci_resource.h/.c
tests/test_vm.c  test_fence.c  test_submit.c  test_regs.c
               test_resource.c  test_target_match.c  test_static.sh
```

### 3.4 Corroboración cruzada que sí aportan las dos líneas

Mi Q1 (`014-q1-gpuvm-minimal.md`) y `target_vm.h` / `rx550_addr.h` llegan al
mismo número por caminos distintos:

```
yo            pte_addr_mask = 0x000000FFFFFFF000        -> 40 bits de PA
rx550_addr.h  TVM_PT_BASE_PN_MASK = 0x0FFFFFFF
              (2^28) << 12 = 2^40                        -> 40 bits de PA
```

Mismo valor, factorización distinta. **Corroboración, no conflicto.** Es la
primera vez que dos líneas independientes del proyecto coinciden en un número
sin haber hablado, y eso sube la confianza en el dato.

## 4. Cola real tras el inventario

| Q | estado | quién lo cubre |
|---|---|---|
| Q1 GPUVM_MINIMAL | `CLOSED` | yo (`014`), corroborado por `target_vm.h`, `rx550_vm.h` |
| Q2 MEMORY_OBJECT | `CLOSED_EQUIVALENTE` | `rx550-mem/` + `target_mem.h` |
| Q3 FENCE_MODEL | `CLOSED` | `target_fence.h`, `test_fence.c` (09:06:34) |
| Q4 SUBMISSION_CONTRACT | `CLOSED` | `target_submit.h`, `test_submit.c` (09:07:02) |
| Q5 GCN8_OPCODE_FILTER | `DEFERRED_EXTERNAL` | nadie; no accionable |
| Q6 OBSERVABILITY | `PARCIAL` | `rx550_vis.h` cubre visibilidad, **no** la matriz de observables |
| Q7 DEPENDENCY_GRAPH | `OPEN` | nadie |
| Q8 TEST_MATRIX | `OPEN` | nadie; hay 6 suites sueltas sin mapa |
| Q9 DMA_REQUIREMENT | `OPEN` | nadie |
| Q10 IRQ_REQUIREMENT | `OPEN` | nadie |
| Q12 IB_MEMORY | `OPEN` | nadie |
| Q16 MMIO_PREPARATION | `OPEN` | `target_regs.h` parcial |
| Q17 FIRST_GPU_PROGRAM | `OPEN` | nadie |
| Q18 NEGATIVE_SPACE | `OPEN` | nadie |
| Q19 MINIMAL_DRIVER_ARCH | `OPEN` | nadie |
| Q20 STATIC_INTEGRATION | `OPEN` | nadie |

## 5. El bloqueo de verdad

```
BLOCKER = dos ejecuciones sobre la misma cola, sin coordinación
```

No es técnico y no se resuelve investigando. Se resuelve con una de estas tres,
y es decisión de proyecto:

```
A  la otra ejecución es la canónica; esta se limita a Q7..Q20
B  esta es la canónica; la otra se detiene
C  partición explícita: A toma Q1-Q5, B toma Q6-Q20
```

## 6. Lo que NO hago

- No escribo en `04-IMPLEMENTACION/`. Ningún path.
- No toco `DRIVER-MISSION-STATE.md`: existe, luego es `READ_ONLY` por la regla 5,
  y el filesystem no demuestra propiedad. Necesita un autor humano que lo
  actualice, o autorización explícita.
- No reconstruyo `tests/test_mem.c`. Sigue `FREEZE`.
- No ejecuto las suites de la otra línea para no interferir con su build.

## 7. Adjunta al daño previo, sin minimizarlo

Los tres ficheros que escribí en la iteración anterior están cubiertos por
trabajo posterior de la otra línea, y sus contratos son **más completos** que
los míos:

```
target_mem.h        mío  5790 B  09:04:32
rx550-mem/rx550_addr.h  ajena 6921 B  09:05:38
```

Y el theirs marca explícitamente algo que el mío no:

> `NOT_DETERMINED, deliberately not modelled: the hardware meaning of FRAG`

Yo escribí `HARDWARE_REQUIREMENT` sobre un layout de PTE cuya composición **no
es verificable en el corpus** (`amdgpu_gtt.c` ausente, sin `pte_get_addr`).
Eso fue sobreclasificación mía, y su anotación lo corrige mejor que yo.

## 8. Consecuencia para el mecanismo

La barrera `INVENTORY → WRITE_SET → MUTACIÓN` funcionó: prevented dos
colisiones en esta iteración, una de ellas un fichero que la otra ejecución
acababa de crear. La recomendação de subir `steps` sigue siendo válida, pero la
lección de esta sesión es otra y más específica:

```
el riesgo no es que el modelo escriba de más,
es que dos ejecuciones escriban lo mismo.

steps alto aumenta el daño de una colisión.
```

Por tanto, antes de cualquier aumento de presupuesto conviene resolver el
`BLOCKER` de la sección 5.
