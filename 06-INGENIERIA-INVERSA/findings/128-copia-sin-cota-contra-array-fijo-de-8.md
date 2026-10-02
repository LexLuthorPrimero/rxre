# 128 · Una copia sin cota contra un array fijo de 8, y el limite de overdrive que la hace alcanzable

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

**Cierra el `NOT_IN_CORPUS` de `127` con un numero medido en mi VBIOS, y encuentra la copia que
ese hallazgo hacia falta. Empieza con una hipotesis mia que queda REFUTADA antes de publicar.**

## La hipotesis que refute

`polaris10_smumgr.c:970` (y `:1165`) hacen:

```c
if (hwmgr->od_enabled)
        vdd_dep_table = (phm_ppt_v1_clock_voltage_dependency_table *)&data->odn_dpm_table.vdd_dependency_on_sclk;
else
        vdd_dep_table = table_info->vdd_dep_on_sclk;
```

A primera vista es un **cast entre structs que no tienen nada en comun**. Lo primero que mire
fue si `vdd_dependency_on_sclk` era del mismo tipo, porque si no, el codigo estaria leyendo
`options` como si fuera `entries[0]` y `count` estaria leyendo `size`.

**Refutado antes de escribir nada:**

```c
/* smu7_hwmgr.h:177-180 */
struct smu7_odn_clock_voltage_dependency_table {
        uint32_t count;
        phm_ppt_v1_clock_voltage_dependency_record entries[MAX_REGULAR_DPM_NUMBER];
};
```

Mismo `count` en el offset 0, **y el mismo tipo de registro**. Los layouts coinciden. **El cast
es legitimo.**

> **Un cast no es una confusion de tipos hasta que se comprueban los dos layouts.** Pregunté
> «¿son estos dos tipos el mismo?» antes de escribir, y la respuesta fue que si. Casi publico
> un hallazgo que era una lectura a medias de la declaracion de un struct.

## El defecto real: la copia no tiene cota

```c
/* smu_helper.c:604-628 */
int smu_get_voltage_dependency_table_ppt_v1(
                const struct phm_ppt_v1_clock_voltage_dependency_table *allowed_dep_table,
                struct phm_ppt_v1_clock_voltage_dependency_table *dep_table)
{
        uint8_t i = 0;
        PP_ASSERT_WITH_CODE((0 != allowed_dep_table->count),
                        "Voltage Lookup Table empty", return -EINVAL);

        dep_table->count = allowed_dep_table->count;
        for (i = 0; i < dep_table->count; i++) {
                dep_table->entries[i].clk = allowed_dep_table->entries[i].clk;
                ...   /* 9 campos copiados uno a uno */
        }
        return 0;
}
```

El segundo argumento, en la firma, es un `struct phm_ppt_v1_clock_voltage_dependency_table` —
cuyo `entries[]` es de **tamano flexible**, y entonces este bucle estaria bien. **Pero los dos
unicos llamadores del arbol entero le pasan el mismo puntero, casteado:**

```c
/* smu7_hwmgr.c:961-962 */
smu_get_voltage_dependency_table_ppt_v1(dep_sclk_table,
        (struct phm_ppt_v1_clock_voltage_dependency_table *)&(odn_table->vdd_dependency_on_sclk));
/* smu7_hwmgr.c:973-974, idem para MCLK */
```

Y ese destino **real** es un array **fijo de `MAX_REGULAR_DPM_NUMBER = 8`** (`smu7_hwmgr.h:179`,
`MAX_REGULAR_DPM_NUMBER 8` en `smu7_hwmgr.h:95`).

**La firma promete un destino flexible y los dos llamadores dan uno fijo. El bucle no comprueba
nada contra 8.**

- `LA_COPIA_NO_COMPRUEBA_LA_CAPACIDAD = PROVEN`: `smu_helper.c:613-614`, no hay cota.
- `SOLO_HAY_DOS_LLAMADORES_Y_LOS_DOS_DAN_EL_ARRAY_FIJO = PROVEN`: `smu7_hwmgr.c:962` y `:974`.
- `CAPACIDAD = 8` y **el VBIOS de mi placa declara exactamente 8** (`121`): **margen cero.**

## La geometria del desbordamiento, medida con gcc

```
sizeof(phm_odn_performance_level)            =  12
sizeof(phm_odn_clock_levels)                 = 112   (16 + 8*12)
sizeof(registro de dependencia)               =  28
sizeof(smu7_odn_clock_voltage_dependency_t)  = 228   (4 + 8*28)

offsetof(smu7_odn_dpm_table, vdd_dependency_on_sclk) = 224
offsetof(smu7_odn_dpm_table, vdd_dependency_on_mclk) = 452
offsetof(od... min_vddc)=684  max_vddc=688  odn_mclk_min_limit=680
sizeof(smu7_odn_dpm_table)                   = 692
```

Y los offsets **reales** dentro del registro, medidos (mi aritmetica a mano fallaba por uno):

```
clk=0   vddc=10   vddci=14   mvdd=16
```

Con eso, un VBIOS que declarase **9 entradas SCLK** escribiria `entries[8]`, cuya base es
`452 + 4 + 8*28 = 680`:

| lectura de `entries[8]` | direccion | donde cae |
|---|---|---|
| `.clk` | **680** | justo `odn_mclk_min_limit` |
| `.vddc` | **689** | byte 1 de `max_vddc` |
| `.vddci` | **693** | **1 byte pasado el fin de la struct (692)** |
| `.mvdd` | **695** | **3 bytes pasados el fin de la struct (692)** |

**Las dos lecturas fuera de limite de `127` (`:408` lee `vddc`, `:414` lee `mvdd`) caen
exactamente en 689 y 695.** La de `:414` se sale **3 bytes del final de `smu7_odn_dpm_table`**.

Como la struct esta embebida en `struct smu7_hwmgr`, esos 3 bytes caen en un miembro
siguiente de `data`: **no hay fallo de pagina, hay basura leida**.

- `LA_LECTURA_DE_414_SE_SALE_3_BYTES_DE_LA_STRUCT = PROVEN`: 695 contra un total de 692.
- `NO_HAY_FALLO_DE_PAGINA_PORQUE_ODN_DPM_TABLE_NO_ESTA_AL_FINAL = PROVEN_DERIVED`: esta
  embebida en `smu7_hwmgr`, y hay miembros detras.

## Y los dos desbordamientos estan enmascarados hoy

Esto es lo que hace el hallazgo mas pequeno, y conviene decirlo de entrada:

1. **El de SCLK esta reparado por la siguiente linea.** El orden es SCLK primero (`:961`) y
   MCLK despues (`:973`). La llamada de MCLK ejecuta `dep_table->count = allowed->count` sobre
   `vdd_dependency_on_mclk`, que es exactamente la direccion que el desbordamiento de SCLK
   acaba de pisar. **El dato corrupto se sobrescribe inmediatamente.**
2. **El de MCLK cae en un campo que nadie lee.** `odn_mclk_min_limit` (680) aparece en **tres
   cabeceras como declaracion y en ningun `.c` de todo `amdgpu`**. Buscado por nombre completo
   y por el patron partido `mclk_min_limit`: solo las tres declaraciones.

- `EL_DESBORDAMIENTO_DE_SCLK_LO_REPARA_LA_LLAMADA_SIGUIENTE = PROVEN_DERIVED`: `:974` escribe
  esa direccion justo despues.
- `EL_DE_MCLK_CAE_EN_UN_CAMPO_SIN_LECTORES = PROVEN`: `odn_mclk_min_limit` declarado en smu7,
  vega12 y vega20, leido en ninguno.

**Asi que el defecto es real y hoy inocuo, por dos razones que se pueden cancelar en cuanto
alguien lea `odn_mclk_min_limit` o reordene las dos llamadas.**

## La parte que si importa: el limite de overdrive, medido

`127` dejo abierto si Ruta B de `polaris10_get_dependency_volt_by_clk` puede ejecutarse. La
puerta es `smu7_check_clk_voltage_valid:5583-5590`:

```c
if (type == PP_OD_EDIT_SCLK_VDDC_TABLE) {
        if (data->golden_dpm_table.sclk_table.dpm_levels[0].value > clk ||
            hwmgr->platform_descriptor.overdriveLimit.engineClock < clk)
                return false;                 /* fuera de rango */
}
```

El techo es `overdriveLimit.engineClock`, que sale de `ulMaxODEngineClock` **sin conversion**
(`process_pptables_v1_0.c:886-887`, `le32_to_cpu` a secas). Y ese campo esta en mi VBIOS.

**Ubicacion, por dos vias independientes:**

1. Buscando el valor conocido `ulPlatformCaps = 0x068000`: aparece en `0x9C1D`. La tabla
   arranca en `0x9C0A`. **Offset = 19.**
2. Aritmetica: `ATOM_COMMON_TABLE_HEADER` = `USHORT + UCHAR + UCHAR` = **4 bytes**
   (`atombios.h:208-214`, con `#pragma pack(1)` en `atombios.h:191`). Luego
   `1 + 2 + 4 + 4 + 2 + 2 = 15`. **4 + 15 = 19.** Coincide.

**No hay confirmacion por gcc**: `gccverify` no compila este arbol (faltan las cabeceras
generadas de `arch/x86/include/generated`, el bloque conocido de `xref`), y `struct_layout` no
busca en el subarbol `powerplay`. **La aritmetica con el struct leido del codigo es la segunda
via, y basta porque las dos convergen en 19.**

**Los valores:**

```
ulMaxODEngineClock  = 180000
ulMaxODMemoryClock  = 225000
```

**Unidad: 10 kHz.** No es una suposicion: el propio driver imprime
`overdriveLimit.engineClock/100` rotulado «MHz» (`smu7_hwmgr.c:5586`), o sea
`valor/100 = MHz` ⟹ `unidad = 10 kHz`. Y es la misma unidad que midio `121` en la tabla de
dependencia.

```
overdriveLimit.engineClock = 1800 MHz
maximo de la tabla dep SCLK = 1071 MHz     (121)
```

**1800 > 1071.** Un usuario puede fijar por overdrive un reloj **por encima del maximo de la
tabla donde se busca**.

- `UL_MAX_OD_ENGINE_CLOCK = 180000 = 1800 MHZ = PROVEN`: dos vias de ubicacion, unidad por el
  propio print del driver.
- `EL_LIMITE_DE_OD_SUPERA_EL_MAXIMO_DE_LA_TABLA = PROVEN`: 1800 contra 1071.
- `POR_TANTO_RUTA_B_DE_127_ES_ALCANZABLE = PROVEN_DERIVED`: `:4354-4358` mete el reloj del
  usuario en `dpm_table.sclk_table.dpm_levels[].value`, `:5584-5585` lo acepta hasta 1800, y
  `:369` no encuentra entrada ⟹ caida del bucle ⟹ Ruta B.
- `CONFIRMACION_POR_GCC = NO_COMPARABLE`: bloque de cabeceras generadas. **No se inventa el
  numero.**

**Y una consecuencia que `127` no tinha:** la tabla de OD es un array **fijo** de 8, no una
reserva exacta. Asi que `entries[count]` con `count == 8` **no se sale de la reserva, se sale
del array** — y cae en la tabla de MCLK, que es justo lo medido arriba. **El alcance de `127`
queda cerrado y con direccion.**

## Un detalle lateral: `uint8_t i`

```c
uint8_t i = 0;
for (i = 0; i < dep_table->count; i++)
```

`i` es de 8 bits y `count` es `uint32_t`. El bucle **no se cuelga** mientras `count <= 255`, y
`count` viene de `ucNumEntries`, que es `UCHAR`. **Es seguro por el tipo del campo de origen, no
por diseno del bucle**: un `count` de 256 lo dejaria dando vueltas.

- `EL_BUCLE_SOLO_ES_SEGURO_PORQUE_UCCOUNT_ES_UCHAR = PROVEN_DERIVED`: `pptable_v1_0.h:196`.
- `UN_COUNT_DE_256_COLGARIA = PROVEN_DERIVED`: `i` desborda a 0 y la condicion se cumple otra vez.

## Clasificacion

- `MI_HIPOTESIS_DE_CONFUSION_DE_TIPOS = REFUTADA`: mismo `count` en 0 y mismo registro.
- `LA_FIRMA_PROMETE_UN_DESTINO_FLEXIBLE_Y_LO_ES_DOS_LLAMADORES_DAN_UNO_FIJO = PROVEN`:
  `smu_helper.c:606` frente a `smu7_hwmgr.h:179`.
- `LA_COPIA_NO_COMPRUEBA_LA_CAPACIDAD = PROVEN`: `smu_helper.c:613-614`.
- `CAPACIDAD_8_Y_MI_VBIOS_DECLARA_8 = PROVEN`: margen cero, con `121`.
- `GEOMETRIA_DEL_DESBORDAMIENTO_MEDIDA = PROVEN`: 680 / 689 / 693 / 695 contra un total de 692.
- `LA_LECTURA_DE_414_SE_SALE_3_BYTES = PROVEN`
- `AMBOS_DESBORDAMIENTOS_ESTAN_ENMASCARADOS_HOY = PROVEN`: por `:974` y por un campo sin
  lectores.
- `UL_MAX_OD_ENGINE_CLOCK = 1800 MHZ = PROVEN`: dos vias de ubicacion
- `EL_LIMITE_DE_OD_SUPERA_EL_MAXIMO_DE_LA_TABLA = PROVEN`: 1800 contra 1071
- `RUTA_B_DE_127_ES_ALCANZABLE_CON_OVERDRIVE = PROVEN_DERIVED`
- `CONFIRMACION_POR_GCC = NO_COMPARABLE`: no se inventa
- `EL_BUCLE_SOLO_ES_SEGURO_POR_EL_TIPO_DE_UCCOUNT = PROVEN_DERIVED`

## Lo que esto obliga a hacer en un driver propio

1. **Una copia entre dos tablas lleva la capacidad de destino en la firma.** Aqui la firma dice
   `struct phm_ppt_v1_..._table *` (flexible) y los dos llamadores dan un array de 8. **El
   contrato escrito no es el contrato real.**
2. **Si el destino es fijo, la cota se comprueba en la copia**, no en el que llama. Si el
   llamador tiene que comprobarlo, van a existir dos llamadores y solo uno lo hara.
3. **Un margen cero se anota como margen cero.** Mi VBIOS declara 8 y el array es de 8. Hoy
   funciona. Mañana, otro VBIOS con 9 y hay un bloque de 28 bytes fuera, **sin que nada avise**.
4. **Un enmascaramiento es una defensa que se puede cancelar.** Este caso es el segundo: la
   llamada siguiente pisa lo que el desbordamiento escribio, y el otro campo no lo lee nadie.
   **Las dos protecciones son casualidad, no codigo.**
5. **Medir el limite, no suponerlo.** `127` no podia cerrarse sin saber si 1800 MHz cabe en una
   tabla cuyo maximo es 1071. **Y cabe.** Esa medicion es la que convierte un `NOT_IN_CORPUS` en
   un alcance demostrado.

## Estado

Hallazgo **128**, y con el queda **cerrado el `NOT_IN_CORPUS` de `127`**: Ruta B **es**
alcanzable, con overdrive, y su lectura fuera de limite tiene direccion medida.