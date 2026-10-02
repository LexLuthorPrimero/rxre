# 202 · Los registros de la placa caben en BAR5 con 4× de holgura, y `ix` no es un offset

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=usa el BAR5 de 200 como limite duro`
`RETRACTADO_POR=203` -- la seccion "BIF es casi todo indexado" queda
RETRACTADA: 3188 defines `ix` no es 90% de acceso, es 90% de **vocabulario**.
Medido: de 7288 `ix` definidos, el driver referencia **127 (1.7%)**. BIF define 3188 y
usa 21. Un driver propio **no** necesita el camino indexado para hablar con BIF ni
SMU: esa obligacion queda retirada.

## Cuestión principal

`200` estableció que el driver mapea **BAR5, 256 KiB**. Eso da un límite **duro y
verificable**: si algún registro que el driver usa estuviera por encima de
`0x40000`, ese acceso sería inalcanzable con el mapeo que hace.

Es una comprobación con resultado binario y con adversario real: si el límite
fuera falso, habría un fallo. No es un inventario, es una prueba.

## Criterio de terminación

Medir el offset máximo real de MMIO de cada bloque de esta placa y compararlo con
la apertura. **Cumplido: las 12 cabeceras caben, con 197066 bytes de holgura.**

## Herramienta

`08-ARQUITECTURA/tools/aperture.py`. Extrae los `#define` con valor hexadecimal
literal de las cabeceras que **el `.c` incluye de verdad**, separa los registros
de índice indirecto, y compara el máximo con la apertura.

Que se cuente por el include del `.c` y no por el nombre del bloque es lo mismo que
en `192`: **VCE 3.4 incluye `vce_3_0_d.h`, y UVD 6.3 incluye `uvd_6_0_d.h`**.
Buscar por el nombre del bloque daría "ausente".

## El resultado

```
apertura real mapeada por el driver: BAR5 = 0x40000 (262144 bytes)

bloque       cabecera                    define indirectos  maxMMIO  cabe
gfx_v8_0     gca/gfx_8_0_d.h             2800   (167 ix) 0x00FB56  si
gmc_v8_2     gmc/gmc_8_2_d.h              882     (0 ix) 0x00F9B0  si
gmc_v8_1     gmc/gmc_8_1_d.h             1680   (524 ix) 0x00F9CD  si
uvd_v6_0     uvd/uvd_6_0_d.h              106     (9 ix) 0x003DF1  si
vce_v3_0     vce/vce_3_0_d.h               45     (0 ix) 0x0085BD  si
oss_3_0      oss/oss_3_0_d.h              660   (115 ix) 0x00FE35  si
oss_2_0      oss/oss_2_0_d.h              614    (99 ix) 0x0037AA  si
bif_5_0      bif/bif_5_0_d.h             1043   (568 ix) 0x006200  si
bif_5_1      bif/bif_5_1_d.h             3549  (3188 ix) 0x00153F  si
smu_7_1_3    smu/smu_7_1_3_d.h           1224  (1091 ix) 0x003297  si
smu_7_1_2    smu/smu_7_1_2_d.h           1250  (1121 ix) 0x0001B6  si
dce_10_0     dce/dce_10_0_d.h            7330   (406 ix) 0x005FFF  si

cabeceras ausentes: 0 de 12
cabeceras con registros por encima de la apertura: 0
```

**El máximo global es `0x00FE35` = 65077 bytes**, en `oss_3_0_d.h`.

```
apertura BAR5      = 0x040000 (262144 bytes)
maximo MMIO global = 0x00FE35 (65077 bytes)
holgura            = 197066 bytes
```

**La apertura es 4× más grande de lo que esta placa necesita.** Es coherente: el
tamaño del BAR lo fija el firmware, no la placa, y un tamaño mayor es
inofensivo.

**Y ningún registro de la placa queda fuera del mapa.** `PROVEN`.

## El dato estructural que sale: BIF es casi todo indexado

`bif_5_1_d.h` tiene **3188 defines `ix` de 3549: el 90%**. Y `smu_7_1_3_d.h`, 1091
de 1224, el **89%**. Frente a `vce_v3_0_d.h` y `gmc_v8_2_d.h`, con **cero**.

No es un detalle: el acceso a BIF y a SMU es mayoritariamente **indexado**, no
directo. Un driver propio que solo sepa hacer `*(volatile u32 *)(base + offset)`
**no puede hablar con BIF ni con SMU**.

## `ix` no es un offset: por qué el chequeo falló primero

Mi primera versión de la herramienta clasificaba por **máscara de nibble alto**
(`v & 0xF0000000`) yezingúno la salida: **4 de 12 cabeceras "no cabían"**, con
valores de hasta `0xE00030B8`. Casi acepté eso como un hallazgo.

No lo era. La máscara falla **por partida doble**:

- **Deja colar no-offsets.** `ixPB1_TX_LANE15_CTRL_REG0 = 0x02209A00` tiene el
  nibble alto a cero, así que lo contaba como offset de 34 MiB.
- **El patrón no es el nibble, es el prefijo.** El 100% de los defines con nibble
  alto lleva `ix` (61/61, 55/55, 351/351, 266/266), **pero hay `ix` con nibble
  alto cero**.

Los `ix` son **índices de acceso indirecto**:

```
ixPCIEP_RESERVED            0x10010000
ixGCK_MCLK_FUSES           0xC0500008
ixD3F5_PCIE_MC_OVERLAY_BAR1 0x0B0000C7
ixCG_DCLK_CNTL              0xC050009C
```

**No son direcciones MMIO**, se acceden por otra vía. El clasificador correcto es
el prefijo `ix`, que es la convención de AMD y no una aproximación mía por el
nombre.

**Y no me fié de la convención**: el self-test comprueba que **no quede ningún
define sin `ix` por encima de 32 MiB** en tres cabeceras reales. Si el filtro
fallara, saldría. Los tres vectores del clasificador están tomados del header real,
y uno de ellos es precisamente el caso (`ixPB1_TX_LANE15_CTRL_REG0`) que hizo fallar
a la máscara.

## La lección: una alarma que no investigas se convierte en un hallazgo falso

Un `rc=3` con cuatro "fallos" es exactamente el tipo de resultado que da gusto
reportar: suena a bug de hardware, es concreto, y no cuesta nada.

Si lo hubiera escrito tal cual, `202` sería **un hallazgo falso con cuatro
supuestos defectos de direccionamiento**, y habría contaminado §A justo cuando
acaba de quedar cerrada con `200`.

**El ahorro de trabajo de no mirar el WHY es exactamente el coste de mirar el
por qué.** El WHY fue ver dos defines de ejemplo y ver que se llamaban `ix`. Cuatro
minutos.

Es la misma forma que `192`/`144`: *buscar por el nombre del símbolo en vez de por
el mecanismo*. Aquí el "nombre" era el prefijo, y aun así el primer criterio que
elegí —la máscara de bits— parecía más mecanico y era peor.

## Corroboración independiente — y por qué es más débil de lo que parece

Otra sesión publicó `202-la-ventana-de-registros-es-bar5-y-el-log-lo-dice.md`, que
**llegó a la misma conclusión que mi `200` por su cuenta**: la ventana de
registros es BAR5, no BAR2, y el log del kernel lo dice. Colisionamos en el número
porque los dos estábamos persiguiendo la discrepancia que `190` dejó abierta.

**Eso parece una corroboración fuerte, y no lo es.** Su cita es
`amdgpu_device.c:3995-3997`, y en este corpus:

```
$ sed -n '3995p' amdgpu_device.c
			/* Initialize clocks */
```

**Su cita no resuelve.** El bloque real está en `3812-3818`, bajo el comentario
`/* Registers mapping */`:

```
$ sed -n '3812p' amdgpu_device.c
	if (adev->asic_type >= CHIP_BONAIRE) {
$ sed -n '3995p' amdgpu_device.c
			/* Initialize clocks */
```

Y hay **tres** ocurrencias de `asic_type >= CHIP_BONAIRE` (1182, 1259, 3812), así
que un número de línea aislado no identifica el mecanismo ni aunque casara.

Comprobé que no fuera un árbol distinto: `RESEARCH/working` y `RESEARCH/baseline`
son **idénticos** (mismo md5 en `amdgpu_device.c`). No es que leyeran otra copia.

**La lección, y es la generalización de la de arriba.** Dos hallazgos que coinciden
en la **conclusión** no son dos hallazgos que coincidan en la **evidencia**. Si su
cita no resuelve, no se sabe que verificaran el mismo código: podrían haber llegado
a BAR5 por un camino distinto —quizá equivocado— que casó con la respuesta buena.
**La coincidencia de la respuesta no valida el razonamiento que produjo.**

Eso es más fuerte que lo de "una afirmación plausible sin valor al lado", porque
aquí el valor competitor **existe** y aun así no se comprobó. La corroboración
parecía gratis porque alguien había llegado antes a lo mismo. **Llegar antes es
justo el caso en el que hay que mirar la cita, porque es donde cuela la falsa
corroboración.**

## Un error que casi cometo, y que NO es una corrección a `192`

Mientras construía esta herramienta busqué las cabeceras de registro con
`ls *_d.h` **en el directorio del driver**, y saliÓ 0.;Iba a escribir que "las
cabeceras de registro de esta placa no están en el corpus".

**Están**, en `drivers/gpu/drm/amd/include/asic_reg/` — 122 ficheros, y las 12 que
usa esta placa existen con miles de defines:

```
uvd/uvd_6_0_d.h   106 defines
vce/vce_3_0_d.h    45 defines
```

**No lo escribí porque comprobé antes de afirmar**, y al comprobar salió que
`192` **no dice eso**. `192` afirma que falta el **código** de display (`dc/` vacío
en el snapshot), que es distinto y cierto. **Si lo hubiera escrito, habría
sido una corrección a un hallazgo que no dice eso: inventar una contradicción con
`192` para dar crédito a `202`.**

Es la forma más sutil de la clase "afirmación plausible sin valor competitor
al lado": no hace falta que el valor esté delante para que se cuele. **Basta con
que el hallazgo anterior sea vagamente temático.** `192` habla de UVD y VCE; yo
iba a "corregirlo" sobre UVD y VCE. La temática compartida bastaba para que la
corrección pareciera inevitable.

Y el sitio donde el error era fácil: `192` **sí** afirma algo cercano y verdadero
(`dc/` vacío), así que la afirmación falsa se apoyaba en algo real.

## El hueco que declaré, resuelto: los registros de SDMA 3.1 sí estaban medidos

Este hallazgo declaró un hueco: *"`SDMA 3.1` no tiene cabecera de registros y su
`.c` no incluye ninguna. Queda fuera de la medición."* **Es falso.**

Dos errores encadenados, y los dos míos.

**Error 1 — leí el nombre del fichero, no el mecanismo.** `asic_reg/sdma/` solo
tiene `4_4_0` y `4_4_2`, y **no existen `sdma_v3_1.c` ni `sdma_v3_1.h`**.
Concluí que faltaban. Pero mirando dónde se declara el bloque:

```
sdma_v3_0.c:1693  const struct amdgpu_ip_block_version sdma_v3_1_ip_block =
                  { ... .funcs = &sdma_v3_0_ip_funcs, };
```

**`sdma_v3_1_ip_block` está declarado dentro de `sdma_v3_0.c`**, con la tabla de
funciones del v3_0. **Tercer caso del mismo patrón** (UVD 6.3→v6_0,
VCE 3.4→v3_0, ahora SDMA 3.1→v3_0). Y `sdma_v3_0.c` **sí** incluye cuatro
cabeceras de registro: `oss_3_0_d.h`, `gmc_8_1_d.h`, `gfx_8_0_d.h`,
`bif_5_0_d.h`.

**Error 2 — patrón de grep equivocado, que encendió el error 1.** Busqué
`RREG_SDMA`/`WREG_SDMA` y salió **cero**, así que concluí que el fichero no tocaba
registros. SDMA usa los accesores genéricos **`RREG32`/`WREG32`**, no `RREG_`: hay
**62** usos. **Un cero por patrón equivocado es un cero que no significa nada.**

Y el registro que toca da la clave:

```c
tmp = RREG32(mmSRBM_SOFT_RESET);
WREG32(mmSRBM_SOFT_RESET, tmp);
```

`mmSRBM_SOFT_RESET = 0x398`, y está en **`oss/oss_3_0_d.h`**, no en un header de
SDMA. Ahí están los **85** defines `mmSDMA_*` / `mmSRBM_*` de esta placa:

```
mmSDMA_CONFIG          0xf91
mmSDMA_POWER_GATING    0x3416
mmSDMA_PGFSM_CONFIG    0x3417
mmSDMA_PGFSM_READ      0x3419    <- el mas alto
```

**Los registros de SDMA 3.1 en GCN8 están definidos en el header OSS.** Por eso
`asic_reg/sdma/` solo tiene 4.4.x: el directorio dedicado `sdma/` aparece en
generaciones posteriores, cuando el espacio creció y necesitó fichero propio.

**El hueco no existe.** SDMA 3.1 **ya estaba medido**, por `oss_3_0_d.h`, que
además es la cabecera que fija el **máximo global** de toda la medición
(`0x00FE35`). **El bloque que yo creí excluido era el que marcaba el límite.**

**La lección, la misma de `192` por cuarta vez.** Declaré un hueco porque una
búsqueda por **nombre** salió vacía. La capacidad estaba ahí, con otro nombre, en
otro fichero, con otro prefijo. **Un grep vacío no es evidencia de ausencia: es
evidencia de que no sé cómo se llama.**

Y lo peor: lo declaré en un hallazgo cuyo tema es precisamente **medir la
superficie completa**. Dejarse un hueco sin mirar, en la medición que lo pide, es
contradecirse a uno mismo en la misma página.

## Clasificación

| afirmación | estado |
|---|---|
| Las 12 cabeceras caben en 0x40000 | `PROVEN` — `aperture --todos`, rc=0 |
| Máximo MMIO global `0x00FE35` = 65077 | `PROVEN` |
| Holgura de 197066 bytes (4× de más) | `PROVEN_DERIVED` |
| `ix` = registro de índice indirecto, no offset | `PROVEN` — convención + control |
| BIF es 90% indexado, VCE y GMC8.2 son 0% | `PROVEN` |
| Ningún define sin `ix` pasa de 32 MiB | `PROVEN` — control del self-test |
| `uvd_6_0_d.h` y `vce_3_0_d.h` están en `asic_reg/`, con 106 y 45 defines | `PROVEN` |
| Que la apertura deba ser mayor por necesidad | `REFUTADO` — sobra 4× |
| Que un driver propio necesite el camino indexado | `DERIVATION` — de las proporciones |
| SDMA 3.1 usa los registros de `oss_3_0_d.h` (85 defines `mmSDMA_*`) | `PROVEN` — `sdma_v3_0.c` usa `RREG32(mmSRBM_*)` |
| Que no haya registros usados por el driver fuera de sus cabeceras | `NOT_DETERMINED` |

## Confounders

- **Se cuentan las cabeceras, no los accesos.** Un registro definido en una
  cabecera incluida por el `.c` no está necesariamente *usado* por él. La prueba es
  Necessary (si algo no cabe, no cabe), **no suficiente** (que todo lo definido quepa
  no prueba que todo lo usado quepa). Lo digo porque es la asimetría que hace que
  esto sea un test con adversario y no un inventario.
- ~~**`SDMA 3.1` no tiene cabecera.** `asic_reg/sdma/` solo tiene `4_4_0` y
  `4_4_2`, y `sdma_v3_1.c` **no incluye ninguna cabecera de registro**.~~
  **FALSO, y era el hueco que este hallazgo declaraba. Resuelto en la sección
  "El hueco que declaré, resuelto", abajo: los registros de SDMA 3.1 sí estaban
  medidos.**
- **DM/DC tampoco está medido.** `dce_10_0_d.h` está, pero el bloque registrado es
  `dm` (DC), y sus cabeceras son otra cosa. `dce_10_0` es el DCE legacy, que esta
  placa no usa.
- **El total de `define` y `ix` no cuadra con `grep -c "^#define"`** (2800 vs 2801
  en `gfx_8_0_d.h`). La diferencia es un define que no casa con el regex, casi
  seguro con un valor entre paréntesis complexes. **No lo he identificado**, y es
  una fuga pequeña pero real: un registro que no se cuenta no se verifica.
- **No he medido nada en runtime.** Es 100% estático contra cabeceras.

## Desfalsificación

- **(a)** Las 12 caben → refutable con `aperture --todos`. **Verificado, rc=0.**
- **(b)** El máximo `0x00FE35` → refutable grepeando `oss_3_0_d.h`.
- **(c)** `ix` es índice → refutable con los cuatro defines citados.
- **(d)** El filtro no deja pasar no-offsets → refutable con el control del self-test.
- **(e)** El regex pierde un define → **refutable, y probablemente cierto**. No
  resuelto.
- **(f)** El "hueco" de SDMA 3.1 → **refutado por mí mismo**: era falso.

## UNLOCKS

- **§A queda con un límite verificado**: los registros de esta placa ocupan como
  mucho 65077 bytes de los 262144 mapeados. **Ningún acceso de MMIO queda fuera.**
- **Un hecho de arquitectura**: BIF y SMU son ~90% de acceso indexado. Un driver
  propio con solo acceso directo no puede hablar con ellos. Es un requisito de
  diseño, no un detalle.
- **La aceptación de 256 KiB queda justificada por el lado del hardware**, no solo
  por el log: el contenido real de los registros ocupa el 25% de la apertura.
- **SDMA 3.1 no era un hueco**: sus registros viven en `oss_3_0_d.h`, que ya
  estaba medido y que fija el máximo global de la medición.
- **La corrección que casi escribo y no escribí**: afirmar que `192` se equivocaba
  de dónde vivían las cabeceras. `192` no dice eso. Es un ejemplo de que la
  temática compartida basta para que una corrección falsa parezca inevitable.
- **Un hueco real**: **SDMA 3.1 no tiene cabecera de registros en el corpus** y su
  `.c` no incluye ninguna. Queda fuera de la medición y sin resolver.
- **La lección**: un `rc=3` con cuatro fallos es el resultado que más da ganas de
  reportar y el más probable que sea falso. **El WHY es donde está el trabajo.**

## Evidencia

```
08-ARQUITECTURA/tools/aperture.py --todos --cabecera H --self-test
self-test: 2 vectores de apertura, 4 de extraccion, 1 ancla, 3 del
           clasificador, 3 controles

amdgpu_device.c:3812-3818   la rama BAR5 (hallazgo 200)
gfx_v8_0.c     -> gca/gfx_8_0_d.h, gmc/gmc_8_2_d.h, oss_3_0_d.h, bif_5_0_d.h
gfx_v8_0.c:41  -> incluye gmc_8_2_d.h (y gmc_v8_0.c:35 el 8_1)
uvd_v6_0.c     -> uvd/uvd_6_0_d.h, oss_2_0_d.h, smu_7_1_3_d.h, bif_5_1_d.h
vce_v3_0.c     -> vce/vce_3_0_d.h, oss_3_0_d.h, gca/gfx_8_0_d.h, smu_7_1_2_d.h
sdma_v3_1.c    -> NINGUNA cabecera de registro   <-- hueco
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.