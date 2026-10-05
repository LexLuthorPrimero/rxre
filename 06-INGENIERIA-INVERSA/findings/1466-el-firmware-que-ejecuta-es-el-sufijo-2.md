# 1466 — el firmware que se ejecuta es el `_2`, no el que está en disco con el nombre "natural"

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-HARDWARE+REVISION-PROPIA+TOOL NUEVA(VALIDATED)
TRACK=SYSFS/DEBUGFS + STATIC(corpus) + cabeceras de 11 blobs · 0000:01:00.0 · Intel intacta
GENERADO=2026-10-04
AFECTADO=06-INGENIERIA-INVERSA/findings/1445-*   (el "magico de 32 bits" tiene nombre)
         06-INGENIERIA-INVERSA/findings/1446-*   (el metodo, con su condicion de validez)
         06-INGENIERIA-INVERSA/findings/1447-*   (idem)
         06-INGENIERIA-INVERSA/findings/1418-*   (la lista de bloques, con segunda fuente)
         tools/fwsel.py                          (herramienta nueva)
ESTADO=PROBADO · 7 de 12 bloques IP resueltos con coincidencia EXACTA contra el silicio
       · la contradiccion "730 vs 0x00221700" era un artefacto: 730 es el MEC, no el SMC
       · el MEC que corre NO es polaris12_mec.bin, es polaris12_mec_2.bin
       · y el metodo de 1446/1447 queda con su condicion de validez, que era lo que faltaba
```

## 0. Lo que_no_busqué_y_no_encotré: la contradicción del 730

Un análisis del firmware de la SMULlevó a la conclusión de que KFD publica `fw_version = 730`
mientras la cabecera de `polaris12_smc.bin` dice `ucode_version = 0x00221700` = **2 234 112**,
y lo marcó como contradicción, con un discriminador de una línea.

La contradicción era mía, del análisis. **730 no es el SMC.**

```
$ cat /sys/kernel/debug/dri/1/amdgpu_firmware_info
...
MEC  feature version: 49, firmware version: 0x000002da
MEC2 feature version: 49, firmware version: 0x000002da
...
(no hay ninguna linea SMC)
```

**`0x2da` = 730.** El `fw_version` que publica KFD es **la versión del MEC**, el
micro-motor que emite PM4 — que es lo coherente, porque es el firmware de gráficos.

Y el SMC **no aparece** en ese atributo, porque su microcódigo vive en SRAM y lo carga
`smu_init_smc`, no la carga genérica de firmware. **No había contradicción: se compararon
dos firmware distintos.** `REFUTADA`, y el estado del SMC sigue `NOT_DETERMINED` porque su
versión no se publica por ninguna vía que haya encontrado.

## 1. LA REGLA DE SELECCIÓN: por nombre, no por contenido

En `amdgpu/gfx_v8_0.c`, la función que carga el microcódigo de GFX:

```c
/* gfx_v8_0.c:1105-1113 */
if (adev->asic_type >= CHIP_POLARIS10 && adev->asic_type <= CHIP_POLARIS12) {
        err = amdgpu_ucode_request(adev, &adev->gfx.mec_fw,
                                   AMDGPU_UCODE_OPTIONAL,
                                   "amdgpu/%s_mec_2.bin", chip_name);
        if (err == -ENODEV)
                err = amdgpu_ucode_request(adev, &adev->gfx.mec_fw,
                                   AMDGPU_UCODE_REQUIRED,
                                   "amdgpu/%s_mec.bin", chip_name);
}
```

`CHIP_POLARIS12` está dentro del rango, así que **se pide primero el `_2`**, con
`AMDGPU_UCODE_OPTIONAL`, y sólo se recurre al fichero sin sufijo si el primero da `-ENODEV`.
El mismo bloque se repite para PFP (`:983-991`), ME (`:1002-1010`) y MEC2 (`:1126-1134`).

**La consecuencia es la que importa, y es una trampa silenciosa:**

> `polaris12_mec.bin` **no se abre nunca en esta tarjeta.** Existe, está instalado, es
> legible, y no es lo que corre. Analizarlo produce un análisis *correcto* del binario
> equivocado, sin ninguna señal de error.

Es la tercera vez en esta sesión que mi propio método falla antes que la fuente. Las otras
dos: `SBAR` dentro de `CROSSBAR`, y `mmVM_CONTEXT_IDENTITY_PHYSICAL_OFFSET` por un `read`
demasiado ancho. Ésta es la más peligrosa de las tres, porque no da error ni en el código ni
en la salida.

## 2. La comprobación contra el silicio: 7 de 12, coincidencia exacta

Fuente A = cabeceras de los blobs en disco. Fuente B = `amdgpu_firmware_info`, que es **lo
que el driver cargó**. No se derivan una de otra.

| bloque | versiones en disco | vivo | **ejecuta** | estado |
|---|---|---|---|---|
| MC | `0x00b4dc50` | `0x00b4dc50` | `polaris12_mc.bin` | `CORROBORADO` |
| ME | `0x000000a1`, `0x000000a7` | `0x000000a7` | **`polaris12_me_2.bin`** | `CORROBORADO` |
| PFP | `0x000000eb`, `0x000000fe` | `0x000000fe` | **`polaris12_pfp_2.bin`** | `CORROBORADO` |
| CE | `0x00000086`, `0x0000008c` | `0x0000008c` | **`polaris12_ce_2.bin`** | `CORROBORADO` |
| RLC | `0x00000018` | `0x00000018` | `polaris12_rlc.bin` | `CORROBORADO` |
| MEC | `0x000002c1`, `0x000002da` | `0x000002da` | **`polaris12_mec_2.bin`** | `CORROBORADO` |
| MEC2 | `0x000002c1`, `0x000002da` | `0x000002da` | **`polaris12_mec2_2.bin`** | `CORROBORADO` |
| UVD | `0x01008210` | `0x01821000` | — | `NOT_DETERMINED` |
| VCE | `0x03501a03` | `0x351a0300` | — | `NOT_DETERMINED` |
| IMU/SOS/ASD | *(sin blob)* | `0x00000000` | — | `NOT_DETERMINED` |

**Todo el microcódigo de GFX ejecuta la variante `_2`.** Los cinco. Y el patrón es limpio:
**MC y RLC coinciden con el disco; los cinco de GFX no.** Lo que hace el PSP o la lógica de
carga no afecta a MC/RLC, y sí a todo GFX.

### 2.1 Tres binarios MEC distintos, misma longitud

```text
polaris12_mec.bin      262 824 B  sha256 799b3e73fd26  ucode_version 0x000002c1   <- NUNCA SE ABRE
polaris12_mec2.bin     262 824 B  sha256 799b3e73fd26  ucode_version 0x000002c1   <- identico al anterior
polaris12_mec_2.bin    262 824 B  sha256 1e0ce977d292  ucode_version 0x000002da   <- EL QUE CORRE
polaris12_mec2_2.bin   262 824 B  sha256 11dc9315750b  ucode_version 0x000002da   <- EL QUE CORRE (MEC2)
```

Cuatro ficheros, tres binarios. **MEC y MEC2 ejecutan binarios DISTINTOS de la misma versión**
(`1e0ce9…` ≠ `11dc93…`) — dos instancias, mismo número de versión. Y `polaris12_mec2.bin` es
**byte-idéntico** a `polaris12_mec.bin`, o sea que el fichero "mec2" del par sin sufijo es una
copia. Sólo se detecta comparando hashes: por nombre y por versión son indistinguibles.

### 2.2 El "mágico de 32 bits" del hallazgo 1445 tiene nombre

El hallazgo 1445 leyó del silicio `mmMC_SEQ_IO_DEBUG_DATA = 0x00b4dc50` y escribió que **no**
era "el mágico de 32 bits `0x05b4dc40`", y de ahí sacaba que el firmware era polaris12
(clase 64 bits). Ese valor tiene ahora origen:

```text
polaris12_mc.bin       ip 8.1  ucode_version 0x00b4dc50   <- el que corre
polaris12_32_mc.bin    ip 8.1  ucode_version 0x05b4dc40   <- el "32 bits"
polaris12_k_mc.bin     ip 8.1  ucode_version 0x01b4df80
```

Tres variantes de MC, **las tres con `ip_version` 8.1**. El silicio no está ambiguo: devuelve
`0x00b4dc50` y ése es el que corre. **El veredicto de 1445 queda confirmado, y el valor que
yo había tratado como "mágico" es un blob hermano con nombre.**

## 3. Corroboración que no buscaba: `ip_version` ↔ bloque del log de arranque, 1:1

```text
blob      header_size  header_ver  ip_ver   bloque del log de arranque
mc             40         1.0       8.1     gmc_v8_1_0
sdma           52         1.1       3.1     sdma_v3_1_0
uvd            32         1.0       6.3     uvd_v6_3_0
vce            32         1.0       3.4     vce_v3_4_0
mec_2/me_2/…   44         1.0       8.0     gfx_v8_0_0
smc            36         1.0       7.2     smu_v1_0_0 (numeración SMC, no IP)
```

**Cinco de cinco.** El hallazgo 1418 ya había dado la lista de nueve bloques del log de
arranque, y ahora tiene una **fuente independiente**: no sólo dice qué bloques se instancian,
sino que la versión de IP que declara cada firmware en su propia cabecera **es** la versión
del bloque que el driver levanta. Dos fuentes que no se derivan una de otra y coinciden.

## 4. El SMC no trae soft pptable — y eso explica dónde vive la escalera de relojes

`amdgpu/amdgpu_ucode.h:51-54`:

```c
struct smc_firmware_header_v1_0 {
        struct common_firmware_header header;
        uint32_t ucode_start_addr;          /* 32 + 4 = 36 */
};
struct smc_firmware_header_v2_0 {           /* :57-61 */
        struct smc_firmware_header_v1_0 v1_0;
        uint32_t ppt_offset_bytes;          /* soft pptable */
        uint32_t ppt_size_bytes;
};
```

El blob SMC de esta tarjeta declara `header_size_bytes = 36` ⇒ **`smc_firmware_header_v1_0`,
sin soft pptable.** Una v2_0 mediría 44.

> **Esto corrobora por vía independiente el hallazgo 1449.** La escalera de relojes de
> memoria vive en SM RAM y la puebla el driver
> (`polaris10_populate_all_memory_levels`, `polaris10_smumgr.c:1208-1248`), **no** en el
> firmware de disco. Dos análisis que apuntaban al sitio equivocado.

## 5. `crc32`: cerrado como `NOT_NEGATIVE`, y un bloqueado del proyecto cerrado

`amdgpu_ucode.h:40` documenta el campo:

```c
uint32_t crc32;  /* crc32 checksum of the payload */
```

Probé el rango documentado, `[ucode_array_offset_bytes, +ucode_size_bytes)`, con cuatro
algoritmos (zlib, CRC-32 reflejado con y sin inversión final, CRC-32C/Castagnoli) sobre nueve
blobs: **108 intentos, cero coincidencias.**

La pregunta que importa no es cuál es el algoritmo, sino quién lo comprueba:

```
$ grep -rn crc32 amdgpu/
amdgpu/amdgpu_ucode.h:40:  uint32_t crc32;  /* crc32 checksum of the payload */
amdgpu/amdgpu_ucode.c:50:  DRM_DEBUG("crc32: 0x%08x\n", le32_to_cpu(hdr->crc32));
```

**Sólo dos ficheros en todo el árbol amdgpu, y el único uso es un `DRM_DEBUG` que lo
imprime.** El driver **no valida el campo**. Por tanto:

- el desajuste del 1446 no es `NOT_DETERMINED`: es **`NOT_NEGATIVE`**, porque nadie lo
  comprueba y por tanto no puede discriminar nada;
- el bloqueado "`mc_firmware_header_v1_0` crc32 range unknown" queda **cerrado**: el rango es
  irrelevante para este trabajo.

## 6. Herramienta nueva: `tools/fwsel.py` — `VALIDATED`

Existe porque la clase de error de la §1 es exactamente la que un humano comete dos veces.
El procedimiento es: inventariar los blobs candidatos, parsear sus cabeceras, y resolver
contra lo que el driver dice que cargó.

```text
PROPOSITO    resolver que blob ejecuta cada bloque IP, cruzando disco contra el driver
PREGUNTA     ¿este analisis describe el firmware que corre, o el homologo que no corre?
CAPACIDAD    nueva: resolucion de ambiguos de firmware con dos fuentes independientes
ENTRADA      /lib/firmware/amdgpu/<chip>_*.bin[.xz]
SALIDA       tabla por bloque: candidatos, version en disco, version viva, EJECUTA, estado
             + sha256 del que ejecuta + tabla de saltos declarada + propiedades de KFD
ESTRUCTURA   NO supuesta: amdgpu/amdgpu_ucode.h:28-40, :181-186, :44-48, :51-54
VALIDACION   1) coincidencia exacta en 7 bloques contra una fuente independiente
             2) autocomprobaciones por blob: size_bytes == tamaño real, y el final del
                payload (ucode_array_offset + ucode_size) == size_bytes
             3) modo --disk-only sin privilegios, y modo --json, ambos probados
             4) fallo de layout detectado y NO silenciado (ver mis bugs, §7)
LIMITACION   UVD y VCE NO resuelven. Diagnostico: el ip_version en +12 es correcto para
             ambos (6.3 y 3.4), luego la cabecera comun se parsea bien, pero el campo que
             publica el driver no coincide con +16. Hipotesis: UVD/VCE tienen su propia
             cabecera con el campo de version en otro offset. DISCRIMINADOR: localizar el
             struct que el driver usa para UVD (NO esta en amdgpu_ucode.h) y releer en esa
             posicion. Estado: NOT_DETERMINED.
REPRODUCIBLE un comando, sin estado, sin escrituras
```

### 6.1 Por qué la herramienta NO supone layouts

El RLC es el ejemplo. `rlc_firmware_header_v1_0` mide 52 bytes
(`amdgpu_ucode.h:216-223`), pero el blob RLC de esta tarjeta declara `header_size_bytes = 104`
y `header_version 2.0`. Mi primera versión de la herramienta aplicaba los offsets del struct de
GFX (`jt_offset@44`, `jt_size@48`) a **todos** los bloques, y salía una tabla de saltos con
`jt_offset=160 jt_size=61` que **parecía válida y no lo era**.

La herramienta ahora selecciona el layout por `(familia, header_version)` y, cuando no lo
conoce, escribe `ext: NOT_DETERMINED` **en vez de leer offsets a ciegas**. La falsa tabla
desapareció. *(`rlc_firmware_header_v2_0` queda como layout no implementado a propósito.)*

## 7. Mis errores de esta ronda, todos declarados

| # | error | cómo se detectó | alcance |
|---|---|---|---|
| 1 | Formato `struct` con `H` para `header_size_bytes`, que es `u32` ⇒ todo lo posterior desplazado 2 bytes. Salió `ip=0.131079` en vez de `ip=7.2` | el valor era absurdo y no cuadraba con 1446 | **sólo de presentación**; los bytes reales siempre fueron correctos |
| 2 | Aserción `common_firmware_header == 40` en la herramienta. **Son 32** | la aserción saltó sola | me hizo leer la definición en vez de fiarme |
| 3 | Leí los offsets del struct de GFX sobre el blob del RLC y obtuve una tabla de saltos plausible y falsa | contrasté contra `rlc_firmware_header_v1_0` | **corregido en la herramienta** por selección por versión |
| 4 | Leí mal la alineación de columnas de `ls` y creí durante un momento que `polaris12_mec2.bin.xz` eran 20 bytes | el ratio de compresión era imposible | ninguno; el resultado final es correcto |
| 5 | Dije "cinco de cinco" sobre una correspondencia de cinco filas sin haber comprobado que el log de arranque contiene esas cinco | el log ya estaba en el hallazgo 1418 | la tabla de arriba es la que hay que auditar |

## 8. Procedencia

```text
medido   /sys/kernel/debug/dri/1/amdgpu_firmware_info   12 lineas, lectura, requiere raiz
         /sys/class/kfd/kfd/topology/nodes/1/properties  fw_version=730  sdma_fw_version=58
en disco 11 blobs /lib/firmware/amdgpu/polaris12_*.bin.xz, cabeceras parseadas, sha256
fuente   amdgpu/gfx_v8_0.c:983-991, :1002-1010, :1105-1113, :1126-1134  la regla del _2
         amdgpu/amdgpu_ucode.h:28-40  common_firmware_header (32 bytes)
         amdgpu/amdgpu_ucode.h:181-186  gfx_firmware_header_v1_0 (44): ucode_feature_version@40,
                                       jt_offset@44, jt_size@48
         amdgpu/amdgpu_ucode.h:44-48  mc_firmware_header_v1_0 (40): io_debug@32/36
         amdgpu/amdgpu_ucode.h:51-61  smc v1_0 (36) y v2_0 (44, con soft pptable)
         amdgpu/amdgpu_ucode.h:216-223 rlc_firmware_header_v1_0 (52) — NO es el de este blob
         amdgpu/amdgpu_ucode.c:50     crc32 sólo se imprime, nunca se valida
herramienta tools/fwsel.py, validada como se describe en §6
```

```text
ESTADO=PROBADO · el microcodigo GFX que ejecuta es la variante _2 en los cinco bloques
       (ME, PFP, CE, MEC, MEC2).  polaris12_mec.bin NO se abre nunca en esta tarjeta
REFUTADA la "contradiccion" fw_version=730 vs SMC 0x00221700: 730 = 0x2da es el MEC, y el
       SMC no se publica en amdgpu_firmware_info.  Comparaban dos firmware distintos
REFUTADO NOT_NEGATIVE  el crc32 no coincide: el driver no lo valida (amdgpu_ucode.c:50 es un
       DRM_DEBUG).  Cierra el bloqueado del rango de crc32
CORROBORADO el "32 bits magico" del 1445 = polaris12_32_mc.bin, un blob hermano con nombre.
       Tres variantes de MC con la misma ip_version 8.1; el silicio no es ambiguo
CORROBORADO  ip_version de cada firmware = version del bloque del log de arranque, 1:1 en
       cinco de cinco.  Segunda fuente independiente para la lista de 1418
CORROBORADO  el SMC es smc_firmware_header_v1_0 (36 B): sin soft pptable.  Refuerza 1449
NUEVO       tools/fwsel.py VALIDATED.  Resuelve 7 de 12 bloques con coincidencia exacta
NUEVO       cuatro ficheros MEC en disco son tres binarios; dos de ellos de la misma version
       y distinto contenido, indistinguibles si no comparas hashes
NOT_DETERMINED  UVD y VCE: el driver publica una version que no esta en +16 del blob de disco.
       Discriminador en §6: localizar el struct de UVD y releer en esa posicion
LIMITE   el SMC sigue sin version verificable por via de observacion.  Y no hay forma de
       cambiar de blob sin intervencion en la GPU, asi que la regla de seleccion queda
       PROBADA por lectura de codigo + coincidencia con el silicio, no por experimento
RIESGO  la GPU sigue en power/control=on.  Reversible con "echo auto >", y la razon de
       dejarla despierta es que sin ella no hay ningun dato vivo
FRONTERA Intel intacta: fb0=i915drmfb 1366,768, card0 control=auto runtime=active,
       HDMI-A-1=connected, un solo /dev/fb0
Siguiente  1) dos subagentes estan desensamblando polaris12_mec_2.bin (el que CORRE, no el
           otro) buscando la tabla de saltos y el vocabulario PM4, e inventariando el ROM
         2) jt_offset/jt_size del MEC: gfx_v8_0.c:1191 los usa, o sea que si estan declarados
           en la cabecera, y eso acota donde empieza el codigo
         3) la version del SMC solo se puede obtener del propio SMC (registro o SMC RAM),
           y eso es intervencion: NO JUSTIFICADA todavia
```

## 9. La regla que sale de esto

> Un artefacto de firmware tiene **dos** identidades: el nombre del fichero y el contenido.
> En gfx8 el driver elige **por nombre**, y hay tres nombres por bloque. Analizar el fichero
> equivocado **no falla**: produce conocimiento aparentemente sólido sobre el hardware
> equivocado. La única defensa es cerrar el circuito contra una fuente independiente — aquí,
> `amdgpu_firmware_info` — y eso es lo que hace `fwsel.py`.

En el proyecto eso ya había pasado antes: el hallazgo 923 sobre `base+24` frente a
`base+0x20`, el 1419 con la máscara adivinada, el `CROSSBAR`. **Tres instancias distintas de lo
mismo: verificar antes de escribir, y verificar contra una fuente que no seas tú.**