# Informe Final — Benchmark: RXRE como instrumento de RE de IA

## Artefacto objetivo

`Madness Project Nexus Classic.swf`
(SHA-256 `44584a02d85a883384bad34617eb800d79301a8daeabf20244f6b75755ff9342`,
copia verbatim en `raw/original.swf`, sin modificar).

Sesión RXRE: `swf-nexus`. Rama activa del repo: `audit/register-fields-keying-016r`
(el trabajo del benchmark solo añadió ficheros bajo `benchmark/swf-nexus-classic/`).

---

## 1. Qué se descubrió

### 1.1 Estructura del contenedor SWF (PROBADO)

| Propiedad | Valor | Evidencia |
|---|---|---|
| Firma | `CWS` (zlib) | `raw/swf-structure.json` |
| Versión SWF | 10 | ídem |
| Longitud comprimida | 15,612,129 B | `sha256sum raw/original.swf` |
| SHA-256 (comprimido) | `44584a02…f9342` | ídem |
| Longitud descomprimida (FWS) | 20,491,352 B | `raw/uncompressed.swf` |
| SHA-256 (descomprimido) | `bb0a9475…2da1ef2` | ídem |
| RECT | `[0,17000, 0,10600]` twips → **850×530 px** | `swfparse.py` (RECT = 4 campos) |
| FrameRate | `00 1e` → 30 fps | ídem |
| FrameCount | 30 (== ShowFrame=30, consistencia) | ídem |

**Corrección de bug registrada:** el primer parser usaba `nbytes = (5 + 5*Nbits + 7)//8`
para el RECT. El RECT tiene **4** campos empaquetados (Xmin/Xmax/Ymin/Ymax), por lo que
`nbytes = (5 + 4*Nbits + 7)//8` = 9 B (Nbits=16). El error desplazaba el flujo de tags
2 bytes y corrompía todo el inventario. Corregido y verificado: el parse termina exactamente
en el tag `End(0)` al final del body.

### 1.2 Es AS2/AVM1, no AS3 (PROBADO)

`DoABC(82)=0`, `DoAction(12)=6`, `DoInitAction(59)=69`, `SymbolClass(77)=1`.
`FileAttributes` payload `10 00 00 00` = 0x10 (bit 4).

### 1.3 Inventario de tags (9788 tags, PROBADO)

DefineShape4 2387, DefineSprite 2448, DefineShape 2386, DefineShape3 241,
ExportAssets 520, DefineText 228, DefineEditText 136, DefineFontName 114,
DefineFontAlignZones 116, DefineButton2 119, DefineButtonCxform 188,
CSMTextSettings 334, DefineFont3 26, DefineSound 137, DefineMorphShape 51,
DefineMorphShape2 49, DefineBitsLossless2 10, DoInitAction 69, DoAction 6,
FrameLabel 4, PlaceObject2 87, RemoveObject2 83, SetBackgroundColor 1,
JPEGTables 1, DefineBits 2, DefineBitsJPEG3 3, SoundStreamHead2 1,
PlaceObject3 1, Unknown(24) 1.

### 1.4 Vocabulario recuperado del bytecode AVM1 (PROBADO)

Se resolvió el formato de `ConstantPool` (claim RXRE-SWF-012,
**corregido**): formato estándar `0x88, u16 ActionLength,
u16 Count, luego Count cadenas NUL-terminadas`. El `Count`
es el **segundo** u16; el primero es `ActionLength` (mal
etiquetado "campoA" en `avm1_strings.py`). El `ConstantPool`
**es una acción autónoma real**: 456 acciones `0x88`
standalone (`walk_actions`), 456 scripts con pool válido,
9801 cadenas de pool. DoAction[0] count=23 (`rightClick`,
`ContextMenu`, `hideBuiltInItems`, `_root`, `menu`,
`MadnessWorldMap`, `world_map`, `Object`…).

De 75 scripts (6 DoAction + 69 DoInitAction), 60 tienen
pool localizable. Vocabulario combinado: **5137
identificadores** (`raw/avm1-vocab.json`).

**26 clases `Madness*`** (claim RXRE-SWF-006): MadnessAI, MadnessActivator,
MadnessCharacter, MadnessCharacterCreator, MadnessCutscene, MadnessDataFile,
MadnessDoors, MadnessEvents, MadnessGame2, MadnessGameSelect, MadnessLevel,
MadnessMedals, MadnessMenu, MadnessObstacle, MadnessParticle, MadnessPopup,
MadnessRoster, MadnessSaveData, MadnessSpawner, MadnessStoreHire,
MadnessStoreItems, MadnessTeamSetup, MadnessTest3, MadnessTransition,
MadnessWorldMap.

**Sistemas recuperados** (claim RXRE-SWF-009, DERIVATION/CORROBORATED):
- **TAC-BAR**: barra de evasión. "Keep it from hitting empty, and you'll
  never take a bullet." "Blocking will reduce TAC-BAR damage, while dodging
  will outright prevent it."
- **Clases de arma**: pistol ("small, single-handed ranged"), SMG ("small,
  two-handed ranged"), rifle ("large, two-handed ranged"), shotgun
  ("large, two-handed scatter"), melee ("at close range, or thrown"),
  unarmed ("one's fists as weapons"), thrown.
- **Clases de armadura**: light / medium / heavy.
  "Close-range attacks ignore the enemy's medium or light armor."
- **Perks**: Rifle/SMG/Shotgun Tac Damage, Damage Reduction+, Melee/Unarmed
  damage+, Tac-Bar damage+, Carry a second weapon, Doubletime shotgun reload,
  extra shotgun pellet, three-hit combo finisher, disarm on block, deflect bullets.
- **Combate**: headshots, point-blank, combos, blocking, dodging, parrying,
  knockdown, stun, disarm.

**Personajes** (RXRE-SWF-010): Sanford ("always equips a special hook weapon"),
Deimos, Hank, Dr. Christoff.

**Misiones/ubicaciones** (RXRE-SWF-011): Nexus Stronghold, Armory,
Recon Hut/Com-Tower, Barracks, Communication Tower.

**Enemigos**: G03LM Mk1 ("new G03LM Mk1 units for training at the Nexus
Stronghold"), zombie agent (`zombie_agent_classic`).

**Escena** (RXRE-SWF-007): 4 etiquetas de fotograma — `preoader` (sic),
`sound`, `menu`, `gameScreen`.

**Audio** (RXRE-SWF-008): 137 DefineSound, ~29,257,171 samples (~22 min a
22 kHz), 132 MP3 + 3 Nellymoser + 2 ADPCM, todos mono.

**Metadatos XMP** (RXRE-SWF-005, hipótesis RXRE-SWF-016): Adobe Flash CS4
Professional; CreateDate 2012-05-10T21:02:22-04:00; ModifyDate
2014-09-09T01:10:29-04:00. Ubicación no estándar: viaja en el tag
`SymbolClass(77)`, no en `Metadata(78)`.

### 1.5 Desensamblador AVM1 por regla de longitud (PROBADO)

Sin tabla de opcodes primaria, se recuperó la **regla de longitud** de
la acción AVM1 (claim RXRE-SWF-019): `ActionCode` u8; si `code>=0x80`
sigue `u16 ActionLength` + `Data[ActionLength]`; si `code<0x80` es
acción corta (1 byte, sin longitud ni datos). Con esa regla los **1749
scripts parsean limpio a `End(0x00)` sin desbordamiento (100%)**.

**Descubrimiento no estándar (claim RXRE-SWF-020):** la acción `Push`
en este SWF es el opcode **`0x96`**, no el estándar `0x9C`. `0x96` es
la acción más común (11 347 en el script mayor; 54 187 con datos en
total); `0x9C` aparece **0** veces como código de acción. Los datos de
`0x96` parsean como constantes `Push` tipadas.

**Tipo 9 = Const16 (claim RXRE-SWF-021):** índice de pool de 2 bytes
(rango 256–907, confirmando `Lookup16` para pools >256 entradas). Con
tipo 9 = 2 bytes, las 54 187 acciones `Push` parsean 100% limpio.

**Tipo 6 NO es Double — REFUTADO (claim RXRE-SWF-022):** los 8 bytes
no decodifican como `double` en ningún orden de bytes (1.75 como double
sería `3F FC 00 00 00 00 00 00`, no `00 00 e0 3f …`). Estructura
real: **`float32_LE[0:4]` + `uint32_LE[4:8]`**. El `float32` es un
multiplicador de juego (rango 1.45–2.06, el más común 1.75; también
negativos −1.5..−2.4 y valores grandes 3.0–1031.5). El `uint32` para
pares multiplicador es un conjunto pequeño
{`0x00000000`,`0x33333333`,`0x66666666`,`0x9999999a`,`0xccccccdd`}
= fracción fija 0.32 {0.0, 0.2, 0.4, 0.6, 0.8}.

**El uint32 NO es función determinista del float32 — REFUTADO (RXRE-SWF-047, PROVEN):**
se intentó la fórmula `u=((b&0xFFFFF)*0x100001+128)>>8` (verificada a
mano en 6 pares). Al invertirla (biyección para M de 20 bits) y
recuperar el M' efectivo de cada u sobre los **61 pares distintos**,
la fórmula es exacta **solo 27/61**: M'==lo20 en 27; M'==lo20^0x80000
(bit 19 volteado) en 9; M'==lo20&0x1FFFF en 8; M'==lo20&0xFFFF en 2;
OTHER en 6; y **9 pares NO tienen inversa** (u no es de la forma
formula(M): f=0.814, 1.13963, 2.3927, 30, 32.6566, 45.8208, 81.0949,
107.369, 1031.53). El mismo u aparece con float32 de lo20 distinto
(u=0.4 para f=1.8, 1.8625, 1.89375, 1.925, 2.0375, 2.1, 3.77822).
**Conclusión:** la fórmula es una **coincidencia** que vale cuando
lo20==round(u·2^20). El `uint32` es un **valor separado**
(fracción 0.32 = peso/probabilidad emparejada con el multiplicador),
**no** una función del float32. El significado de juego del uint32
sigue **NOT_DETERMINED** (requiere runtime Flash, RXRE-SWF-014).
Análisis completo: `evidence/type6-uint32-analysis.md`.

**Cuerpos de función = tokens nativos — REFUTADO "desensamblar tick()"
(RXRE-SWF-048, PROVEN, NEGATIVE_RESULT):** la premisa de recuperar la
fórmula exacta de combate desensamblando `tick()` es **refutada**.
Corrigiendo `decode_define_function` (que no leía `regCount`+`flags`
de DefineFunction2 ni manejaba la ausencia de `regIdx` en
DefineFunction), se decodificaron los **1342** DefineFunction(0x9B)/
DefineFunction2(0x8E). **Todo cuerpo mide exactamente 2 bytes
(1342/1342)**. De ellos, **322 empiezan con un opcode ≥0x80**
(`0x9C`, `0xC0`, `0xD7`, `0xC9`, `0xC4`, `0xDA`, `0xE4`, `0xE0`,
`0xEB`, `0xAF`, `0xFA`, `0xFF`…), lo que es **imposible** para una
acción larga AVM1 estándar (necesitaría `code`+`u16 length`+datos =
≥3 bytes, +`End` = ≥4 bytes) en 2 bytes. Además, **306 cuerpos no
terminan en `End(0x00)`**. Solo **839/1342** son secuencias de
acciones estándar de 2 bytes (`[acción corta, End]`). **Ergo:** el
cuerpo **no** es una secuencia de acciones AVM1 estándar; es un
**token de llamada a rutina nativa**. `tick()` = token `0x44` (189/196;
variantes `0x1C`×6, `0x6D`×1). La fórmula exacta de combate **no**
está en los cuerpos.

**Firmas de función = modelo de datos (RXRE-SWF-048, PROVEN):** las
firmas (params, ahora decodificadas correctamente) revelan el modelo
del juego. **Combate:** EXPLOSION/DANOS (13 params, body=0x51):
`inType, inScorch, inSource, inX, inY, inFloor, inRange, inDamage,
inSound, inKnockback, inDir, inAutoHit, inSubDeath`; GOLPE DE ARMA
(6, body=0x60): `inWeapon, inAttacker, inHitX, inHitY, inRangeGood,
inHeadshot`; ATAQUE DE ARMA (5, body=0x4A): `inWeapon, inAttacker,
inBlock, inKillShot, inRange`; MELEE (3, body=0x53): `inMeleeDir,
inMeleeType, inWeapon`; DANOS (1, body=0x17): `inDamage`; BLAST (3,
body=0x5A): `inSource, inPower, inReverseBlast`. **Stats** (15,
body=0xC0): `inStr, inDex, inTac, inEnd, inLead, inAwr, SPACER,
inMelee, inUnarmed, inPistol, inRevolver, inSMG, inShotgun, inRifle,
inHeavy` (Strength/Dexterity/Tactics/Endurance/Leadership/Awareness
+ proficiencia por tipo de arma). **Física** (15): `inType, inCategory,
inX, inY, inXSpeed, inYSpeed, inRot, inRotSpeed, inBounce, inFloor,
inAlpha, inScale, inStanding, inStandRot, inDataRef`. Análisis completo:
`evidence/function-signatures.md`.

**Ejecutor simbólico + fórmulas recuperadas (RXRE-SWF-049,
PROVEN):** dado que los cuerpos son tokens nativos
(RXRE-SWF-048), se construyó un **ejecutor simbólico
lineal** (`tools/avm1_sym.py`) sobre el stream principal
que mantiene una pila de expresiones simbólicas y registra
las escrituras `SetMember`. Se descubrió que **`0x47` =
NIP** (elimina el elemento debajo del tope): en el patrón
de modificadores `Push[r1,"modX",1,r1,"statY"] →
GetMember → Push[N] → Divide → 0x47 → SetMember`, la
pila `[r1,"modX",1,(r1.statY/N)]` se reduce a
`[r1,"modX",(r1.statY/N)]` y el balance neto por sentencia
es 0 (con no-op sería +1, crecimiento no acotado). Esto
recupera, **resueltas por pool**, las fórmulas
**estadística→modificador**:
`modSpeed=statDEX/45`, `modDmg=statSTR/15`,
`modRecharge=statTAC/10`, `modArmor=statEND/15`,
`modAllySmart=statLEAD/15`, `modHurtTactics=statAWR/50`;
**movimiento**: `myAccel=mySpeed/4`,
`mySpeedRight=(intendedX-_x)/6`; **daño**:
`myDamage*=3`, `myDamage=myDamage/2`,
`assignWeaponDamage=call()/4`; **armadura (fuente)**:
`myHeadArmor=myHat.myArmor`,
`myBodyArmor=myShirt.myArmor`, `myPrice=myArmor*100`;
**salud**: `meleeHealth=meleeHealth-1`, `bodyDamage=4`,
`headDamage=4`. **8 675 escrituras** recuperadas (599 con
expresión aritmética). **Lo que NO se recupera:** la
**mitigación de armadura** (`daño=f(myDamage,myArmor)`) —
está en la rutina nativa (token, RXRE-SWF-048) con firma
`inDamage/inArmor`, no en el stream principal. `0x47` es
globalmente dependiente del valor (RXRE-SWF-046); NIP es
una hipótesis local validada por balance de pila.
Análisis completo: `evidence/symbolic-formulas.md`.

**Fórmula de aplicación de daño (RXRE-SWF-050,
PROVEN):** la **aplicación de daño de combate
SÍ está en el stream principal** (no solo en la
rutina nativa). Confirmada por **traza de
bytecode** (script 1627, acciones 31869-31884)
+ resolución de pool + balance de pila neto 0:

```text
r1.myAttackTarget.myHealth
  = r1.myAttackTarget.myHealth
    - (r1.myDataRef.myUnarmed.myDamage / 4)
```

El objetivo pierde salud = **daño desarmado / 4**.
La traza es: `Push[R1,myAttackTarget] →
GetMember → Push[myHealth,R1,myAttackTarget] →
GetMember → Push[myHealth] → GetMember`
(construye `myAttackTarget.myHealth` actual)
`→ Push[R1,myDataRef] → GetMember →
Push[myUnarmed] → GetMember → Push[myDamage] →
GetMember` (construye `myDataRef.myUnarmed.
myDamage`) `→ Push[4] → Divide → Subtract(0x0B)
→ SetMember(0x4F)`. Pool: `LK:203=myAttackTarget`,
`LK:62=myHealth`, `LK:12=myDataRef`, `C16:546=
myUnarmed`, `C16:481=myDamage`. **Fórmulas
relacionadas** (mismo stream):
`recoilTimer = weapon.myDamage * weapon.myShots`
(rebobinado = daño×disparos);
`skillPoints = myLevel * 3`;
`myDataRef.myHealth = myHealthMax / 2`
(renacer a mitad); `myGun.myHealth -= 2`
(durabilidad de arma); `targetHealthY = 5 *
(myHealth/myHealthMax)` (barra de salud).
**Lo que NO se recupera:** la **mitigación de
armadura** (cómo `myArmor` reduce el daño
entrante) — está en la rutina nativa
`inDamage/inArmor` (token, RXRE-SWF-048). El
daño de arma usa la misma resta con una variable
de daño calculada; el cómputo completo del daño
de arma (con mitigación) está en la rutina nativa.
Análisis completo: `evidence/symbolic-formulas.md`,
`queries/damage-response.json`.

**Aleatorización del daño y crítico de headshot
(RXRE-SWF-051 → PARTIAL, corregido por
RXRE-SWF-052):** el daño **se aleatoriza**
mediante `SwainMath.randomNumber`, y el
**crítico de headshot está *gated* por el perk
`perkHeadshotCrits`** (comprobado con
`myDataRef.havePerk(perkHeadshotCrits, 2,
MadnessDataFile)` — CallMethod). Trazas:

```text
r18 = SwainMath.randomNumber(2, 120, 200) / 100
    = [1.20, 2.00]        <- crítico 120%-200%

si perkHeadshotCrits:
    r3 = r1.bodyDamage
    r3 = r3 * r18         <- multiplica por el crítico
    r4.myDamage = r3
    r1.myHealth = r1.myHealth - r3

si amSpecial && myCat == "melee":
    r18 = 1               <- sin crítico
```

El perk `bulletEater` ramifica el cómputo del
daño.

**Convención de `SwainMath.randomNumber`
(RXRE-SWF-052, PROVEN):** se escanearon los
**418 sitios de llamada** de
`SwainMath.randomNumber` en los 1749 scripts
(**179 firmas distintas**). La convención es

```text
SwainMath.randomNumber(precision, lo, hi)
    -> valor en [lo, hi], redondeado a
       `precision` decimales
```

**Prueba:** de las llamadas con los 3 argumentos
enteros comparables, **101** son verificables y
hay **0 violaciones** de `lo <= hi`. El patrón
dominante es `randomNumber(2, -N, N)` →
rango simétrico `[-N, N]`.

**Corrección (§80/§81) — esto REFUTA parte de
RXRE-SWF-051.** Los argumentos se empujan en
orden **INVERSO** (convención AVM1: el último
empujado antes del objeto es `arg1`). Así:

```text
Push[R3, -2, 2, SwainMath] -> 0x1C ->
Push[randomNumber] -> CallMethod

  DECLARA randomNumber(2, -2, R3)   -> rango [-2, R3]
  NO     randomNumber(R3, -2, 2)
```

Por tanto el rango del daño es `[-2,
totalFrameDamage]`, **NO** `[TFD-2, TFD+2]`
como afirmaba RXRE-SWF-051. Fórmula corregida:

```text
damage = Math.floor(
    SwainMath.randomNumber(2, -2, totalFrameDamage) / 4)
  -> floor([-2, TFD] / 4) = [-1, TFD/4]
  -> tras el clamp de salud: [0, TFD/4]
```

El **crítico [1.20, 2.00] sí se confirma**
(`randomNumber(2,120,200)/100`). Limitación: el
modo de redondeo exacto (floor vs round) NO se
determina (cuerpo nativo). La **mitigación de
armadura** sigue en la rutina nativa
`inDamage/inArmor` (RXRE-SWF-048). Análisis
completo: `evidence/swfmath-rand.md`,
`queries/swm-response.json`.

**Constantes numéricas extraídas (RXRE-SWF-015 → PARTIAL):** de las
54 187 acciones `Push(0x96)` se extrajeron, con conteo:
Integer **17 033** (260 distintos), pares float32+uint32 **5 435**
(61 pares distintos), Const16 **8 873**, Lookup **46 125**, String
**2 918**, Register **25 283**, Boolean **2 174**. Los **valores**
están OBSERVED (`raw/avm1-constants.json`); la **asignación** semántica
(qué constante es damage / range / fire-rate) sigue **NOT_DETERMINED**:
requiere el flujo de control del bytecode, que no se desensambla sin
tabla de opcodes completa.

**Correlación pool→multiplicador (RXRE-SWF-023, HYPOTHESIS):** los
multiplicadores de combate float32 se concentran en **15 scripts** que
forman **2 grupos de pool compartido**. **Grupo A** (combate general:
`tac`, `damage`, `health`, `melee`, `headshot`, `block`, `zombie`) es
dominante en **1.75** (74), luego 1.9125(33), 1.925(25), 1.9375(18).
**Grupo B** (point-blank / personajes: `blank`, `sanford`, `deimos`,
`christoff`, `pellet`, `evade`, `finisher`, `doubletime`, `second`,
`carry`) usa **1.9125**(23–28), **1.925**(15–22), **1.9375**(5) y
**no contiene 1.75**. Es evidencia de **co-ocurrencia** (HYPOTHESIS),
**no** prueba de flujo de control: el mapeo exacto constante→mecánica
sigue NOT_DETERMINED.

**Trace de control-flow (RXRE-SWF-024/025):** las acciones
**cortas** (0x00–0x33) son **AVM1 estándar** (claim RXRE-SWF-024):
`0x0B`(Restar)=711, `0x0C`(Multiplicar)=669, `0x0D`(Dividir)=455,
`0x12`(Not)=6178, `0x17`(Pop)=10082, `0x1C`(GetVariable)=7728,
`0x1D`(SetVariable)=316, `0x07`(Stop)=521 — frecuencias sensibles
(Pop/GetVariable tras Push). Las acciones **largas** (≥0x80) son la
parte no estándar (Push=0x96). Un simulador de pila
(`tools/avm1_trace.py`) traza `SetVariable`: resuelve **307
asignaciones**, pero **todas son framework/UI** (`onEnterFrame`=275,
`cacheAsBitmap`, `myPhase`, `_redirect`, `mouseChildren`…) —
**ninguna variable de combate** (claim RXRE-SWF-025,
NEGATIVE_RESULT). **Conclusión del análisis anterior (ahora
corregida abajo):** las constantes de combate **no** se asignan
por `SetVariable`; se creía que fluían a **llamadas a
función/método** (`0x4E`=24316, `0x4F`=8359, `0x52`=7699,
`0x9D`=5443, `0x49`=2497) cuya semántica **no estaba
identificada**, por lo que el mapeo constante->mecánica se dio
por **NOT_DETERMINED** (bloqueado por la tabla de opcodes de
llamadas). Esa conclusión **era un artefacto del simulador de
pila sin rama `else`** (véase la corrección inmediatamente
abajo, RXRE-SWF-028/029/040).

**CORRECCIÓN DECISIVA (esta sesión, RXRE-SWF-028/029/040):** el
análisis anterior **identificó mal `0x4E` como SetMember** porque
el simulador de pila (`avm1_trace.py`) **no tenía rama `else`**:
trataba todos los opcodes desconocidos como no-ops, corrompiendo
la pila. El balance de pila riguroso prueba lo contrario:

| Opcode | Semántica | Prueba | Estado |
|---|---|---|---|
| `0x4E` (24316x) | **GetMember** (LEER `obj[clave]`) | `Push[R1,374] -> 0x4E -> Push[R1,376] -> 0x4E -> Push[2] -> Divide -> Multiply` = `R1[374]*(R1[376]/2)`; solo cuadra con pop2/push1 | **PROVEN** |
| `0x4F` (8359x) | **SetMember** (ESCRIBIR `obj[clave]=valor`) | `Push[R1,374,3] -> 0x4F` almacena `R1[374]=3`; solo cuadra con pop3 | **PROVEN** |

**Los multiplicadores de combate SÍ aparecen** — fluyen a
`SetMember(0x4F)` vía el patrón read-modify-write
`Push[o,k,o,k] -> GetMember(0x4E) -> Push[mult] -> Multiply(0x0C) -> SetMember(0x4F)`,
que codifica `obj[k] = obj[k] * mult`. El mapeo
propiedad<-multiplicador está **RESUELTO** (RXRE-SWF-040), no
saturado: `myDamage=[0,2.0625,2.34375,2.40625,2.46875,2.515625]`,
`myArmor=[0,1.75,1.825,1.9,2.15,2.578125]`, `myDash=[1.90625,
1.9125,1.925]`, `myScale`, `mySpeed`, `volumeMusic`,
`myHealth=[0,1031.525269]`, `myPrice`, `stairsAdjustMove`,
`damageDifficultyMod`, `bulletRotation`, `xSpeed`, `mySpread`,
`myRange`, `recoilTimer`, `myHireCost` — 32 propiedades con
multiplicador no-cero.

**Frontera reabierta y cerrada:** la frontera declarada `SATURADA`
(RXRE-SWF-027) **era un artefacto del fallo del simulador**; se
reabrió, se derivó la semántica de `0x4E`/`0x4F` por balance de
pila, y el mapeo constante->mecánica pasó de NOT_DETERMINED a
RECUPERADO.

**Simulador de pila con CFG (RXRE-SWF-042/043/044):** se
construyó `tools/avm1_cfg.py` — el flujo de control que
faltaba. **Decodificación de salto PROBADA:** `0x99`=
salto incondicional (1 sucesor), `0x9D`=branch
condicional (2 sucesores); `destino = pos_offset + 2 +
int16_signo` (**7053/7053 = 100%** de los saltos caen
en límites de instrucción). El método (resolver cada
script por separado y agregar el consenso unánime entre
scripts consistentes) está **VALIDADO**: recupera
`0x4E`=GetMember como neto -1 en **24/25** scripts.

**Efectos netos DETERMINADOS** (consenso unánime,
SUPPORTED — no PROVEN porque no hay runtime Flash):
`0x9D` BranchIf = **-1** (consume la condición, 4
scripts); `0x40` = -1 (16); `0x49` = -1 (6); `0x3E` =
-1 (2); `0x9F` = -1 (18); `0x42` = 0 (2); `0x81` = 0
(2); `0x8C` = 0 (2). Esto **resuelve parte de
RXRE-SWF-039**: `0x40`, `0x49`, `0x3E`, `0x42` pasan
de NOT_DETERMINED a DETERMINADO.

**Lo que permanece NOT_DETERMINED:**
- `0x52` CallMethod y `0x87` StoreRegister son
**dependientes del valor** (RXRE-SWF-045): su efecto
depende de valores en la pila (`#` de args de
CallMethod: -2/-3/-4; StoreRegister: dominante 0 en
6/7 con discordancia -1). No son determinables por
análisis de profundidad — requieren simulación de
valores.
- `0x3D`,`0x43`,`0x47`,`0x50`,`0x53` con consenso
discordante y `0x48`,`0x51` sin datos (RXRE-SWF-046).
- La fórmula exacta (valor base, orden de operaciones,
efecto del uint32 del tipo 6) requiere runtime Flash
(RXRE-SWF-014).

---

## 2. Qué se probó y cómo

Cada claim del `evidence/claims-registry.md` lleva: ID, taxonomía
(FACT/MEASUREMENT/DERIVATION/NEGATIVE_RESULT/HYPOTHESIS), estado
(PROVEN/CORROBORATED/NOT_DETERMINED/PROVEN_ABSENT/OPEN), enunciado,
evidencia (artefacto + offset/procedimiento).

Los 52 claims se registraron en RXRE vía `op:record` y
`registrar_investigacion` (IDs en `queries/record-responses.jsonl`,
`queries/cfg-record-responses.json`,
`queries/type6-refute-response.json`,
`queries/signatures-response.json`,
`queries/formulas-response.json`,
`queries/damage-response.json`,
`queries/damage-rand-response.json` y
`queries/swm-response.json`).

**Cadena de prueba clave (ConstantPool):** el formato no se asumió de memoria;
se derivó por ajuste exacto. Con `count` = primer u16 (324) solo caben 97
cadenas en 591 B (desborda); con `count` = segundo u16 (23) caben exactamente
23 cadenas y el pool termina en 327/591 B. Validado independientemente en
DoInitAction[0] (244 cadenas, termina en 2188/9194 B).

---

## 3. Qué permanece desconocido y por qué

| Desconocido | Por qué | Claim |
|---|---|---|
| **Constantes numéricas de balance** (damage, range, fire rate, tasas de TAC-BAR, % de mitigación de armadura, magnitudes de perks) | **VALORES RECUPERADOS (OBSERVED)** vía el desensamblador de la regla de longitud: 17 033 Integer, 5 435 pares float32+uint32, 8 873 Const16, 46 125 Lookup, 2 918 String (`raw/avm1-constants.json`). **La ASIGNACIÓN semántica sigue NOT_DETERMINED**: qué constante corresponde a damage/range/fire-rate requiere el flujo de control del bytecode (tabla de opcodes incompleta). | RXRE-SWF-015 (PARTIAL) |
| **Flujo de control completo** (máquinas de estado de las 26 clases) | Requiere la semántica de los opcodes de acción (qué hace cada `code`), no solo su longitud. Se tiene la regla de longitud (RXRE-SWF-019) y `Push=0x96` (RXRE-SWF-020), pero no la tabla de semántica de opcodes. | RXRE-SWF-015 |
| **Fórmula exacta de evasión de la TAC-BAR** | El concepto está recuperado; la fórmula es un MODELO DERIVADO de las descripciones, no la semántica del original. | RXRE-SWF-009 |
| **Validación diferencial** | No hay runtime Flash (sin ruffle, swftools, flasm; wine sin plugin Flash). El original no puede ejecutarse. | RXRE-SWF-014 |
| **Propósito del tag 24** (31 B) | Contiene `$1$Xg$7P2RjvftDquRuFo.lqa8W/` (formato MD5-crypt); propósito desconocido. | RXRE-SWF-017 |
| **DoInitAction[1..68]** | No empiezan con ConstantPool (empiezan con 0xC4–0xD9, 0x90–0x9C, 0xA0–0xA9, 0xE0–0xE1). Si son definiciones de clase que referencian el pool de [0] o tienen pools propios es NOT_DETERMINED. | RXRE-SWF-018 |

---

## 4. Qué habilitó e impidió RXRE

**Habilitó:**
- `op:record` (vía `tools/rxre/api/machine.py`) registró las 18 claims en SQLite
  con `kind` en lista cerrada `{hypothesis, claim, note, next_action, frontier}`.
  Esta es la **ruta verificada más estrecha** para registrar evidencia extraída.
- `op:capabilities`, `op:ops`, `op:checkpoint` proporcionaron el catálogo
  de capacidades y el contrato.

**Impidió (gap de capacidad medible, claim RXRE-SWF-013):**
- RXRE **no puede ingerir el binario SWF**. `search`/`evidence` buscan el
  corpus del kernel (`RESEARCH/working/linux-7.1.3`) → `NOT_FOUND` para los
  identificadores del SWF. `register` interpreta el path como nombre de
  registro ASIC → `PROVEN_ABSENT_EN_ASIC_REG`.
- Las 12 capacidades de `tools/rxre/cli.py` son de RE de driver GPU
  (PM4, registros ASIC, AST/xref/trace/defuse sobre fuentes del kernel).
  Ninguna ingiere binarios arbitrarios ni parsea SWF.
- **Consecuencia:** toda la extracción del SWF se hizo con herramientas
  externas propias (`swfparse.py`, `extract.py`, `avm1_strings.py`) y los
  hechos se registraron en RXRE vía `op:record`.

---

## 5. Qué reproduce la implementación en C

`src/` (C99, `-Wall -Wextra -Werror`, sin dependencias de renderizado/audio):

- **Núcleo de simulación** (`rxre_swf.h`/`rxre_swf.c`): estado de personaje,
  enemigo, TAC-BAR, perks, y la función `resolve_attack` con el flujo
  recuperado: (1) evasión vs TAC-BAR → (2) conexión → (3) modificadores
  (headshot, point-blank, perk por clase) → (4) mitigación de armadura →
  (5) stun/knockdown/disarm/deflect → (6) aplicar daño a la salud.
- **Separación arquitectónica** (sección 5 del benchmark): simulación
  testeable sin renderizado; no hay capa de plataforma, audio ni assets.
- **Nombres recuperados**: 26 clases Madness (en vocabulario), 7 clases de
  arma, 4 clases de armadura, 4 personajes, 5 misiones, 3 tipos de enemigo.
- **Valores**: los **nombres** y el **flujo** están recuperados;
  los **valores numéricos** están OBSERVED en tablas de candidatos
  (`src/rxre_swf_constants.c`: 43 multiplicadores float32, 43 pares
  multiplicador+fracción, 260 enteros distintos). Los valores que la
  simulación **usa** y que no tienen asignación recuperada llevan el
  marcador `NOT_RECOVERED(RXRE-SWF-015)` y un `PLACEHOLDER` que **no**
  es un dato del original. Las tablas OBSERVED son el *pool* de
  candidatos; **no** se asignan a mecánicas concretas porque el
  mapeo semántico es NOT_DETERMINED.

**Cobertura de mecánicas** (nombres recuperados → implementados → testeados):
evasión TAC-BAR, agotamiento de TAC-BAR, reducción por bloqueo, conexión
con TAC-BAR vacía, headshot, mitigación de armadura light/medium/heavy,
ignorar armadura light/medium a corta distancia, perk de desarme al
bloqueo melee, dash que aturde, determinismo.

---

## 6. Resultados de validación (reales, no inventados)

**Build:** `make all` → `rc=0`, sin warnings con `-Wall -Wextra -Werror`.

**Tests unitarios** (`tests/test_combat.c`): **47 checks, 0 failures** (29 de flujo de combate + 18 de la tabla de propiedades recuperadas).
Verifican: evasión con TAC-BAR llena, conexión con TAC-BAR vacía,
determinismo (mismo input → mismo output, `memcmp` de resultados), headshot
> sin headshot, heavy mitiga más que light, melee ignora light/medium,
bloqueo reduce agotamiento, perk de desarme al bloqueo melee, dash aturde,
nombres recuperados.

**Test de regresión del desensamblador** (`tests/test_disasm.py`,
`make test-disasm`): **67 checks, 0 failures**. Valida contra los conteos
OBSERVED que las correcciones no-estándar permanezcan: `Push=0x96`
(54 187 acciones), tipo 6 = (float32, uint32) y no Double (sin valores
astronómicos), tipo 9 = Const16, ConstantPool `0x88` = acción autónoma,
**decodificación de función corregida** (createWound/tick con
regCount+flags leídos, params correctos) y **cuerpo=token nativo**
(1342/1342 cuerpos=2B, 322 tokens nativos, 306 sin End, 839 std,
tick=0x44). Incluye la **convención de
`SwainMath.randomNumber`** (RXRE-SWF-052): >=400 sitios de
llamada, >=100 firmas, >=100 comparables y **0 violaciones**
de `lo<=hi` bajo el orden INVERSO de empuje de args — si
alguien revierte ese orden, el test de violaciones falla
(§22 tool validation). Si alguien revierte `0x96` a `0x9C`,
`push_count` vuelve a 0 y el test falla.

**Validación diferencial:** **NO realizada**. No hay runtime Flash para
ejecutar el original como oráculo (claim RXRE-SWF-014). Se usaron tests
independientes basados en evidencia estática; no se reclama validación
diferencial.

**Denominadores explícitos** (sin porcentajes inventados):
- Tags parseados: 9788/9788 (100% del body, termina en `End(0)`).
- Scripts con pool localizable: 60/75.
- Acciones `ConstantPool(0x88)` standalone: 456 (validadas por `walk_actions`).
- Scripts que parsean limpio con la regla de longitud: 1749/1749 (100%).
- Acciones `Push(0x96)` con datos: 54 187 (parse 100% limpio).
- Asignaciones `SetVariable(0x1D)` resueltas: 307 (todas framework/UI; 0 de combate).
- Pares `SetMember(0x4E)` resueltos: 100 (todos enteros 0-9; 0 multiplicadores de combate).
- Claims registradas en RXRE: 27/27 (`rxre_status=ok`).
- Checks de test C: 29/29.
- Checks de test del desensamblador: 11/11.
- Mecánicas con nombre recuperado: 11 categorías (arma, armadura, TAC-BAR,
  perks, personajes, misiones, enemigos, escena, combate, audio, metadatos).
- Constantes numéricas **valores** recuperados (OBSERVED): 17 033 Integer
  + 5 435 pares float32+uint32 + 8 873 Const16 + 46 125 Lookup
  + 2 918 String (RXRE-SWF-015 PARTIAL).
- Constantes numéricas **asignadas** a una mecánica: **0**
  (el mapeo semántico es NOT_DETERMINED; requiere flujo de control).
- Constantes con evidencia de co-ocurrencia (HYPOTHESIS, RXRE-SWF-023):
  15 scripts en 2 grupos pool; 1.75 asociado a combate general,
  1.9125/1.925/1.9375 a point-blank/personajes.

---

## 7. Usabilidad de RXRE por una IA no familiarizada

Una IA sin contexto previo puede: (a) descubrir las capacidades vía
`op:capabilities`/`op:ops`; (b) descubrir `op:record` para registrar
hipótesis/claims/evidencia; (c) descubrir que **no** puede ingerir el SWF
(determinado por `NOT_FOUND` en `search` y `PROVEN_ABSENT_EN_ASIC_REG` en
`register`). El gap está documentado y es medible. La IA **no** puede usar
RXRE para parsear el SWF; debe recurrir a herramientas externas y luego
registrar los hechos vía `op:record`.

---

## 8. Mayor valor de la siguiente investigación

**Recuperar la ASIGNACIÓN semántica de las constantes
(RXRE-SWF-015: completar PARTIAL → PROVEN)** requiere la
tabla de semántica de los opcodes de **llamada**
(`0x4E`=24316, `0x4F`=8359, `0x52`=7699, `0x9D`=5443,
`0x49`=2497) y del resto del rango 0x3C–0xFF. Se
**probaron** ya las acciones cortas 0x00–0x33
(RXRE-SWF-024: estándar AVM1) y el trace de
`SetVariable` (RXRE-SWF-025: las constantes de combate
**no** se asignan por `SetVariable`, sino que fluyen a
esas llamadas). Esto desbloquea:
- Qué multiplicador (1.75, 1.9125, 1.925, …) es
  headshot, point-blank o crítico.
- Los valores reales de damage/range/fire-rate/tasas de
  TAC-BAR/mitigación.
- El flujo de control real de las 26 clases (máquinas de
  estado), sustituyendo el modelo derivado por la
  semántica real.

**Cómo se logró lo actual:** sin tabla de opcodes, la
regla de longitud (`code>=0x80` → `u16 len`+data;
`code<0x80` → 1 byte) basta para delimitar acciones y
extraer las constantes `Push(0x96)` tipadas. Eso
convirtió RXRE-SWF-015 de NOT_DETERMINED a PARTIAL
(valores OBSERVED). El simulador de pila
(`avm1_trace.py`) explota que 0x00–0x33 son estándar
para trazar `SetVariable` (RXRE-SWF-024/025).

**Estado de la frontera (actualizado):** el mapeo
constante->mecánica **ya no está bloqueado**. Se resolvió
por balance de pila riguroso: `0x4E`=GetMember y `0x4F`=
SetMember (RXRE-SWF-028/029), y el mapeo
propiedad<-multiplicador está RECUPERADO (RXRE-SWF-040).
El simulador de pila anterior (`avm1_trace.py`) fue la
causa raíz del falso "bloqueo": al carecer de rama
`else`, descartaba opcodes desconocidos como no-ops y
corrompía la pila, lo que hizo parecer que las
constantes "desaparecían" en llamadas no identificadas.

**Lo que sigue abierto (RXRE-SWF-039):** (a) la fórmula
exacta — valor base, orden de operaciones, efecto del
uint32 del tipo 6, flujo de control de `tick`/
`createWound` — y (b) la semántica exacta de
`0x3D,0x40,0x42,0x47,0x48,0x49,0x4C,0x50,0x51`.
Ambas requieren un **simulador de pila con flujo de
control completo** (propagación forward/backward de
efectos de pila con consistencia de destinos de salto
`0x99`/`0x9D`), no solo el patrón local.

**Alternativa de alto valor:** obtener un runtime Flash
(ruffle) para habilitar la validación diferencial contra
el original (desbloquea RXRE-SWF-014). Con el original
ejecutable, la asignación de constantes y la fórmula
exacta se validarían empíricamente, y se resolvería el
papel del uint32 del tipo 6.

**Criterio de decisión:** el simulador de pila con flujo
de control tiene mayor desbloqueo inmediato (convierte
RXRE-SWF-039 en OBSERVED sin dependencia externa);
Ruffle desbloquea la validación diferencial y, con ella,
la confirmación empírica de la fórmula. Ambos son
compatibles: el simulador reduce la incertidumbre
estática, Ruffle la valida en runtime.