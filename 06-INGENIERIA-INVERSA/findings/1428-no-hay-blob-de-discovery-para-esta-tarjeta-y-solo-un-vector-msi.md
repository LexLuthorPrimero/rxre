# 1428 — con lectura privilegiada: no hay blob de discovery para esta tarjeta, el cuadro de configuración tiene 16 capacidades, y esta GPU tiene **un solo vector MSI**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+CIERRE-DE-HUECO+RESTRICCION-DE-DISENO
TRACK=RUNTIME(solo lectura) · unica intervencion: NINGUNA escritura al dispositivo
GENERADO=2026-10-04
AFECTADO=08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md   (limitaciones de config space)
         04-IMPLEMENTACION/rx550-driver/target_resource.h:44-56   (BARs: CORROBORADO)
         bloque IH / plan de interrupciones del driver propio        (restriccion nueva)
         08-ARQUITECTURA/CONSTANTES-GFX8-DRIVER.md:242-249  (atomics de PCIe: ahora medidos)
ORIGEN=el hallazgo 1418 dejo como hueco mayor "el artefacto decisivo es
       arcturus_ip_discovery.bin y no esta en el corpus".  Con lectura privilegiada se
       puede contestar si ese artefacto existe PARA ESTA TARJETA.
ESTADO=PROBADO · no hay blob de discovery para Polaris12: PROVEN_ABSENT · 16 capacidades
       PCI medidas · MSI Count=1/1 y SIN MSI-X: una sola linea de interrupcion
       · 4 capacidades de virtualizacion de GPU presentes (ATS/PRI/PASID/AWE)
       · el ROM sigue sin poder leerse, y la razon esta medida
```

## 0. Qué se hizo y qué NO se hizo

```text
SÍ    lectura de /lib/firmware/amdgpu/            (listado)
SÍ    lspci -s 01:00.0 -vv                       (lectura de config space)
SÍ    setpci -s 00:01.0 04.W                     (lectura del command register)
NO    ninguna escritura al dispositivo.  ni un registro MMIO, ni un bit de config space,
      ni un module load, ni un resume de la GPU
```

La password se usó únicamente como argumento de `sudo -S`. **No aparece en ningún fichero
del repositorio ni en ningún mensaje de commit**, y no se escribirá en ninguno.

## 1. EL CIERRE: no hay tabla de offsets alternativa para esta tarjeta

El hallazgo 1418 (y el inventario de Arcturus) trataban `amdgpu/arcturus_ip_discovery.bin`
como "el artefacto decisivo que no está en el corpus". Con lectura de disco:

```text
$ ls /lib/firmware/amdgpu/ | wc -l
677

$ ls /lib/firmware/amdgpu/ | grep ip_discovery | sed 's/_ip_discovery.*//'
aldebaran  arcturus  picasso  raven2  raven  vega10  vega12  vega20

$ ls /lib/firmware/amdgpu/polaris12_ip_discovery.bin.xz
ls: no se puede acceder a ...: No existe el fichero o el directorio
```

**Ocho ASICs tienen blob de discovery. Polaris12 no está entre ellos.** Y los 20 ficheros
`polaris12_*` que sí existen son todos **imágenes de firmware**, no tablas de offsets:

```text
polaris12_32_mc  polaris12_k_mc  polaris12_mc  polaris12_smc  polaris12_rlc
polaris12_sdma  polaris12_sdma1  polaris12_me  polaris12_me_2  polaris12_mec
polaris12_mec2  polaris12_ce  polaris12_ce_2  polaris12_pfp  polaris12_uvd
polaris12_vce   polaris12_k_smc  polaris12_mec_2  polaris12_mec2_2
```

(ocho familias: MC, SMC, RLC, SDMA, ME, MEC, CE, PFP, UVD, VCE — el SQ/RLC que la GPU
carga para ejecutar, no direcciones de registros.)

**Y esto encaja con el log, medido en 1418:** `journalctl -k -b | grep -c discovery` = 0.
No es que el blob falte en el firmware dir: **es que para esta ASIC no existe, y el camino
de bloques legacy ni siquiera lo intenta.**

> **Consecuencia, y es la que importa para el driver:** las bases de registro de esta GPU
> **sólo pueden venir de las tablas fijas del código fuente.** No hay blob, no hay
> cabecera firmada, no hay segunda fuente. La tabla del `.c` no es "un respaldo
> degradado": **es la única autoridad posible**, y es estática, y se puede leer entera.

Eso convierte en resoluble por análisis estático lo que era el mayor hueco abierto.

## 2. POR QUÉ el ROM no se pudo leer (medido, no supuesto)

El Volcado de los 128 KiB falla, y **los dos errores son distintos según el privilege**:

```text
sin root :  cat: .../rom : Permiso denegado            (EACCES, modo 0600)
con root :  cat: .../rom : Argumento inválido          (EINVAL)
dd bs=65536 count=2 : el mismo EINVAL, salida 0 bytes
```

Dos errores distintos significan dos causas distintas. Con root, el permiso ya no es el
problema. La causa es el command register del PCI:

```text
$ setpci -s 00:01.0 04.W
0407

bit  0 IO Space = 1        bit  1 Memory Space = 1
bit  2 Bus Master = 1      bit 10 INTERRUPT DISABLE = 1
bit 14 ROM ENABLE = 0                       <-- aqui esta
```

Y lspci lo confirma por otra vía:

```text
Expansion ROM at 000c0000 [disabled] [size=128K]
```

**El decodificador del ROM BAR (bit 14) está apagado**, y por eso la lectura devuelve
`EINVAL` y no bytes. Es también **por qué parte de lo que el hallazgo 1053 declaró
`NO_VERIFICABLE` no lo era**: el fichero es `0600`, pero **aun con root hace falta activar
el bit**. Son dos bloqueos distintos, y antes sólo se había medido el primero.

**No lo he activado.** Es una escritura de config space a un dispositivo de display vivo,
aunque sea un solo bit y reversible. No está justificada por el resultado: el contenido
que se busca es el firmware PSP/SPI, y §1 acaba de demostrar que **la tabla de offsets
que necesitamos no está ahí**. Se declara como la vía restante, con su coste, y no se usa.

## 3. El cuadro de configuración tiene 16 capacidades, no 4

El proyecto tenía registrado que el config space era ilegible ("access denied" sin sudo, y
la ventana de sysfs truncada a 64 bytes con el puntero de capacidades en 0x48, fuera del
rango). Con root, la cadena completa se recorre:

```text
[48] Vendor Specific Information     [50] Power Management v3
[58] Express (v2) Legacy Endpoint    [a0] MSI
[100] Vendor Specific ID=0001        [150] Advanced Error Reporting
[200] Physical Resizable BAR         [270] Secondary PCI Express
[2b0] Address Translation Service    [2c0] Page Request Interface
[2d0] Process Address Space ID       [320] Latency Tolerance Reporting
[328] Alternative Routing-ID Interp. [370] L1 PM Substates
```

**La truncación a 64 bytes era un artefacto de permisos, no una propiedad del
hardware.** Eso quita una limitación registrada como tal.

### 3.1 Barra de direcciones: CORROBORADO contra lo que el proyecto tenía

```text
Region 0: Memory at e0000000  64-bit prefetchable    256M     <- el grande
Region 2: Memory at f0000000  64-bit prefetchable    2M       <- apertura de doorbell
Region 4: I/O ports at e000                           256
Region 5: Memory at f7d00000  32-bit non-prefetchable 256K    <- el de registros
Expansion ROM at 000c0000 [disabled]                   128K
```

Coincide campo por campo con `04-IMPLEMENTACION/rx550-driver/target_resource.h:44-56`, que
ya lo tenía como `MEDIDO_EN_LA_PIEZA`. **Pasa a `CORROBORADO`** con una segunda vía
independiente, y confirma que BAR5 es la ventana de registros (coherente con
`register mmio base: 0xF7D00000  size: 262144` del log).

## 4. LA RESTRICCIÓN NUEVA: UN SOLO VECTOR DE INTERRUPCIÓN

```text
Capabilities: [a0] MSI: Enable+ Count=1/1 Maskable- 64bit+
Interrupts: pin B disabled, MSI(X) routed to IRQ 37
```

**No hay MSI-X.** Y el MSI tiene `Count=1/1`: **un vector, ni uno más.**

Esto es una restricción de diseño dura, y no es una inferencia:

- La tarjeta **no tiene MSI-X**. No hay tabla de vectores, ni `TableSize`, ni nada que
  repartir. La ruta `routing` de amdgpu para GPU con MSI-X **no aplica aquí**.
- Hay **exactamente un vector MSI**, ya habilitado, con capacidad de 64 bits, **no
  enmascarable** (`Maskable-`).
- `pin B disabled`: el INTx legacy está apagado, como corresponde cuando se usa MSI.
  Coherente con el bit 10 = Interrupt Disable del command register medido arriba.

> **Para el driver propio: toda la GPU habla por una única línea de interrupción.** GFX,
> SDMA0, SDMA1, UVD, VCE y GFXOFF compartirán ese vector, y el bloque IH tendrá que
> **desmultiplexar por identificador de fuente en software**, no por vector. Cualquier
> diseño que asuma un vector por motor es incorrecto en esta tarjeta.

Esto también **explica por qué la ruta de carga del finding 1400 (fence por IRQ) es la
única posible**: no hay alternativa a MSI, y MSI no es por cola.

**Caveat honesto**: `Count=1/1` es lo que *reporta* la capacidad MSI del PCI config space.
Que el hardware IH tenga más fuentes de interrupción es otra cosa, y no se afirma aquí. Lo
medido es el número de vectores que la tarjeta ofrece al host.

## 5. Cuatro capacidades de virtualización de GPU presentes

No estaban registradas, y son directamente relevantes para la ruta VMID/GART:

| capacidad | offset | qué es |
|---|---|---|
| **AWE** (AtomicOps) | dentro de `DevCap2` | `AtomicOpsCap: 32bit+ 64bit+`, `AtomicOpsCtl: ReqEn+` → **PCI atomics ACTIVADAS** |
| **ATS** | 0x2b0 | Address Translation Service |
| **PRI** | 0x2c0 | Page Request Interface |
| **PASID** | 0x2d0 | Process Address Space ID |

- **PCI atomics están habilitadas en la tarjeta** (`ReqEn+`). El árbol de geometría tenía
  como abierto *"narrow vs wide coherence"* y *"cuál de los 5 dominios de coherencia
  contiene el peligro"*, y `kfd_set_iolink_no_atomics` lee precisamente
  `PCI_EXP_DEVCAP2_ATOMIC_COMP32/64`. **Ahora esa lectura tiene dato: 32 y 64 bits
  soportados.** Lo que amdgpu haga con ello es otra pregunta.
- **PASID presente** significa que la GPU tiene identification de espacio de direcciones
  de proceso por hardware. Es la base de la virtualización de GPU, y es relevante para la
  decisión entre GART plano (VMID0) y page tables (VMID1+): **la tarjeta tiene hardware
  para lo segundo**, aunque el camino de gfx8 legacy que usa hoy no lo ejercite.

## 6. PCIe: confirma y precisa el hallazgo 1085

```text
LnkCap: Port #0, Speed 8GT/s, Width x8, ASPM L1, Exit Latency L1 <1us
LnkSta: Speed 5GT/s (downgraded), Width x4 (downgraded)
LnkCtl: ASPM Disabled; RCB 64 bytes, CommClk+
LnkCtl2: Target Link Speed: 8GT/s, EnterCompliance- SpeedDis-
        Supported Link Speeds: 2.5-8GT/s, Crosslink-, Retimer-, 2Retimers-, DRS-
DevCtl: MaxPayload 128 bytes, MaxReadReq 512 bytes
```

El hallazgo 1085 resolvió esto desde `journalctl -k` y obtuvo un `3.94x` de déficit. Aquí
**la capacidad se lee directamente del dispositivo** y coincide:

- **x8 a 8 GT/s capaz**, negociado **x4 a 5 GT/s**, y lspci marca **`downgraded` en los dos
  campos** — no es una lectura de velocidad momentánea, es el estado del enlace.
- `SpeedDis-`: el fallo no ha sido puesto por software.
- **`MaxReadReq 512 bytes`** y **`MaxPayload 128 bytes`**: valores bajos frente a lo
  habitual en GPU de escritorio. Limitan el tamaño de lectura e inyección de PCIe y **son
  un techo directo del lado de la CPU hacia la GPU**, independiente del techo de VRAM.

> **Eso añade un techo nuevo al §77, y es medido:** el camino de entrada desde la CPU está
> limitado a 512 B por lectura y a 5 GT/s por 4 carriles = **2 GB/s**, contra un enlace
> capaz de 8 GT/s por 8 = **16 GB/s**. **Factor 8 de déficit ya sólo por PCIe**, antes de
> hablar de anchura de bus o de reloj de DRAM. Cualquier trabajo que sea *submisión* o
> *CPU-bound* está limitado por aquí con independencia de la GPU.

## 7. Lo que este hallazgo NO hace

- **No lee el ROM.** No activé el bit 14 (§2). Consecuencia asumida.
- **No afirma que el IH tenga una sola fuente de interrupción.** Afirma que el host recibe
  **un vector MSI**, que es distinto (§4).
- **No decide el techo de reloj de memoria.** Sigue con dos candidatos medidos, 1500 y
  2000 MHz (hallazgo 1419).
- **No toca la GPU.** Ni un registro, ni un bit de configuración, ni un resume.

## 8. Procedencia

```text
sudo -n true                      -> password required  (antes: sin acceso root)
ls -la /sys/bus/pci/devices/0000:01:00.0/rom        131072 B  0600 root:root
cat .../rom   SIN root            -> EACCES  (Permiso denegado)
cat .../rom   CON root            -> EINVAL  (Argumento inválido)
dd  if=.../rom bs=65536 count=2   -> EINVAL, 0 bytes escritos
setpci -s 00:01.0 04.W            -> 0x0407
lspci -s 01:00.0 -vv              -> 92 lineas, 16 capacidades  (/tmp/opencode/lspci_vv.txt)
ls /lib/firmware/amdgpu/          -> 677 entradas
```

```text
ESTADO=PROBADO · polaris12 NO tiene ip_discovery: PROVEN_ABSENT (8 de 677 blobs lo tienen,
       todos soc15).  Las bases de registro solo pueden venir de las tablas fijas del
       fuente: eso convierte el mayor hueco abierto en analisis estatico.
       · 16 capacidades PCI medidas; la limitacion "config space truncado a 64 bytes"
         era un artefacto de permisos, no del hardware
       · MSI Count=1/1, SIN MSI-X: una sola linea de interrupcion para toda la GPU
       · ATS, PRI, PASID y PCI atomics presentes y habilitadas
       · BARs CORROBORADOS por segunda via
       · PCIe x8/8GT capaz, x4/5GT downgraded: techo de 2 GB/s de entrada desde la CPU,
         deficit de 8x ya solo por el enlace
       · el ROM sigue ilegible porque el bit 14 (ROM ENABLE) esta apagado; NO se activo
LIMITE  leer el ROM exigiria una escritura de config space en un dispositivo de display
       vivo.  No se justifica: lo que se buscaria (tabla de offsets) ya se sabe que no
       existe para esta ASIC.
Siguiente  1) desmultiplexacion por fuente en el bloque IH: con un vector, el registro de
          estado por IP y su mascara son la pieza critica.  Es el bloqueo de la interrupcion
       2) MaxReadReq 512 B: quien lo programa y por que, si el firmware o el driver
       3) amdgpu_mc, que decide si el techo de memoria es 1500 o 2000 MHz (1419)
```
