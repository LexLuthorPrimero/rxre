# 1198 — Un bucle `for` con `!=` **no se rechazaba: se ignoraba en silencio**. Y `PACKET3_TEST` tampoco existe: otro nombre que me inventé, y esta vez lo compruebo antes de cambiarlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-RECOVERY
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=ERROR · IMPLEMENTATION · ESTADO=CORREGIDO
CONTINUA=1197 (roundtrip bloqueada por tres eslabones) -> 1198
ORACULO=tools/_orculo_ibref.pyc  116/116  sha256 e0bdb8d023b1…  modo 444
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · El fallo: un `for` no reconocido desaparecía

`desenrollar` recorre **`RE_FOR`**, que exige `<` con comparación estricta. Un bucle con
otra comparación no casa, así que no entra en el bucle de rechazos, no se registra en
`sin_desenrollar`, y **no aparece en ninguna parte**:

```c
for (i = 0; i != 4; i++)   ib.ptr[ib.length_dw++] = 1;
```

El desenrollador devuelve menos filas de las que hay y **no dice por qué**. Para quien
consume el resultado, un bucle ignorado y un bucle vacío son lo mismo, y la diferencia
—que el bucle vacío se ha decidido y el otro se ha olvidado— es exactamente la que decide
si el IB sintetizado es válido.

> Un bucle que no se reconoce y no se reporta no es un bucle que se ignore con seguridad:
> es una fila que falta sin aviso.

## 1 · Los dos regex recuperados que no estaba usando, y para qué son

Del `.pyc`, siete regex con nombre en `co_names`. Seis los usaba. Los dos que no:

```python
RE_FOR_CUALQUIER = r'^[ \t]*for\s*\('
RE_COMPARACION   = r'^(.+?)\s*(==|!=)\s*(.+)$'
```

`RE_FOR_CUALQUIER` encuentra **cualquier** `for`; `RE_COMPARACION` localiza el operador de
comparación. Juntos dan lo que faltaba: no *qué* bucle se rechaza, sino **por qué**.

```python
tomados = {m.start() for m in RE_FOR.finditer(txt)}
for m in RE_FOR_CUALQUIER.finditer(txt):
    if m.start() in tomados:
        continue
    cmp_ = RE_COMPARACION.search(cabecera)
    if cmp_ and cmp_.group(2) != "<":
        motivo = "comparacion `%s`:  solo se entiende `<`..." % cmp_.group(2)
    else:
        motivo = "forma de bucle NO reconocida:  ..."
```

**+1 vector**: `desenrollo RECHAZA: comparación distinta de <`. **105 de 116.**

## 2 · `PACKET3_TEST` tampoco existe, y esta vez lo comprobé antes de tocarlo

Buscando el layout que necesitan los tres vectores de `decode`, la primera comprobación da:

```text
  PACKET3_TEST en las constantes del .pyc:   0 ocurrencias
  PACKET3_TEST en pm4_emit.py:              0 ocurrencias
  PACKET3_TEST en el STUB:                  0 ocurrencias
```

Es un nombre que inventé, del mismo género que `DELTA`, `EPSILON`, `ZETA`, `ETA` y `THETA`
—los otros cinco que también eran míos y que `1196` ya había destapado.

Los literales que **sí** están en el `.pyc`, y son de otro fixture del original:

```text
  'PACKET3(PACKET3_SH, %d)'
  'PACKET3_SH_X(1)'
  'PACKET3(PACKET3_SH, 1)'
  'nombres: SH'
```

## 3 · Y lo que hice con ese dato: probarlo, y **revertirlo**

Sustituí `PACKET3_TEST` por `PACKET3_SH` en el fichero. Resultado:

```text
  antes    105 de 116
  despues  104 de 116
```

Perdí un vector: `decode: el nombre del opcode se resuelve y se imprime` compara contra la
tabla `ops` que **el mismo fichero declara**, así que cambiar el nombre rompe la
coherencia interna. Y `PACKET3_SH` tampoco está en las tablas de `pm4_emit`: no arreglaba
nada.

Revertido a 105, y escrito en el código por qué se prueba y por qué no se queda.

> Mover el nombre del fixture para que mi código dé el número que yo espero es fabricar
> la evidencia. Es exactamente el fallo que `1193`, `1194` y `1196` corrigieron en mí, y lo
> había vuelto a cometer en el minuto siguiente.

La lección no es "no cambiar nombres". Es que **el nombre del fixture es evidencia**: si se
cambia para encajar con una expectativa, el instrumento deja de medir lo que medía y
empieza a medir lo que yo quería que midiera.

## 4 · El estado

```text
  ibref.py   105 de 116      (63 al terminar 1183,  77 al empezar esta sesion)
  rxre       188 vectores rc=0
  huella      27 vectores rc=0
  toolreg     14 checks, 0 failures
  oraculo    116/116  sha256 e0bdb8d023b1…  modo 444

  los 11 que quedan
     7  round-trip   bloqueado por los tres eslabones de 1197:
                      opcode->nombre, partir por `|`, y el literal de la
                      cabecera con el count real
     3  decode       falta el fixture ENTERO:  su opcode (`PACKET3_SH`) y su
                      campo (`SH_X`) estan en el .pyc,  pero la tabla `ops` y el
                      layout de este bloque no se han recuperado
     1  ampliacion   el vector comprueba que una macro exista,  y la macro no
                      esta en pm4_emit,  ni en el STUB,  ni en el .pyc
```

Y queda una observación que no es un fallo sino una propiedad medida:

```text
  de los 116 vectores,  los nombres de fixture que mi reconstruccion se invento
  son AL MENOS:  DELTA, EPSILON, ZETA, ETA, THETA, PACKET3_TEST

  seis nombres de fixture inventados en un solo fichero.  Los seis comprueban
  COMPORTAMIENTO y no el nombre,  asi que la mayoria sobreviven;  pero un
  fixture inventado es un vector que demuestra que el autor sabia lo que
  queria demostrar,  no que el instrumento lo sepa.
```

## 5 · Procedimiento

```text
CORREGIDO  los bucles no reconocidos se rechazan con su motivo,  usando los dos
           regex recuperados que no estaban en uso:  +1
COMPROBADO PACKET3_TEST:  0 ocurrencias en el .pyc,  en pm4_emit y en el STUB
PROBADO   sustituir el nombre por el literal PACKET3_SH
MEDIDO    105 -> 104:  peor,  porque el vector compara contra la tabla que el
           propio fichero declara
REVERTIDO a 105,  con el motivo escrito en el codigo
NO HECHO  recuperar el fixture de decode y de ampliacion
runtime   RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
