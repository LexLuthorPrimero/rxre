# 1195 — Un filtro que **no filtraba nada** y no daba ningún error: `set.update(tuple(r) for r in …)` metía cada tupla como elemento único. Y mi propio selftest tiene **dos vectores duplicados** — 117 llamadas para 116 vectores

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=ERROR-REPORT + SELF-AUDIT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py
CLASE=ERROR · TEST · ESTADO=CORREGIDO_Y_AUDITADO
CONTINUA=1194 (85->102)  ->  1195 (102->105)
ORACULO=tools/_orculo_ibref.pyc  116/116  sha256 e0bdb8d023b1…  modo 444
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST
```

## 0 · El mejor bug de la serie, y no daba ningún error

```python
fuera.update(tuple(r) for r in (consumidos or ()))
```

`set.update` itera su argumento y **mete cada elemento que aparece**. Aquí el generador
*yield* una sola cosa por vuelta: **la tupla** `(2, 3, 4, 5)`. Así que `fuara` acababa
siendo

```text
  {(2, 3, 4, 5)}        un conjunto de TUPLAS
  3 in fuera -> False   porque en el set hay una tupla, no un 3
```

El filtro de escrituras no filtraba. Un `if` cuya condición valía cero emitía **igual** sus
escrituras, y el IB sintetizado incluía paquetes que el driver no emite bajo esa
configuración. Sin excepción, sin aviso, sin `KeyError`.

Y el detalle que lo escondía:

```python
tuple(r)          # r YA es una tupla:  es un no-op
```

Un no-op en el sitio del bucle hace que un **fallo de tipo** no llegue aostring. Si
`consumidos` llega como lista de enteros sueltos —que es lo natural—,
`tuple(2)` habría sido `TypeError` y el bug se habría visto al primer uso.

> Un no-op en el sitio del bucle hace que un fallo de tipo no se vea.

Corregido distinguiendo los dos casos explícitamente, en vez de adivinar:

```python
for r in (consumidos or ()):
    if isinstance(r, int):
        fuera.add(r)
    else:
        fuera.update(r)
```

**+1 vector** (`cond: lo que NO se emite no sale en la lista de escrituras`).

## 1 · El decimal: el cuidado estaba en el sitio equivocado

`normalizar` hacía

```python
expr.replace("->", "_").replace(".", "_")
```

y el regex que sí distingue miembro de punto decimal (`RE_PUNTO_MIEMBRO`, que exige
**letras** a ambos lados del punto) se aplicaba **después**, en `_alias`. Para cuando
llegaba, el texto ya no tenía ningún punto: `0.5` era `0_5`.

```text
    el cuidado puesto despues del hecho ya no cuida nada
```

`RE_PUNTO_MIEMBRO` se movió **por encima** de `normalizar`, que es donde tiene que estar.
`ib.flags` → `ib_flags` sigue igual; `0.5` se queda `0.5`. **+1 vector.**

## 2 · El `if` sin llaves: proteger la ausencia de flujo no depende de la sintaxis

La exclusión de `propagar_locales` usaba `RE_IF_BLOQUE`, que exige llaves. Un `if` sin
llaves —`if (x)` seguido de una sentencia— no se excluía, y su contenido se propagaba:

```text
  b = 1;
  if (x)
          b = 2;        <- el vector espera que NO se propague

  MEDIDO:  {'b': 2}
```

> Lo que se protege es la ausencia de flujo, y un `if` sin llaves sigue sin tener flujo.
> Que no lleve llaves no lo convierte en una asignación incondicional.

Añadido `RE_IF_SIN_LLAVES`, que excluye la sentencia siguiente. **+1 vector.**

## 3 · Y el hallazgo sobre mi propia reconstrucción: hay vectores repetidos

Contando las llamadas a `chk` sale **117** para los **116** vectores del oráculo. Buscando
nombres repetidos:

```text
  2  comentarios: quitar un comentario NO desplaza las lineas posteriores
  2  comentarios: el contenido del comentario desaparece pero el sitio no
```

Dos nombres duplicados. Es decir: de mis "116 vectores", dos prueban lo mismo dos veces, y
por tanto **falta uno**. Comparando los nombres contra las constantes de `selftest` del
`.pyc`:

```text
  del oraculo que me faltan de verdad
    ampliacion: la prueba de roots se pudo ejecutar
```

Los demás huecos de la comparación son formatos —`ALIGN: %s == %d`, `desenrollo RECHAZA: %s`,
`SELFTEST OK: %d vectores`— que en el oráculo son una cadena y en el mío cuatro o seis
llamadas. Eso no es una discrepancia: es el formato haciendo su trabajo.

> Es la **tercera** duplicación que encuentro en tablas de este árbol, después de
> `radeontop` en `toolreg` y `spatch` en `rxre`. Las tres estaban en tablas escritas a
> mano, y las tres se encontraron mirando los **nombres**, no el comportamiento: un
> vector repetido pasa, y pasar es lo que se supone que tiene que hacer.

Los dos duplicados no están corregidos aquí: corregirlos es quitar una `chk`, y antes
hay que saber cuál de las dos es la buena. Eso es trabajo de oráculo, no de conteo.

## 4 · El saldo

```text
  1183 (reconstruccion)     63 / 116
  1193                     77 -> 85       +8
  1194                     85 -> 102     +17
  1195                    102 -> 105      +3
                           ─────────────
                           +42 desde la reconstruccion, en tres hallazgos

  queda
    round-trip   7   los seis estados con su formato y los fixtures.  El contrato
                      esta RECUPERADO del .pyc: sintaxis `CAMPO[hi:lo]` ->
                      "%d:%d" y `CAMPO[N]` -> "%d (lsb solo)", regex
                      \b%s\s*\[\s*(\d+)\s*:\s*(\d+)\s*\] y
                      \b%s\s*\[\s*(\d+)\s*\], ocho claves por fila
                      (paquete, dword, payload, campo, esperado, rango, leido,
                      veredicto) y el orden de veredictos
                      NO_EXTRAIBLE -> VALOR_NO_AISLABLE -> OK_SOLO_UN_BIT -> OK
                      -> MISMATCH -> FUERA_DE_PAQUETE
    decode       3   falta el layout declarado de PACKET3_TEST
    desenrollo   1   RECHAZA: comparacion distinta de `<`
    ampliacion   1   PACKET3_TEST no esta en ningun lado, ni en pm4_emit ni en el
                      stub:  no se puede saber de donde deberia salir
```

## 5 · Procedimiento

```text
CORREGIDO  el filtro de consumidos, que no filtraba            +1
CORREGIDO  RE_PUNTO_MIEMBRO antes de normalizar, no despues    +1
CORREGIDO  el if SIN LLAVES tambien es ausencia de flujo        +1
AUDITADO   117 llamadas a chk para 116 vectores
           2 nombres duplicados  ->  falta 1 vector
           el que falta: "ampliacion: la prueba de roots se pudo ejecutar"
NO HECHO   quitar los dos duplicados:  hay que saber cual de las dos
           llamadas es la buena,  y eso lo dice el .pyc,  no el conteo
runtime    RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
