# 909 · El bus es de 64 bits y el multiplicador es 4: las dos notas tenían razón a medias
AUTORIA=AGENTE-SMU

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION · TRACK=RUNTIME+STATIC
CORPUS=RESEARCH/working/linux-7.1.3 + amdgpu_object.c:1079 + amdgpu_atombios.c:1152
          + boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log:35 + amdioread.py
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · GPU INTACTA · MODIFICATIONS_CORPUS=0
```

> ## **`REFUTADA` por `911`. 64 bits no estaba corroborado: estaba mal.**
>
> Esta nota llegó a la conclusión de que el ancho de 64 bits era correcto y que el problema era
> el multiplicador. **El problema era el ancho, y el multiplicador nunca hizo falta.**
>
> ```text
>   VBIOS      GDDR5 128bit         <- la verdad, escrita por el firmware de la placa
>   driver     vram_bit_width = 64  <- amdgpu_atombios.c:786, tabla de IGP en una dGPU
>   techo      128/8 x 2 x 1,5 GHz = 48,0 GB/s
>   medido     43,2 a 44,5 GB/s   = 90,0% a 92,7%
> ```
>
> **El error de esta nota fue de método, y `909` lo describe en su propio §1:** tomó el log
> de arranque como prueba sin haberlo abierto, y lo que el log mostraba era el valor del driver
> repetido, no una segunda fuente. Las dos lecturas salían de la **misma variable**,
> `adev->gmc.vram_width`, que a su vez sale de la función mal escrita.
>
> **La regla que sale, y que vale para todo el proyecto:** un valor que informa el driver es
> evidencia **sobre el driver**. Para que sea evidencia sobre el hardware hace falta un segundo
> camino que no comparta origen.

## Qué resuelve

**⇒ Cierra la `CONTRADICTION` de `908`. El ancho de bus de 64 bits es correcto y está
corroborado por dos lecturas del kernel. La contradicción no era con el ancho: era con el
multiplicador de transferencia, que ningún campo del driver informa.** `RESOLVED`

**⇒ `CORROBORATED`: `adev->gmc.vram_width` = 64.** `PROVEN`

```text
  boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log:35   [drm] RAM width 64bits GDDR5
  amdgpu_object.c:1079-1080   drm_info("RAM width %dbits %s\n",
                                        adev->gmc.vram_width, amdgpu_vram_names[type])
  AMDGPU_INFO_DEV_INFO        vram_bit_width = 64     con amdioread.py, sin root
```

**⇒ `PROVEN_DERIVED`: el techo real es 48,0 GB/s, y las dos notas anteriores loque.de
por razones distintas.** `PROVEN_DERIVED`

| nota | ancho | multiplicador | techo | qué acertó | qué falló |
|---|---|---|---|---|---|
| `258` | 64 | 2 | 24,0 GB/s | el ancho | el multiplicador |
| `602` | 128 | 2 | 48,0 GB/s | la cifra | el ancho |
| medido en `606` | — | — | 43,2 a 44,5 GB/s | — | — |

**⇒ `PROVEN_DERIVED`: con 64 bits, el multiplicador tiene que ser 4 para que el techo sea 48,0, y
eso es exactamente lo que exige la medición.** `PROVEN_DERIVED`

```text
  64 bits x 2 =  24,0 GB/s    imposible: seria el 180% de lo medido
  64 bits x 3 =  36,0 GB/s    insuficiente: solo el 120% de lo medido
  64 bits x 4 =  48,0 GB/s    90,0% a 92,7% de lo medido        COHERENTE
  64 bits x 8 =  96,0 GB/s    dejaria el 54% del techo sin usar, y no se observa
```

**⇒ `NOT_DETERMINED`: que el multiplicador sea 4. Es el único valor de la tabla que encaja, pero
«el único que encaja» no es un hecho, y el campo que lo declara existe y se descarta.** `NOT_DETERMINED`

**⇒ `PROVEN`: ese campo existe, lo parsea el driver, y no lo usa nadie.**
`amdgpu_atombios.c:1152-1153`:

```c
mpll_param->qdr = (args.ucPllCntlFlag & MPLL_CNTL_FLAG_QDR_ENABLE) ? 1 : 0;
```

**⇒ `PROVEN_DERIVED`: `grep` de `qdr` en todo el driver devuelve esa línea y nada más. El flag
QDR de la PLL de VRAM se lee del VBIOS y se tira. Y por eso `vram_bit_width` no lleva información
sobre la tasa: son dos propiedades distintas y el driver informa una y descarta la otra.** `PROVEN_DERIVED`

## 1 · Por qué `908` se equivocó de lado

**⇒ `ERROR`: en `908` declaré que el campo del driver era el valor dudoso, y escribí «el bus es 128
bits y el campo está mal». No había leído el log de arranque.** `ERROR`

**⇒ `PROVEN_DERIVED`: la cuarta fuente estaba en el fichero de evidencia que `258` ya había citado
como `amdgpu_object.c:1079`, y decía 64. Yo tenía la línea en el corpus y no la abrí, porque
buscaba un campo de ioctl y no un `drm_info` del log.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y hay un punto epistémico que sí importa y que la nota de `908` no tenía.
El log y el ioctl no son dos fuentes: los dos leen `adev->gmc.vram_width`, que viene de
`amdgpu_atombios_get_vram_width`, o sea del VBIOS. **Dos lectores de una variable son una fuente,
no dos.** Y lo que la contradicción tenía al lado era una tercera cosa, que es el multiplicador, y
que ningún campo de la estructura del ioctl expone.** `PROVEN_DERIVED`

## 2 · Lo que `258` acertó y lo que le hice mal

**⇒ `PROVEN_DERIVED`: `258` §5, líneas 210-213, dice textual:** `PROVEN_DERIVED`

> **⇒ `NOT_AVAILABLE`**: el ancho de bus de 64 bits viene del log de arranque, no de una lectura en
> vivo. `amdgpu_object.c:1079` lo imprime como `drm_info("RAM width %dbits %s\n", …)` desde
> `adev->gmc.vram_width`, y `amdgpu_kms.c:1016` lo publica como `vram_bit_width` en
> `amdgpu_gpu_info`, que está en debugfs y **requiere privilegios**. `NOT_AVAILABLE`.

**⇒ `PROVEN_DERIVED`: `258` acertaba el ancho, tenía la cita correcta, y su `NOT_AVAILABLE` era
informativo. Lo único que hizo mal fue la aritmética del multiplicador.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y su `NOT_AVAILABLE` sobre la lectura en vivo es FALSO, y es un hallazgo que
vale por sí solo: `amdgpu_kms.c:1016` no publica nada por debugfs, publica `vram_bit_width` en
`drm_amdgpu_info_device`, que se pide con `AMDGPU_INFO_DEV_INFO` sobre `/dev/dri/renderD129`. Ese
nodo es `crw-rw-rw-` y no necesita privilegios. Una frontera marcada como bloqueada por permisos
que no estaban bloqueada, durante el tiempo que estuvo marcada.** `PROVEN_DERIVED`

**⇒ `ERROR`: mis banners en `602` y en `258` se apoyaban en la afirmación de que la cita
no existía, cuando `258` la tenía en su §5 y yo había leído la §2.** `ERROR`

## 3 · Y el error de citar una línea que había cambiado de sitio

**⇒ `ERROR`: cité `258:193` como la línea de la cita. Cuando lo verifiqué, `258:193` hablaba de
temperatura, porque los dos banners que yo había puesto hoy esa misma mañana desplazaron el
contenido 19 líneas. La cita real está ahora en `258:212`.** `ERROR`

**⇒ `PROVEN_DERIVED`: eso es un problema estructural del método de citar, y no un despiste. Las
citas del proyecto son `fichero:línea`, y las notas de `findings/` **se editan**: cada banner de
corrección desplaza todo lo que está debajo. Así que una cita de línea es estable solo hasta la
siguiente corrección de esa misma nota, y quien la lea después está leyendo un número que ya no
apunta a lo que apuntaba.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: y por casi repetir el error. `908` afirmaba «la cita existía, en la nota que
estaba corrigiendo, a 112 líneas del sitio que leí», y al verificarlo la línea no decía eso. Si no
hubiera comprobado el número de línea y hubieraleído la cita por otra vía, habría escrito una
corrección de una corrección basándome en un número obsoleto, que es exactamente el fallo que
iba a corregir.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: la regla que sale de esto, y es de las que más valen: **en las notas de
`findings/`, citar por sección y no por línea.** La sección no se desplaza; la línea sí. Y cuando
la cita sea de un fichero que no se edita —el corpus, el banco— `fichero:línea` sigue siendo lo
correcto y hay que mantener la verificación con `citecheck.py` antes de escribir, no después.** `PROVEN_DERIVED`

## 4 · Lo que queda abierto, y ahora es una sola cosa

**⇒ `NOT_DETERMINED`: el multiplicador de transferencia, y por tanto si el techo de 48,0 GB/s se
debe a 64 bits con transferencia cuádruple o a otra causa.** `NOT_DETERMINED`

```text
  lo que lo resolveria, y su coste
    - el VBIOS: atom_get_vram_pll_param devuelve mpll_param con el campo qdr ya relleno.
      Es el mismo volcado que ya usa amdgpu_atombios_get_vram_width, que esta pendiente de
      sudo desde 272. Con el, sale el flag, y con el flag sale el multiplicador.
    - o el registro MPLL_CNTL de la VRAM: MMIO, nivel 4
  ninguna de las dos necesita algo que no estuviera ya en la lista de bloqueos
```

**⇒ `PROVEN_DERIVED`: y el valor del bloque cambia. `908` lodata como una contradicción entre
una medición y un campo del driver, y era una contradicción entre dos números incompletos. Con el
VBIOS no solo se cierra esta: se cierra también el ancho de bus de `TODO-2`, que llevaba desde el
comienzo de la sesión esperando exactamente ese fichero.** `PROVEN_DERIVED`

**⇒ `PROVEN_DERIVED`: lo que sí queda establecido y no depende del VBIOS. El techo de VRAM de este
proyecto es 48,0 GB/s, y se usa el 90% a 93%. `258` lo subestimó al doble por el multiplicador;
`602` lo acertó por un ancho equivocado. Los tres percentages de utilización de VRAM de `258`,
`271` y `282` estaban mal por lo que `258` hizo, y los de `602` estaban bien por una razón que no
era la buena.** `PROVEN_DERIVED`

## 5 · PENDIENTE

```text
908   | ESTADO=RESUELTA por 909. vram_bit_width = 64 es correcto; la contradiccion era
           |          con el multiplicador, no con el ancho.
602   | SU CORRECCION DE 258 ESTABA MAL en el mecanismo: el bus no es de 128 bits, es de 64
           |          con un multiplicador que aun no esta establecido. El numero, 48,0, vale.
258   | SU ARITMETICA ESTABA MAL: multiplico por 2 y dio 24,0. El ancho, 64, vale.
           | SU NOT_AVAILABLE SOBRE LA LECTURA EN VIVO ESTABA MAL: no exige privilegios.
265   | ESTADO=CORROBORADA por 908: gl2c_cache_size vale 0
TODO-2 | ESTADO=REDUCIDA a una sola variable: el flag QDR de la PLL de VRAM, que el driver
           |          parsea en amdgpu_atombios.c:1152 y descarta. Salida: el VBIOS, sudo,
           |          el mismo volcado que ya estaba pendiente.

REGLA NUEVA | En las notas de findings/, citar por SECCION y no por linea. Los banners de
           |          correccion desplazan las lineas de lo que esta debajo, y una cita de
           |          linea deja de apuntar a lo que apuntaba en la siguiente correccion.
           |          En el corpus y en el banco, fichero:linea sigue siendo lo correcto.

INSTRUMENTO=amdioread.py | ESTADO=VALIDATED, 11 de 11, lee el ASIC sin root
```