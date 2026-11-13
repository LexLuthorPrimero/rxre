
## 1044. R3 — CADENA E2E DE RECONSTRUCCIÓN SEMÁNTICA DE `filevercmp`/`filenvercmp` SOBRE `/usr/bin/ls` (G1044 EXECUTED) (2026-11-12)

Añadida el 2026-11-12 con autorización explícita de la Dirección (actualización documental). Preserva íntegramente el histórico §1036–§1043 (no se reescribe, no se sustituye, no se borra; esta sección es addendum). **No certifica** nada sobre `filevercmp`/`filenvercmp` como capacidad cerrada; no habilita producción ni generalización a otros binarios o funciones. Objetivo original de la misión: cadena operativa reproducible desde un binario real hasta una reconstrucción validada por oráculo independiente; criterio de cierre = cadena completa con cero discrepancias en el dominio declarado. Restricciones mantenidas: sin GPU física, `sudo`, `--auto`, `op:claim` ni bucles autónomos; sin modificar repo, Plan Maestro, `AGENTS.md`, bases protegidas, ni los contratos; sin ampliar el objetivo a otras funciones o binarios.

### 1044.1 Identidad del objetivo (sellada)
- `/usr/bin/ls` — sha256 `54e936d37decdad9ecaf189b1de347605a0a99037ec87bd17679b6cbde871a0c`; BuildID `ae6605eeca6cc2f19d18fdd53a521e501df3456d`; 153 400 B; ELF64 PIE stripped; `.text` vaddr `0x10c0`.
- Objetivo semántico identificado por localización y bytes (no por símbolo exportado): `filenvercmp` en `0x4fa0` (con `verrevcmp` en `0x4b60` y `file_prefixlen` en `0x4a80`). `.rodata` inspeccionado. Sin ejecuciones privilegiadas ni hardware especial.

### 1044.2 Método aplicado (heredado de §1026–§1029 y LXXXIX)
EVIDENCE → SEMANTICS → SCHEMA → DISCRIMINATING TEST → IMPLEMENTATION → VALIDATION con:
1. Identidad y secciones verificadas con `sha256sum`/`stat`/`readelf`/`objdump`.
2. Corpus propio y determinista: `oracle/gen_cases.py` (SEED=20261112; base×base + 6.000 aleatorios) → `cases_seed20261112.txt` (sha256 `bfa30fb358…`, 34.145 pares). Sin cajas históricas de `filevercmp` usadas como ground truth.
3. Oráculo independiente por mmap de `/usr/bin/ls`: `oracle/matrix_gen` (C, `-O2 -std=c11 -Wall -Wextra -Werror -pedantic`) → `matrix_native.txt` (sha256 `ed5e91ef…`, 34.145 líneas).
4. Reconstrucción fresca desde desensamblado y descubrimiento semántico por sondeo (sin copiar implementación histórica): `reconstruction/filenvercmp.c`. Compilada limpia con `-std=c11 -Wall -Wextra -pedantic -Werror`.
5. Diferencial completa sobre los 34.145 pares con `harness/verify_recon` (no se modifica la semántica del harness).

### 1044.3 Componentes verificados con evidencia positiva
| Componente | Método | Resultado |
|---|---|---|
| Comparador de byte único (posición 0 / 1..255) | `oracle/probe255` + `oracle/probe_interior` sobre el binario real; 32.385 pares por punto | **0 / 32.385** discrepancias. Modelo: `rc = RANK[a]−RANK[b]` con tres excepciones catalogadas (`.` líder, `.`×`0` = `-114` documentado, `~` = segundo mínimo) |
| `file_prefixlen` (0x4a80) | 7.320 cadenas estructuradas (`records/prefix_scan2.txt`) | **7.320 / 7.320** exacto; `out_len == strlen` en todos los casos; regla del «longest trailing letter/`~`-init segment» |
| `w_end_probe` (fin de lado para `la/lb`) | 255 sondas (1/byte) | **255 / 255** match con `w_of` (letras `c+1`; dígitos `{0}→0,{1..9}→1`; demás `c+257`; `~ → −1`) |
| Relación transitiva y antisimetría del orden de bytes (1..127) | 8.001 pares (`pair_matrix.csv`) | Cero violaciones de transitividad detectadas durante el ajuste afín |

### 1044.4 Diferencial vs oráculo nativo — résultat de esta publicación
`harness/verify_recon` sobre el corte actual de `reconstruction/filenvercmp.c`:
- **Total = 34.145 casos; coinciden = 33.354; divergen = 791 (97,7 % coincidencia). PASS = false.**
- Distribución de las 791 divergencias: 777 con al menos un `.` en posición interior (`dot-mid`) y 14 con `.` líder múltiple (`both-dot`).
- Las tres subfunciones validadas (ver 1044.3) **no componen** el comportamiento completo: el anidamiento `filenvercmp → file_prefixlen → verrevcmp` y las ramas de extensión `.` interior requieren evidencia adicional en la cadena de extensión; el mecanismo final de la clase `.` en cadena **no queda determinado** por los probes actuales.
- Discriminantes concretos reproducibles: `'a!b' vs 'a.'` (recon=1 / native=−13), `'R96]'9B' vs 'R.'` (recon=1 / native=−302), `'...' vs '.a'` (recon=−1 / native=205).

### 1044.5 Segunda generación
- **NOT_EXECUTED** (bloqueada por el criterio de cierre declarado: cero discrepancias en la primera generación). Seed 20261113 no generada; corpus independiente no producido; oráculo de segunda generación no ejecutado.

### 1044.6 Restricciones preservadas y non-actions
- Sin integración en producción; ninguna etiqueta promovida; `op:claim` no invocado; `--auto` no usado; GPU física no utilizada; sin modificaciones de repo aparte de este addendum autorizado; `AGENTS.md`, `rxre.sqlite3`, `core/store.py`, contratos protegidos y fixtures Ratificados: intactos (verificados con sha256 durante la sesión).
- Sin alteración de §1036–§1043; addendum, no sustitución.
- Sin discrepancias ocultas o excluidas post-hoc: el diferencial se ejecutó completo; los 34.145 casos cuentan en el descuento; las 791 divergencias quedan registradas íntegras en `/tmp/rxre-r3/records/mismatch_fresh.txt`, con intentos fallidos archivados en `records/stale/` (preservados, no destruidos).
- Sin cierre acotado todavía: no se aplica nombre de clase `PASS`/`PROVEN` a la capacidad global; la presente sección documenta un expediente abierto.

### 1044.7 Sellado y procedencia
- Sellos: `/tmp/rxre-r3/records/final_package.sha256`, `records/recon_final.sha256` (`f23362a3…`), `records/SEAL.txt` (actualizado 2026-11-12, sha256 `af5cb228…`), `EXPEDIENTE_R3.md` (sha256 `38eb42e8…`).
- Expediente reproducible: `/tmp/rxre-r3/EXPEDIENTE_R3.md`.
- Entradas selladas de referencia: `oracle/cases.sha256`, `oracle/matrix_native.sha256`, `oracle/pair_matrix_255.csv`, `oracle/pair_matrix_interior.csv`, `oracle/w_end_probe.csv`.
- No se usa `m835 --record`; registros redactados manualmente y validados con `python -m json.tool`/`sha256sum`, donde aplica.
- Bases intactas confirmadas: `rxre.sqlite3` `c24d58d6…` (270 336 B), `AGENTS.md` `25d57344…`, `jorgeeee.md` sin modificar. **Dos copias del Plan Maestro sincronizadas en esta publicación** (`rxre/RXRE_PLAN_MAESTRO.md` y `documentacion/RXRE_PLAN_MAESTRO.md`, contenido idéntico, `cmp` OK); tercera copia física no localizada en el árbol; se documenta como discrepancia explícita en vez de declarar `SYNC_OK ×3` sin evidencia.

### 1044.8 Veredicto y siguientes pasos
- **R3 = OPEN — NOT_PASS.** El criterio de cierre (cero discrepancias) no se alcanza en esta publicación.
- Pasos siguientes (no autorizados por esta sección): (1) completar la clasificación semántica de la rama de extensión `.` en `verrevcmp` con discriminantes mínimos/GDB; (2) recién entonces regenerar corpus y oráculo de segunda generación (seed 20261113) según la cadena R3 original; (3) sólo con cero discrepancias ambas generaciones, tabular el dictamen de cierre. Hasta entonces: ninguna capacidad, ninguna integración, ninguna generalización declarada.

