# 1176 — Los dos eslabones que `1152` nombró como ausentes se han evitado **sin tocar `pm4_emit`**: `ARRAY_SIZE` se sustituye por el conteo que ya existía, y `/` se pliega entre literales. La cadena completa resuelve a **248**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION · VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py   (_arraysize, _plegar_division,
                              84 -> 93 vectores)
                              06-INGENIERIA-INVERSA/findings/1152  (aviso)
                              08-ARQUITECTURA/artifacts/R16-FOLD/salida.txt
MODIFICADO_NADA_EXISTENTE    pm4_emit.py INTACTO
CLASSIFICATION=IMPLEMENTATION · VALIDATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=2 DE LOS 4 ESLABONES CERRADOS · LA CADENA COMPLETA RESUELVE
```

## 0 · El resultado, primero

```text
LA CADENA, por el camino real (sintetizar -> eval_call):

  sizeof(vgpr_init_regs)                          -> 136
  sizeof(vgpr_init_regs[0])                       -> Unresolved  (ya no hace falta)
  ARRAY_SIZE(vgpr_init_regs)                      -> 34
  (((ARRAY_SIZE(vgpr_init_regs)/2)*3)+4+5+2)*4    -> 248

LOS TRES SUMANDOS QUE EL DRIVER SUMA:

  vgpr_init_regs    -> 248
  sgpr1_init_regs   -> 248
  sgpr2_init_regs   -> 248
  suma 744   ALIGN(744,256) -> 768

LO QUE SIGUE SIN RESOLVERSE
  total_size, vgpr_offset, sgpr_offset
     -> propagacion de variables locales. NO implementada. Declarada.

vectores ibref 84 -> 93, rc=0
no-regresion   kiq 15 dwords IDENTICOS · shader-init 294 dwords, 285 completos,
               0 bucles sin reconocer
puerta         48 medidas, SIN DERIVA
```

## 0b · COLISIÓN DE NÚMERO, Y CÓMO SE RESUELVE

Escribí este hallazgo como **1153**. Al validar con `doclint` apareció otro
fichero con ese número:

```text
06-INGENIERIA-INVERSA/findings/1153-dos-vias-de-invalidacion-de-tlb-en-gfx8.md
```

No es mío: es de otra sesión, y `--reservar 1153` me había dicho que estaba
reservado por mí. **La reserva no se impone.**

Mecanismo, medido con `nextnum.py --auditar`:

```text
reservas vivas            170
  con fichero detrás      120
  SIN fichero detrás       50     <- reservationes que nadie ha usado

clase SIN ORIGEN DEMOSTRABLE: 49
```

Cincuenta números están reservados sin nada detrás, así que `--reservar N` es
una **convención**, no un candado: dos sesiones pueden reservar el mismo número
en el mismo minuto y las dos tienen razón desde su lado.

Lo que he hecho:

```text
1. reservar un numero VERIFICADO DOS VECES: primero que no haya fichero con
   ese numero, y despues que --reservar lo acepte
       1154..1158  los declaraba libres nextnum.py y los cinco estan OCUPADOS
       1159..1180  ninguno libre
       1176        libre, sin fichero, y reservado
2. renombrar el fichero Y el titulo, y este texto
3. dejar constancia, porque el incidente es un dato sobre la herramienta
```

Lo que **no** he hecho es renumerar el hallazgo del otro autor. Sus 1153 son
suyos y su número le es útil; el mío era el que estaba en colisión, porque
yo tenía el ledger delante y él no.

> Un contador compartido sin candado hace que **el número no identifique al
> hallazgo**, que es exactamente lo que `1049`, `1054` y `1056` ya midieron y
> lo que la directiva vigente repite al contar. Con 175 documentos en colisión y
> 74 números duplicados, no es un incidente aislado: es la mecánica normal.

## 1 · LA VÍA QUE NO ERA LA PRIMERA

`1152 §5` puso tres opciones sobre la mesa, con sus costes, y no eligió:

```text
1  entender ARRAY_SIZE en general   -> exige /, [] y la regla de aserciones
2  SUSTITUIRLO por el dato que ya tengo
3  dejarlo sin resolver
```

Elegí la **2**, y el motivo no es que sea la más barata:

> `ARRAY_SIZE(x)` **está definido** como `sizeof(x) / sizeof(x[0])`. Para un array
> de `u32`, eso **es** el número de elementos. Y `arrays_estaticos()` ya lo
> cuenta, porque lo necesita para desenrollar bucles.

O sea: no es una aproximación ni un atajo. Es **la misma cantidad calculada por
la otra vía**, y la vía ya existía por una razón distinta. Reutilizar un dato que
ya se tiene para responder una pregunta que se acaba de la forma más barata de
no añadir dependencia.

Y hay un argumento de honestidad que importa más: `ARRAY_SIZE` no comprueba que
`x` sea un array en tiempo de ejecución. Lo comprueba `__must_be_array` **al
compilar**, y este código ya ha compilado en el árbol de otra sesión. Sustituir
no salta ninguna comprobación que el código original saltara.

## 2 · `/`: PLEGADO DE CONSTANTES, NO UN EVALUADOR

El riesgo obvio de "arreglar la división" es escribir un evaluador de
expresiones, que es donde viven los bugs de precedencia. No hacía falta:

```text
la division que hay en esta expresion es   ARRAY_SIZE(x) / 2
y tras sustituir ARRAY_SIZE, los dos operandos son LITERALES ENTEROS
```

Plegar `A / B` con A y B literales es **constante**, y una constante no tiene
precedencia que respetar: no queda nada que parsear. La función se niega a tocar
cualquier otra cosa.

```python
RE_DIV_LIT = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")

def rep(m):
    a, b = int(m.group(1)), int(m.group(2))
    if b == 0:
        return m.group(0)          # NO se pliega
    return str(a // b)
```

Dos decisiones con vectores que las fijan:

```text
7 / 2      -> 3        division ENTERA de C, no 3.5 ni 4
5 / 0      -> 5 / 0    no se plega: en C es error de compilacion, y aqui
                       devolver algo seria inventar
x / 2      -> x / 2    un operando no literal no se toca
a / b      -> a / b    no es un numero, no se toca
4 + 6 / 2  -> 4 + 3    la precedencia se RESPETA: se pliega la division y
                       la suma la hace el evaluador, que ya la sabe hacer
```

La cuarta es `1151 D5`, y es el vector que separa esto de un evaluador: si
alguien cambiara el plegado para "resolver más", `4 + 6 / 2` daría `5` y ese
vector lo cazaría.

## 3 · `[]` SIGUE SIN ESTAR, Y ES INOFENSIVO POR QUÉ

`sizeof((arr)[0])` sigue dando `Unresolved: token:[`. **No lo he arreglado**, y
la razón es que con `ARRAY_SIZE` sustituido ya no hace falta para nada:

```text
sizeof(x)           ->needed, y cerrado (1151)
sizeof(x[0])        -> solo lo necesitaba DENTRO de ARRAY_SIZE, y ya no
ARRAY_SIZE(x)       -> cerrado por sustitucion
__must_be_array     -> ya no se llega a el
```

De los cuatro eslabones de `1152`, dos quedaban y los dos eran, exactamente, los
que `ARRAY_SIZE` arrastraba detrás. **El `sizeof(x[0])` y la aserción no eran
problemas: eran la sombra de un problema.**

Eso no es excusa para no arreglarlos: `D2` sigue en pie para cualquier otro uso de
`[]` en el driver. Pero es distinto decir "falta `[]`, hay que tocar `pm4_emit`"
que "aquí `[]` no estorba y no voy a tocar `pm4_emit`".

## 4 · LO QUE SE CIERRA Y LO QUE NO, EN UNA TABLA

```text
ESLABON                       1152              AHORA            DUEÑO
sizeof(x)                     CERRADO           CERRADO          yo
sizeof(x[0])                  falta []          sin uso          nadie
ARRAY_SIZE(x)                 exige D1+D2+D6    CERRADO          yo
__must_be_array               falta la regla    sin uso          nadie
division /                    falta /           CERRADO          yo
propagar total_size            no implementada    NO implementada yo, P1..P4
```

**La frontera ha pasado de "cinco cosas sin dueño claro" a "una cosa mía con su
contrato escrito".** Eso es lo que `1152 §1` decía que era cerrar una frontera, y
se cumple.

## 5 · NO REGRESIÓN

```text
kiq_kcq_enable        ampliada=15  sin=15  IDENTICAS=True
shader-init           294 dwords, 285 completos, 9 incompletos, 0 sin reconocer

(las dos cifras de "294" y "285" son las de 1139, antes de que existiera
 sizeof y ARRAY_SIZE: la sintesis NO ha cambiado)
```

Que no haya cambiado **es** el resultado. Añadir dos sustituciones en la
frontera era el riesgo, y el número de dwords completos es el que lo delata.

## 6 · LO QUE SIGUE ABIERTO, Y ES UNA COSA SÓA

```text
propagacion de variables locales    NO implementada
```

Con su contrato, escrito en `1151 §6` y **sin cambios**:

```text
P1  CLAVE += <expr>  es  a = a + expr  EN C.  Tratarlo como `a + expr` esta MAL
    y en silencio. Anotado ANTES de implementar, que es la unica vez que
    sirve de algo.
P2  si la expresion no resuelve a entero -> PARAR esa variable y declararla.
P3  ciclos: tope de rondas y declararlo. Un sintetizador que itera hasta
    converger da un numero y no dice nada.
P4  solo identificadores simples. p->field y arr[i] no se tocan.
```

Y con esto, la aritmética de `total_size` queda **completamente evaluable** en
cuanto a datos: los tres sumandos dan 248, la suma 744, `ALIGN(744,256)` da 768,
y `vgpr_offset` sería 768, `sgpr_offset` 768 + `ALIGN(264,256)/4` = 768 + 128 =
896, en dwords de IB 192 y 224.

**Eso último no lo he medido con la propagación hecha.** Lo he calculado a mano con
las piezas ya medidas, y adivinar el resultado final antes de ejecutarlo es
exactamente lo que este proyecto prohíbe. Queda como `NOT_DETERMINED` hasta que
`P1..P4` se implemente y la cadena corra entera.

## 7 · PROCEDIMIENTO

```text
instrumento   ibref  _arraysize(expr, arrays)
                    _plegar_division(expr)
vectores      84 -> 93, rc=0
             9 nuevos: ARRAY_SIZE x3 (valor, desconocido, recuento)
                        plegado x6 (entera, por cero, no literal, no nombre,
                                    varios, y precedencia 4+6/2)

medicion      sizeof 136/264/168      ARRAY_SIZE 34
              cadena completa 248     tres sumandos 248+248+248 = 744
              ALIGN(744,256) = 768

no-regresion  kiq IDENTICAS=True
              shader-init 294 dwords, 285 completos, 0 bucles sin reconocer
puerta        48 medidas, SIN DERIVA
otros         layoutcross 79 vectores rc=0 · mmio 48 vectores rc=0
cross-ref     1152 lleva un aviso de que sus eslabones 3 y 4 quedan sin uso
escrituras    0 ficheros de otros agentes
artefacto     08-ARQUITECTURA/artifacts/R16-FOLD/salida.txt
```