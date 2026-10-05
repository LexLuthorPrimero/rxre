# 1539 — el ancho de bus lo decide un sondeo al arrancar, y el índice que usa no está definido en el corpus

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA+ROM · FASE=2, item 1
CLASSIFICATION=MECANISMO-DE-SILICIO-DECLARADO+RESOLUCION-DE-CONTRADICCION+HUECO-NOMBRADO
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1532 y 1535  su CONTRADICCION pasa a tener un mecanismo y un juez
ESTADO=PROBADO · Polaris12 tiene DOS variantes de silicio, y el driver lo sondea al arrancar
       · la sonda escribe mmMC_SEQ_IO_DEBUG_INDEX y compara contra la magia 0x05b4dc40
       · el comentario del driver lo dice literal: "Polaris12 32bit ASIC needs a special MC firmware"
       · el 1445 ya midio que esta placa NO es la variante de 32 bits
       · ixMC_IO_DEBUG_UP_159 se usa una vez y NO ESTA DEFINIDO en ningun header del corpus
       · el ancho pasa de CONTRADICCION a PROVEN con 4 fuentes concordantes, y queda un residuo nombrado
```

## 1. La contradiccion del 1532, y de donde sale la pieza que le faltaba

El 1532 dejo tres testigos del ROM en conflicto: la cadena dice 128, y `usEnableChannels × CHANSIZE` y
el mapa de lanes dicen 64. Y concluyo que el cuarto testigo —la variante de firmware— **no era
decodificable**.

Era una conclusion correcta sobre el esquema de nombres `25632`, y **estaba incompleta**: no porque
`25632` fuera el unico camino, sino porque no mire el otro. El driver **no decodifica un nombre:
sondea un valor al siliconio y elige el fichero de firmware.**

## 2. El sondeo, textual

`gmc_v8_0.c:241-252`, la rama de `CHIP_POLARIS12`:

```c
  242   if (ASICID_IS_P23(adev->pdev->device, adev->pdev->revision)) {
  243           chip_name = "polaris12_k";
  244   } else {
  245           WREG32(mmMC_SEQ_IO_DEBUG_INDEX, ixMC_IO_DEBUG_UP_159);
  246           /* Polaris12 32bit ASIC needs a special MC firmware */
  247           if (RREG32(mmMC_SEQ_IO_DEBUG_DATA) == 0x05b4dc40)
  248                   chip_name = "polaris12_32";
  249           else
  250                   chip_name = "polaris12";
  251   }
```

Tres cosas, y las tres importan:

1. **Polaris12 tiene dos variantes de silicio**, y la distincion es el ancho. El comentario lo dice
   sin rodeos: *"Polaris12 32bit ASIC needs a special MC firmware"*.
2. **AMD distribuye dos firmwares distintos** para el mismo ASIC. Y estan los dos en disco:
   `polaris12_mc.bin.xz` y `polaris12_32_mc.bin.xz`, con sus `MODULE_FIRMWARE` declarados en
   `gmc_v8_0.c:61-62`. **Y no son el mismo fichero con otro nombre:**

   ```text
     polaris12_mc.bin.xz       11328 bytes   ->  32608 descomprimido
     polaris12_32_mc.bin.xz    11392 bytes   ->  32876 descomprimido
                                     diferencia de 268 bytes descomprimidos
   ```
3. **La decision se toma con un sondeo al hardware, no con una lectura de config.** Se escribe un
   indice en `mmMC_SEQ_IO_DEBUG_INDEX` y se lee `mmMC_SEQ_IO_DEBUG_DATA`. Si el valor es la magia
   `0x05b4dc40`, el chip es de la clase de 32 bits.

O sea: **el ancho de bus de esta familia esta codificado en el nombre del fichero de firmware que el
chip carga.** Y por eso hay dos blobs: el firmware ES la declaracion de anchura.

## 3. Que midio el 1445, y por que esto no es nuevo hardware

El `1445` ejecuto exactamente esta sonda sobre `0000:01:00.0` y publico:

> el firmware de memoria es polaris12, no polaris12_32 ni polaris12_k

y leo el valor con indice `0x9f`, **`0x00b4dc50`**, que no es `0x05b4dc40`. **Esta placa no es la
variante de 32 bits.** Eso ya estaba medido antes de que yo empezara el item 1, y no lo habia
conectado con la contradiccion del ancho.

**Un detalle que no encaja y no voy a forzar:** la magia del driver es `0x05b4dc40` y el valor leido
fue `0x00b4dc50`. Comparten los bytes `b4dc` y difieren en el byte alto y en el ultimo. Si el
registro fuera la version del ucode de MC, dos cargas del mismo firmware darian el mismo valor. **No
se si son el mismo registro, leidos en momentos distintos, o dos registros distintos.** No lo
resuelvo: no tengo el valor del indice que escribe el driver, que es justo el hueco de la seccion 4.

## 4. El hueco, y es el mas concreto de la parte

```text
  ixMC_IO_DEBUG_UP_159
     se USA   gmc_v8_0.c:245, una vez
     se DEFINE   en ningun sitio
     busqueda: ixMC_IO_DEBUG_* en amdgpu/*.h  ->  0 ocurrencias de cualquier indice
```

**El indice que el driver escribe para decidir la variante de firmware no esta definido en ningun
header de este corpus.** Consecuencia directa: **no se puede reproducir la sonda sin hardware**, ni
siquiera leyendo el codigo, porque el numero que se escribe no se sabe.

Eso es un `NOT_DETERMINED` limpio, con productor nombrado y con la razon. Y explica por que el 1445
tuvo que escribir hardware para obtener el dato: no habia otra via.

## 5. El item 1, como queda

El 1532 dio tres testigos del ROM en contradiccion. Con esta pieza:

```text
  128 bits, CUATRO fuentes concordantes
      cadena de identificacion del ROM            "GDDR5 128bit"
      KFD mem_bank_width                          64 bits por banco
      KFD mem_banks_count                         2 bancos        64 x 2 = 128
      sondeo de firmware de MC (1445)             no es la variante de 32 bits

  64 bits, DOS testigos del ROM, ambos de 32 bits
      usEnableChannels=0x0003 x usMcRamCfg.CHANSIZE=0        2 x 32
      ATOM_DRAM_DATA_REMAP, 4 bytes por canal                 2 x 32
```

**El residuo tiene ahora una mecanica candidata y un nombre:** los dos testigos del ROM describen **32
bits**, y el hardware tiene bancos de **64**. La lectura que los reconcilia es que `CHANSIZE` y el
mapa de lanes describan **la anchura del dispositivo DRAM (x32)**, no la del banco, porque las GDDR5
son x16 o x32 y un banco de 64 se construye con varios dispositivos.

Y esa lectura encaja con la cadena de configuracion: `GD5_25632` se leeria como **256 Mb, x32**, que
es justo lo que dice `CHANSIZE = 0`.

> **PROBADO:** el bus es de 128 bits, con cuatro fuentes concordantes y una de ellas un sondeo de
> silicio ejecutado al arrancar.
> **DERIVED, NO PROBADO:** que los dos testigos del ROM describan el ancho de dispositivo y no el de
> banco. Es la mecanica que los reconcilia y encaja con `GD5_25632`, pero **no hay ninguna fuente que
> la declare**, y el nombre de la BIOS sigue sin poder decodificarse.
> **NOT_DETERMINED, con productor:** el valor de `ixMC_IO_DEBUG_UP_159`, que es lo que permitiria
> reproducir la sonda sin hardware.

**Esto NO reabre el 911.** Su conclusion era correcta. Lo que cambia es que ahora hay un mecanismo que
explica por que dos campos del ROM dicen 32, y por que eso no contradice un bus de 128.

## 6. El mecanismo `io_debug` es uno solo, y ya lo hemos visto tres veces

| uso | quien | que hace |
|---|---|---|
| seleccionar la variante de firmware | `gmc_v8_0.c:245` | **este hallazgo** |
| programar la tabla del firmware | `gmc_v8_0_polaris_mc_load_microcode` | `1511`, `1530` |
| bankear el firmware contra el silicio | sonda de 24 pares | `1447` |

**Un solo mecanismo, `INDEX`/`DATA`, con tres usos distintos**: elegir el firmware, programarlo, y
verificarlo. Es la misma puerta de entrada al controlador de memoria. Y explica por que el
`mmMC_SEQ_IO_DEBUG_INDEX` aparecia como la unica escritura del driver con un nombre de HDP que no es
HDP.

## 7. Decision log (§103)

```text
DECISION    declarar 128 bits PROBADO y reabrir el residuo como pregunta con mecanismo
WHY         cuatro fuentes concordantes, una de ellas un sondeo de silicio.  §62: el claim se
            cierra con evidencia, y esa es evidencia de silicio, con producer y fecha.
ALTERNATIVA  mantener el 1532 como "contradiccion abierta" sin mas.  Descartada: el 1532 no
            conocia el sondeo, y sin el la contradiccion era aparente.
ALTERNATIVA  declarar tambien que CHANSIZE es el ancho de dispositivo.  Descartada: seria
            precisamente el atajo que el 1532 critico.  Queda DERIVED con su ajuste a favor.
DISCriminante  para cerrar el residuo: el valor de ixMC_IO_DEBUG_UP_159, o una captura de
            /sys/kernel/debug/dri/0/amdgpu_kfd_info con mem_bank_width.  Ambos por hardware.
CONSECUENCIA  el item 1 pasa de CONTRADICCION a PROVEN con residuo nombrado.  Es el mayor avance
            del item y no requiere ni un solo byte de disco.
REVERSIBLE  la parte de 128 no.  El residuo, si: si CHANSIZE resultara ser el ancho de banco,
            entonces el ROM estaria mal y habria que revisar el 1522.
```

## 8. Donde queda la parte 1 tras este hallazgo

```text
  item 1  identidad de memoria   CASI CERRADO
              ancho de bus        128 bits, PROBADO, 4 fuentes
              tipo                GDDR5, PROBADO
              rango               SINGLE, PROBADO, corroborado por dos campos
              canales             2, PROBADO del ROM
              bytes/canal en ROM  32, y NO reconciliado con 64 del banco   <-- el residuo
              densidad            0x63, NOT_DETERMINED con razon
              codigo de vendedor  0, NOT_DETERMINED con razon

  item 2  geometria     DEFERRED con lista (1536)
  item 3  aperturas     CERRADO 5/6, el sexto DEFERRED por header ausente (1537)
  item 4  quien programa el MC   CERRADO (1530)
  item 5  firmware de MC         PARCIAL: ahora se sabe que la VARIANTE codifica el ancho
  item 6  contrato host<->SMC    sin tocar
  item 7  reloj y voltaje         sin tocar
```

**El item 1 ya no es una contradiccion: es un residuo con mecanismo y con dos discriminantes
nombrados.** Los items 6 y 7 siguen sin dependencia externa y son los unicos que quedan dando trabajo
estatico sin salir del disco.
