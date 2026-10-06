# 1582 — Ítem 5 cerrado: el trío `LOAD_*_REG` es **inalcanzable en GFX8 por construcción**, no simplemente no usado; y la permutación de opcodes de `sid.h` que registré en `1224` **tiene mecanismo y es una instantánea congelada**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CLOSEOUT · ALCANCE-DE-ALCANZABILIDAD
CLASSIFICATION=EVIDENCIA-POR-GRAFO-DE-INCLUDES+EVIDENCIA-POR-CUENTA-DE-EMISIONES+EXPLICACIÓN-DE-ANOMALÍA
MODIFICATIONS=1224 §"las 4 anomalías de opcode están todas en sid.h"  (ahora con causa)
MODIFICATIONS=1230 §pendientes  (el bloque LOAD_*_REG sale de la lista)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   el quinto hueco de riesgo cero
```

## 1 · La pregunta que había que responder, y que no era "¿se usa?"

Mi ítem 5 estaba escrito así:

```text
  "¿Es alcanzable el trío LOAD_SH_REG / LOAD_CONFIG_REG / LOAD_CONTEXT_REG?
   Sé que hay 0 emisiones.  Lo que NO he mirado es si existe alguna bandera
   o compuerta que los habilite.  Si no la hay,  sid.h deja de ser una
   divergencia latente y pasa a ser PROVEN_ABSENT."
```

Eso es exactamente el patrón que en `1580` me produjo una afirmación falsa: dar
por hecho que el mecanismo es una bandera. **Lo busqué de la forma que lo podía
refutar**, que es contar en toda la superficie de emisión, no leer el punto de uso.

## 2 · La cuenta de emisiones, en tres presupuestos distintos

```text
  token                       .c      .h
  PACKET3_LOAD_SH_REG         0        6
  PACKET3_LOAD_CONFIG_REG     0        6
  PACKET3_LOAD_CONTEXT_REG    0        6
```

Y **`grep` del nombre sin el prefijo `PACKET3_`, en `amdgpu/*.c` y `pm/`**: vacío.
No hay ningún constructor genérico que los arme por nombre.

**Cero en los dos presupuestos.** Eso es `NOT_FOUND` sobre dos búsquedas, y no
`PROVEN_ABSENT` todavía — para eso hace falta el alcance, que es lo de abajo.

## 3 · El alcance que convierte `NOT_FOUND` en `PROVEN_ABSENT`, para esta placa

La emisión de paquetes en GFX8 es **literal**, no dirigida por tabla. Medido sobre las
cabeceras que `gfx_v8_0.c` enlaza realmente:

```text
  amdgpu.h  amdgpu_gfx.h  amdgpu_ring.h  vi.h  vi_structs.h  vid.h
  amdgpu_ucode.h  amdgpu_atombios.h  atombios_i2c.h  clearstate_vi.h

  soc15d.h   no      cikd.h   no      nvd.h   no      sid.h   no
  vid.h      SI
```

Y sus 56 emisiones son todas de la forma `amdgpu_ring_write(ring, PACKET3(...))`,
que es una llamada con el opcode en la línea.

**Consecuencia:** para que uno de esos tres paquetes saliera en esta GPU, alguien
tendría que escribir la llamada literal. **No hay ninguna en todo el árbol.** No es
que estén deshabilitados: es que **en el camino de GFX8 no existe el despachador que
los haría alcanzables**, porque el camino de GFX8 es anterior a las tablas de tipos de
paquete. Las tablas están en `soc15d.h` / `cikd.h` / `nvd.h`, y ninguna la enlaza
`gfx_v8_0.c`.

```text
  ESTADO:  PROVEN_ABSENT  para la via de emision de GFX8
  ALCANCE: todo .c del arbol amdgpu/  y  pm/   (contado,  no supuesto)
  NO AFIRMO:  que el opcode este ausente del hardware.  Solo que este driver,
             por esta placa,  no tiene forma de emitirlo
```

## 4 · Y el hallazgo de verdad: cuatro diccionarios coinciden y `sid.h` está permutado

```text
  cabecera      LOAD_CONFIG   LOAD_CONTEXT   LOAD_SH_REG
  ------------------------------------------------------------
  sid.h            0x5F          0x60           0x61
  vid.h            0x60          0x61           0x5F
  soc15d.h         0x60          0x61           0x5F
  cikd.h           0x60          0x61           0x5F
  nvd.h            0x60          0x61           0x5F
```

**Cuatro diccionarios independientes coinciden. `sid.h` solo, tiene los tres
corridos un puesto.** Y la consecuencia sería grave si ambos se mezclaran: con el
número de `sid.h` y los macros de campo del otro, se emitiría un paquete
distinto del que se cree.

**Pero no se mezclan, y esto es lo que lo cierra:**

```text
  quien incluye sid.h
    amdgpu/gfx_v6_0.c      amdgpu/dce_v6_0.c      amdgpu/si.c
    amdgpu/si_dma.c        amdgpu/si_ih.c         amdgpu/uvd_v3_1.c
    amdgpu/vce_v1_0.c      pm/legacy-dpm/si_dpm.c pm/legacy-dpm/si_smc.c
```

**Todo GFX6 y toda la pila legacy de Southern Islands. GFX8 no aparece.** El
diccionario de esta placa es `vid.h`, y ahí la numeración es la que coinciden los
cuatro.

## 5 · El mecanismo de la permutación, que es la explicación que le faltaba a `1224`

En `1224` registré, sin explicar, que **"las 4 anomalías de opcode están todas en
`sid.h`; ninguna en `vid.h`"**. Ahora tengo la causa, y es mundane:

```text
  vid.h:336   PACKET3_LOAD_UCONFIG_REG   0x5E
  vid.h:337   PACKET3_LOAD_SH_REG        0x5F
  vid.h:338   PACKET3_LOAD_CONFIG_REG    0x60
  vid.h:339   PACKET3_LOAD_CONTEXT_REG   0x61

  sid.h:520   PACKET3_LOAD_CONFIG_REG    0x5F
  sid.h:521   PACKET3_LOAD_CONTEXT_REG   0x60
  sid.h:522   PACKET3_LOAD_SH_REG        0x61
```

**`sid.h` no tiene `PACKET3_LOAD_UCONFIG_REG`.** Es un paquete que se añadió después.
Cuando entró en el diccionario vivo ocupó el hueco `0x5E`… y los tres anteriores
subieron un puesto: `SH` pasó de `0x61` a `0x5F`, `CONFIG` de `0x5F` a `0x60`,
`CONTEXT` de `0x60` a `0x61`. **`sid.h` es una instantánea anterior a ese paquete y
no se actualizó**, porque el código que la usa —GFX6 y SI— nunca va a encontrar
`LOAD_UCONFIG_REG`, así que el corrimiento no le afecta.

O sea: **no es un error del driver. Es un diccionario congelado, y congelado
correctamente para las ASICs a las que sirve.** Eso es un ejemplo de divergencia
aparente que no es divergencia, y por eso vale la pena haberlo medido: la forma de
distinguirlo fue contar cuántos ficheros usan cada diccionario, no comparar números.

**Y explica por qué las anomalías de `1224` caen todas ahí.** Es una sola causa, no
cuatro.

## 6 · Procedimiento y alcance

```text
PREGUNTA   si el trio LOAD_*_REG es alcanzable en GFX8,  y si la permutacion de
           opcodes de sid.h es un error o una instantanea congelada
FUENTES    amdgpu/sid.h,  la seccion de opcodes
           conteo del token en .c y en .h por separado  (no con grep -c,  que
           cuenta lineas)
           las cabeceras que enlaza gfx_v8_0.c,  una por una
           el bloque 0x5E-0x61 en vid.h  frente al bloque 0x5F-0x61 en sid.h
           quien incluye sid.h,  fichero por fichero
MEDIDO     0 emisiones de los tres en cualquier .c del arbol
     0 apariciones del nombre sin prefijo en amdgpu/*.c  y  pm/
     gfx_v8_0.c enlaza vid.h  y  NO sid.h,  ni soc15d.h,  ni cikd.h,  ni nvd.h
     su emision de paquetes es literal en las 56 apariciones
     LOAD_SH_REG: 0x61 en sid.h   frente a 0x5F en vid/soc15d/cikd/nvd
     PACKET3_LOAD_UCONFIG_REG = 0x5E existe en vid.h  y  NO existe en sid.h
     sid.h lo usan 9 ficheros,  todos de GFX6  o de la pila legacy de SI
     GFX8 no aparece en ninguno de los 9
DESVIO MIO  ninguno medible.  Y anoto la tentacion:  el item estaba escrito
     asumiendo que el mecanismo era una bandera.  No lo era.  Si hubiera
     insistentido en esa suposicion,  el cierre habria sido falso por la misma
     via que en 1580
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 7 · Lo que sigue

```text
  huecos de riesgo cero de mi lista de siete:  4 · 7     (1, 2, 3, 5 y 6, cerrados)

  y con esto queda el otro bloque de PACKET3_LOAD_* sin resolver,  resuelto,
  que era el bloque que 1224 dejo abierto:
    LOAD_SH_REG / LOAD_CONFIG_REG / LOAD_CONTEXT_REG  ->  PROVEN_ABSENT en GFX8
    y la permutacion de sid.h  ->  instantanea congelada,  con mecanismo

  item 4 (comparar POR OFFSET las copias smu71/72/73/75)  y  item 7 (cobertura de
  descubrimiento de RXRE con un denominador que no sea mio)  quedan.  Los dos
  tienen valor de metodo,  no de placa

  y sigue en pie lo unico que cierra soft_regs_start:  el valor de
    SMC_RAM[0x20030].  Con la receta del driver (1579),  las dos direcciones
    confirmadas en los tres linajes,  y pendiente de tu OK
```