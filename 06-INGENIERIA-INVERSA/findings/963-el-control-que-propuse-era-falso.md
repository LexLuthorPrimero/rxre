# 963 · El control que propuse era falso, y su premisa no era mía

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Lo que este hallazgo registra
>
> **El criterio de cierre de `962` NO se cumple, y no por un fallo mio sino porque
> el segundo conjunto nunca fue una señal de autoría.** Lo dejo escrito para que
> nadie vuelva a recorrer el mismo camino.

## 1. El criterio que propuse, y su resultado

En `962` fijé:

> «el conjunto de los 29 con mi `AUTORIA` es **exactamente** el de los que
> declaran `WORK_CLASS=READ_ONLY` con `WRITE_EXECUTION=NONE`; si no coinciden, el
> control señala que volví a contaminar»

```
AUTORIA=AGENTE-SMU            29
READ_ONLY + WRITE_EXEC_NONE   29
SOLO sello, sin forma:         920, 921
SOLO forma, sin sello:         932, 959
COINCIDEN EXACTAMENTE:         False
```

**Los dos tienen 29 elementos y no son los mismos 29.** Los cuatro que los
separan dicen exactamente por qué el criterio es inválido, y ninguno de los dos
lados es un error mío:

```
920, 921   mios, cabecera ANTERIOR: WORK_CLASS=READ_ONLY sin WRITE_EXECUTION=NONE
           ("MODIFICATIONS 0 en el corpus" y "MODIFICATIONS: **1 fichero**")
932, 959   del otro agente, con la MISMA forma que uso yo
```

## 2. Defecto 1: la premisa es falsa

**`WORK_CLASS` es un campo de clasificación de trabajo, no de autoría.**

```
932-bench-declara-writes-gpu-y-no-escribe.md   CLASSIFICATION=EVIDENCE · TRACK=STATIC ·
                                                WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE ...
959-el-barrido-como-suite-y-los-tres-fallos.md WORK_CLASS=READ_ONLY/EVIDENCE ·
                                                WRITE_EXECUTION=NONE · MODIFICATIONS=0 ...
```

**El otro agente declara exactamente el par que yo tomaré como «mi forma».** Un
conjunto que contiene ficheros de dos autores **no puede ser un criterio de
autoría**, por muy limpiamente que yo lo haya definido.

**Esto es `NAME_MATCH ≠ SEMANTIC_MATCH` aplicado a un campo de metadatos**: el
campo existe, tiene el valor que esperaba, y no significa lo que yo asumí. **El
mismo patron que ha producido hoy ocho errores**, y aqui con un campo que yo mismo
escribí y por eso daba por hecho que era mío.

## 3. Defecto 2: la implementacion tampoco habria funcionado

Con independencia de que la premisa sea falsa, el patron no detecta lo que dice
detectar: **el otro agente parte `WORK_CLASS=READ_ONLY` y `WRITE_EXECUTION=NONE`
en dos lineas distintas** de su cabecera. Un chequeo de una sola linea no lo
habria visto nunca.

**Dos defectos independientes en el mismo control, y el segundo oculta el primero:**
si solo hubiera arreglado la implementacion, el control habria seguido marcando
`920` y `921` como sospechosos, y yo lo habria leído como «la contaminacion
sigue ahi» en vez de como «el control esta mal».

## 4. Lo que hice: retirarlo, no arreglarlo

`integridad.py` **v2.2.0**, con el motivo escrito **en el propio codigo**, los dos
defectos y el resultado sobre datos reales de cada uno.

```
v2.1.0  anadi el control: "todo fichero con mi AUTORIA debe tener mi forma"
        ejecutandolo marco 2 ficheros MIOS (920, 921) como sospechosos
        y no habria marcado a ninguno ajeno
v2.2.0  retirado. El motivo queda en el codigo, con los datos.
```

**El principio que aplique, y que es el contenido de esta finding:**

> **Un control que señala ficheros correctos destruye la confianza mas rapido que
> no tener control.**

Un control que nunca falla es inutil; **uno que falla de mas es peor**, porque
enseña a ignorar sus propias alarmas, y la primera alarma que se ignora es la
real. Este control no tenia señal valida, y por eso la decision correcta no era
arreglarlo sino **retirarlo y dejar por escrito por que**.

## 5. El control que si queda, y por que ese si vale

```
CONTROL 1   mi AUTORIA declarada + un CORPUS ajeno  ->  CONTAMINADOS
            mi AUTORIA declarada + mi corpus        ->  no es contaminacion
```

**Ese si tiene señal**, porque **una declaración de corpus ajeno es evidencia
positiva de que el fichero no es mío**, y eso es lo unico que importa para
detectar el incidente de `962` v2: mi sello puesto sobre trabajo ajeno.

```
sobre la banda real:  ok   ninguna AUTORIA mia sobre un corpus ajeno
```

Y esta vez con **los dos signos en el self-test**, que es lo que un control
necesita para ser creible:

```
ok  CONTROL 1: mi sello + corpus ajeno se detecta como CONTAMINADO
ok  CONTROL 1: mi sello + MI corpus NO es contaminacion
ok  sin contaminacion, el control NO falla
```

**Ese positivo es el que importa.** Un control con un solo signo no se puede
usar, y es lo mismo que critiqué al principio de esta linea en `atom_chain`: el
primer self-test que escribi ahi probaba el camino bueno y no el malo, y por eso
no valia nada.

## 6. El estado, que es el que hay que citar de aqui en adelante

```
integridad.py v2.2.0   21 casos, 0 fallos, exit=0

MIO       29    con AUTORIA=AGENTE-SMU declarada
AJENO      0    nadie declara otra autoria
SIN_DECL  25    sin AUTORIA: los 25 hallazgos del otro agente en mi banda

controles sobre los 29 mios:
  ok   duplicados: ninguno
  ok   ficheros vacios: ninguno, en toda la banda
  ok   texto no latino ni ingles: ninguno
  ok   ninguna AUTORIA mia sobre un corpus ajeno
---> FALLA: SIN_DECL 25        exit=1
```

**El `exit=1` es el resultado correcto y hay que dejarlo asi.** No puedo probar
la pertenencia de 25 hallazgos de mi banda, y el control se niega a certificar en
vez de contarlos como míos.

**Lo que `integridad.py` puede y no puede:**

```
PUEDE   probar que 29 hallazgos son mios, por su declaracion
PUEDE   Exclusion de cualquiera que declare corpus o autoria ajena
NO PUEDE probar que los 25 SIN_DECL no sean mios
NO PUEDE identificar autoria por ningun campo de cabecera salvo AUTORIA
```

## 7. Errores de esta iteracion

**1. Propose un control con una premisa que no compruebe.** Dije «mi forma de
trabajo es `READ_ONLY + WRITE_EXECUTION=NONE`» **sin verificar que fuera mia y no
compartida**. Y con el nombre de `WORK_CLASS` delante, darlo por mio era
razonable... **y por eso es el fallo: el nombre me hizo creer que era mio.**

**2.** Y lo grave: **el self-test paso.** Con 21 casos en verde y el control
falso. **El fixture no reproducia la condicion**, porque los ficheros ajenos del
fixture no declaran `AUTORIA` y nunca entraban en el conjunto que el control
comparaba. **Un self-test verde sobre un fixture que no reproduce la situacion
real es peor que no tener self-test**, porque certifica un control que no sirve.

**3.** Dos `NameError` y un `UnboundLocalError` en mis parches, por aserciones
colocadas antes de que existiera la variable. Los vi por el traceback y el
`exit`, no porque el script anunciara exito.

**4.** Y un `TypeError` en una llamada anterior a `tools.shell` que no existe en
este harness. Fallo mio de API, no de criterio, pero tambien es un `0` disfrazado:
si no llego a mirar el error, habria seguido como si la llamada hubiera pasado.

## 8. Frontier siguiente

```
1.  los dos conjuntos tienen 29 y NO coinciden                      PROVEN
2.  920, 921 son mios con cabecera anterior                        PROVEN
3.  932, 959 usan la misma forma de WORK_CLASS que yo               PROVEN
4.  WORK_CLASS no identifica autoria                                PROVEN
5.  el control propuesto era falso en premisa y en implementacion   PROVEN
6.  retirado, con el motivo escrito en el codigo                   PROVEN
7.  CONTROL 1 si tiene senal y tiene los dos signos                 PROVEN
8.  integridad.py v2.2.0, 21 casos, 0 fallos                         VALIDATED
9.  exit=1 en la banda, por los 25 SIN_DECL                         PROVEN
10. propiedad de los 25 SIN_DECL                                    NOT_PROVEN
```

**El punto 10 es el unico que queda abierto, y no lo puedo cerrar con una
herramienta porque no hay mas senal en la cabecera.** Y es una situacion que
merece nombrarse en vez de disimularse:

**Mi banda de hallazgos contiene 25 ficheros de otro autor que no declaran quien
son.** Yo se quienes son por el tema y por los instrumentos que citan. **Pero «lo
se» no es una verificacion**, y mientras no declaren su autoria, cualquier
control que corra sobre esa banda **no puede certificarla**, y el `---> OK` que
falta por `SIN_DECL` es la respuesta honesta.

**Y hay una consecuencia de seguridad que no es rhetorica:** mientras 25 ficheros
ajenos sin declarar convivan con los mios **en la misma banda y bajo el mismo
numero**, **cualquier agente que reserves numeros aqui puede chocar con ellos sin
saberlo**, que es exactamente lo que me paso con `959`, `961` y `944`.

Criterio de cierre: una de dos, y ambas sonorrectas. **(a)** Que el otro agente
declare `AUTORIA` en sus cabeceras, con lo que `SIN_DECL` baja a 0 y la banda
queda enteramente clasificada. **(b)** Que yo no vuelva a numerar en `9xx` y
reserva una banda distinta, que es lo que haria un proyecto que reconoce que su
numeracion no es la unica. **Lo que no es una salida es dejar las dos cosas como
están y que `exit=1` sea el estado permanente.**
