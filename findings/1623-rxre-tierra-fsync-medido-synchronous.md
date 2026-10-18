# 1623 — RXRE TIERRA: fsync medido y decisión de `synchronous`

- Fecha: 2026-10-15
- Clasificación: **DEMOSTRADA (medición)** — cada cifra de aquí salió de
  correr el código, no de estimar.

## El síntoma

`op:plan` tardaba 0.284 s sin hacer trabajo real. `op:run` 0.412 s.
Arrancar `machine.py` y listar ops cuesta 0.054 s, así que ~0.23 s no eran
arranque.

## Perfil (cProfile, 5 llamadas, DB real)

```
5 llamadas  ->  0.597 s total
registrar_evento        0.406 s  (0.081 s/llamada)
  commit (fsync)        0.405 s  <-- 68% del total
  close x2              0.181 s  (0.018 s c/u, había 2 conexiones/op)
```

## Lo que se midió, incluido lo que se descartó

Medido sobre una copia de la base real, **20 commits en la misma conexión**
(solo para comparar el coste del commit):

| configuración | s/commit |
|---|---|
| `FULL` rollback (default) | 0.0676 |
| `synchronous=NORMAL` | 0.0022 (31x) |
| `synchronous=OFF` | ~0 |
| `journal_mode=WAL` | 0.0467 |
| `WAL + NORMAL` | 0.0017 (40x) |

**Esa medición fue engañosa y por eso se repitió en el camino real**
(1 escritura por proceso, que es el patrón de esta CLI):

| configuración | commit | close | total/op:plan | veredicto |
|---|---|---|---|---|
| FULL rollback | 0.081 | 0.018 | 0.099 s | baseline |
| WAL + NORMAL | 0.071 | **0.109** | 0.180 s | **PEOR**: `close` hace checkpoint del `-wal`; el patrón "una escritura por proceso" lo paga entero |
| NORMAL rollback | — | — | **0.250 s** total medido | **elegida** |

Lección TIERRA medida: un benchmark de 20 commits en una misma conexión
favorece a WAL; el patrón real de esta CLI (un proceso, una escritura,
cerrar) lo penaliza. La única medición que cuenta es la del camino que se
usa.

## Cambios aplicados

1. `store.conectar`: `PRAGMA synchronous=NORMAL` (sin WAL). Documentado en
   el código con las dos tablas de arriba, incluida la medición descartada,
   para que nadie "optimice" repitiendo el error.
2. `_handle_plan`: se eliminó la segunda conexión a la DB (medido: `close`
   se pagaba dos veces por op). Ahora registra el evento con la misma
   conexión antes de cerrarla.

## Resultado medido tras el cambio

```
op:plan  0.284 s -> 0.250 s   (-12 %)
op:run   0.412 s -> 0.362 s   (-12 %)
```

El commit sigue siendo el grueso (fsync a disco). Bajarlo más exigiría
`OFF` o agrupar escrituras, y eso cambia la durabilidad —no se hace sin una
decisión explícita.

## Semántica aceptada (declarada, no oculta)

`synchronous=NORMAL` en rollback journal: la integridad del fichero sigue
garantizada contra fallo de proceso y de aplicación. La ventana de riesgo
es corte de energía en el instante exacto del commit. `OFF` se midió y se
descartó por esa razón.

## Regresión

cli009 92/92, backends004 159, eventlog006 4/4, agua_application013 5/5,
lecciones006 7/7, aether008 23/23, eter_correlation011 7/7,
aire_consistencia012 9/9, agua_plan008 4/4, autonomy003 11/11,
eco_principios002 39/39. Sin sidecars `-wal/-shm` en `tools/rxre/storage/`.
