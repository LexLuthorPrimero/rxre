# 1182 — El sintetizador escribía un paquete que el driver no escribe: sin el flag daba **7** dwords en vez de **4**. Y el `7` con el que se cumplía era el **`.emit_ib_size = 7`** que el propio driver declara

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=DEFECT-REPORT · VALIDATION
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   tools/ibref.py    (condicionales_de, alias de
                              ligadura, raices uapi/arch, siembra con el
                              resolutor de comillas, tope medido; 105 -> 116)
                              tools/verif.py    (1 medida, 50 -> 51 declaradas)
                              08-ARQUITECTURA/artifacts/R18-COND/salida.txt
MODIFICADO_NADA_EXISTENTE    pm4_emit.py, gfx_v8_0.c INTACTOS
CLASSIFICATION=DEFECT-REPORT · IMPLEMENTATION · VALIDATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
ESTADO=DEFECTO CERRADO · LA MEDIDA ES EL PAR (4, 7), NO EL 7
```

## 0 · El resultado, primero

```text
ANTES (medido)      ib.flags=0   ->  7 dwords     <-- paquete que no se escribe
                    ib.flags=16  ->  7 dwords

AHORA (medido)      ib.flags=0   ->  4 dwords     OK
                    ib.flags=16  ->  7 dwords     OK   == .emit_ib_size
                    ib.flags=32  ->  4 dwords     OK   (bit 5, no el bit 4)

nueva medida        ibref.emit_ib_vs_declarado = ['sin_flag=4', 'con_flag=7']
                    perturbada a ('7','7')  ->  rc=1
                    restaurada                ->  rc=0
```

## 1 · EL DEFECTO, Y POR QUÉ NO SE VIO

```c
/* gfx_v8_0.c:6119 */
if (ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID) {
        amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
        amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID
                                        - PACKET3_SET_CONFIG_REG_START);
        amdgpu_ring_write(ring, ring->adev->gds.gds_compute_max_wave_id);
}
amdgpu_ring_write(ring, PACKET3(PACKET3_INDIRECT_BUFFER, 2));
...
```

`escrituras()` recogía **todo** lo que hubiera con `amdgpu_ring_write`, sin mirar
que estuviera dentro de un `if`. Con el flag apagado, el driver escribe 4 dwords y
la herramienta escribía 7.

**Una IB con una escritura de más no es una IB "de más": es otra IB**, y de las
que el hardware ejecuta. El `SET_CONFIG_REG` que se cuelaba de mas escribe
en otro registro, con un valor de otro.

### 1a · Y lo grave es que ya estaba declarado en otro sitio

`propagar_locales`, que escribí antes, tiene esta regla:

```text
una asignacion DENTRO de un `if` no se propaga (no hay flujo)
  VECTOR   a = 1; if (x) a = 2;   ->  a = 1
```

Y `escrituras()` no la tenía. **Las dos rutas eran incoherentes**: la propagación
rechazaba lo condicional y las escrituras lo aceptaban. La incoherencia no la
detectó ningún test porque ninguna de las dos se probó contra la otra.

> Un instrumento con dos caminos que toman la misma decisión y una sola
> probada no tiene dos caminos: tiene uno probado y otro **supuesto**.

## 2 · EL ORÁCULO QUE LO DELATÓ, Y QUE NO BUSCABA

Buscaba `length_dw` (`1181 §7`) y encontré otra cosa:

```c
/* gfx_v8_0.c:6934, en la tabla de funciones de anillo */
.emit_ib_size =  7, /* gfx_v8_0_ring_emit_ib_compute */
```

**El driver declara cuántos dwords escribe su propia función de emisión.** Es un
oráculo del Fourth Kind: no es un layout, ni un nombre, ni una aritmética del
código que se sintetiza — es el **resultado declarado por el propio autor del
código**.

Y contra ese 7:

```text
bandera puesta   -> 7 dwords    coincide
bandera apagada  -> 7 dwords    NO coincide: con el flag apagado son 4
```

## 3 · POR QUÉ LA MEDIDA ES EL **PAR**, Y NO EL 7

Si la medida fuera "el sintetizado tiene que dar 7", el defecto **no la habría
visto**:

```text
sin flag    7  ┐
con flag    7  ┘  ambos dan 7.  La medida "vale 7" pasa.
```

El 7 de la bandera apagada es el número que hace el defecto **indetectable**
contra una medida de igualdad. Por eso lo medido es el par ordenado:

```text
['sin_flag=4', 'con_flag=7']
```

y el par del defecto es `(7, 7)`, que contiene un 7 y por eso parece conforme con
cualquier medida que mire solo uno de los dos.

> **Una medida de agregado esconde exactamente los fallos que son de agregado.**
> El bug no era «escribo 7 en vez de 4»: era «escribo 7 siempre», y eso solo se
> ve mirando los dos casos.

## 4 · TRES CAUSAS ENCADENADAS, Y LAS TRES SON DE LA MISMA FAMILIA

Cerrar el defectohubo que resolver tres cosas, y cada una es un «no llega»:

### 4a · `&` no estaba implementado en el evaluador

```
gfx_v8_0.c:6119   if (ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID)
                  ^^^^^^^^^^operador ausente en eval_call (1151 §3)
```

El mismo `/` que `1151 §3` bisecó. Con la bandera sin resolver, la condición no
tenía valor y no se podía decidir nada.

### 4b · La bandera es un `#define` de una cabecera **UAPI**, y `uapi/` no era raíz

```text
amdgpu.h:51                     #include <drm/amdgpu_drm.h>
kernelbuild/include/drm/amdgpu_drm.h          NO EXISTE
kernelbuild/include/uapi/drm/amdgpu_drm.h    SI     <-- aquí está
```

Y ahí está la definición:

```c
/* include/uapi/drm/amdgpu_drm.h:1006 */
#define AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID (1 << 4)
```

Mi ampliación de `1141` resolvía los `<...>` solo contra `include/`, y por eso
alcanzaba 380 cabeceras y **cero** de `drm/`. Añadidas cuatro raíces
(`include/`, `include/uapi/`, `arch/x86/include/uapi/`,
`arch/x86/include/generated/`): **400** cabeceras, 47 de `drm/`.

### 4c · Y el paseo angular nunca veía `amdgpu.h`

Esta es la que más cuesta ver. `#include <drm/amdgpu_drm.h>` está en
`amdgpu.h`, y `amdgpu.h` se llega desde `gfx_v8_0.c` con **comillas**:

```text
con comillas -> relativos y de los directorios con nombre   (pm4_emit)
con angulo   -> include/, include/uapi/, arch/...           (el mio)
```

Con solo la entrada como semilla, mi paseo angular veía 400 cabeceras y cero de
`drm/`, **aunque la raíz `uapi/` ya estaba añadida**. Lo que hay tras la primera
comilla es invisible para él.

Semillas con los 108 ficheros que el resolutor de comillas ya encontró:
**602** alcanzadas, `uapi/drm/amdgpu_drm.h` incluida.

> **Dos resolutores que resuelven cada uno la mitad, y ninguno basta solo.** Es el
> mismo patrón que `1140`/`1141` con `sizeof` y `ARRAY_SIZE`: la respuesta no era
> «falta la macro», era «falta el camino hasta ella».

## 5 · EL TOPE DE 400, Y QUE OCULTABA EL 33%

Cuando subí las raíces pasé de 380 a 400 alcanzadas — **exactamente el tope**.
Lo comprobé subiendo el tope:

```text
tope 400  ->  400 alcanzadas  truncado=True
tope 1500 ->  602 alcanzadas  truncado=False
tope 6000 ->  602 alcanzadas  truncado=False
```

El tope de 400 estaba ocultando **202 cabeceras**, y entre ellas la que trae la
bandera. El campo `truncado` existía desde `1141` y **nadie lo miraba**; yo mismo
lo escribí como «hueco declarado en el código pero no en la salida» y no lo
convertí en salida hasta que me truncó.

Ahora el tope es 1200, por encima de 602 con margen, y `truncado` sale en el
informe que imprime la herramienta.

## 6 · EL BUG LÓGICO, Y QUE LO PRODUJO EL VECTOR

Con las tres causas resueltas, el condicional seguía dando `NO` con
`ib_flags = 0`. Mi decisión era:

```python
if all(v == 0 for v in vals):        #  [0, 16] -> False
    ver = "SI"                       #  -> no entra
elif None not in vals:
    ver = "NO"                       #  -> entra aqui
```

Los términos de `ib->flags & BANDERA` con `ib_flags = 0` son **`[0, 16]`**. No
son todos cero → segunda rama → `NO` → **se emite**. Y `0 & 16` es `0`: la
condición es falsa.

Lo correcto es una línea:

```python
valor = vals[0]
for w in vals[1:]:
    valor &= w
if valor == 0: ver = "SI"
```

Es el caso general, sin árbol de decisiones, y no puede salir mal por un término
que valga cero y otro que no.

> El sintoma era «emite un paquete de más». La causa era un `all()` sobre una
> conjunción, que no es una conjunción. Dos cosas que se parecen muchísimo y no
> lo son.

## 7 · LA LIGADURA, QUE NO CASABA CON LA FORMA DEL CÓDIGO

El driver escribe `ib->flags`. El instrumento normaliza a `ib_flags`. Y la
primera versión de la ligadura solo aceptaba `--set ib_flags=16`:

```text
--set ib_flags=16   -> 7 dwords   (funcionaba)
--set flags=16      -> 4 dwords   (no ligaba nada)
--set ib.flags=16   -> 4 dwords   (no ligaba nada)   <-- la forma natural
```

`ib.flags` es lo que escribe cualquiera mirando el código C. Ahora la clave se
normaliza también con el punto, y **un punto entre dos letras**; un punto decimal
(`0.5`) se deja como está.

## 8 · PROCEDIMIENTO

```text
medicion    gfx_v8_0.c:6119        la condicion
            gfx_v8_0.c:6934        .emit_ib_size = 7, declarado por el driver
            uapi/drm/amdgpu_drm.h:1006   la bandera = (1 << 4) = 16
            amdgpu.h:51            #include <drm/amdgpu_drm.h>  (con angulo)

raices      antes   include/                     -> 380 alcanzadas, 0 de drm/
            +uapi/  include/, include/uapi/,
                    arch/x86/include/uapi/,
                    arch/x86/include/generated/ -> 400, 47 de drm/
            +semillas del resolutor de comillas  -> 602, uapi/drm/ incluida

tope        400 -> truncado=True   |   1500 -> 602, truncado=False
            (el de 400 ocultaba 202 cabeceras, el 33%)

medido      ib.flags=0  -> 4 dwords  cond=SI    "la condicion vale 0"
            ib.flags=16 -> 7 dwords  cond=NO    "la condicion vale 16"
            ib.flags=32 -> 4 dwords  cond=SI    (bit 5, no el bit 4)

vectores    ibref 105 -> 116, rc=0
            11 nuevos: la bandera llega, vale 16, SI con 0, NO con 16, SI con 32,
            NO_RESUELTO sin ligar, no-sale-lo-que-no-se-emite,
            sale-lo-que-si-en-orden, `ib.flags` == `ib->flags`, punto decimal

puerta      50 -> 51 declaradas, SIN DERIVA
            ibref.emit_ib_vs_declarado = ['sin_flag=4','con_flag=7']
            perturbada a (7,7)   rc=1     <- el sintoma del defecto
            restaurada           rc=0

no-regresion  kiq_kcq_enable     15 dwords IDENTICOS (con y sin ampliacion)
              shader-init        294 dwords, 285 completos, locales intactas
otros         layoutcross 79 vectores rc=0 · mmio 48 vectores rc=0
artefacto     08-ARQUITECTURA/artifacts/R18-COND/salida.txt
escrituras    0 ficheros de otros agentes
```

## 9 · LO QUE SIGUE SIN ESTAR HECHO

**No hay modelo de flujo de control.** El `if` se decide por su condición y solo;
un `for` dentro de una función con condición que depende de la iteración no se
modela, y un `else` no se mira. Lo que hay es un reconocimiento de `if (cond) { }`
con condición resoluble a entero, y **todo lo demás se rechaza y se declara**.
Es un límite declarado, no un olvido.

**`|`, `&&` y `!` no se resuelven.** `if (a || b)` y `if (a && b)` dan
`NO_RESUELTO` y no se emite. La razón está escrita en el código: el evaluador no
tiene caso para ellos, y decidir el cortocircuito sin evaluar los dos lados sería
inventar la semántica.

**No he buscado cuántos condicionales hay en `gfx_v8_0.c`.** He arreglado el de
esta función porque lo medí. Cuántos más hay y cuántos se resuelven es un
`NOT_DETERMINED` declarado, y es la medición que toca.

**`.emit_ib_size` da 7 como máximo, no como valor por ruta.** Que con el flag
apagado sean 4 se deduce leyendo el código, no de la tabla. La tabla da el
tope, y **el tope es exactamente lo que no delata este bug** — por eso la medida
es el par.

**Y nada de esto es evidencia de hardware.** `RUNTIME=NOT_RUN`. Que el ASIC
ejecute 4 o 7 dwords según el flag es lo que el código dice; que lo ejecute es
otra afirmación.