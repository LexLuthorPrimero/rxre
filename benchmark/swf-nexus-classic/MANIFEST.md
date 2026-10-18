# MANIFIESTO de entregables — benchmark/swf-nexus-classic

Benchmark: RXRE como instrumento de RE de IA sobre
`Madness Project Nexus Classic.swf`.

## Artefacto objetivo (inmutable)

- `raw/original.swf` — copia verbatim del original.
  SHA-256 `44584a02d85a883384bad34617eb800d79301a8daeabf20244f6b75755ff9342`.
  No modificado.

## raw/ — artefactos crudos

| Fichero | Contenido | Producer |
|---|---|---|
| `original.swf` | copia del SWF original (CWS) | cp |
| `uncompressed.swf` | forma FWS descomprimida (20,491,352 B) | `swfparse.py` |
| `swf-structure.json` | inventario de 9788 tags (code/name/length/offset) | `swfparse.py` |
| `extracted.json` | ExportAssets(520), FrameLabels(4), DefineEditText(136), DefineSound(137), vocab, XMP | `extract.py` |
| `avm1-vocab.json` | pools de constantes + vocabulario de 5137 identificadores de 75 scripts AVM1 | `avm1_strings.py` |
| `avm1-disasm.json` | resumen del desensamblado AVM1 (conteos de Push, histogramas) | `avm1_disasm.py` |
| `avm1-constants.json` | constantes AVM1 extraídas: 17033 Integer, 5435 pares float32+uint32, 8873 Const16, 46125 Lookup, 2918 String | `avm1_disasm.py` |

## tools/ — herramientas de extracción (research instruments)

| Fichero | Propósito |
|---|---|
| `swfparse.py` | parser estructural SWF (RECT corregido = 4 campos) |
| `extract.py` | extractor de símbolos/texto/sonido/vocabulario |
| `avm1_strings.py` | extractor de ConstantPool + vocabulario AVM1 |
| `avm1_disasm.py` | desensamblador AVM1 por regla de longitud (Push=0x96, tipo6=float32+uint32, tipo9=Const16) + **semántica recuperada esta sesión**: ConstantPool(0x88), GetMember(0x4E), SetMember(0x4F), DefineFunction(0x9B)/DefineFunction2(0x8E), resolución de propiedades, tabla de opcodes |
| `avm1_trace.py` | simulador de pila AVM1 (**OBSOLETO/FLAWED**: no tenía rama `else`, trataba todos los opcodes desconocidos como no-ops y **identificaba 0x4E como SetMember — es GetMember, RXRE-SWF-028**; sus trazas SetVariable/SetMember son poco fiables y fueron la causa de la falsa frontera "saturada") |
| `avm1_cfg.py` | **simulador de pila con CFG** (RXRE-SWF-042/043/044): construye el CFG (bloques básicos, 0x99=incondicional/0x9D=condicional), propaga la profundidad de pila como expresión lineal sobre los efectos desconocidos, y agrega el consenso unanime entre scripts consistentes. VALIDADO (0x4E=-1 en 24/25). Determina 0x9D=-1, 0x40=-1, 0x49=-1, 0x3E=-1, 0x9F=-1, 0x42=0, 0x81=0, 0x8C=0. Detecta opcodes dependientes del valor (0x52/0x87). |
| `register_cfg_claims.py` | registra los hallazgos CFG en RXRE vía `registrar_investigacion` (estados válidos) |
| `register_type6_refutation.py` | registra la refutación del uint32 tipo-6 (RXRE-SWF-047) en RXRE vía `registrar_investigacion` (PROVEN, NEGATIVE_RESULT) |
| `extract_signatures.py` | extrae las firmas de función (params/regCount/flags/body) de DefineFunction/DefineFunction2 y escribe `evidence/function-signatures.md` (RXRE-SWF-048) |
| `register_signatures.py` | registra el hallazgo de cuerpo=token nativo + firmas (RXRE-SWF-048) en RXRE vía `registrar_investigacion` (PROVEN, NEGATIVE_RESULT) |
| `update_registry.py` | actualiza `claims-registry.json`/`.md` (añade RXRE-SWF-048, corrige RXRE-SWF-033) |
| `avm1_sym.py` | **ejecutor simbólico lineal** (RXRE-SWF-049): pila de expresiones simbólicas + `expr_depth` para el marco de `CallMethod`; descubre `0x47`=NIP por balance de pila; registra escrituras `SetMember` con su expresión simbólica |
| `extract_formulas.py` | extrae las fórmulas recuperadas por el ejecutor simbólico, las categoriza (stats/armadura/daño/movimiento/salud/temporizadores) y escribe `evidence/symbolic-formulas.md` (RXRE-SWF-049) |
| `register_formulas.py` | registra el hallazgo del ejecutor simbólico + fórmulas (RXRE-SWF-049) en RXRE vía `registrar_investigacion` (PROVEN) |
| `register_damage.py` | registra la fórmula de aplicación de daño (RXRE-SWF-050) en RXRE vía `registrar_investigacion` (PROVEN); traza el bytecode y verifica el balance de pila |
| `trace_r16.py` / `trace_r3.py` / `trace_total.py` | trazas de la cadena de cómputo del daño (r16 = `Math.floor(randomNumber(...)/4)`, base `r3` = `totalFrameDamage`); premisa qué registro contiene la mitigación de armadura |
| `trace_headshot.py` | traza el multiplicador de crítico de headshot (`StoreRegister R18`) y la ruta de `headDamage` (gated por `perkHeadshotCrits`) |
| `register_damage2.py` | registra la aleatorización del daño y el crítico de headshot (RXRE-SWF-051, PARCIAL) vía `registrar_investigacion` |
| `register_swm.py` | escanea los **418 sitios** de `SwainMath.randomNumber` y registra la convención `(precision, lo, hi)` (RXRE-SWF-052, PROVEN) + la corrección del rango del daño |
| `swf_all_scripts.py` | recolector recursivo de DefineSprite (1680 DoAction anidados) |
| `register_claims.py` | registra las claims en RXRE vía `op:record` (**OBSOLETO**: usaba estados no válidos CORROBORATED/PROVEN_ABSENT que el store rechaza; las claims quedaban como OPEN) |

## evidence/ — registro de claims

- `claims-registry.json` — **52 claims** (RXRE-SWF-001…052) con taxonomía, estado, evidencia, ID de registro RXRE.
- `claims-registry.md` — tabla legible del mismo registro.
- `type6-uint32-analysis.md` — análisis completo de la refutación del uint32 tipo-6 (RXRE-SWF-047): inversión de fórmula sobre 61 pares, distribución M' vs lo20, conclusión (valor separado, no función del float32).
- `function-signatures.md` — firmas de función (RXRE-SWF-048): formato DefineFunction/DefineFunction2 PROBADO, cuerpo=token nativo de 2 bytes (1342/1342; 322 opcode>=0x80; 306 sin End; 839 std), modelo de datos (combate/stats/física).
- `symbolic-formulas.md` — fórmulas recuperadas por el ejecutor simbólico (RXRE-SWF-049): 0x47=NIP, stats→modificadores (modDmg=statSTR/15, modArmor=statEND/15, modSpeed=statDEX/45, modRecharge=statTAC/10, modAllySmart=statLEAD/15, modHurtTactics=statAWR/50), movimiento (myAccel=mySpeed/4), daño (myDamage*=3), armadura-fuente (myHeadArmor=myHat.myArmor, myBodyArmor=myShirt.myArmor), **aplicación de daño** (myAttackTarget.myHealth -= myUnarmed.myDamage/4, RXRE-SWF-050), recoilTimer=weapon.myDamage*weapon.myShots, skillPoints=myLevel*3. La mitigación de armadura NO se recupera (rutina nativa).
- `damage-response.json` — respuesta de registro de RXRE-SWF-050 (fórmula de aplicación de daño, traza bytecode).
- `damage-rand-response.json` — respuesta de registro de RXRE-SWF-051 (aleatorización del daño + crítico de headshot, PARCIAL/corregido).
- `swm-response.json` — respuesta de registro de RXRE-SWF-052 (convención de `SwainMath.randomNumber`, 418 sitios, 0 violaciones).
- `swfmath-rand.md` — convención `(precision, lo, hi)` de `SwainMath.randomNumber` + tabla de las 30 firmas más comunes + corrección del rango del daño.

## src/ — implementación nativa C99

| Fichero | Contenido |
|---|---|
| `rxre_swf.h` | tipos + API: armas, armaduras, TAC-BAR, perks, personajes, enemigos, escena, misión, **tabla de propiedades recuperadas** (`rxre_property_t`) |
| `rxre_swf.c` | núcleo de simulación `resolve_attack` (flujo: evasión→conexión→modificadores→mitigación→stun/knockdown/disarm/deflect) + `rxre_property_find` |
| `rxre_swf_constants.c` | tablas OBSERVED: 43 multiplicadores float32, 43 pares, 260 enteros, **32 propiedades recuperadas (RXRE-SWF-040)** |
| `main.c` | 9 escenarios deterministas |
| `slice.c` | **vertical slice jugable (ncurses)**: bucle principal, input, movimiento, colisión, un combate `resolve_attack`, salud/dano, IA enemiga, renderizado, reinicio. Simulación separada de renderizado. Mecánica de combate RECUPERADA; movimiento/IA/render APPROXIMATION (RXRE-SWF-039) |

## tests/ — validación

| Fichero | Contenido |
|---|---|
| `test_combat.c` | **83 checks** (29 lógica de combate + 18 tabla de propiedades + 23 fórmulas recuperadas RXRE-SWF-049/050 + 13 aleatorización/crítico RXRE-SWF-051/052) |
| `test_disasm.py` | **67 checks** (11 correcciones no-estándar + 20 semántica recuperada + 12 simulador CFG + 4 convención SwainMath.randomNumber (RXRE-SWF-052) + 7 refutación uint32 tipo-6 + 13 decodificación de función/token nativo) |

## Estado de la frontera semántica (esta sesión)

- **0x4E = GetMember** (PROVEN, RXRE-SWF-028), **0x4F = SetMember** (PROVEN, RXRE-SWF-029): por balance de pila.
- **ConstantPool(0x88)**: formato corregido (RXRE-SWF-030); pool principal = 908 entradas.
- **Mapeo propiedad←multiplicador** RESUELTO (RXRE-SWF-040): myDamage, myArmor, myDash, myScale, mySpeed, volumeMusic, myHealth, myPrice, etc.
- **Corregida** la falsa frontera "saturada" (RXRE-SWF-027) y las asociaciones falsas del heuristico de proximidad (RXRE-SWF-041).
- **Decodificación de salto** PROBADA (RXRE-SWF-042): 0x99=incondicional, 0x9D=condicional; destino = pos_offset + 2 + int16_signo (100%).
- **Simulador de pila con CFG** (RXRE-SWF-043/044): método validado (0x4E=-1 en 24/25); efectos determinados **0x9D=-1, 0x40=-1, 0x49=-1, 0x3E=-1, 0x9F=-1, 0x42=0, 0x81=0, 0x8C=0**.
- **uint32 tipo-6 NO es función del float32** (RXRE-SWF-047, PROVEN): fórmula `u=((b&0xFFFFF)*0x100001+128)>>8` exacta solo 27/61; 9 pares sin inversa. El uint32 es un valor separado (fracción 0.32 = peso/probabilidad).
- **Cuerpos de función = tokens nativos** (RXRE-SWF-048, PROVEN, NEGATIVE_RESULT): `decode_define_function` corregido (lee regCount+flags de DefineFunction2, maneja ausencia de regIdx en DefineFunction). Todo cuerpo = 2 bytes (1342/1342); 322 empiezan con opcode>=0x80 (imposible para acción larga en 2B); 306 sin End; 839 std. `tick()`=token 0x44. La fórmula exacta de combate NO está en los cuerpos. Las firmas revelan el modelo (combate/stats/física).
- **Ejecutor simbólico + fórmulas** (RXRE-SWF-049, PROVEN): `avm1_sym.py` (pila simbólica + `expr_depth` para marco de CallMethod). `0x47`=NIP (balance neto 0). Fórmulas pool-resueltas: modSpeed=statDEX/45, modDmg=statSTR/15, modRecharge=statTAC/10, modArmor=statEND/15, modAllySmart=statLEAD/15, modHurtTactics=statAWR/50, myAccel=mySpeed/4, myDamage*=3, myHeadArmor=myHat.myArmor, myBodyArmor=myShirt.myArmor, myPrice=myArmor*100. 8675 escrituras (599 aritméticas). La MITIGACIÓN de armadura NO se recupera (rutina nativa RXRE-SWF-048).
- **Aplicación de daño** (RXRE-SWF-050, PROVEN): `myAttackTarget.myHealth = myAttackTarget.myHealth - (myDataRef.myUnarmed.myDamage/4)`. Confirmada por traza de bytecode (script 1627, acc 31869-31884) + pool + balance neto 0. El objetivo pierde salud = daño desarmado/4. Recoil=weapon.myDamage*weapon.myShots; skillPoints=myLevel*3; myDataRef.myHealth=myHealthMax/2; myGun.myHealth-=2; targetHealthY=5*(myHealth/myHealthMax). La mitigación de armadura (cómo myArmor reduce el daño) NO se recupera (rutina nativa inDamage/inArmor).
- **Aleatorización del daño + crítico de headshot** (RXRE-SWF-051 → **PARTIAL**, corregido por 052): el daño se aleatoriza con `Math.floor(randomNumber(...)/4)`; el crítico está gated por `perkHeadshotCrits` (`havePerk(perkHeadshotCrits,2,MadnessDataFile)`) y multiplica por `r18 = randomNumber(2,120,200)/100 = [1.20, 2.00]`; `r18=1` para `amSpecial && myCat=="melee"`; perk `bulletEater` ramifica el cómputo. `totalFrameDamage = r3` (daño total del frame).
- **Convención de `SwainMath.randomNumber` (RXRE-SWF-052, PROVEN)**: `randomNumber(precision, lo, hi)` → valor en `[lo,hi]` redondeado a `precision` decimales. **418 sitios de llamada, 179 firmas, 101 comparables, 0 violaciones de `lo<=hi`.** Los args se empujan en orden INVERSO (AVM1), así que `Push[R3,-2,2,SwainMath]` declara `randomNumber(2,-2,R3)` → rango `[-2,R3]`. Fórmula corregida: `damage=Math.floor(randomNumber(2,-2,totalFrameDamage)/4)` → `[0, TFD/4]`.
- **Abierto**: 0x52 CallMethod y 0x87 StoreRegister dependen del valor (RXRE-SWF-045); 0x3D,0x43,0x47,0x50,0x53 discordantes y 0x48,0x51 sin datos (RXRE-SWF-046); significado de juego del uint32 tipo-6 y la fórmula exacta de propiedades (requiere runtime Flash, RXRE-SWF-014).

## queries/ — interacción con RXRE

- `record-responses.jsonl` — respuestas de `op:record` para cada claim (27/27 `ok`).

## src/ — reimplementación C (C99, `-Wall -Wextra -Werror`)

| Fichero | Capa | Contenido |
|---|---|---|
| `rxre_swf.h` | tipos/decls | tipos de arma, armadura, TAC-BAR, perks, personaje, enemigo, resultado de combate, escena, misión, decls de constantes OBSERVED |
| `rxre_swf.c` | simulación | `resolve_attack` (flujo de combate recuperado), nombres, init |
| `rxre_swf_constants.c` | datos OBSERVED | tablas de constantes AVM1 recuperadas (43 multiplicadores float32, 43 pares mult+frac, 260 enteros) — valores OBSERVED, mapeo NOT_DETERMINED |
| `main.c` | harness | 9 escenarios deterministas (inspección) |
| `slice.c` | plataforma/plataforma | vertical slice jugable (ncurses): input, movimiento, colisión, IA, renderizado, bucle; usa `resolve_attack` (combate RECUPERADO); movimiento/IA/render APPROXIMATION (RXRE-SWF-039) |

**Separación arquitectónica:** simulación testeable sin
renderizado/audio/plataforma. Sin dependencias externas.

## tests/

- `test_combat.c` — 29 checks unitarios (flujo, no balance).
- `test_disasm.py` — 67 checks de regresión del desensamblador AVM1 + simulador CFG + refutación uint32 tipo-6 + decodificación de función/token nativo (tool validation, §22).
- `avm1_sym.py` — ejecutor simbólico lineal (RXRE-SWF-049): recupera fórmulas del stream principal; 0x47=NIP; stats→modificadores, movimiento, daño, armadura-fuente.

## reports/

- `final-report.md` — informe final (descubrimientos, pruebas,
  desconocidos, RXRE, C, validación, siguiente paso).
- `coverage-matrix.md` — evidencia → módulo → test.
- `rxre-effectiveness.md` — evaluación de efectividad de RXRE
  como instrumento: cuello de botella por descubrimiento
  (AI_REASONING / RXRE_RETRIEVAL / PROVENANCE / TOOLING /
  RUNTIME_DEPENDENCY), brechas encontradas y cómo se repararon.

## Construcción y ejecución

```bash
cd benchmark/swf-nexus-classic
make all        # compila bin/rxre_swf_demo y bin/test_combat
make run        # ejecuta los 9 escenarios deterministas
make test       # 29 checks C, 0 failures
make test-disasm  # 50 checks Python (regresión desensamblador + CFG + refutación tipo-6)
make test-all   # test + test-disasm
make clean      # elimina bin/
```

Requisito: gcc (C99). Sin dependencias de red, GPU ni Flash.

## Limitaciones declaradas

1. **Sin validación diferencial** (RXRE-SWF-014): no hay runtime Flash.
2. **Constantes: valores OBSERVED, mapeo NOT_DETERMINED** (RXRE-SWF-015
   PARTIAL): las tablas en `rxre_swf_constants.c` son el pool de candidatos
   recuperados; la asignación a mecánicas requiere el flujo de control.
   Los valores que la simulación usa sin asignación llevan `PLACEHOLDER`.
3. **RXRE no ingiere binarios** (RXRE-SWF-013): extracción externa +
   registro vía `op:record`.
