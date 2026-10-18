# DOGFOOD-003 — VALIDACIÓN REAL DE IDENTIDAD FINDING → RELATION → EVIDENCE

## RESUMEN EJECUTIVO

**Resultado:** `RELATION_GAP_REPRODUCED`

El RXRE activo **no puede** identificar inequívocamente un finding mediante su número de hallazgo, rompiendo la cadena de identidad:

```
FINDING
   ↓
CLAIM
   ↓
RELATION
   ↓
EVIDENCE
   ↓
SOURCE
```

La causa raíz es que el **número de hallazgo no es una clave primaria única** — 65 de 255 números de hallazgo (25.5%) apuntan a múltiples archivos, haciendo que las relaciones que referencian estos números sean ambiguas.

## 1. IDENTIDAD DEL ÁRBOL ACTIVO

```
REPO_ROOT = /home/lucas/Escritorio/rxre
HEAD = 9ce74c53ba5a356fed9893c5f62b32e01f9d883a (main)
BRANCH = main
WORKTREE_STATE = MODIFIED (112 archivos modificados + 203 no rastreados - trabajo activo preservado)
```

## 2. PREGUNTA REAL

Usando la investigación existente sobre la cadena de invalidación TLB de Polaris12:

```
mmhub_v3_0_1_get_invalidate_req
gmc_v8_0_emit_flush_gpu_tlb
mmVM_INVALIDATE_REQUEST
CHIP_POLARIS12
```

El problema central es: **¿puede RXRE identificar inequívocamente el finding y la relación que conectan producer → representation → consumer?**

## 3. ANÁLISIS DE LA TRAYECTORIA

### 3.1 Identidad del Finding (PRIMER ESLAZÓN DE LA CADENA)

```text
TOTAL FINDINGS: 347
NUMEROS DISTINTOS: 255
NUMEROS CON COLISIÓN (>1): 65
FICHEROS IMPLICADOS: 157
PORCENTAJE AMBIGUO: 25.5% (65/255)
```

**Ejemplo crítico - Finding 023:**
- `023-pm4-count-convencion-medida.md` (convención de conteo PACKET3)
- `023-pte-productor-sdma-gfx8.md` (productor de PTE en SDMA)

**Ambos comparten el número 023 pero son hallazgos totalmente distintos.**

### 3.2 Trayectoria de Identidad

**Forward (source → evidence → finding → claim → relation):**
```
SOURCE: gfx_v8_0.c:6320-6332
       ↓
EVIDENCE: PACKET3(COND_EXEC,3) → payload 4
       ↓
FINDING: 023 (AMBIGUOUS: 2 candidatos)
       ↓
CLAIM: Line 200 (NOT_DETERMINED sobre spec PM4)  
       ↓
RELATION: Depends on which 023 file was intended
```

**Backward (relation → finding → claim → evidence → source):**
```
RELATION: CORRECTS=023 (from finding 035)
       ↓
FINDING: 023 (AMBIGUOUS: 2 candidatos - which one did 035 correct?)
       ↓
CLAIM: Could be in either file
       ↓
EVIDENCE: Unknown without knowing which finding
       ↓
SOURCE: Unknown
```

### 3.3 Experimento A/B de Identidad

| Método | Resolución Única | Ambigüedad | Vinculación Incorrecta |
|---|---|---|---|
| **A: Solo número de finding** | ❌ NO | ✅ SÍ (65 casos) | ✅ SÍ |
| **B: Identificador completo (file + line)** | ✅ SÍ | ❌ NO | ❌ NO |

## 4. PRUEBA DE CONSISTENCIA BIDIRECCIONAL

**Fallo demostrado:**
- Finding 035 tiene `CORRECTS=023` 
- Finding 023 tiene DOS archivos posibles
- No se puede determinar cuál de los dos archivos de 023 es el que 035 corrige
- **BIDIRECTIONAL_IDENTITY = FAIL**

## 5. MEDICIÓN DE LA TRAYECTORIA DEL AGENTE

Durante esta sesión:
- Total llamadas RXRE: 3 (relations.py, claims.py, análisis personalizado)
- Llamadas fallidas RXRE: 0
- Llamadas de recuperación manual: 0 (análisis puro de lectura)
- Resoluciones ambiguas detectadas: 65 casos de número de finding
- Vinculaciones incorrectas posibles: Alta (cualquier relación a número ambiguo)
- Trayectos exitosos de relación: 0 (la cadena se rompe en el finding)

## 6. CLASIFICACIÓN DEL PROBLEMA

Cada problema observado debe clasificarse:
- ✅ `RELATION_GAP`: El número de finding no identifica inequívocamente el objeto relacional
- ❌ `RXRE_CORRECTNESS_GAP`: El sistema entrega correctamente la información
- ❌ `PROVENANCE_GAP`: El provenance (file:line) es absoluto y único
- ❌ `WORKFLOW_GAP`: El workflow es correcto, falla la identidad subyacente
- ❌ `AGENT_REASONING_GAP`: El razonamiento es correcto dado los datos de entrada
- ❌ `EXTERNAL_KNOWLEDGE_GAP`: El conocimiento interno es suficiente para detectar el gap

## 7. EVIDENCIA DEL GAP

### 7.1 Hallazgo 259 — Prueba directa
```
# 259 · La clave primaria de findings/ no es única: 65 números con dos ficheros
...
"El número de hallazgo es la clave primaria de la base de conocimiento.
Todo lo que cuelga de él queda ambiguo:
- CORRECTED_BY=025 — ¿qué hallazgo corrige el 025, de los dos?
- CLAIM-025 — ¿cuál de los dos es el claim?
- Una cita como 006-.../025-... — ¿a cuál apunta?"
```

### 7.2 Caso concreto 023/035
```
035-correccion-ptepde-es-polaris12.md: CORRECTS=023
023-pm4-count-convencion-medida.md: Sobre convención de PACKET3 count
023-pte-productor-sdma-gfx8.md: Sobre productor SDMA de PTE
```

### 7.3 Herramienta nextnum.py — Causa raíz
```text
"nextnum.py calcula el siguiente número sin lock y sin reserva en disco,
así que dos sesiones que numeran a la vez obtienen el mismo número."
```

## 8. CONCLUSIÓN

**Resultado principal:** `RELATION_GAP_REPRODUCED`

La relación FINDING → CLAIM → RELATION → EVIDENCE → SOURCE **no puede** ser resuelta inequívocamente porque:

1. **El número de finding no es un identificador único** (65/255 números ambiguos)
2. **Cualquier relación que referencia un number ambiguous es inherentemente ambigua**
3. **La cadena se rompe en el primer eslabón (FINDING)**, haciendo imposible determinar el claim, relation, evidence o source correctos
4. **Solo EVIDENCE (file:line) y SOURCE (file + line) proporcionan identidad absoluta**

## 9. IMPLICACIONES

- Las contradicciones calculadas en `CONTRADICTIONS.md` pueden ser arbitrarias cuando apuntan a números ambiguos
- Los claims citados como `CLAIM-025` son intrínsecamente ambiguos
- El provenance tracking es preciso, pero el subject of that provenance (el finding) puede estar mal identificado
- **No es un problema de correctness de RXRE**, es un problema de identidad subyacente en el sistema de numeración de findings

## 10. ESTADO FINAL

```
RELATION_GAP = REPRODUCED
IDENTITY_CHAIN = BROKEN AT FINDING
STRONGEST_IDENTITY = EVIDENCE/SOURCE (file:line)
REQUIRES_MANUAL_INTERVENTION = YES (para resolver ambigüedades de number)
```

El RXRE activa entrega correctamente la información disponible, pero el identificador de finding es fundamentalmente no único, haciendo imposible la identificación inequívoca en la cadena de conocimiento.

---

# FIN DEL REPORTE
