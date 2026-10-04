# 1046 — la acción discriminante se ejecuta: 8 CU, 320 KB de L1, línea de 64 B, y `perf/` vacío

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-KFD-TOPOLOGY
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST, sysfs, SIN ROOT
VINCULO=MICROARCH-GFX8.md § ACCION_DISCRIMINANTE (propuesta por el nodo, ejecutada aqui)
FUENTES=/sys/class/kfd/kfd/topology/nodes/1/{properties,caches/*,mem_banks/*,io_links/*,name}
ESTADO=PROBADO · la corroboracion triple del nodo SUBE de CORROBORATED a PROVEN
       contra la pieza, y dos cosas que eran NOT_DETERMINED quedan PROVEN
```

## Qué se iba a comprobar

El nodo `MICROARCH-GFX8` dejó escrita una acción que no ejecutaba, y la razon por la que era la
correcta: **dos lecturas de fichero de texto, sin MMIO, sin root y sin abrir
`/dev/dri`**. Su tesis era condicional y honesta:

> «Si `max_gprs != 256` o `max_waves_per_simd != 10` o `lds_size_in_kb != 64`,
> **CAE la corroboración triple de §2.3** y cae §3.3 con ella. Si coinciden,
> §2.3 sube de CORROBORATED a PROVEN contra la pieza y las once ideas dejan de
> estar bloqueadas por geometría.»

Eso es un experimento con falsador declarado. Se ejecutó.

## MEDIDO

### 1. Las cuatro propiedades esperadas: COINCIDEN LAS CUATRO

`/sys/class/kfd/kfd/topology/nodes/1/properties`, formato `clave valor`:

```
max_waves_per_simd        10        esperado 10   COINCIDE
lds_size_in_kb            64        esperado 64   COINCIDE
simd_per_cu                4        esperado  4   COINCIDE
wave_front_size           64        esperado 64   COINCIDE
```

La corroboración triple **no cae**. Sube. Y con ella dejan de estar bloqueadas por
geometría las ideas del usuario que dependen del presupuesto de ocupación:
**R-NEW-63** (barrido de ILP), **R-NEW-64** (matriz occupancy × ILP),
**R-NEW-68** (complejidad vs presión de registros), **N-INT-01** (latency hiding
vs throughput), **N-INT-02** (distancia load→use), **N-INT-04**, **N-INT-05**,
**N-INT-08** (SGPR vs VGPR), **N-INT-10**, **N-INT-12**, **N-INT-63**.

### 2. `8 CU`, que el nodo había marcado `NOT_FOUND`

El nodo escribió: *«Número de CU / CU-por-SH / SH-por-SE / SE: viene del VBIOS
(`amdgpu_atombios.c:744-750`). NOT_FOUND en el corpus. NO_NUMERADO, no
inventado.»* Con razón: no está en el código.

Está en sysfs:

```
simd_count                32
simd_per_cu                4
  ->  32 / 4  =  8 CU
```

Y sale corroborado por una segunda vía independiente: **16 cachés L1** para 8
unidades de cómputo son 2 por CU.

### 3. La jerarquía de memoria, que era `NOT_DETERMINED`

`caches/*/properties`, 16 entradas, **todas `level 1`**:

```
nivel=1  size=16 KB  type=9    x12 caches  ->  192 KB
nivel=1  size=32 KB  type=10    x4 caches  ->  128 KB
cache_line_size = 64 B   en las 16, sin excepcion
total de L1 = 320 KB
L2 = NO APARECE en el informe de KFD
```

**`cache_line_size = 64` es el número que faltaba.** Toda la línea de ideas sobre
acceso a memoria del usuario —**R-NEW-06** (roofline), **R-NEW-07**, **R-NEW-09/10**
(umbrales de textura), **N-INT-09** (localidad temporal vs espacial),
**N-INT-10** (divergencia de accesos), **N-INT-11**, **N-INT-14** (MLP),
**N-INT-16** (capacidad de caché), **N-INT-17** (thrashing), **N-INT-18**
(reuse distance)— depende de la línea de caché y del tamaño de la L1. Ya están.

Que **no haya L2** en el informe de KFD coincide con lo que el nodo de memoria
encontró en el driver: `polaris12_cache_info` es un `#define` de
`carrizo_cache_info` con un `TODO: Add L2 Cache information` literal. **Dos
fuentes independientes dicen lo mismo**, y por fuentes independientes, la
ausencia de L2 deja de ser «no lo sé» y pasa a **lo que el silicio declara de sí
mismo**.

### 4. VRAM: exactamente 2 GiB, y el reloj de memoria

```
mem_banks/0/properties
  heap_type       2
  size_in_bytes   2147483648      = 2 GiB exactos
  width           64
  mem_clk_max     1500
```

El contrato de objetivo decía «~2 GiB». Es **2 GiB exactos**, medido. Y
`mem_clk_max 1500` es el primer número de reloj de memoria que aparece en todo el
proyecto por una vía que no es un nombre de registro.

### 5. `perf/` VACÍO — la línea de contadores queda cerrada por medición

```
/sys/class/kfd/kfd/topology/nodes/1/perf/   ->  0 entradas
```

El mapa de contadores sabía que el path de perfmon de GFX8 no está en el kernel.
Esto es **la misma conclusión por otra vía**, y la cierra: no es que el código no
esté, es que **el propio driver no publica ningún contador por esta interfaz**.

### 6. Identidad de la ASIC, legible y legible por humans

```
/sys/class/kfd/kfd/topology/nodes/1/name         ->  polaris12
/sys/class/kfd/kfd/topology/nodes/1/properties:
  device_id             27039   = 0x699F     (coincide con el PCI id medido)
  vendor_id             4098    = 0x1002
  gfx_target_version    80003              (GFX8.0.3)
  array_count           2
  simd_arrays_per_engine 1
  cu_per_simd_array     5                  <-- ver CONTRADICCION
  num_cp_queues         24
  num_sdma_engines      2
  num_sdma_queues_per_engine 2
  max_slots_scratch_cu  32
  ctl_stack_size        4096
  cwsr_size             2789376
  max_engine_clk_fcompute 1071
```

`name = polaris12` cierra el `TARGET_MATCH` de §4 por una vía que no es PCI.

### 7. Nodo 0 = la CPU, y confirma el contrato de objetivo

```
nodes/0/properties:  cpu_cores_count 8    simd_count 0
```

**8 núcleos** con `simd_count 0`. El i7-4790 del contrato tiene 4 núcleos / 8
hilos; KFD cuenta 8. Es el número de hilos, no de núcleos físicos, y queda
registrado como tal en vez de ajustarla para que cuadre.

## CONTRADICCIÓN que queda abierta, y no se cierra

```
simd_count 32 / simd_per_cu 4  ->  8 CU
cu_per_simd_array             ->  5
```

**5 × 1 array = 5, no 8.** Las dos cifras son del mismo fichero y no reconcilian
con la aritmética de `simd_count`. No se elige una: se registra. La vía que
decidiría es el VBIOS (`amdgpu_atombios.c:744-750`), que no está en el corpus, y
`io_links/0` tampoco ayuda (`min_bandwidth 0`, `max_bandwidth 0`).

Lo que **no** se afirma: que KFD se esté equivocando. Lo que se afirma: que hay
dos cifras incompatibles y que una de ellas no puede ser la cuenta de CU sin más
evidencia.

## Dos correcciones a mí mismo, porque las cometí durante esta misma acción

1. **Mi primer parser de KFD devolvió «vacío» y mi veredicto fue `DIFFERES`.**
   Las propiedades no estaban vacías: **el formato es `clave valor` separada por
   espacio, no `clave=valor`**, que es lo que yo asumí. Lo vi porque el
   veredicto era absurdo — cuatro propiedades ausentes y ninguna leída — y fui al
   crudo. Un `DIFFERES` inventado por un parser que no sabe leer el formato es
   exactamente el falso negativo que este proyecto lleva la sesión desmontando, y
   lo he cometido yo en este turno.
2. **Conté mal las cachés.** De un vistazo al listado en crudo escribí «8 de 16 KB
   y 8 de 32 KB». El agrupamiento correcto da **12 de 16 KB y 4 de 32 KB**. No
   publiqué esa cuenta: la rehice antes de escribirla aquí. Y una consecuencia
   honesta de eso: **la lectura «16 KB de datos + 32 KB de instrucción por CU» NO
   se sostiene** con 12 y 4. Queda `NOT_DETERMINED`; lo único firmado es «16
   cachés L1, línea 64 B, 12 de 16 KB y 4 de 32 KB, sin L2».

## Lo que queda abierto, con el dueño

- **`max_gprs` sigue sin leerse.** Es la segunda pata de la acción discriminante y
  está en `/sys/kernel/debug/dri/1/amdgpu_gca_config`. `debugfs` está montado pero
  **no es legible por uid 1000** (`PermissionError` medido), y este usuario no
  está en `wheel` ni ejecuta como root. **La pata que confirma no requiere root;
  la que falta, sí.** Las otras tres coinciden, así que §2.3 no cae: sube
  con tres de cuatro corroboraciones independientes, y la cuarta queda
  `NOT_DETERMINED` con la causa nombrada.
- **La identidad de CU (5 vs 8).** Dueño: VBIOS, ausente del corpus.
- **Qué significan `type 9` y `type 10`.** KFD no los decodifica aquí; la
  asignación a «datos» / «instrucción» es `NOT_DETERMINED`.

## Por qué esto importa más de lo que parece

Once ideas del usuario dependían de la geometría de ocupación y estaban
bloqueadas por una cifra que el corpus no tiene. **No hacía falta root, ni MMIO,
ni tocar la GPU, ni el VBIOS**: estaba en un fichero de texto de sysfs que el
driver ya escribía al arrancar. El bloqueo nunca fue de acceso. Era de que nadie
miró el fichero que el propio kernel tenía delante.

Y el hallazgo 1045 sigue en pie, sin cambiar: **`max_gprs` sí requiere root**, y
la vía MMIO por ioctl requiere abrir el nodo render, que reanuda la GPU de
display. Aquí no hizo falta ninguna de las dos cosas. Por eso esto avanza donde
lo otro no pudo: **no porque sea más valiente, sino porque era más barato.**