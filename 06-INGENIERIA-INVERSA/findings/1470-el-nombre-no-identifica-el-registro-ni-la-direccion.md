# 1470 — Ni el nombre ni la dirección identifican un registro: hacen falta las dos cosas, y hay un fallo de grep que produce `NOT_FOUND` falsos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

ARTEFACTO MEDIDO=rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/include/asic_reg
                  224 ficheros en indice, 246 leidos, 84,5 MB
HERRAMIENTA NUEVA=tools/regalias.py 1.0.0   33 vectores, 33 PASS, exit 0
CROSS-CHECK=3 de 3 con grep puro, sin usar la herramienta

CORRIGE=una premisa mia de dos veces en la misma sesion:
         - `_is_field` exigia `__` en el nombre y dejaba entrar los `_DEFAULT`
         - los vectores pedian 4 direcciones donde hay 3
NUEVO=la clase de fallo que produce `NOT_FOUND` falsos (§16)
```

## 0 · RESUMEN

`1412` mide que `0x0bcc` son 10 símbolos en 5 bloques y que el contexto decide cuál
es. Dio la impresión de que el caso era raro. **No es raro: es la regla general.**

MEDIDO sobre las cabeceras `asic_reg` de este corpus:

| magnitud | valor |
|---|---|
| definiciones de registro leídas | 458 273 |
| direcciones distintas | 56 239 |
| direcciones definidas en **más de un bloque** | **15 044 (26,75 %)** |
| bloques distintos en la dirección más ambigua | **29** |
| símbolos distintos | 136 492 |
| símbolos definidos en **más de una dirección** | **42 505 (31,14 %)** |
| direcciones del símbolo más ambiguo | **9** |
| símbolos escritos con **más de un ancho** de literal hex | **9 197** |
| direcciones escritas con más de un ancho de literal | 2 099 |

**Las dos mitades fallan.** Una dirección no nombra un registro, y un nombre de
registro no direcciona uno. La clave fiable no es el bloque: es **el fichero**.

## 1 · LA DIRECCIÓN NO IDENTIFICA

`regalias.py 0x504` sobre este corpus:

```text
0x0504  bloques=8  simbolos=32
```

Ocho bloques distintos definen `0x504`. El hallazgo `1401` afirma
`mmVM_CONTEXT0_CNTL = 0x504`, y es cierto — pero sólo dentro de `gmc`.

```text
  0x0504  [gmc ]  mmVM_CONTEXT0_CNTL
  0x0504  [nbio]  cfgBIFPLR0_LINK_CAP_32GT
  0x0504  [vcn ]  mmUVD_LMI_JRBC_RB_64BIT_BAR_HIGH
  0x0504  [gc  ]  mmSDMA3_PAGE_CSA_ADDR_LO
  0x0504  [dce ]  mmAZALIA_F0_CODEC_FUNCTION_PARAMETER_GROUP_TYPE
  0x0504  [dcn ]  mmMPC_CRC_RESULT_AR
  0x0504  [mmhub]  mmMMEA2_DRAM_RD_GRP2VC_MAP
  0x0504  [nbif]  cfgBIF_CFG_DEV0_EPF0_LINK_CAP_32GT
```

**La causa, medida:** el offset reinicia en cada bloque de IP. Por eso las
direcciones más ambiguas son las triviales: `0x0040` la definen 29 bloques con 146
símbolos, y `0x0000`, `0x0001`, `0x0041`, `0x0042` la definen 28 cada una.
Verificado por grep crudo, 29 directorios distintos.

Esto no es un defecto del catálogo de AMD: es la estructura del hardware. Un
`WAVES` en la dirección `0x40` de la IP de display y un `0x40` de la IP de
memoria **son registros distintos en buses distintos**, y el corpus tiene razón
en definir los dos.

## 2 · EL NOMBRE TAMPOCO IDENTIFICA

Ésta es la parte que no esperaba, y es la que cambia el método.

```text
$ regalias.py --simbolo mmVM_CONTEXT0_CNTL
0x0504  [gmc  ]  gmc/gmc_6_0_d.h, gmc_7_0_d.h, gmc_7_1_d.h, gmc_8_1_d.h, gmc_8_2_d.h
0x06c0  [mmhub]  mmhub/mmhub_1_0_offset.h, mmhub_9_1_offset.h, mmhub_9_3_0_offset.h
0x0880  [gc   ]  gc/gc_9_0_offset.h, gc_9_1_offset.h, gc_9_2_1_offset.h
```

**El mismo nombre, tres direcciones y tres bloques.** Y `mmIH_STATUS`:

```text
0x00c2  [oss]  oss/osssys_4_0_1_offset.h, osssys_4_0_offset.h, ...
0x0e38  [oss]  oss/oss_2_4_d.h, oss_3_0_1_d.h, oss_3_0_d.h
0x0f88  [oss]  oss/oss_1_0_d.h, oss_oss_2_0_d.h
```

Aquí hay un matiz que el directorio esconde: **`osssys_*.h` vive dentro de
`oss/` pero es otra IP** (OSSYS, no OSS). Está medido con un vector de prueba.
Así que el directorio — que fue mi primer intento de bloque — tampoco basta.

**La generación sólo existe en el nombre del fichero.** `gmc_7_1_d.h` frente a
`gmc_8_1_d.h` es lo único que separa dos ASIC. Y para esta tarjeta el fichero
correcto está fijado por fuera, medido en `1459` §0:

```text
/usr/share/umr/database/polaris12.asic
    gmc810  ->  ip/gmc_8_1_0.reg
```

**regalias.py --simbolo mmVM_CONTEXT0_CNTL --cabecera gmc_8_1_d.h** marca
`0x0504` como la definición de esta ASIC. Sin ese dato, `0x06c0` y `0x0880`
son registros igual de válidos en otro bloque.

## 3 · EL FALLO QUE PRODUCIRÍA `NOT_FOUND` FALSOS

Encontré una contradicción entre la herramienta y un grep mío, y la resolví antes
de escribir nada (§80). El grep decía 1 bloque para `0x504`; la herramienta decía
8. **Tenía razón la herramienta, y la razón es un fallo de método:**

```bash
grep -rn "^#define [A-Za-z_0-9]*  *0x504$" --include=*.h .   ->  4 ficheros, 1 bloque (gmc)
```

El mismo valor se escribe con padding distinto según el fichero:

```text
gmc/gmc_8_1_d.h:601          #define mmVM_CONTEXT0_CNTL    0x504
nbio/nbio_7_7_0_offset.h:1955 #define cfgBIFPLR0_LINK_CAP_32GT  0x0504
```

`0x504$` no casa con `0x0504`, y `0x0504$` no casa con `0x504`. MEDIDO: 9 197
símbolos están escritos con más de un número de dígitos.

**Por qué esto es el peor tipo de fallo del proyecto.** Un error de padding
produce **menos** resultados, no más. El `NOT_FOUND` que sale de ahí es
indistinguible de una ausencia real, y el `§16` obliga a no concluir ausencia sin
alcance suficiente. Este error rompe exactamente esa regla sin que nada lo delate:
`grep` sale con 0, la cadena es válida, y el artefacto "existe".

`1459` resolvió `0x0bcc` por contexto después de un trabajo de identificadores de
cadena de 6 saltos. Ese trabajo se hizo porque el primer `grep` no dio un nombre
único. **La causa de fondo era esto.**

## 4 · LOS ERRORES PROPIOS, QUE SON EL OTRO HALLAZGO

Cuatro, y tres los detectó la propia herramienta mediante vectores. Los dejo
escritos porque el §93 dice que un hallazgo que solo confirma no compensa uno que
corrige.

**4.1 · `_block_of` con la condición invertida.** Pedía `len(parts) > 1` para
saber si no estaba en la raíz, pero para `asic_reg/oss` la ruta relativa es
`"oss"`, de **una** componente. Los 488 ficheros se atribuían a un bloque único
llamado `raiz`, y la ambigüedad multibloco salía **0 sobre 57 453 direcciones**.
Una proporción de cero no es un dato: es un error con aspecto de dato.

**4.2 · `simbolos` tenía dos tipos según el camino.** Sin `--bloque` salía una
lista de tuplas `(símbolo, bloque)`; con `--bloque`, una lista de strings. Dos
vectores lo detectaron. El mismo campo con dos tipos es un fallo de contrato de
salida (§25), no un detalle de formato.

**4.3 · `_DEFAULT` no se excluía.** El filtro pedía `__` en el nombre, pero
`mmVM_CONTEXT0_CNTL_DEFAULT` no lo tiene. Los valores por defecto entraron en el
índice de direcciones y `0x0000` apareció como la dirección más ambigua del
corpus con 47 032 símbolos. **El máximo del catálogo era basura.** Corregido a
`_MASK`, `_SHIFT` o `_DEFAULT`, sin condición de `__`. Las cifras de la tabla de
§0 son las de después.

**4.4 · Los vectores repetían la misma trampa que la herramienta.** Pedían 4
direcciones para `mmVM_CONTEXT0_CNTL` cuando hay 4 *escrituras* y 3
*direcciones*: `0x504` y `0x0504` son el mismo valor. El vector afirmaba la
ambigüedad de padding en el sitio donde el tool la normaliza. **Un test malo
enseña el error que dice corregir.**

## 5 · LO QUE ESTO CIERRA Y LO QUE ABRE

```text
CIERRA
  1412     el alcance del caso 0x0bcc: no es una rareza, es el 26,75 %
  1459 §0  la identificacion por bloque: el bloque es NECESARIO y NO SUFICIENTE
  1440 §4  por que un grep por direccion no puede cerrar un nombre
  1412     el metodo de identificacion por cadena de 6 saltos: era un
           rodeo contra una trampa del catalogo, no una propiedad del ASIC

ABRE
  +  la GENERACION es parte de la clave, y no hay ninguna fuente en el driver
     que diga que fichero se incluye para QUE ASIC.  El mapa esta en el nombre
     del fichero, disperso, y nadie lo lee.  Esto es un hueco real de
     observabilidad, no una tarea de limpieza.
  +  para ESTA tarjeta el subconjunto aplicable es gmc_8_1_d.h / gca gfx_8_0_d.h.
     Falta un indice (bloque, generacion) -> fichero, y el orculo de umr ya da
     parte de la columna de generacion.
  +  el impacto en las citas existentes hay que revisarlo: cualquier afirmacion
     del tipo "X = 0xNNN" escrita sin fichero de procedencia es incompleta,
     aunque sea correcta para esta ASIC.
```

## 6 · ESTADO DE LA HERRAMIENTA

```text
regalias.py 1.0.0
  vectores    33, 33 PASS, exit 0
  alcance     SELF_TESTED -> VALIDATED, con la salvedad del §22:
              validado contra vectores observables en ESTE corpus. Si el corpus
              cambia de version, los vectores fallan, y eso es lo correcto.
 .cross-check 3 de 3 con grep puro, sin usar la herramienta:
              - mmVM_CONTEXT0_CNTL en 3 direcciones  (4 escrituras, 2 paddings)
              - 0x06c0 en mmhub_1_0/9_1/9_3_0 y 0x0880 en gc_9_0/9_1/9_2_1
              - 0x0040 en 29 directorios
  modo nuevo  --simbolo (consulta inversa), --cabecera (fijar generacion)
  coste       1,6 s el indice, 84,5 MB leidos. Se saltan los 221 ficheros
              _sh_mask.h (396,8 MB, 82 % del arbol) porque solo contienen
              campos de bit, que el indice descarta. Sin ese salto la consulta
              no terminaba en 120 s.

LIMITE DECLARADO
  regalias.py NO decide que registro es el correcto. Solo hace visible que la
  pregunta tiene mas de una respuesta. Decidir es trabajo del contexto: el
  bloque que emite el codigo, el valor que escribe, la cabecera de la ASIC.
  Un numero unico de esta herramienta NO seria una mejora: seria una mentira.
```

## 7 · LA LECCION, PORQUE ES LA QUE MAS ME HA COSTADO

Cinco hallazgos seguidos de esta sesion (`1404`, `1421`, `1412`, `1420`, `1442`)
afirmaron algo que el fichero decia a tres lineas de distancia. Siempre por el
mismo motivo: **el primer resultado de un grep no es un resultado, es una
muestra.**

Y hay un caso peor que el primer resultado equivocado: el primer resultado que
**falla en silencio**. Un `grep` que devuelve 1 bloque en lugar de 8 no señala
nada. Solo lo señala el recuento — que es lo único que este hallazgo produce.
