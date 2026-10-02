# 044 · La corrección de `043` aplicada, y por qué `make` no vio el cambio

`CLASSIFICATION=IMPLEMENTATION+CORRECTION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`IMPLEMENTS=043` · `CIERRA=la retracción de 035/036`

## CUDA principal

Corregido el codificador: el campo de entradas del PTEPDE vuelve a ser `count` plano, que es
lo que escribe el ASIC que corre. Y encontré un fallo en mi propio arnés de pruebas que
hubiera dejado pasar un error sin darme cuenta.

**El fallo:** `make` dijo "está actualizado" y el binario de test **no se había reconstruido**.
El `.h` tenía una marca de tiempo *posterior* al `.o`, y el objetivo del Makefile depende de
`$(KERNEL_SRC)` = `../kernel/rx550_pm4.c`, **no de `../kernel/rx550_pm4.h`**.

```
test_pm4: test_pm4.c $(KERNEL_SRC)
	$(CC) $(CFLAGS) -I../kernel -o $@ $^
```

Cambié una constante en `rx550_pm4.h`, ejecuté `make`, y make reconstruyó porque
`test_pm4.c` también había cambiado. Cuando restauré el `.h` con `cp` —que actualiza la
mtime— **make lo vio más nuevo que el `.o` y no tenía ninguna regla que lomentionara**, así
que dijo "actualizado" y dejó el binario viejo.

El síntoma: `make` informaba éxito, el binario era de la versión anterior, y el test
fallaba con el valor mutado. **Un harness que dice "compilado" sin comprobar la mtime de
todas sus dependencias informa de una compilación que no ocurrió** — que es exactamente lo
que `AGENTS.md` §"PRE-EXECUTION CONTRACT CHECK" prohíbe con "Nunca aceptar 'compiló'".

**La corrección es de una línea y la hago con `$(wildcard)`**, que es lo que un Makefile
debería haber tenido desde el principio:

```make
KERNEL_HDRS := $(wildcard ../kernel/*.h)
test_pm4: test_pm4.c $(KERNEL_SRC) $(KERNEL_HDRS)
	$(CC) $(CFLAGS) -I../kernel -o $@ $(KERNEL_SRC) $<
```

**Y el `$<` en vez de `$^` es la mitad de la corrección.** La primera versión del arreglo
compilaba, y fallaba con `error: nombre de tipo 'bool' desconocido` en cuatro sitios de
`rx550_pm4.h`. Motivo: `$^` son *todos* los requisitos, y al añadir los `.h` como
dependencias `$^` los pasó **al compilador**, que los trata como unidades de traducción y
compila cada uno suelto, sin el `<stdbool.h>` que sí incluye el `.c` compartido.

Es el mismo error que la cabecera de `rx550_pm4.h` documenta en su propio comentario — *el
kernel no tiene `<stdbool.h>`*— y lo provoqué yo al añadir la dependencia que debía
arreglarlo. Un arreglo de dependencias que rompe la regla de oro del fichero que arregla
necesita su propia prueba, no solo que «no falle».

Verificado en los dos sentidos: tocar un `.h` **reconstruye** (`cc` en la salida), y
`make -B` sigue funcionando. **M-A reinyectado ahora falla 2 checks en lugar de pasar.**

## Lo que cambió en el codificador

| | antes (035/036) | ahora (043/044) |
|---|---|---|
| dword 9 del PTEPDE | `count - 1` | `count` |
| `count == 0` | rechazado | **rechazado** (se mantiene) |
| nombre del opcode en el comentario | `SDMA_OP_PTEPDE` | `SDMA_OP_GEN_PTEPDE` |

**El rechazo de `count == 0` sobrevive a la corrección**, y por un motivo que cambia: con la
codificación plana `0` significa "cero entradas" y no sirve para nada; con la de más-uno
sería `0xFFFFFFFF`. Como no se sabe cuál de las dos cosas haría el hardware, y `043`
establece que no lo sabemos, **no se emite**. Antes el motivo era "evitar 2³² entradas", que
dependía de la codificación equivocada. Ahora es "no se sabe qué significa", que no depende
de nada.

Las mutaciones M1 y el vector de frontera de la suite cuentan ahora la codificación nueva, y
sus nombres dicen a qué finding corrigen: un check que dice "count" a secas es indistinguible
de la versión equivocada.

## Las dos mitades de la retracción, y por qué solo affects una

`043` deshizo parte de `035` y `036`, no todo. La distinción es el dato:

```
gmc_v8_1_ip_block    definido en gmc_v8_0.c:1762   .funcs = &gmc_v8_0_ip_funcs
gmc_v8_0_ip_block    definido en gmc_v8_0.c:1754   .funcs = &gmc_v8_0_ip_funcs
gmc_v8_5_ip_block    definido en gmc_v8_0.c:1770   .funcs = &gmc_v8_0_ip_funcs
```

**Los tres bloques GMC están en el mismo fichero y comparten la misma tabla de funciones.**
Lo único que los distingue es `major/minor`. Polaris12 usa `gmc_v8_1_ip_block` y por tanto
**ejecuta el código de `gmc_v8_0.c`**. Todo lo de `037` —los dos tramos de PTBA, el aperture,
`VM_INVALIDATE_REQUEST`— sigue siendo `PROVEN`.

```
sdma_v3_1_ip_block   definido en sdma_v3_0.c:1693  .funcs = &sdma_v3_0_ip_funcs
sdma_v4_0_ip_block   definido en sdma_v4_0.c:2735  .funcs = &sdma_v4_0_ip_funcs
```

**Los dos SDMA están en ficheros distintos con tablas distintas.** Polaris12 usa el de
`sdma_v3_0.c`, así que `sdma_v4_0.c` no corre.

**La misma lógica, dos resultados opuestos, y el que decide es `.funcs`, no el nombre del
fichero.** Un fichero puede contener varios bloques con tablas compartidas (GMC), y dos
ficheros pueden describir el mismo siliconio con nombres parecidos (SDMA). Preguntar "¿este
fichero es el mío?" no tiene respuesta; preguntar **"¿qué tabla de funciones ejecuta esta
GPU?"** sí, y `which_hw.py` responde a eso.

## `amdgpu_device_ip_block_add` no rechaza duplicados

```c
/* amdgpu_ip.c:240-250 */
adev->ip_blocks[adev->num_ip_blocks].adev = adev;
adev->ip_blocks[adev->num_ip_blocks++].version = ip_block_version;
```

Sin comprobar el `type` previo. Y el consumidor toma **el primero** que encuentra
(`amdgpu_ip.c:150-151`).

No importa en amdgpu porque el switch de `amdgpu_device.c:2145` es excluyente: family VI
toma el `case` y nunca llega al `default`. **Pero importa para un driver propio**: añadir dos
bloques del mismo `type` hace que el segundo sea inalcanzable sin ningún aviso. Es un
`REQUIREMENT`, no una curiosidad, y está anotado como tal.

## Lo que sigue `NOT_DETERMINED`

Nada de esto cambia el hueco de fondo, y conviene no fingir lo contrario:

- Si el hardware de esta pieza concreta lee el campo como el driver de referencia lo
  escribe. La mejor evidencia disponible es lo que hace el driver, y `033` estableció que el
  spec de GFX8 no está publicado. Es `PROVEN_DERIVED`, no `PROVEN`.
- Cuál es la versión de `SDMA0_HWIP` de esta tarjeta, que es lo que decide el despacho y
  requiere leer un registro.
- Todo lo de `033`/`037`/`040` que depende de la semántica del MMU.

## UNLOCKS

- El arnés de pruebas ya no puede decir "compilado" sin haber recompilado. La dependencia
  que faltaba era `$(wildcard ../kernel/*.h)`, y la había estado ocultando desde el
  principio.
- `which_hw.py` resuelve "¿qué tabla de funciones ejecuta esta GPU?", que es la pregunta
  correcta y la que nadie se estaba haciendo. `.funcs` es el discriminante, no el nombre.
- El mapa real está medido: `CHIP_POLARIS12` → `gmc_v8_1_ip_block` (en `gmc_v8_0.c`),
  `sdma_v3_1_ip_block` (en `sdma_v3_0.c`), `gfx_v8_0_ip_block` (en `gfx_v8_0.c`).

## Falsación

- La corrección del `count` se refuta si `vi_set_ip_blocks()` no se ejecutara para
  `CHIP_POLARIS12`, o si ambos caminos se ejecutaran y el segundo bloque ganara. El switch
  de `amdgpu_device.c:2145-2153` es excluyente y `amdgpu_ip.c:150` toma el primero.
- La corrección del Makefile se refuta si `make` vuelve a decir "actualizado" tras tocar un
  `.h` de `../kernel/`. Comprobable en un segundo, y ya se comprobó al revés: con la
  dependencia puesta, `make` sí reconstruye.

## Evidencia

```
07-DRIVER/tests/Makefile    KERNEL_HDRS con $(wildcard), dependencia anadida
07-DRIVER/kernel/rx550_pm4.c   dword 9 = count, con el porque en el comentario
07-DRIVER/kernel/rx550_pm4.h   nombre del opcode corregido
07-DRIVER/tests/test_pm4.c     checks renombrados con el finding que corrigen
tools/rx550pm4val.c            dword 9 leido como entradas planas
mutacion M-A (count-1)         2 checks FAIL (antes pasaba)
validador mutado (nm1+1)       1 vector FAIL de 16
suite completa                 22 + 12 + 195 = 229 checks, 0 fallos
crosscheck                     10 vectores CLEAN
rx550pm4val --selftest         16/16
audit_citations                239 citas, 0 fallos
herramientas nuevas            vmid_map.py, which_hw.py, oracle.sh
corpus:                        MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
