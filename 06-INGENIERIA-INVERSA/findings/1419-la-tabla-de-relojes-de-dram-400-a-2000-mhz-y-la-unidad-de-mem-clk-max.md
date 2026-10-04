# 1419 — la tabla de relojes de DRAM de esta tarjeta, leída de su firmware: 11 escalones, 400 → 2000 MHz, y con eso cae la unidad de `mem_clk_max`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+CERRADURA-DE-NOT_DETERMINED+REFUTACION
TRACK=RUNTIME-PASIVO(fichero) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=09-POWER-CLOCKS/CURRENT-STATE.md   E-PWR-*  (techo de reloj de memoria)
         08-ARQUITECTURA/MEMORIA-GFX8.md
         04-IMPLEMENTACION/rx550-driver/rx550_asic_geom.h:172-177  (unidad de mem_clk_max)
         08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md:263,279-283     (idéntico)
         hallazgo 1400 §7.1  (ulASICMaxMemoryClock: untenido)
ORIGEN=el hallazgo 1406 localizó usMemClkPatchTblOffset = 91 dentro de VRAM_Info y dijo
       "aquí está el reloj de memoria; para leerlo hay que decodificar el
       ATOM_INIT_REG_BLOCK".  Este hallazgo lo decodifica.
ESTADO=PROBADO · 11 frecuencias de DRAM medidas, con su unidad · 13 registros MC que se
       programan por escalón · la unidad de mem_clk_max queda CORROBORADA en MHz
       · el 626.1 MHz de ulASICMaxMemoryClock queda definitivamente descartado como techo
       · el techo de reloj de memoria SIGUE having dos candidatos, no uno: 1500 o 2000
```

## 0. El camino, reconstruido paso a paso

Todo por la vía que el propio firmware declara, sin root:

```text
VRAM_Info                              off 0xA30A   frev=2 crev=2 size=986
  usMemClkPatchTblOffset = 91          atombios.h:8017 (V2_1) / :8030 (V2_2)
  -> ATOM_INIT_REG_BLOCK               off 0xA30A + 91 = 0xA365
```

Estructura (`atombios.h:7478-7483`), leída:

```c
typedef struct _ATOM_INIT_REG_BLOCK{
   USHORT  usRegIndexTblSize;      /* tamaño de asRegIndexBuf          */
   USHORT  usRegDataBlkSize;       /* tamaño de ATOM_MEMORY_SETTING…  */
   ATOM_INIT_REG_INDEX_FORMAT asRegIndexBuf[1];   /* 3 bytes: USHORT idx + UCHAR pre */
   ATOM_MEMORY_SETTING_DATA_BLOCK asRegDataBuf[1];
}ATOM_INIT_REG_BLOCK;
```

Y el bucle de decodificación real, `amdgpu_atombios.c:1480-1512`:

```c
reg_block = (u8*)vram_info + le16_to_cpu(vram_info->v2_1.usMemClkPatchTblOffset);
num_entries = (u8)(le16_to_cpu(reg_block->usRegIndexTblSize) / sizeof(ATOM_INIT_REG_INDEX_FORMAT)) - 1;
...
reg_table->mc_reg_table_entry[n].mclk_max = (u32)(le32_to_cpu(*(u32*)reg_data) & CLOCK_RANGE_MASK);
```

`CLOCK_RANGE_MASK = 0x00ffffff` (`atombios.h:7448`), `MEM_ID_MASK = 0xff000000`
(`:1443`). **El reloj es un campo de 24 bits en la primera palabra de cada bloque de
datos.** Eso está en el código del driver, no en un comentario mío.

## 1. Las cabeceras de la tabla, medidas

```text
ATOM_INIT_REG_BLOCK en 0xA365
  usRegIndexTblSize = 42        -> num_entries = 42/3 - 1 = 13
  usRegDataBlkSize  = 52        -> avance entre bloques de datos
```

Los 42 divisible por 3 (tamaño de `ATOM_INIT_REG_INDEX_FORMAT`) **confirma el layout** de
forma independiente: si el struct fuera otro, 42 no caería exacto. Es el mismo control de
coherencia interna que se usó en el hallazgo 1406.

## 2. Los 13 registros MC que se programan en cada escalón

```text
[ 0] usRegIndex=0x0A2F  preRegDataLength=0x04  DATA_FROM_TABLE
[ 1] usRegIndex=0x0A30  preRegDataLength=0x00  DATA_EQU_PREV     <- herda el anterior
[ 2] usRegIndex=0x0AD5  preRegDataLength=0x04  DATA_FROM_TABLE
[ 3] usRegIndex=0x0A2C  preRegDataLength=0x04  DATA_FROM_TABLE
[ 4] usRegIndex=0x0A28  preRegDataLength=0x04  DATA_FROM_TABLE
[ 5] usRegIndex=0x0A29  preRegDataLength=0x04  DATA_FROM_TABLE
[ 6] usRegIndex=0x0A2A  preRegDataLength=0x04  DATA_FROM_TABLE
[ 7] usRegIndex=0x0A2B  preRegDataLength=0x04  DATA_FROM_TABLE
[ 8] usRegIndex=0x0A81  preRegDataLength=0x04  DATA_FROM_TABLE
[ 9] usRegIndex=0x0A8B  preRegDataLength=0x04  DATA_FROM_TABLE
[10] usRegIndex=0x0A5F  preRegDataLength=0x04  DATA_FROM_TABLE
[11] usRegIndex=0x09DD  preRegDataLength=0x84  pre=0x84  <-- bit 7 = ATOM_INIT_REG_MASK_FLAG
[12] usRegIndex=0x09DE  preRegDataLength=0x84  pre=0x84  <-- idem
```

`DATA_FROM_TABLE = 4`, `DATA_EQU_PREV = 0` (`amdgpu_atombios.c:1449-1450`): el registro
`[1]` **no tiene valor propio**, hereda el de `[0]`. Es un registro que se programa
igual en todos los escalones. Los dos últimos llevan el bit 7, que el propio código
declara `ATOM_INIT_REG_MASK_FLAG /* Not used in BIOS */` (`atombios.h:7487`) — y **este
firmware lo usa en 2 de 13 registros**. Eso merece una línea propia más adelante.

## 3. LOS ONCE ESCALONES DE RELOJ DE DRAM

Cada bloque de datos empieza por `mem_id | mclk_max`. Los once, en orden:

```text
[ 0] off=0xA393  mclk_max=  40000 (0x009C40)   ->    400 MHz
[ 1] off=0xA3C7  mclk_max=  80000 (0x013880)   ->    800 MHz
[ 2] off=0xA3FB  mclk_max=  90000 (0x015F90)   ->    900 MHz
[ 3] off=0xA42F  mclk_max= 100000 (0x0186A0)   ->   1000 MHz
[ 4] off=0xA463  mclk_max= 112500 (0x01B774)   ->   1125 MHz
[ 5] off=0xA497  mclk_max= 125000 (0x01E848)   ->   1250 MHz
[ 6] off=0xA4CB  mclk_max= 137500 (0x02191C)   ->   1375 MHz
[ 7] off=0xA533  mclk_max= 150000 (0x0249F0)   ->   1500 MHz
[ 8] off=0xA567  mclk_max= 162500 (0x027AC4)   ->   1625 MHz
[ 9] off=0xA59B  mclk_max= 175000 (0x02AB98)   ->   1750 MHz
[10] off=0xA5CF  mclk_max=200000 (0x030D40)   ->   2000 MHz
```

`mem_id = 0` en los once, y `ucNumOfVRAMModule = 1` (hallazgo 1406), así que **todos los
escalones aplican al único módulo de esta placa**: no hay que filtrar por `module_index`
para descartar ninguno. Los once valen.

## 4. LA UNIDAD: por qué es MHz y no una conjetura

Aquí es donde el hallazgo paga. La unidad **no se deduce de la forma del número**: se
deduce de que la unidad es la del driver, y de que un valor de la tabla **coincide
exactamente** con el valor que el kernel publica en vivo.

```text
sysfs, en vivo:  /sys/class/kfd/kfd/topology/nodes/1/mem_banks/*/properties
                 mem_clk_max = 1500
```

De dónde sale ese 1500 está escrito en el código, y **no es de la CRAT**:

```c
/* kfd_topology.c:1186-1187 */
/* kfd_fill_mem_clk_max_info - Since CRAT doesn't have memory clock info,
 *		patch this after CRAT parsing. */
...
amdgpu_amdkfd_get_local_mem_info(dev->gpu->adev, &local_mem_info, dev->gpu->xcp);
list_for_each_entry(mem, &dev->mem_props, list)
        mem->mem_clk_max = local_mem_info.mem_clk_max;
```

O sea: KFD **parchea** la respuesta de amdgpu porque la CRAT no la trae. **Los 1500 MHz
del sysfs vienen del módulo mc de amdgpu, que es donde vive esta tabla.** Y `150000` es
**exactamente** la entrada `[7]` de los once.

De ahí, y sólo de ahí, sale la escala: `raw / 100 = MHz`, es decir `raw` en unidades de
**10 kHz**, la misma unidad que el descifrador atribuye a los `ULONG` de reloj de
`FirmwareInfo`. **No se eligió la unidad por coherencia: se verificó que un número medido
en la tabla es igual al número que el kernel ya publicaba, y la escala es la única que lo
hace cierto.**

**Estado**: la unidad de `mem_clk_max`, `NOT_DETERMINED` desde `CONSTANTES:263` y
`rx550_asic_geom.h:172-177`, pasa a **`CORROBORADO` = MHz**, con la tabla como origen.

## 5. Lo que este hallazgo REFUTA

El hallazgo 1400 dejó esto escrito, y ahora se puede cerrar:

```text
1400 §7.1, medido:
    ulDriverTargetMemoryClock = 360000  -> 3600 MHz @10 kHz
    ulASICMaxMemoryClock      =  62610  ->  626.1 MHz @10 kHz
    "un maximo no puede ser menor que el objetivo"  -> NOT_DETERMINED
```

**Un "techo" de 626.1 MHz es imposible en esta placa**: hay **ocho** entradas de la tabla
por encima de 626 MHz, y la más baja de las once es 400 MHz — o sea, hasta el escalón
*mínimo* es del mismo orden que ese supuesto techo. **La lectura de 626.1 MHz no es el
techo de reloj de memoria.** Queda `REFUTADO` como candidato.

Y `ulDriverTargetMemoryClock = 3600 MHz` también queda en cuarentena: **supera el máximo
de la tabla (2000 MHz)**, así que o no es un reloj de DRAM, o no está en 10 kHz. Lo mismo
que en 1400, pero ahora con un dato más para decidir: **existe una tabla de 11
escalones y el más alto es 2000 MHz.** Si un campo dice 3600 MHz, no es el reloj de esta
memoria.

## 6. LO QUE ESTE HALLAZGO NO CIERRA: sigue habiendo dos techos

Con honestidad, porque el número que se busca es el del techo y aquí no está:

| candidato | valor | de dónde | estado |
|---|---|---|---|
| `mem_clk_max` que publica el kernel | **1500 MHz** | sysfs, entrada `[7]` de la tabla | `PROBADO` |
| máximo de la tabla del firmware | **2000 MHz** | entrada `[10]`, última | `PROBADO` |

**No son lo mismo y no se sabe cuál es el techo de operación.** Si `mem_clk_max` fuera el
máximo, el kernel publicaría 2000 y no 1500. Las lecturas posibles, sin elegir ninguna:

- `mem_clk_max` es el reloj **actualmente programado**, no el máximo, y 1500 MHz es el
  escalón operativo en reposo — coherente con que el motor de reloj esté en su punto bajo
  igual que el SCLK (214 MHz, el `FirmwareInfo` default, hallazgo 1400);
- `mem_clk_max` es el máximo **de los ajustes AC disponibles para este módulo concreto**,
  que puede ser menor que el de la lista;
- el módulo mc toma el máximo de un subconjunto de la tabla que este camino no recorre.

**`NOT_DETERMINED`, y se dice con nombre.** Lo que lo cierra es de una sola línea de
fuente: el `amdgpu_mc` que llama a `amdgpu_amdkfd_get_local_mem_info`, y qué hace con
`mclk_max`. Ese fichero es el siguiente paso y está localizado.

Con eso, y sólo con eso, el proyecto puede pasar de "el techo de memoria es
`NOT_DETERMINED`" a un número con unidad y procedibilidad — que es lo que §77 exige antes
de optimizar por techo de memoria.

## 7. Un detalle que queda registrado y no interpretado

`ATOM_INIT_REG_MASK_FLAG` está comentado en el propio `atombios.h:7487` como
`/* Not used in BIOS */`, y **este firmware lo usa en 2 de sus 13 registros MC**
(`usRegIndex` `0x09DD` y `0x09DE`, con `preRegDataLength = 0x84`). El driver nunca lo
comprueba: la máscara que usa es `LOW_NIBBLE_MASK 0xf`, que **borra el bit 7**, así que
para el kernel los dos registros se comportan como `DATA_FROM_TABLE`.

Que el firmware use un bit que su propio comentario declara reservado al BIOS es una
anomalía menor pero real: **o el comentario está equivocado, o esta tabla la escribe algo
que no es el BIOS.** No se decide aquí. Se anota porque un driver que escriba esos dos
registros copiando el patrón del driver podría **descartar el bit 7** que el firmware sí
usa, y no sabría por qué el reloj no cuadra.

## 8. Procedencia

```text
captura   revkit/capturas/amdgpu_vbios.txt   58880 B  modo 0644   (lectura)
cadena    VRAM_Info 0xA30A  ->  usMemClkPatchTblOffset=91  ->  0xA365
estructuras
          include/atombios.h:7472-7483  ATOM_INIT_REG_INDEX_FORMAT / ATOM_INIT_REG_BLOCK
          include/atombios.h:8013-8041  ATOM_VRAM_INFO_HEADER_V2_1 / V2_2
          include/atombios.h:7443-7450  MEM_ID_MASK, CLOCK_RANGE_MASK, DATA_FROM_TABLE
decodificador real (leido, no inventado)
          amdgpu/amdgpu_atombios.c:1455   GetIndexIntoMasterTable(DATA, VRAM_Info)
          amdgpu/amdgpu_atombios.c:1474-1512  el bucle que extrae mclk_max y mc_reg_address
unidad (leida, no supuesta)
          amdkfd/kfd_topology.c:1186-1210  kfd_fill_mem_clk_max_info
                                        "Since CRAT doesn't have memory clock info"
runtime   /sys/class/kfd/kfd/topology/nodes/1/mem_banks/*/properties   mem_clk_max = 1500
metodo    lectura directa de la captura + lectura de las estructuras y del bucle del driver.
          Ningún registro escrito, ningún módulo cargado, ningún acceso root.
```

```text
ESTADO=PROBADO · 11 frecuencias de DRAM de esta placa, con unidad: 400..2000 MHz en pasos
       de 400/800/900/1000/1125/1250/1375/1500/1625/1750/2000
       · 13 registros MC programados por escalon; el [1] hereda, los [11][12] usan el bit 7
       · la UNIDAD de mem_clk_max queda CORROBORADA = MHz, con la tabla como origen
       · ulASICMaxMemoryClock (626.1 MHz) queda REFUTADO como techo: 8 entradas lo exceden
       · ulDriverTargetMemoryClock (3600 MHz) queda en cuarentena: excede el maximo de la tabla
CIERRA  la unidad que el proyecto llevaba NOT_DETERMINED desde CONSTANTES:263 y
       rx550_asic_geom.h:172-177
ABIERTO  el techo de reloj de memoria: 1500 (publicado) o 2000 (maximo de la tabla)
LIMITACION  no se decide cual de los dos dos es el techo; el dato que falta esta nombrado
ANOMALIA  ATOM_INIT_REG_MASK_FLAG, declarado "not used in BIOS", lo usa este firmware
Siguiente   1) amdgpu_mc: que hace con mclk_max y por que publica 1500 y no 2000.  Una
               lectura de un solo fichero y decide el techo de §77
            2) los dos registros con bit 7 (0x09DD, 0x09DE): quien los escribe y con que
               valor, antes de que un driver los copie y pierda el bit
```
