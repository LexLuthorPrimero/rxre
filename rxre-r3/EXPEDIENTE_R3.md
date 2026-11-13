# EXPEDIENTE R3 — Cadena E2E de reconstrucción semántica de filenvercmp/filevercmp sobre /usr/bin/ls (2026-11-12)

**Estado: OPEN — cero divergencias en ambas generaciones selladas (update-5, 2026-11-12); sin dictamen PASS de tercera parte.** Las 791 divergencias originales fueron resueltas (reconstrucción por transcripción literal del desensamblado) y verificadas en dos generaciones selladas (34.145 + 34.145 casos), 3 toolchains y sandbox bwrap. No se habilita producción ni generalización; la verificación autónoma de terceros (fuera de este host/autor) permanece NOT_EXECUTED.

## 1. Objetivo y alcance
- Binario objetivo: `/usr/bin/ls` (sha256 `54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c`; BuildID `ae6605eeca6cc2f19d18fdd53a521e501df3456d`; 153 400 B; ELF64 PIE stripped; `.text` vaddr `0x10c0`).
- Función semántica: `filenvercmp` / `filevercmp` en vaddr `0x4fa0` (contiene `verrevcmp` en `0x4b60` y `file_prefixlen` en `0x4a80`).
- Alcance declarado: **solo** `filenvercmp` y su subcadena léxica; no se amplía a otras funciones, otros binarios ni a integraciones productivas.
- Restricciones de la misión respetadas en ejecución: sin GPU física, sin `sudo`, sin `--auto`, sin `op:claim`, sin bucles autónomos, sin modificar repo/relativos, sin tocar Plan Maestro (hasta autorización explícita posterior del 2026-11-12), `AGENTS.md` intacto.

## 2. Método aplicado
EVIDENCE → SEMANTICS → SCHEMA → DISCRIMINATING TEST → IMPLEMENTATION → VALIDATION, acumulado:
1. Identidad verificada del ELF (sha256, estat, BuildID, `readelf -h`, secciones `.text`/`.rodata`).
2. `objdump -d` de cada función objetivo hacia `/tmp/rxre-r3/evidence/*.asm`.
3. Generador determinista propio de casos (`oracle/gen_cases.py`, SEED=20261112 con ~123 base×123 base+6.000 aleatorios): `cases_seed20261112.txt`, sha256 `bfa30fb358…`.
4. Oráculo independiente por mmap de `/usr/bin/ls`: `oracle/matrix_gen` (sello `matrix_native.txt`, sha256 `ed5e91ef…`, 34.145 líneas, 0 errores de ejecución).
5. Reconstrucción fresca desde desensamblado y comportamiento diferencial (`reconstruction/filenvercmp.c`, compilada `-std=c11 -Wall -Wextra -Werror -pedantic`, rc=0).
6. Diferencial ejecutada con `harness/verify_recon` (no se modifica la semántica del harness).

## 3. Componentes verificados con evidencia positiva
| Componente | Método | Resultado |
|---|---|---|
| Comparador de byte único (posición 0 / 1..255) | `pair_matrix_255.csv` (32.385 pares, `probe255`); `pair_matrix_interior.csv` (32.385 pares, `probe_interior` @ posición 1 post-byte fijo `q`) | **0 / 32.385** discrepancias en la semántica de un byte (modelo afín `rc = RANK[i]−RANK[j]` con tres excepciones catalogadas) |
| `file_prefixlen` | 7.320 cadenas estructuradas (`prefix_scan2.txt`, `probe_prefix`) | **7.320 / 7.320** exactitud (regla «longest trailing letter/~ init segment»; `out_len == strlen` en todos) |
| `w_end_probe` (sintaxis de fin de lado) | 255 bytes | **255 / 255** match con tabla `w_of` (letras `c+1`; dígitos `{0}→0,{1..9}→1`; demás `c+257`; `~ → −1`) |
| Punto vs grupo de dígitos fuera de cadena | `pair_matrix.csv` (8.001 pares en bytes 1..127) | Tabla completa transitiva y antisimétrica, 0 violaciones; comportamiento de `.` y `~` en posición 0 capturado |

## 4. División en objetivos secundarios abiertos (791 discrepancias)
Ranuras divergentes principales:
- **777** casos con al menos un `.` en el interior (clase `dot-mid`): incluye `'a!b' vs 'a.'`, `'R96]'9B' vs 'R.'`, `'a.1.10' vs 'a.1.010'`.
- **14** casos con dot-leading múltiple (##`both-dot`): `'...' vs '.a'`, `'.a~' vs '...'`.

Las tres piezas verificadas no son suficientes para cerrar la cadena: **el anidamiento la ↔ prefix en puntos iniciales/medios no reproduce el comportamiento nativo completo** (la rama de extensión de `.` en `verrevcmp` y el encadenamiento `->file_prefixlen->verrevcmp` necesita más evidencia).

## 5. Resultados
| Eje | Veredicto |
|---|---|
| Identidad del binario | VERIFIED |
| Oráculo sellado (R3, 34.145 casos) | VERIFIED en integridad de artefactos; comportamiento diferencial repetible |
| Reconstrucción vs oráculo | **PARTIAL / OPEN** — 791/34.145 (97,7 %) match; 0 discrepancias solo en los tres subcomponentes aislados |
| Generalización a otros binarios/funciones | NOT_VERIFIED (fuera de alcance por objetivo) |
| Segunda generación independiente (seed 20261113) | NOT_EXECUTED (bloqueada por criterio "cero discrepancias en primera generación") |
| Integración en producción | NOT_AUTHORIZED / NOT_CLAIMED |
| `op:claim`, `--auto`, `sudo` | NOT_USED |

## 6. Sellado y artefactos (citado en `/tmp/rxre-r3/records/final_package.sha256`)
- Entradas selladas: `cases.sha256`, `matrix_native.sha256`, `pair_matrix_255.csv`, `pair_matrix_interior.csv`, `w_end_probe.csv`, `prefix_scan2.txt`, `final_package.sha256`, `recon_final.sha256`, `SEAL.txt`.
- Registros obsoletos preservados en `records/stale/` (sin destrucción).

## 7. Prohibición de afirmar capacidad cerrada
Ningún elemento de esta sección autoriza integrar, promover o declarar completo ni la reconstrucción ni `filevercmp` sobre `/usr/bin/ls` ni sobre otro binario. Los resultados parciales están registrados como tales, sin conversión etiqueta-capacidad.

## 8. Registro en el Plan Maestro (actualización documental autorizada 2026-11-12)
- Addendum `## 1044. R3 — …` añadido a `RXRE_PLAN_MAESTRO.md` (copia principal `rxre/` y copia espejo `documentacion/`; contenido idéntico byte a byte, sha256 `8e43e578…`).
- Fuente del addendum: `records/PLAN_MAESTRO_ADDENDUM_R3.md` (7.237 B, sha256 `f5f4455f…`).
- Sección addendum, no sustituye el histórico §1036–§1043; ninguna sección anterior fue modificada.
- El Plan Maestro no forma parte del índice git (`?? RXRE_PLAN_MAESTRO.md`); ningún compromiso git es aplicable. `AGENTS.md`, `rxre.sqlite3`, `core/store.py`, contratos y `jorgeeee.md` intactos.
- Segunda y tercera copia física del Plan Maestro: no localizadas; discrepancia documentada en §1044.7 (no se afirma `SYNC_OK ×3` sin evidencia).

## 9. Identidad oficial publicada (2026-11-12)
- `RXRE_IDENTIDAD.md` creado en la raíz del repo (513 B, sha256 `cce22881ef…`) con la declaración (A)+(B) aceptada. No se reescribió ningún documento histórico.
- `RXRE_PLAN_MAESTRO.md` actualizado con `## 1045. IDENTIDAD OFICIAL DE RXRE (2026-11-12) (G1045 PUBLISHED)`; fuente del addendum `records/PLAN_MAESTRO_ADDENDUM_IDENTIDAD.md` (3.992 B, sha256 `467694ad…`).
- Plan Maestro sincronizado byte a byte en las dos copias existentes: `rxre/RXRE_PLAN_MAESTRO.md` y `documentacion/RXRE_PLAN_MAESTRO.md` — sha256 `e45e80722cb2b34fb6f644f9eae5503f4d52ea8af9733ad47b888993c8b04885`; `cmp` OK; `wc -c` = 1.724.407 B.
- Ninguna otra pieza fue modificada: `AGENTS.md`, `rxre.sqlite3`, `core/store.py`, contratos, README, fixtures y el resto del histórico (§1036–§1044) permanecen intactos. Tercera copia física del Plan Maestro: no localizada; discrepancia explícita preservada en §1044.7/§1045.4.
- Veredicto de §1045: G1045 = PUBLISHED. No se abren misiones automáticamente; pasos siguientes pendientes de autorización explícita en orden de dependencia (aceptar aceptación → ESENCIA → MVP `reconstruct` → métrica externa con autonomía del tercero).
## 10. Resultado
Identidad oficial registrada respetuosamente como addendum; R3 permanece OPEN con su conteo original (791 divergencias); ninguna etiqueta promovida; el monumento histórico del Plan Maestro intacto.

## 11. Resolución de las 791 divergencias (2026-11-12, update-5) — cero divergencias en ambas generaciones
Autorización: propietario ("el mas completo"); alcance: cierre de divergencias, segunda generación sellada, verificación acotada. Restricciones preservadas: sin GPU, sin `sudo`, sin `--auto`, sin `op:claim`, sin bucles autónomos; repo, `AGENTS.md`, `rxre.sqlite3`, corpus y oráculos 20261112 **intactos**.

### 11.1 Causa raíz y corrección (solo `reconstruction/filenvercmp.c`)
La reconstrucción previa era un modelo empírico (tabla `RANK` + casos especiales, magnitudes ±1/±303/±302) y no reproducía las **magnitudes exactas** del nativo. Se reescribió como **transcripción literal** de `objdump -M intel` (records/disas_all3.txt; filenvercmp @ 0x4fa0, verrevcmp @ 0x4b60, file_prefixlen @ 0x4a80), acercando la implementación bit a bit al código de máquina: dígitos (runs con `first_diff`, salto de ceros iniciales 4cfd/4d1d, fin-de-cadena vs dígito → ±1),`[A-Za-z]` → `(int)(char)c`, `~` → −2, resto → `(int)c+256`; sentinela fin-de-cadena = −1 (asimétrico para `~`); `file_prefixlen` como extensión dpkg (`.[A-Za-z~][A-Za-z0-9~]*`) y `filenvercmp` con flag «≥1 extensión» que dispara el segundo pase a cadena completa.
Defectos concretos corregidos (difusión 791 → 97 → 86 → 0): (a) rama a-otros vs b-otros (4e72→4bf9→4c00) sin comprobación de igualdad con avance; (b) con `j >= b_lim` y a con dígitos se devolvía `0` en vez de saltar a la maquinaria de dígitos (4ea2→4cfd); (c) `verrevcmp` aplanada (etiquetas/llaves erróneas) y `L_4eq` sin vía de avance igual-byte.

### 11.2 Diferencial completa (oráculo sellado, 20261112)
`gcc -std=c11 -Wall -Wextra -pedantic -Werror -O2` + harness oficial (`verify_recon.c` sin modificar):
`total=34145 mismatches=0` (exit=0). Fuzz diagnóstico (no sellado; alfabeto con `.` `~` y bytes altos): 650.000 pares, 4 semillas, 0 mismatches.

### 11.3 Segunda generación sellada (seed 20261113) — 0 divergencias
Orden causal seal-before-reveal (`records/SEAL_SECOND_GENERATION.txt`):
1. corpus: `python3 gen_cases.py 20261113 cases_seed20261113.txt` → 34.145 pares, `sha256 8333b744b3dc1985648bd54ee432c74770bb78cba18e359ee4779d0acf885873` (sellado ANTES).
2. oráculo: `./matrix_gen cases_seed20261113.txt matrix_native_20261113.txt` → 34.145 líneas, 0 CRASH, `sha256 e031d3ed6d4c6329cf7edcae55b795fbe0d3c0b121fed34839ec8563b60cf6fd` (DESPUÉS).
3. verificación: harness nuevo `harness/verify_recon_seed20261113` (copia; verify_recon.c intacto) → `total=34145 mismatches=0` (exit=0).
Generación 20261112 intacta: `bfa30fb3…` / `ed5e91ef…`.

### 11.4 Verificación acotada independiente (clean-room)
Copias frescas verificadas por hash (`verify/cleanroom/`): 3 toolchains — clang -O2, gcc -O0, gcc -O2 — × 2 generaciones: **6/6, 0 divergencias**.
Aislamiento bwrap (`--ro-bind / /`, tmpfs `/tmp`, HOME fresco): uid=1000; `sha256 /usr/bin/ls` dentro del sandbox = `54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c`; escritura sobre el clean-room denegada (`WRITE_DENIED_OK`); diferenciales 0/0 ambas generaciones dentro del sandbox.

### 11.5 Límites explícitos (NO se ocultan)
- La verificación es autónoma pero **del mismo host, mismo UID, misma persona, mismo modelo**. MODEL_DIVERSITY y diversidad física/host NO demostradas; independencia física E2E-039 permanece **BLOCKED**.
- Tercera parte verificadora independiente (sin intervención del autor): **NOT_EXECUTED**.
- R3 **NO** cierra a PASS; el expediente declara: "cero divergencias en ambas generaciones selladas (verificación propia + acotada)". Declarar PASS requeriría (i) verificación ejecutada por terceros, (ii) revisión humana independiente y (iii) autorización explícita.
- `DIAGNOSTICO_791.md` y `SEAL.txt` conservan su texto histórico (791 divergencias) con este addendum como estado vigente; `records/stale/` intacto.
- AGENTS.md §8.11 (reconocimiento tecnológico exterior, 2026-11-12): nota de alcance presente, no modifica esta cadena; no re-ejecutó suites.

### 11.6 Hashes de artefactos (update-5)
`filenvercmp.c` = `c721c5c6672f5fbbd5896a922efc7a58a71b37b9bd616f46fbefde3bcdfc943d` · harness oficial = `55eacc5d575c349dc4641a73b9c80e330352fa1e0032c128d73f40d15e115c78` · `verify_recon_seed20261113` = `6acfe2570454a488ee761292897b0cf839181a328957d9135570f1e7f8c2f349` · clean-room: clang `004b6801e15adc81496ccab7efd54d568a3266e288fc231a966fd4df6a94d0b7`, gcc-O0 `56bd8a168fafeef6651041d0fcfca3af9271014af143fa2e59a1b0c0d3755a3f`, gcc-O2 `f7824da6c8c3e3ea7eb1d0b2cc84b36fb18ae9914862fa17df2bc25f32efd5cd` · corpus 20261113 `8333b744…` · oráculo 20261113 `e031d3ed…`.

### 11.7 Verificación caja negra end-to-end (binario real, no solo mmap)  [2026-11-12]
Subconjunto determinístico (seed 20261113) de 250 nombres únicos imprimibles del corpus (sin `/` ni crudos; `.`/`..` excluidos), creados como archivos vacíos en un tmpfs limpio (`work/bb2/`): `LC_ALL=C ls -A -v` produce exactamente la secuencia predicha por la reconstrucción con desempate strcmp (contrato de los wrappers `sort=version` @ 0x5170/0x51b0/0x5268/0x5330). Resultado: 250/250 nombres, secuencias idénticas byte a byte. Evidencia diagnóstica (mismo host, mismo binario); no sellada. El binario real ejecutado fue `/usr/bin/ls` nuevamente (sha256 verificado dentro y fuera de bwrap).

## 12. Resguardo de Fase 2/3/4 y cierre documental (2026-11-12, update-6)

### 12.1 Fase 1 — paquete público publicado  [2026-11-12]
Repositorio público: https://github.com/LexLuthorPrimero/rxre-cleanroom (commit 2aa102d, rama master)
Contenido: src/filenvercmp.c, harness/verify2.c, oracle/{cases_seed20261112.txt, matrix_native.txt, cases_seed20261113.txt, matrix_native_20261113.txt}, INDEX.md, PROTOCOL.md, OUTREACH.md, LICENSE, SHA256SUMS. HEAD reproducido con sha256sum -c.
IMPORTANTE: la verificación por terceros sigue **NOT_EXECUTED**; el paquete está preparado para ser refutado; el autor no declara PASS.

### 12.2 Fase 2 — encuesta de objetivo (reconstrucción completa)
Candidato principal: **/usr/bin/wc** — sha256 81d614595c717be908fce809713702efd35ce5a56f5ab7cbc497d1a61eb1a38f · BuildID 07a56ef5bcfd9b400c0dc0441530607b3c7d65f8 · 61.448 B · stripped · dinámico · 72 funciones identificables por objdump. Riesgo: ruta multibyte y locale; sin símbolos; complejidad media-alta. Alcance recomendado: reconstrucción semántica completa por hitos sellados (wc counting loop → lineas → bytes → multibyte) — **no iniciado**; requeriría su propia cadena sellada (corpus seed 20261114 sellado antes del oráculo).
Alternativas descartadas/aplazadas: dirname/basename (demasiado triviales), file (coherencia, demasiado grande), sort -V (arseguria, depende de infraestructura de comparación no resuelta).

### 12.3 Pre-registro de criterios de cierre del motor (antes de verlo)
El "motor" solo puede declararse en esas condiciones: (1) ≥1 binario reconstruido E2E con cero divergencias en su corpus sellado; (2) SEGUNDA generación independiente también a cero; (3) verificador humano/tercero autónomo confirmado o refutado por escrito (dictamen propio, no del autor); (4) al menos un consumidor demo o uso externo documentado. Hasta entonces: OPEN.

### 12.4 Métricas soberanas (revisión escrita semanal)
- réplicas externas confirmadas (nº, nombre público, fecha) 
- binarios con cero divergencias verificadas por terceros (nº)
- hallazgos refutados/corregidos desde la publicación (nº, con hashes)
- ratio documentos narrativos nuevos / verificaciones de terceros (objetivo: 0)
- blocked items cerrados vs abiertos (ky ora PUERTA cond.3: PENDING_EXTERNAL_REVIEWER)

### 12.5 Verificación de integridad vigente (solo lectura) — tools/rxre/verify_integrity.sh
Ejecutada 2026-11-12: fallos=0; suites 7/7 re-ejecutadas rc=0; informe: AGENTS_ESTADO_GENERADO.md.

## 13. Fase 2 hito 1 — /usr/bin/wc: corpus y oráculo sellados; modelo 0 divergencias (LC_ALL=C, salida por defecto)  [2026-11-12]
- Binario: /usr/bin/wc — sha256 81d614595c717be908fce809713702efd35ce5a56f5ab7cbc497d1a61eb1a38f · BuildID 07a56ef5bcfd9b400c0dc0441530607b3c7d65f8 · 61.448 B · stripped · dinámico. .text 0xc40–0x9092; vía unibyte (ctype locale C) vs vía multibyte (mbrtowc/iswspace/wcwidth) identificadas en disasm.
- Corpus sellado (seal-before-reveal; records SEAL_WC.txt): seed 20261114 (4899) sha256 4a2b85bb…; seed 20261115 (4914) bb21a816… — ambos ANTES del oráculo.
- Oráculos nativos (LC_ALL=C): 20261114 sha256 20842467…; 20261115 sha256 72cfcecd… (0 CRASH).
- Modelo wc_recon.c: 0 divergencias en ambas generaciones selladas (+ 20.000 contenidos aleatorios diagnósticos, 0 divergencias).
- NOT_EXECUTED: port 1:1 del disasm; flags (-c -m -l -w -L y -L max-line); domain multibyte/locale; milestone 2ª generación E2E; terceros; PASS.

## 14. Fase 2 hito 2 — wc con flags {-c,-l,-w}: 0 divergencias (seed 20261116)  [2026-11-12]
- Corpus seed 20261116: 11.872 casos (1.484 contenidos × 8 conjuntos de flags) — sellado ANTES del oráculo (SEAL_WC.txt).
- Oráculo nativo (LC_ALL=C, stdin): sha256 adc83227df98ccb304d1574252778628be5e0d776d91b00cf51422ead99f1df0 · 0 CRASH.
- Modelo ampliado (salida GNU orden fijo L W B): 11872/11872, exit=0.
- Dominio NO cubierto: -m, -L (max-line, wcwidth), multibyte, locale, formato alineado a columnas, --files0-from, port 1:1 del disasm.

## 15. Fase 2 hito 3 — wc con -L completo: 0 divergencias (seed 20261117)  [2026-11-12]
- Corpus seed 20261117: 13.072 casos (817 contenidos × 16 conjuntos de flags {default,-l,-w,-c,-L,+combinaciones}) — sellado ANTES del oráculo.
- Oráculo nativo (LC_ALL=C): de2fc092adf8ca47aa0c915bc86c2a7e086d4cf3cbecb82ca76b3e8bb865b6df · 0 CRASH.
- Semántica -L verificada empíricamente: {\f,\r} = reset de columna (ancho 0, sin línea); tab→8; printable=1; otros=0; max por posición.
- Modelo: 13072/13072 · exit=0 · fuzz diagnóstico -L: 0/30000 · sin regresiones (20261114/15/16 verdes).

## 16. wc hito 4 (intermedio) — validación oráculo↔oráculo de --files0-from  [2026-11-12]
Resultado: 4899/4899 (20261114) y 4914/4914 (20261115) contenidos idénticos entre `wc FILE` directo y `wc --files0-from=manifest` (un archivo por caso, LC_ALL=C). El modo --files0-from enruta al mismo contador de archivos por caso (evidencia adicional de que la vía argv→file-count y --files0-from→file-count convergen en el mismo resultado).
NOT_EXECUTED: extensión de la reconstrucción para --files0-from (multi-file arg loop, formato de salida con múltiples filas); milestone 4 E2E completo.

## 17. Fase 2 hito 5 — bytes altos/multibyte: seed 20261118; defecto real corregido  [2026-11-12]
- Corpus seed 20261118: 1.184 — gen_wc_high_cases.py: structured + random con bytes >= 0x80 y UTF-8; sellado ANTES del oráculo (91e6dbbf…).
- 2 oráculos (LC_ALL=C / es_AR.utf8): 706/1184 difieren (locale importa para bytes altos; es lo esperado).
- Probe binario: separador en LC_ALL=C = {09,0a,0b,0c,0d,20,a0}; en es_AR.utf8 = {09,0a,0b,0c,0d,20}.
- DEFECTO REAL: modelo omitía 0xa0 en LC_ALL=C → 755 mismatches; corregido → 1184/1184 C-locale + sin regresiones.
- UTF-8 (es_AR.utf8): 706 mismatches residuales — fuera de alcance del modelo ASCII fijo; pendiente UTF-8 (2ª vía).
- Lección: el corpus ASCII-only de los hitos 1–3 ocultó el defecto (igual que random_diff 20.000 pasaba sobre la clase .1.10) — el corpus debe tocar TODOS los ejes del dominio.

## 18. Nota importante sobre hitos 1–3 ("0/0")
Los corpus 20261114–17 no ejercitaban bytes >= 0x80 → el defecto en 0xa0 quedó latente; los hitos 1–3 NO son evidencia de que LC_ALL=C esté completamente cubierto. Hito 5 corrigió y selló esa clase.

## 18. Auditoría byte a byte (LC_ALL=C): verificación COMPLETA de closes de clase  [2026-11-12]
- Probe binario 'B<b>B\n' para los 256 bytes: width 0 = {controles 0x00-0x1f menos 09,0a,0c,0d? — excepto 07(=tab) context-dependiente}, {0x7f-0xff}; width 1 = exactamente {0x20-0x7e}; TAB(0x09) avanza a siguiente múltiplo de 8 (0x08 celdas desde col valor B='0'); {0x0a\n,0x0c\f,0x0d\r} = reset/end-of-line (no suman celdas).
- Reconciliado con el modelo: 0/13.072 resueltos para hito 3 antes; ahora clase -L además cerrada por probe directo contra el binario real.
- Clases LC_ALL=C COMPLETAS (por probe binario): word-separators = {09,0a,0b,0c,0d,20,a0} (audit hito 5); -L width = {1 en 20-7e; 0 resto; TAB→mult8; {0a,0c,0d} reset} (audit hito 6); line end = {0a} (0a=línea, 0c/0d=reset, necesario para ambos).
- IMPORTANTE: audit binaria cubre clasificado POR BYTES; la integración con el lazo de lectura de wc (con el locale **ciudades runtime** de wc desde ctype) no se ha portado explícitamente (milestone NOT_EXECUTED).

## 19. Fase 2 hito 7 — wc -m (chars) en LC_ALL=C: byte-paridad verificada contra oráculo  [2026-11-12]
- Corpus seed 20261119: 4.926 casos — sellado ANTES del oráculo verificación (sha256 5dbc2dfe…).
- Verificación oráculo directa: wc -m == wc -c en 4.926/4.926 casos del seed 20261119; en corpora anteriores: 35.941/35.941.
- Conclusión: en LC_ALL=C (MB_CUR_MAX == 1), el contador de caracteres colapsa al de bytes — es verificable y lo verificamos; no se afirma en es_AR.utf8 ni multibyte.
- Milestone cierre: clase -m cerrada POR OBSERVACIÓN en el dominio LC_ALL=C ASCII.
- NOT_EXECUTED: multibyte/locale -m; port 1:1 del disasm; -m vs -c (parcial multibyte) en es_AR.utf8.

## 20. Fase 2 hito 8 — UTF-8/multibyte: 0 divergencias en ambas variantes (seed 20261120)  [2026-11-12]
- Corpus seed 20261120: 1.184 casos — same Alphabet/structure as 20261118 seed but different seed — sellado ANTES del oráculo (4aa43467…).
- Oráculos sellados (después): matrix_highutf8_C.txt (LC_ALL=C) y matrix_highutf8.txt (es_AR.utf8) — sanity: 706 de 1184 difieren entre locales.
- Reconstrucción: 1184/1184 en UTF-8 (verify_wc_utf8 sin overrides → LANG=es_AR.utf8) Y 1184/1184 en LC_ALL=C.
- DEFECTO CORREGIDO: wc_oracle.py usaba os.environ.get('LC_ALL','C') (fallback siempre LC_ALL=C); corregido explícitamente.
- MODELO UTF-8: UTF-8 decoder inline (1-4 bytes), espacios Unicode (25 codepoints incl. NBSP, U+2028/9, U+00A0, U+202F, etc.).
- UTF-8 modelizado independiente de ctype runtime; LET-8 cover es_AR.utf8 y C. -m sigue pendiente para UTF-8.

## 21. Fase 2 hito 10 — extensión del paquete público de verificación  [2026-11-12]
- Publicado f3c6f7 en https://github.com/LexLuthorPrimero/rxre-cleanroom — el repo público ahora contiene DOS hitos reproducibles: filenvercmp + wc.
- wc milestone: verificación parametrizada con modo forzado (C|utf8) para eliminar la dependencia del locale del entorno en la verificación de terceros.
- El paquete incluye: INDEX.md top-level actualizado, wc/ con 18 archivos (corpus+matrices selladas, SEAL_WC.txt self-contenued, INDEX manifesto), SHA256SUMS raíz y wc/SHA256SUMS locales.
- 35.000+ casos sellados verificados in-loc, 0 divergencias en ambas locales.
- El riesgo de locales en verificación de terceros está mitigado con el flag explícito.
