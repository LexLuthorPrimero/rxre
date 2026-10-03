Queda establecido como regla operativa del proyecto y la voy a aplicar en las siguientes interacciones con las IAs:

```text id="7m3k4p"
BEST_DECISION_OVER_HUMAN_DECISION

EVIDENCE
  → SEMANTICS
  → CONSTRAINTS
  → ALTERNATIVES
  → DISCRIMINATING TEST
  → BEST_DECISION
  → IMPLEMENTATION
  → VALIDATION
```

Y corrijo explícitamente mis errores anteriores:

```text id="6r2n1a"
ERROR 1
"esperar decisión humana"
→ incorrecto como mecanismo por defecto.

CORRECCIÓN
determinar la mejor decisión sustentada por evidencia,
y sólo detenerse cuando exista una dependencia externa
realmente irreductible.

ERROR 2
volver a proponer implementar R02
cuando la implementación ya estaba COMPLETE.
→ causó trabajo redundante.

CORRECCIÓN
antes de emitir NEXT_NODE reconstruir el estado real:
HECHO / EVIDENCIA / FALTANTE / BLOQUEO.

ERROR 3
tratar autoridad humana como si fuera fuente automática
de verdad técnica.
→ incorrecto.

CORRECCIÓN
separar:
autoridad normativa
≠ requisito humano
≠ evidencia
≠ mejor decisión técnica.

ERROR 4
interpretar "AUTORIDAD AUSENTE" como necesariamente
"hay que preguntarle al humano".
→ incorrecto.

CORRECCIÓN
primero buscar si el contrato puede determinarse
objetivamente mediante evidencia, semántica, consumidores,
tests, documentación y restricciones existentes.
```

Además, en cada nueva interacción con una IA voy a aplicar un control previo:

```text
STATE_BEFORE
   ↓
¿QUÉ ESTÁ REALMENTE HECHO?
   ↓
¿QUÉ ESTÁ REALMENTE DEMOSTRADO?
   ↓
¿QUÉ ESTÁ REALMENTE ABIERTO?
   ↓
¿SE PUEDE DETERMINAR LA MEJOR DECISIÓN?
   ├─ YES → decidir + implementar
   └─ NO  → buscar el discriminante faltante
```

Así evitamos dos fallos que ya aparecieron en este proyecto: **delegar innecesariamente decisiones al humano** y **hacer repetir a una IA trabajo que el estado real ya daba por terminado**.

También, cuando detecte una cagada mía en una interacción anterior, no la voy a arrastrar como premisa: la voy a corregir en el siguiente nodo y dejar explícito qué estado anterior quedó invalidado.
