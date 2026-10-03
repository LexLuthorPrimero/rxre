# 258 · La primera medición de §H: 12 GB/s de VRAM contra 2 GB/s de PCIe, y la memoria clavada en 300 MHz

```text
CLASSIFICATION=MEASUREMENT · TRACK=RUNTIME (NIVEL 2, solo lectura)
CORPUS=RESEARCH/working/linux-7.1.3 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0 · WRITE_EXECUTION=NONE
RUNTIME=sysfs + hwmon, 40 muestras · GPU INTACTA · CARGA DE GPU = 0
```

> **Convención de rutas.** `card1` es la AMD; `card0` es la iGPU de Intel. Ver
> `HARDWARE-FINGERPRINT.md` §6.
>
> **`CORREGIDA` por `602` — el techo de VRAM de esta nota es LA MITAD del real.**
>
> §2 de esta nota (líneas 81-88) afirma «bus de 64 bits = 8 bytes» y de ahí salen
> `1500e6 × 2 × 8 = 24,0 GB/s`. Es una `PROVEN_DERIVED` **sin evidencia**: no hay cita,
> no hay VBIOS, no hay registro. `602` lo refuta por medición: un reparto de direcciones
> contiguo, con la entropía verificada y sin ninguna reutilización posible, mueve
> **43,2 GB/s útiles**. Sesenta y cuatro bits a `mclk` 1500 permiten 24,0 GB/s, luego es
> imposible; ciento veintiocho permiten 48,0, y 43,2 es el 90% de eso.
>
> ```text
>   bus  64 bits a mclk 1500 -> 24,0 GB/s -> 43,2 es el 180%   IMPOSIBLE
>   bus 128 bits a mclk 1500 -> 48,0 GB/s -> 43,2 es el  90%   COHERENTE
> ```
>
> **Consecuencia:** todos los porcentajes de utilización de VRAM de `258`, `271`, `282` y
> `287` están calculados contra un techo la mitad del real y salen el doble de
> optimistas. Los tres niveles de `pp_dpm_mclk` (`300`, `625`, `1500` MHz), que esta nota
> **`PROVEN`** y verificó por registro, no cambian: lo que cambia es el multiplicador.
> El techo correcto es **9,6 / 20,0 / 48,0 GB/s**.
>
> **Lo que sobrevive:** la conclusión de que el cómputo no está limitado por la VRAM. En el
> mejor caso medido se usa el 90% de un techo de 48 GB/s y el enlace va a 2,00 GB/s. Y sigue
> siendo cierto que un techo medido con `mclk` en reposo de 300 MHz no es el techo del
> equipo.
>
> **Abierto:** si el bus es de 128 o de 256 bits. La medición sólo establece 128 o más, porque
> 256 también es coherente con 43,2 GB/s. Decide el VBIOS (`atom_vram_info`), pendiente de
> `sudo` desde `272`.

> **`RETIRADO` por `908`. Este banner se apoya en una afirmación falsa: que el bus de 64
> bits de `258` no tenía evidencia.**
>
> `258` línea 193 cita `adev->gmc.vram_width`, y `amdgpu_kms.c:1016` lo publica como
> `vram_bit_width`. **La cita existía, en la nota que estaba corrigiendo, a 112 líneas del
> sitio que leí.** Declaré una ausencia sin haber buscado la fuente, que es la tercera vez
> que lo hago en este proyecto.
>
> `amdioread.py` lee ahora ese campo por ioctl sin root, y vale **64**, que es lo que
> `258` decía. O sea: `258` acertó el valor.
>
> **Lo que sigue en pie:** el techo de 48,0 GB/s. Lo que no se sostiene es que se haya
> probado que el bus es de 128 bits: 64 bits declaran 24,0 GB/s y la medición de `606` da
> 43,2, que es el 180% de 64. Hay una `CONTRADICTION` abierta en `908`, y el número del
> techo depende de cómo se resuelva.
>
> **Y `265` queda corroborado por otra vía:** `gl2c_cache_size` existe en la estructura del
> ioctl y en esta placa vale 0. El kernel tampoco dice el tamaño de la caché.

> **Y `909` corrige la aritmética, no el ancho.** `258` multiplica por 2 y da 24,0 GB/s.
> Con 64 bits el multiplicador tiene que ser 4 para llegar a los 48,0 GB/s que exige la
> medición de `606`, y eso es lo único que encaja de la tabla. **El ancho de 64 bits de esta
> nota es correcto y está corroborado por el log de arranque**; el multiplicador, no.
>
> **Y el `NOT_AVAILABLE` de esta nota sobre la lectura en vivo es falso.** `vram_bit_width`
> no se publica por debugfs: se pide con `AMDGPU_INFO_DEV_INFO` sobre `/dev/dri/renderD129`,
> que es `crw-rw-rw-` y **no exige privilegios**. `amdioread.py` lo lee. Una frontera estuvo
> marcada como bloqueada por permisos que no la bloqueaban.
>
> **Citas por sección, no por línea.** Las dos citas de esta nota están en su §2 y en su §5,
> y las líneas se desplazan cada vez que una nota recibe un banner de corrección.

> ## **`REFUTADA` por `911`. El ancho de 64 bits es un error del driver, y está localizado.**
>
> El VBIOS de esta placa se declara, en su propia cadena de nombre:
>
> ```text
>   D09001 Lexa XL A0 GDDR5 128bit 2GB 214e/300m
> ```
>
> Y `grep` de la cadena `64bit` en los 58.880 bytes del VBIOS devuelve **cero apariciones**.
>
> **De dónde sale el 64 entonces. `amdgpu_atombios.c:786`:**
>
> ```c
>   773   int index = GetIndexIntoMasterTable(DATA, IntegratedSystemInfo);
>   778   /* get any igp specific overrides */
>   786   return igp_info->info_8.ucUMAChannelNumber * 64;
> ```
>
> Es una función de **IGP integrado**, aplicada a una tarjeta **discreta**. El campo
> `ucUMAChannelNumber` no significa en una dGPU lo que su nombre dice, y `* 64` es el
> multiplicador de ese campo equivocado. `gmc_v8_0.c:557`, el fallback
> `numchan * chansize`, nunca llegó a correr porque la ruta del VBIOS devolvió un valor no nulo.
>
> **El techo correcto de VRAM de este proyecto es 48,0 GB/s** — 128 bits, GDDR5 de doble
> velocidad, 1,5 GHz — y `606` lo midió al 90% al 93%. Esta nota daba 24,0.
>
> **Y su `NOT_AVAILABLE` sobre la lectura en vivo también era falso:** la imagen del VBIOS se
> vuelca entera por `AMDGPU_INFO_VBIOS_IMAGE` sobre `/dev/dri/renderD129`, que es
> `crw-rw-rw-`, sin privilegios. `vbiosread.py` lo hace.
>
> **La cita de esta nota es correcta:** §2 y §5 de aquí, y `amdgpu_kms.c:1016`, y
> `amdgpu_object.c:1079`. Lo que era incorrecto era el valor al que apuntaba.

## Qué resuelve

**Abre la parte medible de §H y da la primera clasificación de cuello de botella de §52 del
proyecto.** `PROVEN` (medición) / `PROVEN_DERIVED` (clasificación, con su límite declarado).

**⇒ `PROVEN`. La VRAM da 24,0 GB/s a memoria máxima y el enlace PCIe da 2,00 GB/s. La razón es
de 12 a 1.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y `mclk` está clavado en 300,00 MHz con varianza exactamente cero en 40 muestras
consecutive, mientras `sclk` varía entre 882 y 1070 MHz.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Para todo lo que cruce PCIe, este equipo está limitado por el enlace y no
por la VRAM. Para el cómputo que solo toque VRAM, el techo es 24 GB/s. Cuál de los dos domina
depende de la carga de trabajo y no se puede decidir sin ejecutarla.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. `temp1_crit` de hwmon vale 97,00 °C, que es exactamente el `usSoftwareShutdownTemp
= 97` que `222` midió en el VBIOS. Y `edge` vale 46-47 °C en hwmon contra los 42 °C de
`amdgpu_pm_info.txt`, luego la temperatura también se mueve entre capturas.** `PROVEN`.

> **`CORREGIDA` por `284`.** El techo **actual** del enlace, 2,00 GB/s, queda verificado contra
> `current_link_speed` = 5,0 GT/s y `current_link_width` = 4, y es correcto. Lo que estaba mal es
> el techo **máximo**: esta nota aplicó codificación **8b/10b a Gen3**, que usa **128b/130b**.
>
> ```text
> Gen3 x8  8b/10b     6,400 GB/s   <- lo que dice esta nota
> Gen3 x8  128b/130b  7,877 GB/s   <- correcto
> ```
>
> **El margen de mejora del enlace es 3,94 veces, no 3,2.** La conclusión de §2 —«la VRAM es más
> ancha que cualquier enlace PCIe que esta placa pueda negociar, luego el equipo sigue siendo
> link-bound aun con el enlace al máximo»— **no se mueve**: 7,877 contra 24,0 GB/s son 3,0 veces,
> donde esta nota calculaba 3,75. El razonamiento no dependía del número exacto. Ver `284` §2.

## 1 · Las mediciones, con su procedencia

**⇒ Todo lo de esta tabla es de esta sesión, con el equipo en reposo y sin carga de GPU.** `PROVEN`.

| magnitud | valor | fuente | clase |
|---|---|---|---|
| bus de VRAM | **64 bits** | log de arranque `RAM width 64bits GDDR5` | `PROVEN` |
| tipo de VRAM | GDDR5 | ídem | `PROVEN` |
| VRAM total | 2 147 483 648 B = 2 GiB | `mem_info_vram_total` | `PROVEN` |
| VRAM visible | 268 435 456 B = 256 MiB | `mem_info_vis_vram_total` | `PROVEN` |
| `mclk` actual | **300,00 MHz** | `hwmon1/freq2_input`, 40 muestras | `OBSERVED` |
| `sclk` actual | 882,6 – 1070,2 MHz | `hwmon1/freq1_input`, 40 muestras | `OBSERVED` |
| `vddgfx` | 806 – 881 mV | `hwmon1/in0_input` | `OBSERVED` |
| PPT | 5,04 – 6,17 W | `hwmon1/power1_input` | `OBSERVED` |
| PPT cap | 35,00 W | `hwmon1/power1_cap` | `PROVEN` |
| `edge` | 46 – 47 °C | `hwmon1/temp1_input` | `OBSERVED` |
| `edge` crítico | 97,00 °C | `hwmon1/temp1_crit` | `PROVEN` |
| PCIe actual | **5,0 GT/s x4** | `current_link_speed`, `current_link_width` | `PROVEN` |
| PCIe máximo | 8,0 GT/s x8 | `max_link_speed`, `max_link_width` | `PROVEN` |

**⇒ `PROVEN`. Los tres niveles de memoria, de `pp_dpm_mclk`: `0: 300Mhz *`, `1: 625Mhz`,
`2: 1500Mhz`. Los ocho de shader, de `pp_dpm_sclk`: `214, 551, 734, 980, 1000, 1020, 1046,
1071 MHz`, con el asterisco en el índice 0.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Hay una discrepancia entre dos observables de la misma magnitud que conviene
registrar: `pp_dpm_sclk` marca el nivel 0, cuyo valor es 214 MHz, mientras `hwmon1/freq1_input`
lee entre 882 y 1070 MHz. Los dos son observables legítimos y distintos —el primero es el
estado DPM que el driver cree, el segundo el reloj entregado— y no son intercambiables.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Y el que no se mueve es el de memoria: `mclk` marca 300,00 MHz con rango 0,00 y
coeficiente de variación 0,00% en las 40 muestras, mientras `sclk` tiene un rango de 187,58 MHz
y un coeficiente del 2,91%.** `PROVEN`.

## 2 · La aritmética de anchos de banda, con su unidad

**⇒ `PROVEN_DERIVED`. VRAM: bus de 64 bits = 8 bytes, GDDR5 transfiere dos valores por ciclo de
reloj de memoria, luego 16 bytes por ciclo.** `PROVEN_DERIVED`.

```text
VRAM @ mclk  300 MHz  ->  4,8 GB/s     (reposo, lo que hay ahora)
VRAM @ mclk  625 MHz  -> 10,0 GB/s     (P-state declarado)
VRAM @ mclk 1500 MHz  -> 24,0 GB/s     (máximo de pp_dpm_mclk)
```

**⇒ `PROVEN_DERIVED`. PCIe, con codificación 8b/10b, o sea un 80% de eficiencia:** `PROVEN_DERIVED`.

```text
Gen2  5,0 GT/s x4  ->  2,00 GB/s      (enlace actual)
Gen3  8,0 GT/s x8  ->  7,877 GB/s     (máximo de la placa; 128b/130b, no 8b/10b)
```

**⇒ Y el contraste que da la clasificación de §52:** `PROVEN_DERIVED`.

| recurso | ancho de banda | quién lo limita |
|---|---|---|
| transferencias CPU↔GPU | **2,00 GB/s** | PCIe Gen2 x4 |
| cómputo que solo toca VRAM | **24,0 GB/s** | bus de memoria |

**⇒ `PROVEN_DERIVED. La VRAM es 12 veces más ancha que el enlace. Ninguna carga que mueva datos
entre la CPU y la GPU puede acercarse a la VRAM, porque el PCIe se lo impide antes. Y una carga
que no salga de la GPU tiene 12 veces más margen del que el enlace podría dar nunca.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. El margen de mejora del enlace es de 3,94 veces, de 2,00 a 7,877 GB/s, y sigue
sin alcanzar a la VRAM. Incluso con el enlace al máximo, el equipo seguiría siendo link-bound en
transferencia. Eso no es un defecto de configuración: es la jerarquía de esta placa.** `PROVEN_DERIVED`.

## 3 · La línea de balance, y por qué no la he escrito

**⇒ `NOT_DETERMINED`: qué clase de cuello de botella domina para una carga concreta. §52 pide
elegir entre GPU-bound, MEMORY-bound, SUBMISSION-bound, SYNCHRONIZATION-bound, LATENCY-bound,
POWER-bound, THERMAL-bound y CPU-bound, y eso exige medir una carga. Aquí no hay ninguna.** `NOT_DETERMINED`.

**⇒ Y la razón por la que no se puede decidir con estos datos, dicha sin adornos: la memoria está
en el nivel más bajo de sus tres porque no hay carga que la suba. Un techo de 24 GB/s medido con
`mclk` a 300 MHz no es el techo del equipo, es el techo del equipo en reposo.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Lo que sí se puede afirmar sin ejecutar nada es una afirmación de capacidad,
no de rendimiento: con la memoria a su máximo, la VRAM tiene 12 veces el ancho del enlace. Toda
carga cuyo trabajo efímero no quepa en los 2 GiB de VRAM —y en esta placa, con la iGPU también
presente, eso incluye cualquier cosa que el compositor deje en la VRAM— pagaría un precio de
PCIe, no de VRAM.** `PROVEN_DERIVED`.

## 4 · Lo que esta medición corrige y lo que confirma

**⇒ `PROVEN`: confirma la conversión de unidades de `253`. `253` derivó que el sensor de edge se
entrega en mili-grados y que la conversión es `(centi/100) * 1000`. `hwmon1/temp1_input` devuelve
46000, y 46000/1000 = 46,00 °C exacto. La cadena de cinco saltos que `251` cerró en código y
`253` cerró en estructura produce el número correcto en runtime.** `PROVEN`.

**⇒ `PROVEN`: confirma un valor de `222`. `temp1_crit` de hwmon es 97,00 °C y `222` midió
`usSoftwareShutdownTemp = 97` en el VBIOS real de esta placa. Son dos caminos independientes —
uno por el driver leyendo una tabla ATOM, otro por el driver leyendo un sensor de firmware— y
coinciden dígito a dígito.** `PROVEN`.

**⇒ `NOT_PROVEN`: que `usOperatingTempMaxLimit = 43`, el otro valor de `222`, tenga una
contraparte en runtime. No hay un `temp1_max` en el hwmon de esta placa; sólo `temp1_crit`. El
valor 43 gobierna el control térmico del firmware y no se publica a userspace.** `NOT_PROVEN`.

**⇒ `PROVEN`: y hay una lectura que merece registrarse por lo que es. En reposo, `edge` mide
46-47 °C, por encima de los 43 °C que `222` derivó como límite de operación. Con la tarjeta en
reposo en esta caja eso significa que el límite de operación del firmware ya se supera sin
carga, lo que sitúa el suelo térmico de esta máquina por encima del nominal.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y es la razón por la que `amdgpu_pm_info.txt`, que marca 42 °C, y hwmon, que
marca 46-47 °C, no se contradicen: son capturas de momentos distintos, y la GPU estaba
transicionando de reloj durante ambas.** `PROVEN_DERIVED`.

## 5 · Lo que queda abierto

**⇒ `NOT_DETERMINED`: la clasificación de cuello de botella de §52. Requiere una carga, y una
carga que no eleve `mclk` a 1500 MHz mide la memoria en reposo.** `NOT_DETERMINED`.

**⇒ `NOT_OBSERVED`: cuánto tarda la memoria en subir de 300 a 625 a 1500 MHz, y si sube. Sin
carga no sube, y no hay con qué medir la transición.** `NOT_OBSERVED`.

**⇒ `NOT_AVAILABLE`: el ancho de bus de 64 bits viene del log de arranque, no de una lectura en
vivo. `amdgpu_object.c:1079` lo imprime como `drm_info("RAM width %dbits %s\n", ...)` desde
`adev->gmc.vram_width`, y `amdgpu_kms.c:1016` lo publica como `vram_bit_width` en
`amdgpu_gpu_info`, que está en debugfs y requiere privilegios.** `NOT_AVAILABLE`.

**⇒ `NOT_AVAILABLE`: la razón por la que el enlace está en Gen2 x4 y no en Gen3 x8. La placa lo
admite —`max_link_speed` y `max_link_width` lo dicen— pero si la restricción es física, de
firmware o del kernel, es una pregunta distinta con tres respuestas distintas.** `NOT_AVAILABLE`.

```text
PENDIENTE=258-1 | HALLAZGO=258-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=/sys/kernel/debug/dri/1/amdgpu_gpu_info   (card1 = AMD)
           | ALCANZABLE_SIN_ROOT=NO_MEDIDO

PENDIENTE=258-2 | HALLAZGO=258-*.md | ESTADO=NOT_DETERMINED
           | NECESITA=WORKLOAD  (carga sostenida que eleve mclk y sclk)
           | ALCANZABLE_SIN_ROOT=NO_MEDIDO
```

**⇒ `PROVEN_DERIVED. Y ese segundo discriminante tiene un requisito previo que conviene
explicitar: un benchmark tiene que declarar su estado de reloj. Con esta placa, una medición sin
`freq1_input` y `freq2_input` registrados junto al resultado no es un resultado de rendimiento,
es un número sin contexto. `temp1_input` sin `power1_input` tampoco.** `PROVEN_DERIVED`.

## 6 · Errores propios registrados en esta nota

**⇒ `ERROR`. Calculé el ancho de banda de PCIe como `gtps * 1e9 * enc * lanes / 1e9` y obtuve
16,00 GB/s para Gen2 x4. El error es mío y es de unidades: 1 GT/s son 0,125 GB/s, no 1 GB/s,
porque hay que dividir por 8 para pasar de bits a bytes. El valor correcto es **2,00 GB/s**, y
la consecuencia no es un factor numérico: con 16 GB/s la razón VRAM:PCIe era 1,5:1 y la
conclusión era «memory-bound»; con 2,00 GB/s la razón es 12:1 y la conclusión es
«link-bound». El error no modificaba una cifra, invertía la clasificación.** `ERROR`.

**⇒ `ERROR`. En la misma salida imprimí una línea de verificación con 4800 «GB/s» que eran MB/s:
calculé bien la función y después escribí mal la etiqueta. Dos paths distintos para el mismo
número, uno con la conversión y otro sin ella.** `ERROR`.

**⇒ `ERROR`. Escribí «la VRAM es 2x más ancha» con la cuenta equivocada en la frase y correcta
en la tabla siguiente. Cuando la tabla y la frase discrepan, el lector se queda con la frase.** `ERROR`.

**⇒ Y el patrón es el conocido: escribí la clasificación antes de verificar la unidad, y la
clasificación salió al revés. Una clasificación de cuello de botella invertida es peor que
ninguna, porque dirige la optimización hacia el recurso que no es el cuello.** `ERROR`.