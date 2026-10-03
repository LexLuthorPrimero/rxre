# 602 · La cadena de `div.comp` colapsaba, y el techo de VRAM del proyecto estaba en la mitad

```text
CLASSIFICATION=MEASUREMENT+ERROR-CORRECTION · TRACK=RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/ + boot log de 272
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan nivel 1 · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vcp con lane.comp y modelo 7 | ESTADO=VALIDATED (6 controles, ver §2)
```

> **`§4 CORREGIDA` por `606`. El número de esa sección sale; la causa que le puse no.**
>
> Escribí «6,1 ms por vkQueueSubmit-equivalente» y lo llamé coste de descarga. **Es falso.**
> La región temporizada del banco son las líneas 529-534 —`vkResetFences`,
> `vkQueueSubmit`, `vkWaitForFences`— y el intercepto **depende de la huella**:
>
> ```text
>   16 MiB -> 0,198 ms      32 MiB -> 3,447 ms   (+3,25)
>   64 MiB -> 6,924 ms      128 MiB -> 7,117 ms  (+0,19, plano)
> ```
>
> `vkQueueSubmit` no sabe quantos MiB tiene el búfer, luego el efecto no puede ser suyo.
> Son dos escalones de unos 3,3 ms al cruzar 32 y 64 MiB, iguales en la ruta de VRAM y en
> la de RAM del host, y el mecanismo queda `NOT_DETERMINED` en `606` §3.
>
> **Lo que sí se sostiene de §4:** el margen. Con cinco puntos y mínimos cuadrados la banda
> contigua sale 44,0 a 44,5 GB/s, y `606` la confirma por una segunda ruta hasta 512 MiB de
> huella. El 43,2 GB/s de esta nota era correcto.
>
> **Y el error de método es el sexto de la serie:** publiqué una magnitud medida y le añadí
> un mecanismo sin discriminarla. Una magnitud medida necesita una unidad justificada **y**
> una causa que sea suyo; yo sólo había hecho la primera.

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

> **Y `909` le retira el fondo.** El bus **no** es de 128 bits. `258:212` y
> `boot-amdgpu-...log:35` dicen 64, y eso está corroborado. El techo de 48,0 GB/s sigue en
> pie, pero por un mecanismo que ni `258` ni `602`axx-propios: 64 bits con un multiplicador
> de transferencia que **ningún campo del driver informa**. `amdgpu_atombios.c:1152` parsea
> `MPLL_CNTL_FLAG_QDR_ENABLE` en `mpll_param->qdr` y no hay ninguna otra referencia a `qdr`
> en el driver: se lee del VBIOS y se tira.
>
> **Lo que hay que retirar de este banner es la frase «128 bits»**, no el número. `602` dio la
> cifra correcta con un ancho equivocado.

> ## **`CONFIRMADA` por `911`. El bus es de 128 bits, y la predicción de esta nota era correcta.**
>
> Esta nota dedujo que 43,2 GB/s no caben en 24,0 GB/s, y que por tanto el bus no podía ser de
> 64 bits. **El VBIOS lo dice por escrito: `GDDR5 128bit`.**
>
> ```text
>   techo correcto  128/8 x 2 x 1,5 GHz = 48,0 GB/s
>   medido en 606   43,2 a 44,5 GB/s    = 90,0% a 92,7%
> ```
>
> **Lo que `602` no podía saber, y esta nota tampoco settled:** que el campo del driver que
> decía 64 era un error. `amdgpu_atombios.c:786` lee la tabla de IGP
> (`IntegratedSystemInfo`) y devuelve `ucUMAChannelNumber * 64`, en una tarjeta discreta.
> `911` lo localizó leyendo el VBIOS, que estaba bloqueado por una búsqueda incompleta.
>
> **Y el flag QDR de `909` queda sin uso:** con 128 bits y doble velocidad no hace falta para
> ningún techo de este proyecto, y sigue sin consumidor en el driver.

## Qué resuelve

**⇒ Cierra `287-1`. La contradicción del 371% no era una discrepancia entre `hwmon` y la
memoria: era que los 17,829 GB/s los produjeron un kernel cuya cadena de direcciones **colapsa**
a un solo valor, y que el techo contra el que los comparé estaba **calculado con la mitad del
ancho de bus**. Las dos mitades del error son mías. `RESOLVED`.**

**⇒ `PROVEN_DERIVED`. El techo de VRAM del proyecto era la mitad del real. `258` affirmed un bus
de 64 bits sin citar fuente; una medición con reparto de direcciones verificado lo refuta, y
obliga a 128 bits.** `PROVEN_DERIVED`.

**⇒ `PROVEN`. Con el mismo número de cargas de carril, el mismo trabajo de ALU, la misma
ocupación y la entropía verificada, un acceso disperso de 4 bytes cuesta **1,58 GB/s** y uno
contiguo **43,2 GB/s`: 27 veces. Es el margen que el control de direcciones deja sobre la mesa, y
es la razón por la que un driver especializado tiene algo que ganar aquí.** `PROVEN`.

**⇒ `NOT_DETERMINED`: 128 bits o 256. Lo que la medición establece es una cota inferior —128 bits
o más— y 128 bits deja el 90% del techo ocupado, que es coherente; 256 bits lo dejaría en el 45%,
que también es coherente. deciding requires el VBIOS (`atom_vram_info`), pendiente de `sudo` en
`272`.** `NOT_DETERMINED`.

## 1 · La cadena colapsa, y era el instrumento entero

**⇒ `PROVEN`. `div.comp` termina la cadena con `idx = acc % WSIZE`, y como `idx = acc mod WSIZE` el
estado del sistema es un único índice, no `acc`. Sustituyendo en la recurrencia queda una
recurrencia lineal** `PROVEN`:

```text
acc_{k+1} = 1664525 * acc_k + (PATRON + idx_k) + 1013904223
idx_{k+1} = acc_{k+1} mod WSIZE        =>    idx_{k+1} = f(idx_k)
```

**⇒ `PROVEN_DERIVED`. Eso no es un paseo aleatorio. Es una aplicación de un mapa lineal sobre un
conjunto de `WSIZE` estados, y cada iteración reduce la imagen.** `PROVEN_DERIVED`.

| `ITERS` | índices distintos entre 4.096 hilos, `WSIZE` 4096 |
|---|---|
| 1 | 2.567 |
| 4 | 186 |
| **16** | **1** |
| 1.024 | 1 |

**⇒ `PROVEN`. A partir de 16 iteraciones los 4.096 hilos están en la misma dirección. Un
`ITERS = 1024` entero, que es el que usé en `287`, `288` y en el barrido de anchos de banda, mide
un acceso a una dirección.** `PROVEN`.

**⇒ `ERROR`. `287` publicó una tabla de seis puntos de «ancho de banda de VRAM» y todos esos
números salen de un kernel degenerado. La tabla no es un dato de anchura de banda: es una tabla
deUNA dirección, leída por 65.536 hilos.** `ERROR`.

**⇒ `CORROBORATED`: la firma independiente. El banco escribe la última dirección leída y devuelve
`3553` para los 512 hilos probados; el modelo del host, ejecutado aparte, converge al mismo `3553`.
El número medido es exactamente el valor fijo al que colapsa la cadena, lo que confirma el
mecanismo sin depender de mi interpretación.** `CORROBORATED`.

**⇒ `PROVEN_DERIVED`. Y el fallo de instrumentación es el mismo que ya nombro en `290`: el control
de contenido no puede verlo.** `PROVEN_DERIVED`

```text
el control compara lo que el dispositivo devuelve contra lo que el host calcula
si el host hace la MISMA cuenta equivocada, los dos coinciden perfectamente
=> 256 de 256 correctos sobre un kernel que hace UNA sola carga
```

Un control de resultado no puede detectar que el kernel hace el trabajo equivocado. Sólo puede
detectar que hace un trabajo distinto del que el host espera. **El control que hacía falta es
sobre el trabajo, no sobre el resultado.**

**⇒ `PROVEN_DERIVED`: `div.comp` no colapsa del todo, y con `STEPS = 0` retiene 2.567 de 4.096
destinos, o el 63%. Los 37% restantes comparten destino con otro hilo, luego leen la misma línea
de caché. El 63% no es dispersión limpia, y un 63% de dispersión con un 100% de aciertos de
cachía no mide DRAM.** `PROVEN_DERIVED`.

## 2 · El control que faltaba, y los seis controles de `lane.comp`

**⇒ `PROVEN`. `lane.comp` existe para medir el mismo número de cargas de carril con tres repartos
de direcciones, y para eso necesita que cada corrida se auto-verifique. `ADDR = 1` hace que el
shader escriba lo que hay que mirar.** `PROVEN`.

| # | control | qué exige | fallo |
|---|---|---|---|
| 1 | contenido | 256 de 256 contra el modelo del host | `exit 4` |
| 2 | estructura, difusión | los 64 carriles de un wavefront coinciden | `exit 7` |
| 3 | estructura, disperso | carriles vecinos difieren | `exit 7` |
| 4 | entropía | ≥128 y ≤256 direcciones distintas en disperso; 2 a 10 en difusión | `exit 8` |
| 5 | configuración | `WSIZE == wsize`, `LANEMODE ≤ 2`, `ADDR ≤ 1` | `exit 2` |
| 6 | **trabajo** | `ADDR = 0` y `ADDR = 1` tardan lo mismo | por debajo del 10% |

**⇒ `PROVEN_DERIVED`. El control 6 es el que faltaba en toda la serie, y el que ya habría
detectado el colapso si se hubiera escrito antes. Con la primera versión de `ADDR = 1`, que
escribía un solo valor, `acc` quedaba muerto y el compilador borraba la cadena entera: en difusión
y contiguo el índice no depende de ninguna carga, así que se deduce en forma cerrada y las 1.024
cargas desaparecen. Medido: 1,3 × 10¹¹ cargas/s, imposibles.** `PROVEN_DERIVED`.

```text
                       ADDR=0        ADDR=1        diferencia
  DIFUSION           0,007097 s     0,006924 s        2,44%
  DISPERSO           0,175368 s     0,175389 s        0,01%
  CONTIGUO           0,013076 s     0,013023 s        0,41%
```

**⇒ `PROVEN`. Corregido, `ADDR = 1` escribe el índice y además la cadena en una segunda región,
con lo que la carga queda viva y el resultado sigue siendo la dirección que hay que mirar.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. El modo contiguo mezcla por iteración, `idx = hash(acc ^ k·0x85ebca6b)`, y
por eso conserva la dispersión; sin esa mezcla `lane.comp` colapsaba al mismo valor único que
`div.comp`, y eso es lo que el control 4 mide antes de dejar pasar cualquier número.** `PROVEN_DERIVED`.

**⇒ `ERROR`: cuatro defectos del instrumento en una tarde, y todos del mismo tipo — el banco y el
shader no coincidían en qué constante va dónde.** `ERROR`

```text
1. el banco mandaba 6 entradas de specialization y lane.comp declara 4. Las entradas para
   constant_id 4 y 5 no existen en el SPIR-V y el driver las ignora EN SILENCIO: sin error,
   sin aviso, y el kernel recibe un valor que nadie pidio. nentries ahora depende del modelo.
2. off_escritura = g_wsize*4 pero los shaders escriben en d[WSIZE+i]. Solo coinciden si
   WSIZE == wsize, y eso no se exigia para ningun modelo: se cumplia por costumbre al pasar los
   mismos numeros en argv[4] y argv[5]. Con WSIZE 4096 y wsize 8192 el shader escribia donde
   nadie leia y el readback devolvia 0x00000000 en las 256.
3. la linea del modo contiguo no llego al modelo del host por un fallo de sangria en el parche
   automatico. El banco y el shader dejaron de hacer la misma cuenta.
4. el invariante que escribi para el caso 2 era WSIZE + items <= wsize, que es FALSO: el buffer
   es de (wsize + items)*4 y el shader escribe en WSIZE+i. Sale bien solo porque loCOMPARE
   con el buffer entero.
```

**⇒ `PROVEN_DERIVED`. Ninguno de los cuatro habría salido sin el control de contenido, porque los
cuatro habrían Elevated el resultado del host para que coincidiera... salvo el 1, que es
precisamente el caso en el que el host y el shader se ponían de acuerdo sin que nadie lo pidiera.
Un instrumento que valida el resultado no valida el cable.** `PROVEN_DERIVED`

## 3 · Lo que sí mide, y lo que no

**⇒ `MEASUREMENT. 65.536 hilos, huella de 256 MiB, 4.096 y 32.768 vueltas, con la entropía
verificada en cada corrida: 7 de 7 en todos los puntos.** `MEASUREMENT`.

| reparto | cargas de carril/s | GB/s útiles | % de 48,0 GB/s | % de 24,0 GB/s |
|---|---|---|---|---|
| disperso, 64 direcciones distintas | 3,9 × 10⁸ | **1,58** | 3,3% | 6,6% |
| contiguo, 64 direcciones consecutivas | 1,1 × 10¹¹ | **43,2** | **90%** | 180% |
| difusión, 1 dirección por wavefront | 9,7 × 10⁹ | 38,8 | 81% | 162% |

**⇒ `PROVEN`. El reparto contiguo vale 27,4 veces el disperso con la misma cantidad de cargas. En
un banco donde el enlace PCIe va a 2 GB/s y la VRAM puede dar 48, esto decide dónde hay que
trabajar: no en más relojes, no en más ancho de bus, sino en cómo se traducen las direcciones de
las lanes a transacciones de memoria.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. La difusión no dice nada sobre DRAM. Con 4 direcciones distintas entre 256
hilos, todo el conjunto activo son unos pocos sectores: es caché por construcción, y por eso sus
38,8 GB/s no son un techo.** `PROVEN_DERIVED`.

**⇒ `NOT_DETERMINED`: el reparto entre el número de transacciones y la amplificación de bytes. Un
wavefront disperso pide hasta 64 transacciones de 32 B para entregar 256 B, o sea 8 veces de
amplificación; uno contiguo pide 8. El cociente medido es 27,4, que supera el 8 del byteo y no
llega al 64 de las transacciones, así que interviene más de una cosa. Con el banco actual no se
separan: haría falta un cuarto modo que varye la separación de las direcciones de lane dentro del
sector, y eso es una operación nueva.** `NOT_DETERMINED`.

## 4 · `mclk`, y por qué `287` lo leyó mal dos veces

**⇒ `PROVEN`. `mclk` es dinámico y responde a la demanda: con un proceso por invocación y huecos
entre invocaciones estuvo en 1500 MHz el 24% de las muestras, y con un solo despacho continuo, el
83% y el 86% en dos repeticiones, con medias de 1.292 y 1.328 MHz. En reposo, el 2%.** `PROVEN`.

**⇒ `ERROR`: leí `mclk` antes y después de la corrida en `287`. Antes y después es en reposo, y en
reposo son 300 MHz. La primera contradicción que abrí era un artefacto de cuándo miré, no de qué
miré.** `ERROR`.

**⇒ `ERROR`: la medición de `mclk` por modo que hice hoy tampoco valía. El despacho contiguo dura
31 ms y el proceso vive unos 400 ms, así que el 90% de las muestras era la fase de
inicialización en reposo. Iba a concluir que el reparto contiguo va a 13,9 GB/s con `mclk` en 300,
que es imposible. Corregido con despachos largos en los dos modos antes de sacar ninguna
conclusión, y el tiempo por lanzamiento se midió por separado.** `ERROR`.

**⇒ `PROVEN_DERIVED`. El coste por lanzamiento es de 5,4 a 6,8 ms y sale IGUAL en los tres modos,
que no pueden compartir trabajo de shader. Es coste de descarga, y es enorme: con 1.024 vueltas
y 65.536 hilos es el 52% del tiempo total en modo contiguo. Con el enlace a 2,00 GB/s de `286` y
un despacho de 1.024 vueltas, la descarga del comando pesa tanto como la mitad del trabajo.** `PROVEN_DERIVED`

```text
                coste fijo      marginal        GB/s marginales
  DISPERSO      0,0054 s       1,660e-04 s        1,58
  CONTIGUO      0,0068 s       6,063e-06 s       43,23
```

## 5 · El techo de VRAM estaba en la mitad

**⇒ `ERROR`: `258` (§2, líneas 81-88) afirma «bus de 64 bits = 8 bytes» y de ahí sale
`1500e6 × 2 × 8 = 24,0 GB/s`. Es una `PROVEN_DERIVED` sin evidencia: no hay cita, no hay VBIOS,
no hay registro.** `ERROR`.

**⇒ `PROVEN_DERIVED`. La medición lo refuta. El modo contiguo mueve 43,2 GB/s útiles con un
patrón que no reutiliza: la huella de 256 MiB se barre en bloques de 256 KiB avanzando 1 MiB por
vuelta, cada dirección se repite cada 256 vueltas, y entre dos repeticiones se tocan 64 MiB. No
hay reutilización posible con un nivel de 256 a 320 KiB.** `PROVEN_DERIVED`.

```text
  bus 64 bits  a mclk 1500 -> 24,0 GB/s   ->  43,2 es el 180%   IMPOSIBLE
  bus 128 bits a mclk 1500 -> 48,0 GB/s   ->  43,2 es el  90%   COHERENTE
```

**⇒ `REFUTED`: el bus de 64 bits. `PROVEN_DERIVED`: el bus es de 128 bits o más. `NOT_DETERMINED`:
128 o 256, porque 256 bits también es coherente con 43,2 GB/s y solo el VBIOS lo separa.** `NOT_DETERMINED`

**⇒ `PROVEN_DERIVED`. Consecuencia sobre lo ya publicado: todos los porcentajes de utilization de
VRAM de `258`, `271`, `282` y `287` están calculados contra un techo la mitad del real, y por eso
salen el doble de optimistas.** `PROVEN_DERIVED`

```text
  DISPERSO  1,58 GB/s =  6,6% de 24,0   |   3,3% de 48,0
  CONTIGUO 43,2 GB/s = 180% de 24,0     |  90% de 48,0
```

**⇒ `PROVEN_DERIVED`. Y la conclusión de que el cómputo no está limitado por la VRAM sobrevive con
holgura: en el mejor caso medido se usa el 90% de un techo de 48 GB/s, y el enlace va a 2,00 GB/s.
El límite real de esta GPU para cómputo es la traducción de direcciones, no el
ancho de banda.** `PROVEN_DERIVED`

## 6 · Los errores

**⇒ `ERROR`: cinco en una tarde, y el patrón es el de siempre — el defecto estaba en el
encuadre, el denominador o el cable, nunca en el hardware.** `ERROR`

| # | error | cómo lo detectó el control |
|---|---|---|
| 1 | specialization constants de más, el driver las ignora en silencio | contenido, `exit 4` |
| 2 | `WSIZE` y `wsize` sin relación, el shader escribía donde nadie leía | contenido, `exit 4` |
| 3 | el modelo del host desfasado del shader, por sangría | contenido, `exit 4` |
| 4 | invariante falso, `WSIZE + items <= wsize` | invariante, `exit 2` |
| 5 | `acc` muerto y el compilador borró la cadena | **control de trabajo**, el único que podía |

**⇒ `PROVEN_DERIVED`. Cuatro de los cinco los detectó el control de contenido, porque el host y el
shader dejaron de hacer la misma cuenta. Sólo el quinto no habría salido de ahí: el host y el
shader sí coincidían, y los dos estaban midiendo un bucle sin cargas. Es el único que exigía un
control nuevo, y ese control —que `ADDR = 0` y `ADDR = 1` tarden lo mismo— vale más que los otros
cuatro juntos, porque es el único que se refiere al trabajo y no al resultado.** `PROVEN_DERIVED`

## 7 · PENDIENTE

```text
287-1 | ESTADO=RESOLVED por 602
           | CAUSA_1=colapso de la cadena de div.comp: 1 direccion a partir de 16 iteraciones
           | CAUSA_2=el techo de 258 estava en la mitad por un bus de 64 bits sin fuente
           | NINGUNA_HIPOTESIS_DE_287_SOBREVIVE: no era que hwmon mintiera, ni que una cache
           |   explicara el exceso. Era que no habia DRAM de la que hablar.

258   | ESTADO=CORREGIDA por 602
           | ERROR=techo de VRAM la mitad del real; bus de 64 bits sin evidencia
           | AFECTA=258, 271, 282, 287 (todos los porcentajes de utilizacion de VRAM)
           | VERIFICAR_AUN=si el bus es de 128 o de 256 bits (VBIOS, sudo)

287-3 | ESTADO=OPEN, NUEVO
           | PREGUNTA=cuanto de las 27,4 veces es numero de transacciones y cuanto
           |          amplificacion de bytes
           | NECESITA=un cuarto modo que varye la separacion de las direcciones de carril
           |           dentro del sector, con lo demas identico
           | ALCANZABLE_SIN_ROOT=si

287-4 | ESTADO=OPEN, NUEVO
           | PREGUNTA=de donde salen los 5,4 a 6,8 ms por despacho
           | PORQUE=es igual en los tres modos, luego no es del shader
           | CANDIDATOS=coste de la API de Vulkan, de la construccion del command buffer,
           |          del fence, o del vaciado del ring de SDMA
           | ALCANZABLE_SIN_ROOT=si, y con un kernel vacio el coste se separa del trabajo

INSTRUMENT=vcp | ESTADO=VALIDATED
           | KERNELS=8 (probe, occ, chain, div, page, reuse, spread, lane)
           | MODELOS=8 (0..7)
           | CONSTANTS=6 (ITERS, WSIZE, STEPS o B o LANEMODE, MODE o ADDR, GRP, LANE)
           | INVARIANTES_5=wsize >= items, WSIZE >= items, WSIZE == items x B (modelos 5 y 6),
           |               GRP coprimo con 64 (modelo 6), WSIZE == wsize (modelo 7)
           | CONTROLES_6=contenido, estructura por modo, entropia por modo, invariantes,
           |               especializacionreachable, equivalencia spread(GRP=1) == reuse,
           |               trabajo ADDR=0 == ADDR=1
```