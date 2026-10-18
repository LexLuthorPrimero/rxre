# Funciones recuperadas: firmas (RXRE-SWF-048)

Metodo: decode_define_function(data, opcode) corregido.
Formato PROBADO contra bytes brutos:
  0x9B DefineFunction:  nombre NUL, u16 numParams,
       params (nombre NUL, SIN regIdx), body.
  0x8E DefineFunction2: nombre NUL, u16 numParams,
       u8 regCount, u16 flags, params (u8 regIdx +
       nombre NUL), body.

## HALLAZGO: cuerpo = token nativo de 2 bytes

TODO DefineFunction/DefineFunction2 de este SWF tiene
un cuerpo de EXACTAMENTE 2 bytes (1342/1342).
  - 322 cuerpos empiezan con opcode >= 0x80
    (0x9C, 0xC0, 0xD7, 0xC9, 0xC4, 0xDA, 0xE4,
     0xE0, 0xEB, 0xAF, 0xFA, 0xFF...), lo que es
    IMPOSIBLE para una accion larga AVM1 estandar
    (necesitaria code + u16 length + datos = >=3
    bytes, + End = >=4 bytes) en 2 bytes.
  - 306 cuerpos NO terminan en End(0x00).
  - Solo 839/1342 son secuencias de acciones
    estandar de 2 bytes ([accion corta, End]).

Ergo: el cuerpo NO es una secuencia de acciones
AVM1 estandar. Es un TOKEN DE LLAMADA A RUTINA
NATIVA. La formula exacta de combate NO esta en
los cuerpos; hay que recuperarla del stream
principal (Push/GetMember/arith/SetMember) o
requiere runtime (RXRE-SWF-014).

Esto REFUTA la premisa de desensamblar tick()
para la formula: tick() es un token nativo
(0x44 la mayoria), no codigo AVM1.

## Firmas (nombre -> params, regCount, flags, body)

| Funcion | #params | Params | regCount | flags | body | ocurrences |
|---|---|---|---|---|---|---|
|  | 0 | - | - | - | 0x00 | 96 |
|  | 0 | - | 2 | 0x0029 | 0x09 | 73 |
|  | 0 | - | 3 | 0x0019 | 0x1E | 9 |
|  | 0 | - | - | - | 0x19 | 8 |
|  | 1 | val | 3 | 0x0029 | 0x1D | 8 |
|  | 0 | - | 2 | 0x001a | 0x11 | 7 |
|  | 0 | - | - | - | 0x47 | 6 |
|  | 0 | - | 2 | 0x0029 | 0x3D | 5 |
|  | 0 | - | - | - | 0x5E | 5 |
|  | 2 | inCard, inWeapon | - | - | 0x00 | 5 |
|  | 0 | - | 2 | 0x0029 | 0x20 | 4 |
|  | 0 | - | 2 | 0x0029 | 0x4D | 4 |
|  | 0 | - | - | - | 0x27 | 4 |
|  | 0 | - | 2 | 0x0029 | 0x18 | 4 |
|  | 0 | - | 3 | 0x0026 | 0x42 | 4 |
|  | 0 | - | 2 | 0x0029 | 0x12 | 3 |
|  | 0 | - | 2 | 0x0029 | 0x22 | 3 |
|  | 0 | - | - | - | 0x16 | 3 |
|  | 0 | - | - | - | 0x6D | 3 |
|  | 0 | - | - | - | 0x4B | 3 |
|  | 0 | - | - | - | 0x44 | 3 |
|  | 0 | - | - | - | 0xCD | 3 |
|  | 0 | - | - | - | 0x5A | 3 |
|  | 0 | - | - | - | 0x85 | 3 |
|  | 0 | - | - | - | 0x51 | 3 |
|  | 0 | - | - | - | 0x64 | 3 |
|  | 0 | - | - | - | 0x50 | 3 |
|  | 0 | - | 2 | 0x0029 | 0x35 | 3 |
|  | 0 | - | - | - | 0x28 | 3 |
|  | 0 | - | - | - | 0x18 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x64 | 2 |
|  | 0 | - | 2 | 0x0029 | 0xA0 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x28 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x3A | 2 |
|  | 0 | - | 3 | 0x0029 | 0xF0 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x7E | 2 |
|  | 0 | - | 2 | 0x0029 | 0x54 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x33 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x16 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x86 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x79 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x36 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x4C | 2 |
|  | 0 | - | 2 | 0x0029 | 0x25 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x63 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x2D | 2 |
|  | 0 | - | 2 | 0x0029 | 0x2F | 2 |
|  | 0 | - | 2 | 0x0029 | 0x98 | 2 |
|  | 0 | - | - | - | 0x1C | 2 |
|  | 2 | inRoom, inDoor | 3 | 0x002a | 0x27 | 2 |
|  | 2 | inRoom, inDoor | 3 | 0x002a | 0xB6 | 2 |
|  | 2 | inTarget, inEvent | 4 | 0x002a | 0x44 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x0B | 2 |
|  | 0 | - | - | - | 0xDB | 2 |
|  | 0 | - | - | - | 0xB9 | 2 |
|  | 0 | - | - | - | 0x63 | 2 |
|  | 0 | - | 2 | 0x006a | 0x9A | 2 |
|  | 0 | - | - | - | 0x8A | 2 |
|  | 0 | - | - | - | 0xA4 | 2 |
|  | 0 | - | - | - | 0x8C | 2 |
|  | 0 | - | - | - | 0xAD | 2 |
|  | 0 | - | - | - | 0xC0 | 2 |
|  | 0 | - | - | - | 0x26 | 2 |
|  | 0 | - | - | - | 0xCC | 2 |
|  | 0 | - | - | - | 0x88 | 2 |
|  | 0 | - | - | - | 0xA2 | 2 |
|  | 0 | - | - | - | 0x67 | 2 |
|  | 0 | - | 2 | 0x006a | 0x2B | 2 |
|  | 0 | - | 2 | 0x0029 | 0x24 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x26 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x47 | 2 |
|  | 0 | - | 2 | 0x006a | 0x2F | 2 |
|  | 1 | inSound | 3 | 0x0029 | 0x2D | 2 |
|  | 2 | inX, inY | 4 | 0x0029 | 0x2C | 2 |
|  | 0 | - | 2 | 0x006a | 0x60 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x69 | 2 |
|  | 0 | - | - | - | 0x2F | 2 |
|  | 0 | - | 2 | 0x0029 | 0x65 | 2 |
|  | 1 | value | 3 | 0x0029 | 0x1D | 2 |
|  | 1 | object | 4 | 0x0029 | 0x68 | 2 |
|  | 0 | - | 2 | 0x0029 | 0x0C | 2 |
|  | 1 | data | 2 | 0x002a | 0x14 | 2 |
|  | 1 | name | 3 | 0x0029 | 0x0F | 2 |
|  | 1 | id | 5 | 0x0029 | 0x6C | 2 |
|  | 1 | v | 3 | 0x0029 | 0x27 | 2 |
|  | 1 | val | 3 | 0x0029 | 0x30 | 2 |
|  | 2 | src, key | 6 | 0x002a | 0xA6 | 2 |
|  | 0 | - | - | - | 0x2E | 2 |
|  | 0 | - | 2 | 0x006a | 0x59 | 1 |
|  | 1 | inTrack | 2 | 0x002a | 0x4E | 1 |
|  | 1 | inTrackObj | 2 | 0x002a | 0x37 | 1 |
|  | 1 | inTrackObj | 2 | 0x002a | 0x7D | 1 |
|  | 0 | - | - | - | 0x0D | 1 |
|  | 0 | - | - | - | 0x49 | 1 |
|  | 1 | inOn | 2 | 0x002a | 0x75 | 1 |
|  | 0 | - | - | - | 0x3D | 1 |
|  | 2 | inSound, inPan | 5 | 0x002a | 0xB2 | 1 |
|  | 0 | - | 2 | 0x002a | 0xC7 | 1 |
|  | 1 | inSound | 3 | 0x002a | 0xFA | 1 |
|  | 0 | - | - | - | 0xF2 | 1 |
|  | 1 | inName | 3 | 0x002a | 0x2F | 1 |
|  | 1 | inName | 3 | 0x002a | 0x11 | 1 |
|  | 1 | inTrack | 2 | 0x002a | 0x3D | 1 |
|  | 4 | source_x, source_y, target_x, target_y | 5 | 0x002a | 0xD5 | 1 |
|  | 3 | this_mc, this_rotation, this_speed | 4 | 0x002a | 0xDA | 1 |
|  | 3 | this_axis, this_rotation, this_speed | 4 | 0x002a | 0xF2 | 1 |
|  | 5 | startX, startY, this_rotation, this_distance, this_axis | 6 | 0x002a | 0xE4 | 1 |
|  | 2 | mc_1, mc_2 | 3 | 0x002a | 0xA7 | 1 |
|  | 4 | mc_1_x, mc_1_y, mc_2_x, mc_2_y | 5 | 0x002a | 0x9B | 1 |
|  | 2 | min, max | 4 | 0x002a | 0x49 | 1 |
|  | 2 | inStart, inEnd | 4 | 0x002a | 0x31 | 1 |
|  | 2 | inRot1, inRot2 | 4 | 0x002a | 0x89 | 1 |
|  | 1 | inArray | 5 | 0x002a | 0xB4 | 1 |
|  | 1 | inArray | 2 | 0x002a | 0x2F | 1 |
|  | 2 | inElement, inArray | 4 | 0x002a | 0x5D | 1 |
|  | 1 | inNum | 5 | 0x002a | 0xE0 | 1 |
|  | 2 | inMC, inSpeed | 5 | 0x006a | 0xC4 | 1 |
|  | 1 | inFaction | 3 | 0x0029 | 0x0A | 1 |
|  | 1 | inChar | 3 | 0x0029 | 0x52 | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x1E | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x9C | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x6C | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x9F | 1 |
|  | 4 | inUnits, inDifficulty, inCategory, inLeader | 5 | 0x0029 | 0xA3 | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x5B | 1 |
|  | 1 | inWeapon | 3 | 0x0029 | 0x2D | 1 |
|  | 1 | inWeapon | 4 | 0x0029 | 0x95 | 1 |
|  | 1 | inArmor | 3 | 0x0029 | 0x33 | 1 |
|  | 1 | inArmor | 4 | 0x0029 | 0x95 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x0E | 1 |
|  | 0 | - | 3 | 0x0029 | 0x56 | 1 |
|  | 1 | inReason | 2 | 0x0029 | 0x12 | 1 |
|  | 1 | otherRoster | 6 | 0x0029 | 0x81 | 1 |
|  | 0 | - | 5 | 0x0029 | 0x0B | 1 |
|  | 1 | inMembers | 5 | 0x0029 | 0x99 | 1 |
|  | 0 | - | 4 | 0x0029 | 0xB8 | 1 |
|  | 0 | - | 5 | 0x0029 | 0xB0 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x9E | 1 |
|  | 1 | inChar | 5 | 0x0029 | 0x0B | 1 |
|  | 1 | inChar | 3 | 0x0029 | 0x9D | 1 |
|  | 3 | inSlot, inType, silencer | 6 | 0x0029 | 0x40 | 1 |
|  | 1 | inType | 4 | 0x0029 | 0x45 | 1 |
|  | 2 | inItem, forceSlot | 4 | 0x0029 | 0x1A | 1 |
|  | 2 | inCat, inStore | 6 | 0x0029 | 0xA3 | 1 |
|  | 2 | inItem, inSlot | 5 | 0x0029 | 0xEB | 1 |
|  | 4 | inCat, inCurrent, inArray, inRatio | 6 | 0x0029 | 0xA1 | 1 |
|  | 1 | inVariety | 5 | 0x0029 | 0xAD | 1 |
|  | 15 | inStr, inDex, inTac, inEnd, inLead, inAwr, SPACER, inMelee, inUnarmed, inPistol, inRevolver, inSMG, inShotgun, inRifle, inHeavy | 16 | 0x0029 | 0xC0 | 1 |
|  | 0 | - | 3 | 0x0029 | 0xC8 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x36 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x2C | 1 |
|  | 0 | - | 4 | 0x0029 | 0xC7 | 1 |
|  | 5 | inStat, inNum, inTextName, inTextDescription, inChar | 8 | 0x002a | 0x86 | 1 |
|  | 2 | inStat, inCat | 4 | 0x0029 | 0x75 | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x30 | 1 |
|  | 2 | inPerk, inChar | 3 | 0x002a | 0x09 | 1 |
|  | 2 | inLevel, inXP | 2 | 0x002a | 0x2F | 1 |
|  | 1 | inXP | 3 | 0x0029 | 0x46 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x89 | 1 |
|  | 2 | inType, inArray | 5 | 0x0029 | 0x61 | 1 |
|  | 1 | inLvl | 3 | 0x0029 | 0xA3 | 1 |
|  | 1 | inLvl | 3 | 0x0029 | 0x40 | 1 |
|  | 1 | inChar | 6 | 0x002a | 0xB2 | 1 |
|  | 0 | - | 5 | 0x0029 | 0x09 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x0D | 1 |
|  | 1 | inTarget | 9 | 0x002a | 0x35 | 1 |
|  | 1 | inType | 2 | 0x002a | 0x55 | 1 |
|  | 0 | - | 3 | 0x0019 | 0x6E | 1 |
|  | 8 | inRef, inRosterRef, inFaction, inPlayer, inRoster, myDoor, myStartX, myStartY | 9 | 0x0029 | 0x4A | 1 |
|  | 0 | - | 10 | 0x0029 | 0x61 | 1 |
|  | 0 | - | 6 | 0x0069 | 0x6D | 1 |
|  | 0 | - | 5 | 0x0069 | 0x8F | 1 |
|  | 0 | - | 2 | 0x0029 | 0xB3 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xAC | 1 |
|  | 0 | - | 2 | 0x0029 | 0xBB | 1 |
|  | 0 | - | 2 | 0x0029 | 0x3C | 1 |
|  | 0 | - | 5 | 0x0029 | 0xF3 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x8D | 1 |
|  | 6 | inWeapon, inAttacker, inHitX, inHitY, inRangeGood, inHeadshot | 23 | 0x0069 | 0x60 | 1 |
|  | 2 | inChar, inCategory | 4 | 0x002a | 0x07 | 1 |
|  | 1 | inChar | 3 | 0x002a | 0xF3 | 1 |
|  | 3 | inMeleeDir, inMeleeType, inWeapon | 27 | 0x0029 | 0x0E | 1 |
|  | 2 | hitType, hitHeight | 5 | 0x0029 | 0x53 | 1 |
|  | 1 | inAction | 3 | 0x0029 | 0xF4 | 1 |
|  | 3 | inTarget, inAttacker, thisWeapon | 4 | 0x002a | 0x05 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x5F | 1 |
|  | 4 | inSource, inX, inY, inWeapon | 9 | 0x0029 | 0xFF | 1 |
|  | 4 | inSource, inX, inY, inWeapon | 6 | 0x0029 | 0x63 | 1 |
|  | 4 | inX, inY, inFloor, inSparkCat | 8 | 0x0029 | 0x84 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x7A | 1 |
|  | 0 | - | 4 | 0x0029 | 0x22 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x55 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x61 | 1 |
|  | 1 | inArmor | 5 | 0x0029 | 0x61 | 1 |
|  | 6 | inLevel, inBlood, inDirMod, inX, inY, head | 15 | 0x0029 | 0xCE | 1 |
|  | 3 | inChar, inContainer, inID | 4 | 0x002a | 0x04 | 1 |
|  | 2 | inSpeedX, inSpeedY | 4 | 0x0029 | 0x5E | 1 |
|  | 1 | inSpeed | 3 | 0x0029 | 0x55 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xC1 | 1 |
|  | 1 | inEnemy | 3 | 0x0029 | 0x56 | 1 |
|  | 1 | inChar | 10 | 0x002a | 0x22 | 1 |
|  | 3 | inX, inY, inRoom | 10 | 0x002a | 0x73 | 1 |
|  | 1 | inDoor | 3 | 0x0029 | 0x77 | 1 |
|  | 2 | inMC, inInteractType | 4 | 0x0029 | 0xD0 | 1 |
|  | 2 | inMC, inNum | 4 | 0x002a | 0xDB | 1 |
|  | 0 | - | 8 | 0x0029 | 0x85 | 1 |
|  | 1 | inPlayer | 9 | 0x0029 | 0x7A | 1 |
|  | 0 | - | 2 | 0x0029 | 0x72 | 1 |
|  | 5 | inWeapon, inAttacker, inBlock, inKillShot, inRange | 7 | 0x0029 | 0x06 | 1 |
|  | 1 | inWeapon | 3 | 0x0029 | 0x2A | 1 |
|  | 1 | inWeapon | 5 | 0x0029 | 0xE1 | 1 |
|  | 1 | inMajor | 4 | 0x0029 | 0x90 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x19 | 1 |
|  | 0 | - | 5 | 0x0029 | 0xC9 | 1 |
|  | 1 | inTarget | 3 | 0x0029 | 0xA5 | 1 |
|  | 1 | inTarget | 3 | 0x0029 | 0x91 | 1 |
|  | 1 | inNum | 3 | 0x0029 | 0x17 | 1 |
|  | 3 | inPart, inValue, inCount | 4 | 0x002a | 0x20 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x43 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x40 | 1 |
|  | 0 | - | 10 | 0x0029 | 0xC4 | 1 |
|  | 0 | - | 9 | 0x0029 | 0xA1 | 1 |
|  | 3 | inSource, inPower, inReverseBlast | 5 | 0x0029 | 0x02 | 1 |
|  | 2 | inAttacker, inWeapon | 3 | 0x0029 | 0x5A | 1 |
|  | 0 | - | 3 | 0x0069 | 0xAF | 1 |
|  | 1 | inObs | 3 | 0x0029 | 0x61 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x05 | 1 |
|  | 1 | inUnit | 5 | 0x002a | 0xD4 | 1 |
|  | 1 | inSound | 3 | 0x0029 | 0x31 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xD0 | 1 |
|  | 0 | - | 2 | 0x002a | 0x5C | 1 |
|  | 5 | inType, inLock, inTarget, inX, inY | 7 | 0x0029 | 0x4B | 1 |
|  | 0 | - | 3 | 0x0029 | 0x84 | 1 |
|  | 1 | inTarget | 3 | 0x0029 | 0xAF | 1 |
|  | 0 | - | 2 | 0x0029 | 0x9A | 1 |
|  | 0 | - | 2 | 0x0029 | 0x89 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x07 | 1 |
|  | 1 | inAttacker | 3 | 0x0029 | 0x5B | 1 |
|  | 13 | inType, inScorch, inSource, inX, inY, inFloor, inRange, inDamage, inSound, inKnockback, inDir, inAutoHit, inSubDeath | 22 | 0x002a | 0x51 | 1 |
|  | 1 | inType | 3 | 0x0029 | 0x59 | 1 |
|  | 0 | - | 8 | 0x0029 | 0x5B | 1 |
|  | 2 | inChar, inData | 2 | 0x002a | 0x8E | 1 |
|  | 0 | - | 2 | 0x0029 | 0x11 | 1 |
|  | 1 | inDamage | 3 | 0x0029 | 0x40 | 1 |
|  | 1 | inEvent | 3 | 0x0029 | 0x17 | 1 |
|  | 0 | - | 3 | 0x0019 | 0x82 | 1 |
|  | 2 | inPlaceholder, inDataRef | 6 | 0x0029 | 0x6E | 1 |
|  | 0 | - | 3 | 0x0029 | 0x1F | 1 |
|  | 1 | inChar | 6 | 0x0029 | 0xE9 | 1 |
|  | 2 | inSprite, inDelete | 5 | 0x0029 | 0x92 | 1 |
|  | 2 | inChar, inGoal | 4 | 0x0029 | 0x8A | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0xDE | 1 |
|  | 0 | - | 2 | 0x0029 | 0x9E | 1 |
|  | 1 | inSprite | 9 | 0x0069 | 0x26 | 1 |
|  | 1 | inChar | 3 | 0x0029 | 0x16 | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x6F | 1 |
|  | 0 | - | 2 | 0x0029 | 0xD5 | 1 |
|  | 1 | inQual | 4 | 0x0069 | 0x4F | 1 |
|  | 0 | - | 3 | 0x0069 | 0x99 | 1 |
|  | 1 | inOn | 3 | 0x0029 | 0x69 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x6B | 1 |
|  | 1 | inQual | 3 | 0x0029 | 0x53 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x76 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x11 | 1 |
|  | 1 | inDir | 5 | 0x002a | 0x44 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xF1 | 1 |
|  | 0 | - | 2 | 0x006a | 0xCB | 1 |
|  | 0 | - | 2 | 0x006a | 0x22 | 1 |
|  | 0 | - | - | - | 0x3F | 1 |
|  | 3 | inSource, inTarget, inType | 6 | 0x006a | 0x2C | 1 |
|  | 0 | - | 2 | 0x006a | 0x9F | 1 |
|  | 2 | inWorld, inLevel | 3 | 0x002a | 0x99 | 1 |
|  | 0 | - | - | - | 0xC4 | 1 |
|  | 0 | - | 2 | 0x002a | 0x4E | 1 |
|  | 0 | - | 3 | 0x006a | 0x98 | 1 |
|  | 0 | - | 5 | 0x006a | 0x47 | 1 |
|  | 0 | - | 4 | 0x006a | 0x04 | 1 |
|  | 0 | - | 5 | 0x006a | 0x7E | 1 |
|  | 0 | - | 11 | 0x006a | 0xD0 | 1 |
|  | 0 | - | 7 | 0x006a | 0x2E | 1 |
|  | 0 | - | 3 | 0x002a | 0x4B | 1 |
|  | 0 | - | 2 | 0x002a | 0x42 | 1 |
|  | 0 | - | 3 | 0x006a | 0x7A | 1 |
|  | 0 | - | 3 | 0x006a | 0x76 | 1 |
|  | 0 | - | 6 | 0x006a | 0xFE | 1 |
|  | 2 | inCharArray, inDifficulty | - | - | 0x00 | 1 |
|  | 2 | inFaction, inUnitsArray | 6 | 0x002a | 0xE0 | 1 |
|  | 0 | - | 10 | 0x006a | 0x80 | 1 |
|  | 2 | inLevel, inWave | 10 | 0x002a | 0x5B | 1 |
|  | 2 | inLevel, inWave | 9 | 0x002a | 0x89 | 1 |
|  | 2 | inWorld, inLevel | 4 | 0x0029 | 0xB2 | 1 |
|  | 2 | inWorld, inLevel | 4 | 0x0029 | 0xCD | 1 |
|  | 1 | inStartWave | 7 | 0x0069 | 0xF4 | 1 |
|  | 0 | - | 3 | 0x0029 | 0xBF | 1 |
|  | 0 | - | 3 | 0x0029 | 0xD5 | 1 |
|  | 0 | - | 3 | 0x0029 | 0xE3 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x95 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x1C | 1 |
|  | 0 | - | 3 | 0x0029 | 0x5D | 1 |
|  | 0 | - | 3 | 0x0029 | 0xFF | 1 |
|  | 0 | - | 3 | 0x0029 | 0x68 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x90 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x01 | 1 |
|  | 0 | - | 3 | 0x0029 | 0xC7 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x43 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x7C | 1 |
|  | 2 | inRooms, inMode | 6 | 0x0029 | 0xC1 | 1 |
|  | 2 | inRooms, inDoors | 7 | 0x0029 | 0x06 | 1 |
|  | 5 | inRoom1, inDoor1, UNUSED, inRoom2, inDoor2 | 5 | 0x002a | 0x7E | 1 |
|  | 3 | inRoom, inDoor, inDir | 4 | 0x002a | 0x27 | 1 |
|  | 2 | inRoom, inDoorArray | 5 | 0x0029 | 0x4C | 1 |
|  | 3 | inRoom, inDoor, inType | 4 | 0x002a | 0x27 | 1 |
|  | 1 | inRoom | 2 | 0x002a | 0x70 | 1 |
|  | 1 | inDoor | 2 | 0x002a | 0x0F | 1 |
|  | 2 | inRoom, myType | 4 | 0x002a | 0xA6 | 1 |
|  | 2 | inRoom, inSpawnArray | 5 | 0x0029 | 0x4B | 1 |
|  | 8 | inRoom, inSpawner, UNUSED, inUnit, inTrigger, inTimer, inActive, inFaction | 8 | 0x002a | 0xC8 | 1 |
|  | 2 | inRoom, myType | 4 | 0x002a | 0x9B | 1 |
|  | 2 | inRoom, inActArray | 5 | 0x0029 | 0x4A | 1 |
|  | 5 | inRoom, inActivator, UNUSED, inTarget, inAction | 6 | 0x002a | 0x98 | 1 |
|  | 2 | inRoom, myType | 4 | 0x002a | 0x72 | 1 |
|  | 2 | inRoom, inObstArray | 5 | 0x0029 | 0x4A | 1 |
|  | 4 | inTarget, inType, inRequired, inHidden | 5 | 0x002a | 0x4C | 1 |
|  | 3 | inThing, inObjective, inReaction | - | - | 0x00 | 1 |
|  | 2 | inTarget, inType | 5 | 0x002a | 0xC2 | 1 |
|  | 7 | inRoom, inChar, inFaction, inLoadout, inLevel, inSurprised, inTotalGuys | 11 | 0x0029 | 0x00 | 1 |
|  | 3 | inRoom, inChar, inSurprised | 4 | 0x002a | 0x42 | 1 |
|  | 2 | inRoom, inChar | 4 | 0x002a | 0x70 | 1 |
|  | 5 | inRoom, inCreateArray, inFaction, inLoadout, inLevel | 9 | 0x002a | 0xDB | 1 |
|  | 2 | inRoom, inRoster | 4 | 0x002a | 0x70 | 1 |
|  | 2 | inTarget, inItem | 3 | 0x002a | 0x3A | 1 |
|  | 3 | inRoom, inLocker, inWeapons | 6 | 0x0029 | 0x79 | 1 |
|  | 2 | inStart, inChance | 4 | 0x0029 | 0x16 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x0A | 1 |
|  | 2 | inTrack, inDestination | 3 | 0x002a | 0x0B | 1 |
|  | 0 | - | 2 | 0x006a | 0x08 | 1 |
|  | 0 | - | - | - | 0x79 | 1 |
|  | 0 | - | - | - | 0xED | 1 |
|  | 0 | - | - | - | 0x1D | 1 |
|  | 0 | - | - | - | 0x14 | 1 |
|  | 0 | - | 2 | 0x006a | 0x28 | 1 |
|  | 0 | - | 2 | 0x006a | 0x0A | 1 |
|  | 0 | - | - | - | 0xC6 | 1 |
|  | 0 | - | - | - | 0x87 | 1 |
|  | 0 | - | - | - | 0x30 | 1 |
|  | 0 | - | - | - | 0x8E | 1 |
|  | 0 | - | - | - | 0x90 | 1 |
|  | 0 | - | - | - | 0xFA | 1 |
|  | 0 | - | - | - | 0xCB | 1 |
|  | 0 | - | - | - | 0xAF | 1 |
|  | 0 | - | - | - | 0xFE | 1 |
|  | 0 | - | - | - | 0x4E | 1 |
|  | 0 | - | - | - | 0xC3 | 1 |
|  | 0 | - | - | - | 0x6E | 1 |
|  | 0 | - | - | - | 0x60 | 1 |
|  | 0 | - | - | - | 0x72 | 1 |
|  | 0 | - | - | - | 0x86 | 1 |
|  | 0 | - | 2 | 0x002a | 0x36 | 1 |
|  | 0 | - | - | - | 0x5D | 1 |
|  | 0 | - | 2 | 0x002a | 0x74 | 1 |
|  | 0 | - | - | - | 0x94 | 1 |
|  | 0 | - | - | - | 0x42 | 1 |
|  | 0 | - | - | - | 0xAB | 1 |
|  | 0 | - | - | - | 0xF7 | 1 |
|  | 0 | - | - | - | 0x6F | 1 |
|  | 0 | - | 2 | 0x002a | 0x2A | 1 |
|  | 0 | - | - | - | 0xD5 | 1 |
|  | 0 | - | - | - | 0x45 | 1 |
|  | 0 | - | - | - | 0x2A | 1 |
|  | 0 | - | - | - | 0xB1 | 1 |
|  | 0 | - | 2 | 0x006a | 0xF5 | 1 |
|  | 0 | - | - | - | 0x70 | 1 |
|  | 0 | - | 2 | 0x002a | 0x86 | 1 |
|  | 0 | - | - | - | 0xF6 | 1 |
|  | 0 | - | - | - | 0x52 | 1 |
|  | 0 | - | - | - | 0x68 | 1 |
|  | 0 | - | - | - | 0x39 | 1 |
|  | 0 | - | - | - | 0x75 | 1 |
|  | 0 | - | - | - | 0x40 | 1 |
|  | 0 | - | - | - | 0x65 | 1 |
|  | 0 | - | - | - | 0x31 | 1 |
|  | 0 | - | - | - | 0x3B | 1 |
|  | 0 | - | 2 | 0x006a | 0xC7 | 1 |
|  | 0 | - | 4 | 0x002a | 0xDB | 1 |
|  | 0 | - | - | - | 0x1F | 1 |
|  | 0 | - | 2 | 0x006a | 0x5E | 1 |
|  | 0 | - | 2 | 0x006a | 0x27 | 1 |
|  | 2 | inChar, inEvent | 3 | 0x002a | 0x70 | 1 |
|  | 1 | inDataRef | 5 | 0x0029 | 0x3E | 1 |
|  | 0 | - | 2 | 0x0029 | 0x1B | 1 |
|  | 0 | - | 3 | 0x006a | 0xA1 | 1 |
|  | 2 | inTimer, inYesFunction | 4 | 0x002a | 0xBC | 1 |
|  | 9 | inType, inText, inChar, inStickX, inStickY, inLinkedItem, inTimer, inYesFunction, inNoFunction | 11 | 0x002a | 0xEE | 1 |
|  | 0 | - | - | - | 0x34 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xE9 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x8F | 1 |
|  | 1 | inPlayerPressedYesManually | 3 | 0x0029 | 0x4C | 1 |
|  | 1 | inSource | 3 | 0x0029 | 0x89 | 1 |
|  | 0 | - | 2 | 0x006a | 0x90 | 1 |
|  | 1 | inSlot | 4 | 0x0029 | 0xAD | 1 |
|  | 1 | inSlot | 9 | 0x0029 | 0xBE | 1 |
|  | 1 | inSlot | 8 | 0x0029 | 0x5A | 1 |
|  | 0 | - | 5 | 0x0029 | 0x36 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x99 | 1 |
|  | 1 | inDiff | 3 | 0x0029 | 0x33 | 1 |
|  | 0 | - | 2 | 0x002a | 0xDE | 1 |
|  | 0 | - | 8 | 0x0069 | 0x92 | 1 |
|  | 1 | inCard | 4 | 0x0069 | 0xA2 | 1 |
|  | 1 | inCash | 2 | 0x002a | 0x0A | 1 |
|  | 2 | inLoc, inData | 9 | 0x002a | 0x2E | 1 |
|  | 2 | inBar, inValue | 5 | 0x002a | 0x7A | 1 |
|  | 3 | inCard, inData, inAddTeam | 4 | 0x006a | 0xD4 | 1 |
|  | 1 | inCard | - | - | 0x00 | 1 |
|  | 0 | - | 6 | 0x0069 | 0xEF | 1 |
|  | 0 | - | 12 | 0x0069 | 0xE9 | 1 |
|  | 0 | - | 19 | 0x0069 | 0x17 | 1 |
|  | 1 | inData | 3 | 0x0029 | 0x2C | 1 |
|  | 1 | inCard | 3 | 0x0029 | 0x54 | 1 |
|  | 1 | inChar | 4 | 0x0029 | 0x75 | 1 |
|  | 1 | inCard | 2 | 0x002a | 0xB6 | 1 |
|  | 1 | inSprite | 3 | 0x0029 | 0x39 | 1 |
|  | 2 | inCard, inWeapon | 4 | 0x0069 | 0x70 | 1 |
|  | 1 | inPortrait | 3 | 0x0029 | 0x3C | 1 |
|  | 0 | - | 2 | 0x0029 | 0xA9 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x4F | 1 |
|  | 1 | inCat | 3 | 0x0029 | 0x7B | 1 |
|  | 0 | - | 3 | 0x0069 | 0x37 | 1 |
|  | 0 | - | 5 | 0x0029 | 0xC0 | 1 |
|  | 1 | inIcon | 3 | 0x0029 | 0x2A | 1 |
|  | 1 | inIcon | 3 | 0x0029 | 0x6E | 1 |
|  | 0 | - | 2 | 0x002a | 0x63 | 1 |
|  | 0 | - | 18 | 0x002a | 0x33 | 1 |
|  | 1 | inType | 3 | 0x002a | 0x2B | 1 |
|  | 2 | inType, silencer | 4 | 0x002a | 0xD8 | 1 |
|  | 1 | inWeapon | 2 | 0x002a | 0x84 | 1 |
|  | 1 | inWeapon | 2 | 0x002a | 0x56 | 1 |
|  | 1 | inWeapon | 3 | 0x002a | 0xD5 | 1 |
|  | 3 | inChar, inItem, inCat | - | - | 0x06 | 1 |
|  | 2 | inItem, inCat | - | - | 0x00 | 1 |
|  | 0 | - | 2 | 0x002a | 0xDB | 1 |
|  | 3 | inChar, inAttack, inDashPerk | 4 | 0x002a | 0x41 | 1 |
|  | 2 | inSprite, inWeapon | 3 | 0x002a | 0xFC | 1 |
|  | 3 | inChar, inLoadout, inLevel | 18 | 0x002a | 0xAA | 1 |
|  | 1 | inType | 4 | 0x002a | 0x83 | 1 |
|  | 2 | inCat, inUpgrade | 3 | 0x002a | 0x50 | 1 |
|  | 2 | inLevel, inWave | 4 | 0x002a | 0xEA | 1 |
|  | 2 | inChar, inLvl | 8 | 0x002a | 0xCB | 1 |
|  | 3 | inTrans, inAction, inObj | 5 | 0x0029 | 0x32 | 1 |
|  | 0 | - | 3 | 0x0069 | 0xBB | 1 |
|  | 1 | inName | 3 | 0x006a | 0xE0 | 1 |
|  | 3 | inPlaceholder, inDataRef, inAutoDelete | 5 | 0x0029 | 0x73 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x3E | 1 |
|  | 0 | - | 3 | 0x0069 | 0xD3 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x14 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xBC | 1 |
|  | 0 | - | 2 | 0x0029 | 0xDD | 1 |
|  | 0 | - | 2 | 0x0029 | 0x1A | 1 |
|  | 0 | - | 2 | 0x0029 | 0x7D | 1 |
|  | 0 | - | 3 | 0x0019 | 0x78 | 1 |
|  | 1 | inStartRef | 17 | 0x0069 | 0x21 | 1 |
|  | 0 | - | 9 | 0x0069 | 0x5F | 1 |
|  | 2 | inX, inY | 5 | 0x0029 | 0xF9 | 1 |
|  | 1 | inMC | - | - | 0x00 | 1 |
|  | 8 | inMC, inRotOffset, inLength, inTargX, inTargY, inX, inY, inTracer | 16 | 0x0029 | 0xDC | 1 |
|  | 5 | inStartX, inStartY, inDistance, inAngle, inTarget | 8 | 0x0069 | 0x2C | 1 |
|  | 6 | inX, inY, inEffect, inScaleLow, inScaleHigh, inRotation | 9 | 0x0029 | 0x9F | 1 |
|  | 2 | inObject, inTarget | 5 | 0x0029 | 0x9A | 1 |
|  | 15 | inType, inCategory, inX, inY, inXSpeed, inYSpeed, inRot, inRotSpeed, inBounce, inFloor, inAlpha, inScale, inStanding, inStandRot, inDataRef | 18 | 0x0029 | 0x75 | 1 |
|  | 4 | inX, inY, inType, inRot | 7 | 0x0029 | 0xD0 | 1 |
|  | 1 | inChar | 3 | 0x0029 | 0x2F | 1 |
|  | 4 | inChar, inDoor, inX, inY | 8 | 0x0069 | 0xDC | 1 |
|  | 0 | - | 3 | 0x0069 | 0xC3 | 1 |
|  | 0 | - | 2 | 0x006a | 0xBD | 1 |
|  | 0 | - | 3 | 0x0069 | 0x67 | 1 |
|  | 0 | - | 8 | 0x0069 | 0xA8 | 1 |
|  | 0 | - | 5 | 0x006a | 0x31 | 1 |
|  | 0 | - | 5 | 0x0069 | 0x1F | 1 |
|  | 1 | inRoster | 4 | 0x002a | 0x15 | 1 |
|  | 1 | inFac | 3 | 0x002a | 0x6C | 1 |
|  | 0 | - | 3 | 0x0029 | 0x10 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xB2 | 1 |
|  | 1 | inRoster | 2 | 0x002a | 0x9A | 1 |
|  | 1 | inNum | 3 | 0x0029 | 0x1B | 1 |
|  | 4 | inX, inY, inScale, inGun | 6 | 0x0029 | 0x7B | 1 |
|  | 2 | inSource, inTarget | 6 | 0x0029 | 0x67 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x4E | 1 |
|  | 1 | inStartPoint | 9 | 0x0029 | 0x9A | 1 |
|  | 0 | - | - | - | 0x1A | 1 |
|  | 1 | inFaction | 3 | 0x002a | 0x66 | 1 |
|  | 0 | - | 2 | 0x002a | 0xAD | 1 |
|  | 1 | inFreeze | 2 | 0x002a | 0x15 | 1 |
|  | 1 | inX | 2 | 0x002a | 0x8D | 1 |
|  | 1 | inRoster | 3 | 0x0029 | 0x5F | 1 |
|  | 1 | inFaction | 2 | 0x002a | 0x1A | 1 |
|  | 0 | - | 3 | 0x0019 | 0x32 | 1 |
|  | 2 | inPlaceholder, inDataRef | 5 | 0x0029 | 0x29 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x5A | 1 |
|  | 1 | inType | - | - | 0x00 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xF8 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x81 | 1 |
|  | 1 | inDamage | 3 | 0x0029 | 0x13 | 1 |
|  | 5 | inX, inY, inType, inVariant, inRot | 9 | 0x0029 | 0x11 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xB6 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x10 | 1 |
|  | 3 | inX, inY, inWidth | 5 | 0x002a | 0x72 | 1 |
|  | 2 | inPlaceholder, inDataRef | 4 | 0x0029 | 0x60 | 1 |
|  | 0 | - | 5 | 0x0029 | 0xD0 | 1 |
|  | 0 | - | 5 | 0x0029 | 0xF9 | 1 |
|  | 2 | inItem, inX | 4 | 0x0029 | 0x66 | 1 |
|  | 0 | - | 5 | 0x0029 | 0x66 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x02 | 1 |
|  | 15 | inType, inCategory, inX, inY, inXSpeed, inYSpeed, inRot, inRotSpeed, inBounce, inFloor, inAlpha, inScale, inStanding, inStandRot, inDataRef | 19 | 0x0029 | 0x6B | 1 |
|  | 0 | - | 11 | 0x0069 | 0xAA | 1 |
|  | 1 | inDestination | 3 | 0x0029 | 0x00 | 1 |
|  | 0 | - | 5 | 0x0029 | 0x2B | 1 |
|  | 1 | inPickup | 3 | 0x002a | 0x4E | 1 |
|  | 1 | inArray | 4 | 0x0029 | 0x60 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x6E | 1 |
|  | 5 | inChar, inWeapon, headHit, hitX, hitY | 8 | 0x0029 | 0x4C | 1 |
|  | 2 | inScorch, inAutoHit | 12 | 0x0029 | 0xCE | 1 |
|  | 2 | inWeapon, inSource | 4 | 0x0029 | 0x61 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x2B | 1 |
|  | 0 | - | 2 | 0x0029 | 0x7C | 1 |
|  | 0 | - | 4 | 0x0029 | 0xC8 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xE1 | 1 |
|  | 0 | - | 3 | 0x0069 | 0x89 | 1 |
|  | 3 | inCutscene, inAction, inObject | 4 | 0x002a | 0x2A | 1 |
|  | 0 | - | 2 | 0x002a | 0xD1 | 1 |
|  | 0 | - | 3 | 0x0019 | 0xFA | 1 |
|  | 2 | keyName, keyNum | 3 | 0x002a | 0x57 | 1 |
|  | 0 | - | 2 | 0x002a | 0xB3 | 1 |
|  | 0 | - | 2 | 0x002a | 0x41 | 1 |
|  | 1 | inKey | 2 | 0x002a | 0x17 | 1 |
|  | 0 | - | 3 | 0x0069 | 0x58 | 1 |
|  | 1 | inMode | 4 | 0x0069 | 0xA4 | 1 |
|  | 1 | inChar | 16 | 0x002a | 0x34 | 1 |
|  | 2 | inChar, inSkill | 4 | 0x002a | 0x41 | 1 |
|  | 2 | inChar, inEquipped | 4 | 0x002a | 0x7A | 1 |
|  | 2 | inChar, inEquipped | 4 | 0x002a | 0x77 | 1 |
|  | 0 | - | - | - | 0x4A | 1 |
|  | 2 | inCount, inRatio | 4 | 0x002a | 0xAB | 1 |
|  | 0 | - | 4 | 0x0029 | 0xAB | 1 |
|  | 2 | inWorld, inStages | 5 | 0x0029 | 0xE4 | 1 |
|  | 1 | inWorld | - | - | 0x00 | 1 |
|  | 0 | - | 2 | 0x006a | 0xCC | 1 |
|  | 2 | inWorld, inLevel | 5 | 0x0069 | 0xAD | 1 |
|  | 1 | inStartWave | 3 | 0x006a | 0x5E | 1 |
|  | 2 | inLevel, inRollOver | 10 | 0x0029 | 0xBA | 1 |
|  | 2 | inLevel, inHi | 11 | 0x0029 | 0x01 | 1 |
|  | 1 | inWorld | 3 | 0x0029 | 0x3D | 1 |
|  | 1 | value | 4 | 0x0029 | 0xAA | 1 |
|  | 0 | - | - | - | 0x13 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x44 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x3B | 1 |
|  | 4 | command, completeHandler, parameters, secureParameters | 7 | 0x0029 | 0xB0 | 1 |
|  | 1 | command | 3 | 0x0029 | 0x10 | 1 |
|  | 3 | command, newWindow, parameters | 6 | 0x0029 | 0x6D | 1 |
|  | 2 | type, listener | 6 | 0x0029 | 0x8A | 1 |
|  | 2 | type, listener | 7 | 0x0029 | 0xA3 | 1 |
|  | 1 | event | 7 | 0x0029 | 0x97 | 1 |
|  | 1 | type | 3 | 0x0029 | 0x0A | 1 |
|  | 1 | value | 2 | 0x002a | 0x3D | 1 |
|  | 0 | - | - | - | 0x37 | 1 |
|  | 1 | event | 4 | 0x0029 | 0x3B | 1 |
|  | 1 | event | 5 | 0x0019 | 0x7C | 1 |
|  | 1 | event | 5 | 0x002a | 0xC5 | 1 |
|  | 1 | hash | 4 | 0x0029 | 0xBF | 1 |
|  | 2 | number, minimumChars | 6 | 0x0029 | 0xD3 | 1 |
|  | 1 | encodedNumber | 5 | 0x0029 | 0x79 | 1 |
|  | 1 | command | 4 | 0x0019 | 0x4D | 1 |
|  | 0 | - | 3 | 0x002a | 0x8D | 1 |
|  | 1 | event | 2 | 0x002a | 0x54 | 1 |
|  | 1 | hexValue | 5 | 0x002a | 0xB7 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x3D | 1 |
|  | 4 | filename, data, dataField, contentType | 7 | 0x0029 | 0x68 | 1 |
|  | 1 | filename | 3 | 0x0029 | 0x1D | 1 |
|  | 0 | - | 3 | 0x0029 | 0xCD | 1 |
|  | 2 | connection, newWindow | 8 | 0x0069 | 0x25 | 1 |
|  | 1 | connection | 4 | 0x0029 | 0x82 | 1 |
|  | 1 | connection | 14 | 0x0029 | 0x14 | 1 |
|  | 3 | url, data, contentType | 5 | 0x0029 | 0x90 | 1 |
|  | 1 | data | 5 | 0x0029 | 0xB9 | 1 |
|  | 1 | event | 2 | 0x0029 | 0x88 | 1 |
|  | 1 | error | 3 | 0x0029 | 0x8A | 1 |
|  | 1 | data | 4 | 0x0029 | 0x12 | 1 |
|  | 1 | id | 5 | 0x0029 | 0xC6 | 1 |
|  | 1 | event | 3 | 0x0029 | 0x47 | 1 |
|  | 2 | command, parameters | 5 | 0x0029 | 0x42 | 1 |
|  | 2 | event, parameters | - | - | 0x00 | 1 |
|  | 1 | event | - | - | 0x00 | 1 |
|  | 3 | type, data, error | 6 | 0x0019 | 0xE4 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x39 | 1 |
|  | 1 | val | 2 | 0x002a | 0x3D | 1 |
|  | 1 | eventType | 2 | 0x002a | 0x98 | 1 |
|  | 4 | _root, apiId, encryptionKey, movieVersion | 6 | 0x006a | 0x64 | 1 |
|  | 1 | flashVars | 5 | 0x002a | 0xA9 | 1 |
|  | 1 | event | 7 | 0x002a | 0x9A | 1 |
|  | 1 | event | 22 | 0x002a | 0x07 | 1 |
|  | 0 | - | 3 | 0x002a | 0xB2 | 1 |
|  | 0 | - | - | - | 0x55 | 1 |
|  | 0 | - | - | - | 0x53 | 1 |
|  | 1 | linkName | 3 | 0x002a | 0x62 | 1 |
|  | 1 | medalName | 2 | 0x002a | 0x1F | 1 |
|  | 1 | medalName | 3 | 0x002a | 0x9F | 1 |
|  | 1 | event | 4 | 0x002a | 0x11 | 1 |
|  | 1 | event | 3 | 0x002a | 0x0D | 1 |
|  | 0 | - | 3 | 0x002a | 0xC0 | 1 |
|  | 1 | scoreBoardName | 2 | 0x002a | 0x4C | 1 |
|  | 5 | scoreBoardName, period, firstResult, numResults, tag | 7 | 0x002a | 0x95 | 1 |
|  | 3 | scoreBoardName, numericScore, tag | 5 | 0x002a | 0xA0 | 1 |
|  | 1 | groupName | 2 | 0x002a | 0x4C | 1 |
|  | 1 | id | 4 | 0x002a | 0x8C | 1 |
|  | 1 | groupName | 3 | 0x002a | 0xA8 | 1 |
|  | 2 | saveId, loadContents | 5 | 0x002a | 0x66 | 1 |
|  | 1 | event | 3 | 0x002a | 0x77 | 1 |
|  | 1 | groupName | 4 | 0x002a | 0xB3 | 1 |
|  | 2 | groupName, sortDescending | 4 | 0x002a | 0x7D | 1 |
|  | 4 | groupName, filename, exactMatch, sortDescending | 6 | 0x002a | 0xC6 | 1 |
|  | 3 | groupName, ratingName, sortDescending | 5 | 0x002a | 0x54 | 1 |
|  | 1 | event | 3 | 0x002a | 0xBF | 1 |
|  | 4 | eventType, listener, priority, useWeakReference | 5 | 0x002a | 0x63 | 1 |
|  | 2 | eventType, listener | 3 | 0x002a | 0x28 | 1 |
|  | 3 | event, data, error | 4 | 0x002a | 0x6D | 1 |
|  | 2 | saveId, saveData | 5 | 0x002a | 0x93 | 1 |
|  | 1 | saveId | 4 | 0x002a | 0xC7 | 1 |
|  | 1 | eventName | 3 | 0x002a | 0x84 | 1 |
|  | 1 | data | 2 | 0x002a | 0xA7 | 1 |
|  | 1 | data | 2 | 0x002a | 0xE8 | 1 |
|  | 1 | string | 4 | 0x002a | 0xC6 | 1 |
|  | 2 | hashLength, charsPerPixel | 4 | 0x0029 | 0x93 | 1 |
|  | 1 | v | 3 | 0x0029 | 0x91 | 1 |
|  | 3 | source, callbackFunction, callbackObject | 12 | 0x0029 | 0x08 | 1 |
|  | 3 | source, callbackFunction, callbackObject | 13 | 0x0029 | 0xDE | 1 |
|  | 1 | state | 4 | 0x0029 | 0x33 | 1 |
|  | 1 | state | 5 | 0x0029 | 0x66 | 1 |
|  | 1 | pixel | 8 | 0x0029 | 0x3F | 1 |
|  | 1 | encodedPixel | 9 | 0x0029 | 0x0F | 1 |
|  | 1 | group | 4 | 0x0019 | 0x74 | 1 |
|  | 2 | group, fileData | 10 | 0x002a | 0xB5 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x5E | 1 |
|  | 1 | v | 3 | 0x0029 | 0x1D | 1 |
|  | 1 | v | 3 | 0x0029 | 0x23 | 1 |
|  | 1 | source | 11 | 0x0029 | 0x69 | 1 |
|  | 1 | parent | 3 | 0x0029 | 0x49 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x5B | 1 |
|  | 1 | encodedIcon | 3 | 0x0029 | 0x1A | 1 |
|  | 0 | - | 13 | 0x0029 | 0x49 | 1 |
|  | 1 | encode | 3 | 0x0029 | 0x6F | 1 |
|  | 2 | parent, property | 9 | 0x0029 | 0x88 | 1 |
|  | 0 | - | 11 | 0x0029 | 0xF1 | 1 |
|  | 1 | data | 3 | 0x0029 | 0x28 | 1 |
|  | 0 | - | 4 | 0x0029 | 0x0B | 1 |
|  | 1 | event | 3 | 0x0029 | 0x9D | 1 |
|  | 1 | data | 3 | 0x0029 | 0x38 | 1 |
|  | 1 | error | 3 | 0x0029 | 0x79 | 1 |
|  | 1 | event | 3 | 0x0029 | 0x74 | 1 |
|  | 2 | ratingName, vote | 10 | 0x0029 | 0x76 | 1 |
|  | 1 | event | 5 | 0x0029 | 0x6A | 1 |
|  | 0 | - | 4 | 0x0029 | 0x14 | 1 |
|  | 6 | connection, name, id, type, keys, ratings | 13 | 0x0029 | 0x0B | 1 |
|  | 3 | name, id, type | 5 | 0x0029 | 0x1E | 1 |
|  | 1 | value | 4 | 0x0029 | 0x93 | 1 |
|  | 5 | name, id, isFloat, minimum, maximum | 7 | 0x0029 | 0x32 | 1 |
|  | 1 | value | 5 | 0x0029 | 0x95 | 1 |
|  | 2 | defaultBitmap, url | 5 | 0x0019 | 0x25 | 1 |
|  | 0 | - | 3 | 0x0069 | 0x74 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x95 | 1 |
|  | 1 | parent | 7 | 0x0069 | 0x95 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x6A | 1 |
|  | 1 | group | 4 | 0x0019 | 0x3A | 1 |
|  | 1 | val | 3 | 0x0029 | 0x46 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xB4 | 1 |
|  | 0 | - | 3 | 0x0029 | 0xDD | 1 |
|  | 0 | - | 6 | 0x0029 | 0xF8 | 1 |
|  | 3 | field, operator, value | 12 | 0x0029 | 0x76 | 1 |
|  | 2 | field, sortDescending | 11 | 0x0029 | 0xA7 | 1 |
|  | 0 | - | 7 | 0x0029 | 0xD0 | 1 |
|  | 1 | event | 6 | 0x0029 | 0xA4 | 1 |
|  | 9 | connection, id, name, description, secret, unlocked, value, difficultyId, iconURL | 12 | 0x0019 | 0xC8 | 1 |
|  | 1 | parent | 3 | 0x0029 | 0x16 | 1 |
|  | 0 | - | 5 | 0x0029 | 0x2A | 1 |
|  | 1 | unlocked | 3 | 0x0029 | 0x0A | 1 |
|  | 1 | event | 3 | 0x0029 | 0xDC | 1 |
|  | 3 | connection, name, id | 6 | 0x0019 | 0x2F | 1 |
|  | 0 | - | 10 | 0x0029 | 0x93 | 1 |
|  | 2 | numericScore, tag | 9 | 0x0029 | 0x53 | 1 |
|  | 1 | event | 7 | 0x0029 | 0x56 | 1 |
|  | 1 | event | 5 | 0x0029 | 0xFD | 1 |
|  | 2 | priority, messages | 4 | 0x002a | 0x4E | 1 |
|  | 2 | event, listener | 3 | 0x002a | 0x35 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x34 | 1 |
|  | 0 | - | 4 | 0x0029 | 0xF5 | 1 |
|  | 0 | - | 5 | 0x0029 | 0x01 | 1 |
|  | 0 | - | 3 | 0x0029 | 0x5C | 1 |
|  | 0 | - | 2 | 0x0029 | 0xD1 | 1 |
|  | 0 | - | 2 | 0x0029 | 0xAF | 1 |
|  | 0 | - | 2 | 0x006a | 0x5D | 1 |
|  | 0 | - | - | - | 0x32 | 1 |
|  | 0 | - | 6 | 0x0019 | 0xE9 | 1 |
|  | 3 | target, error, httpStatus | 4 | 0x002a | 0x1A | 1 |
|  | 1 | v | 3 | 0x0029 | 0x51 | 1 |
|  | 1 | value | 4 | 0x0029 | 0xC9 | 1 |
|  | 1 | event | 3 | 0x0029 | 0xA2 | 1 |
|  | 1 | data | 3 | 0x0029 | 0x43 | 1 |
|  | 1 | adURL | 3 | 0x0029 | 0xD7 | 1 |
|  | 3 | target, error, httpStatus | 2 | 0x0029 | 0x32 | 1 |
|  | 0 | - | - | - | 0x22 | 1 |
|  | 5 | rank, username, score, numericValue, tag | 7 | 0x0029 | 0x46 | 1 |
|  | 0 | - | 2 | 0x0029 | 0x27 | 1 |
|  | 0 | - | 17 | 0x0069 | 0x27 | 1 |
|  | 1 | inCat | 9 | 0x0029 | 0x12 | 1 |
|  | 1 | inItem | 3 | 0x0029 | 0x3C | 1 |
|  | 0 | - | 2 | 0x0029 | 0x8E | 1 |
|  | 0 | - | 3 | 0x0069 | 0x61 | 1 |
|  | 1 | inCat | 3 | 0x0029 | 0x24 | 1 |
|  | 2 | inCat, inTeamActive | 7 | 0x006a | 0x00 | 1 |
|  | 1 | src | 2 | 0x002a | 0x26 | 1 |
|  | 1 | src | 2 | 0x002a | 0x7D | 1 |
|  | 2 | x, len | 12 | 0x002a | 0xC3 | 1 |
|  | 6 | q, a, b, x, s, t | 7 | 0x002a | 0xBC | 1 |
|  | 7 | a, b, c, d, x, s, t | 8 | 0x002a | 0x4C | 1 |
|  | 7 | a, b, c, d, x, s, t | 8 | 0x002a | 0x49 | 1 |
|  | 7 | a, b, c, d, x, s, t | 8 | 0x002a | 0x3C | 1 |
|  | 7 | a, b, c, d, x, s, t | 8 | 0x002a | 0x43 | 1 |
|  | 2 | num, cnt | 3 | 0x002a | 0x18 | 1 |
|  | 2 | x, y | 5 | 0x002a | 0x5C | 1 |
|  | 1 | str | 5 | 0x002a | 0xAE | 1 |
|  | 1 | binarray | 5 | 0x002a | 0xE9 | 1 |
|  | 2 | src, key | 6 | 0x002a | 0x86 | 1 |
|  | 1 | pwd | 6 | 0x002a | 0xCD | 1 |
|  | 2 | plaintxt, psw | 11 | 0x002a | 0x34 | 1 |
|  | 1 | chars | 5 | 0x002a | 0xAB | 1 |
|  | 1 | hex | 4 | 0x002a | 0xB6 | 1 |
|  | 1 | chars | 4 | 0x002a | 0x6B | 1 |
|  | 1 | str | 4 | 0x002a | 0x69 | 1 |
|  | 2 | arg, noquotes | 10 | 0x002a | 0xA2 | 1 |
|  | 2 | arg, callback | 10 | 0x002a | 0x73 | 1 |
|  | 2 | arg, callback | 11 | 0x002a | 0xB0 | 1 |
|  | 1 | text | 13 | 0x002a | 0x35 | 1 |
|  | 1 | m | 6 | 0x002a | 0x2B | 1 |
|  | 0 | - | - | - | 0x33 | 1 |
|  | 0 | - | - | - | 0x6C | 1 |
|  | 0 | - | 6 | 0x002a | 0x66 | 1 |
|  | 0 | - | 2 | 0x002a | 0x1D | 1 |
|  | 0 | - | 3 | 0x002a | 0x69 | 1 |
|  | 0 | - | 3 | 0x002a | 0x38 | 1 |
|  | 0 | - | - | - | 0xAE | 1 |
|  | 0 | - | - | - | 0xDC | 1 |
|  | 1 | v | 2 | 0x002a | 0x21 | 1 |
|  | 0 | - | 3 | 0x002a | 0x3F | 1 |
|  | 0 | - | 4 | 0x002a | 0xCA | 1 |
|  | 0 | - | - | - | 0x05 | 1 |
|  | 0 | - | 3 | 0x002a | 0xD5 | 1 |
|  | 0 | - | 4 | 0x002a | 0x69 | 1 |
| _addArrayKey | 0 | - | 2 | 0x002a | 0x83 | 1 |
| _addParent | 1 | child | 2 | 0x002a | 0x38 | 1 |
| _apiConnect | 0 | - | 3 | 0x006a | 0x5F | 1 |
| _array | 0 | - | 2 | 0x002a | 0x61 | 1 |
| _boolean | 0 | - | 2 | 0x002a | 0x70 | 1 |
| _getCurrent | 0 | - | 5 | 0x002a | 0xFB | 1 |
| _getParent | 0 | - | 5 | 0x002a | 0x04 | 1 |
| _null | 0 | - | 2 | 0x002a | 0xF4 | 1 |
| _number | 0 | - | 3 | 0x002a | 0x0E | 1 |
| _object | 0 | - | 2 | 0x002a | 0xAF | 1 |
| _onConnected | 1 | event | 2 | 0x002a | 0xD7 | 1 |
| _onItemClick | 0 | - | 4 | 0x00a9 | 0x9C | 1 |
| _onListChange | 1 | selection | 2 | 0x002a | 0x1B | 1 |
| _onListClick | 0 | - | - | - | 0x31 | 1 |
| _onLoaded | 0 | - | - | - | 0x40 | 1 |
| _onPageClick | 0 | - | 3 | 0x0029 | 0x75 | 1 |
| _onPlayClick | 0 | - | 3 | 0x00ea | 0x36 | 1 |
| _onScoresLoaded | 1 | event | 2 | 0x002a | 0x52 | 1 |
| _setTargetValue | 1 | newval | 4 | 0x002a | 0x8D | 1 |
| _string | 0 | - | 2 | 0x002a | 0x4C | 1 |
| _useParent | 0 | - | - | - | 0x9F | 1 |
| arenaTick | 0 | - | 2 | 0x0029 | 0x4E | 1 |
| createCutscene | 0 | - | 2 | 0x002a | 0x35 | 1 |
| createGameMenu | 0 | - | 2 | 0x002a | 0x35 | 1 |
| createHireStore | 0 | - | 2 | 0x002a | 0x49 | 1 |
| createItemStore | 0 | - | 2 | 0x002a | 0x49 | 1 |
| createMainMenu | 0 | - | 2 | 0x002a | 0x35 | 1 |
| createMicroMenu | 1 | inGameMode | 2 | 0x002a | 0x4D | 1 |
| createNewGuy | 0 | - | 2 | 0x002a | 0x35 | 1 |
| createRoom | 0 | - | 2 | 0x002a | 0x4B | 1 |
| createTeamSetup | 0 | - | 2 | 0x002a | 0x49 | 1 |
| createTransition | 3 | inTrans, inAction, inObj | 5 | 0x002a | 0x53 | 1 |
| createWorldMap | 0 | - | 2 | 0x002a | 0x49 | 1 |
| createWound | 1 | inNumber | 3 | 0x0029 | 0x31 | 6 |
| createWound | 1 | inNumber | - | - | 0x00 | 2 |
| cutsceneDone | 0 | - | - | - | 0x1D | 1 |
| enterFrameHandler | 0 | - | 3 | 0x006a | 0x9C | 1 |
| exitAll | 0 | - | - | - | 0x60 | 1 |
| exitHireStore | 0 | - | - | - | 0x1D | 1 |
| exitItemStore | 0 | - | - | - | 0x1D | 1 |
| exitMainMenu | 0 | - | - | - | 0x1D | 1 |
| exitNewGuy | 0 | - | - | - | 0x1D | 1 |
| exitTeamSetup | 0 | - | - | - | 0x1D | 1 |
| exitWorldMap | 0 | - | - | - | 0x1D | 1 |
| forceAlwaysOnTop | 0 | - | 3 | 0x006a | 0xC9 | 1 |
| generateArena | 1 | inStartWave | 3 | 0x002a | 0x24 | 1 |
| generateLevel | 2 | inWorld, inLevel | 4 | 0x002a | 0x26 | 1 |
| hideList | 0 | - | - | - | 0x12 | 1 |
| initPlayButton | 0 | - | 2 | 0x0029 | 0x3E | 1 |
| loadScores | 0 | - | - | - | 0x3A | 1 |
| medalPopupEnterFrame | 0 | - | 3 | 0x00aa | 0xC4 | 1 |
| muteMusic | 0 | - | - | - | 0x00 | 1 |
| onMedalUnlocked | 1 | event | 2 | 0x002a | 0x4A | 1 |
| onPlayClick | 0 | - | - | - | 0x1D | 1 |
| onReloadClick | 0 | - | - | - | 0x10 | 1 |
| onScoreClick | 0 | - | 4 | 0x0069 | 0x46 | 1 |
| pickCreate | 0 | - | - | - | 0x20 | 1 |
| pickCutscene | 0 | - | - | - | 0x00 | 1 |
| pickItems | 1 | inEquip | 2 | 0x002a | 0x6C | 1 |
| pickMap | 0 | - | - | - | 0x20 | 1 |
| pickMenu | 0 | - | - | - | 0x20 | 1 |
| pickStore | 0 | - | - | - | 0x20 | 1 |
| pickTeam | 0 | - | - | - | 0x20 | 1 |
| removeGameMenu | 0 | - | - | - | 0x1D | 1 |
| removeMicroMenu | 0 | - | - | - | 0x1D | 1 |
| removeRoom | 0 | - | 2 | 0x006a | 0x35 | 1 |
| selectRosterCharacter | 1 | inChar | 3 | 0x006a | 0x3C | 1 |
| setListItems | 1 | listItems | 5 | 0x002a | 0xC7 | 1 |
| setSelectedIndex | 1 | i | 2 | 0x002a | 0x5F | 1 |
| setSelectedItem | 1 | data | 3 | 0x002a | 0x67 | 1 |
| showNextUnlock | 0 | - | - | - | 0x77 | 1 |
| tick | 0 | - | 3 | 0x00a9 | 0x44 | 168 |
| tick | 0 | - | 3 | 0x0069 | 0x44 | 21 |
| tick | 0 | - | 3 | 0x00a9 | 0x1C | 4 |
| tick | 0 | - | 3 | 0x0069 | 0x1C | 2 |
| tick | 0 | - | - | - | 0x6D | 1 |
| workaroundMedalUnlock | 1 | inName | 2 | 0x002a | 0x29 | 1 |

## Modelo de datos revelado por las firmas

### Combate (danos/arma/impacto)

 - EXPLOSION/DANOS (13 params, body=0x51):
   inType, inScorch, inSource, inX, inY, inFloor,
   inRange, inDamage, inSound, inKnockback, inDir,
   inAutoHit, inSubDeath
 - GOLPE DE ARMA (6 params, body=0x60):
   inWeapon, inAttacker, inHitX, inHitY,
   inRangeGood, inHeadshot
 - ATAQUE DE ARMA (5 params, body=0x4A):
   inWeapon, inAttacker, inBlock, inKillShot, inRange
 - MELEE (3 params, body=0x53): inMeleeDir, inMeleeType, inWeapon
 - DANOS (1 param, body=0x17): inDamage
 - BLAST (3 params, body=0x5A): inSource, inPower, inReverseBlast

### Estadisticas de personaje (15 params, body=0xC0)

  inStr, inDex, inTac, inEnd, inLead, inAwr, SPACER,
  inMelee, inUnarmed, inPistol, inRevolver, inSMG,
  inShotgun, inRifle, inHeavy
  (Str=Strength, Dex=Dexterity, Tac=Tactics,
   End=Endurance, Lead=Leadership, Awr=Awareness;
   + proficiencia por tipo de arma)

### Fisica de sprite (15 params)

  inType, inCategory, inX, inY, inXSpeed, inYSpeed,
  inRot, inRotSpeed, inBounce, inFloor, inAlpha,
  inScale, inStanding, inStandRot, inDataRef
  (posicion, velocidad, rotacion, rebote, piso,
   transparencia, escala, enPie)
