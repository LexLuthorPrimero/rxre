# 309 · El allocator de numeros era ciego a los hallazgos 1000-1020, y por eso podia entregar un numero ya usado

```
PENDIENTE=309-1 | HALLAZGO=309-el-allocator-no-veia-los-numeros-de-cuatro-cifras.md
             | ESTADO=NOT_DETERMINED
             | NECESITA=CORPUS | ALCANZABLE_SIN_ROOT=si
```

## Que paso

`run_all.py` reporto `FALLA [objetivo] findnum: control negativo`, con un
`AttributeError` en vez de un fallo de asercion:

```
  File "tools/findnum.py", line 94, in reservations
    n = int(re.match(r"^(\d{3})-", name).group(1))
  AttributeError: 'NoneType' object has no attribute 'group'
```

La causa era un patron de ancho EXACTO. `\d{3}` casa con "298" y no con
"1000", y `.group(1)` sobre un `None` revienta.

## El defecto es mas grande que el crash

El crash es visible. Lo que no lo era:

```
                                  antes    despues
  numeros que ve el allocator       411      420
  maximo que ve                     999     1020
  ¿ve el 1000?                     NO       SI
```

`used_numbers()` es la funcion que decide si un numero esta ocupado. Con
`\d{3}` **no contaba los hallazgos de cuatro cifras que existian en disco**, de modo que
`next_free` podia devolver un numero que ya tenia fichero. El allocator
respondia, y respondia mal: el fallo es silencioso y se manifestaba al
escribir encima de un hallazgo existente, no al reservar.

Medido el alcance de la ceguera, sobre el estado actual:

```
  ficheros en disco                       521
  numeros que ve el allocator             420
  maximo que ve el allocator             1020   (antes: 999)
  numeros con mas de un fichero            74   <- ver 308
```

La cuenta no cierra y no debe: 520 ficheros, 420 numeros distintos, 74 de esos
numeros con dos o tres ficheros. La aritmetica de "ficheros = numeros" no aplica
a este corpus, y por eso el alcance de la ceguera se mide por su maxima y no
por un recuento derivado.

La cifra crecio porque el corpus ha seguido creciendo durante la medicion (hoy
hay 521 ficheros y antes habia 520). Lo que no cambia es la cuenta que
importa: el allocator ve 420 numeros donde `escanear()` ve mas, y el maximo que
ve es 1020 frente a los 999 que veia antes.

## Porque el mismo fichero ya lo sabia

`findnum.py` tiene el aviso escrito, en `used_numbers()`, unas lineas mas abajo:

```
  # \d{3,} y NO \d{3}. Un ancho de tres es un ancho EXACTO: en cuanto aparezca
  # la nota 1000, "1000-algo.md" deja de casar y used_numbers deja de verla...
  m = re.match(r"^(\d{3,})-", name)
```

La mitad de LECTURA de numeros de este fichero ya estaba corregida, con el
razonamiento escrito. La mitad de RESERVAS, treinta lineas mas abajo, seguia
con `\d{3}`. La incoherencia estaba dentro del mismo fichero y el comentario
que la explica estaba a la vista.

Eso es el patron, y es el mismo de los hallazgos anteriores: **la mitad de
escritura y la mitad de lectura no decian lo mismo**, y una se arreglo sin
arreglar la otra.

## Alcance: tres ficheros, un defecto

El mismo patron aparece en tres sitios distintos, y los tres se han medido:

```
  08-ARQUITECTURA/tools/findnum.py   used_numbers()     {3,}  ya estaba
  08-ARQUITECTURA/tools/findnum.py   reservations()     {3}   CRASH en run_all
  08-ARQUITECTURA/tools/findnum.py   (via nextnum)      {3}   --check 1000 rechazaba
  tools/nextnum.py                   NUM_RX             {3}   no contaba 9 hallazgos
  tools/nextnum.py                   validar()          {3}   rechazaba "1000"
  tools/nextnum.py                   leer .nextnum.lock  {3}   no leia reservas de 4
  08-ARQUITECTURA/tools/findings_index.py  RE_NUM      {3}   9 hallazgos invisibles
  08-ARQUITECTURA/tools/refs_repair.py     RE_CITA     {3}   no veia citas de 4
```

Y uno mas que queda, que se dejo fuera a proposito:

```
  08-ARQUITECTURA/tools/findings_index.py  RE_REF      {3}   SIN USAR
```

`RE_REF` esta definido en `findings_index.py:250` y no lo referencia ningun
otro fichero (los tres `FIXTURE_REF` de `revkit/emitref.py` son otra cosa). Es codigo muerto con el mismo defecto. No se toca porque arreglar un
regex que nadie ejecuta es cambiar algo sin medir si estaba haciendo algo: lo
que si se puede afirmar es que esta muerto, y que si algun dia se usa, fallara
igual que los otros siete.

Siete regex con el mismo defecto, en tres herramientas, y **ninguno de sus
tests lo cazaron** hasta que el corpus cruzo los 999.

## Por que los self-tests no lo cazaron

Porque todos probaban con numeros de tres cifras. Un vector de prueba tiene
que usar el valor que rompe, no un valor que funciona. Los tres patrones que
fallaron tenian el mismo problema: el self-test usaba `123`, no `1000`.

Consecuencia practica: **"el self-test pasa" no es evidencia de cobertura**.
Solo lo es si el vector incluye el caso limite.

## Que se ha hecho

- `reservations()` a `\d{3,}`, con `continue` explicito si aun asi no casa.
- `nextnum.py`: `NUM_RX`, `reservar()`, `--check` y la lectura de
  `.nextnum.lock`, las cuatro.
- Verificado: el allocator ve 420 numeros con maximo 1020, y
  `--check 1000` responde `unico` con el nombre del fichero real.
- Mutado cada cambio a la version anterior: las cuatro vuelven al
  comportamiento viejo, medido. Un patron que no se puede volver a romper no
  esta arreglado.

**Estado: `PROVEN`.** El defecto estaba, la ceguera estaba, la correccion esta
comprobada por conteo antes y despues.

## Lo que sigue abierto

`298` sigue reservado en `.nextnum.lock` sin fichero (ver 307). Con este
arreglo, el allocator ya lo ve como ocupado, que es lo correcto: no entregara
el 298. Pero **sigue sin haber un hallazgo 298**, y eso es un agujero en el
corpus, no un fallo de la herramienta.
