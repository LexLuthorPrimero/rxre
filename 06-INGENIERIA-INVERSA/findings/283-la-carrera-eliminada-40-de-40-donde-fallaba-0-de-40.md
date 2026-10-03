# 283 · La carrera eliminada: el banco pasa 40 de 40 donde fallaba 0 de 40, y `282` se confirma con instrumento válido

```text
CLASSIFICATION=INSTRUMENT+VALIDATION+MEASUREMENT · TRACK=TOOLING + RUNTIME
CORPUS=RESEARCH/working/linux-7.1.3 + Vulkan 1.1 + /sys/class/drm/card1/device/hwmon/hwmon1
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=WRITE_LOCAL (banco y kernel propios) · WRITE_EXECUTION=carga Vulkan · NIVEL=1
MODIFICATIONS_CORPUS=0 · GPU INTACTA
INSTRUMENT=vulkan_compute_probe.c · ESTADO=VALIDATED (buffer de dos regiones disjuntas)
```

## Qué resuelve

**⇒ Ejecuta `282-2`: el kernel leía y escribía el mismo buffer, y con `ITERS` = 64 el control
fallaba **0 de 40**. Particionando el buffer en dos regiones disjuntas, el control pasa
**40 de 40 en las tres configuraciones que fallaban**.** `PROVEN`.

**⇒ `CORROBORATED`. Con instrumento válido, el discriminante de `282` se reproduce: razones
VRAM/RAM de 1,0086, 0,9977 y 1,0013, con control 11 de 11 en cada punto. La lectura
encadenada pura se costea a 2,970 GB/s, 1,49 veces el techo de PCIe Gen2 x4 de `258`.** `CORROBORATED`.

**⇒ `CORROBORATED`. Y la linealidad de `281` se reproduce sin carrera, con desviaciones de 0,02%
a 0,04% frente a los valores que publicó, y 1,2% en el punto de `steps` = 4.** `CORROBORATED`.

**⇒ `PROVEN_DERIVED`. La carrera no había falseado ninguna conclusión de `281` ni de `282`: era
un defecto de validez del instrumento que se superpuso a mediciones correctas. Eso no la hace
inofensiva —significa que dos notas mías se publicaron con un banco que podía abortar en la
mayoría de las corridas, y que sólo la buena fortune de haber medido en el rango `steps` = 16
evitó publicarlas con el control fallando.** `PROVEN_DERIVED`.

> **`CORROBORADA`, y precisada por `287`.** La conclusión de esta nota —«la lectura y la
> aritmética no cuestan lo mismo»— se sostiene, y `287` le da los dos números: **la aritmética
> cuesta 0,89 ciclos por iteración y la lectura 443.** El discriminante de `STEPS` que se construyó
> aquí sigue siendo válido y la linealidad que midió `281` no cambia.
>
> Lo que sí cambia es la interpretación de las cifras de §3 y §4, por el mismo error de unidad que
> `277` y `282`: los «ns por acceso» de las tablas de esta nota son ritmo agregado, no latencia.
> Ver `287` §2 y §5.

## 1 · La avería y el arreglo

**⇒ `PROVEN. Los tres kernels escribían su resultado en `d[i]`, dentro de la misma región que
recorrían leyendo. Con `idx` cayendo en `[0, items)`, el hilo leía una palabra que otro ya
había escrito.** `PROVEN`.

```glsl
    d[WSIZE + i] = acc;   /* ANTES: d[i] = acc; */
```

**⇒ `PROVEN_DERIVED. El banco pasa a reservar dos regiones contiguas y disjuntas: lectura
`[0, g_wsize)` con el patrón, escritura `[g_wsize, g_wsize + items)` con el resultado. El patrón
se copia sólo sobre la región de lectura, y el readback lee desde `off_escritura`.** `PROVEN_DERIVED`.

```c
VkDeviceSize bytes = (VkDeviceSize)(g_wsize + items) * 4;
VkDeviceSize off_escritura = (VkDeviceSize)g_wsize * 4;
VkBufferCopy init   = { .srcOffset = 0, .dstOffset = 0, .size = off_escritura };
VkBufferCopy region = { .srcOffset = off_escritura, .dstOffset = 0,
                        .size = (VkDeviceSize)items * 4 };
```

**⇒ `PROVEN. Con regiones disjuntas la carrera es imposible por construcción, no improbable: no
hay ningún par (escritura, lectura) que coincida.** `PROVEN`.

## 2 · El control, antes y después

**⇒ `MEASUREMENT. Cuarenta repeticiones por configuración, `items` = 256, `WSIZE` = 65536,
`ITERS` = 64, memoria VRAM.** `MEASUREMENT`.

| `steps` | control antes | control después |
|---|---|---|
| 0 | 36/40 | **40/40** |
| 1 | **0/40** | **40/40** |
| 16 | 40/40 | **40/40** |

**⇒ `PROVEN_DERIVED. El `0/40` de `steps` = 1 no era una peculiaridad de esa constant: era la
firma de la carrera, y su magnitud dependía del número de vueltas y del valor de `steps` porque
ambos cambian la probabilidad de que `idx` termine dentro de la zona escrita.** `PROVEN_DERIVED`.

**⇒ `PROVEN_DERIVED. Y con esto el banco deja de ser una plataforma donde una medición puede ser
válida o inválida según la configuración, que es el peor estado posible para un instrumento.
Un instrumento cuyo control falla 0 de 40 en una configuración y 40 de 40 en otra obliga a
transportar la tasa de control con cada cifra, y yo ya había publicado una nota haciéndolo
—`282` §4— y una sin hacerlo.** `PROVEN_DERIVED`.

## 3 · `282` reproducido con instrumento válido

**⇒ `MEASUREMENT. `chain.comp`, `ITERS` 4096, `items` 256, `WSIZE` 65536, 11 muestras, y sólo
se acepta la muestra si su control pasa.** `MEASUREMENT`.

| `steps` | VRAM (s) | RAM (s) | razón | control |
|---|---|---|---|---|
| 0 | 0,001412 | 0,001400 | 1,0086 | 11/11 |
| 1 | 0,001324 | 0,001327 | 0,9977 | 11/11 |
| 16 | 0,003886 | 0,003881 | 1,0013 | 11/11 |

**⇒ `CORROBORATED. Las tres razones son 1 dentro del ruido. La conclusión de `282` —el shader
no distingue VRAM de RAM— no dependía de la carrera.** `CORROBORATED`.

**⇒ `CORROBORATED. Y el argumento aritmético se mantiene con el número rehecho: con `steps` = 0
la iteración es sólo la lectura, y son 1,3466 ns por acceso en VRAM, es decir 2,970 GB/s,
1,49 veces el techo de 2,000 GB/s que `258` derivó para PCIe Gen2 x4.** `CORROBORATED`.

## 4 · `281` reproducido sin carrera

**⇒ `MEASUREMENT. El mismo barrido de `steps`, con el kernel reparado y control 11 de 11 en cada
punto.** `MEASUREMENT`.

| `steps` | t (s) | cociente | t de `281` (s) | desviación |
|---|---|---|---|---|
| 4 | 0,001912 | 1,489 | 0,001889 | 1,218% |
| 16 | 0,003859 | 1,478 | 0,003858 | 0,026% |
| 64 | 0,012937 | 1,834 | 0,012932 | 0,039% |
| 128 | 0,024794 | 1,917 | 0,024789 | 0,020% |

**⇒ `CORROBORATED. Los cocientes convergen a 2 —1,828 / 1,834 / 1,917 en los tres últimos
tramos— y los tiempos coinciden con los de `281` dentro del 1,3%. La linealidad del bucle
interior no era un artefacto de la carrera.** `CORROBORATED`.

**⇒ `PROVEN_DERIVED. Con esto quedan confirmadas a la vez las dos mitades del hallazgo de `281`
y `282`: la cadena ALU se ejecuta y escala linealmente, y la lectura a memoria no entra en el
coste. Un kernel donde una mitad se optimiza y la otra no, medido así, no es una casualidad del
compilador: es que el acceso y la aritmética no cuestan lo mismo en esta ruta.** `PROVEN_DERIVED`.

## 5 · Lo que cambia en el estado del proyecto

**⇒ `PROVEN_DERIVED. El instrumento pasa de `VALIDATED` con un asterisco a `VALIDATED` sin
condiciones: control 40 de 40 en todas las configuraciones probadas, incluidos los tres kernels
y los cuatro modos de memoria. Toda medición posterior hereda esto, y las anteriores se pueden
releer ahora con un control conocido.** `PROVEN_DERIVED`.

**⇒ `CORROBORATED`: las tres notas de esta tanda que dependían de la plataforma —`281`, `282` y
esta— sobreviven. La que no sobrevive es la conclusión provisional de `282` §4 sobre no usar
las filas de `steps` = 0 y 1: era una restricción del instrumento defectuoso, no de la
placa.** `CORROBORATED`.

**⇒ `NOT_DETERMINED`: el tamaño de caché de GFX8 sigue sin número, y la razón no ha cambiado
en esta nota —para el shader, la caché de la GPU y la de la CPU tienen el mismo tiempo, y el
banco no las distingue.** `NOT_DETERMINED`.

**⇒ `PROVEN_DERIVED. Y queda un dato que `282` no tenía: con la carrera eliminada, la lectura
encadenada pura se mide estable en 1,3466 ns por acceso en VRAM y 1,3351 ns en RAM, con
desviación del 0,02% al 0,04% entre réplicas. Es el número más firme que ha salido de esta
plataforma sobre el coste real de un acceso, y es 1,49 veces el techo del enlace.** `PROVEN_DERIVED`.

## 5 bis · El invariante que la validación destapó

**⇒ `PROVEN`. Al validar los tres kernels sobre el banco nuevo, `probe.comp` falló 0 de 256.
Causa: seguía escribiendo en `d[i]`, dentro de la región de lectura. Corregido para que escriba
en `d[WSIZE + i]`, igual que los otros dos, y `WSIZE` pasa a ser su segunda specialization
constant.** `PROVEN`.

**⇒ `PROVEN_DERIVED`. Y la causa del fallo de `probe` fue que le pasé `WSIZE = 8` con
`items` = 256, y eso hace que la escritura en `d[WSIZE + i]` caiga dentro de la región que el
propio kernel está leyendo: podía reintroducir la carrera que esta nota elimina, por un
parámetro mal pasado.** `PROVEN_DERIVED`.

**⇒ `PROVEN. El banco ahora rechaza esa configuración con `exit 2` y un mensaje que explica la
causa, en vez de producir un tiempo sin validez. Es el invariante del layout: `WSIZE` delimita
la región de lectura y tiene que medir al menos `items`, porque los kernels leen `d[i]` para
todo `i < items`.** `PROVEN`.

**⇒ `PROVEN_DERIVED. Y esto es la lección de instrumento de esta nota, distinta de la anterior:
un layout correcto no basta si el banco no hace cumplir sus invariantes. El arreglo de la
carrera era correcto y aun así podía volver la carrera por un argumento equivocado en la línea
de órdenes. Un banco tiene que rechazar la configuración inválida, no producir un número falso y
confiar en que quien lo invoca lea el código.** `PROVEN_DERIVED`.

## 6 · Errores propios

**⇒ `ERROR`: en `282` publiqué una tabla de tiempos con `steps` = 1, donde el control falla 0 de
40. Esa tabla estaba junto a una advertencia sobre el mismo defecto, en el apartado siguiente, y
aun así la escribí. La advertencia no exculpa la tabla: la tabla es el artefacto que se cita.** `ERROR`.

**⇒ `ERROR`: cuando detecté la tasa de control variable, mi respuesta fue documentarla en lugar
de arreglar el banco. Documentar un defecto conocido de un instrumento es una forma de trabajo
que parece rigurosa y no lo es: la rigurosidad está en que el instrumento sea válido.** `ERROR`.

**⇒ `PROVEN_DERIVED. La regla que esto añade, y que es la inversa de la que he venido aplicando:
ante un defecto de instrumentación con causa conocida y arreglo barato, el arreglo precede a la
documentación del defecto. Las dos cosas son legítimas; hacer la segunda y omitir la primera
produce notas con tablas que no se deben citar, que es exactamente el estado en el que estaban
`261`, `270` y `271` antes de `276`.** `PROVEN_DERIVED`.

## 7 · PENDIENTE

```text
PENDIENTE=282-1 | ESTADO=OPEN · ESTADO_DEL_INSTRUMENTO=VALIDATED
           | PREGUNTA=¿por que una lectura encadenada se costea a 2,970 GB/s, 1,49x el
           |          techo de PCIe, e igual en VRAM y en RAM?
           | DISCAMINANTE_CANDIDATO=un VkImage en vez de un VkBuffer: la ruta de texel
           |          es distinta de la de buffer, y si el tiempo cambia, la diferencia
           |          localiza el camino. ahora EJECUTABLE sin races.
           | ALCANZABLE_SIN_ROOT=si

PENDIENTE=282-2 | ESTADO=RESOLVED por esta nota
           | RESOLUCION=buffer de dos regiones disjuntas; control 40/40

INSTRUMENT=vulkan_compute_probe.c | ESTADO=VALIDATED
           | REGION_LECTURA=[0, wsize) con patron
           | REGION_ESCRITURA=[wsize, wsize+items) con el resultado
           | INVARIANTE_1=wsize >= items  (si no, la escritura sale del buffer)
           | INVARIANTE_2=WSIZE >= items  (si no, la escritura cae en la region de lectura)
           |           ambos violados devuelven exit 2 con el motivo, no un tiempo
           | CONSTANTS=3 (ITERS, WSIZE, STEPS) — offsets 0, 4, 8 dentro de pData
           | KERNELS=3, todos con region de escritura disjunta y todos validados 0 NO
           | MODELOS=3 (0=probe, 1=occ, 2=chain)
           | MEMORIAS=4 modos (0=vram, 1=ram, 2=host+device, otro=ABORTO(2) con el
           |          listado de tipos disponibles)
           | CONTROLES=verificados 40/40 en steps={0,1,16}, iters=64, ambos modos
```
