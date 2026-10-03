# 296 · Ciento cincuenta y ocho líneas sin probar, y el clasificador que no las reduce

```text
CLASSIFICATION=MEASUREMENT+LIMITATION · TRACK=TOOLING
CORPUS=NINGUNO (el proyecto) · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

El `NEXT_ACTION` de `295` era: de las 150 líneas que el self-test no ejecuta,
clasifícalas por su propia forma —sin mirarlas— con el criterio ya escrito, y
mira cuántas quedan. Mi predicción era que quedarían unas pocas.

```text
  lineas NO EJECUTADAS por su self-test          158
  .....................................................
  tras quitar las formas que se pueden quitar
  sin mirar:                                      99

  predicho  unas pocas
  medido    99 de 158
```

**La predicción era falsa por un factor grande, y esa es la primera mitad del
hallazgo.**

## 1 · El reparto, con el clasificador por forma

```
  CONTRATO_DE_SALIDA             17   return 0 / return 1
  GUARD_DE_LECTURA               15   if txt is None: / if not x.is_file():
  BANDERA_DE_LINEA_DE_ORDENES    15   if a.json: / if args.check:
  COMENTARIO_O_IMPRESION          9   lo que no es codigo
  PUNTO_DE_ENTRADA                3   if __name__ == "__main__":
  OTRO                           99   <- no encaja en ninguna de las cinco
```

Setenta y siete se van con reglas que no necesitan mirar. Noventa y nueve no.

Y lo importante es que los 99 **no son una clase**, sino al menos tres:

### Validación de entrada que nadie ejecuta

```text
  nextnum.py   L465   if not re.match(r"^\d{3}$", n):
  lint.py      L152   if fn == YO_MISMO:
  lint.py      L891   if os.path.basename(ruta) != "Makefile":
  toolaudit    L299   if not f.endswith(".md"):
```

### Lógica de decisión que nadie ejecuta

```text
  nextnum.py   L470   if not cands and n in reservados():
  nextnum.py   L481   if len(cands) == 1:
  fingerprint  L106   if r.returncode != 0:
  fingerprint  L509   if v == "TARGET_MISMATCH":
  lint.py      L938   if len(rows) > 80:
```

### Y la que más molesta, porque la escribí yo hoy

```text
  toolaudit.py  L390  if EVIDENCIA_SELFTEST.search(salida) or REPORTA_DEFECTO...
  toolaudit.py  L413  if EVIDENCIA_SELFTEST.search((r.stdout or "") or ...)
```

Esas dos están dentro de `bandera_convencion()`, que es **la función que decide
si una herramienta tiene self-test o no**. La escribí hace unas horas, le añadí
cuatro consideraciones sobre por qué hay que preguntar en vez de adivinar, y su
propio self-test no la ejecuta ni una vez.

```text
  la logica que decide si las demas herramientas estan bien probadas
    no la prueba nadie
```

Eso no es un hecho del proyecto ni una observación: es una consecuencia medible de
`295`, y de haber escrito el self-test de una herramienta y no mirar dónde están
sus ramas.

## 2 · Y el clasificador por forma es una hipótesis, como todo lo demás

No lo doy por bueno porque clasifique limpio. Lo validé leyendo una parte:

```text
  mi regex de BANDERA  if (a|args|o)\.(json|selftest|check|...):
  la linea real         if args.desde is None:

  -> mi regex falla, y la linea cae en OTRO
  -> es la razon por la que hay 99 y no menos
```

Es decir: **parte de los 99 son error de mi clasificador, no línea sin probar.**
Y no hay forma de distinguir las dos cosas sin mirar, que es justo lo que el
método debía evitar.

Lo que sí se puede decir del clasificador:

```text
  acierta en 77 casos de 158, por reglas que no necesitan mirar
  falla en algunos, y se sabe por que: la regla no cubre `args.desde`
  y los 99 restantes NO son una clase, sino tres
```

Un clasificador con un 49 % de acierto y sin forma de detectar sus propios fallos
**no es un filtro**, es una partición con ruido. Se declara y se usa para orientar
la lectura, no para borrarla.

## 3 · El coste, que es la pregunta de una línea del `NEXT_ACTION`

> «cuántas quedan después de quitar las formas que se pueden quitar sin mirar, y
> si ese número cabe en un día de trabajo o necesita un plan»

```text
  quedan                          99
  de las cuales, validación de entrada   ~15   y son cortas, se prueban bien
  de las cuales, lógica de decisión      ~20
  de las cuales, clasificación fallida   ~64   sin mirar, no se sabe cuales

  coste de añadir un vector por linea, con su mutacion para probarlo
    ~3 lineas de vector + 1 mutacion declarada + 1 ejecucion del self-test

  a 30 lineas por hora de trabajo escrito y ejecutado:
    99 lineas  ~3,5 horas si todas fueran codigo, y no lo son
```

**No cabe en un día de trabajo honesto**, porque 64 de las 99 no se sabe qué son
hasta mirarlas. Y la parte que sí se sabe, la lógica de decisión, es la que más
vale: `nextnum:470` decide si una reserva se ve, y es el mismo defecto que
`295` encontró con una mutación declarada.

## 4 · Lo que NO se establece

```text
  cuales de las 99 son codigo y cuales error del clasificador
    NO DETERMINADO, y no se puede determinar sin leerlas una a una. Es la razon
    por la que el 99 es un numero con uncertainty, no una lista
  si la cobertura del 28 % a 42 % es baja para el tipo de herramienta que son
    NO SE COMPARA. No hay referencia. Lo que si se puede decir es que `mutscore`
    solo ha medido 3 operadores sobre 5 ficheros de ~129, y su rendimiento sobre
    lo que no ejecuta no dice nada
  si las lineas sin ejecutar contienen un defecto de verdad
    NO_CENSADO. Un mutante que sobrevive en una linea no ejecutada no prueba que
    la linea este bien: prueba que nadie la ha llamado
  las ~60 herramientas fuera del alcance de `mutscore`
    NADA ESCRITO. Ni una ha pasado por un self-test que mida su propia cobertura
```

## 5 · La regla, que sale de mirar los 99

```text
  UNA RAMA QUE NADIE EJECUTA NO ESTA PROBADA, ESTE SEA LEGIBLE O NO

  y eso no se arregla con mas vectores de los que ya se ven:
  se arregla ejecutando la rama
```

Es la diferencia entre `NOT_OBSERVADO` y `PROVEN`, aplicada al código: una línea
que nadie ejecuta no está en ningún estado, y un mutante que sobrevive en ella no
informa sobre nada.

Y tiene una consecuencia operativa que es lo que decide la acción siguiente: **el
trabajo útil aquí no es escribir vectores, es llamar a las ramas.** Una herramienta
que puede self-testearse sin hardware —y estas cinco pueden— puede ejecutar su propia
ruta `--json` en su self-test con un solo `run`, y eso convertiría de golpe quince
de las líneas de «BANDERA» en línea cubierta.

## 6 · Trazabilidad

```text
  findings/295 §4ter                    los 472 mutantes y el segundo eje
  tools/mutscore.py --eje2              la particion ejecutada / no ejecutada
  tools/mutscore.py lineas_del_selftest  el settrace que la hace
  las 158 lineas sin ejecutar            en el informe de la vuelta completa
  toolaudit.py:390, :413                la funcion sin probar, escrita hoy
  nextnum.py:470                        la reserva que no se ve a si misma
```

## 7 · Correlación

```text
  294   "puede fallar" no es sintactico; dos detectores mentiron
  295   la mutacion automatizada: 472 sitios, y un punto ciego
  296   ESTE: el segundo eje separa 39 de 189, y los 99 que quedan NO se
        reducen por forma. El trabajo util es ejecutar ramas, no escribir vectores
```

## 8 · Corrección de numeración

```text
  este fichero se escribio como 296, reservado con --reservar antes de escribir
  CORRECTED_BY: --reservar 296  RESERVADO
```