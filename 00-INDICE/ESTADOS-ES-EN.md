# ESTADOS-ES-EN.md — Normalización de estados documentales

**Fecha:** 2026-09-24 · **Ámbito:** reconciliación documental, sin cambiar resultados.

Esta tabla fija equivalencias para evitar que una traducción o abreviatura se convierta
en una afirmación más fuerte. El estado canónico debe conservar su ambigüedad cuando la
evidencia no permite decidir.

| Español canónico | Inglés equivalente | Significado | Regla de uso |
|---|---|---|---|
| `EXISTE` | `PRESENT` | El artefacto está en el repositorio | No implica ejecución ni validez |
| `IDEA` | `IDEA` | Pregunta o mecanismo propuesto sin evidencia suficiente | No es resultado |
| `DISEÑADO` | `DESIGNED` | Protocolo/documento completo, sin ejecución | No implementar sin autorización |
| `PLANIFICADO` | `PLANNED` | Roadmap sin diseño o ejecución cerrada | No es resultado |
| `AUTORIZADO` | `AUTHORIZED` | Existe permiso concreto para una acción delimitada | La autorización externa es un hecho separado del diagrama |
| `EJECUTADO` | `EXECUTED` | Se realizó al menos una corrida | No implica muestra válida |
| `VALIDADO` / `VALID` | `VALIDATED` / `VALID` | Criterios y evidencia cumplen el gate | Solo con gate explícito |
| `INCONCLUSO` | `INCONCLUSIVE` | Muestra o precondiciones insuficientes | No promover a `SUPPORTED` |
| `PARADA D` | `STOPPED` | Corrida detenida por una condición definida | No se reintenta sin autorización |
| `DESCONOCIDO` | `UNKNOWN` | No se dispone de evidencia suficiente | No se infiere |
| `NO VERIFICABLE` | `NOT VERIFIABLE` | Referencia o artefacto no comprobable en el estado actual | Se conserva, no se sustituye |
| `HISTÓRICO` | `HISTORICAL` | Se conserva para trazabilidad, no como operación actual | No es especificación |
| `SNAPSHOT` | `SNAPSHOT` | Vista o protocolo conservado en un estado anterior | No se actualiza para parecer vigente |
| `PERDIDO` | `LOST` | Artefacto temporal no preservado | No reconstruir sin decisión nueva |
| `NO AUTORIZADO` | `NOT AUTHORIZED` | Requiere permiso explícito nuevo | No ejecutar |
| `REQUIRES CAPABILITY AUDIT` | `REQUIRES CAPABILITY AUDIT` | Falta enumeración o confirmación de capacidad local | No afirmar soporte/runtime |
| `REQUIRES EXPERIMENT` | `REQUIRES EXPERIMENT` | Falta una intervención o medición local | No es un resultado |
| `PARTIALLY VERIFIED` | `PARTIALLY VERIFIED` | Evidencia parcial, sin causalidad completa | Indicar siempre el alcance probado |
| `THERMALLY CONFOUNDED` | `THERMALLY CONFOUNDED` | La ventana no es válida para el veredicto térmico | Excluir del gate y conservar evidencia |
| `DIAGNOSTIC ONLY` | `DIAGNOSTIC ONLY` | La evidencia solo sirve para diagnóstico | No ascender por gates |
| `NOT FOR VERDICT` | `NOT FOR VERDICT` | La evidencia está excluida explícitamente del veredicto | No contarla como PASS/FAIL |
| `CONGELADO` | `FROZEN` | No modificar sin autorización específica | Preservar hash/mtime |
| `NO IMPLEMENTADO` | `NOT IMPLEMENTED` | Diseño sin código o adopción | No confundir con existente |
| `DRAFT` | `DRAFT` | Documento o vista provisional | No es `LIVE` ni resultado |
| `CONFLICT` | `CONFLICT` | Fuentes incompatibles sin precedencia resuelta | El texto canónico prevalece |
| `LIVE` | `LIVE` | Vista reauditada compatible con las fuentes canónicas | No autoriza acciones por sí sola |
| `REQUIRES AUTHORIZATION` | `REQUIRES AUTHORIZATION` | Acción bloqueada hasta permiso nuevo y concreto | No ejecutar |

## Regla de evidencia

- `EJECUTADO` no significa `VALIDADO`.
- `VALIDADO` no significa `SUPPORTED` si el protocolo no lo permite.
- `DIAGNOSTIC ONLY`, `THERMALLY CONFOUNDED` y `NOT FOR VERDICT` no son veredictos.
- Un `HISTÓRICO` o `SNAPSHOT` no prueba capacidad actual.
- `UNKNOWN` no se convierte en resultado negativo por reiteración documental.
- R-4B v2.3: `S1 = EXECUTED / COMPLETADA`, `S2 = PARADA_D`, `VERDICT = INCONCLUSIVE`.
- Los localizadores `/tmp` perdidos se escriben como `HISTÓRICO / NO VERIFICABLE` o
  `PERDIDO / NO VERIFICABLE`, nunca como rutas nuevas.
- `power1_input` se registra como `W_SMU`/potencia estimada por sensor SMU; no como vatímetro independiente.
- `mem_busy_percent` es un proxy de actividad; no es bandwidth.
- MCLK se distingue de la velocidad de datos DRAM efectiva.
