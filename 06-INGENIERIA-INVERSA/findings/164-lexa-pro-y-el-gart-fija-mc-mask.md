# 164 · El chip se llama Lexa PRO, y el 88% de su VRAM no la ve el anfitrión

```
CLASSIFICATION=DOCUMENTATION · TRACK=OBSERVED
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=LOG_READ_ONLY · GPU INTACTA
```

## Qué resuelve

**La pregunta que `233` dejó como la única con consecuencias — cuánta VRAM hay en la
placa — y tres cosas más que salen de mirar la lista de recursos PCI en vez del log del
driver.**

**Y una que corrige el título de `233`: no es un RX550 de 2 GiB, es un Lexa PRO con
2.048 MiB visibles, de los cuales el anfitrión puede mapear 256 MiB.**

## 1 · El nombre del silicio, que no estaba en ninguna nota

```
01:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI]
        Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X] (rev c7)
        Subsystem: Advanced Micro Devices, Inc. [AMD/ATI] Device 0b04
```

```
modalias: pci:v00001002d0000699Fsv00001002sd00000B04bc03sc00i00
```

**⇒ El chip se llama `Lexa PRO`, es un `0x699F` con subsistema `0x0B04`, revisión `c7`,
y su familia de mercadotecnio cubre las Radeon 540/550 y las RX 540X/550X.** `PROVEN`,
observado.

**Y el `Lexa PRO` es un nombre de silicio, no de producto: el producto es la SKU de la
placa, y el silicio es el que comparte genealogy con Polaris 10 y Polaris 12.** `PROVEN_DERIVED`.
**Y eso encaja con el cuarto eje de `233`:** el chip se anuncia como `POLARIS12` y su SMU
es `polaris10_smu`, y el `Lexa` es la razón por la que las dos cosas son ciertas a la vez.

## 2 · Y los 2.048 MiB de VRAM de los que el anfitrión ve 256 MiB

Las regiones PCI del dispositivo, leídas de `/sys/bus/pci/devices/0000:01:00.0/resource`
y confirmadas con `lspci -vv`:

| BAR | dirección | tamaño | tipo |
|---|---|---|---|
| 0 | `0x0E0000000` | **256 MiB** | memoria 64-bit prefetchable |
| 2 | `0x0F0000000` | 2 MiB | memoria 64-bit prefetchable |
| 4 | `0x0E000` | 256 B | puertos de E/S |
| 5 | `0x0F7D00000` | **256 KiB** | memoria 32-bit no prefetchable |
| ROM | `0x0C0000` | 128 KiB | |

**⇒ Total mapeable por el anfitrión: 258,38 MiB. VRAM física: 2.048 MiB.** `PROVEN`.

**⇒ 1.792 MiB —el 88% de la VRAM— no son visibles por el anfitrión, y se alcanzan sólo a
través de la GART.** `PROVEN_DERIVED`.

**Y esto explica, de una vez, por qué `140` tiene un mapa de direcciones que no se parece
al mapa PCI: son dos espacios distintos.**

| espacio | qué contiene | direcciones |
|---|---|---|
| **PCI del anfitrión** | BAR0, BAR2, E/S, MMIO, ROM | `0x0C0000` … `0x0F7D3FFFF` |
| **controlador de memoria de la GPU** | VRAM y GART | `0xF400000000` … `0xFF0FFFFFFF` |

**El BAR de 256 MiB es una ventana del anfitrión sobre el principio del espacio de la
GPU, y los 1.792 MiB restantes no tienen BAR: sólo existen detrás de la GART.** `PROVEN_DERIVED`.

**Y la ventana de MMIO son 256 KiB = 65.536 dwords, que es todo lo que se puede tocar en
una BAR: `register mmio size: 262144`, observado.** `PROVEN`.

## 3 · Y la aritmética inversa que fija `mc_mask`

`140` dejó `mc_mask` sin derivar, y el motivo es que **no está en el código: se sobrescribe
en tiempo de ejecución.**

```
gmc_v8_0.c:1133    mc_mask = 0xffffffffff      (40 bits, todos unos)  -> valor POR DEFECTO
amdgpu_psp.c:1998  mc_mask = adev->umc.active_mask                     -> valor REAL
```

**Y el default no produce la posición observada del GART.** Medido por programa:

```
gart_start observado                              = 0xFF00000000
gart_start = max_mc_address - gart_size + 1        (amdgpu_gmc.c:328, BEST_FIT)
  => max_mc_address = 0xFF00000000 + 0x10000000 - 1 = 0xFF0FFFFFFF
```

**Si `mc_mask` fuera `0xFFFFFFFFFF`, el GART caería en `0xFFF0000000`, que está 3,75 GiB
más arriba de lo observado.** `PROVEN`.

**⇒ El `max_mc_address` efectivo de esta placa es `0xFF0FFFFFFF`, y no sale de
`gmc_v8_0.c` sino del PSP, que lo lee del firmware.** `PROVEN_DERIVED`.

**⇒ `mc_mask` es el noveno punto de contacto con firmware del proyecto, y es del mismo
tipo que el reloj de `161`:** un valor que el driver no calcula sino que recibe. **Y la
posición observada del GART es el dato que lo fija, por aritmética inversa.** `PROVEN`.

**Y esto explica por qué `140` no pudo cerrarlo y no era culpa de nadie: el valor por
defecto de 40 bits está en el código, y el valor real de esta placa es 3,75 GiB más
bajo, y la diferencia la pone el firmware.** `PROVEN_DERIVED`.

## 4 · Y el «hueco» de `140` no es el `HOLE` del código: undécima colisión

`amdgpu_gmc.h:35-39`, que `140` no llegó a leer:

```c
/* VA hole for 48bit and 57bit addresses */
#define AMDGPU_GMC_HOLE_START   (adev->vm_manager.max_level == 4 ?\
                                0x0100000000000000ULL : 0x0000800000000000ULL)
#define AMDGPU_GMC_HOLE_END     (adev->vm_manager.max_level == 4 ?\
                                0xff00000000000000ULL : 0xffff800000000000ULL)
```

**El log dice `2 levels`, luego `max_level != 4`, luego `AMDGPU_GMC_HOLE_START` =
`0x800000000000` = 2^55 = 128 TiB.** `PROVEN`.

**⇒ El «hueco» de `140` —los 42,0 GiB entre el fin de la VRAM y el inicio del GART— NO es
este `HOLE`.** Está en `0xF480000000`…`0xFEFFFFFFFF`, dentro del espacio de 2^40 del
controlador; el `HOLE` del código está en 2^55, muy por encima. **Son dos cosas
distintas que en español se llaman igual.** `PROVEN_DERIVED`.

**Y las tres escalas, que es la lista de lo que no hay que confundir:**

| | valor | qué es |
|---|---|---|
| espacio del controlador de memoria | `0xF400000000` … `0xFF0FFFFFFF` | 2^40: VRAM al principio, GART al tope |
| «hueco» de `140` | `0xF480000000` … `0xFEFFFFFFFF`, 42 GiB | dónde **no** se coloca nada, porque el GART se ponía arriba |
| `AMDGPU_GMC_HOLE_START` | 2^55, 128 TiB | reserva de VA de 48/57 bits, **fuera** del controlador |

**Y el `HOLE` de 2^55 no es decorativo: se hace cumplir.**

```c
amdgpu_gem.c:839   if (args->va_address >= AMDGPU_GMC_HOLE_START &&
amdgpu_gem.c:840       args->va_address < AMDGPU_GMC_HOLE_END) {
amdgpu_gem.c:843           "va_address 0x%llx is in VA hole 0x%llx-0x%llx\n", ...
amdgpu_gem.c:845           return -EINVAL;
amdgpu_gem.c:848   args->va_address &= AMDGPU_GMC_HOLE_MASK;
```

**Una dirección virtual dentro de la banda se rechaza con `-EINVAL` y se dice por qué; y
fuera de ella se enmascara, que es lo que hace el comentario de `amdgpu_gmc.h:41-47`: «el
hardware se programa como si el hueco no existiera».** `PROVEN`.

**Y el truncamiento que cierra la cadena con el log:**

```c
amdgpu_kms.c:995   vm_size = min(vm_size, 1ULL << 40);          /* 1 TiB */
amdgpu_kms.c:999   dev_info->virtual_address_max = min(vm_size, AMDGPU_GMC_HOLE_START);
```

**`min(64 GiB del log, 128 TiB) = 64 GiB`, y el log dice `vm size is 64 GB`.** Cuarta vía
independiente que da el mismo número, después de las tres de `233`. `PROVEN`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El silicio se llama `Lexa PRO` | `PROVEN`, observado |
| 2.048 MiB de VRAM, 256 MiB con BAR, 1.792 MiB sólo por GART | `PROVEN` |
| Dos espacios de direcciones distintos: PCI y controlador | `PROVEN` |
| La ventana de MMIO son 256 KiB = 65.536 dwords | `PROVEN` |
| `max_mc_address` efectivo = `0xFF0FFFFFFF` | `PROVEN`, por aritmética inversa |
| El default `0xFFFFFFFFFF` daría el GART 3,75 GiB más arriba | `PROVEN` |
| `mc_mask` lo sobrescribe el PSP desde el firmware | `PROVEN_DERIVED` |
| `mc_mask` es el noveno punto de contacto con firmware | `PROVEN` |
| `AMDGPU_GMC_HOLE_START` = 2^55, muy por encima del hueco de `140` | `PROVEN` |
| Undécima colisión: el «hueco» de `140` y el `HOLE` del código | `PROVEN_DERIVED` |
| El `HOLE` se hace cumplir con `-EINVAL` | `PROVEN` |
| `min(vm_size, HOLE_START)` = 64 GiB, como el log | `PROVEN`, cuarta vía |
| Cuánta VRAM física tiene la placa por detrás de la de arranque | **`NOT_DETERMINED`** |
| Si el PSP lee `active_mask` de un registro o de una tabla de firmware | **`NOT_DETERMINED`** |
| Si la banda de 42 GiB puede alojar algo si el GART se colocara abajo | **`NOT_DETERMINED`** |

**La primera de las abiertas es la que más pesa: 2.048 MiB visibles es lo que el BIOS
entrega, y una placa con más VRAM detrás daría un `max_mc_address` mayor y un GART distinto
— porque `mc_mask` viene del firmware y no del código.** El único modo de cerrarlo sin
instrumentar es leer el registro del controlador, y eso es `MMIO`, nivel 4.

## Procedencia

- `OBSERVED` -- `lspci -s 01:00.0`, `lspci -vv -s 01:00.0`,
  `/sys/bus/pci/devices/0000:01:00.0/{dst,modalias,resource}`,
  `journalctl -k -b` (solo para `vm size is 64 GB`, `register mmio size`, y las líneas de
  `233`). Sin root, sin MMIO, sin tocar la GPU.
- Medición por programa: **las seis regiones PCI decodificadas y sus tamaños, la suma
  258,38 MiB, y el 1.792/2.048 = 88% de VRAM no visible por el anfitrión**;
  **la aritmética inversa `gart_start → max_mc_address`, y la comparación contra el
  default de `gmc_v8_0.c` que da una diferencia de 3,75 GiB**; los tres tamaños de hueco;
  el `min(64 GiB, 128 TiB)`.
- `STATIC` -- `drivers/gpu/drm/amd/amdgpu/amdgpu_gmc.h:35-39` (la macro y su condición),
  `:41-48` (el comentario del enmascaramiento y `AMDGPU_GMC_HOLE_MASK`),
  `amdgpu/amdgpu_gmc.c:299` (`max_mc_address = min(mc_mask, AMDGPU_GMC_HOLE_START - 1)`),
  `:326-328` (las dos ramas de colocación del GART), de `140`;
  `amdgpu/amdgpu_psp.c:1998` (`mc_mask = adev->umc.active_mask`),
  `amdgpu/gmc_v8_0.c:1133` (`mc_mask = 0xffffffffff`),
  `amdgpu/amdgpu_gem.c:839-848` (el rechazo y el enmascaramiento),
  `amdgpu/amdgpu_kms.c:995-999` (los dos truncamientos),
  `amdgpu/amdgpu_gem.c` (el hueco inferior) y `amdgpu/amdgpu_amdkfd.c:187`.
- **Y una precisión sobre `140`, y no es una refutación:** el hueco entre VRAM y GART son
  exactamente 42,0 GiB (`0xFF00000000 - 0xF47FFFFFFF = 0xA80000000`), y `140` lo dibujaba
  como «<40.0 GiB» en la figura. **Es una cifra ilustrativa redondeada y no una conclusión**;
  el resto de `140` queda confirmado por `233` en sus nueve puntos.
- Encadenada con `233` (**el `NOT_DETERMINED` de la VRAM queda cerrado en cuanto al valor
  visible, y abierto en cuanto a la VRAM física**), `161` (el reloj lo pide el BIOS:
  ésta es la misma forma, noveno contacto), `232` (la tabla y el constructor, elevada a
  hecho de silicio en `233`), `155` (DCE 11.2), `153` (los siete `path` que siguen sin
  poder contar), `140` (**el mapa, y ahora con los dos espacios separados**),
  `136` (la cadena de coherencia), `132` y `130` (geometría, verificada en `233`),
  `220` (BAR 256 MiB y VRAM 2 GiB — el que ya lo sabía).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El hecho de que el 88% de la VRAM sea invisible para el anfitrión no salió del driver:
salió de comparar `lspci` con la línea del log, y las dos cosas las dice kernels
distintos en momentos distintos.**

*`Detected VRAM RAM=2048M, BAR=256M` está en una sola línea del log y la he estado
leyendo como un par de hechos sin relación durante toda la tanda.* La línea **es** la
relación, y dice que la BAR es un dieciseisavo de la VRAM. *Cuesta un `lspci -vv` y
cambia la forma de pensar sobre `140`: no es que la GPU tenga 256 MiB, es que el anfitrión
pide una ventana de 256 MiB sobre una VRAM de 2 GiB y el resto se sirve por la GART.*
**Y esa es precisamente la razón de existir de la GART, y `140` la tenía como un rango
de direcciones más sin ver que es el 88% de la memoria de la placa.**

**Y el segundo hallazgo es una limitación del corpus que sólo se ve al intentar derivar:**
`mc_mask` **está** en el código, con un valor de 40 bits, y si se deriva sale mal — el GART
caería 3,75 GiB más arriba. *El valor real lo pone el PSP desde el firmware, y no hay
forma de saberlo leyendo.* Pero hay una forma de saberlo sin leer: **aritmética inversa
desde la posición observada del GART**, que es un dato que el log ya daba desde `140`.

*Esa es la forma más barata de cerrar un `NOT_DETERMINED` que he encontrado en el
proyecto, y es nueva:* **cuando un valor no se puede derivar pero alguna magnitud observada
lo determina, la aritmética hacia atrás es una derivación.** *`gart_start =
max_mc_address - gart_size + 1` con `gart_size` conocido y `gart_start` observado resuelve
`max_mc_address` exactamente, y un `RREG32` del registro de máscara lo confirmaría.* Es
NIVEL 2 en vez de NIVEL 4, y por eso es la vía que se agotó antes.
