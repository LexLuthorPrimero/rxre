# 1138 — Desenrollado de bucles: la IB de inicialización de shader de GFX8 pasa de 42 dwords (11 resolubles) a **186 dwords (54 registros con nombre)**. Y un bug de números de línea producía **5 dwords duplicados** sin decirlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=IMPLEMENTATION · VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py       (desenrollar, +18 vectores)
                              tools/verif.py       (3 medidas, 44 -> 46/48)
                              08-ARQUITECTURA/artifacts/R12-DESENROLLO/{ib.txt,
                              ib.json, mmio.txt}
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4_emit.py, gfx_v8_0.c INTACTOS
CLASSIFICATION=IMPLEMENTATION · VALIDATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=DESENROLLADO OPERATIVO Y CON CONTRATO DE RECHAZO PROBADO
```

## 0 · El resultado, primero

```text
                          ANTES        DESPUES
dwords escritos              42            186
completos                    33            177
incompletos                   9              9

bucles desenrollados           0   ->  3 x 17 iteraciones = 153 dwords
registros con nombre (mmio)    3   ->  54
duplicados                     ?   ->  0   (medido, y hubo 5 antes)

puerta      44 -> 46 medidas declaradas, 48 en total
vectores    ibref 39 -> 57, rc=0
```

Y una corroboración que no busqué: el propio driver calcula el tamaño del IB
con `ARRAY_SIZE(vgpr_init_regs) / 2` y `* 3` dwords por vuelta. **17 pares × 3
dwords = 51**, tres veces. Mi aritmetica de desenrollado coincide con la del
driver que escribio el codigo.

## 1 · EL BUCLE, Y POR QUÉ ERA EL CUELLO

```c
/* gfx_v8_0.c:1528 */
for (i = 0; i < ARRAY_SIZE(vgpr_init_regs); i += 2) {
        ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);
        ib.ptr[ib.length_dw++] = vgpr_init_regs[i]     - PACKET3_SET_SH_REG_START;
        ib.ptr[ib.length_dw++] = vgpr_init_regs[i + 1];
}
```

`ibref` buscaba escrituras con dos regex y las ordenaba por línea. Eso encuentra
**una** iteración, y `vgpr_init_regs[i]` no se puede evaluar porque `i` no está
ligado. Resultado: una IB de 42 dwords con 9 sin resolver.

Y 9 `INCOMPLETO` no son 9 huecos: son **51 registros** de un shuttle de estado de
shader que el instrumento no veía. La mitad de la información de la IB estaba
ausente, y lo que se via era correcto, así que **nada indicaba que faltaba
nada**. Esa es la clase de hueco que este proyecto ha pagado más veces, y aquí
no era un `NOT_FOUND` sino un `NOT_LOOKED_FOR`.

## 2 · EL CONTRATO, Y POR QUÉ ES ESTRECHO A PROPÓSITO

Un desenrollado mal hecho **no falla**: produce una IB distinta, completa y
plausible. Y una IB completa y plausible es **peor** que una IB incompleta,
porque parece un resultado en lugar de una ausencia.

Por eso solo se desenrolla una forma, y solo si todo encaja:

```text
for (V = <entero>;  V < <limite>;  V += <entero>)
```

y el límite tiene que resolverse a entero. Todo lo demás **se rechaza con el
motivo escrito**:

```text
ARRAY_SIZE de un array inexistente   -> "no hay ningun `u32 x[]` declarado..."
limite que no es un entero            -> "el limite 'n_regs' no es un entero..."
paso no positivo                     -> "el paso no es positivo"
comparacion distinta de `<`           -> "forma de bucle NO reconocida"
inicializacion no entera              -> "la inicializacion no son enteros"
tope de iteraciones excedido          -> "el calculo da N iteraciones..."

6 vectores, uno por motivo.
```

## 3 · UN BUCLE QUE NO SE ENTIENDE NO PUEDE DESAPARECER

Este lo encontró el selftest, y es el más importante de todos:

```python
RE_FOR = re.compile(r"for\s*\(\s*(V)\s*=\s*([^;]+);\s*\1\s*<\s*([^;]+);...")
```

Un bucle `for (i = 0; i != 4; i += 2)` **no casa con `RE_FOR`**. Antes de
arreglarlo, ese bucle:

```text
no estaba en `bucles`        -> porque no se desenrolló
no estaba en `sin_desenrollar` -> porque el patrón no casó
```

Desaparecido. La IB salía "completa" sin las escrituras del bucle, y **no había
nada** que indicara que faltaba nada.

Es el peor modo de callar: no es un dato que se pierda, es un dato que se
declara inexistente.

El arreglo es contar los `for` que existen y no se han entendido:

```python
for mf in RE_FOR_CUALQUIER.finditer(txt):        # ^\s*for\s*\(
    ...
    melan.append({"linea": ln, "motivo":
                  "forma de bucle NO reconocida (solo se entiende "
                  "`for (V = <entero>; V < <limite>; V += <entero>)`"})
```

Medido sobre la función real:

```text
NO desenrollados:
   L1517  for (i = 0; i < ARRAY_SIZE(vgpr_init_compute_shader); i++)
   L1520  for (i = 0; i < ARRAY_SIZE(sgpr_init_compute_shader); i++)
   L1628  for (i = 0; i < ARRAY_SIZE(sec_ded_counter_registers); i++)
```

Son bucles de `i++`, fuera del contrato, y se dicen. Las tres líneas son
correctas —lo que llega al final de §4 no lo era.

## 4 · EL BUG DE NÚMEROS DE LÍNEA, Y LOS 5 DWORDS DE MÁS

`_sin_comentarios()` borraba el texto de los comentarios. Al borrar un
comentario **multilínea**, sus saltos de línea se iban con él, y todas las
líneas posteriores se desplazaban.

Lo vi por el lado más feo: la primera versión reportaba bucles no reconocidos en

```text
L1493   WREG32(mmGB_EDC_MODE, 0);
L1496   (((ARRAY_SIZE(vgpr_init_regs) / 2) * 3) + 4 + 5 + 2) * 4;
L1604   /* shedule the ib on the ring */
```

Ninguna de las tres contiene un `for`. El instrumento reportaba bucles que no
existían, en líneas que no eran, con el motivo equivocado.

Y el efecto no era solo cosmético. `escrituras()` filtra las líneas del cuerpo
de un bucle para no emitirlas dos veces, y ese filtro usaba números de línea
**corruptos**: no filtraba lo que debia, y **`desenrollados` no cuadraba**:

```text
ANTES del arreglo      191 dwords      <- 5 de mas
DESPUES del arreglo    186 dwords

  bucles:  3 x 17 iteraciones x 3 escrituras = 153   (medido: 153)
  filas duplicadas dentro de bucles: 0
```

Los 5 de más eran **dwords repetidos**: el mismo `ib.ptr[...]` salía una vez
con el elemento ligado (por el desenrollado) y otra sin ligar (por
`escrituras()`). Una IB con duplicados no es una IB "de más": es **otra IB**, y
el framing deja de cuadrar sin que nada lo diga.

El arreglo conserva los saltos de línea dentro del sustituto:

```python
txt = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), txt, flags=re.S)
```

Se borra el contenido del comentario sin mover el resto del documento. Dos
vectores lo fijan.

## 5 · MEDIDO, NO DECLARADO

```text
dwords totales      186
  de bucles         153   (3 bucles x 17 iter x 3 escrituras)
  sin bucle          33
iteraciones         17, cada una con 9 filas (3 escrituras x 3 bucles)
duplicados           0
```

Y el conteo cuadra solo: `153 = 3 × 17 × 3`. Si el desenrollado hubiera
duplicado o perdido una escritura, ese producto no saldría.

Sobre esa IB, `mmio` resuelve:

```text
NO_ES_DIRECCION 51    <- los 51 VALORES, correctamente no tratados como dirección
SIN_LIGAR       6
UNICO          54    <- 51 de las tablas + 3 de mmCOMPUTE_PGM_LO

  17  SET_SH_REG  0x00000216  0x2E16  UNICO  mmCOMPUTE_STATIC_THREAD_MGMT_SE0
  18  SET_SH_REG  0x00000215  0x2E15  UNICO  mmCOMPUTE_RESOURCE_LIMITS
  19  SET_SH_REG  0x00000207  0x2E07  UNICO  mmCOMPUTE_NUM_THREAD_X
  ...
  24  SET_SH_REG  0x00000240  0x2E40  UNICO  mmCOMPUTE_USER_DATA_0
```

Los 51 `NO_ES_DIRECCION` son los **valores** que van detrás de cada dirección, y
que decodificar como si fueran direcciones habría producido 51 registros
equivocados. Que salgan con ese nombre es el instrumento diciendo "esto no es lo
que tú buscas" en lugar de dar un nombre plausible.

## 6 · LAS TRES MEDIDAS, Y POR QUÉ SON TRES

Un desenrollado se puede ir de tres maneras, y ninguna lanza excepción:

```text
ibref.desenrollados            3 x 17        <- fewer iteraciones = IB incompleta
ibref.dwords_duplicados        []            <- mas iteraciones = IB con duplicados
ibref.bucles_no_desenrollados  L1517 L1520 L1628   <- y si NO aparece, no se sabe
```

La tercera es la que no tiene ancla natural: un bucle que desaparece no cambia
ningún número, así que las dos primeras seguirían verdes. Solo por medirla en
explícito se ve.

Las tres perturbadas una por una:

```text
ibref.desenrollados            perturbada   rc=1
ibref.dwords_duplicados        perturbada   rc=1
ibref.bucles_no_desenrollados  perturbada   rc=1
restaurada                                rc=0
```

## 7 · MIS ERRORES

| # | error | cómo salió |
|---|---|---|
| 1 | **bucle no reconocido desaparece en silencio** | `SELFTEST FALLIDO` en el vector de `!=` |
| 2 | **números de línea corruptos** por el borrado de comentarios | reportaba `for` en una línea con `WREG32` |
| 3 | **5 dwords duplicados** de consecuencia del 2 | el conteo `153` no cuadraba: salia 191 |
| 4 | `_sin_comentarios` no quitaba el contenido, solo lo hacía ilegible | vector: `"tres" not in ...` |

Los cuatro los encontró el selftest. **Ninguno habría salido ejecutando la
herramienta**: la salida era plausible en los cuatro casos. `#4` es el que más
me gusta porque el comentario se puede borrar sin dejar rastro y el bug sigue
ahí.

Y uno de proceso, el mismo de `1133 §3`: la primera versión de `desenrollar`
usaba estado de módulo (`_BUCLES`, `_DESENROLLADOS`) y un multiplicador mágico
`k * 100000` para los números de línea. Lo detecté al releer mi propio docstring,
que decía literalmente *"un módulo con estado de la última llamada es un módulo
cuyo resultado depende de si se ha llamado antes"*, y luego hice exactamente
eso. El comentario estaba bien; el código no lo escuchó. Hay un vector por eso:

```text
desenrollo: es reentrante: dos llamadas seguidas dan lo mismo
```

## 8 · LO QUE NO ESTÁ HECHO

**Los tres bucles `i++` siguen sin desenrollarse.** `vgpr_init_compute_shader`,
`sgpr_init_compute_shader` y `sec_ded_counter_registers` son bucles de un
elemento, y mi contrato solo acepta `+=`. Es la extensión más obvious y la
**no he hecho a propósito**: cuanto más estrecho es el contrato, más se puede
confiar en lo que sí acepta. Están declarados con línea y motivo, así que
cualquiera puede ver que faltan.

**Los 6 `SIN_LIGAR` restantes** son `lower_32_bits(gpu_addr)` y
`upper_32_bits(gpu_addr)`, que dependen de una dirección de buffer. Ligable con
`--set`, pero es un argumento que no es un literal.

**No he desenrollado bucles anidados ni `while`.** `RE_FOR` no los ve, y como
no hay vector que los mencione, no puedo afirmar que estén o no en
`gfx_v8_0.c`. Es un `NOT_DETERMINED`, no un `PROVEN_ABSENT`.

**Y `gfx_v8_0_do_edc_gpr_workarounds` no es una función de shader-init.** Es la
que contiene los tres bucles de las tablas de estado, y su nombre dice otra
cosa. Busqué `gfx_v8_0_do_shader_init` porque es donde pensé que estaba, y no
existe en `gfx_v8_0.c`. El nombre correcto habría salido de leer el
contenedor de las tablas.

## 9 · PROCEDIMIENTO

```text
instrumento   ibref --func <fn>   ahora desenrolla ARRAY_SIZE de u32[]
              devuelve `bucles` y `bucles_no_desenrollados` con su motivo
vectores      ibref 39 -> 57, rc=0
puerta        44 -> 46 declaradas, 48 en total, SIN DERIVA
              las tres medidas nuevas perturbadas una por una: rc=1
              restaurada: rc=0
artefactos    08-ARQUITECTURA/artifacts/R12-DESENROLLO/{ib.txt,ib.json,mmio.txt}
otros         layoutcross 79 vectores rc=0
              mmio        48 vectores rc=0
escrituras    0 ficheros de otros agentes
```