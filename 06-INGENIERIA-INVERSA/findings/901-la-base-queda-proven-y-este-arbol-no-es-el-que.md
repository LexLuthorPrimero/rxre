# 901 · La base queda PROVEN, y este árbol no es el que conduce mi placa

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## ANULADO POR `906` — este hallazgo se construyó sobre un método defectuoso
>
> Texto íntegro conservado (§68), pero **su premisa central era falsa y la medí
> mal**.
>
> | afirmación de este fichero | estado real |
> |---|---|
> | «el VBIOS va empaquetado y el struct no» | **`REFUTED`**: los dos van empaquetados (`pptable_v1_0.h:30` tiene `#pragma pack(push,1)` y el struct está dentro) |
> | «este árbol lee direcciones imposibles» | **`REFUTED`**: leía el struct mal, no el árbol |
> | «este árbol no conduce mi placa» | **`REFUTED`**: la versión coincide (`7.1.3-200.nobara.fc44.x86_64`) y el árbol es correcto |
> | «la captura está truncada» | **`REFUTED`**: el option header declara 115×512 = 58880 y el fichero tiene eso |
> | «`base = 0x9C0A`» | **`PROVEN`**, y el BTF del módulo confirma los tres offsets que leí |
>
> **Causa**: mi generador de probes extraía el *cuerpo* del struct y lo compilaba
> fuera del `#pragma pack` que lo rodea. Un solo defecto produjo los cuatro
> síntomas: `usTableSize`@6, los offsets en 46/58/62, y `usClockStretchAmount`@26.
>
> El BTF del `amdgpu.ko` en marcha da `usTableSize`@**5**, offsets **45/57/61** y
> `usClockStretchAmount`@**25**. Los cinco valores que leí a mano del VBIOS
> coinciden con el módulo y **ninguno** con mi probe.
>
> Lo que sí sobrevive de este fichero: la cadena de `base = 0x9C0A` con sus cinco
> validaciones, y la medición del option header.


> ## Resultado
>
> Resuelvo H1 frente a H2 y **la base del `PowerPlayInfo` queda `PROVEN` por la
> cadena del propio driver, con cuatro validaciones independientes**. El VBIOS
> está empaquetado 1 byte más apretado que el struct C. **H1 confirmada.**
>
> Y al aplicarlo aparece algo que no puedo explicar desde el código: el driver,
> con este árbol, lee **direcciones imposibles**. Lo atribuí a que mi captura
> estaba truncada, **lo medí y era falso**: el ROM declara 115×512 = 58880 bytes
> y mi fichero tiene exactamente eso.
>
> Lo que queda es que **este árbol no es el que conduce mi placa**, y eso es
> `REFUTED` con evidencia, no con una inferencia.

## 1. La base, validada por cuatro puntos independientes

La cadena exacta, tal como la recorre el driver:

```
atom.c:1560   CU16(0)            vs ATOM_BIOS_MAGIC 0xAA55   -> 0xAA55     OK
atom.c:1573   base = CU16(ATOM_ROM_TABLE_PTR = 0x48)          -> 0x021C
atom.c:1575   strncmp(base + 4, "ATOM", 4)                    -> "ATOM"     OK
atom.c:1583   ctx->data_table = CU16(base + ATOM_ROM_DATA_PTR = 0x20) -> 0x97F2
atom.c:1646   offset = index*2 + 4      (index = 15, PowerPlayInfo)
atom.c:1647   idx = CU16(data_table + offset) @0x9814         -> 0x9C0A
```

Cuatro validaciones que **no dependen entre sí**:

| validación | resultado |
|---|---|
| `CU16(0)` == `ATOM_BIOS_MAGIC` (0xAA55) | OK |
| `"ATOM"` en `base+4` | OK |
| `ctx->data_table` == 0x97F2 | coincide con mi anotación |
| `mdt[15]` == 0x9C0A | coincide con mi anotación |
| `usStructureSize` @base+0 == **778** | 778 = 0x30A, el valor conocido del PowerPlayInfo Tonga/Fiji/Polaris |

**`base = 0x9C0A` es `PROVEN`.** Y las dos anclas que ya tenía (`0x97f2`,
`0x9C0A`) eran correctas. Eso **anula** mi barrido de bases de `608`: no
encontró una base alternativa, y `0x9C09` era solo la misma dirección descrita
distinto.

## 2. H1 confirmada: el VBIOS va 1 byte más apretado

El origen del desfase está localizado, y es en el primer campo tras la cabecera:

```
ATOM_COMMON_TABLE_HEADER (4 B):  usStructureSize@0, ucTableFormatRevision@2, ucTableContentRevision@3
ATOM_Tonga_POWERPLAYTABLE:       ucTableRevision@4  (UCHAR)
                                 usTableSize@6      (USHORT)  <-- 1 byte de relleno en @5
                                 ...y todos los siguientes, en pares
```

Y en el ROM:

```
+0   0A 03 07 01 00 4D 00 5D
     ^^^^^^^^^^^ ^  ^^^^
     identicos    @4 @5..6 = 4D 00 -> usTableSize = 77   EMPAQUETADO
                     @6..7 = 00 5D -> usTableSize = 23808  ALINEADO
```

**77 es plausible; 23808 = 0x5D00 es basura.** Los cuatro campos discutidos:

| campo | kernel alineado | yo leí empaquetado | valor empaquetado |
|---|---|---|---|
| `usTableSize` | @6 = 23808 | @5 | **77** |
| `usSclkDependencyTableOffset` | @46 = 30465 | @45 | **267** |
| `usPowerTuneTableOffset` | @58 = 2 | @57 | **673** |
| `usPCIETableOffset` | @62 = 2 | @61 | **752** |

**H1: el VBIOS empaqueta y el driver lee corrido todos los campos de la
cabecera.** Y solo hay **una** declaración de `ATOM_Tonga_POWERPLAYTABLE` en el
árbol (`pptable_v1_0.h:100`), así que el driver usa exactamente el struct que
medí con gcc. No hay struct alterno donde mirar.

## 3. Por qué esto predecía una tarjeta rota: y por qué la captura NO es la causa

Aplicando lo anterior, el driver leería:

```
usSclkDependencyTableOffset = 30465  ->  destino 0x1130B
usPowerTuneTableOffset      = 2      ->  destino 0x9C0C  (dentro de la cabecera)
usPCIETableOffset           = 2      ->  destino 0x9C0C
```

El primero está **fuera** del ROM, y los otros dos apuntan dentro de la propia
cabecera. Eso predecía un `vdd_dep_on_sclk` basura y un `PP_ASSERT` en
`process_pptables_v1_0.c:526`. Una tarjeta rota.

Y lo atribuí a que mi artefacto estaba truncado. **Era falso, y lo medí en los
minutos siguientes, dentro de esta misma iteración.**

```
option header de PCI, byte +2 = 0x73 = 115 bloques de 512
TAMAÑO DECLARADO = 115 * 512 = 58880 = 0xE600
TAMAÑO DE LA CAPTURA         = 58880 = 0xE600     COINCIDEN
```

**La captura está completa.** El ROM es de 58880 bytes de verdad: no es potencia
de dos, pero el option header lo declara así y el fichero coincide byte a byte
en longitud. Mi «no es potencia de dos, luego está truncado» fue una inferencia
sin medir, del mismo tipo que las que vengo corrigiendo en los demás.

## 3-bis. La contradicción vuelve, y es la buena

Con la captura completa, las tres lecturas del driver son **reales**:

```
usSclkDependencyTableOffset = 30465  ->  0x1130B   FUERA del ROM (0xE600)
usPowerTuneTableOffset      = 2      ->  0x9C0C    dentro de la cabecera
usPCIETableOffset           = 2      ->  0x9C0C    dentro de la cabecera
```

Y las cinco validaciones de la base siguen en pie, incluida `usStructureSize` =
778. El desfase de 1 byte sigue siendo real, y ahora **no hay salida por el
artefacto**.

La única resolución que queda es la del punto 4: **este árbol no es el que
conduce mi placa.** Y la evidencia de eso ya no es una inferencia mía sobre
tamaños de fichero: es que el árbol, aplicado a un ROM completo y validado por
cinco puntos, produce direcciones imposibles.

| afirmación | estado real |
|---|---|
| `base` del `PowerPlayInfo` = `0x9C0A` | **`PROVEN`**, cinco validaciones |
| el VBIOS va empaquetado, el struct no | **`PROVEN`** |
| la captura es el ROM entero | **`PROVEN`**, 58880 = 115×512 declarados |
| el driver, con este árbol, lee direcciones imposibles | **`PROVEN`** |
| el árbol que conduce mi placa es este | **`REFUTED`** |
| `usClockStretchAmount` = 26880 → `:2118` no corre | **`NOT_DETERMINED`**: es una lectura de este árbol, y este árbol no es el que corre |
| los 6 `TAPADA` de `502` | **`NOT_DETERMINED`**, igual que en `608` |

## 4. Lo que esto hace con `605`

`605` cerró `PROVEN` que la ruta legacy se registra para `CHIP_POLARIS12`. Ese
razonamiento **no dependía del VBIOS**: se apoyaba en que swsmu no tiene
generación smu7 y en que el `switch` de `amdgpu_discovery.c:2293` es exhaustivo.
**Eso sigue en pie.**

Lo que queda en pie es que la medición es sobre el código de
`RESEARCH/kernelbuild/linux-7.1.3/`. Y ahora hay una razón nueva y buena para
dudar de si ese árbol es el que corre:

**un árbol cuyo struct no coincide con el ROM de mi placa, en 1 byte, en cuatro
campos consecutivos, y de forma que el resultado sería una tarjeta sin power
management, es un árbol que probablemente no es el que está en marcha.**

No lo afirmo. Es `NOT_DETERMINED` y la vía para cerrarlo es de una sola medición:
**comparar el `amdgpu.ko` realmente cargado contra este árbol.** Si el struct
del módulo cargado tiene la cabecera sin el byte de relleno, mi árbol es
histórico y todas mis mediciones de struct sobre él sirven para entender el
código pero no para interpretar mi hardware.

## 5. Errores de esta iteración

**1. Leí `ATOM_ROM_TABLE_PTR` como `0x20` cuando es `0x48`**, porque mi `cut` de
100 caracteres recortó una línea de 143 y me equivoqué con el valor. Ya me había
pasado con `cut` en `605`, con `powerplay/Makefile`, y era la **tercera vez en
dos iteraciones**: no he incorporado la regla pese a haberla escrito.

**2. Conté mal `usMasterDataTableOffset`.** Lo puse en 28; el valor real es 32
(`ATOM_ROM_DATA_PTR = 0x20`). Lo detecté porque la comprobación cruzada
falló: `CU16(base+28) = 0x0240 ≠ 0x97F2`. La comprobación cruzada funcionó, y
eso salvó la conclusión.

**3. `atomctrl.c` no existe en `pm/atomctrl/`**, busqué por un path supuesto y
encontré la definición real en `amdgpu/atom.c:1642`. Esta vez **no** saqué una
ausencia del path errado: lo busqué por el símbolo.

**4. Verifiqué la firma `ATOM_BIOS_MAGIC` contra `0x55AA` en vez de `0xAA55`** y
declaré que el fichero estaba mal, cuando el fichero estava bien y mi
constante mal. Es **undécima** vez que un error mío produce un `PROVEN_ABSENT`
o un `PROVEN` falso.

## 6. Lo que me llevo

Tres cosas, y la tercera es la que más me cuesta:

**La cuarta validación (`usStructureSize` = 778) y la comprobación cruzada
(`data_table` leída por dos Producers) fueron lo que evitó que esto acabara en
una conclusión falsa.** Ninguna de las dos era necesaria: las tres primeras ya
decían lo mismo. Añadirlas costó poco y es lo que convirtió una lectura
«coherente» en una medición sólida.

**El truncamiento estaba ahí desde el principio y no lo miré.** Nunca verifiqué
que el artefacto tuviera el tamaño que dice ser. `SILENT_ZERO_IS_A_CLAIM`
tenía un hermano aquí: **un artefacto truncado produce ceros y casi-coherencias
que parecen datos.**

**Y el patrón de las últimas cuatro iteraciones es el mismo:** afirmo algo
«plausible y coherente» con un artefacto mío, y la coherencia me sirve de
prueba. Funcionó dos veces y por eso confié. **Un artefacto que produce un
resultado plausible no está validado por el hecho de ser plausible.**

## Frontier siguiente

**Comprobar si `RESEARCH/kernelbuild/linux-7.1.3/` es el árbol que conduce esta
máquina, y si no, cuál lo es.**

La medición del tamaño del ROM ya está hecha y salió **completo**; queda la otra
mitad, que es la que sostiene la conclusión.

ElTree esObservable: `modinfo amdgpu` da la `vermagic` del módulo cargado, y esa
`vermagic` dice contra qué kernel se compiló. Si no coincide con la versión del
`linux-7.1.3/` del corpus, **la premisa del corpus queda `REFUTED`** y con ella
todas las mediciones de struct que he hecho contra el VBIOS.

La comparación fuerte es una sola: **`sizeof` y `offsetof` del
`ATOM_Tonga_POWERPLAYTABLE` tal como queda en el módulo cargado**, contra las que
mide gcc en este árbol. Si difieren en el byte de relleno de `usTableSize`, está
cerrado y se sabe cuál es el layout bueno.

**Criterio de cierre: la `vermagic` del `amdgpu.ko` cargado, y si el struct de
`pptable_v1_0.h` del árbol coincide con el del módulo.**

Si coinciden, entonces la contradicción es real yDeepa: significaría que un
kernel de producción lee mal su propia cabecera de power play en mi placa, lo
que sería un hallazgo de primer orden y **no un error mío**. Si no coinciden,
este árbol es histórico, y el trabajo real empieza de nuevo contra el que corre.
