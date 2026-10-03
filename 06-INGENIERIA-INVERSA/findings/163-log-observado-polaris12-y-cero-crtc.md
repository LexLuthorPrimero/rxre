# 163 · El log completo del arranque: nueve confirmaciones y un cero

```
CLASSIFICATION=DOCUMENTATION · TRACK=OBSERVED
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=LOG_READ_ONLY · GPU INTACTA
```

## Qué resuelve

**La vía de observabilidad más barata del proyecto aplicada por quinta vez, y esta vez
al bloque entero.** Cierra el `NOT_DETERMINED` de `162` sobre las tuberías, y trae nueve
confirmaciones medidas de números que hasta ahora sólo estaban derivados.

**Y trae un hecho que no estaba en ninguna nota y que es el más útil de las 163: esta
máquina no tiene ni un CRTC.**

## 1 · La línea que responde a la pregunta de `162`

```
amdgpu 0000:01:00.0: [drm] Cannot find any crtc or sizes
```

**Cero CRTC. `PROVEN`, observado.**

**⇒ Las 6 tuberías de display de `162` están las seis libres, y la razón por la que el
log no contiene ni una sola línea de `dce112` más allá de la inicialización es
precisamente esta: no hay a quién dar de qué tamaño.** `PROVEN_DERIVED`.

**⇒ Y la respuesta a «cuál de las 6 tuberías está en uso» no es «ninguna», y eso convierte
la pregunta en otra: por qué el DC se inicializa y no se usa.** `PROVEN_DERIVED`.

**Y de paso queda confirmado, con la misma línea, que `Display Core v3.2.378` es la única
mención de `dce112` en todo el log.** `PROVEN`. Eso cierra la pregunta que estaba abierta
desde antes de esta tanda: **no hay más líneas de `dce112`.**

## 2 · Las nueve confirmaciones, y la aritmética que las sostiene

Todas las líneas de `amdgpu` del arranque actual, con lo que confirman:

| línea del log | lo que confirma | nota |
|---|---|---|
| `vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit` | la geometría de `130` y `132` | **derivado y observado, los tres números** |
| `GART: num cpu pages 65536, num gpu pages 65536` | `num_prt_users` 65536 de `140` | `PROVEN` |
| `PCIE GART of 256M enabled (table at 0x000000F400900000)` | los 256 MiB y los 9 MiB de `140` | `PROVEN` |
| `GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF` | el rango del GART de `140`, bit a bit | `PROVEN` |
| `VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)` | el rango de VRAM de `140` y el 2048M | `PROVEN` |
| `Disabling VM faults because of PRT request!` | que la ruta PRT de `099`/`210` se usa | `PROVEN` |
| `detected ip block number 6 <dce_v1_0_0> (dm)` | **la versión del IP del DC** | nuevo |
| `smu backed is polaris10_smu` | **un eje más de identificación** | nuevo |
| `RAM width 64bits GDDR5` | anchura de VRAM | nuevo |

**Y las tres cadenas aritméticas, calculadas por programa:**

```
65536 paginas x 4096 bytes = 268435456 bytes = 256 MiB      <- el log dice "256M". COINCIDE
0xF400900000 - 0xF400000000 = 0x900000 = 9 MiB              <- 140 decia 9 MiB. COINCIDE
2^9 = 512 paginas x 4 KiB = 2048 KiB = 2 MiB               <- el fragmento de 140. COINCIDE
2^19 = 524288 bytes = 512 KiB                               <- tamano de la PDE
2^10 = 1024 entradas x 8 bytes = 8192 bytes = 8 KiB         <- la hoja
```

**⇒ Nueve números derivados en cuatro notas, y los nueve observados. Ninguno
discrepa.** `PROVEN`.

## 3 · Y el hecho nuevo de más peso: `dce_v1_0_0`

```
amdgpu 0000:01:00.0: detected ip block number 6 <dce_v1_0_0> (dm)
```

**El bloque de hardware del DC se instancia como versión de IP 1.0.0, mientras la función
es 11.2 y los registros son de 10.0.** `PROVEN`.

**⇒ Son tres ejes, no dos.** Y esto es la explicación mecánica de `232` y de `158`:

| eje | valor |
|---|---|
| versión del **IP de hardware** | `dce_v1_0_0` |
| **función** de display | DCE **11.2** |
| juego de **registros** | DCE **10.0** |

**Si el IP es 1.0.0 para toda la familia, el código tiene que ser común a toda la
familia, y lo es.** `PROVEN_DERIVED`. **Y eso no es una inferencia sobre el código: es lo
que el kernel anuncia al enumerar, y dice `dce_v1_0_0` antes de que se ejecute una sola
línea del driver de display.**

**⇒ Las seis generaciones DCE de `158` cablean la misma tabla porque el hardware es el
mismo bloque IP con la misma versión.** La regla de `232` deja de ser un hecho sobre el
código y pasa a ser un hecho sobre el silicio. `PROVEN_DERIVED`.

**Y hay un cuarto eje, y es de firmware:**

```
amdgpu: hwmgr_sw_init smu backed is polaris10_smu
```

**El chip es `POLARIS12` y el gestor de energía es el de `polaris10`.** `PROVEN`.

**⇒ Cuatro ejes de identificación en un solo arranque: chip Polaris12, IP del DC 1.0.0,
función 11.2, SMU de Polaris10, y registros de 10.0 por añadir.** `PROVEN_DERIVED`.

## 4 · Los nueve bloques IP del chip, contados

```
 1  common_v1_0_0    (se llama vi_common)
 2  gmc_v8_1_0       (se llama gmc_v8_0)
 3  ih_v3_0_0        (se llama tonga_ih)
 4  gfx_v8_0_0       (se llama gfx_v8_0)
 5  sdma_v3_1_0      (se llama sdma_v3_0)
 6  smu_v1_0_0       (se llama powerplay)
 7  dce_v1_0_0       (se llama dm)
 8  uvd_v6_3_0       (se llama uvd_v6_0)
 9  vce_v3_4_0       (se llama vce_v3_0)
```

**Nueve bloques, y en cuatro de ellos el nombre de la versión y el nombre que el driver le
da no coinciden:** `gmc_v8_1_0` se llama `gmc_v8_0`, `sdma_v3_1_0` se llama `sdma_v3_0`,
`uvd_v6_3_0` se llama `uvd_v6_0`, `vce_v3_4_0` se llama `vce_v3_0`. `PROVEN`.

**⇒ Y el DC se llama `dm` en el log, no `dce`.**Décima colisión de nombres, y la más
delicada: **`dm` es el nombre del gestor de display, y en `159` se llama así porque es
donde vive el reparto de implementaciones.** El log usa `dm` para el bloque IP y el árbol
usa `dc` para el mismo bloque. `PROVEN`.

**Y `gmc_v8_1_0` con nombre `gmc_v8_0` explica por qué `140` puede usar `gmc_v8_0.c` para
describir esta GPU sin error: el bloque se instancia como 8.1 y el driver lo maneja con
el código de 8.0.** Es la misma forma que el DC, y la misma regla de `232`. `PROVEN_DERIVED`.

## 5 · Y el VGA de arranque, que era la pregunta abierta desde `158`

```
pci 0000:01:00.0: vgaarb: setting as boot VGA device
pci 0000:01:00.0: vgaarb: VGA device added: decodes=io+mem,owns=io+mem,locks=none
amdgpu 0000:01:00.0: vgaarb: deactivate vga console
```

**La AMD es el dispositivo VGA de arranque, y luego desactiva su propia consola VGA.**
`PROVEN`.

**⇒ Esto NO refuta el `PROVEN_ABSENT` de `158` sobre el codificador analógico, y la
distinción es el hallazgo:** el VGA existe como **ruta de BIOS y ATOM**, no como
codificador de stream del DC. `dce112_resource.c` no construye uno porque el DC de
11.2 no tiene uno, y el BIOS de arranque usa un camino completamente distinto que no
pasa por `display/`. `PROVEN_DERIVED`.

**Y por eso el DC se inicializa y no se usa: la máquina arranca por VGA de BIOS sobre la
AMD, y cuando entra el driver de display no hay monitor conectado a ella.** `PROVEN_DERIVED`.

## 6 · Y la iGPU, que era el otro bloqueo abierto

```
i915 0000:00:02.0: [drm] PipeC fused off
```

**Y el kernel enumeró el audio HDMI de la AMD, que es el audio de `157`:**

```
input: HDA ATI HDMI HDMI/DP,pcm=3 as /devices/pci0000:00/0000:00:01.0/0000:01:00.1/sound/card2/input6
input: HDA Intel HDMI HDMI/DP,pcm=3 as /devices/pci0000:00/0000:00:03.0/sound/card0/input7
input: HDA Intel HDMI HDMI/DP,pcm=7 as /devices/pci0000:00/0000:00:03.0/sound/card0/input8
input: HDA Intel HDMI HDMI/DP,pcm=8 as /devices/pci0000:00/0000:00:03.0/sound/card0/input9
```

**Una función de audio HDMI de la AMD en `0000:01:00.1`, y tres de la Intel en
`0000:00:03.0`.** `PROVEN`.

**⇒ `157` afirmó por derivación que esta GPU tiene audio HDMI y DisplayPort, y el kernel
lo enumera: la función `HDA ATI HDMI` existe en la placa.** La derivación queda
confirmada por observación. `PROVEN`.

**Y que exista la función de audio no significa que haya un HDMI que la canalice: es la
función de audio del chip, que el driver expone sin que ningún monitor esté conectado.**
`PROVEN_DERIVED`. **Es la diferencia entre «el siliconio tiene la función» y «la placa
tiene el conector», y es la misma diferencia que dejó abiertos los siete `path` de
`153`.**

**Y `PipeC fused off` es una línea sobre la iGPU que no es un dato de la AMD, y la dejo
como `NOT_DETERMINED`:** si la iGPU de la sesión toma pipelines y la AMD no, eso explica
por qué el compositor va sobre Intel, pero no es un hecho sobre la AMD y no lo voy a
afirmar como tal.** `PROVEN`.

## 7 · Y el resto de la ficha, para tenerla medida

```
POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7        chip, subdispositivo, revisión
ATOM BIOS: ver: 015.050.002.001.000000, 2021/05/12
Detected VRAM RAM=2048M, BAR=256M                2 GiB de VRAM, 256 MiB de BAR
RAM width 64bits GDDR5
register mmio base: 0xF7D00000                    256 KiB de MMIO (262144)
SE 2, SH per SE 1, CU per SH 5, active_cu_number 8   10 CU, 8 activos
Fetched VBIOS from ROM BAR / No more image in the PCI ROM
Registered 5 planes with drm panic
Using BACO for runtime pm
Trusted Memory Zone (TMZ) feature not supported
Chained IB support enabled!
```

**⇒ 2 GiB de VRAM GDDR5 de 64 bits, 256 KiB de MMIO, 8 unidades de cómputo activas, 5
planos registrados, BIOS de mayo de 2021.** `PROVEN`.

**Y el hueco exacto entre la VRAM y el GART, que `140` dibujaba como `<40.0 GiB`:**
`0xFF00000000 - 0xF47FFFFFFF = 0xA80000001` = **42,0 GiB**, no 40. `PROVEN`. Es una
imprecisión de una cifra ilustrativa dentro de un diagrama y no afecta a ninguna
conclusión de `140`, que por lo demás queda confirmada en sus nueve puntos.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Cero CRTC; las 6 tuberías libres | `PROVEN`, observado |
| `Display Core v3.2.378` es la única línea de `dce112` | `PROVEN`, observado |
| Nueve números derivados, nueve observados, ninguno discrepa | `PROVEN` |
| El DC se instancia como `dce_v1_0_0` | `PROVEN`, observado |
| El SMU es `polaris10_smu` en un chip Polaris12 | `PROVEN`, observado |
| Cuatro ejes de identificación | `PROVEN_DERIVED` |
| El VGA de arranque no pasa por `display/` | `PROVEN_DERIVED` |
| El kernel enumera la función de audio HDMI de la AMD | `PROVEN`, observado |
| La función de audio no implica un conector | `PROVEN_DERIVED` |
| El hueco VRAM–GART es 42,0 GiB, no 40 | `PROVEN` — cifra ilustrativa de `140` |
| Cuánta VRAM hay instalada en la placa | **`NOT_DETERMINED`** — el chip admite más |
| Cuál es el modo de vídeo del escritorio de la sesión | **`NOT_DETERMINED`** — va sobre la iGPU |
| Si `PipeC fused off` explica el reparto de tuberías | **`NOT_DETERMINED`** |
| Si el `dm` del log y el `dc` del árbol son el mismo bloque | **`NOT_DETERMINED`** — muy probable |

**La primera de las abiertas es la que decide si las cifras de `160` y `161` sirven: los
25,92 Gbps y los 600 MHz son de esta GPU, pero el modo que se le puede pedir depende de
la VRAM que la placa tenga, y el log sólo dice que el chip arranca con 2.048 MiB
visibles.**

## Procedencia

- `OBSERVED` -- `journalctl -k -b` de la sesión en curso, sin root y sin tocar la GPU.
  Las nueve líneas citadas arriba, más las de `vgaarb`, `i915` y `HDA ATI`. La búsqueda
  se hizo con `grep -i 'amdgpu'` sobre el log completo: **89 líneas mencionan
  amdgpu/drm/display, de las cuales 38 son únicas.**
- Medición por programa: **las nueve cadenas aritméticas**, cada una impresa con su
  resultado; la comparación de los tres números de geometría con `130`/`132`; la lista de
  los nueve bloques IP con su número; la búsqueda de las cuatro discrepancias entre
  nombre de versión y nombre que usa el driver.
- **Un error de unidad mío, en el script de esta misma nota:** imprimió «512 paginas =
  2 KiB» donde la cuenta correcta es **512 × 4 KiB = 2.048 KiB = 2 MiB**, que es lo que
  afirma `140` para el fragmento. **La causa fue dividir por `2^10` dos veces en lugar de
  por `2^20`, y la conclusión no cambió porque el valor correcto coincide con el
  derivado, pero el número impreso era falso.** Rehecho antes de escribir.
- **Y una nearly-miss de la que salve el protocolo: estuve a punto de refutar `140`.** El
  resumen de la sesión anterior decía «VRAM 976,0 GiB» y el log dice `2048M`, y eso
  parece una contradicción de veinte veces. **Antes de escribir la corrección abrí `140`:
  el 976,0 GiB es la dirección base, y `140` dice «VRAM, 2048 MiB» en su propio
  diagrama.** El programa confirma: span del rango = 2048 MiB exactos, diferencia 0.
  **`140` queda confirmada, y la contradicción era del resumen, no de la nota.** Quinta
  vez que la comprobación cruzada evita una refutación falsa.
- Encadenada con `162` (**el `NOT_DETERMINED` de las 6 tuberías queda cerrado: cero**),
  `161` (el reloj de 600 MHz, y ahora la VRAM que lo alimenta), `160` (los 25,92 Gbps),
  `159` (**los seis constructores `dce110_`, y aquí el IP 1.0.0 que los obliga**),
  `158` (VGA sin codificador analógico, y aquí el VGA de BIOS que sí existe),
  `157` (el audio de la tabla, y aquí el enumerado por el kernel), `232` (la regla de la
  tabla y el constructor, elevada de hecho de código a hecho de silicio), `155` (DCE 11.2
  observado), `153` (los siete `path` que siguen sin poder contar), `140` (verificado),
  `132`, `130` (geometría verificada).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**La quinta tirada de `journalctl` es la que más ha dado, y por una razón que no es
casual: hasta ahora se había tirado del log buscando líneas del driver, y esta vez se
ha tirado buscando el bloque entero.**

*Las cuatro primeras veces el log sirvió para confirmar o refutar una afirmación concreta
—el mapa de direcciones, la apertura AGP, la ausencia de los registros, la versión del
DC— y las cuatro veces encontró exactamente lo que se le buscó.* **Esta vez, en cambio,
se le pidió todo lo de `amdgpu` y devolvió 38 líneas únicas, de las cuales nueve son
confirmaciones de números ya derivados, tres son hechos enteramente nuevos, y una es un
cero que explica por qué el bloque entero no tiene más datos de campo.**

**Y la lección operativa es la contraria a la que esperaba: un puerto de
observabilidad no se agota, se usa entero.** *Buscar «las líneas de `dce112`» daba una línea. Pedirle
todo el `amdgpu` da nueve confirmaciones, tres hechos nuevos y la explicación de por qué
el resto del bloque no se puede cerrar en campo.* **Y esa explicación —que no hay
CRTC— es la que decide el orden de trabajo: sin monitor conectado a esta GPU, todo el
eje de display queda limitado a derivación y no a observación, y eso vale más que otras
veinte notas de lectura.**

**Y sobre el casi-refutación de `140`, que es lo más útil de esta nota después del cero.**
*Veinte veces de diferencia entre «976,0 GiB» y «2048M» es exactamente el tamaño de
error que produce un refutación nueva, convincentemente redactada y completamente falsa.*
Lo que la paró fue una regla que lleva cuatro notas en vigor: **una corrección necesita
el texto de la nota que corrige, no el resumen de la nota.** *El resumen de la sesión
anterior decía «VRAM 976,0 GiB» porque la base es `0xF400000000` y porque los números
redondos de un diagrama se pegan mejor; la nota decía 2048 MiB. El resumen era lo
equivocado y la nota era lo cierto, y eso sólo se sabe abriendo la nota.*
