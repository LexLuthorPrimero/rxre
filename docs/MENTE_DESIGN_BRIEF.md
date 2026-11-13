# MENTE — Brief de diseño (borrador, no implementación)

Estado: `DRAFT / DESIGN ONLY / NOT IMPLEMENTED`. Este documento define qué debería ser
MENTE antes de decidir si se construye y cómo. No autoriza ejecución. No modifica el
reconstructor ni contratos protegidos. Fecha: 2026-11-13.

## 1. Qué es y qué no es

MENTE es el mecanismo que hoy falta en RXRE: un motor que **propone hipótesis
rivales, selecciona el experimento con mayor poder discriminante y actualiza las
hipótesis con la observación**, en lugar de elegir herramientas por disponibilidad.
No es un "descompilador LLM", ni un orquestador de herramientas, ni un generador
de informes CFG. Produce una decisión acreditada por dominio, no un prospecto.

Esquema de evolución (flujo completo, única capacidad nueva):

BINARIO DESCONOCIDO → identidad/formato/secciones/símbolos
→ EXTRACCIÓN DE EVIDENCIA (CFG, callgraph, memoria, instrucciones, entradas/salidas)
→ MENTE: HIPÓTESIS RIVALES
→ SELECCIÓN DEL EXPERIMENTO (maximizar discriminación / minimizar coste+riesgo)
→ EJECUCIÓN CONTROLADA → OBSERVACIÓN INDEPENDIENTE (trazas, efectos, estados)
→ ACTUALIZACIÓN DE HIPÓTESIS (descartar / conservar / dividir / declarar incertidumbre)
→ RECONSTRUCCIÓN EJECUTABLE del comportamiento identificado en su dominio
→ ORÁCULO NATIVO SELLADO + DIFERENCIAL (corpus + contraejemplos + 0 divergencias)
→ DICTAMEN POR PROPIEDAD Y POR DOMINIO (PROVEN / PARTIAL / NOT_DETERMINED / BLOCKED)

## 2. Formalización mínima

Hipótesis (unidad de afirmación rival):

```
hypothesis = {
  "id": "...",
  "target_sha256": "...",
  "property": "...",             # propiedad del binario bajo estudio
  "claim": "...",                # afirmación falsable
  "supporting_evidence": [],     # refs a artefactos (sellos)
  "contradicting_evidence": [],
  "predictions": [],             # qué debe observarse si es verdadera
  "required_conditions": [],
  "domain": {},                  # sobre qué entradas/entorno vale
  "epistemic_status": "NOT_DETERMINED"
}
```

Experimento (unidad de discriminación):

```
experiment = {
  "id": "...",
  "hypotheses_to_discriminate": ["h1", "h2"],
  "input_conditions": {...},
  "predicted_outputs": {"h1": ..., "h2": ...},
  "observation_method": "...",   # GDB / traza / diferencial / instrumentación controlada
  "cost_estimate": {...},
  "risk": "...",
  "acceptance_condition": "..."  # resultado observable que confirma o descarta
}
```

Selección: priorizar el experimento cuyas predicciones difieren entre hipótesis
rivales con mayor ganancia informativa esperada sobre coste+riesgo. No la hipótesis
más convincente: el experimento más discriminante. Si dos hipótesis producen la
mismas salidas en todo lo conocido, buscar entrada que las separe; si no existe,
declararlas **indistinguibles en el dominio** y conservar incertidumbre explícita.

## 3. Integración con lo existente (sin duplicar)

| Mecanismo existente | Rol en MENTE |
|---|---|
| Reconstructor (post-Fase 5) | Fuente de evidencia estructural (inventario, CFG, callgraph); no decide semántica |
| `experimental_profiles/` | Conocimiento condicionado por hash como contexto EXTERNO, nunca veredicto |
| `replay`/`evaluate_contract` endurecidos | Puerta de admisión/integridad para cualquier resultado del ciclo |
| `verify.sh` | Sellado + revalidación reproducible de cualquier reconstrucción resultante |
| Hermetic matrices (tests) | Plantilla de pruebas para MENTE: tmp sqlite/artefactos, fail-closed |
| ALMA/ETER/TIERRA (privado) | Evaluadores existentes para claims/registros; MENTE no los sustituye |
| bwrap sandbox | Contención de ejecuciones observadas (rootless, o BLOCKED) |

## 4. Métricas de vida (no volumen)

- Hipótesis rivales realmente discriminadas (no generadas).
- Experimentos con resultado discriminante vs redundantes evitados.
- Hipótesis descartadas por contradicción con experimento (contraejemplos).
- Reducción de incertidumbre por experimento (antes/después).
- % de conclusiones que sobreviven a una prueba nueva.
- Coste de cómputo por propiedad resuelta.
- **Éxito real**: una TERCERA reconstrucción de un binario
  no preparado, con oráculo nativo sellado y 0 divergencias en dominio declarado.

## 5. Estadios y stop-loss

| Estadio | Entrega | Criterio de salida |
|---|---|---|
| 0. Diseño validado | este brief + diagrama + contratos verbales | acuerdo del propietario |
| 1. NO sintético | MENTE sobre binario sintético con semántica conocida y código abierto recompilado (sha distinto): ciclo completo con predicciones y experimentos | la observación descarta hipótesis muertas; incertidumbre residual declarada |
| 2. Dominio de regresión | aplicar al dominio ya sellado (filenvercmp) end-to-end, con el objetivo de REDUCIR hipótesis antes producidas a mano | el ciclo reproduce con ≥ información y sin inventar |
| 3. Objetivo real nuevo | binario GNU real no preparado por el autor; dominio acotado (p. ej. una función version-compare-like); corpus sellado; 0 divergencias en dominio | dictio de dominio PASS/PARTIAL por propiedad; terceros pueden refutar |

Regla stop-loss: si la etapa 3 no produce reducción de incertidumbre real, se
suspende MENTE como capacidad; se conserva lo aprendido como `NOT_DETERMINED`
documentado. No se promociona `PROVEN` a ninguna propiedad sin seal completo.

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Hipótesis plausibles pero infundadas | Cada hipótesis requiere supporting/contradicting evidence sellada; status inicial `NOT_DETERMINED` |
| Métrica inflada (contar volumen) | Única métrica de éxito: discriminación real + tercera reconstrucción |
| Filtro de confirmación | Contraejemplos son salida obligatoria del ciclo, no opcionales |
| Dependencia de host/herramientas | bwrap + timeouts + experimento fallido ⇒ `BLOCKED/NOT_DETERMINED`, nunca `PASS` |
| Subsistema ajeno al proyecto | MENTE reutiliza reconstructor/replay/gate; nada nuevo escribe sin contrato |
| Filtración de conocimiento previo | Perfiles experimentales SOLO por hash (post-Fase 5) |
| Rechazo por terceros | Toda promoción de estado exige paso por PUERTA con revisor externo |

## 7. Preguntas abiertas al propietario (antes de construir)

1. Generador de hipótesis: ¿rule-based explícito vs. LLM asistido con verificación
   obligatoria de predicciones? ¿Ambos, con el LLM solo generando y el motor
   aceptando/rechazando?
2. Persistencia: ¿registramos hipótesis/experimentos en `operations`/`results`
   (store append-only) con actor MENTE? (muy probablemente sí; sin sustituir store)
3. Objetivo de la etapa 3 (p. ej. otra función de coreutils) y criterio de
   cierre exacto (corpus mínimo, oráculo, tolerancia 0, dominio explícito).
4. Presupuesto (tiempo de cómputo, artefactos GDB permitidos, tamaño máximo
   de binario) antes del stop-loss.
5. Nombre de la puerta: ¿DICTAMEN_MENTE_R4 o algo más corto?

## 8. Declaración

Este brief documenta diseño, no capacidad. No afirma que MENTE exista, que
elimine incertidumbre, ni que rinda veredictos. El proyecto sigue necesitando
verificación externa para promover cualquier etiqueta; MENTE es ortogonal a eso.
