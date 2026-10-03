# Artefacto · Q8 TEST_MATRIX de la línea de driver

```text
PRODUCER   make -s run   en 04-IMPLEMENTACION/rx550-driver/tests/
CAPTURA    gate-run-1.txt · gate-run-2.txt   (dos corridas consecutivas)
WORKSPACE  06-DRIVER-C-ASM-PERFORMANCE   (bind mount de RX550-INVESTIGACION)
FECHA      2026-10-03   kernel 7.1.3-200.nobara.fc44.x86_64   uid 1000, sin sudo
RUNTIME    NOT_RUN · GPU INTACTA · sin MMIO · sin cargar el módulo
HALLAZGO   06-INGENIERIA-INVERSA/findings/977-suite-gart-no-compila-y-no-era-un-maximo.md
CERROJO    .write-lock/drv-q8
```

## Regla de este artefacto

Las dos corridas se conservan **íntegras**, no resumidas. Un recorte de la
salida de una puerta es un dato sin su contexto, y este proyecto ya ha
pagado por eso más de una vez.

## Qué contiene cada fichero

| | `gate-run-1.txt` | `gate-run-2.txt` |
|---|---|---|
| forma | salida de `make -s run` | ídem, segunda invocación |
| rc | `0` | `0` |
| relacion con el otro | `diff -q` → **byte a byte idénticas** | |

## Recuento de la puerta ampliada

15 suites C + `test_static.sh`:

| suite | aserciones |
|---|---|
| test_vmid1_pgt_backing | 1 238 |
| test_vmid1_pgt | 610 |
| test_mmio_access | 207 |
| test_submission | 59 |
| test_ib_bridge | 59 |
| test_gart_write | 59 |
| test_vmid0_gart | 92 |
| test_ib_composer | 74 |
| test_pdb0 | 75 |
| test_block_size | 79 |
| test_vm | 56 |
| test_submit | 51 |
| test_resource | 50 |
| test_fence | 49 |
| test_regs | 32 |
| test_target_match | 24 |
| **total C** | **2 814** |
| test_static.sh (T1-T14 + auditorías del .ko) | 34 |
| **total puerta** | **2 848** |

## Lo que la puerta NO cubre, y por qué

`test_mem` no compila: `target_mem_host.h:19` declara
`typedef unsigned long long u64;` y el propio `test_mem.c` declara otro `u64`.
Conflicto de tipos. Es trabajo de **otra sesión** (Q2), ya excluido de la cola
por el `tests/Makefile` desde antes de este nodo, y **no se ha tocado**.

Sin sixth suite que inventar: la línea tiene 16 `test_*.c` y la puerta alcanza
a 15. La 16ª depende de trabajo ajeno en vuelo.

## Mutaciones que demuestran que la puerta tiene dientes

Aplicadas sobre **copias en `/tmp/opencode/drv-q8/mut*/`**. El corpus no se
tocó para ninguna de ellas; el fichero de producción reparado es el que está en
`04-IMPLEMENTACION/rx550-driver/rx550_gart_write.c` y el hash está en el commit.

| mutación | rc | recuento | `CHECK` rojo |
|---|---|---|---|
| ninguna (corpus reparado) | 0 | 59 / 0 | — |
| `entries > 65536` de vuelta | 1 | 58 / 1 | `5. backing de 65537 entradas: NO rechazado` |
| sin la guarda `E+F` | 1 | 37 / 65 538 | `5. y el centinela posterior NO fue sobrescrito` |
| `B` de `>` a `>=` | 0 | 59 / 0 | ninguno — mutación mal elegida, no guarda floja |
| sin la guarda `B` entera | 1 | 58 / 1 | `5b. y el canario al que CAERÍA la fuga, intacto` |

La cuarta fila es una mutacion mal elegida, no una guarda floja. La quinta es
la que ANTES de anadir el caso 5b daba `56 / 0` en verde: por eso se anadio 5b.