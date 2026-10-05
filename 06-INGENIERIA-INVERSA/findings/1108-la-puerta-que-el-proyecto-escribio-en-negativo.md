# 1108 — el proyecto escribió la puerta que falta, en negativo, y la dejó sin ejecutar

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/nextnum.py --auditar (la puerta que propuse en 1122 §5, ya escrita)
         06-INGENIERIA-INVERSA/findings/_reservas/RESERVAS.ledger  (128 reservas vivas)
ESTADO=PROVEN-HUECO-CONOCIDO-Y-DECLARADO · el defecto esta escrito en el propio
       proyecto, con su nombre, y no hay nada que lo ejecute
```

## 0 · LO QUE EL PROYECTO YA SABE, CON SUS PALABRAS

Salida literal de `tools/nextnum.py --auditar` en este árbol, hoy:

```
AUDITORIA DEL REGISTRO DE BLOQUEO
  reservas vivas          : 128
  con fichero detras      : 96
  SIN fichero detras      : 32

  clase SIN ORIGEN DEMOSTRABLE (puede ser un hallazgo perdido): 31
     1072  <- reservada y sin fichero. No se libera: cerrar el
            sintoma taparia el defecto (nada comprueba que una
            reserva tenga fichero detras).
```

**La frase «nada comprueba que una reserva tenga fichero detrás» es el hueco
que el hallazgo `1122` propone cerrar, escrita por el propio proyecto, con su
nombre y suywym consequence.** Y lleva el argumento completo: cerrar la reserva
taparía el síntoma, o sea que **la decisión de no liberar es correcta** y por
eso el defecto tiene que cerrarse en otro sitio.

## 1 · LO QUE NO ESTÁ HECHO, Y ES LO ÚNICO QUE FALTA

Hay un **contador** que sabe cuántos huecos hay. No hay una **puerta** que
impida abrir uno nuevo.

```
  nextnum.py --reservar N      ->  ledger           [ARBITRO, FUNCIONA]
  ... escribir findings/N-*     ->  fichero          [NADA COMPRUEBA]
  nextnum.py --auditar         ->  CUENTA los huecos [DETECTOR, POSTERIOR]
  check_num_unico.py           ->  detecta colisiones [DETECTOR, POSTERIOR]
```

El proyecto tiene el detector y el arbitro. **Lo que no tiene es el paso entre
los dos**, y ese paso es una línea.

## 2 · LO QUE CUESTA MEDIDO, Y NO ES «COLISIONES»

Lo que se paga por una reserva huérfana no es una colisión. Es esto:

```
  128 reservas vivas
   96 con fichero detrás
   32 sin fichero detrás       <- 25 % de las reservas vivas
```

MEDIDO que la consecuencia es doble, y la segunda es la cara:

1. **Gastar números.** Cada una es un número del contador que no produce
   trabajo. Con la directiva vigente, el contador es la medida, así que un
   número sin fichero hace que el progreso parezca mayor de lo que es — que es
   justo lo que la propia directiva de trabajo warns contra cuando dice que el
   contador **sobrestima**.
2. **No poder distinguir un hallazgo perdido de una reserva muerta.** El propio
   audit lo dice: *«puede ser un hallazgo perdido»*. Y esa frase **no se puede
   resolver con el dato que hay**: un número reservado sin fichero es
   compatible con las dos lecturas.

> **La puerta que falta no es «que no haya reservas huérfanas». Es que se pueda
> distinguir «reservé y no llegué a escribir» de «escribí y se perdió el
> fichero».** Lo segundo ya ocurrió en este árbol — hay hallazgos con
> correcciones y retractions, lo que significa que se han escrito y se han
   tocado — y lo primero ocurre a cada lote.

## 3 · POR QUÉ NO SE IMPLEMENTA AQUÍ, Y ES UNA DECISIÓN CON NOMBRE

Porque `tools/nextnum.py` **lo usa otra sesión** y en este árbol hay ficheros
suyos modificados sin commitear. Es la misma razón por la que no toqué
`revkit/pm4dec.py` en `1063`, y por la que no regeneré `TOOLS-STATUS.md` en
`R5a-PROSA`.

Escribir encima del trabajo de otro nodo no es una corrección: es un conflicto.
Y la propuesta de `1122` §5 está completa —siete líneas— para quien lo posea.

## 4 · LO QUE ESTE HALLAZGO AFIRMA

- **MEDIDO**: hay 32 reservas vivas sin fichero detrás, de 128.
- **MEDIDO**: el propio proyecto escribe el nombre del hueco y por qué cerrarlo
  por el otro lado está equivocado.
- **PROVEN**: el arbitro y el detector funcionan; lo que falta es la puerta
  intermedia, y su ausencia es la causa de que el defecto se pueda repetir.
- **NO AFIRMA**: que las 32 reservas correspondan a hallazgos perdidos. La
  herramienta las clasifica como «puede ser» y no se puede ir más lejos con el
  dato que hay: **es `NOT_DETERMINED` y no se convierte en `PROVEN_ABSENT` ni
  en `PROVEN` en ninguna dirección.**

## 5 · UNA RESERVA MÍA, Y POR QU ESO ESTÁ EN ESTE HALLAZGO

MEDIDO: de este documento, **tres** números que reservé quedaron sin fichero:
`1108` (este), `1109` y `1123`. El primero se está usando ahora mismo; los otros
dos no.

Lo escribo porque **mi caso es el caso**: reservé tres números, produje dos
hallazgos, renumeré uno por una colisión, y me quedan dos números gastados sin
nada detrás. Exactamente el patrón que el audit cuenta y que el proyecto lleva
contando desde el principio.

> La consecuencia de que eso esté en un hallazgo y no en un archivo de reservas
> es que **al menos queda una frase que lo explica**. Las 31 Reservas del audit
> no tienen frase. Ese es el punto.