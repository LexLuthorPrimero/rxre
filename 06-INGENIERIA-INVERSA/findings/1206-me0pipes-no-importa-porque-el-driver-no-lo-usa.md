# 1206 — `CONTRAD-01` resuelta: `ME0PIPE2/3` no existen, y **no importa**, porque el driver GFX8 nunca escribe ME0

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=CONTRADICTION-RESOLUTION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
RESUELVE   CONTRAD-01, abierta por 1205
ESTADO     CONTRADICTION -> RESOLVED  ·  no-load-bearing para este target
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 0 · Lo que estaba en contradicción

```text
  AFIRMA_A   gfx_v8_0.c:1910   adev->gfx.mec.num_pipe_per_mec = 4,  sin condicion
  AFIRMA_B   el header del ASIC nombra 4 pipes para MEC1 y para MEC2
  PERO       ME0PIPE2 y ME0PIPE3 tienen 0 ocurrencias en gfx_8_0_sh_mask.h
             (y 32 cada una para ME0PIPE0 y ME0PIPE1)
```

Tres hipótesis registradas en `1205`: (a) el primer MEC tiene 2 pipes y el driver declara de
más, (b) el campo cuenta contextos y no pipes, (c) el header está incompleto. Ninguna medida.

## 1 · Hipótesis (c) queda muerta: la asimetría es sistemática, no de GFX8

Mismo censo sobre cuatro generaciones de GCN:

```text
    gfx_6_0   10 combinaciones
    gfx_7_2   10 combinaciones
    gfx_8_0   10 combinaciones
    gfx_8_1   10 combinaciones
        las MISMAS 10 en las cuatro:
        ME0PIPE0 ME0PIPE1 ME1PIPE0 ME1PIPE1 ME1PIPE2 ME1PIPE3
        ME2PIPE0 ME2PIPE1 ME2PIPE2 ME2PIPE3
```

Un header incompleto lo estaría en uno o dos. Que seabidentical en cuatro generaciones
separadas por cuatro años de silicio es evidencia de que la asimetría **es del hardware**, no
de la documentación.

## 2 · Hipótesis (b) queda muerta: `MEnPIPEn` viene de TRES registros distintos

Mi censo de `1205` mezclaba nombres de tres registros con tres significados distintos. El
desglose lo deja claro:

```text
  registro                 campos                        que cuenta
  ------------------------------------------------------------------
  CP_CONTEXT_CNTL 0x30ad   ME0PIPE0, ME0PIPE1            limites de contexto
                             MAX_PIPE_CNTX, MAX_WD_CNTX

  CP_CPC_BUSY_STAT          MEC1_PIPE0..3, MEC2_PIPE0..3   ocupacion

  GRBM_STATUS2     0x2002   ME0PIPE1, ME1PIPE0..3,       peticiones
                             ME2PIPE0..3                    pendientes

  GRBM_READ_ERROR2          ME1PIPE0, ME2PIPE3            quien leyo
```

Y hay un detalle que mi censo anterior **dio por bueno y era falso**: dije que `GRBM_STATUS2` nombraba
`ME0PIPE0` y `ME0PIPE1`. **No nombra `ME0PIPE0`.** El desglose de `GRBM_STATUS2` con sus
posiciones reales:

```text
    ME0PIPE1_CMDFIFO_AVAIL   bits [3:0]   MASK 0x0f
    ME0PIPE1_CF_RQ_PENDING   bit  [4]      MASK 0x10
    ME0PIPE1_PF_RQ_PENDING   bit  [5]      MASK 0x20
    ME1PIPE0_RQ_PENDING      bit  [6]      MASK 0x40
    ME1PIPE1_RQ_PENDING      bit  [7]      MASK 0x80
    ME1PIPE2_RQ_PENDING      bit  [8]      MASK 0x100
    ME1PIPE3_RQ_PENDING      bit  [9]      MASK 0x200
    ME2PIPE0_RQ_PENDING      bit  [10]     MASK 0x400
    ME2PIPE1_RQ_PENDING      bit  [11]     MASK 0x800
    ME2PIPE2_RQ_PENDING      bit  [12]     MASK 0x1000
    ME2PIPE3_RQ_PENDING      bit  [13]     MASK 0x2000
    RLC_RQ_PENDING           bit  [14]     MASK 0x4000
```

Los bits **[4..13] son diez slots contiguos**, sin huecos: uno para ME0, cuatro para ME1,
cuatro para ME2, uno para el RLC. **La estructura reserva un solo slot de pipe para ME0.** Y
`ME0PIPE0` no tiene slot en este registro en absoluto.

Así que (b) era falsa en su forma buena — no es que el campo cuente contextos en vez de
pipes; `CP_CONTEXT_CNTL` sí cuenta contextos, pero es *otro* registro y no es la fuente de la
ausencia.

## 3 · Lo que resuelve de verdad: el driver nunca escribe ME0

Las dos asignaciones de `ring->me` que existen para GFX8, literales:

```text
    gfx_v8_0.c:1857        ring->me = mec + 1;
    amdgpu_gfx.c:295        ring->me = mec + 1;
```

Censo de **todas** las asignaciones del driver, por fichero:

```text
    amdgpu_gfx.c:295            mec + 1     <- la ruta comun
    gfx_v6_0.c:3159            = 1
    gfx_v7_0.c:4315            mec + 1
    gfx_v8_0.c:1857            mec + 1
    gfx_v10_0.c:4659           = me        (solo NPI, no GFX8)
    gfx_v10_0.c:4690           mec + 1
    gfx_v11_0.c:1149           = me        (solo NPI)
    gfx_v12_0.c:983            = me        (solo NPI)
    amdgpu_ring.c:418          = 0         <- desmontaje
```

El `+1` no es cosmético: en esta familia el hardware **numera los MEC desde 1**, y el campo de
1 bit de `MAP_QUEUES` lleva `ring->me == 1 ? 0 : 1`. O sea que `me = mec + 1` es exactamente la
conversión de índice 0-based a índice 1-based que el hardware usa.

Para esta máquina:

```text
    num_mec = 2   (CHIP_POLARIS12, gfx_v8_0.c:1894-1901)
    me = mec + 1  ->  me ∈ {1, 2}  =  MEC1, MEC2
    me = 0        ->  IMPOSIBLE por construccion
```

`amdgpu_ring.c:418` es `ring->me = 0` dentro de `amdgpu_ring_free_kernel()`, o sea reset de
desmontaje. No es una ruta que emita `MAP_QUEUES`, y lo comprobé por contexto y no por el
nombre de la función.

## 4 · Resolución

```text
CONTRAD-01   RESOLVED

  NO es que el driver declare 4 pipes de más para esta placa.
  NO es que el header esté incompleto.
  NO es un campo que cuente otra cosa.

  Es que el hardware de esta familia reserva UN slot de pipe para el primer
  MEC en GRBM_STATUS2, y cuatro para cada uno de los otros, y el driver
  NO NUNCA USA ESE PRIMER MEC:  en GFX8 me = mec + 1 y esta placa tiene
  num_mec = 2,  asi que solo escribe MEC1 y MEC2.

  Los dos MEs que el driver usa son precisamente los que nombran los cuatro
  pipes.

  ESTADO PARA ESTE TARGET:  no-load-bearing.
  PIPE = 4 valores = 2 bits   CORROBORADO  (1205, reforzado aqui)
  ME   = 2 valores = 1 bit    CORROBORADO  (1205, reforzado aqui)

  LO QUE QUEDA SIN RESOLVER, y no se resuelve aqui:
  por qué el hardware reserva un slot para ME0.  Es una pregunta sobre el
  silicio,  no sobre el driver,  y este hilo es sobre el driver.  Queda
  como pregunta abierta,  no como contradiccion.
```

## 5 · Lo que este hallazgo no dice

```text
  NO dice que ME0 tenga 2 pipes.       Que en GRBM_STATUS2 tenga 1 slot no
                                       prueba nada sobre cuantos pipes hay:
                                       un slot de estado y un pipe son cosas
                                       distintas.  NO SE DETERMINADO.
  NO dice que el driver pueda usar ME0.  Si num_mec fuera 3,  usaria ME3,  que
                                       tampoco esta nombrado.  El limite es
                                       dos MEs,  y el hardware expone
                                       estado de pipeline hasta dos.
  NO ha leido ni un registro de la GPU.  RUNTIME=NOT_RUN.
  NO ha tocado 0000:01:00.0 ni 0000:00:02.0.
```

## 6 · Procedimiento

```text
PREGUNTA     ¿el primer MEC de GFX8 tiene 2 pipes o 4?
ACCION       censo por nombre de campos de registro, y lectura de las dos
             asignaciones de ring->me
DESCRITO     tres registros distintos usaban el prefijo MEnPIPEn con
             tres significados,  y mi censo los mezclaba
RESULTADO     las tres hipotesis de 1205 quedan fuera,  y la contradiccion
             es real pero no aplica a esta placa
DISC.        la diferencia de comportamiento entre el primer MEC y los otros
             dos.  NO ES UNA MEDIDA DE LA GPU:  es el driver el que nunca
             selecciona el primero,  no el hardware el que lo rechaza
LECTURA      gfx_8_0_sh_mask.h,  gfx_8_0_d.h:337 y :863,
             gfx_v8_0.c:1857, 1894-1911,   amdgpu_gfx.c:61-72, 295-296,
             amdgpu_ring.c:405-419,   amdgpu_drv.c:2041
DISPOSITIVO  NINGUNO
RUNTIME      NOT_RUN.  dmesg NO se pudo leer:  "Operación no permitida".
             Se dejo constancia,  no se escalo.
MEDIO        4 headers GCN para el censo comparativo
AUTOCORR.    en 1205 afirmé que GRBM_STATUS2 nombraba ME0PIPE0 y ME0PIPE1.
             No nombra ME0PIPE0.  Lo detectó el desglose por posicion de bit.
```

> Nota sobre el método. El error de `1205` fue **contar nombres sin mirar en qué registro
> estaban**. Un nombre de campo es una etiqueta plana; el mismo prefijo significa cosas
> distintas en registros distintos, y un censo que no los separa cuenta campos que no
> compiten entre sí. Cuando el número salga raro, la pregunta correcta no es «¿qué nombres
> hay?» sino «¿de qué registro es cada nombre y qué cuenta?».