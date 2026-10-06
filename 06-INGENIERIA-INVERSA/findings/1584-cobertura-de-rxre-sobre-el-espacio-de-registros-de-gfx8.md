# 1584 — Ítem 7 cerrado: la cobertura de descubrimiento de RXRE sobre esta placa es **22%**, y el denominador correcto son los **11.866 registros que una TU de GFX8 alcanza de verdad**, no los 2.633 de la cabecera nativa

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=EVALUACIÓN-DE-HERRAMIENTA · COBERTURA
CLASSIFICATION=EVIDENCIA-POR-CUENTA+EVIDENCIA-POR-GRAFO-DE-INCLUDES+MUESTRA-DECLARADA
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/rxre_cobertura_gfx8.py  (nuevo,  SELF_TESTED)
MODIFICATIONS=1575 §"DISCOVERY COVERAGE 15/15"  (retirado como cifra no utilizable)
MODIFICATIONS=1576 §defecto (a)  dword_index  (de caso local a prevalencia medida)
CIERRA   el septimo hueco de riesgo cero,  y el ÚLTIMO de la lista de siete
CORRIGE   el 15/15 de 1575  como cifra NO utilizable
DA       la prevalencia del defecto (a) de 1576:  73.4%  de los registros nativos
```

## 1 · Por qué el 15/15 de `1575` no servía, y por qué mi primer intento de arreglarlo tampoco

`1575` dio `DISCOVERY COVERAGE 15/15` sobre `enum SMU_MEMBER`, y ya decía ahí que
"el denominador lo elegí yo y es el conjunto más fácil". Era correcto y no bastaba.

**Mi primer intento de esta ronda fue peor de lo que parecia,  y lo vi al
lanzarlo.** Usé como denominador los `#define mm*` de `gca/gfx_8_0_d.h`: **2.633**,
mucho más respectable que quince `case`. Y es **el caso fácil otra vez, un nivel más
profundo**: ese fichero se llama `gfx_8_0`, así que casa con el filtro `--gfx gfx_8_0`
de RXRE y resuelve siempre.

Lo vi al lanzar el trabajo y al preguntarle por `mmSMC_IND_DATA_11`:

```text
  mmSMC_IND_DATA_11   byte_offset 0x1AD   dword_index 0x6B   chosen  None
```

`chosen: None`, con `--gfx gfx_8_0`, para un registro que **esta placa usa en su camino
real**. Así que el 2.633 no era un denominador, era el subconjunto que la herramienta
ya sabe resolver.

## 2 · El denominador que sí sirve: lo que una TU de GFX8 alcanza de verdad

No lo elijo yo. Lo define el **grafo de includes de la propia placa**, el mismo
criterio que `1546`, `1578` y `1579` han venir usando:

```text
  pm/powerplay/inc/smu7_common.h:30-50,  el juego de registros de GFX8
```

| cabecera | estado | generación | `#define mm*` |
|---|---|---|---|
| `smu/smu_7_1_3_d.h` | **PRESTADO** | 7.1.3 | 133 |
| `gmc/gmc_8_1_d.h` | **PRESTADO** | 8.1 | 1.156 |
| `bif/bif_5_0_d.h` | **PRESTADO** | 5.0 | 475 |
| `dce/dce_10_0_d.h` | **PRESTADO** | 10.0 | 6.924 |
| `gca/gfx_8_0_d.h` | **NATIVO** | 8.0 | 2.633 |
| `oss/oss_3_0_d.h` | **PRESTADO** | 3.0 | 545 |

```text
  TOTAL alcanzable desde una TU de GFX8        11.866
  en cabeceras PRESTADAS                        9.233   =  77.8%
  en la cabecera NATIVA gca/gfx_8_0_d.h         2.633   =  22.2%
  nombres definidos en mas de una del juego          0   (los conjuntos son disjuntos)
```

**Ese último cero es lo que hace el resultado limpio:** como los seis conjuntos son
disjuntos, cada registro tiene **una** cabecera de origen, y el filtro de RXRE --
que Casa por la generación que lleva el nombre del fichero -- **solo puede acertar en
la única cuyo nombre es `8_0`.**

## 3 · La medición que confirma la predicción: 25 de 25

Cinco nombres por cabecera, con paso uniforme sobre la lista ordenada —método de
selección declarado, no elegido por resultado—:

```text
  cabecera            estado      n_def  chosen    veredicto
  ---------------------------------------------------------------------------
  smu_7_1_3_d.h      PRESTADO        6-7  None      SIN ELEGIR   (5/5)
  gmc_8_1_d.h        PRESTADO        2-8  None      SIN ELEGIR   (5/5)
  bif_5_0_d.h        PRESTADO        3-5  None      SIN ELEGIR   (5/5)
  dce_10_0_d.h       PRESTADO       1-12  None      SIN ELEGIR   (5/5)
  gca/gfx_8_0_d.h    NATIVO         6-10  dict      OK           (5/5)
  oss_3_0_d.h        PRESTADO       3-10  None      SIN ELEGIR   (5/5)
```

```text
  cobertura medida sobre el denominador HONESTO:   22.2%
  (muestra de 30 sobre 11.866,  más el argumento estructural que la cierra)
```

**Y esto NO es "RXRE no encuentra el productor".** La columna `n_def` vale entre 1 y
12: **RXRE encuentra las definiciones.** Lo que hace es no elegir ninguna. El estado
correcto es `RXRE COVERAGE GAP` con causa nombrada:

```text
  el selector --gfx  casa con la GENERACION que lleva el nombre de la cabecera
  gca/gfx_8_0_d.h   -> "8_0"  ->  casa
  gmc/gmc_8_1_d.h   -> "8_1"  ->  no casa con gfx_8_0
  smu/smu_7_1_3_d.h -> "7_1"  ->  no casa

  CAUSA:  la relacion de PRESTAMO no esta declarada.  RXRE sabe donde esta cada
  definicion  y sabe que ASIC la usa,  pero no modela "este ASIC se con
  cabeceras de otra generacion".
```

**Que es exactamente la función que ya pedí** cuando me preguntaste qué necesita RXRE
para mapearlo todo: *"route `--for<ASIC>` por grafo de includes"*. Ahora está medido
en cuántos registros, no en palabras.

## 4 · Y el otro defecto, cuantificado: `dword_index` es inválido en el 73,4% de los nativos

`1576` registró el defecto (a) como un caso local: para `mmSMC_IND_DATA_11` en `0x1AD`,
`dword_index = byte_offset // 4` trunca a `0x6B` y direcciona **su propio par**, que es
un lazo de escritura. Lo presenté como un bug de un registro. **Es una regla general,
y el alcance se mide:**

```text
  denominador:  los 2.633 #define mm* de gca/gfx_8_0_d.h
  (la regex exige que el valor sea lo ultimo de la linea;  el grep de control
   cuenta las mismas 2.633 lineas ->  no se ha perdido ninguna)

  offsets NO alineados a 4:      1.933 de 2.633   =  73.4%
  offsets alineados a 4:            700
```

Demostración directa sobre tres:

```text
  registro            byte_offset   dword_index
  mmSMC_IND_DATA_11      0x1AD         0x6B     (0x1AD // 4)
  mmCB_BLEND_RED         0xA105        0x2841
  mmCP_BUSY_STAT         0x219F        0x867
```

Y el dato que hace el hallazgo incómodo: **la unidad que RXRE declara para sí misma es
la correcta.**

```text
  unit = "byte offset (contrato del kernel)"
```

El `byte_offset` es un byte, que es lo que quiere el kernel. **`dword_index` es un campo
extra, y para el 73,4% de la población no significa nada.** No es que dé un valor
raro: es que un índice de dword **no existe** para un registro de granularidad de byte.
Un campo así no debería salir sin condición, o debería salir marcado como inválido.

**Esto es una consecuencia física, no un descuido de la herramienta:** los registros de
`CB_*`, `DCC`, `SPI_SHADER_PGM` y compañía están en el espacio byte-granular del
color buffer. `0xA105` es un byte de un registro de mezcla. La unidad correcta para
ellos es el byte, y `1578`/`1579` ya sostienen que el kernel sí lo trabaja así —el
`mmSMC_IND_DATA_11` en `0x1AD` es byte-granular de verdad.

## 5 · La herramienta que hice para esto, y en qué estado

```text
  tools/rxre_cobertura_gfx8.py
    estado        SELF_TESTED      (no VALIDATED)
    denominador   NO lo elige el script:  es un diccionario del arbol
    oraculo       regex DISTINTA de la de rxre,  para que no compartan fallo
    salida        JSONL incremental,  una linea por registro  ->  un corte no
                  tira el trabajo hecho
    modos         --mutacion   cambia el valor esperado y exige que el veredicto
                               cambie
                  --muestra N  submuestra con paso uniforme sobre la lista
                               ordenada,  y declara el metodo
    autocomprobacion ejecutada:  8/8 "ok"  en modo normal
                                 8/8 "DIVERGE"  con el oraculo mutado
```

**La autocomprobación es lo que da valor al número**: si el oráculo se mueve y el
veredicto no, el script está mintiendo. Mutarlo lo detecta en los 8 casos.

**Lo que NO le he hecho y por tanto no es `VALIDATED`:** una prueba deKnown-vectors con
respuesta conocida de RXRE, ni una comprobación cruzada con un segundo productor del
valor. Con un solo oráculo, un fallo compartido no se ve. Queda anotado.

## 6 · Una corrida completa en marcha, y lo que va a dar

```text
  artefacto   artifacts/rxre_cobertura_gfx8.jsonl
  alcance     los 2.633 mm* de gca/gfx_8_0_d.h
  avance      66 de 2.633   al cierre de este hallazgo   (2%)
  reparto     {"ok": 66}
  coste       ~1.8 s por registro,  reconstruye el indice en cada invocacion
```

**La prediction es 2.633 / 2.633 `ok`, y por eso la lanzo igual:** convierte
"el caso nativo funciona" de una muestra de cinco en una cifra completa, y da el
contraste exacto contra el 22,2%. **No la presento como cobertura general**, porque es
el 22% fácil. Cuando termine, la cifra que importa sigue siendo la de arriba.

## 7 · Procedimiento y alcance

```text
PREGUNTA   cual es la cobertura de descubrimiento de RXRE sobre el espacio de
           registros que ESTA PLACA usa,  con un denominador que no sea mio
FUENTES    smu7_common.h:30-50  (el juego de cabeceras de GFX8)
           conteo de #define mm* por cabecera,  con el estado prestado/nativo
           el solapamiento entre los seis conjuntos
           muestra de 5 por cabecera,  con paso uniforme sobre la lista ordenada
           alineacion a 4 de los 2.633 nativos,  con regex y con grep de control
           ejecucion de rxre register --gfx gfx_8_0 --json-only  en 35 registros
MEDIDO     11.866 registros alcanzables desde una TU de GFX8
     9.233 (77.8%) en cabeceras prestadas;  2.633 (22.2%) en la nativa
     los seis conjuntos son DISJUNTOS:  0 nombres en mas de una cabecera
     muestra 25/25 prestadas -> chosen None ;   5/5 nativas -> elegido
     cobertura sobre el denominador honesto:  22.2%
     n_def entre 1 y 12 en las prestadas  ->  las encuentra,  no las elige
     1.933 de 2.633 nativos (73.4%) con offset no multiple de 4
     rxre declara  unit = "byte offset (contrato del kernel)"  ->  correcto
DESVIO MIO  uno,  y el mas caro de la ronda
     escogi gca/gfx_8_0_d.h como denominador PORQUE ERA FACIL,  y solo lo vi al
     preguntarle por mmSMC_IND_DATA_11  y ver chosen None.  El 15/15 de 1575 y mi
     2.633 eran el mismo error con distinto disfraz.  Lo que lo salva no es el
     criterio del grafo de includes  —que ya use desde 1546—  sino preguntar por
     un registro que yo SABIA que esta placa usa  y no por una muestra ciega
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 8 · Lo que sigue

```text
  huecos de riesgo cero de la lista de siete:  CERRADOS LOS SIETE
    1577 dispatch · 1578 la struct de esta placa · 1579 el bit de auto-incremento
    1580 el opcode que no era pendiente · 1581 la sincronizacion PFP<->ME
    1582 alcanzabilidad de LOAD_*_REG · 1583 el linaje por offset · 1584 cobertura

  El veredicto sobre RXRE queda,  con numeros y no con adjetivos:
    INCREMENTAL_VALUE           para descubrimiento y procedencia  (1575)
    COVERAGE GAP con causa      el 77.8% del espacio de GFX8  (este)
    UNTRUSTWORTHY_FOR_CLAIM    para dword_index,  invalido en el 73.4%
    NO_LAUNDERING               (1575)

  y sigue en pie lo unico que cierra soft_regs_start:  el valor de
    SMC_RAM[0x20030].  Con la receta del driver (1579),  las dos direcciones
    confirmadas en los tres linajes,  y pendiente de tu OK
```