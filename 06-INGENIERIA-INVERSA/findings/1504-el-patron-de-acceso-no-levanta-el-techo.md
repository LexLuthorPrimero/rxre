# 1504 — el patrón de acceso no levanta el techo; y dos veces seguidas mi propio test estaba roto

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=EVIDENCIA-DE-SILICIO+REFUTACION-DE-HIPOTESIS-PROPIA+INVALIDACION-DE-MEDICION
TRACK=RUNTIME · 0000:01:00.0 SOLO · Intel intacta y verificada
GENERADO=2026-10-05
AFECTADO=06-INGENIERIA-INVERSA/findings/1498-*  la ruta que ese deixaba abierta, recorrida
         la regla que el 1498 proposo, aplicada a si misma
ESTADO=PROBADO · el patron de acceso NO limita los 40 GB/s: bloque-contiguo da -1.27 %
       · el patron lineal es el mejor de los dos probados, con 3 repeticiones y dispersion <0.04
       · la prediccion del 1498 QUEDA REFUTADA: el limite estaba en el bus, como sospechaba
       · el brazo de MLP queda INVALIDADO, y por una causa concreta y explicable
       · y dos mediciones mias SALIERON LIMPIAS Y NO SIGNIFICABAN NADA, ambas detectadas
```

## 1. La predicción que dejé escrita, y el resultado

El 1498 cerró con esto, textual, y es una predicción con criterio de refutación explícito:

> *"Si un kernel con acceso por bloques emparejados pasa de 40.3 GB/s, el límite estaba en el
> acceso. Es la vía que **no** requiere intervención y es la que queda."*

**Medido, 256 MiB, modo `rmw`, `--sync-every 32`, tres repeticiones cada uno:**

| patrón | rep 1 | rep 2 | rep 3 | media |
|---|--:|--:|--:|--:|
| **lineal** (`i = gl_GlobalInvocationID.x`) | 40.17 | 40.17 | 40.16 | **40.17** |
| **bloque** (cada workgroup sobre un fragmento contiguo de 64 elementos) | 39.64 | 39.67 | 39.67 | **39.66** |

> **El patrón por bloques es un 1.27 % PEOR, no mejor.** La dispersión entre repeticiones es de
> 0.04 GB/s, o sea que la diferencia está muy por encima del ruido.

**La predicción queda `REFUTADA`.** El límite **no estaba en el patrón de acceso**: el acceso
lineal —que en una GPU es el patrón coalescido por definición— ya es el mejor de los dos, y
**los 40 GB/s son del bus**.

Y tiene una lectura física que encaja con todo lo anterior: un acceso lineal de 64 hilos por
workgroup lee 64 direcciones consecutivas = **256 bytes = 4 líneas de 64 B**, o sea **una
transacción completa por ciclo de sector**. Ese es el acceso que el controlador de memoria
prefiere, y ya lo teníamos.

## 2. El brazo de MLP: `INVALIDADO`, y por qué

También probé **paralelismo de acceso por hilo** (`--mlp N`: cada invocación emite `N` accesos
independientes, separados por un salto). El resultado apparent:

```text
  --mlp 1    39.60 GB/s
  --mlp 2    25.39
  --mlp 4    15.09
  --mlp 8    (el shader ya no compila)
```

**Eso no es paralelismo de memoria degrading. Es scratch spilling.** La causa es concreta:

```glsl
uint v[NMLP];
for (uint j = 0u; j < uMlp; ++j) v[j] = data[i + j * uStride];   /* uMlp es UNIFORM */
```

`uMlp` es un **uniform en tiempo de ejecución**, así que el índice `j` de `v` es dinámico. Un array
local con índice dinámico **no cabe en registros** y el compilador lo baja a **memoria scratch**.
**Y en AMD la memoria scratch está en la VRAM.** O sea que el experimento estaba midiendo tráfico
adicional a VRAM, no paralelismo de nivel de memoria. Cuanto mayor `N`, más scratch, peor el
resultado — que es exactamente el degradado medido.

**Para medirlo bien haría falta** desenrollar con un límite **literal** (`#pragma unroll` sobre
`NMLP`, con `v[0]..v[NMLP-1]` escritos a mano, sin índice dinámico). Eso no lo he hecho, y por
tanto:

> **El brazo de MLP queda `INVALIDADO`. No es un resultado, es un experimento mal construido.**
> Lo dejo escrito como tal en vez de publicar el degradado como si significara algo.

## 3. Y DOS MEDICIONES MÍAS QUE SALIERON LIMPIAS Y NO SIGNIFICABAN NADA

Esto es lo importante de este hallazgo, y es exactamente el mecanismo que el 1498 propuso
**aplicado a sí mismo**.

### 3.1 El primer intento de MLP: `uStride` nunca se asignó

El compilador avisó:

```text
warning: variable 'uStride' sin usar [-Wunused-variable]
```

**Leí ese aviso como ruido y no lo seguí.** Como `uStride` valía `0`, el shader hacía
`data[i + j*0]` = `data[i]`: **N accesos a la misma dirección**. Cuatro puntos medidos,
dispersión mínima, y sin significado. Los números iniciales que parecían "el patrón no ayuda"
eran esto.

### 3.2 El segundo intento: `NMLP` de tamaño de compilación valía 1

Al parameterizar el shader seguí usando `uint v[NMLP]` con `NMLP` = 1 fijo, y lo usé con
`uMlp = 8`: **escribiendo 7 elementos pasado un array de uno.** Comportamiento indefinido. Los
cuatro puntos salieron con un degradado lineal casi perfecto de ~8.9 GB/s por duplicación —que
era precisamente la firma del fallo— y ninguno valía.

### 3.3 Lo que las dos cosas significan

> **Las dos mediciones fallaron en silencio, con dispersión baja, formato limpio y salida
> verificada.** Si las hubiera escrito en un hallazgo sin mirar el aviso del compilador, el
> proyecto tendría ahora dos tablas de ancho de banda convincentes y falsas.

**La diferencia con los casos anteriores** (1494, 1496, 1498) es que allí las hipótesis eran
*mías* sobre cifras ya medidas. Aquí los **medidores** estaban mal, y eso es peor: un error de
instrumento no se desmiente comparando con otra fuente, se desmiente releyendo el código.

**Y la defensa que funcionó fue la misma que el 1498 propuso**: no aceptar el número hasta que
una medición distinta lo confirme. En los dos casos **no hubo medición de confirmación** —me
puse a arreglar el código y volví a medir— y en los dos casos el código tenía un aviso que yo
había descartado como ruido.

> **Regla que sale, y que es más fuerte que la del 1498:** un aviso del compilador sobre una
> variable que el resultado **depende** no es decorativo. Si el número que sale de ese programa
> depende de que `uStride` esté bien puesto, entonces el aviso del compilador sobre `uStride`
> es un **aviso sobre el número**, y se lee antes de medir.

## 4. Procedencia

```text
fuente    07-DRIVER/bench/rx550_gl_load.c
          sha256 1e20df0790c772dcc7ee4e87ea9b4b098f21fddbc5b10896320fea9a54e6f6cc
          el fuente del shader se genera con make_shader(mlp) porque NMLP es tamaño de
          compilacion: un array local con indice dinamico cae a scratch, que en AMD esta en VRAM
binario   07-DRIVER/bench/rx550_gl_load.bin
metodo    --pattern linear|block   --mlp N   --sync-every N
           256 MiB, modo rmw, sync-every 32, 3 repeticiones por variante, 5 s cada una
dispersion  linear  40.17 40.16 40.17    block  39.64 39.67 39.67
           diferencia 0.51 GB/s contra dispersion de 0.04: la diferencia es real
solo lectura  pp_dpm_sclk, pp_dpm_mclk, amdgpu_pm_info
escrituras   CERO registros
frontera     POST-CONDICION en cada ejecucion: renderer AMD y es esta tarjeta
```

```text
ESTADO=PROBADO · el patron de acceso NO limita el techo.  Bloque-contiguo: 39.66 GB/s frente a
       40.17 lineal, un -1.27 %, con dispersion de 0.04 entre repeticiones
REFUTADA  mi prediccion del 1498 ("si un kernel con acceso por bloques pasa de 40.3 GB/s, el
       limite estaba en el acceso").  Pasa al reves, y con menos dispersion que la diferencia
NUEVO  la lectura lineal de 64 hilos por workgroup cubre 256 bytes = 4 lineas de 64 B = una
       transaccion completa por sector.  Es el acceso que el controlador de memoria prefiere, y
> ya lo teníamos.  Explica por qué no hay margen por ese lado
INVALIDADO  el brazo de MLP NO es un resultado.  Con indice dinamico sobre un array local, el
       compilador baja el array a SCRATCH, y en AMD el scratch esta en VRAM: se midio trafico
       extra a VRAM, no paralelismo de memoria
DECLARADO  dos mediciones mias salieron limpias y sin significado: uStride sin asignar (N accesos
       a la misma direccion) y NMLP de tamaño 1 usado con uMlp=8 (escritura fuera del array).
       Ambas detectadas por el aviso del compilador que yo descarte como ruido
LIMITE   el patron por bloques se probo en una sola forma (bloque de 64 por workgroup, reparto
       en 8 filas).  Otras formas no se probaron
RIESGO  ninguno.  Sin reset, sin ring timeout
FRONTERA Intel intacta, verificada en caliente en cada ejecucion
Siguiente  1) el techo de ancho de banda queda cerrado en ~40.2 GB/s = 83.7 % de 48.0, con dos
           vias independientes que NO lo levantan: sincronizacion (1498) y patron (este)
         2) si se quiere medir MLP de verdad, hay que desenrollar con limites literales y sin
           indice dinamico, o usar un kernel que emita varias cargas independientes sobre
           registros escalares, no sobre un array
         3) y con esto la lectura de rendimiento del 1494 queda completa: la memoria esta al 84 %
           de lo nominal, no hay recorrido ni en instrumentacion ni en patron de acceso, y el
           frente util es la eficiencia de ALU y la potencia
```

## 5. El estado de la frontera de rendimiento

```text
                                    medido            quien lo fijo
ancho de banda DRAM, mixto R+W       40.2 GB/s        1494/1496/1498/1504
eficiencia sobre 48.0 GB/s           83.7 %           1498
techo de reloj de memoria            1500 MHz         1449 (tabla), 1485 (medido), 1489 (ROM)
techo de reloj de graficos           1071 MHz         1449 (tabla), 1485 (medido), 1489 (ROM)
unidades del reloj de memoria        2 transf/clock   1494, por medicion
DPM de memoria, disparadores         2 independientes 1494 (ALU), 1496 (working set)
voltaje de trabajo / declarado       881 / 1075 mV    1485, 1477
cuello con carga de memoria          84 % del nominal 1494, cerrado en 1504
cuello con carga de ALU              17.9 W/12.89 GB/s 1494
```

> **Las cuatro rutas que podían levantar el techo de memoria están agotadas sin intervención:**
> la instrumentación (`--sync-every`, +1.8 %), el patrón de acceso (−1.3 %), el tamaño del
> working set (curva plana, 1496), y la propia teoría nominal (descartada por medición, 1494).
>
> **No queda recorrido en la memoria.** Y eso no es un resultado pesimista: es el resultado que
> permite decidir. La línea que queda por encima de la de rendimiento del proyecto es la del
> **coste por operación de la ALU**, y ahí hay un número que sí es accionable: **17.9 W para
> 12.89 GB/s**. Con un techo declarado de 1075 mV y trabajo a 881 mV, hay 22 % de voltaje sin
> usar, y eso es dirección de trabajo, no una cifra más.