# 1067 — el poder discriminante del oráculo depende de las cuentas que haya en el anillo, y eso hay que declararlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/pm4tila.py 1.1.0 (instrumento de este hallazgo)
         revkit/capturas/amdgpu_ring_gfx.txt (el anillo que hace posible la medicion)
ESTADO=PROVEN-MI-DEFECTO · el defecto era del VECTOR, no del instrumento
herramienta   tools/pm4tila.py 1.1.0
sha256        4f3175d250c0f62e2bc74022a102230b4bdc4372d1c43abba1b0a4ecd1c920de
selftest      23 vectores, 0 fallos, rc=0
```

## 0 · EL HECHO, Y ES UNA ARITMÉTICA DE UN SEGUNDO

Dos convenciones de longitud de PACKET3 que se parecen entre sí son
`count + 2` y `2*count + 2`. Coinciden exactamente cuando `count = 0`:

```
count=0 -> count+2 = 2   2*count+2 = 2   INDISTINGUIBLES
count=1 -> count+2 = 3   2*count+2 = 4   distinguibles
count=2 -> count+2 = 4   2*count+2 = 6   distinguibles
count=5 -> count+2 = 7   2*count+2 = 12  distinguibles
```

Por tanto: **un anillo PM4 compuesto solo de paquetes con `count = 0` no puede
determinar la convención**, y el veredicto correcto es `NOT_DETERMINED` sobre esa
dimensión. No es una sutileza: es que el método **no puede decidir**, y un
método que no puede decidir tiene que decirlo.

## 1 · CÓMO SE DESCUBRIÓ: POR UN VECTOR MÍO QUE ERA FALSO

El primer selftest de `pm4tila.py` **falló 2 de 19 vectores**. Los dos afirmaban
que el veredicto era `UNICA` sobre un anillo sintético construido con
`count = 0`.

La herramienta devolvía `PARCIAL`, con `pkt2` ambiguo. **La herramienta acertó y
el vector estaba mal.**

Es el caso raro y el más instructivo: el defecto no estaba en el instrumento sino
en mi manera de **describir** lo que el instrumento tenía que encontrar. Y es
precisamente el caso que un vector escrito a posteriori no caza nunca, porque se
escribe después de que el código ya hace lo correcto.

## 2 · LO QUE SE HIZO, Y NO ES "ARREGLAR EL VECTOR"

Se añadió un vector que **exige la degeneración**:

```
BORDE__count_0_no_distingue_count_mas_2_de_2count_mas_2
    un anillo de dos paquetes con count=0
    => el veredicto DEBE declarar pkt3 ambigua con {count+2, 2*count+2}
```

Ese vector no comprueba que la herramienta funcione: comprueba que **se niegue a
decidir cuando no puede**. Un instrumento al que se le exige saber cuándo no
sabe, es un instrumento que se puede usar.

## 3 · POR QUÉ EN ESTE ANILLO SÍ SE PUEDO, Y ES SUYENA DE ESA MEDICIÓN

El anillo GFX real de esta RX550 trae `PACKET3_WAIT_REG_MEM` con `count = 5`, que
**sí** distingue `count + 2` (7 dwords) de `2*count + 2` (12 dwords). Por eso la
dimensión PACKET3 quedó adjudicada.

Y por eso mismo el anillo **no** puede cerrar PACKET2: **no contiene ningún
PACKET2 con cuenta distinta de cero**, así que `2*count + 1` y `count + 1` dan
ambos 1 y no hay dato. El veredicto es `NOT_DETERMINED`, y cerrarlo exigiría una
captura nueva — trabajo del nodo de runtime, no de aquí.

> **La misma captura que hace posible una medición la vuelve imposible para la
>dimensión vecina.** Un informe que dice "he determinado la convención de
> longitud PM4" sin decir **qué** dimensiones, ni con **qué** poder discriminante
> tiene, está vendiendo de más.

## 4 · LA LECCIÓN

Todo oráculo tiene un **techo de resolución**, y el techo no se deduce del
resultado: se deduce de **qué casos contiene el dato**. Los dos oráculos de
`pm4tila.py` lo declaran en su cabecera, porque un método cuyo techo no se
declara no se puede usar: se usa como si no tuviera ninguno.

Esto conecta con `1065` (instrumento que no puede fallar) y con `1066`
(instrumento que acusa de más) por la misma vía: **los tres fallos son fallos
sobre lo que el instrumento PUEDE decir, no sobre lo que dice.**