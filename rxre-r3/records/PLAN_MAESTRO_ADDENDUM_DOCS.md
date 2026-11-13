
## 1046. PUBLICACIÓN DOCUMENTAL DE BASE (2026-11-12) (G1046 PUBLISHED)

Añadida el 2026-11-12 tras autorización explícita de Dirección (“dale hace todo eso”). Preserva íntegro el histórico §1036–§1045 (addendum, no sustitución). **No certifica** capacidades; documenta estado, identidad y navegación del repo para audiencias externas e internas. No reescribe ni elimina ningún documento histórico ni ningún contrato protegido.

### 1046.1 Documentos de base publicados (esta sesión)
| Documento | Propósito | Estado |
|---|---|---|
| `RXRE_ESENCIA.md` | Punto de entrada — qué es / qué leer primero | `PUBLISHED_2026-11-12` |
| `RXRE_ESTADO.md` | Estado real verificado hoy (100s de hashes) | `PUBLISHED_2026-11-12` |
| `RXRE_INDICE.md` | Índice autogenerado del Plan Maestro (1.320 `## `) | `PUBLISHED_2026-11-12` |
| `RXRE_FLUJO.md` | Flujo mínimo reproducible desde cero | `PUBLISHED_2026-11-12` |
| `RXRE_PROTOCOLO_SELLADO.md` | seal-before-reveal protocolo | `PUBLISHED_2026-11-12` |
| `RXRE_PROCEDENCIA.md` | Mapa artefacto→origen→hash→estado | `PUBLISHED_2026-11-12` |
| `RXRE_CHANGELOG.md` | Hitos documentantes 2026-11-12..2026-10-18 | `PUBLISHED_2026-11-12` |
| `RXRE_LIMITACIONES.md` | Limitaciones externas conocidas | `PUBLISHED_2026-11-12` |
| `RXRE_OBSOLETOS.md` | Candidatos a archivo (no eliminar sin revisión) | `PUBLISHED_2026-11-12` |
| `VERIFIED_HASHES.md` | Hashes verificados y re-verificación de sesión | `PUBLISHED_2026-11-12` |
| `RXRE_IDENTIDAD.md` (*sesión previa*) | Identidad oficial (A)+(B) | `PUBLISHED` |

### 1046.2 Actualización de `README.md` y `AGENTS.md`
- `README.md`: línea apunta a `RXRE_IDENTIDAD.md` + `RXRE_ESTADO.md` + `RXRE_INDICE.md`.
- `AGENTS.md`: sección nueva `IDENTIDAD DEL PROYECTO (2026-11-12 — RXRE_IDENTIDAD.md)` declarativa; no sustituye §IDENTIDAD ARQUITECTÓNICA ni los controles ejecutables; referencia a `RXRE_ESTADO.md`.

### 1046.3 Sincronía y verificación
| Artefacto | Verificación en sesión |
|---|---|
| `README.md` | `sha256` 24897ba8… (6.839 B) |
| `AGENTS.md` | `sha256` dcaf870c… (55.638 B) |
| `RXRE_ESENCIA.md` | `64f14a2a…` (2.204 B) |
| `RXRE_ESTADO.md` | `dd1b83ba…` (4.076 B) |
| `RXRE_INDICE.md` | `086b77aa…` (2.850 B) |
| `RXRE_FLUJO.md` | `1ec2a781…` (1.820 B) |
| `RXRE_PROTOCOLO_SELLADO.md` | `49edce38…` (2.405 B) |
| `RXRE_PROCEDENCIA.md` | `ce21f3c1…` (3.185 B) |
| `RXRE_CHANGELOG.md` | `dca69e0a…` (1.732 B) |
| `RXRE_LIMITACIONES.md` | `49b2e6bd…` (2.887 B) |
| `RXRE_OBSOLETOS.md` | `6fff92f3…` (1.578 B) |

### 1046.4 Bases intactas (verificado en esta sesión)
`AGENTS.md` (`dcaf870c…` — actualizado con esta nota de integración, contenido normativo preservado), `rxre.sqlite3` (`c24d58d6…`, 270.336 B), `core/store.py`, `core/evidence_integrity.py`, contratos protegidos, `jorgeeee.md`. Bases de datos no leídas/ejecutadas. Ninguna promoción de etiquetas; ningún `push` remoto; ningún `--auto`/`sudo`/`op:claim` propuesto ni aplicado.

### 1046.5 Documentación resultante vs limitaciones
- Addenda §1044–§1046 son **complementarios**; ningún histórico reescrito.
- Tercera copia física del Plan Maestro continúa **no localizada** (discrepancia §1044.7/§1045.4 preservada).
- Nuevos documentos de base no habilitan producción; estado entre filas no cambia.

### 1046.6 Veredicto
- **G1046 = PUBLISHED** — documentación de base completa para audiencia entrante; histórico preserved; identidad publicada; sin avance de motor.
- **Siguientes (no autorizados)**: ESENCIA como punto de entrada ya es efectivo vía `README.md`+`RXRE_ESENCIA.md`; MVP `rxre reconstruct` según §1044.5/§1045 pendiente de autorización explícita.
