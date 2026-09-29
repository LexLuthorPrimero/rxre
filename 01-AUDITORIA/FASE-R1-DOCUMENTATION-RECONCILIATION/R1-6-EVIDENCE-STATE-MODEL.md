# R1-6 — MODELO DE ESTADOS DE EVIDENCIA (EVIDENCE STATE MODEL)

> **Tarea R-1.6** — FASE R-1 — 2026-09-22 — SOLO DOCUMENTAL
> Define el vocabulario único de estados de evidencia usado por toda la documentación A–R-1, para que cada
> afirmación sea tasable y comparable. Los informes deben declarar el estado de cada resultado.
>
> **Reconciliación 2026-09-24:** la presencia de un catálogo externo no es validación runtime.
> GFX8, MCLK, RGP/SQTT y ACEs se clasifican como `PARTIALLY_RECONCILED`/`UNKNOWN` salvo
> medición local explícita.

---

## 1. Estados de evidencia de una afirmación (categorías)

| Estado | Nombre | Definición | Usar cuando | Prohibido como base de diseño experimental |
|---|---|---|---|---|
| **[VERIFICADO]** | Verificado | La afirmación tiene fuente primaria/medible y fue confirmada por cross-check independiente | catálogos source-level (GPUPerfAPI v3.17/v3.11.1); datos primarios reproducidos (telemetría) | sí parcial |
| **[REPRODUCIBLE]** | Reproducible | El resultado experimental se repitió ≥2 veces de forma idéntica con el mismo método | contraste A/B×3; soak; escalado | no |
| **[OBSERVADO]** | Observado | Dato sensor directo en un evento único (no repetido) | telemetría de una sola corrida | — |
| **[HIPÓTESIS]** | Hipótesis | Conjetura explicativa NO confirmada por experimento | causas de discrepancia de conteos etc. | SÍ |
| **[DOCUMENTADO]** | Documentado | La afirmación es textual de una fuente (drivers, archivos .reg, whitepapers) pero no medida aquí | offsets, campos, semántica de registros | parcial |
| **[PARTIALLY_RECONCILED]** | Parcialmente reconciliado | Dos fuentes difieren en conteo/alcance; la estructura puede documentarse, pero la semántica/ASIC puede quedar `UNKNOWN` | catálogos GFX8; no habilita programación |
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
4. `[PARTIALLY_RECONCILED]` no desbloquea programación ni rangos seguros; requiere una tupla
   evento/ASIC/instancia y autorización específica.

## 5. Aplicación a resultados actuales (ejemplos)

- GRBM GUI_ACTIVE=2 para GFX8 → **[PARTIALLY_RECONCILED / CATALOG ONLY]** (GPUPerfAPI; no ASIC/runtime).
- SQ WAVES=4 para GFX8 → **[PARTIALLY_RECONCILED / CATALOG ONLY]** (idem; no validación ASIC).
- `W_SMU` A 22.25 vs B 15.78 W → **[OBSERVADO/REPRODUCIBLE según protocolo]** (6 corridas; correlación, no causalidad).
- Lectura SPI_CSQ=0 → **[VERIFICADO]** valor; **[DOCUMENTADO]** semántica snapshot-por-cola sin SELECT.
- Régimen histórico 17/09 → **[NO REPRODUCIBLE]**.
- Conteos CB/SQ/MC → **[PARTIALLY_RECONCILED]** (R1-1; 19/23, 4 discrepancias; no rango seguro).
- Unidad de eventos MC → **[UNRESOLVED]**.

---

**Confirmación read-only:** modelo definido sin escrituras de sistema.
