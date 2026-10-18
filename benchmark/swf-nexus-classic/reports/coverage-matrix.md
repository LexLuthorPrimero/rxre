# Matriz de Cobertura — Evidencia → Módulo → Test

Mapeo de claims recuperadas a los módulos de la implementación C
y a los tests que las cubren.

**Leyenda de estados:**
- `RECUPERADO` = nombre/estructura extraído del vocabulario AVM1.
- `MODELO` = flujo derivado de descripciones recuperadas (no semántica exacta).
- `OBSERVED` = valor numérico extraído del bytecode (RXRE-SWF-015 PARTIAL); mapeo a mecánica NO determinada.
- `NOT_RECOVERED` = valor numérico no recuperado (RXRE-SWF-015).

| Claim | Qué se recuperó | Módulo C | Test | Estado |
|---|---|---|---|---|
| RXRE-SWF-003 | AS2/AVM1, no AS3 | (no aplica: es metadata del contenedor) | — | RECUPERADO |
| RXRE-SWF-006 | 26 clases `Madness*` | (vocabulario en `raw/avm1-vocab.json`) | — | RECUPERADO |
| RXRE-SWF-007 | 4 etiquetas de escena | `scene_t` en `rxre_swf.h` | — | RECUPERADO |
| RXRE-SWF-009 | TAC-BAR (concepto) | `tacbar_t`, evasión en `resolve_attack` | `TAC-BAR llena evita`, `TAC-BAR vacia conecta`, `bloqueo reduce agotamiento` | MODELO (fórmula no recuperada) |
| RXRE-SWF-009 | Clases de arma (7) | `weapon_class_t`, `weapon_class_name` | `nombres recuperados` | RECUPERADO |
| RXRE-SWF-009 | Clases de armadura (4) | `armor_class_t`, `armor_mitigation_pct` | `heavy mitiga más que light`, `melee ignora light/medium` | RECUPERADO (nombre) + MODELO (mitigación %) |
| RXRE-SWF-009 | Perks (11 nombres) | `perks_t` | `perk de desarme al bloqueo melee` | RECUPERADO (nombre) + NOT_RECOVERED (magnitud) |
| RXRE-SWF-009 | Combate (headshot, point-blank, dash, disarm, deflect) | `resolve_attack` | `headshot`, `dash puede aturdir`, `desarme` | RECUPERADO (nombre) + MODELO (flujo) + NOT_RECOVERED (valores) |
| RXRE-SWF-010 | Personajes (Sanford, Deimos, Hank, Christoff) | `character_id_t`, `character_name` | `nombres recuperados` | RECUPERADO |
| RXRE-SWF-011 | Misiones (5) | `mission_t`, `mission_name` | `nombres recuperados` | RECUPERADO |
| RXRE-SWF-019 | Regla de longitud de acción AVM1 | `tools/avm1_disasm.py` (no aplica a C) | — | PROBADO (parse 100% limpio) |
| RXRE-SWF-020 | Push = opcode 0x96 (no estándar) | `tools/avm1_disasm.py` | — | PROBADO |
| RXRE-SWF-021 | Tipo 9 Push = Const16 (2 bytes) | `tools/avm1_disasm.py` | — | PROBADO |
| RXRE-SWF-022 | Tipo 6 Push ≠ Double (float32+uint32) | `tools/avm1_disasm.py`; tablas en `rxre_swf_constants.c` | — | REFUTADO (como Double) / caracterizado |
| RXRE-SWF-015 | Constantes numéricas: VALORES | `rxre_swf_constants.c` (tablas OBSERVED: 43 mult float32, 43 pares, 260 enteros) | — | **OBSERVED** (valores) / mapeo NOT_DETERMINED |
| RXRE-SWF-015 | Constantes numéricas: ASIGNACIÓN a mecánica | tabla `rxre_recovered_properties[]` (32 propiedades) en `rxre_swf_constants.c` | `test_combat.c` (`propiedades recuperadas`) | **RECUPERADO** (mapeo propiedad<-multiplicador, RXRE-SWF-040); fórmula exacta NOT_DETERMINED |
| RXRE-SWF-012 | ConstantPool 0x88 = acción autónoma (formato estándar) | `tools/avm1_disasm.py walk_actions` | `test_disasm.py` | PROBADO (456 acciones) |
| RXRE-SWF-023 | Correlación pool→multiplicador (2 grupos) | `tools/avm1_disasm.py` | — | **REFUTADO** (RXRE-SWF-041): los float32 son multiplicadores de propiedad repartidos, no "daño en 2 grupos" |
| RXRE-SWF-024 | Acciones cortas 0x00-0x33 = AVM1 estándar | `tools/avm1_disasm.py` | `test_disasm.py` | PROBADO (frecuencias sensibles) |
| RXRE-SWF-025 | Constantes de combate NO en SetVariable (fluyen a llamadas) | `tools/avm1_trace.py` | — | **NEGATIVE_RESULT** (0 variables de combate) |
| RXRE-SWF-026 | `0x4E` = SetMember (object[key]=value) | `tools/avm1_trace.py` | — | **REFUTADO** (corregido por RXRE-SWF-028: `0x4E` es **GetMember**; el simulador anterior no tenía rama `else`) |
| RXRE-SWF-027 | Multiplicadores de combate NO en `0x4E` (fluyen a llamadas) | `tools/avm1_trace.py` | — | **CORREGIDO** (RXRE-SWF-040): la frontera NO estaba saturada; los multiplicadores fluyen a `SetMember(0x4F)` vía RMW `GetMember(0x4E)→Multiply`. Mapeo RESUELTO. |
| RXRE-SWF-014 | Validación diferencial | — | — | **NO REALIZADA** (sin runtime Flash) |
| RXRE-SWF-028 | `0x4E` = **GetMember** (LEER obj[clave], pop2/push1) | `tools/avm1_disasm.py` | `test_disasm.py` (count=24316) | **PROVEN** (balance de pila) |
| RXRE-SWF-029 | `0x4F` = **SetMember** (ESCRIBIR obj[clave]=valor, pop3) | `tools/avm1_disasm.py` | `test_disasm.py` (count=8359) | **PROVEN** (balance de pila) |
| RXRE-SWF-030 | ConstantPool(0x88): data[0:2]=u16 Count + strings | `tools/avm1_disasm.py` | `test_disasm.py` (count=456) | **PROVEN** (bytes crudos) |
| RXRE-SWF-031 | Resolución de propiedades (lookup/const16→pool[908]) | `tools/avm1_disasm.py` | `test_disasm.py` (pool=908) | **PROVEN** |
| RXRE-SWF-032 | Tipo-6 = float32(valor) + uint32(fracción 0.32, valor separado) | `tools/avm1_disasm.py` | `test_disasm.py` | **PARTIAL** (NO es Double; la parte "función determinista" REFUTADA por RXRE-SWF-047) |
| RXRE-SWF-033 | DefineFunction(0x9B)=289, DefineFunction2(0x8E)=1053 | `tools/avm1_disasm.py` | `test_disasm.py` (tick=196, createWound=8) | **PROVEN** |
| RXRE-SWF-034 | Mapeo propiedad<-multiplicador (SUPERSEDADO) | `tools/avm1_disasm.py` | — | **PROVEN** (con asociaciones falsas; ver 040) |
| RXRE-SWF-035 | `0x52` = CallMethod | `tools/avm1_disasm.py` | — | **HYPOTHESIS** (SUPPORTED) |
| RXRE-SWF-036 | `0x99`/`0x9D` = salto/branch | `tools/avm1_disasm.py` | — | **HYPOTHESIS** (SUPPORTED) |
| RXRE-SWF-037 | `0x87` = store-a-registro | `tools/avm1_disasm.py` | — | **HYPOTHESIS** (SUPPORTED) |
| RXRE-SWF-038 | `0x67` = comparación unaria | `tools/avm1_disasm.py` | — | **HYPOTHESIS** (SUPPORTED) |
| RXRE-SWF-039 | Opcodes desconocidos (0x3D/0x40/0x42/0x47/0x48/0x49/0x4C/0x50/0x51) | `tools/avm1_cfg.py` | `test_disasm.py` (CFG tests) | **PARCIAL** (RXRE-SWF-044): `0x40`=-1, `0x49`=-1, `0x3E`=-1, `0x42`=0 DETERMINADOS (CFG unanime); `0x3D`,`0x47`,`0x48`,`0x50`,`0x51` NOT_DETERMINED (discordantes/sin datos) |
| RXRE-SWF-040 | Mapeo propiedad<-multiplicador EXACTO (32 propiedades) | `tools/avm1_disasm.py`; `rxre_swf_constants.c` | `test_combat.c` (propiedades recuperadas); `test_disasm.py` | **PROVEN** (patrones STORE/RMW) |
| RXRE-SWF-041 | Asociaciones falsas del heuristico de proximidad | `tools/avm1_disasm.py` | — | **REFUTADO** (NEGATIVE_RESULT) |
| RXRE-SWF-042 | Decodificación de salto (0x99/0x9D) | `tools/avm1_cfg.py` | `test_disasm.py` (`cfg_jump_decode_pct`) | **PROVEN** (7053/7053 = 100% en límites de instrucción) |
| RXRE-SWF-043 | Método CFG (consenso por script) | `tools/avm1_cfg.py` | `test_disasm.py` (`cfg_validation_0x4e_pct`) | **SUPPORTED** (validado: 0x4E=-1 en 24/25) |
| RXRE-SWF-044 | Efectos netos determinados (CFG) | `tools/avm1_cfg.py` | `test_disasm.py` (`cfg_0x*_net`) | **SUPPORTED** (0x9D=-1, 0x40=-1, 0x49=-1, 0x3E=-1, 0x9F=-1, 0x42=0, 0x81=0, 0x8C=0) |
| RXRE-SWF-045 | 0x52 CallMethod / 0x87 StoreRegister dependen del valor | `tools/avm1_cfg.py` | `test_disasm.py` (`cfg_0x52_valuedep`) | **NOT_DETERMINED** (efecto depende de valores en pila) |
| RXRE-SWF-046 | 0x3D,0x43,0x47,0x50,0x53 discordantes; 0x48,0x51 sin datos | `tools/avm1_cfg.py` | — | **NOT_DETERMINED** |
| RXRE-SWF-047 | uint32 tipo-6 NO es función determinista del float32 (fórmula exacta 27/61; 9 pares sin inversa) | `tools/register_type6_refutation.py` | `test_disasm.py` (`type6_*`) | **PROVEN** (NEGATIVE_RESULT) |
| RXRE-SWF-048 | Cuerpos de DefineFunction/DefineFunction2 = tokens nativos de 2 bytes (NO acciones AVM1); firmas revelan modelo de datos | `tools/avm1_disasm.py` `decode_define_function(data,opcode)`; `tools/extract_signatures.py` | `test_disasm.py` (`fn_*`) | **PROVEN** (NEGATIVE_RESULT: 1342/1342 cuerpos=2B; 322 con opcode>=0x80 imposible en 2B; 306 sin End; 839 std) |
| RXRE-SWF-049 | Ejecutor simbolico recupera formulas del stream principal; 0x47=NIP; modSpeed=statDEX/45, modDmg=statSTR/15, etc. | `tools/avm1_sym.py`; `tools/extract_formulas.py` | `tools/register_formulas.py` | **PROVEN** (pool-resuelto + balance de pila; mitigacion de armadura NO recuperada — rutina nativa RXRE-SWF-048) |
| RXRE-SWF-050 | Aplicación de daño en el stream principal: `myAttackTarget.myHealth = myAttackTarget.myHealth - (myDataRef.myUnarmed.myDamage/4)` | `tools/avm1_sym.py`; `tools/register_damage.py` (traza bytecode) | `queries/damage-response.json` | **PROVEN** (traza bytecode + pool + balance neto 0; mitigación de armadura NO recuperada — rutina nativa) |
| RXRE-SWF-051 | Aleatorización del daño (`Math.floor(randomNumber(...)/4)`) y crítico de headshot gated por `perkHeadshotCrits` | `tools/trace_headshot.py`; `tools/trace_total.py`; `tools/register_damage2.py` | `queries/damage-rand-response.json` | **PARTIAL** (CORRIGIDO por RXRE-SWF-052: el rango del daño era erróneo; el crítico [1.20, 2.00] se confirma) |
| RXRE-SWF-052 | Convención de `SwainMath.randomNumber(precision, lo, hi)` → valor en `[lo, hi]` redondeado a `precision` decimales | `tools/register_swm.py` (escaneo de los 418 sitios de llamada) | `evidence/swfmath-rand.md`; `queries/swm-response.json` | **PROVEN** (418 llamadas, 179 firmas, 101 comparables, **0 violaciones** de `lo<=hi`; args empujados en orden INVERSO) |

## Cobertura por categoría

| Categoría | Recuperado | Implementado | Testeado | Denominador |
|---|---|---|---|---|
| Estructura SWF | 1 | — | — | 1 |
| Clases Madness | 26 | 0 (en vocabulario, no en C) | 0 | 26 |
| Escenas | 4 | 1 (enum) | 0 | 4 |
| Clases de arma | 7 | 7 | 1 | 7 |
| Clases de armadura | 4 | 4 | 2 | 4 |
| Personajes | 4 | 4 | 4 | 4 |
| Misiones | 5 | 5 | 2 | 5 |
| Tipos de enemigo | 3 | 3 | 2 | 3 |
| Perks | 11 | 11 (campos) | 1 | 11 |
| Mecánicas de combate | 8 | 8 | 9 | 8 |
| Constantes numéricas (valores) | OBSERVED (17033 Int, 5435 pares, 8873 Const16, 46125 Lookup, 2918 String) | tablas en `rxre_swf_constants.c` | 0 | todas (valores) |
| Constantes numéricas (mapeo a mecánica) | RECUPERADO (32 propiedades: myDamage, myArmor, myDash, myScale, mySpeed, volumeMusic, myHealth, myPrice, etc.) | `rxre_recovered_properties[]` | `test_combat.c` (6 checks de propiedades) | 32 propiedades |

**Nota:** las 26 clases Madness se recuperaron como vocabulario
(`raw/avm1-vocab.json`) pero **no** se reimplementan en C: su lógica
interna (máquinas de estado) está en el bytecode no desensamblado
(RXRE-SWF-015). La C implementa el subconjunto de mecánicas cuyos
*nombres* y *flujo* están recuperados, con los valores como PLACEHOLDER.
**Las fórmulas recuperadas del stream principal (RXRE-SWF-049/050) SÍ se
implementan en C** (`src/rxre_swf.c`): estadística→modificador
(`modDmg=statSTR/15`, etc.), aplicación de daño
(`target.health -= unarmed.damage/4`), movimiento
(`myAccel=mySpeed/4`), recoil (`weapon.damage*weapon.shots`),
`skillPoints=myLevel*3`, `respawn=max/2`, `targetHealthY=5*(health/max)`,
escalado de daño (`*3`, `/2`), durabilidad de arma (`-=2`). La
mitigación de armadura sigue PLACEHOLDER (rutina nativa, RXRE-SWF-048).

## Tests unitarios (83 checks)

1. TAC-BAR llena evita (luck<fullness)
2. TAC-BAR vacia siempre conecta
3. determinismo (mismo input, mismo output)
4. headshot inflige más que sin headshot
5. armadura heavy mitiga más que light
6. melee ignora armadura light y medium
7. bloqueo reduce agotamiento de TAC-BAR
8. perk de desarme al bloquear (melee)
9. dash puede aturdir
10. nombres recuperados (Sanford, Deimos, Hank, Christoff, G03LM_Mk1, zombie_agent, shotgun, heavy, Nexus Stronghold, Armory)
11. 32 propiedades recuperadas presentes
12. myDamage: 6 valores, max ~2.515625, STORE
13. myArmor: 6 valores, min 0, max ~2.578125
14. myDash: 3 valores, min ~1.90625
15. myHealth: max ~1031.525 (salud, no multiplicador)
16. mySpeedRight: tiene RMW y valor negativo
17. búsqueda de propiedad inexistente → NULL (sin crash)

**Fórmulas recuperadas (RXRE-SWF-049/050, PROVEN):**

18. modDmg = statSTR/15 (30/15=2.0)
19. modArmor = statEND/15 (30/15=2.0)
20. modSpeed = statDEX/45 (90/45=2.0)
21. modRecharge = statTAC/10 (40/10=4.0)
22. modAllySmart = statLEAD/15 (30/15=2.0)
23. modHurtTactics = statAWR/50 (100/50=2.0)
24. modDmg(NULL) = 0 (sin crash)
25. unarmed: 100 - 8/4 = 98
26. unarmed: 100 - 4/4 = 99
27. apply_damage: 100 - 10 = 90
28. apply_damage clamp a 0
29. unarmed clamp a 0
30. recoil = 2.0 * 6 = 12
31. skillPoints = 5*3 = 15
32. respawn = 100/2 = 50
33. targetHealthY = 5*(50/100) = 2.5
34. targetHealthY max=0 → 0
35. accel = 8/4 = 2.0
36. speedRight = (12-0)/6 = 2.0
37. damage_triple = 2*3 = 6
38. damage_halve = 8/2 = 4
39. gun_shot = 10-2 = 8
40. gun_shot clamp a 0

**Aleatorización y crítico de headshot (RXRE-SWF-051/052):**

41. damage TFD=20 random=20 → floor(5) = 5
42. damage TFD=20 random=0 → 0
43. damage random=-2 → floor(-0.5) = -1
44. damage TFD=21 → floor(5.25) = 5
45. crit mult 120 → 1.2 (120%)
46. crit mult 200 → 2.0 (200%)
47. crit mult 160 → 1.6 (160%)
48. crit aplica con perk
49. crit NO aplica sin perk
50. crit NO aplica en melee-especial (amSpecial && melee)
51. crit aplica en especial no-melee
52. pipeline: floor(40/4)×1.5 = 15
53. objetivo 50 − 15 = 35

**Resultado:** 83 checks, 0 failures (`make test` → rc=0).

## Test de regresión del desensamblador (67 checks, Python)

`tests/test_disasm.py` (`make test-disasm`): valida los conteos OBSERVED
y que las correcciones no-estándar permanezcan (Push=0x96,
tipo6=float32+uint32 no Double, tipo9=Const16, ConstantPool=0x88
autónoma), **más** la semántica recuperada esta sesión:
`0x4E`=GetMember, `0x4F`=SetMember, ConstantPool(0x88),
DefineFunction(0x9B/0x8E), resolución de propiedades (myDamage,
myArmor, myDash), hipótesis (0x52/0x99/0x9D/0x87/0x67),
**y los 12 tests del simulador de pila con CFG** (RXRE-SWF-042/043/044):
decodificación de salto (100%), validación 0x4E, efectos
determinados (0x9D/0x40/0x49/0x3E/0x9F/0x42/0x81/0x8C),
y opcodes dependientes del valor (0x52/0x87),
**y los 4 tests de la convención de
`SwainMath.randomNumber`** (RXRE-SWF-052):
>=400 sitios de llamada, >=100 firmas,
>=100 comparables, **0 violaciones** de `lo<=hi`
(probando el orden INVERSO de empuje de args),
**y los 7 tests de refutación del uint32 tipo-6** (RXRE-SWF-047):
61 pares distintos, fórmula exacta 27/61, 9 pares sin inversa,
**y los 11 tests de decodificación de función + token nativo**
(RXRE-SWF-048): createWound/tick con regCount+flags leídos,
params correctos (inNumber), DefineFunction(0x9B) sin regCount/flags,
cuerpos=2B (1342/1342), 322 tokens nativos (opcode>=0x80),
306 sin End, 839 acciones std, tick=0x44.

**Resultado:** 67 checks, 0 failures (§22 tool validation).

## Vertical slice jugable (`src/slice.c`, ncurses)

Demostración end-to-end de las mecánicas recuperadas.
**Separación arquitectónica:** simulación (`rxre_swf.c`,
testeable sin render) vs plataforma/input/render (`slice.c`).

| Componente | Estado | Claim |
|---|---|---|
| Combate (`resolve_attack`) | RECUPERADO | RXRE-SWF-009/010 |
| Salud máxima (1031) | OBSERVED | RXRE-SWF-040 (myHealth) |
| TAC-BAR (evasión) | RECUPERADO (flujo) | RXRE-SWF-009 |
| Headshot / stun / disarm | RECUPERADO (nombre+flujo) | RXRE-SWF-009 |
| Movimiento | APPROXIMATION | RXRE-SWF-039 |
| Colisión (rango) | APPROXIMATION | RXRE-SWF-039 |
| IA enemiga | APPROXIMATION | RXRE-SWF-039 |
| Renderizado | APPROXIMATION | RXRE-SWF-039 |
| Valores de dano | PLACEHOLDER | RXRE-SWF-015 |

**Verificación:** `make bin/slice` (rc=0, linka ncurses);
ejecutado en pty: arena renderizada (@/E), barras de HP,
combate disparado (dano/EVADIO/TAC-BAR), notas de
aproximación visibles.
