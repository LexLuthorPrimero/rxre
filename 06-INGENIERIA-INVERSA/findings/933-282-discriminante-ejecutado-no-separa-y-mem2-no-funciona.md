# 933 — El discriminante de `282` ejecutado por primera vez: la lectura encadenada no separa VRAM de RAM. Y `--mem=2` no funciona en absoluto

Estado: `282` CORROBORADA con el flag vivo. `--mem=2`: `PROVEN_ABSENT` como modo utilizable.
Alcance: la RX 550 de esta placa, Polaris12/GFX8.1, RADV, Mesa de este equipo.
AUTORIA=AGENTE-SMU
Cierra `606-2`.

## Por qué el discriminante no se había ejecutado

`282` se contradijo a si mismo: la lectura encadenada se costea igual en VRAM y en RAM. La causa
de que fuera el único resultado del banco era que su discriminante **no se había corrido nunca**. El
flag `--mem=host` estaba muerto: `strtoul("host")` devuelve 0, así que `--mem=host` caía al valor por
defecto, `--mem=0`, y las dos ramas acababan en el mismo tipo de memoria. `606` lo destapó y dejó el
flag reparado. `606-2` era el pendiente que quedaba: ejecutarlo.

Es la tercera vez en este proyecto que un discriminante previsto y no ejecutado se confunde con un
resultado. La diferencia entre «lo probé y no separa» y «no lo probé» es la diferencia entre una
medición y una ausencia, y aquí llevaba dos notas existiendo como si fuera lo primero.

## Los tres modos de memoria, y dónde cae cada uno

El banco imprime el tipo de memoria que elige, y eso es lo que hace descartable el confound:

```
--mem=0   kernel=tipo[0]  flags=0x00000001  heap=0   DEVICE_LOCAL                 -> VRAM del ASIC
--mem=1   kernel=tipo[2]  flags=0x00000006  heap=1   HOST_VISIBLE|HOST_COHERENT    -> RAM del sistema
--mem=2   kernel=tipo[3]  flags=0x00000007  heap=2   DEVICE_LOCAL|HOST_VISIBLE|... -> BAR
```

Los tres son tipos **distintos y de heap distintos**. El confound de que las dos ramas acaben en el
mismo sitio está descartado por construcción, no por argumento.

## El resultado: no separa

Conjunto de trabajo de 64 MiB, muy por encima de la L3 de 8 MiB de esta CPU, 64 MiB movidos por
pasada, 31 repeticiones, control de contenido activo en las tres ramas:

```
VRAM  (heap 0)   mediana=0,042482 s   sigma=0,001252 s (2,9 %)   1,5797 GB/s   2,5321 ns por acceso
RAM   (heap 1)   mediana=0,042406 s   sigma=0,000943 s (2,2 %)   1,5825 GB/s   2,5276 ns por acceso

diferencia = 0,000076 s     sigma maximo = 0,001252 s
```

**La diferencia es el 6% de la sigma.** No separa, y por tanto `282` queda corroborada: la lectura
encadenada cuesta lo mismo en VRAM que en RAM, con una separación real de memoria y un conjunto de
trabajo fuera de caché. La diferencia es de 0,18% en GB/s; el ruido es de 2,2–2,9%.

Esto tiene una consecuencia que va más allá de confirmar una nota antigua. Una lectura de 4 B que
cuesta 2,53 ns **sin importar de dónde estén los datos** no está midiendo el transporte de datos. O
bien el acceso no llega a la VRAM y se resuelve en una estructura de la GPU que no depende del tipo de
memoria del buffer, o bien el tiempo lo fija algo que no es la jerarquía de memoria. Cualquiera de las
dos es una afirmación fuerte, y ninguna de las dos se puede cerrar sin `282-1`, que es exactamente lo
que `282-1` tiene que responder y sigue sin responder.

## `--mem=2`: el modo del BAR no funciona en esta placa

El tercer modo falla su control de contenido en **todos** los tamaños, de 4 KiB a 64 MiB. No es un
problema de tamaño.

El valor que lee el shader es `0xdeadbeef`:

```
--mem=2   DATO i=0  gpu=0xdeadbeef  modelo=0x0f018bcc
          DATO i=1  gpu=0xdeadbeef  modelo=0xb5b7ffd8
          DATO i=2  gpu=0xdeadbeef  modelo=0x78e65f34
```

`0xdeadbeef` es el valor con el que Mesa envenena la memoria recién asignada y nunca escrita. Pero
eso, por sí solo, no demuestra que la copia no llegara: una cadena calculada sobre veneno también
devolvería algo distinto del modelo. El discriminante es variar `ITERS`:

```
ITERS=1    gpu=0xdeadbeef
ITERS=4    gpu=0xdeadbeef
ITERS=64   gpu=0xdeadbeef
```

**Una cadena cuyo valor no cambia con el número de iteraciones no es un resultado calculado.** Es la
región de salida sin tocar. Conclusión: con `--mem=2`, **ni la copia de entrada ni las escrituras del
shader son visibles desde el host.** El modo no está degradado ni lento: no está operativo.

Lo que queda `NOT_DETERMINED`, y son candidatos distintos con discriminantes distintos:

- la asignación del heap 2 devuelve memoria sin respaldo real y el driver no lo detecta;
- la copia de buffer a buffer hacia el BAR se descarta en silencio, y las escrituras del shader se
  descartan también por el mismo motivo: una caché que no se hace coherente con el host;
- el envío falla de forma silenciosa en este camino y el banco no lo ve, porque
  `vkWaitForFences` devuelve éxito aunque el command buffer se haya descartado.

**Eso último es un agujero del banco, no una hipótesis del hardware**, y es el más barato de cerrar:
`vkGetFenceStatus` después de esperar, y `vkGetQueryPoolResults` sobre las marcas de trabajo. Sin
eso, cualquier fallo de envío se manifiesta como un buffer de ceros o de veneno, que es como se
manifestó.

Lo que sí es `PROVEN` y no necesita más: la ruta del BAR, tal y como la expone Vulkan en esta placa,
no es utilizable para escribir y leer desde el host. Un driver propio no puede contar con ella.

## Un defecto del banco que esta vuelta descubrió

El chequeo «no nulos» del banco cuenta como válido el veneno de Mesa. Con `--mem=2` y `--nocontrol`
la salida fue **«256 de 256 no nulos»**, y eso lo leí en un primer momento como «las escrituras del
shader sí llegan al host». Es falso: `0xdeadbeef` no es cero, así que el chequeo lo aprueba.

Un control que solo distingue cero de no-cero no distingue datos de memoria sin inicializar. Y en un
banco cuyo trabajo es decidir si un número es creíble, ese es un fallo del instrumento, no un detalle
de implementación. Se anota como pendiente con el mismo criterio que el resto: el arreglo es más
barato que la nota.

## Instrumentos

- `bench.py` 15 de 15. La puerta de frescura del binario añadida en `930` está activa y no estorba.
- `vulkan_compute_probe.c` con `--tex`; los tres modos de memoria operativos salvo `--mem=2`.

## Errores propios de esta iteración

1. **Compare listas vacias y lo llame acuerdo.** Al buscar los valores del shader use `--nocontrol`,
   que no imprime la linea `DATO`, y el programa comparo tres listas vacias y dio un veredicto. En
   plan de trabajo

   La comparacion tiene que **decir que no hay nada que comparar**, y ahora lo dice: `SIN DATOS: la
   comparacion no se puede hacer`. Sin eso, un vacio y un vacio parecen un acuerdo.

2. **Leí `DATO` del flujo equivocado.** Va a `stderr` (por eso usa `fprintf(stderr, …)`), y yo lo
   buscaba en `stdout`. Con `2>&1` aparecía; con `subprocess` sin `stderr`, no.

3. **Leí «256 de 256 no nulos» como «las escrituras llegaron».** Ver arriba: es el veneno de Mesa
   contándose como dato. De ahí la necesidad del barrido con `ITERS`, que es lo que desmintió la
   lectura.

Los tres son el mismo patrón: **aceptar un indicador que no distingue lo que tiene que distinguir.**
Una lista vacía, un canal equivocado y un valor no nulo. En los tres casos el instrumento dio una
respuesta y yo la traduje a una conclusión sin comprobar que la respuesta distinguiera algo.

## Lo que queda abierto

- ~~**`282-2`**~~ **RANCIOSO**: cerrado en `283`, con buffer de dos regiones disjuntas y
  control 40/40 donde antes fallaba 0/40.
- **Cerrar el agujero del banco**: comprobar el estado del fence y las marcas de trabajo, para que un
  envío fallido no se vea como un buffer de veneno. Es la acción siguiente, y es barata.
- **Endurecer el chequeo «no nulos»** para que no acepte `0xdeadbeef`, y en general para que
  compruebe el valor esperado y no solo que no sea cero.
- **`282-1`** sigue necesitando una tecnica que pase de 64 KiB.
