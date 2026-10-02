# docs/archive/

Contenido histórico que **no se borra** pero que ya no describe el estado actual.

Regla aplicada en todo `docs/`: un cambio de conclusión no borra la anterior. Se marca
`SUPERSEDED` y se conserva el texto original, con el commit y la fecha que lo deja
obsoleto. Sin el estado anterior no se puede reconstruir cómo llegó el conocimiento al
actual.

## Lo que hay aquí

| Fichero | Qué es | Por qué está archivado |
|---|---|---|
| *(pendiente)* | — | — |

## Material histórico que vive fuera de `docs/`

No se copia aquí: ya está en el árbol, y duplicarlo crea una segunda fuente que se
desincroniza. Se referencia:

| Ruta | Qué es | Estado |
|---|---|---|
| `00-INDICE/MASTER-RESEARCH-STATUS.md` | Estado de la línea de telemetría (R-4B / D6 / C1), 64 KB, v2.19, 2026-09-25 | `HISTORICO`. Se autodescribe "punto único de entrada" y ya no lo es: 0 menciones de la línea A. **No se borra.** Ver `CONTRADICTIONS.md` C-007 |
| `00-INDICE/FINAL-RESEARCH-STATUS.md` | Cierre de la línea de telemetría, 2026-09-19 | `HISTORICAL_SNAPSHOT` por su propio autor, con nota de precedencia que apunta a `01-README.md` |
| `00-INDICE/PROJECT-DOCUMENTATION-STATUS.md` | Salud documental de septiembre | `HISTORICO`. Declarado obsoleto por el propio overlay de 2026-09-25 |
| `04-IMPLEMENTACION/PATCH-REGISTRY-FINAL.md` · `PROBLEM-STATUS-FINAL.md` · `RELEASE-CANDIDATE.md` · `FINAL-RELEASE-REPORT.md` | Matriz de problemas y gate de publicación de la línea de telemetría | `VIGENTE` para esa línea, `HISTORICO` para la actual |
| `08-ARQUITECTURA/designs/014-q1-gpuvm-minimal.md` | Geometría GPUVM de Q1, tres cifras `PROVEN` | `REFUTED` por `2599c65`. El texto se conserva. Ver `CONTRADICTIONS.md` C-005 |
| `29⁄9⁄26.md` | Diario de la sesión del 29/09 | `PARCIALMENTE OBSOLETO`: su línea 169 (`WAIT_REG_MEM espera REQUEST == 0`) es `REFUTED` por `017 §4` y **no lleva marca de enmienda**. Ver C-002 y la acción F6 |
| `Escritorio/RX550-INVESTIGACION-NOTEBOOKLM/` | Colección documental anterior (~50 ficheros, sept-2026) | Archivo natural de la línea de telemetría. **Fuera del repo actual**, no versionada aquí |
| `Escritorio/nootbooklm50archivos/` | Segunda copia de esa colección, con la línea BC3 ya incorporada (30/09) | Ídem. Contiene 20 ficheros más que la anterior: es la más reciente de las dos |

## Lo que NO se archiva y por qué

```
NINGUNA CONTRADICCIÓN RESUELTA   van a CONTRADICTIONS.md con las dos versiones
NINGÚN REFUTED                    van a EVIDENCE-MATRIX.md con la marca REFUTED
NINGÚN RESULTADO NEGATIVO         van a NEGATIVE-RESULTS.md con su alcance
NINGUNA HERRAMIENTA INVALIDADA    van a TOOLS-STATUS.md con su arreglo pendiente
NINGÚN SNAPSHOT DENTRO DE docs/   los docs/ describen el estado ACTUAL. Un snapshot
                                  aquí estorbaría: es el error que 00-INDICE ya cometió
```

La razón de no tener todavía nada en este directorio: `docs/` se creó el 2026-10-01 y
todavía no ha ocurrido ninguna supersesión **dentro** de `docs/`. La primera vez que
ocurra, el fichero afectado se mueve aquí con su marca, en lugar de quedarse pareciendo
vigente.