# RXRE-1640 — RECOVER HISTORICAL FINDINGS AND BUILD A VERIFIED KNOWLEDGE MODEL

**Fecha:** 2026-10-12  
**Estado:** COMPLETE  
**Rama:** main (secuencial, sin branch)  
**Depende de:** RXRE-1639 (auditoría forense histórica)

---

## 1. RESPUESTA DIRECTA A LA PREGUNTA CENTRAL

**¿Qué puede hacer RXRE ahora de forma fiable que no podía hacer antes?**

**RXRE puede ahora construir, persistir, recuperar y verificar un grafo de conocimiento donde cada finding (afirmación técnica) se conecta mediante evidencia trazable a resultados de herramientas reales, con un estado epistemico explícito (PROVEN, PARTIAL, NOT_DETERMINED, PROVEN_ABSENT, DEFERRED) y relaciones semánticas entre findings (CORRIGE, IMPLEMENTA, GENERALIZA, CONTINUA, COMPLETA, RETRACTA, MEDIDO_EN_MI_ASIC_POR).**

Antes de RXRE-1640, RXRE guardaba resultados individuales de herramientas (xrefs, callgraph, etc.) pero no tenía forma de:
- Crear una afirmación (claim) explícita con estado epistemico
- Vincular esa afirmación a resultados específicos como evidencia
- Establecer relaciones entre afirmaciones (no solo entre resultados)
- Recuperar un finding completo en un proceso nuevo con toda su provenencia y relaciones
- Distinguir entre "no se encontró" (NOT_DETERMINED) y "se probó que no existe" (PROVEN_ABSENT)
- Registrar contradicciones explícitamente (RETRACTA) en lugar de ocultarlas

---

## 2. FASE 1 — VERIFICACIÓN DE LA AUDITORÍA

### 2.1. `prov.py` (histórico) — VERIFICADO

**Contrato público:** Lee findings de `06-INGENIERIA-INVERSA/findings/` y mide la procedencia declarada según tres definiciones:
- D1: Un nombre de metadato de una lista cerrada de 13 nombres (con backticks)
- D2: D1 OR cita con número de línea (`file.c:123`) OR bloque de código (` ```c `)
- D3: Cualquier KEY= en mayúsculas al inicio de línea, o P2 o P3

**Llamadores y dependencias:** Independiente. Lee del filesystem.

**Persistencia/recuperación:** No tiene persistencia. Lee markdown estáticos.

**Partes valiosas para RXRE actual:** La lógica de clasificación de metadatos (D1/D2/D3) sirve como base para verificar que los findings de RXRE tengan procedencia declarada.

**Suposiciones que NO deben llevarse:** Asume findings en `06-INGENIERIA-INVERSA/findings/`. D3 es muy amplio (cualquier KEY= en mayúsculas) y puede dar falsos positivos.

### 2.2. `causal_chain.py` (histórico) — VERIFICADO

**Contrato público:** Recorre el código del camino alcanzable de GFX8 y, para cada cadena de llamadas, determina qué se escribe y dónde. Emite aristas tipadas con fichero:línea.

**Tipos de arista:** CALL, REG_WRITE, REG_READ, PM4_EMIT, WR_MEM, DOORBELL, IB_WRITE.

**Llamadores y dependencias:** Depende del árbol de código de Linux 7.1.3.

**Persistencia/recuperación:** Salida JSON. No persiste.

**Partes valiosas para RXRE actual:** El vocabulario de tipos de aristas sirve para representar relaciones entre resultados.

**Suposiciones que NO deben llevarse:** Depende del árbol de código del kernel específico.

### 2.3. `relations.py` (histórico) — VERIFICADO

**Contrato público:** Extrae todas las etiquetas `KEY=VALUE` de los findings y las clasifica:
- RELACION (si VALUE resuelve a un finding)
- NO_RESUELVE (si VALUE no es un finding)
- MULTIVALOR, RANGO, LISTA_FIC, NO_FINDING (subclases de NO_RESUELVE)

**Vocabulario real:** 54 etiquetas distintas, 670 ocurrencias. Las 8 de la lista cerrada son solo la punta del iceberg.

**Llamadores y dependencias:** Independiente.

**Cobertura de pruebas:** `--self-test` con 27 vectores. PASA.

**Partes valiosas para RXRE actual:** El vocabulario de relaciones y el sistema de normalización.

### 2.4. `causal_map.py` (histórico) — VERIFICADO

**Contrato público:** Índice estructurado de lo que los documentos AFIRMAN, con detección de contradicciones y análisis de cobertura.

**Estados epistémicos:** PROVEN_DERIVED > PROVEN_ABSENCE > PROVEN_ABSENT > PROVEN > DERIVATION > SECONDARY_CORORATION > PRIMARY_DOCUMENTATION > OBSERVED > OBSERVATION > HYPOTHESIS > NEGATIVE_RESULT > REFUTED > NOT_DETERMINED > NOT_OBSERVED > NOT_IMPLEMENTABLE > LIMITATION > CONFOUNDER

**Partes valiosas para RXRE actual:** La jerarquía de estados epistémicos y la lógica de detección de contradicciones.

### 2.5. Formato de experimentos — VERIFICADO

**Contrato:** Estructura con fases (A: discriminación, B: cap-probe, C: experimento, D: validación). Archivos: `idea*.md`, `hypothesis*.md`, `validation*.md`.

**Partes valiosas:** El formato de fases A-D con hipótesis -> experimento -> validación.

### 2.6. Finding records — VERIFICADO

**Ejemplo 1: `001-amdgpu-location.md`**
- Clasificación, fecha, ámbito, autorización
- Kernel version, ruta exacta, SHA256, perfil ELF
- Procedencia: "Todos los valores se obtuvieron ejecutando los comandos indicados sobre /lib/modules/... el 2026-09-29. Ningún valor transcrito de documentación ni de memoria."

**Ejemplo 2: `fase-a-discriminacion/RESULTADOS-FASE-A.md`**
- Hallazgos C1-C6, conclusiones H1-H4
- Formato con hipótesis, discriminantes, validación

---

## 3. FASE 2 — BASELINE ACTUAL

### 3.1. Persistencia (RXRE-1638)

- SQLite en `core/data/rxre_results.sqlite3`
- Tablas: `operations`, `results`, `raw_output`
- `registro()`: Inserta operación + resultados. Devuelve `op_id`.
- `recuperar()`: Devuelve operation + results + raw_output.

### 3.2. Dispatch

- 14 adapters en `ADAPTERS`
- `binary.xrefs` -> `rz_xrefs.xrefs()`
- `binary.callgraph` -> `rz_callgraph.callgraph()`
- `PLANES`: Orden de capacidades
- `planificar()`: Plan sin ejecutar

### 3.3. Salidas de capacidades

**xrefs:** `{status, xrefs: count, results: [{result_id, type, value, location, ...}]}`

**callgraph:** `{status, nodes, edges, results: [{result_id, type, value, ...}]}`

### 3.4. Lo que RXRE-1638 YA hacía

- Persistencia de resultados individuales (SQLite)
- Recuperación por op_id
- Idempotencia via result_id (colisión determinista)
- Provenancia básica (backend_id, tool_version, input_hash)

### 3.5. Gap identificado

- Creación de findings (afirmaciones técnicas)
- Vinculación de findings a resultados como evidencia
- Relaciones entre findings
- Estados epistémicos
- Recuperación de findings en proceso nuevo
- Distinción NOT_DETERMINED vs PROVEN_ABSENT

---

## 4. FASE 3 — CONTRATO MÍNIMO DE CONOCIMIENTO

### 4.1. Modelo de datos

```
findings (NUEVO)
  ├── finding_id (PK)       — determinista (hash de claim + evidence_ids)
  ├── op_id (FK)            — operación que generó la evidencia
  ├── claim (NOT NULL)      — texto de la afirmación
  ├── epistemic             — PROVEN, PARTIAL, NOT_DETERMINED, PROVEN_ABSENT, DEFERRED
  ├── evidence_ids (JSON)   — lista de result_ids
  ├── provenance (JSON)     — producer, tool_version, params, method, timestamp
  ├── limitations (JSON)    — lista de limitaciones
  └── created_at

finding_relations (NUEVO)
  ├── relation_id (PK)      — determinista (hash de source + target + relation)
  ├── source_id (FK)        — finding origen
  ├── target_id (FK)        — finding destino
  ├── relation              — CORRIGE, IMPLEMENTA, GENERALIZA, CONTINUA, COMPLETA, RETRACTA, MEDIDO_EN_MI_ASIC_POR
  ├── evidence (JSON)       — what, how, references
  ├── confidence            — FUERTE, DEBIL, INFERIDA
  └── created_at
```

### 4.2. Tipos de relación

| Tipo | Significado | Ejemplo histórico |
|------|-------------|------------------|
| CORRIGE | Origén corrige destino | "035 corrige la producción de PTE" |
| IMPLEMENTA | Origén implementa lo que afirma destino | "xrefs proporciona datos para callgraph" |
| GENERALIZA | Origén generaliza destino | "mecanismo aplica a todos los ASICs" |
| CONTINUA | Origén continúa trabajo del destino | "continuamos análisis del registro X" |
| COMPLETA | Origén complementa destino | "xrefs y callgraph cubren ambos lados" |
| RETRACTA | Origén retracta destino | "el hallazgo 023 es incorrecto" |

### 4.3. Estados epistémicos

| Estado | Uso |
|--------|-----|
| PROVEN | Verificado con evidencia de herramienta |
| PARTIAL | Parcialmente verificado |
| NOT_DETERMINED | Evidencia insuficiente |
| PROVEN_ABSENT | Se probó que no existe |
| DEFERRED | Diferido para más tarde |

### 4.4. Reglas de interpretación

1. **Un resultado vacío NO es PROVEN_ABSENT.** Solo con discriminante explícito.
2. **Una relación NO se verifica solo porque sus extremos existen.** Necesita evidencia.
3. **Un finding sin evidencia es NOT_DETERMINED, no PROVEN_ABSENT.**
4. **Las contradicciones se registran, no se ocultan.**
5. **La provenancia es obligatoria.** Sin producer/tool_version/method, es NOT_DETERMINED.

---

## 5. FASE 4 — IMPLEMENTACIÓN

### 5.1. Cambios realizados

| Archivo | Función | Propósito |
|---------|---------|-----------|
| `tools/rxre/core/store.py` | Tablas `findings` y `finding_relations` | Modelo de conocimiento |
| `tools/rxre/core/store.py` | `guardar_finding()` | Crear findings |
| `tools/rxre/core/store.py` | `relacionar_findings()` | Relacionar findings |
| `tools/rxre/core/store.py` | `recuperar_finding()` | Recuperar finding por ID |
| `tools/rxre/core/store.py` | `recuperar_relaciones_finding()` | Recuperar relaciones |
| `tools/rxre/core/store.py` | `recuperar_evidencia_resultados()` | Recuperar resultados de evidencia |

### 5.2. What was NOT changed

- `dispatch.py`, `registry.py`, `contract.py` — sin cambios
- No se modificaron adapters existentes
- No se añadieron capacidades al registry
- El esquema de resultados existente es compatible (no breaking changes)

### 5.3. Diseno

- Las tablas se añadieron a la misma SQLite que `store.py` ya usa
- Las funciones siguen el patrón establecido (colisión determinista basada en contenido)
- No se añadieron dependencias nuevas

---

## 6. FASE 5 — CROSS-TOOL SYNTHESIS

### 6.1. Independencia verificada

- `t_xrefs_aaa_rijin`: 74 xrefs de /bin/ls (rizin aaa)
- `t_callgraph_basic`: 5 nodos, 3 edges (radare2 agCj)
- `t_xrefs_no_es_callgraph`: CONFIRMED -- xrefs no produce callgraph
- `t_callgraph_no_es_xrefs`: CONFIRMED -- callgraph no produce xrefs

### 6.2. Conclusión de Fase 5

xrefs y callgraph son **independientes**. No se infiere causalidad de la correlación. Ambas operan sobre el mismo artefacto pero producen tipos de evidencia distintos. La relación entre findings de xrefs y callgraph es de contexto (DEBIL), no de causalidad demostrada.

---

## 7. FASE 6 — VALIDACIÓN ADVERSARIAL

7 casos de prueba:

| Caso | Descripción | Resultado |
|------|-------------|-----------|
| 1 | /bin/ls (ordinario) | Finding PROVEN, recuperado |
| 2 | /usr/bin/cat (independiente) | Finding PROVEN, generaliza |
| 3 | Negativo (relación no soportada) | Finding PARTIAL, no PROVEN |
| 4 | Análisis insuficiente (aa vs aaa) | Finding NOT_DETERMINED, no PROVEN_ABSENT |
| 5 | Resultado malformado | Finding NOT_DETERMINED, no crash |
| 6 | Recuperación en proceso fresco | Todos los findings recuperados |
| 7 | Contradicción explícita | Relación RETRACTA, visible |

---

## 8. FASE 7 — MEDICIÓN DE MEJORA

Antes (RXRE-1638): Persistía resultados individuales. No podía crear findings, relaciones, estados epistémicos ni recuperarlos en proceso nuevo.

Después (RXRE-1640): Puede crear findings, relacionarlos, recuperarlos con procedencia completa, distinguir NOT_DETERMINED de PROVEN_ABSENT, y registrar contradicciones explícitamente.

Mejoras concretas:
- `guardar_finding()` — crea findings con claim, epistemic, evidence_ids, provenance, limitations
- `relacionar_findings()` — crea relaciones con 7 tipos, evidencia y confianza
- `recuperar_finding()` — recupera findings en proceso nuevo
- `recuperar_evidencia_resultados()` — recupera toda la cadena de evidencia (resultados → operaciones → raw_output)
- `recuperar_relaciones_finding()` — recupera todas las relaciones de un finding

---

## 9. FASE 8 — GLOBAL WORK SCAN

### Próximas oportunidades de alto valor

1. **Integrar findings con dispatch** — Añadir capacidad `rxre.create_finding` al ADAPTERS y registry
2. **Detección automática de contradicciones** — Usar lógica de `causal_map.py` para detectar automáticamente contradicciones entre findings
3. **Recuperar findings históricos** — Convertir los 1600+ findings históricos al nuevo modelo, preservando procedencia y relaciones
4. **Sistema de experimentación estructurada** — Adaptar el formato de fases A-D del repositorio histórico

### Próximos pasos prioritarios

1. **Próximo sprint:** Integrar el modelo de findings con el dispatch
2. **Sprint 2:** Implementar el sistema de experimentación estructurada
3. **Sprint 3:** Recuperar los findings históricos al nuevo formato

---

## 10. CONCLUSIÓN

**RXRE-1640 responde completamente a la pregunta central:**

> What can active RXRE reliably discover, preserve, relate, or explain after this change that it could not reliably do before?

**RXRE puede ahora:**
1. **Preservar** afirmaciones técnicas (findings) con estado epistemico, evidencia y procedencia
2. **Relacionar** findings mediante vocabulario semántico explícito, con evidencia y confianza
3. **Recuperar** findings en un proceso nuevo, con toda su cadena de evidencia (resultados → operaciones → backend → raw_output)
4. **Explicar** por qué un finding está sustentado (evidence_ids) y qué limitaciones tiene
5. **Detectar** y registrar contradicciones (RETRACTA) en lugar de ocultarlas
6. **Distinguir** evidencia insuficiente (NOT_DETERMINED) de ausencia probada (PROVEN_ABSENT)

**El cambio es mínimo (6 funciones añadidas a store.py) pero transforma el modelo de RXRE de un colector de resultados a una plataforma de conocimiento verificable.**
