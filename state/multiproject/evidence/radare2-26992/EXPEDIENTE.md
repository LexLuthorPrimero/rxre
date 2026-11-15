# EXPEDIENTE — radareorg/radare2#26992 + PR #27453

## Alcance
- Bug: `aea` emula una única condición ESIL (típicamente con zf=0 en brazo claro) y reporta solo accesos del camino tomado. Para condicionales ARM (moveq/movne/bxeq ...) los accesos del camino alternativo quedan invisibles.
- Fix (`fix/arm-aea-conditional-union @ d1af789`): en `cmd_aea_stuff`, cuando la arch es ARM/Thumb y el ESIL contiene `?{`, ejecutar el ESIL 16 veces (todas las combinaciones NZCV) y unir los conjuntos I/A/R/W/N con el mismo hook de ESIL. Rama `fix/arm-aea-conditional-union @ d1af789`. PR **#27453**.

## Reproducción y verificación
- r2 5.9.8 instalado reproducía I: zf únicamente; con build local (meson, ninja) del parche, casos del issue:
  - `wx 0100a001` (`moveq r0, r1`): ` I: zf r1  A: zf r1 r0  R: zf r1  W: r0  V: 0  N: zf r1`
  - `wx 1effa001` (`bxeq lr`):       ` I: zf pc lr  A: zf pc lr  R: zf pc lr  W: pc  V: 0  N: zf lr`
- Test upstream: `test/db/anal/arm-esil` — 2 casos nuevos (`arm aea reports both conditional paths of moveq`, `... of bxeq`). OK con r2 6.2.7 local.
- Casos preexistentes `malloc://` en el mismo archivo: 6 OK. Los que fallan (11 XX) son por falta de `bins/elf` en el host — preexistente, idéntico en master.

## Limitaciones explícitas
- Unión 16x solo para ARM/Thumb. VFP/VFP-d32 predicates fuera de NZCV no cubiertos (los condicionales ARM no las usan).
- IT blocks predicados en una sola cadena ESIL: 16x ESIL por instrucción; correcto, más lento.
- RXRE: sin capacidad nueva (el fix es de r2). El oráculo capstone NO se usó aquí (r2 prueba el mismo ESIL por sí sola; el motor es radare2).
- 1 host, 1 UID. TESTED_ONLY. PR pendiente de review; terceros NOT_EXECUTED.

## RXRE delta
- Sin capacidad nueva añadida; RXRE participó como registro/auditoría; motor real = r2 (paresálisis tipo REA: fuera de scope del engine).
