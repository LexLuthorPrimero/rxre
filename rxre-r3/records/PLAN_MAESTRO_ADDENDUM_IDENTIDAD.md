
## 1045. IDENTIDAD OFICIAL DE RXRE (2026-11-12) (G1045 PUBLISHED)

Publicación: 2026-11-12 tras dictamen explícito de la Dirección. Preserva íntegro el histórico §1036–§1044 (addendum, no sustitución). **No certifica** capacidad, no habilita producción; establece la identidad oficial contra la que cualquier resultado futuro debe medirse. No reescribe la composición del repo; el contenido normativo vive en `RXRE_IDENTIDAD.md` (sello independiente).

### 1045.1 Declaración oficial e íntegra

> RXRE es un proyecto de investigación y autoría de método para la ingeniería inversa asistida por IA. Su contribución primaria es un método reproducible por terceros, con rigor epistémico y rechazo explícito de resultados no demostrados. Su motor es una línea de desarrollo experimental cuya eficacia se mide por reconstrucciones semánticas de binarios reales, con cero divergencias y verificación autónoma por terceros, sin intervención del autor original.

_Fecha: 2026-11-12_ — documento sellado: `RXRE_IDENTIDAD.md` (513 B, sha256 `cce22881eb7c1e414d5f8a8d7edca423ce1d0779d4c94aaa55569937a76753ed`).

### 1045.2 Dos métricas, explícitas y separadas

| Métrica | Qué mide | Criterio de éxito |
|---|---|---|
| **Método** | Replicabilidad independiente del procedimiento y sus resultados por terceros | Un tercero reproduce el proceso y obtiene el mismo resultado, sin intervención del autor original |
| **Motor** | Reconstrucciones semánticas de binarios reales | Cero divergencias vs oráculo sellado; verificación autónoma por tercero, sin intervención del autor original |

Las dos métricas quedan en firme:
- Método: replicabilidad independiente del procedimiento y sus resultados por terceros.
- Motor: reconstrucciones reales, exactas y verificadas externamente.

### 1045.3 Qué esta identidad no hace (y no debe interpretarse como)
- No convierte los resultados actuales en éxitos: R3 sigue **OPEN — NOT_PASS** (791/34.145 divergencias; ver §1044.4). La declaración no rebaja ese estado ni lo maquilla.
- No autoriza promoción de etiquetas, integración en producción ni generalización.
- No rebaja la disciplina epistémica: el motor seguirá midiéndose por cero divergencias y verificación autónoma por tercero; los 20+ estados anteriores siguen sobrevendiéndose como notas y no como certificados (documentación derivada, sin sustitución ni reescritura del histórico).
- No autoriza reescritura de §1036–§1044; solo añade esta sección.

### 1045.4 Fuentes de procedencia y sellado
- `RXRE_IDENTIDAD.md` (raíz del repo) — sha256 `cce22881eb7c1e414d5f8a8d7edca423ce1d0779d4c94aaa55569937a76753ed`; 513 B; lectura-vuelta verificada durante esta publicación.
- Respaldo pre-actualización del Plan Maestro: `/tmp/rxre-r3/records/RXRE_PLAN_MAESTRO.md.before-identity`
- Plan Maestro publicado: `rxre/RXRE_PLAN_MAESTRO.md` y `documentacion/RXRE_PLAN_MAESTRO.md` — contenido idéntico (sha256 idéntico, `cmp` OK esperado).
- Tercera copia física del Plan Maestro: no localizada; se documenta como discrepancia (§1044.7 sin cambio).
- Bases intactas verificadas: `AGENTS.md` (`25d57344…`), `rxre.sqlite3` (`c24d58d6…`, 270.336 B), contratos protegidos, `jorgeeee.md`.
- `AGENTS.md` y demás instrumentos de gobernanza permanecen como estaban; la identidad queda registrada aquí sin sustituirlos.

### 1045.5 Veredicto y siguientes pasos
- **G1045 = PUBLISHED** — identidad formalmente declarada y sellada.
- Identidad (A)+(B): método como contribución primaria; motor como línea experimental falsable.
- No se abren misiones automáticamente por esta publicación. El orden de trabajo siguiente, cuando la Dirección lo autorice, será: (1) §1046 o publicación equivalente sellando la aceptación de la identidad; (2) ESENCIA como punto de entrada, con el histórico relegado a apéndice; (3) el MVP `reconstruct` con `REJECTED` como output de primera clase; (4) métrica externa con autonomía del tercero para el motor.
