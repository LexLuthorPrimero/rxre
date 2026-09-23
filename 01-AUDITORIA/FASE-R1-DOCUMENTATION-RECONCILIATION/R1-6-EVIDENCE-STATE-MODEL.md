# R1-6 — MODELO DE ESTADOS DE EVIDENCIA (EVIDENCE STATE MODEL)

> **Tarea R-1.6** — FASE R-1 — 2026-09-22 — SOLO DOCUMENTAL
> Define el vocabulario único de estados de evidencia usado por toda la documentación A–R-1, para que cada
> afirmación sea tasable y comparable. Los informes deben declarar el estado de cada resultado.

---

## 1. Estados de evidencia de una afirmación (categorías)

| Estado | Nombre | Definición | Usar cuando | Prohibido como base de diseño experimental |
|---|---|---|---|---|
| **[VERIFICADO]** | Verificado | La afirmación tiene fuente primaria/medible y fue confirmada por cross-check independiente | datos primarios reproducidos (GPUPerfAPI v3.11.1; ac_perfcounter.c; telemetría reconstruida) | sí parcial |
| **[REPRODUCIBLE]** | Reproducible | El resultado experimental se repitió ≥2 veces de forma idéntica con el mismo método | contraste A/B×3; soak; escalado | no |
| **[OBSERVADO]** | Observado | Dato sensor directo en un evento único (no repetido) | telemetría de una sola corrida | — |
| **[HIPÓTESIS]** | Hipótesis | Conjetura explicativa NO confirmada por experimento | causas de discrepancia de conteos etc. | SÍ |
| **[DOCUMENTADO]** | Documentado | La afirmación es textual de una fuente (drivers, archivos .reg, whitepapers) pero no medida aquí | offsets, campos, semántica de registros | parcial |
| **[PARTIALLY_RECONCILED]** | Parcialmente reconciliado | Dos fuentes difieren en conteo/alcance pero el mecanismo está explicado y las semánticas válidas coinciden | CB 396 vs 405; SQ 299 vs 273; MC 33 vs 22 | parcial |
| **[UNRESOLVED]** | No resuelto | No hay fuente suficiente; no se puede decidir | semántica/unidad de eventos MC | SÍ |
| **[CONTRADICTED]** | Contradicho | Dos fuentes afirman cosas incompatibles y no se puede resolver | (ninguna actual) | SÍ |
| **[NO REPRODUCIBLE]** | No reproducible | Resultado histórico que no se pudo reconstruir (método/condiciones perdidas) | régimen 17/09 | SÍ |
| **[NO VERIFICADO]** | No verificado | Sin evidencia en ninguna fuente | claims de `UNVERIFIED-CLAIMS.md` | SÍ |

## 2. Estados de contador/registro específicos (FASE D)

| Estado de contador | Significado |
|---|---|
| `existe` | registro/offset confirmado (Mesa↔UMR) |
| `escribible` | MMIO RW documentado |
| `evento definido` | PERF_SEL tiene catálogo de nombres/valores |
| `evento semántica validada` | unidad/semántica confirmada con fuente |
| `requiere ventana de shader/CP events` | demanda PKT3_EVENT_WRITE o CP_PERFMON_CNTL |
| `NO UTILIZABLE (etapa mínima)` | sin manera segura de delimitar/leer |

## 3. Estructura de una entrada de evidencia (plantilla)

```
TEXTO DE LA AFIRMACIÓN
- Estado: [VERIFICADO] / [REPRODUCIBLE] / …
- Fuente primaria: <ruta/archivo/línea>
- Fuente secundaria(complementaria): <…>
- Reproducibilidad: <n_réplicas / comando>
- Confianza: ALTA/MEDIA/BAJA
- Cargada por: <FASE/Documento>
- Desacuerdo(s) conocido(s): <ninguno / X vs Y → PARTIALLY_RECONCILED>
```

## 4. Reglas de uso

1. Un resultado sin estado declarado **no se usa** en diseño experimental (default `[NO VERIFICADO]`).
2. `[HIPÓTESIS]`/`[UNRESOLVED]`/`[CONTRADICTED]`/`[NO REPRODUCIBLE]` → **prohibido** como base de diseño hasta
   alcanzar `[VERIFICADO]`/`[REPRODUCIBLE]`/`[DOCUMENTADO]` con cross-check.
3. Al cambiar un documento de estado se registra en su sección de adenda/changelog (historial intacto).
4. `[PARTIALLY_RECONCILED]` desbloquea el uso de la intersección de rangos (R1-1: CB 0..395, SQ 0..272, MC 0..21).

## 5. Aplicación a resultados actuales (ejemplos)

- GRBM GUI_ACTIVE=2 para GFX8 → **[VERIFICADO]** (GPUPerfAPI v3.11.1, constante `GRBM_PERF_SEL_GUI_ACTIVE`).
- SQ WAVES=4 para GFX8 → **[VERIFICADO]** (idem, `SQ*_PERF_SEL_WAVES` en 8 sub-bloques).
- Potencia A 22.25 vs B 15.78 W → **[REPRODUCIBLE]** (6 corridas intercaladas, ratio 1.41).
- Lectura SPI_CSQ=0 → **[VERIFICADO]** valor; **[DOCUMENTADO]** semántica snapshot-por-cola sin SELECT.
- Régimen histórico 17/09 → **[NO REPRODUCIBLE]**.
- Conteos CB/SQ/MC → **[PARTIALLY_RECONCILED]** (R1-1).
- Unidad de eventos MC → **[UNRESOLVED]**.

---

**Confirmación read-only:** modelo definido sin escrituras de sistema.