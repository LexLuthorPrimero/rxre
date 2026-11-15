# EXPEDIENTE IER-CORE-001

Estado: **PARTIAL** — primera iteración de IER construida y verificada localmente.

No es: un release completo, una prueba de reproducibilidad de terceros, una promoción de capacidades, o un envío upstream.

Es: la estructura completa de IER construida sobre componentes del árbol actual, con sus tests, verificación de clon, y reglas explícitas de promoción (dicta el propietario SIEMPRE).

## Qué se construyó (todos con tests en tools/rxre/tests/test_ier_*.py)

- `ier/mission.py` (+ `test_ier_mission_roundtrip.py`): objeto MISSION tipado (identity/target/hash/problem/hypotheses/experiments/intervention/validation/outcome); roundtrip por proceso separado.
- `ier/capability.py` (+ `test_ier_capability_lifecycle.py`): registro de capacidades con ciclo DECLARED→EXECUTED→VERIFIED→PROMOTED(RETIRED); PROMOTED solo bajo dictado propietario.
- `ier/investigate.py` (+ `test_ier_investigate.py`): hipotesis rivales machine-readable + discriminantes mínimas (exit_code_delta, output_hash_delta, set_identity...); si H1/H2 producen el mismo resultado => NOT_DETERMINED.
- `ier/deficiency.py` (+ `test_ier_deficiency.py`): evaluador 5 alternativas (reparar/extender/sustituir/combinar/crear) con Q(T,G) y J()=0.15C+0.45R+0.15T+0.25M publicados como DEFAULT_NO_OPTIMIZADOS.
- `ier/lab.py` + `test_ier_lab.py`: sesión de reparación aislada (copia temporal); SHA-256 idéntico pre/post.
- `ier/verify.py` + `test_ier_verify.py`: certificado independiente por hash, oráculo distinto del productor; jamás PROVEN automático.
- `ier/evolve.py` + `test_ier_evolve.py`: Triple Condición (corrección+no-regresión+compatibilidad); promoción solo bajo dictado exacto.
- `ier/explore.py` + `test_ier_explore.py`: ranking público-determinista de issues;
- `ier/upstream.py` + `test_ier_upstream.py`: paquete upstream sellado (revisión jamás auto-envío).

## Estado epidemiológico por componente y del IER en su conjunto

- Flujo PROBLEMA→…→CICLO completo: **construido y probado localmente (tests)**.
- Ejecución real sobre un problema hoy: acotada a IER-001 (op:discover idempotente) + verification.
- Promoción de capacidades: **ninguna autopromovida**. El mecanismo Triple Condición está listo pero se ejecuta solo con evidencia de cada capacidad y firma del propietario.
- Terceros: **NOT_EXECUTED**. La publicación del tag/release y del v1.10.0 depende del dictado tuyo.
- Baseline público: sin regresión (verify hoy: 158/158 CLI; 118 bulk; 132 B7; 165; 120).

## Lo que NO se ha hecho (y no se finge que sí)

- NO hay tag v1.10.0 ni push de estos commits.
- NO hay PROMOTED automático en ningún registro.
- NO hay terceros fuera del host de análisis.
- NO hay fix frío upstream; sí hay piezas documentadas que serían útiles (IER-001 por ejemplo);
- NO se validó que se pueda pasar de partial a otra cosa sin revisión externa.

## Pendientes

- Dictado del propietario para tag/release v1.10.0, o el tag permanece local sin empujar.
- Verificación de promoción de capacidades bajo dictado tuyo y evidencia específica.
- Revisión por terceros (si la dictaras).
