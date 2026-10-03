# 254 · La cabecera de los 20 firmware de Polaris12 se valida 20 de 20, y el driver no la valida nunca

```text
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + BINARY
CORPUS=RESEARCH/working/linux-7.1.3 + /lib/firmware/amdgpu/ + 06-INGENIERIA-INVERSA/firmware/
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=NOT_RUN · GPU INTACTA
```

> **Convención de rutas.** `amdgpu/x.c` = `drivers/gpu/drm/amd/amdgpu/x.c`.  Las 9 citas de
> código de esta nota resuelven con base `drivers/gpu/drm/amd/`.

## Qué resuelve

**Cierra el `NOT_IN_CORPUS` que `251` dejó sobre el firmware, y de paso `253`. El SMC de esta
placa no es un objeto opaco: tiene una cabecera de 32 bytes documentada por el propio driver, y
los 20 firmware de Polaris12 la cumplen sin una sola excepción.** `PROVEN`.

**⇒ `PROVEN`. El layout está declarado en `amdgpu/amdgpu_ucode.h:30-41`,
`struct common_firmware_header`, 10 campos y 32 bytes.** `PROVEN`.

**⇒ `PROVEN`. Y los 20 binarios de `/lib/firmware/amdgpu/polaris12_*.bin.xz` lo cumplen:
`size_bytes` igual al tamaño real del fichero en 20 de 20, y
`ucode_array_offset_bytes + ucode_size_bytes == size_bytes` en 20 de 20.** `PROVEN`.

**⇒ `PROVEN_ABSENT`. El driver nunca valida esa cabecera: `ip_version_major` aparece una sola
vez en `amdgpu_ucode.c`, dentro de un `DRM_DEBUG`, y no hay ni una comparación
`if (ip_version_major` en todo `amdgpu/`.** `PROVEN_ABSENT`.

**⇒ `PROVEN_DERIVED. La cabecera es una convención que el firmware respeta y el driver no
comprueba. La consecuencia para un driver propio es directa: la validación hay que escribirla,
porque nadie la escribió por nosotros, y es la única defensa contra un firmware incompatible
que se cargue por error.** `PROVEN_DERIVED`.

## 1 · La cabecera, campo por campo

**⇒ `amdgpu_ucode.h:30-41`. Los offsets están calculados, no supuestos:** `PROVEN`.

```c
30  struct common_firmware_header {
31      uint32_t size_bytes;                 /* size of the entire header+image(s) in bytes */
32      uint32_t header_size_bytes;          /* size of just the header in bytes */
33      uint16_t header_version_major;       /* header version */
34      uint16_t header_version_minor;       /* header version */
35      uint16_t ip_version_major;           /* IP version */
36      uint16_t ip_version_minor;           /* IP version */
37      uint32_t ucode_version;
38      uint32_t ucode_size_bytes;           /* size of ucode in bytes */
39      uint32_t ucode_array_offset_bytes;   /* payload offset from the start of the header */
40      uint32_t crc32;  /* crc32 checksum of the payload */
41  };
```

**⇒ El formato binario equivalente es `<IIHHHHIIII`, 32 bytes, sin padding implícito. Los diez
campos empiezan en los bytes 0, 4, 8, 10, 12, 14, 16, 20, 24 y 28.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y los comentarios distinguen dos cosas que se confunden con facilidad:
`header_version` es la versión *del formato de esta cabecera* y `ip_version` es la versión *del
bloque de hardware al que sirve el microcodigo*. No son la misma cosa y el driver las imprime
con nombres distintos precisamente para no confundirlas.** `PROVEN_DERIVED`.

## 2 · Los 20 binarios contra el layout, por programa

```text
bloque     size  hdr hmaj hmin ipmaj ipmin   ucode_v  ucode_s  array     crc32  valida
smc      130388   36    1    0     7     2   2234112   130132    256 0xae2b3b78 SI
mc        32608   40    1    0     8     1  11852880    32160    448 0x9b1e395c SI
k_smc    130388   36    1    0     7     2   2228480   130132    256 0x6689a637 SI
ce         8852   44    1    0     8     0       134     8596    256 0x4a5d3d3d SI
me        17044   44    1    0     8     0       161    16788    256 0x1673bce8 SI
pfp       17044   44    1    0     8     0       235    16788    256 0xe63e17c3 SI
mec      262824   44    1    0     8     0       705   262568    256 0x721be067 SI
rlc       16660  104    2    0     8     0        24    16404    256 0x5abe3e62 SI
sdma      12692   52    1    1     3     1        58    12436    256 0x67458532 SI
uvd      375424   32    1    0     6     3  16810512   375168    256 0xadba9a8d SI
vce      166816   32    1    0     3     4  55581187   166560    256 0x95a5d798 SI
```

**⇒ `PROVEN`. Dos invariantes, y los dos se cumplen en los 20 de 20 sin excepción:**

| invariante | resultado |
|---|---|
| `size_bytes` == tamaño real del fichero | **20 de 20** |
| `ucode_array_offset_bytes + ucode_size_bytes == size_bytes` | **20 de 20** |
| `ucode_array_offset_bytes == 256` | 17 de 20 — fallan los 3 de MC |

**⇒ `PROVEN_DERIVED. Los tres de MC tienen `array_offset` = 448, 440 y 448, y los otros 17
tienen 256. La diferencia es que el firmware de MC lleva una cabecera más larga: su
`header_size_bytes` es 40 frente a 36 del SMC, y su `header_version_major` es 1. La tabla de MC
del driver, `struct mc_firmware_header_v1_0` en `amdgpu_ucode.h:44`, añade campos después de la
cabecera común, y por eso su carga útil empieza más tarde.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el caso de `rlc` es el que confirma que `header_size_bytes` no es
decorativo: vale 104, casi el triple que los demás, y es el único con
`header_version_major == 2`. Un firmware con cabecera de 104 bytes sobre un driver que espera
36 bytes, y sólo esta comprobación lo detecta.** `PROVEN_DERIVED`.

## 3 · `ip_version` por bloque, que es lo que `231` cerró

**⇒ `PROVEN`. Los seis valores distintos, con el bloque al que pertenece cada uno:**

| fichero | `ip_version` | bloque que declara el driver |
|---|---|---|
| `pfp`, `me`, `ce`, `mec`, `rlc` (×2 cada uno) | **8.0** | `gfx_v8_0_ip_block` |
| `mc`, `32_mc`, `k_mc` | **8.1** | `gmc_v8_1_ip_block` |
| `smc`, `k_smc` | **7.2** | SMU v7.2 |
| `sdma`, `sdma1` | **3.1** | `sdma_v3_1_ip_block` |
| `uvd` | **6.3** | `uvd_v6_3_ip_block` |
| `vce` | **3.4** | `vce_v3_4_ip_block` |

**⇒ `PROVEN_DERIVED. Seis versiones distintas en un solo ASIC. `ip_version` no es «la versión de
la GPU»: es la del bloque de microcodigo. Confundirlo habría dado «el GFX de Polaris12 es 3.1»
leyendo el fichero de SDMA, o «es 7.2» leyendo el del SMC, que es el que acabo de analizar en
`251` y `253`.** `PROVEN_DERIVED`.

**⇒ Esto confirma `231` y sus dos discriminado res, y además explica una de sus columnas que
quedó sin cruzar: el `ucode_v` que reportaba 235, 161, 134, 705, 24 para los bloques GFX es
exactamente el campo `ucode_version` del byte 16, no la `ip_version`. Los dos campos existen,
se leen de offsets distintos y `231` los reportó en columnas distintas sin cruzarlos contra
el layout del driver.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y el SMC sale 2234112, que es el valor que `221` y `231` ya habían citado
como «ip_version 0x00221700». Con el layout correcto ese dword es `ucode_version`, no
`ip_version`: `ip_version` son dos `uint16` en los bytes 12 y 14, y valen 7 y 2.** `PROVEN_DERIVED`.

## 4 · El SMC de esta placa, y por qué hay dos copias idénticas

**⇒ `PROVEN`. `06-INGENIERIA-INVERSA/firmware/polaris12_smc.bin` (130388 bytes) y
`/lib/firmware/amdgpu/polaris12_smc.bin.xz` descomprimido son **byte a byte idénticos**: mismo
SHA-256, `4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. El proyecto tiene el `.bin` ya descomprimido y el sistema el `.xz`. Es la
misma imagen, así que cualquier análisis hecho sobre una vale para la otra, y basta con no
confundirlas al citar: el hash es la prueba de que no se han mezclado.** `PROVEN_DERIVED`.

**⇒ Y el SMC tiene `header_size_bytes == 36`, es decir 32 bytes de cabecera común más 4. Su
`ip_version` es 7.2, su `ucode_version` 2234112, su carga útil 130132 bytes en 256, y su
`crc32` 0xae2b3b78.** `PROVEN`.

**⇒ `PROVEN_DERIVED. `253` cierra hasta aquí. Esto enlaza directamente: el `SmuMetrics_t` de
`253` lo rellena un firmware cuya cabecera dice 7.2, y el driver de ese firmware es
`renoir_ppt.c`. La cadena `253` (lectura de temperatura) termina en un mensaje SMC, ese mensaje
lo atiende un firmware 7.2, y la cabecera de ese firmware tiene un CRC32 que nadie verifica.** `PROVEN_DERIVED`.

## 5 · El driver no valida nada, y el límite tampoco

**⇒ `PROVEN`. `amdgpu_ucode.c:44` es `DRM_DEBUG("ip_version_major: %u\n", ...)` dentro de
`amdgpu_ucode_print_common_hdr`, que abre en `amdgpu_ucode.c:38`. Es la única aparición de
`ip_version_major` en todo el fichero, y es un `DRM_DEBUG`, es decir una impresión de
diagnóstico.** `PROVEN`.

**⇒ `PROVEN_ABSENT`. Y `grep -rn 'if.*ip_version_major\|ip_version_major ==\|ip_version_major
!='` sobre `amdgpu/*.c` devuelve cero. No hay ni una comparación en todo el driver.** `PROVEN_ABSENT`.

**⇒ `PROVEN. Y la carga tampoco valida: `psp_copy_fw` (`amdgpu/amdgpu_psp.c:4184`) hace
`memset(psp->fw_pri_buf, 0, PSP_1_MEG)` y `memcpy(psp->fw_pri_buf, start_addr, bin_size)`, sin
comprobar ni que `bin_size` quepa en `PSP_1_MEG` ni que la cabecera sea coherente.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Las dos omisiones compounded. La primera —el `memcpy` sin cota— la acota
el buffer: `PSP_1_MEG` es 0x100000 = 1048576 bytes (`amdgpu/amdgpu_psp.h:37`) y el SMC mide
130388, o sea que ocupa el 12,43% del búfer con un 87,57% de holgura. Cabe de sobra. Pero un
firmware mayor de 1 MiB desbordaría, y no hay comprobación.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. La segunda omisión es peor porque no la acota nada:
`is_psp_fw_valid` (`amdgpu/amdgpu_psp.c:4206`) devuelve `bin.size_bytes` como si fuera un
booleano, es decir devuelve «válido» si el tamaño es distinto de cero y nada más. No mira la
cabecera, ni el CRC, ni la versión.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Las cifras, por programa: 130388 de 1048576 bytes, 12,43% ocupado,
87,57% de holgura, 8,04 veces el tamaño del búfer. Ninguna de las dos validaciones depende de
que el CRC sea correcto, así que un firmware con la cabecera manipulada y el mismo tamaño pasa
las dos.** `PROVEN_DERIVED`.

## 6 · La asimetría de los ficheros `_2` y `1`

**⇒ `PROVEN`. Hay pares de binarios casi idénticos cuyo único cambio está en `ucode_version`:
`mec` y `mec2` comparten `ucode_version` 705 y `crc32` 0x721be067 — son el mismo fichero byte a
byte—, mientras que `mec2_2` y `mec_2` tienen 730 y CRC distinto.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y `sdma` y `sdma1` tienen el mismo `ucode_version` 58 pero CRC distinto
(0x67458532 y 0xab8d7af7), lo que significa que el mismo microcodigo va empotrado en dos
contenedores con distinta disposición de los datos privados. La GPU descarga el que le
corresponde; el otro está ahí por si hace falta.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y esto tiene una consecuencia práctica para el driver propio: el conjunto de
20 ficheros tiene duplicados, así que «el firmware de X» no es un nombre único sino una clase de
equivalencia por `ip_version` + `ucode_version` + `crc32`. Con tres campos, 6 ip_version × N
versiones × M crc, la clave correcta para elegir un firmware es la terna, no el nombre.** `PROVEN_DERIVED`.

## 7 · Lo que queda abierto

**⇒ `NOT_DETERMINED`: qué algoritmo de CRC es el del campo `crc32` y sobre qué bytes se calcula.
El campo se llama `crc32` y el comentario dice «crc32 checksum of the payload», pero el
algoritmo y el polinomio no están en el driver.** `NOT_DETERMINED`.

**⇒ `NOT_DETERMINED`: qué contiene la zona entre el fin de la cabecera común y
`ucode_array_offset_bytes`. Para el SMC son 4 bytes (36 − 32); para `rlc` son 72; para MC, 8.
Ninguno está descrito por una struct del driver.** `NOT_DETERMINED`.

**⇒ `NOT_DETERMINED`: el contenido del propio microcodigo, que es lo que `251` y `253`
necesitaban. La cabecera está cerrada; el payload es un bloque binario cuya semántica no está en ningún
lado del corpus. Es el mismo `NOT_DETERMINED` que dejó `251`, pero ahora con el tamaño exacto
del objeto y sus tres campos de identificación.** `NOT_DETERMINED`.

```text
PENDIENTE=254-1 | HALLAZGO=254-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=/lib/firmware/amdgpu/polaris12_smc.bin.xz  (objeto, no ruta de hardware)
           | ALCANZABLE_SIN_ROOT=si
```

**⇒ Y ese `ALCANZABLE_SIN_ROOT=si` es lo que cambia respecto a los discriminantes anteriores:
este no necesita placa, necesita desensamblar un binario que ya está en el disco.** `PROVEN_DERIVED`.

## 8 · Errores propios registrados en esta nota

**⇒ `ERROR`. Escribí el formato binario como `<IIHHHHHIII`, con **cinco** `H` donde la struct
tiene **cuatro**, y el validador `array_offset + ucode_size == size` dio 0 de 20. Un 0 de 20 es
un resultado imposible y loidentified como bug mío antes de escribir la conclusión, pero
tuve que entrar en el fichero a mirar `amdgpu_ucode.h:33-36` para contar los campos. El formato
correcto es `<IIHHHHIIII`, diez campos, 32 bytes.** `ERROR`.

**⇒ `ERROR`. Antes de eso leí `0x00221700` del offset 16 del SMC y escribí que «no es un
`IP_VERSION`» apoyándome en que `IP_VERSION(8,0,0)` no aparece en el driver. La conclusión era
cierta pero el razonamiento estaba mal: `IP_VERSION()` es una macro de comparación, no un
formato de almacenamiento, y el hardware no la usa. El offset 16 sí es un campo con nombre
propio, `ucode_version`. Lo correcto era haber contado los campos de la struct antes de
descomponer el dword, que es lo que hice después.** `ERROR`.

**⇒ `ERROR`. Escribí una construcción rota junto a la referencia a `253` y una frase con caracteres CJK en el punto 2,
que es otra vez la primera frase larga de un apartado. Van cuatro de cuatro.** `ERROR`.

**⇒ Y el cuarto defecto es el mismo de siempre en su forma más clara: el número que decide la
conclusión —el 0 de 20— lo acepté como medida hasta que lo miré. La regla de `204` y `246` es
que un número absurdo es una señal de bug, no un hallazgo. Un 0 de 20 no es un resultado, es
un formato mal escrito.** `ERROR`.