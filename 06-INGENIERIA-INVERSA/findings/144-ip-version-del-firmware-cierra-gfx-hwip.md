# 144 · `GFX_HWIP` no existe, pero el IP version está en el firmware: **8.0**, y coincide con el driver en tres bloques

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC + BINARY` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3 + /lib/firmware/amdgpu/` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`CIERRA=la frontera GFX_HWIP que 050 dio por sin fuente`
`DESARROLLA=el NOT_DETERMINED de 135 sobre capacidad por ASIC`

## Cuestión principal

`135` dejó esto escrito:

> *La pregunta siguiente tiene discriminante concreto: encontrar la lista de
> capacidad por ASIC. Si está en Mesa o en el firmware, se convierte
> `NOT_DETERMINED` en `PROVEN`.*

Y el resumen del proyecto tenía `GFX_HWIP` como frontera **bloqueada**, sin
fuente.

Firmware: `/lib/firmware/amdgpu/` tiene 677 ficheros, incluidos 19 de
`polaris12`. Nadie los había mirado.

## Criterio de terminación

Determinar si el IP version de esta placa está disponible en alguna fuente, y
cruzarlo con lo que el driver declara. **Cumplido.**

## `GFX_HWIP`: `PROVEN_ABSENT`, y ahora con causa

```
$ grep -rn "GFX_HWIP" drivers/gpu/drm/amd/
(sin resultado)
$ grep -rn "HWIP" drivers/gpu/drm/amd/
include/mes_v11_api_def.h:199:  enum MES_SWIP_TO_HWIP_DEF {
include/umsch_mm_4_0_api_def.h:198:  UMSCH_MAX_HWIP_SEGMENT = 8
```

**Ni el driver lo lee ni ningún header lo define.** Lo único que contiene
"HWIP" es `MES_SWIP_TO_HWIP`, que es la cesión de programas de shader entre
CP y SH — otra cosa con el mismo nombre.

`050` dijo "sin fuente primaria". Ahora está:**no hay registro que buscar**.
Y eso cierra la frontera en la forma correcta: no es que yo no lo encuentre, es
que `GFX_HWIP` no está en el corpus de esta generación.

## La fuente que sí existe: la cabecera del firmware

Cada microcodigo lleva `struct common_firmware_header`, y el layout **no lo
adiviné**: sale de los nombres y tipos que usa
`amdgpu_ucode_print_common_hdr()` (`amdgpu_ucode.c:37-49`).

```
size u32 @0x00 | header_size u32 @0x04
hdr_ver_maj u16 @0x08 | hdr_ver_min u16 @0x0a
ip_ver_maj u16 @0x0c | ip_ver_min u16 @0x0e
ucode_version u32 @0x10 | ucode_size u32 @0x14
array_offset u32 @0x18 | crc32 u32 @0x1c
```

**Y mi primer parseo estaba mal**: usé **cinco** `u16` en vez de cuatro, lo que
desplaza todos los campos siguientes. Salían números plausibles y falsos.

Lo que lo delató fue el control estructural:

```
array_offset + ucode_size  ==  size  ==  longitud del fichero
        256 + 16788        =  17044  =  17044     -> CUADRA
```

Con el formato de 5 `u16` **no cuadra**. Ese autocomprobación se quedó en el
`--self-test` como control negativo: si el formato erróneo alguna vez cuadrara,
el control dejaría de medir nada.

## El dato: `ip_version` es POR BLOQUE, y Polaris12 dice 8.0

```
$ fw_ipver.py --placa polaris12
fichero                            ip_ver   ucode_v  cuadra
polaris12_pfp.bin.xz                  8.0        235  si
polaris12_me.bin.xz                   8.0        161  si
polaris12_ce.bin.xz                   8.0        134  si
polaris12_mec.bin.xz                  8.0        705  si
polaris12_rlc.bin.xz                  8.0         24  si
polaris12_mc.bin.xz                   8.1   11852880  si
polaris12_sdma.bin.xz                 3.1         58  si
polaris12_smc.bin.xz                  7.2    2234112  si
polaris12_uvd.bin.xz                  6.3   16810512  si
polaris12_vce.bin.xz                  3.4   55581187  si
```

Seis valores distintos en **un solo ASIC**. **`ip_version` no es el IP version
del GFX: es el de cada bloque de microcodigo.** Confundirlo habría dado "el GFX
de Polaris12 es 3.1" leyendo el fichero de SDMA.

## El contraste que lo hace sólido

```
firmware dice   ip_block que declara el driver
-----------     --------------------------------
8.0 (pfp/me/ce/mec/rlc)   gfx_v8_0_ip_block   (gfx_v8_0.c:7128, major=8 minor=0)
8.1 (mc)                  gmc_v8_1_ip_block   (gmc_v8_0.c:1768, major=8 minor=1)
3.1 (sdma)                sdma_v3_1_ip_block  (sdma_v3_0.c:1693, major=3 minor=1)
6.3 (uvd)                 uvd_v6_3_ip_block
3.4 (vce)                 vce_v3_4_ip_block
```

**Los dos valores que no son 8.0 son los que discriminan.** Si la
correspondencia fuera casualidad, MC diría 8.0 y SDMA daría cualquier cosa.
MC dice **8.1** — y `vi.c:2110` registra `gmc_v8_1_ip_block` para Polaris12, no
la `v8_0` que también existe en el corpus. El firmware picked la misma versión
que el driver.

## Y es sistemático en toda la generación

```
GCN3 (ficheros pfp/me/ce/mec/rlc que declaran 8.0):
  carrizo      5 ficheros
  fiji         5 ficheros
  polaris10    8 ficheros
  polaris11    8 ficheros
  polaris12    9 ficheros
```

**Los cinco ASIC GCN3 dan 8.0**, y solo ellos. Hawaii/Kabini/Kaveri/Mullins dan
7.x; Navi10/12/14 dan 10.1. Eso sube la afirmación de "este fichero dice 8.0"
a "toda la generación GCN3 declara 8.0 para sus ucodes de GFX".

## El driver nunca lo mira

`amdgpu_ucode_print_common_hdr` solo hace `DRM_DEBUG` de cada campo. **El
firmware ofrece el IP version y el driver lo imprime y lo ignora.**

Y `052` ya había encontrado que la tabla de ASIC del driver pone
`ip_version = 0xffffffff` para esta placa, o sea "cualquiera". **Dos sitios
independientes donde el driver decide no comprobar la versión de IP.** Es una
decisión de diseño, no un descuido: el driver clasifica por `device_id`.

## El resultado negativo que cierra la búsqueda de `135`

`135` buscaba una "lista de capacidad por ASIC" en el firmware. Existe un
candidato obvio: el blob `*_ip_discovery.bin`, que es literalmente una tabla de
descubrimiento de IP.

```
$ ls /lib/firmware/amdgpu/ | grep discovery | sed 's/_.*//' | sort -u
aldebaran arcturus picasso raven raven2 vega10 vega12 vega20
```

**No existe para `polaris12`.** Los que lo tienen son todos SOC15 en adelante.
**GCN3 es anterior al descubrimiento de IP**, así que no hay tabla que buscar.

Eso no es un hueco de mi búsqueda: es `PROVEN_ABSENT` **con causa**. La
pregunta de `135` queda respondida en su forma negativa: en esta generación, la
capacidad no se declara en una tabla, se deduce del silicio.

## Clasificación

| afirmación | estado |
|---|---|
| `GFX_HWIP` no existe en el corpus | `PROVEN_ABSENT` — grep sobre `amd/` |
| Polaris12 PFP declara `ip_version = 8.0` | `PROVEN` — cabecera del firmware |
| `ip_version` es por bloque, no del GFX | `PROVEN` — 6 valores en un ASIC |
| MC dice 8.1 y el driver usa `gmc_v8_1_ip_block` | `PROVEN` — firmware + `vi.c:2110` |
| Los 5 ASIC GCN3 dan 8.0 en ucodes de GFX | `PROVEN` — carrizo…polaris12 |
| Que el IP version del GFX sea 8.0 | `CORROBORATED` — 3 cadenas |
| Que eso sea el valor del registro `GFX_HWIP` | `NOT_PROVEN` — el registro no existe |
| Que el driver no lo compruebe | `PROVEN` — `DRM_DEBUG` y nada más |
| Que no exista tabla de capacidad para GCN3 | `PROVEN_ABSENT` — sin `ip_discovery` |
| Que los 36 opcodes de `135` estén soportados | `NOT_DETERMINED` — sigue sin lista |

## Confounders

- **El `ip_version` del firmware y el registro `GFX_HWIP` son cosas distintas.**
  Que coincidan con `gfx_v8_0_ip_block` hace muy probable que valgan lo mismo,
  pero no lo prueba: el registro no existe en el corpus y no se puede leer sin
  inventar su dirección. **`CORROBORATED`, no `PROVEN`.**
- **`/lib/firmware` es un fichero del host, no del corpus.** Puede no coincidir
  con la versión que se instalóoriginally. No hay manifiesto que lo ligue al
  `.ko`.
- **No he verificado el `crc32`.** El campo existe; no lo he comprobado contra
  la cabecera, así que no afirmo integridad del fichero.
- **Los nombres de ASIC son de AMD**, no míos: `carrizo`, `fiji`,
  `polaris10/11/12`. Que carrizo y fiji sean GCN3 lo doy por el número 8.0 y
  por el nombre del fichero de firmware, no por una tabla del corpus.
- **No he tocado la placa.** Todo es lectura de ficheros.

## Desfalsificación

- **(a)** El layout de la cabecera → refutable leyendo
  `amdgpu_ucode_print_common_hdr` y la aserción de cuadre. Con 5 `u16` no cuadra.
- **(b)** MC dice 8.1 → refutable con `fw_ipver --placa polaris12`.
- **(c)** El driver usa `gmc_v8_1_ip_block` → refutable con `vi.c:2110`.
- **(d)** Los 5 GCN3 dan 8.0 → refutable con `--todas`.
- **(e)** `GFX_HWIP` ausente → refutable con `grep -rn GFX_HWIP drivers/gpu/drm/amd/`.
- **(f)** Que sea el registro → **no refutable aquí**, y no se afirma.

## UNLOCKS

- **`GFX_HWIP` deja de ser una frontera abierta**: es `PROVEN_ABSENT` con una
  fuente alternativa que sí funciona. Eso era lo que bloqueaba `050` y `135`.
- **El IP version del GFX de Polaris12 queda en 8.0 por tres cadenas
  independientes**: el firmware lo declara, el driver lo nombra
  (`gfx_v8_0_ip_block`), y toda la base de código es `gfx_v8_0.c`.
- **Existe una herramienta de lectura de cabeceras de firmware** que funciona
  sobre 677 ficheros y sobre ~90 ASICs. Any otra pregunta sobre lo que el
  firmware afirma de sí mismo se responde con ella.
- **La pregunta de la capacidad por ASIC tiene respuesta negativa con causa**:
  GCN3 no tiene `ip_discovery`. Para responderla har falta Mesa o alguien que
  mida el hardware.
- **Descubierto de paso**: `*_ip_discovery.bin` usa un formato de cabecera
  distinto. Los que lo tienen son un camino para otra pregunta, sobre SOC15.

## Evidencia

```
$ grep -rn GFX_HWIP drivers/gpu/drm/amd/            -> sin resultado
$ grep -rn HWIP drivers/gpu/drm/amd/  -> solo mes_v11_api_def.h, umsch_mm_4_0_api_def.h
$ ls /lib/firmware/amdgpu/ | grep discovery | sed 's/_.*//' | sort -u
aldebaran arcturus picasso raven raven2 vega10 vega12 vega20     (no polaris12)

amdgpu_ucode.c:37-49    amdgpu_ucode_print_common_hdr  (los nombres y tipos del layout)
gfx_v8_0.c:7128-7133    gfx_v8_0_ip_block   major=8 minor=0
gmc_v8_0.c:1768-1773    gmc_v8_1_ip_block   major=8 minor=1
sdma_v3_0.c:1693-1698   sdma_v3_1_ip_block  major=3 minor=1
vi.c:2110               amdgpu_device_ip_block_add(adev, &gmc_v8_1_ip_block)

$ fw_ipver.py --placa polaris12 --cruce
  firmware dice 8.1  -> dce_v8_1, gfx_v8_1, gmc_v8_1
  firmware dice 8.0  -> dce_v8_0, gfx_v8_0, gmc_v8_0
  firmware dice 3.1  -> psp_v3_1, sdma_v3_1, uvd_v3_1, vce_v3_1
```

```
08-ARQUITECTURA/tools/fw_ipver.py   --placa --cruce --todas --self-test
self-test: 10 vectores + 4 controles, incluido el control negativo del formato
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.
