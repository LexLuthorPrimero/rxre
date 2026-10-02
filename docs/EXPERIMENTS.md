# EXPERIMENTS — qué se ejecutó, qué dio, y qué NO se debe repetir

> Un experimento se registra por lo que **descarta** tanto como por lo que produce.
> Un experimento maldito no es un gasto: es una rama eliminada. Lo que no se registra es
> una rama que vuelve a abrirse dentro de tres meses.
>
> `LAST_SCAN: 2026-10-01 11:20 -03:00` ·DAQel histórico procede de
> `MASTER-RESEARCH-STATUS.md` (00-INDICE), `PATCH-REGISTRY-FINAL.md`,
> `PROBLEM-STATUS-FINAL.md`, `CHANGELOG.md` y `90-SELECTIVE-INTEGRATION/`.

---

## 1 · Estado de la experimentación

```
EN CURSO        NINGUNO
AUTORIZADO      NINGUNO
PREPARADO       F2 (AD-12)  -- escrito, con autovalidación, sin ejecutar
               F1 (orden del invalidate) -- discriminante redactado por 017 §5,
                                          BLOQUEADO por autorización
LA LÍNEA A      100 % estática. 0 escrituras a hardware en toda su historia
LA LÍNEA B      1 experimento con resultado (shader BC3), 1 preparado (AD-12)
```

## 2 · Experimentos de telemetría (línea de septiembre) — CERRADOS

### R-4A · Ancho de banda PCIe — `COMPLETADA`

```
ENLACE Gen2 x4        VERIFIED por el techo del root port 00:01.0
PCIE teórico           2.0 GB/s        DERIVED (sentido)
VRAM teórica          96-112 GB/s     ESTIMATED
ratio enlace/VRAM     corregido x48-80
REAL                  UNKNOWN         <-- no se midió
LO QUE DESCARTA       que el ancho de banda del enlace sea la causa de nada
LO QUE NO DESCARTA    el rendimiento real. Sigue UNKNOWN
```

### R-4B v2.3 · Governor read-only — `INCONCLUSIVE`

Es el experimento con más historia del proyecto, y el que mejor ilustra por qué un
resultado negativo hay que conservarlo.

```
PROTOCOLO     v2.2 y v2.3, con la única variación documentada ANTES de ejecutar
FASE 1        15/15 bloques con SCLK 1071 MHz sostenido en los 3 passes
              T_max 86 grados, sin degradacion
              histéresis 0.26 %  ->  GATEs PASS
              FREEZE T=9.168 ms  s*=0.75  sha256 6b6d6952…
FASE 2        8/8 trials ejecutados
VEREDICTO     DIAGNOSTIC / THERMALLY CONFOUNDED — NOT FOR VERDICT
              R1-R7 NO declarados: ni PASS ni FAIL
              El veredicto global es INCONCLUSIVE / INCONCLUSIVE, nunca SUPPORTED
S2            INICIADA y PARADA D durante el cooldown p2->p3, antes de Phase 2
              NO se reintenta
```

**La causa de la contaminación está identificada y es la parte útil**: Phase 2 heredó
84 °C de Fase 1 y 91-92 °C entre trials. La causa conocida es **≥92 °C con N=2**, no la
duración del trial. Los umbrales que quedan en pie:

```
50 grados   condición de entrada/cooldown EJECUTADA en v2.3
35 grados   opción especial NO verificada
90 grados   criterio de confound de ventana
96 grados   abort configurado, NO un límite térmico validado de la placa
t90         NO EXISTE un valor universal. t90≈221 s es extrapolación lineal histórica
```

### R-4C · Jitter / TAA — `COMPLETADA`

```
NIVEL A      MAE = 0.0 px
NIVEL B      MAE = 3.66e-10 px  desde matriz host-visible
8/8 celdas   PASS
ANV          sin devices  ->  NO EJECUTADO
```

Un resultado `0.0` exacto y otro `3.66e-10` en el mismo experimento: el segundo es el
que importa, porque demuestra que la medición tiene resolución y no está comparando
ceros con ceros.

### R-3 / R-3.1 · Catálogo y fusiones — `COMPLETADAS`

```
R-3.1         7 fusiones, 0 PROVEN NOVEL
              FUSION-04 READY · FUSION-02/05/06 REJECTED · FUSION-07 BLOCKED
CATÁLOGO      GFX8 source-level. GRBM=2 / SQ=4 NO validan el ASIC
```

`GRBM=2 / SQ=4` no validan el ASIC: el registro da 4 canales y la silicio tiene 2. Un
número de un registro que no corresponde al hardware no es un dato del hardware.

### M1 · Cap 35/30 W — `NO DISCRIMINATIVO`

```
WORKLOAD      vkmark shading:phong 1080p, cap sostenido 35/30 W, 10 corridas pareadas
RESULTADO     power1_input @35 W = 12.27 W
              -> la compuerta <27 W se activa  ->  NO DISCRIMINATIVO
              Delta FPS y Delta SCLK pareados = 0
```

**El por qué importa más que el resultado**: el cap de 25 W **nunca liga** con una
carga real. La demanda máxima medida de esta GPU es 9.4-13.6 W, así que cualquier cap
por encima de eso no hace nada. Un experimento que no mueve la variable que dice mover
no mide nada, y hay que decirlo en el informe en lugar de reportar "sin diferencias".

## 3 · Experimentos que se DESCARTARON con evidencia

Cada uno con lo que elimina, para que no se reintenten:

| Hipótesis descartada | Experimento | Evidencia |
|---|---|---|
| El cap 25 W liga SCLK en cargas ligeras | Fase B | curva plana |
| El régimen E1/E3 es por cap simple o soak+cap hasta 70-71 °C | Fase B + EP-06 | sin pinzado |
| kalm o el gobernador causaron el régimen histórico | journal 17/09 vs 18-19/09 | 17/09 sin kalm, 18-19/09 con kalm activo y libre |
| Mesa CUSTOM causa el consumo de E5 | EP-05 | CUSTOM == STOCK, libs verificadas |
| E1/E3 muestrearon otra GPU | EP-08 | la telemetría es de la RX550 real |

## 4 · Lo que NO se reproduce, y por qué no es un fallo

```
TODO EL RÉGIMEN E1/E3/E5 DEL 17/09   [NO REPRODUCIBLE]
  power1 == cap 25 W · SCLK 350-390 · MCLK ~1250-1500 · 74-92 °C
  phong 1285 fps · desktop 443@1080@35 W · jelly 691@35 W

NINGÚN PARÁMETRO AUTORIZADO LO REPRODUJO
  ni cap, ni calor, ni kalm, ni Mesa stock, ni Mesa CUSTOM

NO ES UNA ESPECIFICACIÓN DE RENDIMIENTO ESPERADO
```

Lo que sí se sabe del estado actual, que es lo contrario de ese régimen:

```
draw medido      9.4-13.6 W    el cap de 25-35 W NO liga
máximo real      13.6 W        2560x1440 texturizado (EP-06)
SCLK en carga    1071
MCLK en carga    625           con pico transitorio de 1500
temperatura      42-58 °C      corridas cortas · plateau soak 64 °C
GL jellyfish 640p NO ES SCLK-BOUND  (FPS ~igual en 340-1071 MHz)
```

La lección estructural de esta línea, y la razón de que esté aquí: **el régimen
histórico nunca se explicó, y el estado actual se midió**. Un informe que presentara
los 74-92 °C como "el comportamiento de esta GPU" sería falso; uno que presentara los
42-58 °C como "el comportamiento de esta GPU" también, porque no explica la
discrepancia. La postura correcta es la que está escrita en `00-INDICE/FINAL-RESEARCH-STATUS.md`
de la línea histórica: **`[NO REPRODUCIBLE]`, no tratar como hecho**.

## 5 · Experimento B — autorizado en política, no ejecutado

```
QUÉ ES      el experimento B no está definido en el árbol de forma localizable
PARA QUÉ    commit 65447aa cambió insmod/rmmod de deny a ask "para el experimento B"
            -- 2026-10-01 06:39, el mismo día que seonomyaron las puertas
ESTADO      La política lo PIDE. La GPU sigue intacta, ningún módulo cargado
LO QUE FALTA  Una definición escrita del experimento B, sus criterios PASS/FAIL, y su
            prueba de recuperación. Sin las tres, "experimento B" es una etiqueta
PRERREQUISITO  SSH-RECOVERY-PATH-2026-10-01.md está en PARTIAL, 1 de 3 condiciones:
            una sesión de agente cuelga de la sesión gráfica (konsole -> pts/3 ->
            opencode), así que si el takeover deja el display inservible, el pty master
            cierra y la sesión recibe SIGHUP.
            **El agente no puede ser su propia ruta de recuperación.**
            Es una restricción que se sostiene aunque la RX550 no se toque nunca
CANDIDATOS  SSH sobre enp3s0 (construida, parcialmente demostrada)
            VT1/getty (independiente del display, depende de boot_vga, NOT_DEMONSTRATED)
            serie ttyS0 (independiente, NOT_AVAILABLE: getty@serial-console disabled)
            reboot (disponible, pero no equivale a una ruta probada)
```

## 6 · Experimento preparado y no ejecutado — AD-12 (F2)

El único experimento de todo el proyecto que está **completo como diseño** y sin hacer.

```
PREGUNTA      ¿el sampler del Polaris 12 redondea (+3/+2) o trunca la rampa alfa BC3?
POR QUÉ ES DIFERENTE DE TODOS LOS OTROS
  Este proyecto entrega un ENCODER y el consumidor del encoder es el hardware. El
  agreement test actual NO puede responderlo: compara el shader contra el decodificador
  PROPIO, y ese decodificador deriva de las MISMAS decisiones que el encoder. Un
  round-trip propio oculta el error por construcción
MÉTODO       textura DXT5 como color attachment de un FBO, lectura con glReadPixels
             sin shader, sin quad, sin dibujar
             Evita por diseño la ruta de cómputo Vulkan, que ya se sabe que funciona
             pero añade una variable de más
COBERTURA    65536 pares de endpoints x 8 índices = 1048576 observaciones
AUTOVALIDACIÓN  4 puntos; el último es que los índices 0 y 1 decodifiquen exactamente a
             a0/a1, que NO interpolan y por tanto prueban el camino y no la rampa
DISCRIMINANTE  Los dos resultados posibles dan números distintos y ambos preexistentes:
             redondeo -> +3/+2 exacto · truncamiento -> 0..7 sin redondeo
CONFOUNDERS  MSAA, sRGB, filtrado, ROP write masking. De ahí el método sin shader
BLOQUEOS     NINGUNO. Es un experimento de usuario vía Mesa
```

Es la frontera con más consecuencia del proyecto: es la única cuya respuesta pueda
**obligar a revertir una decisión ya tomada y medida** (`AD-11`).

## 7 · Experimento bloqueado dos veces — F1

```
QUÉ ES      el orden de ejecución del invalidate respecto al siguiente IB
POR QUÉ DOS VECES BLOQUEADO
  1. autorización: requiere carga del driver propio y escritura a MMIO
  2. recuperación: la ruta independiente está en PARTIAL. Tomar el control de la RX550
     sin ella puede cortar la sesión del agente
DISCRIMINANTE  YA REDACTADO por la sesión que cerró 017 (§5). No hay que diseñarlo:
     escribir un WAIT_REG_MEM always y un RREG32 de INVALIDATE_REQUEST ENTRE dos IBs,
     con un VMID cuyo invalidate se retrase artificialmente
LO QUE CIERRA  N1 y N2 de golpe. Es el único dato de ordenamiento que falta
CONFUNDERS  TLB preexistente · NO_INVALIDATION en ATC_VMID{n}_PASID_MAPPING bit 30 ·
             reset_domain sem en down_read_trylock · VMID reuse · power state
```

## 8 · Lo que ningún experimento de este repo puede producir hoy

```
LEER UN REGISTRO DE HARDWARE      no hay MMIO, ni debugfs con permiso, ni UMR
                                  y no se va a conseguir sin autorización
VERIFICAR GFX_HWIP                el agreement test no lo consulta ni lo infiere
DISTINGUIR AUSENCIA DE AUSENCIA   evidence_search.py lo resuelve por construcción con
                                  --expect. Los cuatro NOT_FOUND falsos del proyecto
                                  fueron de no usarlo
CONTAR PACKET3 EN RAMAS Y BUCLES  22 emisiones no contables estáticamente [NR-06].
                                  Ninguna cantidad de análisis estático las cierra
```

## 9 · El patrón que los experimentos de este repo ya Pagaron dos veces

```
1. UN EXPERIMENTO CUYO RESULTADO NO DISTINGUE ENTRE DOS HIPÓTESIS NO ES UN
   EXPERIMENTO. M1 es el ejemplo canónico: 10 corridas pareadas, ΔFPS=0, y la
   compuerta ni siquiera llegó a activarse porque el cap no liga. El veredicto
   correcto era NO DISCRIMINATIVO, no "sin diferencias".

2. UN CRITERIO ESCRITO ANTES DE EJECUTAR, O NO ES CRITERIO. El proyecto lo hizo así en
   Q-5 (preregistrado con PASS/FAIL antes de ejecutar, 1259dc4) y en v2.3 de R-4B
   (la variación documentada ANTES). Cuando no se hizo, salió INCONCLUSIVE.

3. UN TEST QUE NUNCA SE HA VISTO FALLAR NO PROBA QUE DETECTE. Demostrado con
   check-ramp-discriminates, con el mutante de pm4_count_census, y con los 12
   controles negativos de gfx8vmgeom — donde un control que no detecta su propia
   mutación se marca [DEAD] y cuenta como fallo, porque "es peor que no tenerlo,
   pues aparenta cobertura".

4. LO QUE UNA PÁGINA DE AGENTE DICE HAY QUE COMPROBAR CONTRA EL DISCO. M1 escribió
   power1==cap 25 W como hecho; era un estimador del SMU con otro comportamiento.
   El fichero entero del proyecto ya lo tenía anotado: "power1_input es estimador
   SMU; hoy reporta valores reales (no plano)". Anotado y no verificado.
```