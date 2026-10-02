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

## 7. FIRMWARE INFO DEL VBIOS, CRUZADA CON EL KERNEL

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

## 8. ERRORES PROPIOS ENCONTRADOS EN ESTA SESION

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
