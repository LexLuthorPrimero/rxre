# 1075 — dos votos en contra que eran verdad: el residuo que hay que adjudicar en vez de redondear

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=tools/pm4tila.py 1.1.0 (instrumento de este hallazgo)
         gfx_v12_1.c:3440  [NAVI 12.1 -> hallazgo 1074]
         gfx_v9_0.c:7476   [NAVI 10/GFX9, forma con if/else]
ESTADO=PROVEN-LIMITE-DEL-INSTRUMENTO · el codigo del driver es CORRECTO en ambos casos
herramienta   tools/pm4tila.py 1.1.0
```

## 0 · EL HECHO

Al ampliar el oráculo de fuente para cubrir los emisores de IB (§3), la
corroboración pasó de `129 vs 0` a **`222 vs 2`**. Los dos votos que quedan en
contra son los únicos que podrían desmentir el hallazgo `1062`, así que los
adjudiqué uno a uno en vez de publicarlos como «dos discrepancias».

**Los dos son de alcance del instrumento. El código del driver es correcto en
ambos casos.** Y esa es la parte que hace que valga la pena escribirlo: un
residuo que se explica es un residuo controlado, y uno que se redondea a cero
es una mentira.

## 1 · EL PRIMERO: UNA RAMA CONDICIONAL

`gfx_v9_0.c:7476`:

```c
  if (amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 4, 2))
      amdgpu_ring_write(ring, PACKET3(PACKET3_RUN_CLEANER_SHADER, 0));
  else
      amdgpu_ring_write(ring, PACKET3(PACKET3_RUN_CLEANER_SHADER_9_0, 0));

  amdgpu_ring_write(ring, 0);  /* RESERVED field, programmed to zero */
```

Mi contador leyó `payload = 0` y votó `count = payload`. La verdad está en las
**cinco** generaciones que escriben este paquete, y **cinco de cinco** ponen el
payload:

```
  gfx_v9_0.c:7476    n=0  payload=1   (forma con if/else)
  gfx_v9_4_3.c:4778  n=0  payload=1
  gfx_v10_0.c:9791   n=0  payload=1   (forma sin if/else, la legible)
  gfx_v11_0.c:7254   n=0  payload=1
  gfx_v12_0.c:5150   n=0  payload=1
```

**Cinco de cinco son `n + 1`.** El driver está bien. Lo que falla es que mi
recorrido es **secuencial**: no entiende que hay dos ramas y que solo una se
emite, así que conté mal.

## 2 · EL SEGUNDO: ES EL HALLAZGO 1074, Y NO ES MÍO

`gfx_v12_1.c:3440` escribe `PACKET3_SET_CONFIG_REG, 1` con **un** payload donde
las otras nueve generaciones del corpus ponen **dos**. Está en el hallazgo `1074`, con su
medida de las diez generaciones y su comprobación de que persiste en los tres
árboles del proyecto.

Es una discrepancia **real del corpus**, en código que **no se compila para
GFX8** y que por tanto no toca esta GPU. Se deja el voto en contra, visible, y
se dice por qué.

## 3 · LOS DOS LÍMITES, QUE NO SON EL MISMO

| caso | naturaleza | quién lo resuelve |
|---|---|---|
| `RUN_CLEANER_SHADER` | **parser secuencial** que no ve ramas | límite de la herramienta, resoluble |
| `SET_CONFIG_REG` en NAVI | **código del driver** que difiere de sus 9 hermanos | no es mío; es semántica de otra generación |

El primero se arregla; el segundo no me toca. Confundir los dos —tratar la
discrepancia de NAVI como un fallo de mi contador porque me incomoda— habría
sido **descartar evidencia verdadera**, que es el error espejo del de `1068`.

## 4 · LA REGLA, Y POR QUÉ NO SE REDONDEA

> **Un residuo que se publica y se explica es un residuo controlado. Uno que se
> redondea a «cero discrepancias» es una mentira, aunque el número redondeado sea
> el que uno quiere oír.**

La herramienta imprime el residuo **con nombre y fichero**. Y el criterio con el
que se publica un voto en contra no es «me molesta», sino **«¿lo he adjudicado
contra la fuente?»**:

```
  222 a favor   n+1     count = payload − 1,  len = count + 2
    2 en contra         adjudicados: 1 es limite mio, 1 es NAVI (1074)
    7 sin_origen        fuera de los dos emisores reconocidos
```

## 5 · LO QUE ESTO LE PIDIÓ AL INSTRUMENTO

Dos cosas concretas, y las dos están hechas:

1. **Reconocer el emisor de IB por sus dos formas** —`ib.ptr[ib.length_dw++]`
   y `ib.ptr[<índice literal>]`— porque la segunda escribe por rangos y solo se
   cuenta con el `ib.length_dw` que declara la función. MEDIDO que sin esto,
   `gfx_v6_0.c:1970` salía con `payload=1` y votaba en contra **falsamente**:
   el código es `ib.ptr[0]=hdr; ib.ptr[1]=valor; ib.ptr[2]=0xDEADBEEF;
   ib.length_dw=3`, o sea dos payload.
2. **Cortar el payload en la próxima cabecera PACKET3**, no en el cierre de la
   función. MEDIDO que contar de más fusionaba paquetes de una misma función y
   producía 91 filas «fuera de alcance» que no lo estaban.

Corroboración: **129 → 222 a favor, y el número de falsas en contra baja de 11
a 0 en el mismo cambio.**

## 6 · LO QUE SIGUE SIN RESOLVERSE

El emisor **`RUN_CLEANER_SHADER` sigue entrando mal**, porque el recorrido
secuencial no modela `if/else`. La solución correcta no es un parche más: es un
analizador que sepa qué rama se emite, o **excluir los constructores con ramas
y decirlo**. Se prefiere lo segundo, y por eso queda aquí escrito como
**`fuera_de_alcance` declarado**, no como voto.

**Preferir la exclusión a la corrección adivinada** es la misma regla del resto
del instrumento: el sesgo va hacia «no se puede concluir».