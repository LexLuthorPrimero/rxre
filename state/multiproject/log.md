# RXRE MULTIPROYECTO v2 — Log cronológico

## 2026-11-14 (primera ejecución de esta misión con continuidad persistente)

**Recuperación de estado real (hechos verificados esta sesión):**

- No existía `state/multiproject/` — las ejecuciones previas de esta misión (visible en `METRICAS_R3.md`) abrieron PRs pero no crearon continuidad persistente. Se crea ahora.
- Working tree de `rxre` con cientos de cambios ajenos/preexistentes — **no tocados**. `git status --short` confirmado antes de actuar.
- Repo público `origin` = https://github.com/LexLuthorPrimero/rxre.git (main @ d7d02230). Autorizado por el propietario (2026-11-14): push a `main` de los artefactos de la misión al terminar; PRs upstream nuevos autorizados en esta sesión.
- Herramientas: `gh` autenticado como LexLuthorPrimero; `rizin 0.7.4` (paquete Fedora); `angr 10.0.5` (pip, py3.14); `z3 5.3.1`; `nasm`, `gcc`, `python3`. Clone angr en `~/Escritorio/rxre-angr` @ 8108445 (master). Clone REA en `~/Escritorio/rea` @ 0909d89 (main). Clone rizin fuente: NO presente (el clone de sesiones previas ya no existe; rizin instalado es 0.7.4-9.fc43, distinto de dev/0.10.0 contra el que se hicieron los PRs).

**Estado real de PRs propios (verificado con `gh` 2026-11-14T11:0xZ):**

- rizin, 7 OPEN (de LexLuthorPrimero): #7044 (gzip #6969, 2026-11-13), #7046 (io.c #7034, 11-14), #7048 (z80 #7011, 11-14), #7049 (hexagon LR #6975, 11-14), #7050 (hexagon dual .new #6974, 11-14), #7052 (OpenSSL SHA3 #6896, 11-14), #7054 (rz_core_arg_set #7020, 11-14).
- rizin, 2 CLOSED sin merge por mantenedores (duplicados): #7047 (notxvilka: PR #6238 de MrQuantum1915 cubre el frente), #7051 (notxvilka: PRs #7030/#7025 cubren TMS320).
- rizin #6866 (TMS320): asignado a Rot127/notxvilka, PR #7030 OPEN — trabajo mantenido por ellos; no intervenir.
- rizin #6861 (x86 reg-indirect jumps): PR #7035 OPEN por notxvilka (basado en draft de Sree24-ui), cambios pedidos por Rot127 — no intervenir.
- rizin #6969: PR propio #7044 + PR #6988 (ajeno) abiertos; CI en maintainers.
- angr #7703: PR #7705 OPEN por zardus (maintainer angr) — no duplicar.
- REA: 21 OPEN + 24 CLOSED (0 MERGED) de LexLuthorPrimero — mantenedores cierran sin merge; 0 fusionados hasta la fecha.
- REA #4972 (verificación de equivalencia semántica de código nativo): OPEN, sin asignar, feature request `area:native` — sigue siendo candidato.

**Sustrato técnico verificado:**
- Rizin issues iniciales #6974/#6975/#6969/#6866/#6861 → todos con PRs abiertos (propios o de mantenedores). Ninguno disponible para nueva reparación inmediata.
- angr #7703 → PR #7705 (zardus) OPEN.

**Decisiones:**
1. Crear `state/multiproject/` (este archivo, mission.json, backlog.json, evidence/, capabilities/) — continuidad exigida por la misión.
2. Reconocimiento de RXRE por subagente (arquitectura ALMA/MENTE/etc., capacidades reales vs documentación).
3. Puntuar candidatos y elegir siguiente objetivo técnico (ver backlog.json).

**Pendiente antes de cerrar la sesión:** push a `main` (autorizado) solo con artefactos de la misión; sin incluir cambios ajenos.

## 2026-11-14 (continua) — REA #4972 seleccionado; prototipo construido y testado; persistencia creada

**Autorización del propietario (2026-11-14):** push de los artefactos de la misión a `main` al terminar; PRs upstream nuevos autorizados en esta sesión.

**Selección:** puntuación REA #4972 = 84 (mayoría: reutilización 5/5, evolución 5/5). Todos los issues iniciales (rizin #6974/#6975/#6969/#6866/#6861, angr #7703) tienen PR abierto propio o de mantenedores → no duplicar. Rizin fresh triage (misma noche): 0 candidatas viables — todos los bugs recientes o tienen PR abierto (propio: #7034→#7046, #7011→#7048, #7020→#7054; #6969/#6974/#6975) o están reclamados (#3646 diseño 1.0.0 pendiente de maintainers; #4857 good-first-issue + PR #6160; #5334 A0su con PoC; #6687 root-cause fijado por ManasBagul23/wargio en rz-libdemangle#91-96; #334 Professional Contributors Only).

**Capacidad nueva implementada:** `tools/rxre/semantic/equiv_check.py` — verificación acotada de equivalencia semántica nativa (binario↔binario/C) para funciones escalares int64→int64:
- Capa simbólica: angr 10.0.5 + z3 5.3.1; UNSAT diferencial sobre dominio completo (modelo VEX) → PROVEN; SAT → counterexample → MISMATCH.
- Capa concreta: ctypes con fork-por-llamada (crash aislado); control, no prueba.
- Controles: PROVEN ×3 (incl. con rama), MISMATCH ×2 (incl. confirmación nativa del contraejemplo), TESTED_ONLY vía --no-symbolic, INCONCLUSIVE (orig ausente / C inválido).
- Pruebas: `tools/rxre/tests/test_semantic_equiv_4972.py` — **7/7 PASS** (pytest y python3 -B, rc=0; compatible run_tests.sh). Sin regresión en test_diff_harness/ssa/dataflow/cfg_coverage/decompiler_lite.
- Evidencia: `state/multiproject/evidence/rea-4972/` (5 runs JSON + EXPEDIENTE.md + fixtures pinned).
- Honestidad: era un hueco real — ninguna capacidad RXRE daba veredicto PROVEN/MISMATCH binario↔binario (formal.check era productor vacío; z3 sin usar; angr instalado pero sin tests).

**Estado epistémico:** PARTIAL (prototipo integrado y testado en RXRE; PROVEN = modelo VEX explícito; sin wiring upstream en REA; ninguna reutilización en segundo proyecto todavía).

**Commit:** artefactos de misión + módulo + test, push a `main` (autorizado). Resto del árbol (cientos de cambios preexistentes) SIN tocar.

**Próxima sesión:** (1) decidir con el propietario el wiring upstream REA (provider contract + CLI/MCP; REA es TS complejo y sus mantenedores cierran la mayoría de PRs externos; 21 propios abiertos, 0 mergeados); (2) revisar CI/estado de los 7 PRs rizin y 21 REA; (3) si se quiere contribución upstream esta misión: seguir REA #4972 con un provider mínimo INCONCLUSIVE-honesto SOLO tras visto bueno del propietario; (4) alternativa: fuzzing del equiv_check con funciones aleatorias; (5) seguir sin intervenir en PRs de mantenedores.


## 2026-11-14 (añadido tras revisión de repos) — Inventario de repos del propietario + dictado "deja" sobre P2patch

Revisión read-only de `gh repo list LexLuthorPrimero` (2026-11-14):
- `rxre` (2026-10-11, propio) — repo de la misión; push autorizado 2026-11-14.
- `rxre-cleanroom` (2026-11-12, propio), `rxre-engine` (2026-11-13, propio) — autorizados 2026-11-13 (v1.9.0).
- `rizin` (2026-11-13, fork de rizinorg/rizin), `rea` (2026-11-13, fork de morluto/rea) — **necesarios**: todas las PRs abiertas (9 rizin, 45 REA) salen de estos forks.
- `P2patch` (2026-11-08, fork de P2Patch/P2patch) + issue #3 ("License declaration request for benchmark POVs", firmado "RXRE provenance audit") + PR #4 (`benchmark/LICENSE`, propuesta pendiente de mantenedores) — **creados por una sesión previa fuera del scope documentado de RXRE; sin mención en METRICAS_R3/EXPEDIENTE_R3**.
- **Dictado del propietario: "deja"** — no tocar P2patch, issue #3 ni PR #4. No cerrar, no borrar, no comentar.
- Resto de repos de la cuenta (abr–may 2026): proyectos personales preexistentes, ajenos a esta misión.

## 2026-11-14 (purga ejecutada) — Auditoría y limpieza del repo (autorizada)

- **Tier 1 borrado y purgado de toda la historia**: `RESEARCH/working` (headers AMD `_sh_mask.h` + fuente amdgpu DRM de Linux 7.1.3), `RESEARCH/kernelbuild` (árbol + build), `amdgpu.ko` (módulo compilado), gitlink `KytyPS5-Source`, `.cmd` de rx550-driver.
- **Tier 2 borrado**: `RESEARCH/GAME-001` (corpus SWF), `benchmark/`.
- **Tier 3 borrado**: 96 sueltos del root (informes/diálogos/métricas, incl. METRICAS_R3.md por el problema de privacidad); conservados estructurales (LICENSE, README.md, AGENTS.md, AGENTS_ESTADO_GENERADO.md, run_tests.sh, RXRE_CHANGELOG.md, VERIFY.md, VERIFIED_HASHES.md, RELEASE-NOTES.md, .gitignore, rxre) y directorios de trabajo/evidencia.
- **Purga**: `git filter-branch --index-filter` en clon fresco; todos los refs reescritos; tag v1.0-fase2-completa sin cambios (sin contenido purgado). **Método verificado**: ningún objeto restante contiene las rutas (rev-list --objects --all × rutas = 0); fsck limpio; pack: 480 MiB → 150 MiB.
- **Force push**: `main` → `71b37f1e` (lease sobre bf1c9903). GitHub: sin otras ramas y sin tag (verificado vía API). Objetos huérfanos permanecen server-side hasta que GitHub haga GC.
- **Backup completo**: `/home/lucas/rxre-backup-2026-11-14.bundle` (499 MB, `--all`); recuperable con `git clone /home/lucas/rxre-backup-2026-11-14.bundle`.
- **Árbol local del propietario NO tocado** (49 archivos M preservados); su `main` local quedó divergente del remoto (historia reescrita).

## 2026-11-14 (noche) — Nueva entrega del prompt; rizin bloqueado por mantenedores; 2 PRs nuevos (angr #7788, capstone #3167)

**Reconstrucción de estado:** repo local re-sincronizado contra el remoto reescrito (`main` ahora `13b5b862`; rama de respaldo `main-local-pre-purge`). 454 entradas ajenas preservadas. PRs propios: rizin 5 abiertos (2 cerrados por mantenedores como duplicados: #7049, #7050 — Rot127: ya hay PR suyo para v0.10); notxvilka en #7054: "please stop spamming with AI-generated PRs... otherwise we'll block you from the organization". **Dictado del propietario: "rizin está lleno, pásalo a otra, ignóralo."** REA: 20 abiertos, 0 mergeados. angr #7703 → PR #7705 de zardus (no duplicar).

**Selección:** re-triaje completo exigió el protocolo antiduplicados por repo:
- LIEF #1412 (PE 1000× memory) → PR **#1413** de Henglie ya abierto → descartado.
- radare2 #27393/#27394/#27395/#27396 → PRs #27424/#27419 abiertos por 0verflowme y #27006/#27420 mergeados → descartado.
- angr #7702/#7703 → mismo PR de zardus (#7705) o cluster #7658 → descartado. angr #7640 → P-Code 16-bit DOS MZ, binario no accesible → BLOCKED.
- **angr #7780** (IndexError VFG/UltraPage): sin PR, crash real en 10.0.2, verificado empíricamente; master/10.0.5 ya gatea el IndexError (cap `min(size, off+length)`), pero el centinela fuera de rango seguía creándose. Fix de 1 línea (`addr + size < memory.page_size`) + test de regresión. Verificado con suite de storage (52 passed) contra copia parcheada localmente (restaurada después). PR **#7788** abierto (fork LexLuthorPrimero/angr creado con autorización del propietario).
- **capstone #3162** (ARM CS_OPT_MODE no vuelve a ARM): reproducido en master 823242a tras build local (cmake+ninja). Root cause: `ARM_option()` usa `|=` y CS_MODE_ARM==0 → no-op. Fix estilo X86 (asignación con máscara `CS_MODE_THUMB|CS_MODE_MCLASS|CS_MODE_V8|CS_MODE_BIG_ENDIAN`) + `tests/unit/arm_mode_switch.c` registrado en CMakeLists. Test falla sin el fix y pasa con él; 12/12 unit tests; valgrind fail = preexistente (PATH, "cstest: command not found"). PR **#3167** abierto (fork LexLuthorPrimero/capstone, base `next`, con autorización del propietario).

**RXRE delta esta sesión:** 0 capacidades nuevas "propias" (solo contribuciones upstream); descubrimiento empírico valioso: verificación pre-fix/post-fix con suite propia + control negativo (parche revertido debe fallar el test) — patrón reutilizable para futuros PRs upstream. PRs abiertos por esta misión: 7 rizin + 2 propios nuevos (angr #7788, capstone #3167) + 20 REA; merged en total: 0.

**Pendiente:** estado upstream de #7788/#3167; rizin en silencio total (dictado); REA #4972 wiring sigue sin autorizar.
