# SwainMath.randomNumber — convencion y correccion del danio

## Convencion (RXRE-SWF-052, PROVEN)

```text
SwainMath.randomNumber(precision, lo, hi)
    -> valor en [lo, hi], redondeado a `precision` decimales
```

Evidencia:

- **418** sitios de llamada en 1749 scripts
- **179** firmas distintas
- **101** llamadas con los 3 args enteros comparables
- **0** violaciones de `lo <= hi`

Patron dominante `randomNumber(2,-N,N)` -> `[-N,N]` simetrico.

### Firmas mas comunes (orden declarado)

| firma | # |
|---|---|
| `randomNumber(('2', '0'))` | 66 |
| `randomNumber(('2',))` | 20 |
| `randomNumber(('2', '0', '1'))` | 15 |
| `randomNumber(('2', '0', '2'))` | 10 |
| `randomNumber(('2', '-800', '800'))` | 9 |
| `randomNumber(('2', '-180', '180'))` | 7 |
| `randomNumber(('2', '0', '3'))` | 6 |
| `randomNumber(('2', '-300', '300'))` | 6 |
| `randomNumber(('2', '-15', '15'))` | 6 |
| `randomNumber(('2', 'r6', 'r4', 'r3'))` | 6 |
| `randomNumber(('2', '0', '5'))` | 5 |
| `randomNumber(('2', '-5', '5'))` | 5 |
| `randomNumber(('2', '1', '2', 'stun_parry', 'myStatus', 'r1'))` | 5 |
| `randomNumber(('2', '-100', '100'))` | 5 |
| `randomNumber(('2', '1', '6', 'melee_better', 'myStatus', 'r1'))` | 5 |
| `randomNumber(('2', '1', '6', 'melee_basic', 'myStatus', 'r1'))` | 5 |
| `randomNumber(('2', '1'))` | 5 |
| `randomNumber(('2', '-20', '20'))` | 5 |
| `randomNumber(('2', '1', '5'))` | 5 |
| `randomNumber(('2', '1', '3'))` | 4 |
| `randomNumber(('2', '1', '5', 'myVariant', 'r4'))` | 4 |
| `randomNumber(('2', '2'))` | 4 |
| `randomNumber(('2', '-900', '900', '1.8'))` | 4 |
| `randomNumber(('2', '-40', '40'))` | 4 |
| `randomNumber(('2', '-30', '30'))` | 4 |
| `randomNumber(('2', '-2', '2'))` | 3 |
| `randomNumber(('2', '-1', '1'))` | 3 |
| `randomNumber(('2', '1', '2', 'unarmed_zombie_', 'myStatus', 'r1'))` | 3 |
| `randomNumber(('2', '1', '4', 'unarmed_brawl_', 'myStatus', 'r1'))` | 3 |
| `randomNumber(('2', '-2'))` | 3 |

## Correccion a RXRE-SWF-051

Los argumentos se empujan en orden **INVERSO** (convencion AVM1): el ultimo antes del objeto es `arg1`.

```text
Push[R3, -2, 2, SwainMath] -> 0x1C -> Push[randomNumber] -> CallMethod
  declara randomNumber(2, -2, R3)
  NO randomNumber(R3, -2, 2)
```

Por tanto el rango es `[-2, R3]`, **no** `[R3-2, R3+2]`.

### Formula corregida del danio

```text
damage = Math.floor(
    SwainMath.randomNumber(2, -2, totalFrameDamage) / 4)
  rango del resultado: floor([-2,TFD]/4) = [-1, TFD/4]
  tras clamp de salud: [0, TFD/4]
```

### Critico de headshot (confirmado)

```text
r18 = SwainMath.randomNumber(2, 120, 200) / 100
    = [1.20, 2.00]  (120%-200%)
```

Gated by `perkHeadshotCrits` (`myDataRef.havePerk(perkHeadshotCrits,,2,MadnessDataFile)`); `r18=1` for `amSpecial && myCat==melee`.

## Limitaciones

- El modo de redondeo exacto (floor vs round) NO se determina (cuerpo nativo).
- La MITIGACION de armadura sigue en la rutina nativa `inDamage/inArmor` (RXRE-SWF-048); no recuperada.
- `totalFrameDamage` se computa en ramas del flujo de control; requiere seguimiento con CFG (no el ejecutor lineal).
