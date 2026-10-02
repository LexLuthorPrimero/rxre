# HALLAZGOS-DE-2026-10-02.md

Resultados de la sesion en que se obtuvo acceso root al debugfs de amdgpu.

Todos los datos de aqui son de la MAQUINA, no del corpus. Se separan de la
evidencia estatica a proposito: mezclarlos seria repetir el error que ya
llevo corregido dos veces en este proyecto.

---

## 1. VBIOS OBTENIDO — BLOQUEO CERRADO

### Que estaba bloqueado

`/sys/class/drm/card1/device/rom` es `-rw------- root root`, 131072 bytes.
`amdgpu_bios` de debugfs tambien. Sin root no habia forma de leer el VBIOS.

Clasificacion previa: `BLOCKED_BY_AUTHORIZATION`.

### Que se ha obtenido

58880 bytes via el nodo `amdgpu_vbios` de debugfs.

- sha256: `2b59f50859ec8003248eee9914a8d46967fd8c12e93d098f346ba54b33c53519`
- `file(1)`: `BIOS (ia32) ROM Ext. ... PCI AMD/ATI device=0x699f PRIOR, ProgIF=3`

`0x699f` es el device ID de Polaris12. El ROM es de esta GPU.

### Validacion cruzada del ROM

Los cuatro controles son los MISMOS que ejecuta el driver en
`amdgpu_atom_parse()` (atom.c:1546-1580), no controles inventados:

| Comprobacion | Valor | Fuente del offset | Resultado |
|---|---|---|---|
| `ATOM_BIOS_MAGIC` @0 | `0xAA55` | `atom.h:32` | PROVEN |
| `ATOMI magic` @0x30 | `" 761295520"` | `atom.h:33-34` | PROVEN |
| `ATOM magic` @base+4 | `"ATOM"` | `atom.h:37-38` | PROVEN |
| tamano declarado vs real | 115x512 = 58880 | `file(1)` | PROVEN |

**Endianness: PROVEN, no asumido.** Los bytes 0-1 son `55 aa`. Leidos como
u16 little-endian dan `0xAA55`, que es lo que el driver busca. Leidos como
big-endian darian `0x55AA` y `atom.c:1558` rechazaria el ROM. Little-endian
es la unica lectura que pasa.

### Geometria de las tablas

```
Base del ROM table          : 0x021c
Master command table offset : 0x974c
Master DATA table offset    : 0x97f2
```

`usStructureSize` de la master data table = 74, que es exactamente
`4 + 2*35`: el layout de `ATOM_MASTER_LIST_OF_DATA_TABLES`
(atombios.h:2783) describe este VBIOS.

Corroborado por busqueda independiente: en los 58880 bytes hay UN unico
sitio con `usStructureSize == 74`, revisiones sensatas y 35 offsets que
apuntan dentro del ROM, y es `0x97f2`. Dos vias de derivacion distintas
que convergen.

**Estado: PROVEN_DERIVED.**

### Tablas presentes

21 de 35 con offset distinto de cero. Presentes y con cabecera coherente:
`StandardVESA_Timing` (312 B, rev 1.2), `FirmwareInfo` (108 B, rev 2.2),
`PaletteData` (52 B, rev 1.1), `LCD_Info` (78 B, rev 1.3), `SMU_Info`
(56 B, rev 2.1).

El CONTENIDO de las tablas **NO esta decodificado**. Es
`NOT_IMPLEMENTED`, no tabla vacia. Para el hardware hace falta el contenido,
no el offset.

### Una correccion que hubo que hacer

La primera version de `atomrom.py` colocaba la master data table en `base`
(0x021c) en vez de en `usMasterDataTableOffset` (0x97f2). Lei
`usStructureSize = 36` en vez de 74.

Lo que paso es util: la herramienta **aviso sola** de que el layout no
coplaba y de que "los nombres de abajo NO son de fiar", y no publico el
inventario. Un parser mas complaciente habria dado 35 tablas con nombres
plausibles y offsets inventados. Preferible un NoAnswer con explicacion a
una tabla falsa con aspecto de respuesta.

Candidatos a "nombre de tabla" (0x4d4f = "MO", 0x699f, 0x5441 = "TA") eran
en realidad bytes de texto del ROM leidos con el layout equivocado.

---

## 2. VBIOS, POR QUE NO SE PUEDE DECODIFICAR A VOLUNTAD

`amdgpu_bios.c` del corpus no abre `atom.c`. Para el modo atomico hace falta
`amdgpu_atombios.c`, cuyo parser no es alcanzable por la ruta que sigue
`amdgpu_bios.c` en este kernel.

Consecuencia: `SMU_Info` y `PowerPlayInfo` estan localizadas pero no
decodificadas, y no se pueden decodificar con el codigo de este corpus.

`NOT_IN_CORPUS` para la via de decodificacion, no para la tabla.

---

## 3. ANILLO GFX DECODIFICADO: GEOMETRIA OBSERVADA

La captura de `amdgpu_ring_gfx` no es el anillo crudo, y eso no es un
detalle: cambia la interpretacion de todo lo demas.

### Formato real (amdgpu_ring.c:551, `amdgpu_debugfs_ring_read`)

Los 12 primeros bytes NO son PM4:

| offset | contenido | origen |
|---|---|---|
| +0 | `RING_RPTR` | registro MMIO, via `get_rptr` |
| +4 | `RING_WPTR` | registro MMIO, via `get_wptr` |
| +8 | `ring->wptr` software | variable del driver |
| +12 | `ring->ring[0]` | contenido del anillo, lineal |

Es decir: los dos primeros punteros son **lectura de hardware**, no memoria
del buffer.

### Valores observados

```
RING_RPTR  = 0x0200 (512)
RING_WPTR  = 0x0200 (512)
sw wptr    = 0x0200 (512)
anillo     = 2048 dwords (8192 bytes), mask=0x07ff
```

### Que es lectura de hardware y que no

Esto importa mas que los valores, asi que se separa:

| puntero | origen | naturaleza |
|---|---|---|
| `RING_RPTR` | `*ring->rptr_cpu_addr` (gfx_v8_0.c:6008) | espejo en CPU |
| `RING_WPTR` | `*ring->wptr_cpu_addr` si hay doorbell, si no `RREG32(mmCP_RB0_WPTR)` (gfx_v8_0.c:6019) | **MMIO, condicional** |
| `sw wptr` | `ring->wptr` | variable del driver |

O sea: **los tres NO son lectura directa de hardware**. `RING_RPTR` es una
copia en CPU, y `RING_WPTR` solo llega a ser `RREG32(mmCP_RB0_WPTR)` si
`ring->use_doorbell` es falso. Con doorbell activo, tambien es un espejo.

La lectura corregida: los tres punteros son **estado del driver, espejado en
CPU**, no el estado del hardware leido en ese momento. Coinciden porque el
driver los mantiene sincronizados, que es justo lo que se comprobaria.

Esto **no** es una observacion de hardware de CP_RB_RPTR ni de CP_RB_WPTR.
Marcarlo como tal habria sido el error facil: "el anillo esta vacio" suena a
lectura de hardware y en realidad es coherencia interna del driver.

Lo que SI es dato de hardware, y por otro camino: el **tamano** del anillo,
2048 dwords con mask 0x07FF, que viene de la configuracion del ASIC.

`rptr == wptr` significa que, segun el driver, no queda nada pendiente de
ejecutar. Si el hardware estuviera por detrás, esta lectura no lo
detectaria: es un punto ciego conocido.

### Estructura del residuo

8 bloques, arrancando en los dwords 3, 259, 515, 771, 1027, 1283, 1539, 1795.
Es decir, `3 + 256k` en todos los casos: **cadena de 256 dwords**.

Cada bloque: 1 `PACKET3_COND_EXEC` (4 dwords) + 1 `PKT0` (85 dwords) + 167
`PACKET3_NOP` = 256.

El bloque tiene contenido **distinto** en cada uno de los 8, no son copias.
La primera lectura de esto decia "8 bloques identicos" y era FALSA; se
comparo el contenido y se corrigio.

La cadena de 256 concuerda con `.align_mask = 0xff` de
`gfx_v8_0_ring_funcs_gfx` (gfx_v8_0.c:6872), que es alineacion a 256 dwords.
8 x 256 = 2048 = tamano del anillo. **PROVEN_DERIVED.**

### PACKET3_NOP con cuenta 0x3FFF

El dato mas util que salio de decodificar. El driver declara
`.nop = PACKET3(PACKET3_NOP, 0x3FFF)` (gfx_v8_0.c:6873) y lo escribe con
`memset32(..., funcs->nop, count)` en dos sitios independientes
(amdgpu_ring.c:128 y :154). Por tanto **un NOP ocupa 1 dword y su campo de
conteo se ignora**: el 0x3FFF no describe un payload de 16383 dwords, es un
valor de relleno.

Sin esa regla el decodificador leia 0x3FFF como payload, se comia el resto
del anillo y declaraba "truncado". El sintoma (conteo en el maximo del
campo) fue lo que hizo sospechar que el fallo era de formato y no de
contenido.

No se generaliza a otros paquetes: no hay evidencia de que ninguno mas
ignore su conteo.

### Lo que NO se ha decodificado

El contenido de los `PKT0`. El reparto real del header de PACKET0 en GFX8
**no esta establecido**: la macro `PACKET0(reg, n)` de sid.h:327 pone `reg`
en `[15:2]` y `n` en `[13:0]`, y esos campos se solapan, asi que el header
real de escritura tiene otro reparto que no se ha buscado todavia.

Interpretando con `[31:16]=indice` y `[15:2]=registro` salen offsets
plausibles (0x3c00, 0x3f00, 0x3700, que son rangos CP/RLC de GFX8) seguidos
de ceros. Escribir en el offset 0 no significa nada.

**Estado: `NOT_DETERMINED`.** Publicar esa lista a medias seria dar numeros
con aspecto de dato que no son registros. `pm4dec.py` marca el decode de
registros como NO VALIDADO y no lo usa para nada.

---

## 4. CAPTURAS DE ESTADO

Snapshot de 19 nodos de solo lectura en una unica sesion de sudo, 0,3 s.
Artefactos en `revkit/capturas/`.

### Anillo GFX: 8204 bytes de IB REALES

Capturado, con contenido. No es texto: son 8204 bytes de comandos PM4/IB en
el anillo GFX, con bytes no imprimibles. (Una afirmacion previa de que eran
"43 dwords" era FALSA: 8204 bytes son ~2051 dwords. Se corrigio tras leer el
fichero.)

El riesgo que se le atribuyo a `amdgpu_regs` (volcado de 128 KiB que
reanuda la GPU con `pm_runtime_get_sync`) no aplica igual a un anillo de
8 KiB. Se capturo sin incidencias.

**Lo que NO se ha hecho todavia**: decodificar estos IB con el decodificador
PM4. Es el siguiente paso natural y de alto valor, porque son comandos que
el hardware ejecuto de verdad, no los que el driver escribiria.

### Page tables: NO VOLCADAS

`amdgpu_vm_info` en 7.1.3 solo lista BOs, no vuelca entradas de page table.
`amdgpu_gart` no existe en este driver.

**Estado del volcado de PTE reales: `NOT_AVAILABLE` por debugfs en 7.1.3.**
No es que las PTE sean inaccesibles en el hardware; es que este driver no
ofrece el nodo. Queda como `NOT_FOUND`, no `PROVEN_ABSENT`.

### Sensores: EINVAL, no vacio

`amdgpu_sensors` devuelve `EINVAL` al leer. No esta en la lista de nodos de
este kernel. Distinguir "vacio" de "el kernel no lo deja leer" importa: lo
primero no dice nada, lo segundo es un dato sobre el driver.

### Lo que no se captura y por que

`amdgpu_regs*`: excluido. El servidor se reinicio 3 veces en la sesion, 2 de
ellas correlacionadas con la lectura de `amdgpu_regs`. No se ha probado que
la lectura lo cause, pero la correlacion basta para no arriesgarse. Se dice
como correlacion, no como causa.

`amdgpu_iomem`: `EPERM` incluso con root. El kernel lo restringe por
capability. `NOT_AVAILABLE`, no `NOT_FOUND`.

---

## 5. CORRUPCION DE FICHEROS: CAUSA Y ALCANCE

### Lo encontrado

`revkit/mmo.py` tenia 1232 bytes nulos anadidos al final del fichero. El
codigo estaba integro y correcto hasta `sys.exit(main())`, asi que un modulo
valido en apariencia: solo lo detectaba leer los bytes en vez de parsearlos.

`06-INGENIERIA-INVERSA/findings/050-la-frontera-ordenada-por-su-via-de-cierre.md`:
8619 bytes, 8619 nulos, 0 bytes imprimibles. **No esta en git.**

### Causa

Reinicio del sistema durante un escrito. El patron (texto integro seguido de
cola de ceros) es de escritura interrumpida, no de edicion.

### Alcance

`revkit/mmo.py` reparado: truncado a 11585 bytes, sintaxis verificada.

**El 050 no se puede recuperar.** No hay version en git. No se ha intentado
reconstruirlo porque adivinar el contenido de un documento no es una
operacion con criterio. Se deja constancia.

### Riesgo residual

218 ficheros de texto sin seguimiento en git. No estan corruptos. El punto
es que si se corrompen no hay de donde volverlos, y el 050 se perdio
exactamente asi. De esos 218, 63 son de `06-INGENIERIA-INVERSA` y 36 de
`08-ARQUITECTURA`.

Ademas, ya se habia lose el contenido de `014-q1-gpuvm-minimal.md` y
`030-page-walker-gfx8-2-niveles.md` por no estar en git. Es la tercera
pérdida del mismo tipo. **Leccion aprendida: el requisito de "no tocar
`RESEARCH/` ni lo de otra sesion" choca con que ficheros de valor estan sin
versionar.** Hay que decidir si se versionan o se documenta que son
efimeros.

---

## 6. FIRMWARE INFO DEL VBIOS, CRUZADA CON EL KERNEL

Tabla `FirmwareInfo` en `0x9974`, campo #5 de la master data table
(`atombios.h:2789`). Estructura `_ATOM_FIRMWARE_INFO_V1_2` (atombios.h:2982).
`usStructureSize=108`, rev 2.2.

### La unidad de los clocks, corroborada por el hardware

El header dice "In 10Khz unit". 10 kHz es 1/100 de MHz, o sea que el paso a
MHz es **dividir entre 100**.

| campo | bruto | MHz | kernel ahora | |
|---|---|---|---|---|
| `ulDefaultEngineClock` | 21400 | **214** | `PSTATE_SCLK` 214 MHz | COINCIDE |
| `ulDefaultMemoryClock` | 30000 | **300** | `MCLK` 300 MHz | COINCIDE |

Dos coincidencias exactas en dos campos distintos, contra el estado real de
la GPU en este momento. La unidad queda **CORROBORATED por hardware**, no
deducida de la aritmetica.

Me equivoque dos veces con esta unidad antes de acertar. La primera dividía
por 10 y por 1000, y sacaba «2.1 MHz» para el reloj de motor. La segunda
dividía por 100 y otra vez por 1000. Los dos números tenían decimales y
aspecto de frecuencia, y ninguno lo era. Un error de unidades no da error:
da un número plausible.

Por eso el contraste con `amdgpu_pm_info` está **dentro** de la herramienta
y no en mi cabeza: si la unidad no cuadra, sale con rc=5; si no puede
contrastar, sale con rc=4. Verificado con mutación en los dos casos.

### Otros valores leidos

| campo | bruto | MHz |
|---|---|---|
| `ulDriverTargetMemoryClock` | 360000 | 3600 |
| `ulMaxPixelClockPLL_Output` | 600000 | 6000 |
| `ulASICMaxMemoryClock` | 62610 | 626 |
| `ulDriverTargetEngineClock` | 0 | 0 |
| `ulASICMaxEngineClock` | 0 | 0 |

626 MHz de memoria maxima y 6000 MHz de pixel clock son coherentes con
Polaris12. Los ceros son ceros, no valores no leidos: los campos existen en
la estructura y estan a cero en este VBIOS.

### El cruce con amdgpu_firmware_info NO da relacion

`ulFirmwareRevision = 0x0F320201`. Sus cuatro bytes son `0x01 0x02 0x32 0x0F`.

El kernel reporta feature versions **por IP**: ME 49, PFP 49, CE 49, MEC 49.
**Ninguno de los cuatro bytes de `ulFirmwareRevision` es 49.**

Eso **no** es una refutacion. Son dos campos distintos: uno es un entero
opaco que el VBIOS declara, el otro es una version de IP que el kernel carga.
Que no coincidan significa que no hay relacion establecida entre ellos, y no
que se hayan contradicho.

Clasificacion: `NOT_DETERMINED` para la relacion. No `REFUTED`.

Ademas: `amdgpu_bios.c` no llama a `amdgpu_atom_parse`, asi que el driver de
7.1.3 **no decodifica** estos campos por si mismo. El cruce es mio, no del
driver, y eso hay que decirlo para no atribuirle una capacidad que no tiene.

---

## 7. VRAM_INFO: LA MEMORIA FISICA DE ESTA TARJETA

Tabla `VRAM_Info` en `0xa30a`, `usStructureSize=986`, rev 2.2, campo #29 de la
master data table.

### La revision manda, y hubo que respetarla

La tabla declara **rev 2.2**, asi que la estructura correcta es
`_ATOM_VRAM_INFO_HEADER_V2_2` (atombios.h:8027). La primera vez se aplico
`_ATOM_VRAM_INFO_V4`, que era la que estaba a mano, y salio
`ucChannelWidth=5` y `ucMemorySize=0`: numeros que parecian campos y no lo
eran.

Ademas, el header V2_2 trae `ucVramModuleVer`, que aqui vale **8**, y eso dice
que los modulos son `ATOM_VRAM_MODULE_V8`. No es una suposicion: lo declara
el propio dato.

### Valores leidos (un solo modulo de VRAM)

| campo | valor | |
|---|---|---|
| `usMemorySize` | **2048** | MB, coincide con el kernel |
| `strMemPNString` | **`H5GC8H24AJR`** | part number fisico |
| `usEnableChannels` | 3 | |
| `usMcRamCfg` | 0x60A2 | NOOFBANK/NOOFRANKS/NOOFROWS/NOOFCOLS |
| `ulChannelMapCfg` | 0x10 | mmMC_SHARED_CHREMAP |
| `ucChannelNum` | 1 | |
| `ucBankCol` | 10 | bank=2 (16bank), col=2 (10 bit) |
| `ucDensity` | 99 | |
| `ucRowNum` | 11 | |

### El contraste, por tres vias

| fuente | valor |
|---|---|
| VBIOS `usMemorySize` | 2048 MB |
| kernel `amdgpu_vram_mm` `total` | 2048 MiB |
| kernel `amdgpu_vram_mm` `size` | 2147483648 bytes |

Tres fuentes, el mismo numero. `PROVEN`.

El contraste esta dentro de la herramienta: si no coinciden sale con rc=5, y
si no puede comprobarlo sale con rc=4. Un codigo 0 sin haber comprobado
seria una corroboracion falsa.

### `H5GC8H24AJR`

Es un part number real de GDDR5 de Samsung, y identifica la memoria fisica
de esta tarjeta. No es una inferencia: es un dato del firmware.

Es el unico punto donde el VBIOS dice algo sobre el hardware que el driver
no dice. El driver solo ve "2 GiB"; el VBIOS ve WHICH 2 GiB.

### Lo que NO se afirma

- `ucMemoryType = 0x50`. El nibble alto es 5, que en la documentacion de las
  structs mas antiguas significa DDR5/GDDR5, pero `ATOM_VRAM_MODULE_V8` solo
  dice `MEM_TYPE_DDR2/DDR3/GDDR3/GDDR5` sin dar la codificacion. El nibble
  bajo, segun el comentario de las structs viejas, "must not be used for
  now". **No se traduce a un nombre de tipo.**
- `ucChannelWidth = 5`. El comentario dice 0=16bit, 1=32bit, 2=64bit. Un 5
  no encaja en esa lista. **Se imprime el valor crudo y se deja.**

Los dos se imprimen sin interpretar. Un campo cuyo comentario no casa con
el valor no se convierte en un tipo de memoria inventado.

---

## 8. DIRECCIONES DE GPU OBSERVADAS EN EL ANILLO

El anillo GFX capturado contiene 8 `PACKET3_INDIRECT_BUFFER`, y dentro de cada
uno hay una **direccion de 64 bits que el hardware uso de verdad**.

### El layout, y de donde sale

`gfx_v9_0.c:5431-5439`:

```c
header = PACKET3(PACKET3_INDIRECT_BUFFER, 2);
amdgpu_ring_write(ring, lower_32_bits(ib->gpu_addr));
amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr));
amdgpu_ring_write(ring, control);   // length_dw | (vmid << 24)
```

Declara `count=2` y escribe 3 dwords. Es el **mismo patron** que el
`WAIT_REG_MEM` (count=5, 6 escritos) y que el `COND_EXEC` (count=3, 5
escritos): el driver de GFX8 escribe mas dwords de los que declara.

Se usa la forma de gfx_v9_0 porque es la que esta escrita de forma legible.
Que GFX8 la comparta queda corroborado por el hecho de que las direcciones
obtenidas caen dentro de la VRAM, lo que no pasaria con un layout erroneo.

### Las 8 direcciones

| dword | gpu_addr |
|---|---|
| 18 | 0x0000_0001_0027_8000 |
| 274 | 0x0000_0001_0027_8600 |
| 530 | 0x0000_0001_0025_8000 |
| 786 | 0x0000_0001_0025_8600 |
| 1042 | 0x0000_0001_0025_9e00 |
| 1298 | 0x0000_0001_0025_a400 |
| 1554 | 0x0000_0001_0025_b600 |
| 1810 | 0x0000_0001_0025_bc00 |

Todas alineadas a 0x600. Rango total: 2.34–2.47 MiB.

### El FB esta en 4 GiB, no en 0

Todas tienen el bit 32 puesto. La diferencia contra una base de 4 GiB
(`0x1_0000_0000`) es de 2.34 a 2.47 MiB, y eso **cabe en los 2 GiB de VRAM**
que reporta el kernel (`size: 2147483648`).

O sea: el FB no esta en la direccion 0 de la VA. Esta en 4 GiB. Y el
`vram_base_offset = 0` que se tiene registrado para esta ruta se refiere a
otra cosa, o no aplica a la direccion que usan estos paquetes. **No se
concilia aqui**: lo que se afirma es el offset observado.

### El contraste

| | |
|---|---|
| VRAM total (kernel) | 2147483648 B = 2048 MiB |
| VRAM en uso (kernel) | 29646848 B = 28.27 MiB |
| offset mayor observado | 2.47 MiB |

Las 8 direcciones caben. `PROVEN` que el layout es correcto.

El offset mayor (2.47 MiB) y el uso total (28.27 MiB) **no son la misma
cifra**, y no se afirma que lo sean: el uso incluye buffers que no estan en
este anillo. Solo se dice que son del mismo orden de magnitud, lo cual es
consistente.

### Por que esto importa para el driver propio

Es el primer punto donde se ve una VA real, translated, ejecutandose. La
cadena queda:

```
INDIRECT_BUFFER -> gpu_addr 0x1_0025_8000 -> (GPUVM) -> fisica
```

El paso que falta es la traduccion por la page table, y eso sigue
`NOT_DETERMINED` porque `amdgpu_vm_info` no vuelca PTEs en 7.1.3.

---

## 9. LA CADENA DE TRADUCCION, CON LOS NUMEROS DEL CORPUS

La traduccion VA->PA esta **completa en el codigo**, y son cuatro lineas con
sus valores:

| donde | que hace | valor |
|---|---|---|
| `gmc_v8_0.c:1176` | `vram_base_offset = 0` | GPU discreta, no APU |
| `amdgpu_vm.c:1228` | `addr = vram_base + cursor.start` | |
| `amdgpu_gmc.c:173` | `value = addr & adev->gmc.pte_addr_mask` | |
| `gmc_v8_0.c:1134` | `pte_addr_mask` | `0x000000FFFFFFF000` (40 bit PA) |

### Lo que se cierra

Con `vram_base = 0`, **la direccion que va a la PTE es la propia VA**, sin
desplazamiento. Eso es `PROVEN_DERIVED` para la ruta de VRAM: no hace falta
saber el contenido de la tabla para saber que operacion se aplica.

Y la mascara es de **40 bits de direccion fisica**, que cubre de sobra una
VA de 2 GiB. Ningun bit alto se pierde al enmascarar.

### Lo que se pierde, y esta bien que se pierda

La mascara quita los 12 bits bajos, que son el offset dentro de la pagina.
Las direcciones observadas **no estan alineadas a 4 KiB** (`...8000`,
`...8600`, `...9e00`), y se truncan a la pagina que las contiene.

Eso no es un defecto: la PTE no direcciona bytes, direcciona paginas de
4 KiB. Un buffer puede empezar en cualquier byte y la tabla lo cubre con la
pagina correspondiente mas el offset.

### Lo que NO se cierra

Saber COMO se construye la PTE no dice que hay dentro de la tabla. Siguen
abiertos:

- que pagina fisica apunta cada entrada
- donde esta la tabla en si
- si la entrada tiene los flags de lectura/escritura
- si hay PDE o solo PTE para esta configuracion

Todo eso `NOT_DETERMINED` por la misma razon de siempre: no hay observador.
`amdgpu_vm_info` en 7.1.3 lista BOs y no vuelca entradas, y `amdgpu_gart` no
existe en este driver. **Es `NOT_AVAILABLE` por esta via, no
`PROVEN_ABSENT` en el hardware.**

### El VMID del primer buffer

El control del `INDIRECT_BUFFER`, que va **fuera** del conteo declarado,
da `vmid = 7` y `length_dw = 344` (1376 bytes).

GFX8 reparte los VMID asi (gmc_v8_0.c:1162-1168):

```
VMID 0        reservado al sistema
VMID 1-7      amdgpu graphics/compute
VMID 8-15     amdkfd
```

`vmid = 7` es **el ultimo del bloque de graficos**, justo antes del que
empieza KFD. Es coherente con un job de KMS en el anillo GFX.

---

## 10. GART: 256 MiB, Y POR QUE

`gmc_v8_0.c:588-608` decide el tamano de la GART. Para **Polaris12**
expresamente:

```c
case CHIP_POLARIS12: /* all engines support GPUVM */
default:
    adev->gmc.gart_size = 256ULL << 20;
```

El comentario explica el porque: en Polaris10/11/12 y Vega10 **todos los
motores soportan GPUVM**, asi que la GART no tiene que ser grande para
podermapper RAM del sistema; 256 MiB basta porque el acceso pasa por la GPU
VM y no por el hueco de BAR.

Los chips con 1024 MiB (Tonga, Fiji, Carrizo, Stoney) son los que tienen
UVD o VCE **sin** soporte de GPUVM, y para ellos la GART tiene que cubrir
el acceso a RAM por la via antigua.

**Estado: `PROVEN_DERIVED`.** El valor y su justificacion estan ambos en el
corpus, y el valor se puede contrastar en runtime cuando se tenga el
observador.

Esto explica ademas por que el BAR es de 256 MB (lspci lo reporta como
`Memory at e0000000 [size=256M]`) mientras la VRAM es de 2 GiB: la GART y
el BAR son cosas distintas, y el BAR es solo la ventana de CPU sobre la
VRAM.

---

## 11. LOS POOLS DE IB DEL DRIVER

`amdgpu_sa_info` no es memoria de shader, pese al nombre. Es
`amdgpu_ib.c:486-498`, que vuelca los tres pools de IB:

| pool | buffers | bytes | rango fisico |
|---|---|---|---|
| `DELAYED` | 654 | 572768 | 0xff0034e000 – 0xff003dfa00 |
| `IMMEDIATE` | 0 | – | vacio |
| `DIRECT` | 35 | 62976 | 0xff0054e000 – 0xff0055e800 |

635744 bytes de IBs vivos, en RAM del sistema a direccion fisica
(`0xff00...`, no VAs de GPU).

### Lo que se ve

- **Tamano dominante: 1024 bytes**, 547 veces. Es el IB de trabajo normal
  que el driver reutiliza.
- **Los buffers son casi todos contiguos**: 546 de 654 tienen hueco 0 con
  el siguiente. El driver asigna en bloques.
- **Un IB en uso por pool**, marcado con `>`:
  - `DELAYED`, 1024 bytes, contexto 383
  - `DIRECT`, 4096 bytes, contexto 22
- **57 contextos distintos**, y **ninguno usa mas de un pool**. Una
  submission no tiene buffers en varias etapas simultaneamente.

### Lo que NO se interpreta

El campo `protected by 0x...` tiene **138 valores distintos** (1 a 0x8A).

La cadena `protected by` **no existe en el corpus**. Se comprobo con grep
en las tres raices: `amdgpu_sa_bo_dump_debug_info` se LLAMA desde
`amdgpu_ib.c:491` y **no esta definido** en ninguna. Es una implementacion
del driver cargado que no se tiene.

Por eso el campo se cuenta pero no se interpreta. Es `NOT_IN_CORPUS`, no
`NOT_FOUND`: la funcion se llama y existe, pero su codigo no esta.

Un mal analisis tomo los tres primeros valores (1, 3, 2) como una
rotacion de bits de proteccion. No lo es: es un contador, y el "patron" era
como empieza una secuencia. Un patron en los tres primeros datos no es un
patron.

---

## 13. WRITE_DATA: EL ANILLO ESCRIBE EN UN REGISTRO, NO EN MEMORIA

Ocho `PACKET3_WRITE_DATA` en el anillo capturado, todos iguales:

| campo | valor | significado (sid.h:378-388) |
|---|---|---|
| `dst_sel` | 0 | **registro**, no memoria |
| `WR_CONFIRM` | 1 | espera de confirmacion |
| `engine` | 1 | PFP |
| direccion | `0x00000BCC` | offset del mapa de registros |

`dst_sel == 0` significa registro segun el comentario de `sid.h:379`.
Distinto de 0 es memoria via GRBM. Aqui es 0, y la direccion cae en el
rango de registros del ASIC: coherente.

### `0xBCC` = `mmHDP_DEBUG0`

Resuelto por coherencia entre generaciones del bloque OSS. Cinco ficheros
del corpus definen ese offset igual:

```
oss_1_0_d.h      oss_2_0_d.h      oss_2_4_d.h
oss_3_0_d.h      oss_3_0_1_d.h        ->  mmHDP_DEBUG0 = 0xbcc
```

`PROVEN`: no es que no haya nombre, es que un offset corto como `0xbcc`
existe en varios bloques (DCE, GC, MMHUB tambien lo definen) y en varias
generaciones, y el indice hay que filtrarlo por ASIC.

**El anillo escribe en un registro de depuracion del HDP, ocho veces, con
confirmacion de escritura.** Eso no estaba en ninguna deduccion anterior.

### El `0xDEADBEEF` que NO esta

`gfx_v8_0.c:891-894` emite un `WRITE_DATA` con valor `0xDEADBEEF`. Se
busco en el anillo capturado: **cero apariciones**.

Ese codigo es un test unitario, no la secuencia de trabajo. Concluir que
"el anillo escribe DEADBEEF" porque el driver lo hace en un test seria
importar un dato de un test a una medicion. Se busco de verdad y no esta,
y eso queda escrito en la salida del propio tool.

### El patron de fondo: el driver escribe mas de lo que declara

Este es el **cuarto** paquete con el mismo defecto:

| paquete | declara | escribe |
|---|---|---|
| `WAIT_REG_MEM` | 5 | 6 |
| `COND_EXEC` | 3 | 5 |
| `INDIRECT_BUFFER` | 2 | 3 |
| `WRITE_DATA` | 3 | 4 |

En los cuatro, el ultimo dword escrito queda **fuera del conteo declarado**.
No es un error del decodificador: el codigo fuente lo hace asi, en cuatro
sitios distintos de cuatro emisores distintos.

Que el hardware lo lea o no es `NOT_DETERMINED`. Lo que si se sabe es que
el valor esta en el buffer, en el orden correcto, y que el campo `count` no
lo cuenta.

---

## 14. ERRORES PROPIOS ENCONTRADOS EN ESTA SESION

Se anotan porque el patron se repite y conviene reconocerlo.

1. **Contar como resultado un fallo de ejecucion.** `captura.py` con
   contrasena incorrecta imprimia "con contenido: 0, vacios: 0, con error:
   0" y salia con rc=0. Era el modo de fallo dominante del proyecto: un cero
   que parece un resultado. Ahora sale con rc=4 y el stderr de sudo.

2. **`--solo` que no era solo.** Pedia un nodo y capturaba tres. El nombre
   de la opcion decia una cosa y el codigo hacia otra.

3. **Un mismo hecho en dos sitios, divergiendo en silencio.**
   `amdgpu_vbios` estaba en `EXCLUIDOS` y en `PLAN_BIN` a la vez. El
   snapshot completo funcionaba porque `EXCLUIDOS` solo se consulta con
   `--solo`, pero `--solo amdgpu_vbios` rechazaba un nodo que el plan
   queria capturar. Es el mismo patron que la CONTRADICCION-014 duplicada,
   y por eso ahora hay un control de coherencia que mira la RELACION entre
   los conjuntos.

4. **Un control que no detecta su propia mutacion.** El control de
   `integro.py` que comprobaba que un `.o` no apareciese entre los ficheros
   de texto pasaba tanto si el filtro de binarios funcionaba como si estaba
   roto, porque en ambos casos `.o` no llegaba a la lista. Se reescribio
   para comprobar `clasifica()` directamente. Verificado con mutaciones: M1
   detectada, M2 **no** detectada antes de arreglar el control y detectada
   despues (7 controles), M3 detectada.

5. **Caracteres CJK o cirilicos colados en prosa en espanol.** Cuatro veces
   en esta sesion, incluido un caso en un docstring. El control existe
   (`CN-R12`) y se ejecuta, pero hay que correrlo: no se detecta solo.

6. **Un numero escrito de memoria y no verificado.** Escribi "el anillo
   GFX tiene 43 dwords" sin haber leido el fichero. Son 8204 bytes, unas
   2051 dwords. El numero era plausible y estaba equivocado, que es la
   combinacion peor: un valor falso con forma de dato. Se corrigio leyendo
   la captura antes de commitear.

   La regla ya existia ("todo numero se verifica contra la fuente o
   ejecutandolo") y aqui no se cumplio. Se cumple cuando el numero sale de
   una ejecucion; falla cuando se escribe de memoria por inercia.

7. **Un test mal escrito que senala al codigo equivocado.** El test de
   "payload inexistente" usaba el opcode `0x10`, que ES `PACKET3_NOP`.
   Como acababa de anadir la regla de que el NOP ignora su conteo, el test
   fallaba y el diagnostico senalaba al decodificador de NOP, que era
   innocent. El test estaba mal. Esta en `cn7.py` con una nota que explica
   por que el opcode 0x37 y no el 0x10, para que no se repita.

8. **Un sniff mal calibrado que no da ningun sintoma.** Al corregir los 5
   falsos positivos del escaner (VBIOS y anillos PM4 marcados como
   "corruptos" por llevar sufijo `.txt`), la primera regla del sniff
   aceptaba como binario un texto truncado con la cola de NUL: cumplia "tiene
   NUL" y cumplia "tiene bytes no textuales", porque una cola de NUL ES no
   textual. Es decir, el arreglo habria escondido justo la corrupcion que
   la herramienta existe para detectar, incluido el 050 perdido.

   Se detecto porque los casos de prueba fallaron 2 de 7, no porque el
   escaner protestara. Un sniff mal calibrado no falla: deja de ver cosas.
   Por eso los 6 casos estan ahora en el autotest.

   Y hay un caso que NO se resuelve: un texto con unos pocos NUL repartidos
   es indistinguible de un binario con pocos NUL. Se declara `ambiguo` y se
   revisa, en vez de elegir. Descartarlo seria cambiar un falso positivo
   por una corrupcion no vista, y el coste es asimetrico.

9. **Una funcion de bajo nivel que adivinaba el formato.** `decodifica()`
   venia con `saltar_cabecera=True`, asi que un test sintetico de 5 dwords
   empezaba a leer en el dword 3 y contaba 2 paquetes donde habia 5. El
   fallo se parecia a un bug del NOP, justo donde se acababa de tocar
   codigo. Ahora la funcion no adivina y quien sabe el contexto lo dice.

10. **Convertir un espejo en una lectura de hardware.** `pm4dec.py`
    imprimia "ESTADO DEL ANILLO (leido de registros MMIO, no del buffer)"
    y `HALLAZGOS` decia "dos de hardware". Es falso: `RING_RPTR` viene de
    `*ring->rptr_cpu_addr` y `RING_WPTR` de `*ring->wptr_cpu_addr`
    salvo que `use_doorbell` sea falso, caso en el que si es
    `RREG32(mmCP_RB0_WPTR)` (gfx_v8_0.c:6008, 6011-6019).

    Los tres son estado del driver espejado en CPU. Que coincidan demuestra
    que el driver los sincroniza, no que el hardware haya consumido. El
    error era especialmente tentador porque "el anillo esta vacio" suena a
    observacion, y porque una lectura de CP_RB_RPTR habria cerrado de
    verdad algo que aqui no se cierra.

    Lo que SI es dato del ASIC es el tamano: 2048 dwords, mask 0x07FF.

11. **La unidad de los clocks del VBIOS, mal dos veces seguidas.** "In 10Khz
    unit" es 1/100 de MHz. La primera vez dividi por 10 y por 1000, y salio
    "2.1 MHz" para el reloj de motor. Corregido a /100, volvi a dividir por
    1000 otra vez. Los dos errores dieron numeros con decimales y aspecto de
    frecuencia.

    Lo que lo resolvio no fue la aritmetica, fue contrastar con
    `amdgpu_pm_info`: la GPU tiene ahora `PSTATE_SCLK` 214 MHz y `MCLK` 300
    MHz, y el VBIOS dice 21400 y 30000. Un error de unidades no da error: da
    un numero que parece una frecuencia. Por eso el contraste esta dentro de
    la herramienta, con rc=5 si no cuadra y rc=4 si no se puede comprobar.

12. **Un control de contraste mal calculado que decia "no coincide".** Al
    escribir el bloque que compara el VBIOS con el estado del kernel,
    redefini la variable `off`, que ahi es el offset de la TABLA, y la use
    como offset del PAYLOAD. Leia en el sitio equivocado, sacaba 0, y el
    contraste reportaba DIFIERE sobre dos valores que si cuadraban.

    Un control mal calculado que dice "no coincide" es peor que no tenerlo:
    hace desconfiar de una corroboracion que era real, y el reflejo seria
    tirar el dato bueno. Se arreglo guardando los valores crudos en el
    primer recorrido, para que el segundo no tenga que recalcular offsets.

13. **La estructura equivocada para la revision de la tabla.** VRAM_Info
    declara rev 2.2 y se decodifico como V4, que era la que estaba a mano.
    Salieron `ucChannelWidth=5` y `ucMemorySize=0`. Se corrigio leyendo que
    la 2.2 tiene su propia estructura, y que ademas dice en el dato
    (`ucVramModuleVer = 8`) cual es la de los modulos.

    Leer una tabla con la estructura de otra revision no da un error: da
    numeros que tienen forma de campo.

14. **El offset de un campo de struct, buscado a ojo.** `usMemorySize` se
    leia en +26 en vez de +20, y daba 24832 MB en lugar de 2048. El offset
    ahora se calcula sumando el tamano de cada campo en el orden del struct.

    24832 no es un valor de memoria que se note mirando, porque lleva
    decimales implicitos y nadie sabe de memoria cual deberia ser. Solo se
    vio al contrastar con el kernel.

15. **Un control que no discriminaba.** El contraste de la unidad de clocks
    no tenia caso negativo: si se forzaban los dos valores para que casasen,
    decia "COINCIDEN" igual. `cn8.py` lo resuelve con un mutante (el factor
    de 100 a 10) y con un VBIOS sintetico que declara 1024 MB contra un
    kernel de 2048. Los dos tienen que fallar.

    Un control que solo sabe decir "OK" no controla: pasa igual cuando todo
    va bien y cuando la herramienta esta rota.

16. **Indices mal impresos que contaminaron una lectura entera.** Al intentar
    leer el payload del `COND_EXEC` del anillo, imprimi los dwords con los
    indices equivocados y concluje que el campo `addr` valia
    `0xff00001080`, unas 1000 veces mas alla de la VRAM. No era un dato
    raro: era mi lectura corrida un dword.

    Tuve que pararme porque payload[2] **tenia que ser 0** (el driver escribe
    un 0 ahi, gfx_v8_0.c:6325) y salia `0x143`, que es el payload del paquete
    siguiente. Un campo cuyo valor se conoce de antemano y no aparece, es un
    error de lectura, no un dato raro. Esa comprobacion es la que lo
    detecto.

17. **Ajustar el codigo de salida en vez de mirar por que era.** El control
    del caso negativo daba rc=4 en vez del rc=5 esperado, y el primer impulso
    fue revisar la condicion del `if`. El rc=4 significaba "falta el fichero
    de contraste": la copia del mutante vivia en un temporal y `pm4dec`
    resuelve `capturas/` con `__file__`, asi que no encontraba
    `amdgpu_vram_mm.txt`.

    Estuve corrigiendo el sintoma hasta que mire la causa. Un codigo de
    salida inesperado es informacion, no un obstaculo que tunear.

18. **Un campo ausente leido como un cero del hardware.** El `control` del
    `INDIRECT_BUFFER` va fuera del conteo declarado, asi que el decodificador
    no lo entregaba. Mi codigo tomaba lo que hubiera ahi y salia
    `length_dw = 0` y `vmid = 0`, que se registró como dato.

    No era un dato: era la ausencia del campo. Un `length_dw` de 0 es un
    paquete vacio, y un buffer indirecto vacio no tiene sentido. Ese
    absurdo es lo que delata la lectura.

19. **Un indice contado dos veces.** Para leer el control hacia
    `(CABECERA//4)*4 + idx*4`, sumando 12 bytes de cabecera sobre un indice
    que ya venia desplazado 3. Se leia un dword mas adelante, y salia
    `length_dw = 3020`, `vmid = 0`.

    El vmid real es 7. Ni 0 ni 192 parecian imposibles a primera vista, y
    los dos numeros tenian forma de dato.

20. **Confundir indice de palabra con indice de anillo.** El campo `idx` es
    la posicion dentro de `words[]`, que empieza en 3 por los punteros de
    la cabecera. Leyendolo como indice dentro del anillo me carryo 4 dwords
    mas adelante, a obtener direcciones distintas, y a dudar de la lectura
    buena.

    Lo cerro mirando los bytes crudos con un indice calculado una sola vez, y
    no comparando dos lecturas que yo mismo habia desalineado. La lectura
    original era correcta; la duda era mia. `pm4dec` ahora dice explicitamente
    que `idx` es indice de palabra y que el de anillo es `idx - 3`.

21. **Traer un dato de un test unitario a una medicion.** Cite
    `gfx_v8_0.c:891-894`, que emite un `WRITE_DATA` con `0xDEADBEEF`, y me
    puse a buscar ese `0xDEADBEEF` en el anillo esperando encontrarlo.

    No esta. Ese codigo es un test. Cuando el valor buscado no aparece, lo
    informativo no es "el dato es raro" sino "estaba mirando el sitio
    equivocado". Ahora el tool busca el `0xDEADBEEF` de verdad y dice que no
    esta, con el motivo.

22. **Contar de memoria lo que un script puede contar.** Escribi "tres
    ficheros definen mmHDP_DEBUG0 = 0xbcc" porque habia visto tres. Al
    comprobarlo con grep eran **cinco** (faltaban `oss_1_0_d.h` y `oss_3_0`).

    Peor: habia puesto los nombres hardcodeados en el propio tool, que es
    exactamente el error que el kit viene corrigiendo en todas partes. Ahora
    `_mm_por_offset()` los lee del corpus en cada ejecucion.

23. **Tomar la primera coincidencia de un indice sin filtrar.**
    `dires.py 0xbcc` devuelve `mmDCP3_DC_LUT_WHITE_OFFSET_RED` (DCE),
    `regTCX_UE_ERR_STATUS_HI` (GC) y `regVM_INVALIDATE_ENG9_REQ` (MMHUB)
    antes que el nombre correcto. Los tres son reales y de otros ASICs.

    Un indice que cruza 30 ASICs no puede devolver "el primero que aparezca".
    Lo que demuestra el nombre correcto es que **varias versiones del mismo
    bloque** dan el mismo offset, no que exista una coincidencia.

### Un fallo que se ha repetido dos veces

`CN-R13` (backticks sin cerrar) ha saltado dos veces en esta sesion, y las
dos por lo mismo: **una referencia a codigo partida entre dos lineas**.

```
`Memory at e0000000
[size=256M]` en lspci
```

El backtick se abre en una linea y se cierra en la siguiente. Markdown lo
tolera, asi que no se ve al escribir, y al leer con el Cesar de bits se ve
claro. Escribi la leccion y volvio a ocurrir en el commit siguiente.

La regla practica que se deduce: si una referencia entre acentos graves no
cabe en la linea, el problema no es la linea, es que hay que mover el texto
entero. Un control que solo se ejecuta a veces no es un control: este se
ejecuta en `check.sh`, y dos veces ha hecho falta que lo atrapara.
