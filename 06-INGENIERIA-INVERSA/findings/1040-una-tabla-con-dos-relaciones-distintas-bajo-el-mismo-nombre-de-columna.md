# 1040 · Una tabla con dos relaciones distintas bajo el mismo nombre de columna, y 27 citas que un "arreglo automático" habría roto

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=N/A` · `HARDWARE_SCOPE=N/A` (ningún acceso a hardware)
`WORK_CLASS=READ_WRITE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1`
`GPU INTACTA` · `MODIFIES_CODE=SI` (`08-ARQUITECTURA/tools/reenvio_gate.py`)

---

## La pregunta

Un nodo concurrente amplió el mapa congelado `REENVIO-FINDINGS.tsv` de 43 a 49 filas.
Seis filas nuevas. Al revisarlas, una de ellas no se sostiene **leída como lo que la
tabla dice que es**:

```
267 | 271 | SI | el-kernel-de-cache-mide-la-tasa-de-emision.md | prosa:271-…:11-12
```

El hallazgo 271 trata de **la tasa de emisión de un núcleo de caché**. El 267 de hoy
trata de **la curva V-f del VBIOS**. Si eso fuera un renumerado de contenido, el
contenido sería el mismo, y no lo es: son dos notas distintas.

La fila era una transcripción fiel de la prosa del 271. El problema es lo que esa
prosa afirma.

## MEDIDO

### Qué dice la prosa que sostiene la fila

`271-el-kernel-de-cache-mide-la-tasa-de-emision.md:11-12`:

> **`RENUMERADA`. Esta nota era la `267` y pasó a ser la `271`, porque el 267 ya lo
> ocupaba `267-la-curva-vf-de-mi-vbios-no-esta-rellena.md`, que es otra nota y no la
> mía.**

Eso **no** dice "mi contenido estaba numerado 267". Dice: **el número 267 estaba
ocupado** por la nota de la curva V-f, así que esta nota tomo el 271. Es una
**colisión de asignación de números**, no un renumerado de contenido.

Y hay una incoherencia interna que lo confirma: si la 271 hubiera tenido el 267 y la
curva V-f se lo hubiera quedado después, la prosa diría "el 267 que era mío pasó a
ser 271". En cambio dice que el 267 lo ocupaba **otra nota**. En el segundo caso —y
es el que el texto describe— el 271 **nunca tuvo** el número 267 en el árbol.

### Las dos relaciones, y por qué la tabla las mezclaba

| procedencia | qué produce la derivación | qué relación es |
|---|---|---|
| `diff` (43 filas) | `git ls-tree HEAD` contra el árbol de trabajo: el fichero `NNN-*` **desapareció** y apareció `MMM-*` | **contenido**: ese contenido pasó de N a M |
| `prosa` (4 filas) | transcripción de la cabecera del fichero de destino | **numero**: el número N estaba ocupado y este contenido tomo el M |
| `git` (2 filas) | lectura de la prosa de un commit | sin determinar fila a fila |

Las 43 filas `diff` son un renumerado de contenido: el fichero con el número viejo
dejó de existir. Las 4 `prosa` son, en los cuatro casos medidos, el otro caso.

Y la tabla tenía **una sola columna para las dos cosas**, con un `reasignado` (SI/no)
que ya reconoce que el número se reutiliza — pero sin decir de qué lado de la relación
está cada fila.

### Por qué importa: la clase se rompe al arreglar

Las citas que hoy apuntan a `267` **no hablan de la curva V-f ni del núcleo de caché**.
Hablan de decodificación de voltaje:

```
266-la-codificacion-del-voltaje-no-es-un-float…:123
    **no existe** con ese nombre~~ — **CORREGIDO en `267`: si existe**, en
    `pm/powerplay/hwmgr/pptable_v1_0.h:185`, no en `atombios.h` como busque.
269-el-techo-de-reloj-no-viene-de-la-tab…:44
    Con los 8 niveles que decodifique en `267` —`cks_enable` = 0 en el nivel 0
```

MEDIDO: 27 citas a `` `267` `` en 13 ficheros. Y el único hallazgo del árbol que
contiene la tabla de niveles con `cks_enable` (5 ocurrencias) es
**`050-correccion-chip-id-y-clock-stretcher.md`**.

O sea: el destino pretendido de esas 27 citas es **ni el 267 ni el 271**. Es un
tercero. Y por eso:

> **Repararlas con la flecha del mapa las habría apuntado al hallazgo del núcleo de
> caché.** Veintisiete afirmaciones sobre voltaje y clock stretching citando, con
> autoridad aparente, un hallazgo sobre emisión de caché.

Eso es exactamente el criterio que el propio proyecto ya escribió en el hallazgo 188,
que se titula literalmente *"y una cita que señalaba a la generación equivocada"*:

> *Una cita equivocada es peor que un número equivocado, porque el número equivocado
> se nota al compararlo con el fichero y la cita equivocada presta autoridad al
> error.*

Una cita colgante **se ve**. Una cita apuntando al fichero equivocado, con el formato
correcto y la línea correcta de un fichero que no habla de eso, **no**.

### Y el mapa no puede repararlas, por construcción

Para reparar una cita de la forma `` `NNN` `` hace falta saber **quién tenía el
número antes**. La tabla tiene `viejo` y `nuevo`, pero `viejo` significa "el número
que este contenido no tiene", no "el número que este contenido tenía antes". Para las
43 filas `diff` las dos cosas coinciden. Para las `prosa` no coinciden nunca, y el
mapa no tiene dónde anotarlo.

## LA REPARACIÓN

1. **Sexta columna, `relacion`, con dos valores**: `contenido` para las 43 `diff`, y
   `numero` para las 4 `prosa`. Es la decisión mínima que hace la tabla legible: una
   fila sin valor en esa columna se rechaza.
2. **La puerta rechaza el uso de una fila `numero` para reparar citas.** No lo
   comprueba por taste: lo comprueba porque las 27 citas medidas de `267` apuntan a un
   tercero, y reparar con la flecha las llevaría al fichero equivocado.
3. **Las 27 citas quedan `NOT_DETERMINED`**, no "reparadas". Su reparación exige leer
   cada una y decidir a qué nota se refiere, que es trabajo de otro tipo y no se
   puede automatizar con la información del mapa.

## LO QUE ESTO DEJA ABIERTO, Y ES LO IMPORTANTE

- **La clase es más grande que 267.** Las otras 3 filas `prosa` —`944→947`,
  `961→962`, `991→994`— se clasificaron como `numero` **por el mismo criterio**, no
  por haber medido sus 3+3+2 citas una a una. MEDIDO que en esos tres casos el
  destino es un hallazgo cuyo tema **tampoco** coincide con lo que las citas dicen —
  `991→994` apunta a *"el ISA de GFX8 sí tiene fuente primaria publicada"* y las dos
  citas que cita son sobre otra cosa. Igual que en 267.
- **Las 44 referencias colgantes que el nodo contabilizó son, por lo menos, las que
  corresponden a las 6 filas nuevas.** Las 38 de las filas `diff` no son de este tipo:
  el fichero viejo desapareció de verdad y la flecha sí mapea contenido. Las dos clases
  necesitan reparaciones distintas y **no deben ir en el mismo lote**.
- **Nueve pares más, medidos y sin escribir.** El nodo los dejó fuera de mandato y es
  lo correcto: `272→274`, `280→288`, `290→291`, `998→1002`, `1000→1004`,
  `1003→1005`, más dos declaraciones que no dicen qué fichero renumeraron
  (`943-setenta-numeros…:110-111` y `400-el-resumen…:181`). Con ellos el mínimo real
  es **55 pares**, no 45. Y cada uno necesita su `relacion` decided por lectura.

## POR QUE NO SE HA ESCRITO UN ARREGLO AUTOMÁTICO

Porque habría funcionado. Eso es lo que lo hace peligroso. Un script que lee el mapa
y reescribe `` `NNN` `` por el número nuevo habría tocado 27 líneas, habría producido
un diff limpio, y habría convertido 27 afirmaciones sobre voltaje en 27 afirmaciones
falsas con cita. El código de salida habría sido 0.

Es el mismo motivo por el que `findings_index.py` se niega a escribir cuando va a
perder renumeraciones, y el motivo por el que 1036 registra que un generador que
regenera y sale con un 0 no es un generador. La puerta que falta aquí es la inversa:
**una puerta que se niegue a reparar**, no una que se niegue a escribir.
