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

Tres punteros distintos (dos de hardware, uno de software) coinciden
exactamente. **PROVEN** por redundancia: no es un valor que dependa de una
sola lectura.

`rptr == wptr` significa **anillo vacio**: la GPU consumio todo lo que el
driver escribio. Lo que queda en el buffer es residuo de comandos ya
ejecutados, no trafico en vuelo. Se dice explicitamente para que nadie lea
esto como lo que la GPU esta haciendo ahora.

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

## 6. ERRORES PROPIOS ENCONTRADOS EN ESTA SESION

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
