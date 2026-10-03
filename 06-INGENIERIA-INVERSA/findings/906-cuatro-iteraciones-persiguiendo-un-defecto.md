# 906 · Cuatro iteraciones persiguiendo un defecto de mi propio extractor

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> La contradicción que arrastraba desde `604` **no existía**. El árbol del
> corpus es correcto, la base `0x9C0A` es correcta, y `usClockStretchAmount` vale
> **2**. No hay ningún desfase de un byte en ninguna parte.
>
> El desfase estaba en **mi generador de probes**, que extraía el cuerpo de un
> struct con una expresión regular y lo compilaba fuera del `#pragma pack` que lo
> rodea. Cuatro hallazgos de este día se paraguas sobre eso.

## 1. El módulo cargado, que es la autoridad

`RESEARCH/kernelbuild/linux-7.1.3/` no es el árbol del kernel en marcha, pero
**la versión sí coincide** y el módulo tiene BTF:

```
uname -r                7.1.3-200.nobara.fc44.x86_64
vermagic del amdgpu.ko  7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload
seccion .BTF            presente
/sys/kernel/btf/vmlinux  6357197 bytes  (BTF base)
```

`pahole --btf_base=/sys/kernel/btf/vmlinux` sobre el `.ko` descomprimido da el
layout del **código compilado**, independiente de cualquier árbol de fuentes:

```c
struct _ATOM_Tonga_POWERPLAYTABLE {
        ATOM_COMMON_TABLE_HEADER   sHeader;              /*  0  4 */
        UCHAR                      ucTableRevision;      /*  4  1 */
        USHORT                     usTableSize;          /*  5  2 */   SIN RELLENO
        ULONG                      ulGoldenPPID;         /*  7  4 */
        ...
        USHORT   usMclkDependencyTableOffset;             /* 43  2 */
        USHORT   usSclkDependencyTableOffset;             /* 45  2 */
        USHORT   usPowerTuneTableOffset;                  /* 57  2 */
        USHORT   usPCIETableOffset;                       /* 61  2 */

struct _ATOM_Polaris_PowerTune_Table {
        UCHAR   ucRevId;                                 /*  0  1 */
        USHORT  usTDP;                                   /*  1  2 */   SIN RELLENO
        ...
        USHORT  usTjMax;                                 /* 17  2 */
        USHORT  usSoftwareShutdownTemp;                  /* 23  2 */
        USHORT  usClockStretchAmount;                    /* 25  2 */
```

**Los cinco valores que leí a mano del VBIOS son los del módulo.** Ninguno
coincide con lo que medí con gcc sobre mi árbol:

| campo | mi probe | **módulo (BTF)** | leí del VBIOS |
|---|---|---|---|
| `usTableSize` | @6 | **@5** | @5 = 77 ✓ |
| `usSclkDependencyTableOffset` | @46 | **@45** | @45 = 267 ✓ |
| `usPowerTuneTableOffset` | @58 | **@57** | @57 = 673 ✓ |
| `usPCIETableOffset` | @62 | **@61** | @61 = 752 ✓ |
| `usClockStretchAmount` | @26 | **@25** | @25 = **2** ✓ |

Y el BTF confirma el layout de la PCIe que usé para tumbar `601`:
`_ATOM_Polaris10_PCIE_Record` no tiene relleno (`@0, @1, @2, @4`) y
`entries[] @2`. **`601` sigue `REFUTED`**, y ahora con la autoridad del módulo.

## 2. La causa: mi extractor tira el `#pragma pack`

`pptable_v1_0.h` del corpus:

```
:30    #pragma pack(push, 1)
:498   #pragma pack(pop)
:100   typedef struct _ATOM_Tonga_POWERPLAYTABLE {      <-- DENTRO de la region
```

**El árbol empaqueta el struct correctamente.** `usTableSize` está en 5, no en 6,
porque el pragma se aplica. El árbol nunca tuvo el defecto.

Lo que hice fue esto, unas veinte veces a lo largo del día:

```
extraer  el CUERPO del struct con una expresion regular
emitirlo como   typedef struct A_X { <cuerpo> } A_X;
compilarlo en una unidad nueva
```

En esa unidad nueva **no hay `#pragma pack`**, porque se quedó en el fichero
original. gcc aplica alineación natural, y el struct sale con 1 byte de relleno
por cada transición `UCHAR` → `USHORT`.

**Eso explica los tres síntomas a la vez**: `usTableSize` en 6, los tres offsets
en 46/58/62, y `usClockStretchAmount` en 26. Un solo defecto, cuatro medidas.

## 3. Lo que queda `PROVEN` y lo que se cae

**Se cae, y era falso:**

| afirmación | estado real |
|---|---|
| «el VBIOS va empaquetado y el struct no» | **`REFUTED`**: los dos van empaquetados |
| «este árbol lee direcciones imposibles» | **`REFUTED`**: era mi probe |
| «este árbol no conduce mi placa» | **`REFUTED`**: la versión coincide y el árbol es correcto |
| «la captura está truncada» | **`REFUTED`** en `901`, dos veces |

**Se mantiene:**

| afirmación | estado |
|---|---|
| `base` del `PowerPlayInfo` = `0x9C0A` | **`PROVEN`**, cinco validaciones, y el BTF confirma los offsets que leí |
| `usClockStretchAmount` = **2** | **`PROVEN`**, BTF del módulo + lectura del VBIOS |
| `usPCIETableOffset` = 752 → `0x9EFA`, 3 entradas, carriles 8/8/8 | **`PROVEN`** |
| `601`: «desfase de 2 bytes en la PCIe» | **`REFUTED`**, ahora con BTF |

## 4. La contradicción de `604`: disuelta

`604`abrió un conflicto entre dos mediciones. No había dos bases candidatas:
había **una base, `0x9C0A`**, y **un offset, 57**, y la tabla estaba en `0x9EAB`,
y el campo en 25, y valía 2.

El «0x9EAA que da los cinco valores» era la misma lectura descrita con la base
desplazada un byte. Nunca fue una tabla alternativa.

## 5. Y con esto, qué pasa con `:2118`

Esta es la parte que cambia trabajo de verdad:

```
usClockStretchAmount = 2        (1..5 -> en dominio)
:1661  stretch_amount = 2
:1696  if (stretch == 0 || stretch > 5)   ->  FALSO, no aborta
:1693  LdoRefSel se escribe igualmente
:2005  result == 0, init_smc_table CONTINUA
:2118  LA COPIA DE 1776 B SE EJECUTA
```

Consecuencias, y estas son las que restauran el trabajo perdido:

- **`502` vuelve a ser válido**: sus **6 `TAPADA` tapan de verdad**, y las
  escrituras AVFS de `:142/:149/:157/:166` **no sobreviven**.
- **`505` queda `CORROBORATED`**: el cap está activo y el populate **tiene
  éxito**, que era su conclusión original.
- Los 95 campos con su último escritor, y las 16 puertas de `:1913`-`:2118`, se
  leen otra vez sobre la ruta que se ejecuta.

## 6. Los cuatro hallazgos que se equivocaron por esto

`604`plantó una contradicción inexistente y failover una premisa que era
cierta. `608`construyó sobre ella y llegó a «este árbol no es el que corre».
`901`llegó a `REFUTED` sobre el árbol, y a un capítulo entero dedicado a un
truncamiento que no existía. `605`necesitó una medición grande (buscar la firma
del discovery binary) por una premisa que ya estaba bien.

**Y la causa estaba identificada y escrita en `608` §6**, en las palabras que
escribí, y no la apliqué al escribir el probe siguiente.

> «Un artefacto que produce un resultado plausible no está validado por el hecho
> de ser plausible.»

El punto exacto del fallo es que **yo era el artefacto**. Medía el código con
gcc, comparaba con el VBIOS, veía coherencia, y trataba la coherencia como
prueba. La coherencia venía de mi extracción, así que era circular: **mi error
se validaba a sí mismo**.

## 7. La regla, y por qué esta vez sí la escribo como herramienta

Lo que faltaba era un segundo método que **no dependiera del que estaba
verificando**. La regla es esta:

> **El layout de un struct no se afirma con gcc sobre un cuerpo extraído. Se
> afirma con el BTF del módulo cargado, que es el código que corre.**

Y tiene una consecuencia operativa inmediata: **cualquier probe de `offsetof`
que genere tiene que declarar el contexto de empaquetado del struct**, o
verificarse contra el BTF antes de usarse.

Eso es una tarea repetida con un esquema claro, así que es una herramienta, y
`§78` del prompt la pide. Es el frente siguiente.

## 8. El resto de errores de la jornada, sin adornos

**Doce** ceros falsos y ausencias inventadas en este día, de cuatro familias
repetidas:

1. **Ámbito de búsqueda corto**: `pptable_v1_0.h` en `amd/include/`, `POWERPLAY`
   como token, `atomctrl.c` en `pm/atomctrl/`. Tres veces.
2. **`cut` comiendo el final**: `powerplay/Makefile` (línea de 101),
   `GetIndexIntoMasterTable` (143), `ATOM_ROM_TABLE_PTR` (leí `0x20` por `0x48`).
   Tres veces, y las tres afectaron a la conclusión del turno.
3. **Supuesto no medido**: `ATOM_COMMON_TABLE_HEADER` de 2 bytes (son 4),
   `ATOM_ATI_MAGIC_PTR = 0x30` sin verificar, «58880 no es potencia de dos luego
   está truncado», `ATOM_MASTER_LIST_OF_DATA` (no existe; es
   `ATOM_MASTER_LIST_OF_DATA_TABLES`). Cuatro veces.
4. **Generador de probes**: `%s` de C en `%` de Python, `%%zu`, llave de más,
   `return` suelto, y ahora el `#pragma pack` perdido. Cinco veces.

**Todas son lo mismo**: un artefacto mío, plausible, y falso, tratado como
medición. Y las cuatro familias se habrían cerrado con una sola cosa: **contar el
ámbito, verificar el `exit`, no recortar columnas, y no afirmar un offset sin un
segundo método que no dependa del primero.**

## Frontier siguiente

**Construir el extractor de structs que preserva el contexto de empaquetado y se
autovalida contra el BTF del módulo cargado.**

La pregunta es concreta: *¿puedo producir un `offsetof` de cualquier struct de
`amd/` que coincida con el BTF del `.ko` en marcha, sin intervención manual?*

Contrato, en la forma que pide `§22`:

```
ENTRADA   etiqueta del struct, fichero de cabecera
SALIDA    tabla de offsetof por campo, con el tamaño total
REGLA     si el struct cae dentro de un #pragma pack, emitirlo dentro
          de un #pragma pack equivalente en la unidad generada
VALIDACION  contra pahole --btf_base=/sys/kernel/btf/vmlinux sobre el .ko
PIVOTE    si no hay BTF para ese struct, el estado NO es VERIFICADO
          y no puede usarse como evidencia
```

**El PIVOTE es la parte que no puede faltar**: un `offsetof` que no se haya
contrastado con el BTF es `NOT_VERIFIED`, no `PROVEN`. Ese es exactamente el
hueco por el que pasó mi error, y por eso la herramienta se autoválida o no sirve.

Y una consecuencia que conviene decir en voz alta: **`901` y `608` deben quedar
marcados como construidos sobre un método defectuoso**, no solo corregidos. Sus
mediciones del código siguen siendo ciertas —el código es el que es— pero la
razón por la que las creí era falsa, y eso es parte del registro (§69).