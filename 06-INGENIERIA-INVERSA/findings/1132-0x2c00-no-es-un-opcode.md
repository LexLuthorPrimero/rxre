# 1132 — `0x2C00` no es un opcode: es la frontera compartida de dos ventanas de direccionamiento relativo, y la tabla de la herramienta lo declara como paquete — **7 de 77 entradas (9%) no pueden ser opcodes**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=VALIDATION + SEMANTIC-CLOSURE
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/layoutcross.py   (4º oraculo, nuevo)
                              tools/verif.py          (2 medidas)
                              08-ARQUITECTURA/artifacts/R10-OPCODE/{copias-kfd.txt,
                              colision.txt, layoutcross-vivo.txt}
                              08-ARQUITECTURA/artifacts/VERIF/linea-base.json
MODIFICADO_NADA_EXISTENTE    pm4_codec.py INTACTO
CLASSIFICATION=MEASUREMENT · DERIVATION · IMPLEMENTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=CONFLICTO MEDIDO Y CORREGIDO EN EL INSTRUMENTO · EL FICHERO VIVO, NO
```

## 0 · El resultado, primero

```text
PRECONDICION  las 4 copias de cada cabecera KFD son byte-identicas (16 ficheros,
              4 contenidos) y linux-7.1.3 == linux-7.2.8.  Procedencia del
              oraculo: RESUELTA, no "no encontrada".

HALLAZGO      vid.h declara 0x2c00 DOS VECES:
                PACKET3_SET_CONFIG_REG_END   linea 342
                PACKET3_SET_SH_REG_START     linea 348

SEMANTICA     0x2c00 no es un opcode.  Es la frontera compartida de dos
              ventanas de direccionamiento relativo ADYACENTES.

CONSECUENCIA  pm4_codec.opcode_table() declara 7 entradas que no pueden ser
              opcodes, probables por rango sin ninguna fuente externa:  7/77

INSTRUMENTO   cuarto oraculo en layoutcross: OPCODE_FUERA_DE_RANGO
PUERTA        36 -> 38 medidas, perturbada y restaurada
```

## 1 · POR QUÉ EMPEZABÁ POR LAS COPIAS

`1131 §8` dejó escrito, como precondición suya, que añadir oráculos sin
verificar produce "un oráculo que miente con más confianza". Y yo estaba
usando `kfd_pm4_headers_vi.h` como oráculo de anchura sin haber comprobado su
procedencia: hay cuatro copias en el árbol, y el proyecto **ya había medido
discrepancias entre copias de `sid.h`**.

```text
4f86997f9ff9ff92   15728 B   kfd_pm4_headers_ai.h        x4
a93d0874298f10ae    2602 B   kfd_pm4_headers_aldebaran.h x4
766cf33f20832ac8    3694 B   kfd_pm4_headers.h           x4
0c8d2b2be79d2247   12060 B   kfd_pm4_headers_vi.h        x4
```

Copia de cada grupo: `baseline/`, `kernelbuild/`, `working/` (7.1.3) y
`rx550-upstream-7.2.8/`. **16 ficheros, 4 contenidos, cero diferencias.**

Y `7.1.3` da el mismo sha que `7.2.8` para los cuatro. Eso es un dato que
importa y que no es obvio: el oráculo **no es ruido de versión**, así que una
discrepancia contra él no se puede explicar por "tomé una versión distinta".

Estado: `PROVEN` identidad, no `NOT_FOUND`.

## 2 · LA COLISIÓN, Y POR QUÉ NO ES UN ERROR DE ESCRITURA

Lo primero que se ve es una aparente errata:

```text
vid.h:342  #define  PACKET3_SET_CONFIG_REG_END   0x00002c00
vid.h:348  #define  PACKET3_SET_SH_REG_START     0x00002c00
```

Dos nombres, un valor. Pero se repite **idéntico** en `soc15d.h:430/436` y en
`gfx_v12_1_pkt.h:344/349`. Una errata no se replica con la misma línea y el
mismo desplazamiento en tres cabeceras de generación distintas. Es
estructural.

Lo que explica la estructura son los dospacket que los nombran, medido en el
código de emisión:

```text
gfx_v8_0.c:1529   ib.ptr[...] = PACKET3(PACKET3_SET_SH_REG, 1);
gfx_v8_0.c:1530   ib.ptr[...] = vgpr_init_regs[i] - PACKET3_SET_SH_REG_START;
gfx_v8_0.c:1535   ib.ptr[...] = PACKET3(PACKET3_SET_SH_REG, 2);
gfx_v8_0.c:1536   ib.ptr[...] = mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START;

gfx_v8_0.c:6121   amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID
                                    - PACKET3_SET_CONFIG_REG_START);
gfx_v6_0.c:1868   amdgpu_ring_write(ring, mmSCRATCH_REG0
                                    - PACKET3_SET_CONFIG_REG_START);
```

El payload de estos paquetes **no es un valor**: es una **dirección MMIO menos
una base**. Los nombres `START` y `END` no describen un paquete que empieza y
otro que acaba. Describen **los extremos de una ventana de direccionamiento
relativo**:

```text
SET_CONFIG_REG   payload = MMIO - 0x2000    ventana [0x2000, 0x2c00)
SET_SH_REG       payload = MMIO - 0x2c00    ventana [0x2c00, 0x3000)
SET_CONTEXT_REG  payload = MMIO - 0xa000    ventana [0xa000, 0xa400)
SET_UCONFIG_REG  payload = MMIO - 0xc000    ventana [0xc000, 0xc400)
```

Y las ventanas son **adyacentes**: `[0x2000,0x2c00)` termina justo donde
`[0x2c00,0x3000)` empieza. Por eso `SET_CONFIG_REG_END` y `SET_SH_REG_START`
son el mismo número: **es la frontera compartida**.

El opcode que emite el paquete es otro y sí cabe en 10 bits:

```text
PACKET3_SET_CONFIG_REG  0x68      PACKET3_SET_SH_REG   0x61
```

Lo que la colisión **no** es: dos packets con el mismo opcode. Es un número que
nunca viaja como opcode.

## 3 · LA PRUEBA QUE NO NECESITA NINGUNA FUENTE — CORREGIDA EN `1133`

Un PACKET3 es, en las **cuatro** cabeceras de generación del árbol y con la
misma definición al byte (`vid.h:105`, `sid.h:336`, `soc15d.h:50`,
`gfx_v12_1_pkt.h:48`):

```text
#define PACKET3(op, n)  ((TIPO << 30) | ((op) & 0xFF) << 8 | ((n) & 0x3FFF) << 16)

cabecera:  bits 31:30  tipo    bits 29:16  count   bits 15:8  OPCODE   bits 7:0  libre
```

El opcode son **8 bits**, luego ningún opcode pasa de `0xFF`. Lo que lo supera
no es "un opcode raro": el campo lo enmascara con `& 0xFF`, así que un literal
de `0x2000` se convertiría en `0x00`, que es **otro paquete**.

> **RETRACCIÓN. La primera versión de esta sección-era falsa.** Escribí que "el
> opcode son los bits 0-9" y puse `OPCODE_MAX = 0x3FF`. **Son los bits 8-15 y
> la cota es `0xFF`.** El campo del opcode no está en el byte bajo de la
> cabecera, sino en `<< 8`.
>
> La **conclusión** de este hallazgo sobrevive intacta: los 7 valores pasan
> también de `0xFF`, así que la lista de `opcode.fuera_de_rango` es la misma. Lo
> que estaba mal era **la prueba y la cota**, y una cota mal puesta no falla
> hoy: habría dado `OK` a un opcode de `0x100` que el hardware no puede
> representar.
>
> La causa de mi error fue no verificar la fórmula antes de razonar sobre ella.
> Di por bueno un "`opcode` en los bits bajos" que es lo que uno se imagina, en
> vez de leer el `#define`. `1133` lo mide, lo corrige y añade el vector que lo
> atrapa. La lista de entradas de este hallazgo no cambia; la justificación, sí.

Este es el único veredicto de `layoutcross` que **no compara dos fuentes**.
Primero de los cuatro, y el más barato: una propiedad interna de la tabla contra
la estructura de la cabecera.

## 4 · LO QUE MIDE SOBRE LA HERRAMIENTA VIVA

```text
opcode.entradas           77
opcode.fuera_de_rango      7   (9%)

   0x2000  PACKET3_SET_CONFIG_REG_START
   0x2C00  PACKET3_SET_SH_REG_START
   0x3000  PACKET3_SET_SH_REG_END
   0xA000  PACKET3_SET_CONTEXT_REG_START
   0xA400  PACKET3_SET_CONTEXT_REG_END
   0xC000  PACKET3_SET_UCONFIG_REG_START
   0xC400  PACKET3_SET_UCONFIG_REG_END

   si pueden ser opcode   70
```

Las 7 son las constantes de ventana. Ninguna es un error de lectura de opcode.

Y un dato que hace el hallazgo más fuerte de lo que parece: **`0x2C00` es la
única entrada con dos nombres en `vid.h`, y solo una de las dos es alcanzable
desde la tabla**.

```text
nombres en vid.h                  78
alcanzables por numero            77
INALCANZABLE                      PACKET3_SET_CONFIG_REG_END
```

Un mapa inverso `{numero: nombre}` **no puede representar** que un valor nombra
dos fronteras de ventana. La forma correcta sería `{numero: {nombres}}`. Eso es
un defecto de estructura de datos, no un dato que falte: por mucho que se añada
información, ese tipo no la puede llevar.

## 5 · GRAVEDAD: LATENTE, Y POR QUÉ

Lo que un decodificador haría con la tabla tal como está: si ve un dword
`0x00002C00` en el anillo, son bits 31:30 = 0, así que **no es cabecera** y un
decodificador bien hecho lo trata como payload. El fallo necesitaría un
decodificador que mire la tabla **antes** de mirar los bits 31:30.

Eso no ocurre hoy, y lo comprobé: `ibref` segmenta por
`((valor >> 30) & 0x3) != 3`, que descarta los valores que no pueden ser
cabecera **antes** de mirar nombres. El orden correcto ya está.

**Estado: `NOT_OBSERVED` en ejecución, `PROVEN` que la tabla contiene entradas
imposibles.** No es `PROVEN_ABSENT` el defecto, ni `PROVEN` el fallo: es una
bomba de relojería documentalizada.

## 6 · LO QUE ESTO ABRE Y ESTÁ SIN HACER

**`SET_SH_REG` no tiene layout.** `pm4_codec` declara 7, y no es una de ellas:

```text
PACKET3_CP_DMA · PACKET3_DMA_DATA · PACKET3_MAP_QUEUES · PACKET3_QUERY_STATUS
PACKET3_RUN_CLEANER_SHADER · PACKET3_SET_RESOURCES · PACKET3_UNMAP_QUEUES
```

Y `gfx_v8_0.c` emite `SET_SH_REG` en 1529, 1535 y 1582. Es decir: **una IB de
inicialización de shader de GFX8 no se puede decodificar**, y es el camino que
usa el compute shader.

Eso no lo arregla añadir una entrada más a `DOC_LAYOUTS`. El payload de
`SET_SH_REG` no son campos: son direcciones **relativas a una ventana**, y
decodificarlo exige una operación que ninguna de las tres tablas existentes
puede expresar — restar la base y volver a sumar `0xFFF00000 | registro`.

Es la primera vez que el punto ciego no es una falta de declaración sino una
**falta de forma**: no es "falta el campo X", es "falta un tipo de transformada".

## 7 · PROCEDENCIA

```text
copias-kfd.txt       16 ficheros, sha256, 4 contenidos, 7.1.3 == 7.2.8
colision.txt         las 3 cabeceras, las 2 lineas, la derivacion de ventanas
layoutcross-vivo.txt salida completa con el 4º oraculo

4º oraculo           contrastar_rango_opcode()
                     lee opcode_table() por ATRIBUTO, no por fuente: lo que se
                     audita es lo que la herramienta PUEDE devolver
                     una herramienta sin opcode_table() NO aparece, y eso se ve
                     (vector: contrastar_rango_opcode([{mod:None}]) == {})
6 vectores nuevos    layoutcross 70 -> 76

puerta               36 -> 38 medidas, perturbadas una por una
                       opcode.entradas 77 -> 99      rc=1
                       restaurada                     rc=0
instrumentos         layoutcross 76 vectores rc=0
                     ibref        32 vectores rc=0
escrituras           0 ficheros de otros agentes
```

## 8 · LO QUE ESTO NO PRUEBA

**No prueba que las ventanas sean esas.** Es una derivación: leí el uso
(`MMIO - CONSTANTE`) en tres sitios de dos generaciones, y los números encajan
con los `START`/`END`. Que la ventana de `SET_SH_REG` empiece exactamente en
`0x2c00` está **corroborado** por la aritmética del propio driver, no
**probado** contra el hardware. Si el hardware usara otra base, el código del
kernel estaría mal; no tengo forma de refutarlo sin placa.

**No prueba que la herramienta tenga un defecto.** Puede que el nombre
`PACKET3_SET_SH_REG_START` sea correcto —lo es como nombre de la constante— y
que el defecto esté en **incluirla en una tabla que se titula "opcodes"**. Son
dos arreglos posibles y no elijo: `DOC_LAYOUTS` y `opcode_table()` son de otra
sesión y la frontera es de otro autor. Lo que sí hago es dejar el hecho medido y
la prueba, que es lo que hace falta para decidir.

**No prueba nada sobre el hardware.** `RUNTIME=NOT_RUN`, no hay placa.

**No cubre los 6 paquetes de KFD frente a `vi.h`.** Comprobé que `_ai.h`
declara **los mismos 6 structs**, no adicionales: añadirlo como oráculo no
ampliaría la cobertura de `CP_DMA` ni de `DMA_DATA`, que siguen sin oráculo de
anchura. La frontera sigue abierta y `1131 §8` la dejó dicha.