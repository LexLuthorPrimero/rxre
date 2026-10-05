# 1522 — la geometría de VRAM cabe en un solo registro, el ROM la declara entera, y el driver lee un bit

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA · FASE=2 (geometria)
CLASSIFICATION=EVIDENCIA-DE-ROM+HEADERS · TRACK=STATIC · CERO HARDWARE
GENERADO=2026-10-05
CIERRA=un discriminante que el 1511 dejo nombrado y el 923 no tenia
ESTADO=PROBADO · CHMAP (0x801) y CHREMAP (0x802) son registros DISTINTOS y contiguos
       · CHMAP tiene NOOFCHAN[15:12]; CHREMAP NO tiene NOOFCHAN, tiene CHAN0..CHAN7
       · el ROM escribe su mapa de canales en CHREMAP; el driver lee el recuento en CHMAP
       · MC_ARB_RAMCFG (0x9D8) contiene la geometria DRAM entera en 14 bits
       · y el driver usa UNO de esos bits
```

## 1. La pregunta, y por qué decide el 1511

El `1511` dejo esto escrito como discriminante pendiente:

> Ojo: CHREMAP en el header, CHMAP en la lectura del driver. Si son registros distintos, la ruta B
> lee el equivocado y eso **DECIDE** el punto 3.

O sea: si son el mismo nombre con una errata, el 64 es un valor mal interpretive. Si son dos
registros, el driver lee un registro que el ROM no usa para declarar los canales de esta memoria.
Son preguntas distintas con respuestas distintas, y la herramienta decide entre ellas.

## 2. Respuesta: son dos registros, y no describen lo mismo

Del header de gfx8.1, el bloque GMC:

```text
  gmc_8_1_d.h:273    mmMC_SHARED_CHMAP      0x801
  gmc_8_1_d.h:274    mmMC_SHARED_CHREMAP    0x802     <-- el siguiente
  gmc_8_1_d.h:300    mmMC_SHARED_CHREMAP2   0x81c
```

No es una errata: son **registros contiguos con nombres distintos**. Y sus campos no se parecen:

```text
  MC_SHARED_CHMAP     (0x801)
     CHAN0   [3:0]      CHAN1   [7:4]      CHAN2  [11:8]
     NOOFCHAN[15:12]                        <-- EL RECUENTO DE CANALES
     CHAN3   [19:16]    CHAN4   [23:20]

  MC_SHARED_CHREMAP   (0x802)
     CHAN0   [3:0]  CHAN1  [7:4]  CHAN2  [11:8]  CHAN3  [15:12]
     CHAN4   [19:16] CHAN5  [23:20] CHAN6 [27:24] CHAN7 [31:28]
     <-- NO TIENE NOOFCHAN.  Ocho nibbles, uno por canal.
```

**Un campo `NOOFCHAN` existe en el primero y no existe en el segundo.** No es un alias, ni una
duplicacion, ni dos nombres para lo mismo.

## 3. Y cada uno lo escribe una cosa distinta

El `ATOM_VRAM_MODULE_V8` declara su mapa de canales en el registro equivocado para lo que el driver
mira. Comentarios literales del header (`atombios.h:7915` y `:7946`):

```c
  ULONG ulChannelMapCfg;   // mmMC_SHARED_CHREMAP
```

Es decir: **el BIOS escribe el mapa en `CHREMAP` (0x802)**, y **el driver lee el recuento de canales
en `CHMAP` (0x801)** (`gmc_v8_0.c:526-527`).

Y aqui el nombre importa. `CHMAP` es *channel map* y `CHREMAP` es *channel **re**map*: el segundo es
la permutacion por nibble de como se reparte la direccion entre canales, y el primero guarda
ademas cuantos canales hay. Son dos preguntas del hardware distintas, con dos registros distintos,
y cada autoridad del proyecto escribe y lee en una.

> **PROBADO:** el valor de canal que lee `gmc_v8_0.c:526` viene de un registro que el ROM no
> usa para declarar los canales del modulo de memoria de esta placa.

## 4. Por eso el `case 0` es la pieza peligrosa

El `switch` de la ruta B, literal (`gmc_v8_0.c:527-531`):

```c
  switch (REG_GET_FIELD(tmp, MC_SHARED_CHMAP, NOOFCHAN)) {
  case 0:
  default:
          numchan = 1;
          break;
```

`case 0` y `default` estan pegados y ambos devuelven **1**. En una GPU con memoria dedicada, el mapa
de canales **compartidos** no describe los canales de VRAM y no hay motivo para que `NOOFCHAN` valga
lo que el driver espera. Si vale `0`, el driver no falla: **devuelve 1 canal**, y con
`CHANSIZE = 64` produce `64`.

```text
  numchan = 1   x   chansize = 64   =   64      <-- el numero que el kernel publico
```

> **PROBADO por estructura, NO por medida:** la combinacion `numchan=1 x chansize=64` se sigue
> sin leer un registro, y el `case 0` convierte un valor no poblado en un `1` plausible en vez de
> en un error. Lo que **no** he medido es que `NOOFCHAN` valga efectivamente `0` en esta placa. Eso
> sigue siendo `NOT_DETERMINED` y es hardware.

## 5. El hallazgo de fondo: la geometria cabe en un registro y el driver usa un bit

Esto es lo que la fase 2 tiene que reconstruir, y sale entero del mismo sitio. `MC_ARB_RAMCFG` es
`0x9D8` y sus campos (`gmc_8_1_sh_mask.h:503-522`):

| campo | bits | mask | que declara |
|---|---|---|---|
| `NOOFBANK` | [1:0] | `0x3` | nº de banks |
| `NOOFRANKS` | [2] | `0x4` | nº de ranks |
| `NOOFROWS` | [5:3] | `0x38` | nº de filas |
| `NOOFCOLS` | [7:6] | `0xc0` | nº de columnas |
| `CHANSIZE` | [8] | `0x100` | **32 o 64 bits** |
| `NOOFGROUPS` | [12] | `0x1000` | nº de grupos |

Y el `ATOM_VRAM_MODULE_V8` (`atombios.h:7943`) guarda, textual (`atombios.h:7948`):

```c
  USHORT usMcRamCfg;   // MC_ARB_RAMCFG (includes NOOFBANK,NOOFRANKS,NOOFROWS,NOOFCOLS)
```

**El ROM declara la geometria DRAM completa como el valor de un registro.** No como una tabla que
alguien interprete: como el operando que se escribe en `0x9D8`.

Y la ruta B del driver lee `0x9D8`, extrae `CHANSIZE`, y **descarta los otros cinco campos de
geometria que estan en el mismo registro y que el ROM si declara**. No los descarto por capricho del
autor: no se usan para calcular `vram_width`, que es lo que la funcion pretendia. Eso es coherente
con que el campo este mal, pero significa que **la fuente de verdad de la geometria de esta tarjeta
es un unico valor de 16 bits que nadie decodifica todavia.**

Ademas hay un segundo sitio: el `V8` lleva `ucBankCol` (`atombios.h:7955`) con
`bit[3:2]=BANK (=2:16bank, =1:8bank, =0:4bank)` y `bit[1:0]=Col (=2:10bit, =1:9bit, =0:8bit)`,
mas `ucRowNum` (`atombios.h:7961`) aparte. O sea que **bank y col estan codificados dos veces**, en `usMcRamCfg` como
campos de registro y en `ucBankCol` como enums. Que los dos coincidan en esta placa es una pregunta
abierta con su propio discriminante.

## 6. Lo que queda abierto, con nombre

```text
ABIERTO   el valor real de MC_SHARED_CHMAP.NOOFCHAN en esta placa.  Requiere leer 0x801.
          Es lo que separa "produce 1 por el case 0" de "produce 1 porque hay 1 canal".
ABIERTO   el valor de usMcRamCfg en el modulo VRAM real de este ROM.  Es la lectura que cierra la
          geometria, y NO necesita hardware: es un campo mas de la tabla VRAM_Info (0xA30A).
          ESA ES LA SIGUIENTE ACCION, y es estatica.
ABIERTO   si usMcRamCfg y ucBankCol+ucRowNum describen la misma memoria o dos cosas distintas.
RIESGO    ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE    todo esto es lectura de headers y de codigo del driver de este corpus podado.  No es
          medida de la tarjeta.  El unico hecho de silicio aqui es la cadena de guardia del 1511.
```

## 7. Decision log (§103)

```text
DECISION    tratar CHMAP y CHREMAP como registros distintos y no como alias
WHY         0x801 y 0x802, contiguos, y solo uno tiene NOOFCHAN.  No hay ambiguedad que resolver.
ALTERNATIVA leer "CHMAP" y "CHREMAP" como la misma cosa con una errata y seguir con el residuo
            del 1511 como explicacion principal.  Descartada: el header no lo permite.
CONSECUENCIA el punto 3 del 1511 se estrecha de tres candidatos a uno con causa estructural, y la
            siguiente accion es leer el ROM, no el registro
REVERSIBLE  si el corpus tuviera una version de estos headers donde coincidieran, habria que
            revisar; en este corpus no coinciden
```

## 8. Por que esto va en la parte 1 y no en otra parte

La geometria es el item 2 de la definicion de cierre de MC/memoria, y es de donde dependen
GPUVM, PM4 y fences. Lo que hay aqui no es un detalle del driver: es que **la tarjeta declara su
geometria en un valor de 16 bits y el proyecto no lo ha leido nunca.** Es la lectura mas barata que
queda en toda la parte, y es estatica.
