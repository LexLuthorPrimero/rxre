# BACKLOG IER — defectos CLI (desde fallas_rxre_8_principios.md)

Fuente: `fallas_rxre_8_principios.md` (oct-2026). Revisión 2026-11-15 verificada en el árbol público.
**Los planos de prueba son propuestas de ciclo IER por falla, no afirmaciones de que cada ciclo haya sido ejecutado.** Cada falla se trata con hipótesis falsable y test concreto; ninguna se da por arreglada sin ejecución.

Verificación actual en el árbol fresco:

| Falla original | Estado verificado hoy | Acción
|---|---|---|
| 6 `_detectar_ciclos_frontier` no detecta ciclos transitivos | **IMPLEMENTADO**: DFS para A→B→C→A en `machine.py:1239` (`_detectar_ciclos_frontier`, docstring «directa + transitiva») | Sin código; pendiente solo el test para ese caso si falta |
| 3 `explain` hash chain | **IMPLEMENTADO**: `machine.py:3012+` calcula y reporta `hash_chain` / `hash_chain_ok` | Sin código; pendiente verificación si el test existe |
| 2 cierre automático de misión | **IMPLEMENTADO**: `machine.py:5459,5486` + `close_mission()` bajo contrato (RXRE-201/202) | Sin código; idem |
| 1 `_with_db_retry` no integrado | **Código muerto**: definida en `machine.py:130`, sin llamadores | Evaluar eliminar o integrar; baja prioridad |
| 8 `discover` crea misiones duplicadas | **CORREGIDO 2026-11-15** (IER-001): `op:discover` reutiliza la misión PENDING del mismo artefacto; test `test_discover_mision_idempotencia.py` — rojo antes → verde después | Hecho |
| 5 prune automático de lecciones | **No implementado** (solo sugerencia) | Candidato a ciclo IER |
| 4 auto-fallback inteligente (fallos recientes del mismo backend) | **No implementado** matiz del cooldown por historial | Candidato a ciclo IER |
| 7 `_clasificar_frontier` heurística simple | Heurística por palabras clave; riesgo de falsa clasificación en texto técnico denso | Candidato a ciclo IER |

## IER-001 (HECHO 2026-11-15)

Ciclo IER aplicado como ejemplo del contrato: problema (duplicación) → hipótesis refutable → test discriminante → corrección mínima → verificación clon → registro.

- **Problema**: `op:discover` llamaba `store.crear_mision` (aleatoria en mission_id) sin verificar duplicados → 2 discover equivalentes producían 2 misiones y 2 tareas.
- **Fix**: en la rama `total_symbols > 0` de `machine.py`, reusar la misión `PENDING` con el mismo título antes de crear; no duplicar tarea; se registra `mission_creation: reused` en findings.
- **Test**: `tools/rxre/tests/test_discover_mision_idempotencia.py` — invoca discover dos veces sobre `/bin/ls`; falla antes (2 misiones, 2 tareas) → pasa después (1, 1).
- **Estado epistemológico**: `PASS PARTIAL` en el dominio del test discriminante; no generaliza a discover sobre otros artefactos hasta que se repita.

## IER-00x pendiente (orden sugerido)

1. **IER-test-frontier** — test discriminante A→B→C→A y A↔B directo para cerrar límites reales del DFS existente.
2. **IER-test-explain** — verificar `hash_chain_ok` en un binario de fixture conocido; red de seguridad.
3. **IER-mission-auto-close-test** — test en discover/select donde todas las tareas quedan COMPLETED → misión cierra; hoy el contrato depende de `mission_closure` — verificar comportamiento en clon fresco.
4. **IER-prune-lessons** — implementar `PRUNE` real con oráculo de "lección obsoleta" (heredoc fixture) o descartar la propuesta documentada.
5. **IER-fallback-cooldown** — medir si `_mejor_backend_para` repite el mismo backend fallido; si sí, cooldown de N ventanas, con test.
6. **IER-clasificar-frontier** — al menos un par de textos adversariales donde ambos motores (heurísticas actual vs. propuesta) divergen; publicación de la discrepancia como límite, no solución.

## Regla

Ningún elemento de este documento se interpretó como defecto hoy sin verificación en árbol — y todos los que resultaron serlo se trataron con el mismo rigor que IER exige para cualquier trabajo sobre código real.
