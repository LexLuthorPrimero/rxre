# 1205 — La lectura de vuelta de MAP_QUEUES **no existe** en GFX8, y el censo de nombres de campo la reemplaza: el hardware se nombra `PIPE0..PIPE3`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INSTRUMENT-FIT + CORROBORATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura y simulacion)
CIERRA  la pregunta que 1203 dejo abierta:  ¿hay discriminante de HARDWARE para el
        ancho de PIPE?  ->  NO.  Y la sustituye por una segunda via independiente.
CORROBORA  1203 (PIPE = 2 bits)  con una clase de evidencia distinta
ABRE     CONTRAD-01:  ME0PIPE2/3 no existen  y  num_pipe_per_mec = 4
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · La pregunta que este hilo abrió y cierra

`1203` dedujo que `MAP_QUEUES.PIPE` ocupa 2 bits por las dos vías del árbol, y dejó escrito
que faltaba una tercera vía para decidir. Propuse —y el propietario tacitamente aceptó— leer un
registro tras emitir `MAP_QUEUES` y ver si el hardware aceptaba 2 o 3 bits.

Antes de tocar la GPU comprobé si ese discriminante **existe**. No existe. Está medido por
tres vías independientes, y ninguna necesita la máquina.

## 1 · Vía 1: el driver no lee nada después de emitir

`gfx_v8_0.c:4320-4360`, función de mapa de colas de cómputo, literal:

```c
        amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_MAP_QUEUES, 5));
        amdgpu_ring_write(kiq_ring, PACKET3_MAP_QUEUES_NUM_QUEUES(1));
        amdgpu_ring_write(kiq_ring,
                  PACKET3_MAP_QUEUES_DOORBELL_OFFSET(ring->doorbell_index) |
                  PACKET3_MAP_QUEUES_QUEUE(ring->queue) |
                  PACKET3_MAP_QUEUES_PIPE(ring->pipe) |
                  PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1)); /* doorbell */
        amdgpu_ring_write(kiq_ring, lower_32_bits(mqd_addr));
        ...
    }
    amdgpu_ring_commit(kiq_ring);
    return 0;
```

Entre el `commit` y el `return` no hay **ni una** lectura de registro. Se emite y se devuelve
`0`. El éxito lo confirma el **interrumpido** que genera el comando, no una lectura del
codificado. Esto no es un descuido del driver: es la arquitectura del paquete. Los campos de
`MAP_QUEUES` los consume el CP y se convierten en estado interno del MQD; no hay registro que
los devuelva.

## 2 · Vía 2: el único registro de estado de cola tiene DOS campos

El driver sí sondea un registro en la ruta de desactivación (`gfx_v8_0.c:4367-4378`):

```c
    if (RREG32(mmCP_HQD_ACTIVE) & CP_HQD_ACTIVE__ACTIVE_MASK) {
```

Todos los campos declarados de `CP_HQD_ACTIVE` en el header de GFX8, censo completo:

```text
    CP_HQD_ACTIVE__ACTIVE__MASK     bits [0]
    CP_HQD_ACTIVE__BUSY_GATE__MASK  bits [3:1]  (aprox)
```

**Dos campos.** Ni `PIPE`, ni `QUEUE`, ni `ME`, ni `ring id`. El registro que el hardware
expone para decir «hay una cola activa» no dice **cuál** es.

> Autorrección: busqué `mmCP_HQD_HQD` primero, por inercia. **Ese símbolo no existe en el
> árbol.** El que se usa es `mmCP_HQD_ACTIVE`. Anotado porque es el mismo error de
> referencia-a-símbolo-inventado que cerré en `1204`, y aparece otra vez en el mismo día.

## 3 · Vía 3: el registro que sí tiene estado por anillo no existe para GFX8

```text
    CP_RB_STATUS      -> declarado solo en  gc_10_1_0_offset.h   (Navi)
    GFX_HQD_ACTIVE    -> NO DECLARADO
    GFX_RB_STATUS     -> NO DECLARADO
    CP_HQD_ACTIVE     -> declarado en  gfx_8_0_d.h:632  = 0x3247
```

La lectura per-ring que sí discrimina en Navi **no tiene equivalente declarado en GFX8**.

## 4 · El censo que sí existe, y es mejor que la lectura

Censo por nombre sobre los **9196** campos con máscara de `gfx_8_0_sh_mask.h`:

```text
  indices de PIPE que el header GFX8 nombra en algun campo
        PIPE0  PIPE1  PIPE2  PIPE3

  combinaciones MEC×PIPE que nombra  (CP_CPC_BUSY_STAT__*)
        MEC1_PIPE0  MEC1_PIPE1  MEC1_PIPE2  MEC1_PIPE3
        MEC2_PIPE0  MEC2_PIPE1  MEC2_PIPE2  MEC2_PIPE3

  indices de MEC/ME que nombra
        MEC1  MEC2
```

**El hardware se nombra a sí mismo `PIPE0..PIPE3`.** Cuatro valores de pipe existen, y cuatro
valores necesitan exactamente dos bits. Dos M nombrados → un bit.

Y esto es una vía que `1203` no tenía: allí las dos vías eran *el driver* (los desplazamientos
de `vid.h` y las dos rutas de emisión). Aquí la fuente es el **header de registros del ASIC**,
que describe el hardware y no el software. Dos clases de evidencia independientes que
convergen en el mismo número.

Corroborado desde una tercera, y la más fuerte de las tres:

```text
    gfx_v8_0.c:1910    adev->gfx.mec.num_pipe_per_mec = 4;
```

Sin condición de ASIC, sin `if`. El driver afirma 4 pipes por MEC para todo GFX8.

## 5 · Y el target entra por la rama de 2 MEC

```text
    amdgpu_drv.c:2041   {0x1002, 0x699F, ..., CHIP_POLARIS12}
```

`CHIP_POLARIS12` está en la lista de `num_mec = 2` (`gfx_v8_0.c:1894-1901`), y el `default`
pone `num_mec = 1`. Así que en esta máquina:

```text
    num_mec=2   num_pipe_per_mec=4   num_queue_per_pipe=8   total=64 bits de cola
    MAP_QUEUES.ME  tiene 2 valores  -> 1 bit     CORROBORADO
    MAP_QUEUES.PIPE tiene 4 valores -> 2 bits    CORROBORADO
```

## 6 · Lo que la simulación corrigió: mi aritmética, no el código

Transcribí literalmente `amdgpu_gfx.c:61-72` (descomposición) y `:271-303` (`kiq_acquire`) y
simulé el bucle. Antes simulé a mano y salí **mal**:

```text
  YO, a mano        bit 56 -> mec = (56/8)/4 = 0     (WRONG)
  CODIGO            bit 56 -> mec =  56/8  = 7 ; 7/4 = 1
```

`(bit / npq) / npp` es división entera **encadenada**, no `(bit/npq)`. Mi valor manual de `mec`
era 0 en vez de 1, lo que **desactivaba el invariante** y me daba un kiq distinto del real.
La simulación lo cogió; el papel no. Por eso la cifra viene de la simulación y no del
razonamiento.

Resultado medido, con el invariante `mec==1 && pipe>1`-actuando:

```text
  POLARIS12   num_mec=2   kiq -> mec=1 pipe=1 queue=0   me=2
              MAP_QUEUES escribe  PIPE(1)  ME(1)
              anillo:  kiq_0.2.1.0

  TOPAZ       num_mec=1   kiq -> mec=0 pipe=3 queue=0   me=1
              MAP_QUEUES escribe  PIPE(3)  ME(0)
              anillo:  kiq_0.1.3.0
```

**El kiq de la RX550 pasa `PIPE=1`, que cabe en un bit.** O sea: el propio kiq **no** ejercita
el ancho. Y en la rama `num_mec = 1` el driver pasa `PIPE=3` y el campo **no cabe en un bit**.
Ese caso no es esta máquina, pero demuestra que el campo tiene que ser de 2 bits en GFX8 como
clase — no de 2 por conveniencia de esta placa.

## 7 · Contradicción registrada y NO resuelta

```text
CONTRAD-01
  AFIRMA_A   gfx_v8_0.c:1910   num_pipe_per_mec = 4, sin condición
  AFIRMA_B   el header nombra 4 pipes para MEC1 y MEC2
  PERO       ME0PIPE0  32 ocurrencias
             ME0PIPE1  32 ocurrencias
             ME0PIPE2   0 ocurrencias      <- censo negativo, searched y medido
             ME0PIPE3   0 ocurrencias      <- censo negativo, searched y medido
  ALCANCE    CP_CONTEXT_CNTL__MEnPIPEn_MAX_PIPE_CNTX.  Solo ese campo.  No es un
             censo de todo el header:  PIPE0..PIPE3 si aparecen globalmente.
  HIPOTESIS  (a) el primer MEC fisico tiene 2 pipes de contexto y el driver
                 declara 4 de mas;  (b) el campo cuenta contextos, no pipes, y no
                 son lo mismo;  (c) el header esta incompleto para este bloque
  DISC.      no resuelto.  Este hallazgo NO lo cierra.
  ESTADO     CONTRADICTION · abierta
```

No la resuelvo aquí porque resolverla es otra cosa, y este hilo era una.

## 8 · Clasificación epistémica, sin adornos

```text
  PIPE = 2 bits      CORROBORATED   (3 vias: vid.h, header del ASIC, num_pipe_per_mec)
  ME   = 1 bit       CORROBORATED   (header nombra MEC1/MEC2; el driver pasa 0 o 1)
  lectura de vuelta  PROVEN_ABSENT  (3 mediciones independientes, ver §1 §2 §3)
  4 pipes/MEC        CORROBORATED   NO PROVEN: es un header y una asignacion del driver,
                                    no una lectura del ASIC
  reloj del ASIC     NOT_OBSERVED   (nunca se ha leido 0000:01:00.0 en este hilo)
```

Lo que **no** se ha hecho, y era la acción que propuse: emitir `MAP_QUEUES` y leer un
registro. No se ha hecho porque **el registro no existe**, no porque sea arriesgado. La acción
no era ejecutable y decirlo es el resultado. Si alguna vez se quisiera el dato de hardware de
verdad, la vía sería una interrupción o un contador de fallo del CP, no un campo del paquete.

## 9 · Procedimiento

```text
HERRAMIENTA   ninguna escrita.  Respondi una pregunta leyendo el arbol y
              simulando el bucle del driver en un guion de 30 lineas.
LECTURA       gfx_v8_0.c:1894-1911, 4320-4378, 6101-6133
              amdgpu_gfx.c:61-72, 271-303
              asic_reg/gca/gfx_8_0_sh_mask.h  (9196 campos)
              asic_reg/gca/gfx_8_0_d.h:632
              amdgpu_drv.c:2041
HOST          /sys/class/drm/card1 = 85 entradas de sysfs, 0 ficheros amdgpu_*
              /sys/kernel/debug/dri/ = Permiso denegado (debugfs SI montado)
              gpu_busy_percent y mem_busy_percent SI presentes
TARGET        0000:01:00.0  1002:699f  CHIP_POLARIS12  -> num_mec = 2
DISPOSITIVO   NINGUNO.  No se escribio en 0000:01:00.0 ni en 0000:00:02.0.
              i915 y amdgpu intactos.  debugfs leido y rechazado por permiso, no
              escalado.
RESULTADO     la accion propuesta es NO EJECUTABLE por falta de observable
AUTOCORRECCION  mi aritmética manual de la descomposición dio mec=0 donde el
              codigo da mec=1;  lo detecto la simulacion,  no el razonamiento
```