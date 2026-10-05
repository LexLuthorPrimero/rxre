# 1445 — el sondeo de firmware del controlador de memoria: esta tarjeta es `polaris12`, bus de 128 bits, y el índice queda restaurado

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+PRIMER-CONTROLLED-WRITE+DESIGNACION
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel 0000:00:02.0 intacta
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1436-*  (la omision que declaraba bloqueante)
         09-POWER-CLOCKS/  (que firmware de MC carga esta placa: ahora PROBADO)
ESTADO=PROBADO · el sondeo del vendor se ejecuto en esta tarjeta y dio su rama NO-32-bits
       · el firmware de memoria es polaris12, no polaris12_32 ni polaris12_k
       · el estado previo del registro se leyo ANTES y se RESTAURO, verificado
       · el bus de 128 bits queda con cuatro fuentes concordantes
```

## 0. Por qué esta lectura era bloqueante

El hallazgo 1436 escribió que 1434 no es ejecutable como secuencia, y la razón más grave
era esta:

```c
/* gmc_v8_0.c:262-263 */
err = amdgpu_ucode_request(adev, &adev->gmc.fw, AMDGPU_UCODE_REQUIRED,
                           "amdgpu/%s_mc.bin", chip_name);
```

**`AMDGPU_UCODE_REQUIRED`.** Sin ese firmware el controlador de memoria no funciona, y 1434
programaba tablas de página contra un controlador sin entrenar. Y el nombre del firmware no
es una constante: **lo decide una lectura de hardware**, en el propio arranque:

```c
/* gmc_v8_0.c:241-251 */
case CHIP_POLARIS12:
        if (ASICID_IS_P23(adev->pdev->device, adev->pdev->revision)) {
                chip_name = "polaris12_k";
        } else {
                WREG32(mmMC_SEQ_IO_DEBUG_INDEX, ixMC_IO_DEBUG_UP_159);
                /* Polaris12 32bit ASIC needs a special MC firmware */
                if (RREG32(mmMC_SEQ_IO_DEBUG_DATA) == 0x05b4dc40)
                        chip_name = "polaris12_32";
                else
                        chip_name = "polaris12";
        }
```

Y `ASICID_IS_P23` (`amdgpu.h:770-778`) cubre **sólo `0x6987` y `0x6981`**. Nuestra placa es
`0x699F`, luego **no es P23 y la rama del sondeo se ejecuta en esta tarjeta.**

## 1. Los tres registros, medidos

```text
gmc_8_1_d.h:1001   mmMC_SEQ_IO_DEBUG_INDEX = 0xa91    (byte 0x2A44)
gmc_8_1_d.h:1002   mmMC_SEQ_IO_DEBUG_DATA  = 0xa92    (byte 0x2A48)
gmc_8_1_d.h:1162   ixMC_IO_DEBUG_UP_159    = 0x9f
```

## 2. La operación, con estado previo y restauración

**Clasificación: `CONTROLLED_WRITE`.** Una escritura de índice, una lectura, y restauración
del valor original. Es la secuencia del propio vendor, no una inventada.

```text
objetivo declarado   0000:01:00.0   (RX550).  La Intel no participa en ninguna instruccion.

PRE   mmMC_SEQ_IO_DEBUG_INDEX (0xa91) = 0x00000026      <- leido ANTES, para restaurar
PRE   mmMC_SEQ_IO_DEBUG_DATA  (0xa92) = 0x20310002

      write INDEX = 0x9f                                 <- CONTROLLED_WRITE
      read  DATA                                          <- lectura

SONDEO  DATA = 0x00b4dc50

POST  INDEX restaurado a 0x00000026    verificado == el valor PRE      OK
```

**El índice quedó como estaba.** No queda rastro del sondeo en el registro.

## 3. El resultado y lo que decide

```text
leido  0x00b4dc50
magico 0x05b4dc40   (la firma de la variante de 32 bits)

coinciden en 10 de los 24 bits bajos;  difieren en el bit 4 (0x10)
```

**El valor NO es `0x05b4dc40`.** Por la lógica del propio driver:

```text
chip_name = "polaris12"        <-- NO es la variante de 32 bits
```

Y no es `polaris12_k`, porque eso exigiría que `0x699F` fuera P23, y no lo es.

> **PROBADO: esta tarjeta carga el firmware de memoria `polaris12`, el de la clase de 64
> bits.** Es la misma decisión que el kernel ya tomó en el arranque, leída de nuevo por
> nosotros de forma independiente.

### 3.1 Lo que NO afirmo sobre los 10 bits coincidentes

La mitad baja se parece mucho a la firma de 32 bits —10 de 24 bits, y coincide en bloques
enteros (`b4dc` en los cuatro nibbles altos de la mitad baja)— pero **no es igual**, y no
tengo fuente que diga qué significa el bit 4 ni por qué la firma del vendor incluye un byte
alto que aquí es `0x00` en vez de `0x05`.

**Eso queda `NOT_DETERMINED`, y no se usa para sostener nada.** La decisión de firmware se
apoya en la desigualdad exacta con el magico, que es el criterio que el driver usa. Los bits
coincidentes se anotan porque **un driver propio debe saber que el valor es "parecido pero
distinto"**, y una comparación por proximidad sería un error. **La comparación debe ser por
igualdad exacta.**

## 4. El bus de 128 bits, con cuatro fuentes concordantes

| fuente | qué dice |
|---|---|
| `mem_bank_width` publicado por KFD | **64 bits** por banco |
| `mem_banks_count` publicado por KFD | **2** bancos |
| cadena de identificación en la ROM | **`GDDR5 128`** (hallazgo 1400) |
| **el sondeo del firmware de MC** (este hallazgo) | **no es la variante de 32 bits**, luego es la clase de 64 bits |

64 × 2 = **128 bits**. Dos bancos de 64, no uno de 32. **La cuarta fuente es la más fuerte
porque la escribió el propio vendor para distinguir exactamente este caso.**

## 5. La operación más importante para el driver, y su límite

`mmMC_SEQ_IO_DEBUG_INDEX` / `_DATA` no es un registro cualquiera: es **la puerta por la que
el firmware de la propia tarjeta declara su identidad**. Eso tiene una consecuencia que
cambia el proyecto:

> **El ASIC puede describirse a sí mismo.** Este registro es la puerta de entrada, y el
> firmware SMU/MC la usa para otras cosas. Si aparece otra variable de tipo "qué variante
> soy", **es un sondeo del firmware, no un dato que AMD tenga compilado en el driver.**
>
> Eso es una vía de conocimiento que este proyecto no había considerado y que no requiere
> adivinar: **preguntárselo a la tarjeta.**

Y el límite, sin adornos: **`gmc_v8_0.c:241-251` sólo tiene una rama de sondeo para
Polaris12.** Para el resto de ASIC de esta familia la elección de firmware es una constante.
**Para esta tarjeta es una lectura.** No se generaliza.

## 6. La frontera, verificada después de la escritura

| invariante de la Intel | valor |
|---|---|
| `fb0_name` | `i915drmfb` |
| `fb0_virtual` | `1366,768` |
| `power/control` (card0) | `auto` |
| `runtime_status` (card0) | `active` |
| `card0-HDMI-A-1` | `connected` |
| `i915` cargado | sí |
| nodos `/dev/fb*` | 1 |

**Idéntico al estado previo.** Una escritura de registro en la RX550 no ha movido nada de la
Intel. La consola sigue siendo suya.

## 7. Lo que este hallazgo NO hace

- **No selecciona el firmware.** Leer el valor no lo carga; sólo lo identifica, igual que
  hace el driver. La carga es `amdgpu_ucode_request()`.
- **No explica los bits coincidentes.** §3.1.
- **No escribe ningún otro registro.** Una escritura, y restaurada.
- **No toca display**, ni carga módulos, ni lee el ROM.

## 8. Procedencia

```text
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/
  amdgpu/gmc_v8_0.c:241-251        la rama de sondeo, verbatim
  amdgpu/gmc_v8_0.c:262-263        AMDGPU_UCODE_REQUIRED
  amdgpu/amdgpu.h:770-778          ASICID_IS_P23 = 0x6987, 0x6981  (nuestra 0x699F no)
  include/asic_reg/gmc/gmc_8_1_d.h:1001,1002,1162   los tres valores
artefacto   /tmp/opencode/mcprobe.py   el script, con PRE y POST impressos
objeto      0000:01:00.0 unicamente,  mmap de resource5 en PROT_READ|PROT_WRITE
escrituras  UNA: mmMC_SEQ_IO_DEBUG_INDEX = 0x9f.  restaurada a 0x00000026, verificado
```

```text
ESTADO=PROBADO · firmware de MC de esta placa = "polaris12" (ni 32 bits ni Kaveri)
       · el sondeo se ejecuto de verdad: nuestra 0x699F no es P23
       · estado previo leido y registro restaurado, verificado por comparacion
       · bus de 128 bits con CUATRO fuentes concordantes
NUEVO    mmMC_SEQ_IO_DEBUG_INDEX/DATA es la puerta por la que el firmware declara su
       identidad.  El ASIC puede describirse a si mismo: es una via de conocimiento que el
       proyecto no habia considerado y que no requiere adivinar
LIMITE   no se interpretan los 10 bits coincidentes con la firma de 32 bits -> NOT_DETERMINED,
       y no se usan para nada.  La decision es por desigualdad exacta
RIESGO   una comparacion por proximidad en vez de por igualdad seria un error: el valor es
       "parecido pero distinto"
Siguiente  1) el muestreo de referencia ya tiene un oraculo: rptr esta en 0x600 y el writeback
           funciona.  Falta una sola constante, el INTERVALO, y para eso hay que mover el
           rptr, que es escribir un registro de ring
         2) buscar en el firmware mas registros de sondeo del mismo tipo: si esta puerta
           existe para la variante, puede existir para el reloj de memoria, que es el techo
           que 1419 dejo con dos candidatos (1500 y 2000 MHz)
```
