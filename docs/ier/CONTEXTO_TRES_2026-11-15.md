# CONTEXTO — «tres» (2026-11-15)

Estado: **CONTEXTO — NO EVIDENCIA**. No eleva ningún estado de RXRE ni autoriza nada.

## Qué es «tres»

`/home/lucas/Escritorio/documentacion/tres/` (62 ficheros, ~6.99 MB) es una copia parcial del pendrive del propietario con la foto histórica de RXRE pre-pivote a IER (oct→nov 2026). Es **anterior** al enfoque IER y al commit de identidad `a0547eb0` (2026-11-15); jamás publicarlo ni promocionarlo como estado actual.

Contenido principal:

- Saga M1266 / ÉTER-WAL: `critica1.md…critica34.md`, `jorgeeee.md` (2.57 MB, contiene además la transcripción de una sesión con la contraseña de sudo en claro — **credencial expuesta; tratar como tal; rotar si se reutiliza**).
- Planes y volúmenes: `RXRE_PLAN_MAESTRO*.md`, `INFORME TÉCNICO INTEGRAL.md`, `rxre-volumen-1…6`, `PLAN_*.md`.
- Crítica estratégica externa: `Crítica al proyecto RXRE.md` (una primera parte crítica/poderosa + ~28.000 líneas de transcripciones con la misma contraseña expuesta).
- `ves` (corrección «10 módulos reales ≠ 27 tecnologías») — contenido valioso como crítica, obsoleto en cifras.

## Qué NO es

- No es evidencia de capacidad actual de RXRE.
- No es autorización de misiones (M1266 `BLOCKED_FOR_EXECUTION`; M1267 desautorizada).
- No es validación independiente (todo es auto-evaluación del mismo sistema; terceros siguen `NOT_EXECUTED`).
- No sustituye a `RXRE_IER.md`, `AGENTS.md` §4, ni al clon público verificado actual (`RXRE_CHANGELOG.md` 2026-11-15).

## Disposición (dictated por el propietario)

- `documentacion/tres/` permanece **intacta**; no se borró, movió ni copió.
- 12 huérfanos byte-idénticos se movieron a `/home/lucas/Escritorio/rxre-archive-2026-11-15/` (fuera del repo) junto con `MANIFEST_SHA256.txt` (62 + 12 verifican) y `LEEME_ARCHIVO.md` (no-publicación, datos sensibles).
- Los ficheros con contraseña (`jorgeeee.md`, `Crítica al proyecto…`) no se incluirán jamás en un clon, zip ni publish.
- Requisitos mínimos de cualquier reutilización futura: dictado del propietario + verificación contra el árbol público + no citar cifras sin cotejar + no declarar `PROVEN`/`PASS` desde estos documentos.

## Lo único que IER extrae de este corpus

`fallas_rxre_8_principios.md` → reescrito en `docs/ier/BACKLOG_IER_CLI.md` como backlog IER. Al 2026-11-15, todas sus «pruebas pendientes» resultaron, al verificarse en el árbol, obsoletas salvo dos — y una de ellas (IER-001, misiones duplicadas en `op:discover`) ya está resuelta con test. Lo demás requiere verificación por misión antes de actuar.
