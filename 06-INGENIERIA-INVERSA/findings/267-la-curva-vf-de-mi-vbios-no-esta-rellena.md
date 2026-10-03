# 267 · La curva V-f de mi VBIOS no esta rellena: los voltajes son indices y los objetos parecen vacios

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Correccion a `266`
>
> Escribi alli que `ATOM_Tonga_SCLK_Dependency_Record` "no existe con ese nombre
> en las cabeceras de este corpus". **Es falso.** Existe, en
> `pm/powerplay/hwmgr/pptable_v1_0.h:185`. Mi busqueda la hizo en `atombios.h` y
> por eso salio vacia: es `NOT_FOUND` **en esa cabecera**, no en el corpus.
> Fallo de alcance de lectura, no una ausencia. El nombre real de la cabecera
> aparecia en la propia linea que yo estaba citando.

## El layout, medido

`pptable_v1_0.h:185-214`, dos versiones:

```
ATOM_Tonga_SCLK_Dependency_Record    11 B   (ucRevId < 1)
  ucVddInd UCHAR | usVddcOffset USHORT | ulSclk ULONG
  usEdcCurrent USHORT | ucReliabilityTemperature UCHAR
  ucCKSVOffsetandDisable UCHAR

ATOM_Polaris_SCLK_Dependency_Record  15 B   (ucRevId >= 1)
  lo mismo + ulSclkOffset ULONG
```

**Mi captura mide 15 bytes por registro**, luego es la version **Polaris**. Y eso
queda corroborado por una aritmetica independiente: `0x9D17 + 8 * 15 = 0x9D8F`,
que es exactamente donde empieza la tabla MCLK.

## Mi tabla SCLK, decodificada

Cabecera en `0x9D15`: `ucRevId = 1`, `ucNumEntries = 8`.

| lvl | `ulSclk` | MHz | `ucVddInd` | `usVddcOffset` | `ulSclkOffset` | CKS |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 21400 | 214 | 0 | 0 | 0 | **deshabilitado** (`0x80`) |
| 1 | 55100 | 551 | 2 | **-26** | 3000 | habilitado |
| 2 | 73400 | 734 | 2 | 0 | 3000 | habilitado |
| 3 | 98000 | 980 | 5 | 0 | 3000 | habilitado |
| 4 | 100000 | 1000 | 6 | 0 | 1500 | habilitado |
| 5 | 102000 | 1020 | 7 | 0 | 1500 | habilitado |
| 6 | 104600 | 1046 | 8 | 0 | 1500 | habilitado |
| 7 | 107100 | **1071** | 9 | 0 | 1500 | habilitado |

**Los 8 `ulSclk` reproducen exactamente la reconstruccion de `121`** (214, 551,
734, 980, 1000, 1020, 1046, 1071 MHz). Corroboracion independiente de un claim
ya publicado, y esta vez con el registro decodificado byte a byte.

`usVddcOffset` del nivel 1 es `0xFFE6`, que como `int16` es **-26**; el resto
cero. `usEdcCurrent` y `ucReliabilityTemperature` valen cero en los ocho.

## El hallazgo: el voltaje no esta en la tabla

**`ucVddInd` no es un voltaje: es un indice.** Los valores son 0, 2, 2, 5, 6, 7,
8, 9 — una lista de indices, no milivoltios. El voltaje real se reconstruye en
dos pasos, y el codigo lo deja explicito
(`process_pptables_v1_0.c:460-466`):

```c
sclk_table_record->vddInd     = sclk_dep_record->ucVddInd;      /* indice, no mV */
sclk_table_record->vdd_offset = le16_to_cpu(sclk_dep_record->usVddcOffset);
```

El primer paso es sumar una **tension base** que sale de la **tabla de busqueda de
voltajes**, que es `vddc_lookup_table`, y esa es la **`VoltageObjectInfo` en
`0xA7F4`**.

Y `134` ya midsu contenido: **los tres objetos de voltaje parecen sin rellenar**
— tres campos a cero y dos GPIO iguales. Titulo de `134`: *"el VBIOS pone a cero
lo que el driver usa como autoritativo"*.

De ahi sale la cadena completa, y es el punto de esta iteracion:

```
VBIOS, nivel 7 (1071 MHz):  ucVddInd = 9, usVddcOffset = 0
        |
        v  VoltageObjectInfo[9]  ->  PROVEN_APARENTLY_UNFILLED (segun 134)
        |
        v  vddc = base[9] + 0 = 0
        |
        v  polaris10_get_dependency_volt_by_clk (:370)
           *voltage = (vddc * VOLTAGE_SCALE) << VDDC_SHIFT = 0
```

**El voltaje minimo que el driver calcula para el nivel mas alto es cero.**

Y hay un segundo problema, independiente: **el indice 9 con una tabla de 3
objetos**. Los indices que usa mi tabla SCLK son 0, 2, 5, 6, 7, 8 y 9. Si la
tabla de voltajes tiene 3 entradas, entonces **6 de los 8 niveles de reloj
apuntan fuera de rango**. `134` ya habia medido el margen: "tres entradas, tres
slots declarados, margen cero".

## Lo que esto significa para el techo de SCLK

Mi `265` afirmo que el techo lo fija el VBIOS en 1071 MHz. **Eso se sostiene como
numero de reloj**, pero ahora hay que anadirle el matiz que lo hace un techo
**declarado y no verificado**:

- El nivel mas alto existe y dice 1071 MHz.
- Su voltaje minimo declarado resuelve a **0**.
- Siete de los ocho niveles usan indices que **no existen** en una tabla de 3.

O sea: **la curva V-f de mi placa no es utilizable tal como viene.** El reloj
maximo esta declarado, pero el voltaje que lo sostiene no esta en la captura.

## Lo que NO afirmo

- **NO** afirmo que la placa no pueda correr a 1071 MHz. Afirmo que **esta
  captura no contiene el voltaje que lo sostiene**. Son cosas distintas, y la
  segunda no implica la primera.
- **NO** he medido ningun voltaje ni reloj. `B_RUNTIME = NOT_EXECUTED`.
- **NO** afirmo que `134` tenga razon en que los objetos estan vacios: lo doy
  por cerrado porque es un claim mio ya publicado, y su conclusion es
  `PROVEN_DERIVED`. Si se cae, esta conclusion cae con el.
- No he tocado hardware, firmware ni VBIOS.

## Lo que esto cierra y lo que abre

**Cierra:** la causa por la que no tenia curva V-f. No era que me faltara el
campo — es que **el campo es un indice y su destino esta vacio**.

**Abre, y es la accion siguiente:** los indices fuera de rango. Siete de ocho
niveles apuntan a slots que `VoltageObjectInfo` no declara. Eso es
`OUT_OF_BOUNDS` potencial en el calculo de `MinVoltage`, y hay dos
hipotesis separables:

- **H1**: el firmware SMC ignora `ucVddInd` y usa su propia tabla. Entonces el
  cero del host es inofensivo.
- **H2**: el firmware lee `MinVoltage` tal cual, recibe 0 para todo, y el
  clock stretching de `132` pasa a ser **imprescindible** en vez de opcional,
  porque es lo unico que evita pedir 1071 MHz sin voltaje.

Discriminante barato: si `usBootUpMVDDCVoltage = 1500 mV` (offset 92 del VBIOS,
que ya tengo) es el unico voltaje real disponible, entonces el firmware **tiene
que** corregirlo de algun modo, y H2 con un mecanismo de correccion. Ese es el
siguiente paso, y es lectura de VBIOS pura.