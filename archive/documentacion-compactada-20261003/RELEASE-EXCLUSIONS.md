# Exclusiones de publicación — RX550-INVESTIGACION

**Candidate:** `RX550-FINAL-20260925`
**Estado:** `SECURITY_REVIEW=NOT_READY`

Esta lista conserva la evidencia en el árbol local y en el commit baseline
`c6146788e0d4fb12d9b0ec1209fa2840692de0c5`, pero evita que artefactos generados
sean incluidos en el árbol publicable final.

## Archivos que no deben subirse

- `05-FUENTES-EXTERNAS/RX550_Benchmarks/official-downloads/gravitymark/GravityMark_1.89.run`
  (193 MB).
- `05-FUENTES-EXTERNAS/RX550_Benchmarks/cancelled-downloads/Unigine_Superposition-1.1.run.partial`
  (34 MB).
- `03-EXPERIMENTOS/**/build/` y sus objetos, bibliotecas, binarios y caches de
  CMake/Ninja.
- `03-EXPERIMENTOS/WORKLOAD-SINTETICO/main` y `main-graphics`, que son
  ejecutables generados; el fuente está en `src/`.
- `*.log`, `*.nohup.log`, `*.stderr` y volcados de proceso que contengan rutas
  personales o salida de sesión.
- `__pycache__/`, `*.pyc` y caches de Python.
- JSON capturados de C1 bajo `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`;
  se conservan localmente y los informes `.md` son la referencia publicable.
- `00-INDICE/REORGANIZACION-MANIFEST.sha256`, cuyo formato pre-movimiento
  contiene absolutos `/home/...`; la evidencia histórica permanece en el
  baseline local.
- `03-EXPERIMENTOS/FASE-D-COUNTERS-AUDIT/runs/etapa2/resultados_etapa2.json`,
  que mezcla JSON y texto de resumen y no es JSON válido.

## Regla de preservación

No se borra físicamente la evidencia local al retirarla del índice. Antes de
cualquier commit público se debe revisar el diff staged, volver a calcular
hashes y comprobar que no se haya incluido un archivo de esta lista.

## Revisión de secretos

La revisión de alta confianza no encontró claves privadas, tokens GitHub/GitLab,
claves AWS ni asignaciones de credenciales. La presencia de rutas personales,
logs y manifiestos históricos mantiene la revisión en `NOT_READY` hasta que se
haga una exportación pública separada o se acepte explícitamente ese riesgo.
