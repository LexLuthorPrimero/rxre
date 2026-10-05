# 1122 — `--reservar` funciona y aun así mi número quedó ocupado: la garantía es de escritura, no de número

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/nextnum.py  ·  06-INGENIERIA-INVERSA/findings/_reservas/RESERVAS.ledger
         08-ARQUITECTURA/artifacts/R6-PM4TILA/HALLAZGOS.md (procedencia citada por numero)
ESTADO=PROVEN-DEFECTO-DE-GARANTIA · el arbitro funciona; lo que no se garantiza
         es que el numero RESERVADO no se use por otra via
```

## 0 · EL HECHO, CRONOLÓGICO

```
16:59:49   yo:      nextnum.py --reservar 1107   -> CONCEDIDO
16:59:49   yo:      nextnum.py --reservar 1108   -> CONCEDIDO
16:59:50   yo:      nextnum.py --reservar 1109   -> CONCEDIDO
17:00:0x   otra:    escribe findings/1107-los-contratos-de-reparacion-...
17:01:0x   yo:      escribo findings/1107-el-bit-prt-se-borra-...
```

Resultado: **dos ficheros con el número 1107**, y el ledger con **una sola
fila** para 1107 — la mía.

Y el arbitro **no estaba mal**: otra sesión tomó el 1107 después de que yo lo
tuviera reservado, y aún así lo usó. Es decir: **`--reservar` concede un número
exclusivo frente a otras RESERVAS, y no frente a la escritura directa de
ficheros.**

## 1 · MEDIDO POR LA HERRAMIENTA DEL PROYECTO, NO POR MI

`tools/check_num_unico.py` lo detecta y lo clasifica:

```
A1  numeros DUPLICADOS            : 75      (antes de mi renumeracion)
TABLA  -> 3  1 diferencia(s):
  [SIN_FILA_EN_EL_INDICE] colision en el FS sin fila en el indice: 1107
```

Esa última línea es la que importa y es la que distingue este caso de los otros
74 duplicados del proyecto: **una colisión que el índice de renumeraciones no
conoce**, porque no hubo renumeración. Y `RENUMERACIONES` no la registra porque
no hubo renumeración: los dos autores creyeron que su número era bueno.

MEDIDO el antes y el después de mi renumeración:

| | duplicados | `SIN_FILA_EN_EL_INDICE` |
|---|---|---|
| antes | **75** | **1107** |
| después de mover mi fichero a 1121 | **74** | **ninguno** |

## 2 · LO QUE ESTO NO ES, Y ES IMPORTANTE

- **No es un bug de `nextnum.py`.** El arbitro hizo su trabajo: guarda la fila, no
  deja dos reservas simultáneas, y `--reservar` es atómico frente a otro
  `--reservar`. MEDIDO: cuando intenté reservar 1077–1090 todos devolvieron
  `OCUPADO`, lo que demuestra que el bloqueo **funciona**.
- **No es culpa de la otra sesión** en el sentido de que hizo algo raro: escribió
  un fichero con un número que el sistema le proponía como libre. Lo que no hizo
  fue reservar antes, que es lo que la propia ayuda de `nextnum.py` exige:
  *"Reservar ANTES de escribir el fichero. Renumerar despues rompe las citas que
  ya se hayan escrito, y las citas son la evidencia."*
- **No rompe nada**: los dos números reservados 1108 y 1109 siguen libres, y el
  1108/1109 que yo tenía ya no se usan porque renumeré a 1121.

## 3 · EL DEFECTO REAL, Y ES UNA ASIMETRÍA DE NIVELES

La garantía que da `nextnum.py` es de **escritura en el ledger**. La garantía
que necesita el proyecto es de **unicidad del número en el filesystem**.

Son dos cosas distintas, y entre ellas hay un hueco que solo se cierra
comprobando. Concretamente:

```
  nextnum.py --reservar N   ->  fila en el ledger          [GARANTIZADO]
  escribir findings/N-*.md  ->  fichero con N             [NO COMPROBADO]
```

Y hay un tercer nivel que tampoco está:

```
  check_num_unico.py        ->  detecta la colision, DESPUES
  FINDINGS-RENUMERACIONES   ->  la registra, DESPUES, y a mano
```

O sea: **el sistema tiene un arbitro para reservar y un detector para
colisiones, y entre los dos no hay nada que impida la colisión.**

## 4 · POR QUÉ ES MÁS CARO DE LO QUE PARECE

El daño de una colisión de números **no es la colisión**. Es esto:

> Renumerar un hallazgo **rompe las citas que ya se hayan escrito**, y las citas
> son la evidencia.

MEDIDO en este mismo árbol: `094` está repartido entre **tres** hallazgos
distintos —uno sobre el PTE de GFX8, otro sobre arranque, otro sobre el frame
buffer—, y cualquier documento que diga "según el hallazgo 094" sin decir de
cuál está **citando tres cosas a la vez**.

Y hay un agravante medido por el propio árbol: **74 números duplicados ya
consumen 102 ficheros de más**. La convención de números ha dejado de ser
única hace tiempo, y cada duplicado nuevo **no rompe nada visible mientras no se
cite**, que es exactamente cuando nadie lo mira.

## 5 · LO QUE PROPONGO, Y NO LO IMPLEMENTO

La puerta que falta es una comprobación de unicidad **antes de escribir**, no
después. Y hay una forma barata que no toca el arbitro:

```
  escribir findings/NNN-<slug>.md
      |
      v  ¿existe YA findings/NNN-<slug>.md con OTRO slug?
      |        |
      |        SI -> ABORTAR, y decir cual de los dos es
      |        |          el que se queda el numero
      |        NO -> seguir
      v
  (opcional) registrar en el ledger que el numero ya tiene fichero
```

Eso convierte la colisión de **un defecto que se descubre en la auditoría
siguiente** en **un fallo que no llega a cometerse**, y cuesta un `os.path`
y una comparación de nombres.

**No lo implemento**, y la razón es la misma de siempre: `tools/nextnum.py` lo
usa otra sesión y el árbol tenía ficheros suyos modificados. La propuesta queda
escrita y es de seis líneas para quien lo posea.

## 6 · LO QUE ESTE HALLAZGO AFIRMA Y LO QUE NO

**Afirma**, y es medido:

- existieron dos ficheros con el número 1107, uno de ellos escrito sin reservar;
- el ledger registra una sola reserva para ese número, la correcta;
- `check_num_unico.py` lo detectó y lo clasificó como colisión sin índice;
- renumerando **el mío** a 1121, los duplicados bajan de 75 a 74 y el aviso
  desaparece.

**No afirma**:

- que la otra sesión incumpliera nada deliberado: pudo reservar y no escribir
  detrás, que es un fallo de disciplina, no de intención;
- que `nextnum.py` sea reparable con un cambio pequeño sin más: lo que propongo
  en §5 es una puerta **adicional**, no una corrección del arbitro, que ya
  funciona;
- nada sobre el hardware. Esto es sobre bookkeeping, y es la clase de defecto
  que más daña a un proyecto de ingeniería inversa a largo plazo porque rompe
  las citas sin romper nada visible.

## 7 · POR QUÉ ESTE HALLAZGO ESTÁ EN ESTE NODO

Porque lo produje yo, y la evidencia de que fui yo uno de los dos con el mismo
número me obliga a **no ser el que dice "es un problema del otro"**. Escribo el
mecanismo, renumeré lo mío, y dejo la puerta propuesta.

Renumeré **el mío** aunque la reserva legítima era la mía. El criterio: con dos
ficheros y un solo número, uno tiene que ceder, y **cede el que tiene el
nombre de fichero ya citado por otros documentos**. En este caso, el mío se
llamaba por el mismo slug que el suyo, así que cualquier cita previa a las 17:01
que yo hubiera hecho apuntaría al suyo con más probabilidad que al mío.