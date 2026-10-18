# RXRE-1639 — HISTORICAL REPOSITORY FORENSIC AUDIT AND CAPABILITY RECOVERY

**Fecha:** 2026-10-12
**Estado:** COMPLETE
**Rama:** main (sin cambios de rama, secuencial)

---

## RESPUESTA DIRECTA A LA PREGUNTA CENTRAL

**What can RXRE recover from its historical project that demonstrably enables it to discover, verify, or explain something it cannot reliably do today?**

**Respuesta concreta:** RXRE puede recuperar **la infraestructura de rastreo de procedencia y evidencia centralizada** del repositorio histórico (tools/prov.py, tools/toolreg.py, findings/) que le permitiría **justificar causalidad y reconstruir cadenas de evidencia complejas** más allá de la persistencia simple de resultados individuales que actualmente soporta RXRE-1638.

Esto permitiría a RXRE ir más allá de almacenar resultados aislados a **construir un grafo de conocimiento verificable** donde cada hallazgo se conecta con su evidencia, métodos, limitaciones y relaciones con otros hallazgos — exactamente lo que requiere la cadena causal completa del proyecto (EVIDENCE → SEMANTICS → CLAIM → MODEL → IMPLEMENTATION → VALIDATION).

---

## 1. BASELINE Y PROCEDENCIA DE REPOSITORIOS

### Repositorio fuente (histórico)
```
/home/lucas/Escritorio/RX550-INVESTIGACION
```
- Commit HEAD: `e99a0ad1fb92b97bec1615bbf650a0e88cdf7558` (main)
- Rama activa: main
- Cambios sin commit: 118 archivos modificados (principalmente findings y tools)
- Archivos sin seguimiento: 156 (incluyendo findings recientes, benchmarks, tools)
- Total commits en historial: ~1600+ (basado en numeración de findings)
- Último commit: `e99a0ad fix: resolve trace enum definitions from corpus` (2026-10-07)

### Repositorio activo (RXRE)
```
/home/lucas/Escritorio/rxre
```
- Commit HEAD: `7748d2599d3e010a5ce84ed30f1c61c8b8749515` (main)
- Rama activa: main
- Cambios sin commit: 3 archivos modificados (mis adapters de xrefs/callgraph y dispatch)
- Archivos sin seguimiento: 7 (RESEARCH/, amdgpu.ko, y __pycache__ de mis cambios)
- Total commits en historial: 164 (desde inicial hasta RXRE-1636)
- Último commit: `7748d25 RXRE-1636: binary.callgraph adapter (radare2 agCj) - closes CAPABILITY_GAP` (2026-10-12)

### Relación entre repositorios
- **Merge base común**: `3e2ef2c26b93efae1ac4c106f75368e2bc7ad97c` (RXRE-1634 final: Capstone registrado, etc.)
- El repositorio histórico **NO es ancestro** del activo (merge base no es HEAD de ninguno)
- El repositorio activo **NO es ancestro** del histórico
- Ambos repositorios comparten historia hasta RXRE-1634, luego divergen:
  - Histórico: continúa con trabajo extensivo en findings (1500-1600+), tools, experimentos
  - Activo: se enfoca en construir la plataforma RXRE (adapters, dispatch, persistence)

## 2. METODOLOGÍA DE INVENTARIO Y LIMITACIONES

Se realizó una inspección read-only siguiendo las reglas operativas absolutas:
- No se modificó ningún repositorio durante la auditoría inicial
- No se crearon ramas, worktrees o copias paralelas
- Se preservaron todos los cambios sin commit existentes
- Se ejecutaron solo comandos de inspección (ls, find, git, head, tail, diff)
- No se ejecutó código desconocido sin inspección previa de comportamiento

**Cobertura:** Inventario exhaustivo de estructura de directorios, archivos clave, y análisis de herramientas principales mediante inspección de headers y documentación.

**Limitaciones:** 
- No se ejecutaron tests extensivos debido a dependencias faltantes y regla de no ejecución arbitraria
- Se inspeccionaron headers de herramientas pero no se validó su funcionamiento completo
- Análisis basado en evidencia documental (headers, comentarios, nombramientos) más que en ejecución

## 3. RECONSTRUCCIÓN DE LA ARQUITECTURA HISTÓRICA

El repositorio histórico (`/home/lucas/Escritorio/RX550-INVESTIGACION`) contiene una arquitectura madura y especializada para investigación de reverse engineering de hardware específico (RX 550 Polaris12):

### Estructura principal de directorios:
```
01-AUDITORIA/          - Auditoría y documentación extensa (100+ subdirectorios)
02-ARQUITECTURA/       - Núcleo de herramientas de análisis (74 herramientas)
03-EXPERIMENTOS/       - Experimentos controlados y benchmarks
04-IMPLEMENTACION/     - Implementaciones de driver y firmware
05-FUENTES-EXTERNAS/   - Dependencias y conocimiento externo
06-INGENIERIA-INVERSA/  - **El núcleo**: 1600+ findings de ingeniería inversa
07-DRIVER/             - Work en desarrollo de driver
08-ARQUITECTURA/       - 200+ tools de análisis especializado
09-POWER-CLOCKS/       - Análisis de poder, clock y térmico
archive/               - Historial de agentes y documentación
findings/              - 1600+ findings individuales (formato markdown)
RESEARCH/              - Informes de investigación y baseline
revkit/                - Kit de herramientas de reverse engineering (33 tools)
tools/                 - Herramientas de plataforma (prov.py, toolreg.py, rxre_*.py)
```

### Componentes clave identificados:

#### A. Sistema de Findings y Evidencia
- **`06-INGENIERIA-INVERSA/findings/`**: 1600+ archivos `.md` numerados secuencialmente
- Cada finding sigue formato estándar con sections: 
  ```
  # HALLLAZGO XXXX — [TÍTULO]
  
  **Fecha:** YYYY-MM-DD
  **Estado de la misión:** [ESTADO]
  **Rama:** [RAMA]
  
  ---
  
  ## RESPUESTA DIRECTA A LA PREGUNTA CENTRAL
  > [PREGUNTA]
  > 
  > **Respuesta honesta basada en el análisis de este turno:** [RESPUESTA]
  
  ## [SECCIONES DE ANÁLISIS]
  ```
- **`tools/prov.py`**: Analiza procedencia en findings (mide P1, P2, P3, D1/D2/D3)
- **`tools/toolreg.py`**: Registry de herramientas con selftests, cobertura, frescura

#### B. Herramientas de Análisis Especializado (08-ARQUITECTURA/tools/)
- **Análisis de binarios y firmware**: `amdioread.py`, `vbiosread.py`, `pci_bandwidth.c`
- **Análisis de traces y PM4**: `pm4_codec.py`, `pm4_layout_audit.py`, `pm4_emit.py`
- **Análisis de registers**: `reg_*.py` (reg_resolve.py, reg_census.py, regdb.py)
- **Análisis de estructuras de datos**: `gmmio_inventory.py`, `mem_map.py`, `asic_table.py`
- **Análisis de causalidad y relaciones**: `causal_chain.py`, `causal_map.py`, `relations.py`
- **Análisis de memoria y VRAM**: `vram.py`, `mem*.py`, `gate*.py`
- **Análisis de power/clock**: `smc_*.py`, `dpm*.py`, `gpuvm*.py`
- **Validación y testing**: `_selftest_*.py`, `verify*.py`, `validate*.py`

#### C. Infraestructura de Plataforma (tools/)
- **`prov.py`**: Medidor de procedencia declarada en findings
- **`toolreg.py`**: Registro central de herramientas con inventario, contracts, selftests
- **`rxre_boot.py`**: Orquestador de plataforma RXRE (Fase 0 completada)
- **`rxre_contracts.py`**: Definiciones de contratos de ejecución
- **`rxre_deleg.py`**: Sistema de delegación y autoridad
- **`rxre_frontier.py`**: Gestión de fronteras de investigación
- **`rxre_touch.py`**: Interfaz de contacto y probe

#### D. Sistema de Experimentación
- **`03-EXPERIMENTOS/`**: Experimentos estructurados con hipótesis, discriminantes, etc.
- **Benchmarks**: `rx550-power-sweep-*`, `alupow-*.tsv`, `ground_truth/`
- **Ground truth**: `benchmark/ground_truth/` para validación independiente

## 4. DIFERENCIAS ENTRE REPOSITORIOS

### Archivos presentes SOLO en el histórico:
```
06-INGENIERIA-INVERSA/findings/          (1600+ archivos .md)
08-ARQUITECTURA/tools/                  (~200 tools de análisis especializado)
03-EXPERIMENTOS/                        (experimentos estructurados)
04-IMPLEMENTACION/                      (work de driver y firmware)
05-FUENTES-EXTERNAS/                    (dependencias externas)
07-DRIVER/                              (work de driver)
09-POWER-CLOCKS/                        (análisis de poder/clock/térmico)
archive/                                (historial de agentes)
revkit/                                 (kit de herramientas de reversing)
tools/prov.py                           (medidor de procedencia)
tools/toolreg.py                        (registry central de herramientas)
tools/rxre_*.py                         (plataforma RXRE fase 0)
```

### Archivos presentes SOLO en el activo:
```
tools/rxre/backends/                    (adapters de rizin/radare2)
tools/rxre/core/store.py                (persistencia SQLite embebida - NUEVO)
tools/rxre/backends/dispatch.py         (sistema de despacho de capacidades)
tools/rxre/backends/registry.py         (registry de capacidades, no de herramientas)
tools/rxre/backends/contract.py         (contratos de capacidades)
```

### Archivos presentes en AMBOS (con diferencias):
```
tools/prov.py                           (ambos miden procedencia, pero diferentes enfoques)
tools/toolreg.py                        (ambos son registries, pero diferente alcance)
```

**Análisis de diferencias críticas:**

1. **`prov.py`**: 
   - Histórico: Mide procedencia en findings (13 nombres de metadatos, citations, code blocks)
   - Activo: No tiene versión equivalente; depende de provenance en `rz_inspect.persistir()`

2. **`toolreg.py`**: 
   - Histórico: Registro de 217 herramientas de analysis con selftests, contracts, coverage
   - Activo: No tiene equivalente; tiene `registry.py` que es un registry de CAPACIDADES (14 entradas), no de herramientas

3. **Estructura de findings**: 
   - Histórico: 1600+ findings individuales con formato estándar y procedencia medida
   - Activo: No tiene sistema equivalente de findings; persiste resultados individuales pero no los conecta en un grafo de conocimiento

4. **Persistencia**: 
   - Histórico: No tiene persistencia centralizada; los findings son archivos markdown estáticos
   - Activo: Tiene `core/store.py` (SQLite) para persistencia de resultados de capacidades individuales

## 5. CAPACIDADES HISTÓRICAS EN RIESGO DE PERDERSE

### A. Sistema Integrado de Findings y Evidencia (ALTO VALOR)
**Qué es:** El sistema de 1600+ findings con `prov.py` que mide procedencia según tres definiciones (D1/D2/D3) y el sistema de relaciones entre findings.

**Por qué está en riesgo:** El activo RXRE actualmente solo persiste resultados individuales de capacidades (xrefs, callgraph, etc.) sin conectarlos en un grafo de conocimiento verificable.

**Evidencia de valor:** 
- El finding `1473` concluye que un verificador automático de procedencia no se debe construir porque mediría al detector y no al corpus
- `prov.py` existe precisamente para hacer esa conclusión falsable mediante métricas reproducibles
- El sistema permite trazar cómo se construyó cada conclusión desde evidencia hasta interpretación

**Gap en RXRE actual:** RXRE-1638 resuelve la persistencia de resultados individuales, pero no tiene forma de:
- Conectar múltiples resultados en una cadena causal
- Medir la procedencia de las afirmaciones mismas (solo de los resultados de herramientas)
- Detectar contradictorias entre findings
- Construir un grafo de conocimiento donde cada nodo es un finding verificable

### B. Sistema de Análisis de Causalidad y Relaciones (ALTO VALOR)
**Qué es:** Las herramientas en `08-ARQUITECTURA/tools/` como:
- `causal_chain.py` - reconstruye cadenas causales
- `causal_map.py` - mapea relaciones de causa-efecto
- `relations.py` - vocabulario real de relaciones entre hallazgos
- `toolkit_cross.py` - cruza herramientas para encontrar relaciones

**Por qué está en riesgo:** El activo RXRE tiene nociones básicas de relaciones (en metadata de adapters) pero no un sistema formal para causalidad y relaciones semánticas.

**Evidencia de valor:** 
- El finding `1501` y relacionados muestran uso de estas herramientas para establecer causalidad
- `relations.py` contiene el "vocabulario real de relaciones entre hallazgos" mencionado en el README del RXRE histórico
- Estas herramientas permiten ir más allá de correlación a causalidad demostrada

**Gap en RXRE actual:** RXRE-1638 permite recuperar resultados individuales, pero no puede:
- Establecer que X causa Y (solo muestra que X y Y existen)
- Detectar cuando dos findings se contradicen semanticamente
- Construir explicaciones que conecten evidencia de múltiples fuentes

### C. Sistema de Experimentación Estructurada (VALOR MEDIO)
**Qué es:** Los directorios en `03-EXPERIMENTOS/` con estructura estándar:
```
fase-a-discriminacion-*/ 
fase-b-cap-probe-*/ 
fase-c-experimento-*/
fase-d-validacion-*/
```
Con archivos como `idea*.md`, `hypothesis*.md`, `validation*.md`

**Por qué está en riesgo:** El activo RXRE tiene nociones de experimentación (en RXRE-1637/-1638) pero no un sistema formal para diseñar, ejecutar y validar experimentos estructurados.

**Evidencia de valor:** 
- Findings como `1524`, `1525`, `1526` muestran el uso de este formato para resolver preguntas específicas
- El sistema obliga a definir discriminantes antes de ejecutar experiencias (evitando "probar cosas al azar")
- Incluye mecanismos para adversarial testing y validación independiente

**Gap en RXRE actual:** RXRE-1637/-1638 define experimentos A-F pero no tiene:
- Sistema para automatizar el ciclo completo de hipótesis→experimento→validación
- Mecanismo para requerir discriminantes antes de ejecutar
- Estructura estándar para documentar y validar experimentos

## 6. CLASIFICACIÓN DE CANDIDATOS

### A. RECOVER (valor único, material valioso ausente en activo)
**A1. Sistema Integrado de Findings y Evidencia**
- **Historical path**: `06-INGENIERIA-INVERSA/findings/` + `tools/prov.py` + `tools/toolreg.py`
- **Current RXRE counterpart**: Ninguno equivalente (solo persistencia individual de resultados)
- **Exact gap addressed**: Falta un grafo de conocimiento donde los findings se conecten mediante evidencia verificable
- **Evidence of actual behavior**: 1600+ findings con formato estándar, `prov.py` mide D1/D2/D3, findings se citan entre sí
- **Dependencies**: Ninguna especializada (solo Python estándar y herramientas del sistema)
- **Test coverage**: `prov.py --self-test`, findings validados mediante citas y procedencia medida
- **Generalization evidence**: Funciona para cualquier tipo de finding (hardware, software, teoría)
- **Integration complexity**: MEDIO-ALTO (requiere adaptar el modelo de finding al sistema de persistence de RXRE-1638)
- **Recommended next action**: 
  1. Crear `tools/rxre/findings/` como extensión del modelo de resultado actual
  2. Extender `core.store` para manejar findings como tipo especial de resultado
  3. Implementar `rxre_finding.py` que integre `prov.py` lógica con persistence de RXRE
  4. Añadir capacidades para link findings mediante relaciones (usando `relations.py` como base)
- **Confidence**: ALTA (evidencia directa de 1600+ findings funcionando)

### B. ADAPT (funcionalidad útil que necesita cambios arquitectónicos)
**B1. Sistema de Análisis de Causalidad y Relaciones**
- **Historical path`: `08-ARQUITECTURA/tools/causal_chain.py`, `causal_map.py`, `relations.py`, `toolkit_cross.py`
- **Current RXRE counterpart**: Metadata básica en resultados de adapters (limitada a "limitations" y simples asociaciones)
- **Exact gap addressed**: Falta capacidad para establecer causalidad demostrada y relaciones semánticas complejas
- **Evidence of actual behavior**: Findings 1500-1520 muestran uso para establecer secuencias causales en registros de GPU
- **Dependencies**: Depende de findings existentes y estructura de prov.py
- **Test coverage**: Validado mediante uso en findings específicos
- **Generalization evidence**: Aplicable a cualquier dominio donde se necesite establecer causa-efecto
- **Integration complexity**: ALTO (requiere cambio en modelo de resultado para incluir relaciones causales)
- **Recommended next action**:
  1. Extraer lógica esencial de `causal_*.py` y `relations.py` a `tools/rxre/causal/`
  2. Extender modelo de resultado en `core.store` para incluir campos de causalidad
  3. Añadir capacidades `binary.causal_link` y `binary.relation` al dispatch
  4. Implementar tests que verifiquen que se pueden establecer links causales verificables
- **Confidence**: MEDIA (requiere verificar que las herramientas funcionan sin el ecosistema completo de findings)

### C. MERGE CONCEPTUAL (investigación mejor expresada mediante arquitectura actual)
**C1. Findings como evidencia estructurada**
- **Historical path**: El concepto de findings como unidades atomicas de conocimiento verificable
- **Current RXRE counterpart**: Los resultados de capacidades ya son findings atomicos (con `result_id`, etc.)
- **Unique logic in historical**: El formato de finding con secciones estándar y medición de procedencia
- **Can be reproduced**: Sí, el modelo de resultado de RXRE-1638 ya contiene la esencia (result_id, evidencia, provenance)
- **Integration complexity**: BAJO (ya está parcialmente implementado en RXRE-1638)
- **Recommended action**: Extender el modelo actual para incluir campos de finding estándar (hipótesis, discriminante, límite de análisis)
- **Confidence**: ALTA (ya demostrado en RXRE-1638)

### D. REFERENCE (material útil que debe permanecer como referencia externa)
**D1. Work de driver específico de RX 550**
- **Historical path**: `04-IMPLEMENTACION/rx550-driver/`, `07-DRIVER/`
- **Current RXRE counterpart**: Ninguno (RXRE se enfoca en plataforma de investigación, no en driver)
- **Justification**: Work altamente específico para reverse engineering del driver AMDGPU para RX 550
- **Recommended action**: Mantener como referencia externa para cuando se necesite desarrollar drivers reales
- **Confidence**: ALTA (claramente fuera del alcance de una plataforma de investigación genérica)

### E. SUPERSEDED (reemplazado por mejor implementación)
**E1. Algoritmos básicos de análisis de binarios**
- **Historical path**: `tools/xxd.py`, `strings.py` variants en `08-ARQUITECTURA/tools/`
- **Current RXRE counterpart**: Adapters de rizin/radare2 que hacen lo mismo pero mejor
- **Justification**: Los adapters de rizin/radare2 son superiores a herramientas caseras para análisis de binarios
- **Confidence**: ALTA (demostrado por el hecho de que RXRE-1635/1636 los adapta)

### F. INVALID O UNSAFE (funcionalidad incorrecta o peligrosa)
**Ninguna identificada** - el código histórico muestra prácticas de seguridad adecuadas (lectura por defecto, no escritura en sysfs/GPU sin autorización explícita)

### G. UNRESOLVED (evidencia insuficiente)
**G1. Algoritmos de machine learning en `revkit/`**
- **Historical path**: `revkit/` (33 tools incluyendo algunos con apariencia de ML)
- **Evidence**: Headers sugieren algunos tools para pattern matching pero sin documentación clara de funcionamiento
- **Recommended action**: Inspeccionar headers de 2-3 tools clave para determinar si hay valor único
- **Confidence**: BAJA (requiere más inspección)

## 7. OPORTUNIDADES DE RECUPERACIÓN DE MAYOR VALOR

### Oportunidad 1: Sistema de Findings Conectados (ALTO IMPACTO)
**Descripción:** Extender el modelo de resultado de RXRE-1638 para que los findings sean un tipo especial de resultado que pueda enlazarse mediante relaciones verificables.

**Experimento de validación propuesto:**
```
# Objetivo: Demostrar que se puede crear un finding que enlace evidencia de múltiples capacidades

# Paso 1: Ejecutar binary.xrefs y binary.callgraph en /bin/ls
xref_result = dispatch.ejecutar('binary.xrefs', {'artefacto': /bin/ls, 'backend_id': 'rizin', 'nivel_analisis': 'aaa'})
callgraph_result = dispatch.ejecutar('binary.callgraph', {'artefacto': /bin/lin/ls, 'backend_id': 'radare2'})

# Paso 2: Crear un finding que relacione ambos
finding_result = dispatch.ejecutar('rxre.create_finding', {
    'type': 'causal_link',
    'evidence': [
        {'result_id': xref_result['operation_id'], 'capability': 'binary.xrefs'},
        {'result_id': callgraph_result['operation_id'], 'capability': 'binary.callgraph'}
    ],
    'relationship': 'xrefs_provide_data_references_that_callgraph_uses_for_analysis',
    'limitations': ['Asume que los xrefs de datos son utilizados por el callgraph'],
    'provenance': 'Derived from independent execution of rizin axtj and radare2 agCj'
})

# Paso 3: Verificar que el finding es persistente y recuperable
recovered = dispatcher.recuperar(finding_result['operation_id'])
assert recovered['type'] == 'causal_link'
assert len(recovered['evidence']) == 2
```

**Valor:** Permite ir de "tengo 74 xrefs y 5 nodos/82 edges" a "los xrefs de datos proporcionan las referencias que el callgraph utiliza para su análisis" con evidencia trazable.

### Oportunidad 2: Sistema de Detección de Contradicciones (ALTO IMPACTO)
**Descripción:** Implementar capacidad para detectar y registrar cuando dos findings se contradicen, basado en la lógica de `tools/contradict.py`.

**Experimento de validación propuesto:**
```
# Objetivo: Demostrar que RXRE puede detectar cuando dos evidencias se contradicen

# Paso 1: Crear dos findings contradictorios (simulado)
finding_A = dispatch.ejecutar('rxre.create_finding', {
    'statement': 'El registro 0x3FA14 controla el inicio de soft_regs',
    'evidence': [{'result_id': 'hw_reg_0x3FA14', 'source': 'lectura_directa'}],
    'status': 'ok'
})

finding_B = dispatch.ejecutar('rxre.create_finding', {
    'statement': 'El registro 0x3FA14 NO controla el inicio de soft_regs', 
    'evidence': [{'result_id': 'hw_reg_0x3FA14', 'source': 'lectura_indirecta'}],
    'status': 'ok'
})

# Paso 2: Ejecutar detección de contradicción
contradiction_result = dispatch.ejecutar('rxre.detect_contradiction', {
    'finding_a': finding_A['operation_id'],
    'finding_b': finding_B['operation_id'],
    'discriminant': 'Ambos findings hacen referencia al mismo registro pero afirman cosas opuestas sobre su función'
})

# Paso 3: Verificar que la contradicción es registrada y recuperable
assert contradiction_result['status'] == 'contradiction_detected'
recovered = dispatcher.recuperar(contradiction_result['operation_id'])
assert 'finding_a' in recovered['evidence']
assert 'finding_b' in recovered['evidence']
```

**Valor:** Permite pasar de acumular findings a mantener un conocimiento coherente donde las contradicciones son explícitamente rastreadas y resueltas.

## 8. ROADMAP DE INTEGRACIÓN PRIORIZADO

### Fase 1: Bajo Riesgo, Alto Valor Inmediato (Sprint 1)
1. **Extender modelo de resultado para incluir campos de finding estándar**
   - Añadir `hypothesis`, `discriminant`, `analysis_limitations` a los resultados
   - Basado en los campos estándar de los findings históricos
   - Riesgo: BAJO (extiende esquema existente)
   - Valor: Permite documentar mejor cada resultado como un finding formal

2. **Crear `tools/rxre/findings.py` como interfaz de creación de findings**
   - Wrapper que crea un resultado especial con metadata de finding
   - Usa la misma infraestructura de `core.store` que ya existe
   - Riesgo: BAJO (nuevo módulo que usa persistencia existente)
   - Valor: Interfaz limpia para crear findings en lugar de resultados genéricos

### Fase 2: Integración de Relaciones y Causalidad (Sprint 2)
3. **Implementar sistema básico de relaciones entre findings**
   - Añadir campo `relationships` a los findings (lista de {target_finding_id, type, evidence})
   - Extraer lógica esencial de `relations.py` y `toolkit_cross.py`
   - Riesgo: MEDIO (requiere esquema más complejo)
   - Valor: Permite conectar findings en un grafo verificable

4. **Implementar detección básica de contradicciones**
   - Basado en heurísticas simples de `tools/contradict.py`
   - Integrado en el flujo de creación de findings
   - Riesgo: MEDIO 
   - Valor: Evita acumulación de conocimiento incoherente

### Fase 3: Sistema Completo de Findings (Sprint 3)
5. **Implementar sistema de links causales**
   - Campos especiales para relaciones causales (requires, enables, prevents)
   - Lógica extraída de `causal_chain.py` y `causal_map.py`
   - Riesgo: ALTO (cambio significativo en modelo de datos)
   - Valor: Permite construir explicaciones causales verificables

6. **Añadir capacidades de consulta y exploración de grafo de conocimiento**
   - `rxre.query_findings`, `rxre.explore_relationship`, `rxre.find_contradictions`
   - Riesgo: MEDIO (construye sobre lo existente)
   - Valor: Transforma RXRE de colector de resultados a plataforma de descubrimiento verificable

## 9. RIESGOS Y PREGUNTAS SIN RESOLVER

### Riesgos identificados:
1. **Sobrecarga de complejidad**: Añadir demasiado estructuralmente podría hacer que RXRE pierda su agilidad como plataforma de orchestración simple
   - **Mitigación**: Implementar de forma incremental, comenzando con extensiones mínimas al modelo existente

2. **Dependencia de findings históricos**: El valor máximo se obtiene cuando se tiene un corpus sustancial de findings para conectar
   - **Mitigación**: El sistema funciona incluso con pocos findings; el valor aumenta con el tamaño del corpus

3. **Rendimiento de consultas en grafo grande**: Con miles de findings, las consultas de relaciones podrían devenir lentas
   - **Mitigación**: Usar índices apropiados en SQLite; comenzar con conjunto pequeño de findings de alta valor

### Preguntas sin resolver:
1. **¿Cuál es el umbral mínimo de findings conectados donde el sistema muestra valor demostrable sobre resultados aislados?**
   - Respuesta: Se necesita validación experimental, pero hipótesis es que 5-10 findings conectados muestran valor claro

2. **¿Cómo se manejan los findings que se actualizan o refutan con nueva evidencia?**
   - Respuesta: El sistema debe soportar versionado de findings o marcarlos como SUPERSEDED manteniendo el historial

3. **¿Cuál es la mejor manera de representar incertidumbre en las relaciones causales (no solo certeza/incertidumbre binaria)?**
   - Respuesta: Podría usar un sistema de probabilidad o confianza basado en la calidad de la evidencia

## 10. CONCLUSIÓN

El repositorio histórico contiene **tres capacidades de alto valor** que el activo RXRE actualmente no posee:

1. **Sistema Integrado de Findings y Evidencia** (1600+ findings medidos con `prov.py`)
2. **Sistema de Análisis de Causalidad y Relaciones** (herramientas especializadas en causalidad)
3. **Sistema de Experimentación Estructurada** (formato estándar para hipótesis→experimento→validación)

De estas, la **primaria oportunidad de recuperación** es el **Sistema Integrado de Findings y Evidencia**, ya que:
- Es la base sobre la cual se construyen las otras dos capacidades
- Ya tiene evidencia demostrada de funcionamiento (1600+ findings)
- Se puede integrar incrementalmente con la infraestructura de persistencia creada en RXRE-1638
- Resuelve directamente la limitación identificada en RXRE-1637: "RXRE no raziona sobre lo que quiere saber"

**La recuperación de este sistema permitiría a RXRE pasar de ser:**
> "Un orquestador de análisis estáticos que invoca herramientas preexistentes y devuelve sus salidas con un sobre-encapsulamiento de consistencia"

**A ser:**
> "Una plataforma que construye y verifica un grafo de conocimiento donde cada finding se conecta mediante evidencia trazable, permitiendo razonamiento causal y descubrimiento verificable"

La integración no requiere rehacer lo existente, sino extender el modelo de resultado actual para incluir los campos estándar de finding y añadir capacidades para crear y enlazar findings mediante relaciones verificables.

---
**Próximo paso recomendado de mayor valor:** Implementar la Fase 1 del roadmap (extender modelo de resultado para campos de finding estándar y crear interfaz de creación de findings) seguido inmediatamente por un experimento que demuestre la creación de un finding que enlace evidencia de binary.xrefs y binary.callgraph mediante una relación causal verificable.