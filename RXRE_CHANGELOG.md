# RXRE — CHANGELOG documental

## 2026-11-15 (reparación pública)

- **PARTIAL — baseline público funcional** (`main` f80989fc..0438586e): el público servía 6 ficheros con marcadores `<<<<<<<` sin resolver (incl. `decision.json` JSON inválido; `tools/toolreg.py` SyntaxError; `tools/rxre/decompiler/` no commiteado). Reparado con resoluciones del propietario + coherencia del registro medido (`mmr_ioctl`, `rea`, `observation_engine`) + tooling recreado adaptado (`verifier/dry_drift.py`, `harness/declared_mutation.py`) + contrato TIERRA-1 en `rxre.create_finding`.
- Verificación pública (clon fresco): `test_cli009` 158/158; `test_backends_bulk` 118/118; `test_dispatch004` 132/132; `test_backends004` 165/165; `test_container1632` 120/120; `test_decomp003` OK; `test_arquitectura_v3_01_contracts` OK.
- Tests dependientes de `amdgpu.ko`: SKIP documentado (artefacto purgado deliberadamente).
- Fallos preexistentes idénticos vs público (DB/corpus locales no públicos): `test_tierra1_contrato`, `test_p003/p004/p0_2_conflict014/cobertura_validacion013`, `test_orchestrator_e2e`.
- **NOT_DETERMINED** independencia por terceros; estado epistemológico PARTIAL, sin `PROVEN`.

## 2026-11-12

- **§1044 R3** — cadena E2E de `filevercmp` sobre `/usr/bin/ls`: `OPEN — NOT_PASS` (791/34.145).
- **§1045** — identidad oficial publicada: método primario; modelo falsable; `RXRE_IDENTIDAD.md`.
- **Añadidos** (esta sesión):
  - `RXRE_ESENCIA.md`, `RXRE_ESTADO.md`, `RXRE_INDICE.md`, `RXRE_FLUJO.md`,
  - `RXRE_PROTOCOLO_SELLADO.md`, `RXRE_PROCEDENCIA.md`, `RXRE_CHANGELOG.md`,
  - `RXRE_LIMITACIONES.md`, `RXRE_OBSOLETOS.md`, `VERIFIED_HASHES.md`
- **Limitaciones preservadas:** sin `--auto`, sin `op:claim`, `AGENTS.md`/DB intactos; R3 abierto; independencia física bloqueada; publicación `READY_NOT_PUBLISHED`.

## 2026-11-12 (M1266 fases)

- A1-DIGEST PASS (scratch); A2 PARTIAL; B2 tmpfs/ext4 PASS_PARTIAL; power-loss NOT_VERIFIED; Gate 2/Recovery/EXP-01…15 no autorizados.
- Contrato `OUTBOX_EVENT_V1 v1.1.0` **RATIFIED**. `OBX1` no migrado.

## 2026-11-11

- M1256..M1265 — reconstrucción `filenvercmp` acotada; `check_tuning` 1080/1080; denominador común de cobertura limitada.
- G1035/G1037/G1042/G1043 EXECUTED (close).

## 2026-10-19 (línea base)

- `SPE 25..29`; `PUB-001..016`; `AUDIT_FINAL`; controversia de desreplegamiento.
- `e2e_001..010` capturados y etiquetados; GPU validado por Vulkan/SPIR-V; `F2` pendiente.
- Bases intactas; `jorgeeee.md` preservado.

## 2026-10-18..2026-10-30 (misiones primeras fases)

- `M300..M350`; arquitectura v3; verificación independiente; sellado; TEERRA/AIRE/FUEGO.
- `benchmark_polari12`; `RX550`; `amdgpu` cargas; GPU validado como oracle SPIR-V; `MMIO` aparte.

## Convenciones

- `PASS` solo integridad / captura física.
- `PARTIAL` admite límites documentados.
- `BLOCKED` sin modificar; código/DB/contratos quedan como están.
- `NOT_DETERMINED` honesto.
