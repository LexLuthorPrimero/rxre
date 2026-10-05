# 1068 — inventé once votos en contra de la convención correcta: un oráculo que fabrica evidencia es peor que no tenerlo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=tools/pm4tila.py 1.1.0 (instrumento de este hallazgo)
         corpus: amdgpu_gfx.c:2510, gfx_v8_0.c:1549  (constructores citados)
ESTADO=PROVEN-MI-DEFECTO · CORREGIDO · 129 vs 11 -> 129 vs 0
herramienta   tools/pm4tila.py 1.1.0
sha256        4f3175d250c0f62e2bc74022a102230b4bdc4372d1c43abba1b0a4ecd1c920de
```

## 0 · EL HECHO

La corroboración desde fuente cuenta cuántos `amdgpu_ring_write(ring, ...)`
siguen a cada `PACKET3(op, n)` del corpus, y clasifica cada constructor:

```
payload == n + 1   ->  count = payload − 1,  len = count + 2
payload == n       ->  count = payload,      len = count + 1
```

**Primera medición: 129 a favor de `count + 2` y 11 a favor de `count + 1`.**

Once votos a favor de la convención **equivocada**. Eran inventados por mi
contador, y las once filas tienen la misma firma: `payload = 0` con `n = 0`.

## 1 · LA CAUSA, Y ES UN ERROR DE ALCANCE, NO DE LÓGICA

```c
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_EVENT_WRITE, 0);   // amdgpu_gfx.c:2510
buffer[count++] = cpu_to_le32(PACKET3(PACKET3_PREAMBLE_CNTL, 0));
```

Esos constructores escriben la cabecera **por una vía que no es
`amdgpu_ring_write`**. Mi contador contaba el payload buscando `amdgpu_ring_write`
en las líneas siguientes, no lo encontraba —porque el payload lo escribe el
código posterior por otra vía— y anotaba `payload = 0`.

Con `n = 0` y `payload = 0`, la comparación `payload == n` daba **cierto**, y el
voto iban a la hipótesis equivocada.

**El defecto era de alcance del oráculo, no de su aritmética**: yo medía "cuántas
escrituras de payload hay" y lo usaba como si fuera "cuántas escrituras de
payload hay **para un emisor que cuenta**".

## 2 · POR QUÉ ESTO ES PEOR QUE NO TENER ORÁCULO

Un oráculo con un sesgo **a favor de la hipótesis correcta** da un resultado
razonable y uno la cree. Un oráculo con un sesgo **en contra** fabrica
evidencia, y esa evidencia:

1. **sube al informe como si fuera un dato del proyecto**, no como un defecto
   mío;
2. **debilita la conclusión buena**: si yo reporto 129 vs 11, el lector tiene
   que preguntarse si hay un residuo real de 11, y esa duda contamina el
   hallazgo `1062` que sí es sólido;
3. **es más caro de detectar que un oráculo roto**, porque un oráculo roto
   falla visible y uno sesgado produce un número plausible.

> El sesgo no tiene que ser grande para hacer daño. Tiene que ser ** invisible
> en la salida**. Once votos de mil doscientos no se ven en un porcentaje.

## 3 · LA CORRECCIÓN, Y SU PRINCIPIO

La corrección es de una línea de alcance, y lo importante es **qué** se añadió,
no cuántas:

```
Si la cabecera no sale por `amdgpu_ring_write`, el constructor NO SE CUENTA,
ni a favor ni en contra.
```

Es decir: **el oráculo declara su alcance y se niega a opinar fuera de él.**

Y el caso del payload fundido en la misma línea:

```c
amdgpu_ring_write(ring, PACKET3(PACKET3_EVENT_WRITE, 0) | EVENT_TYPE(...) | ...);
```

también se excluye, porque ahí `n` ya no es el payload entero. Sin esa segunda
regla, un constructor con payload fundido contaría de menos y votaría en contra.

**MEDIDO tras corregir: 129 a favor, 0 en contra, 69 fuera de alcance.** Y los
69 se **imprimen**, porque un residuo que no se enseña es un residuo que no está
controlado.

## 4 · LA LECCIÓN, Y POR QUÉ LA ESCRIBO COMO HALLAZGO Y NO COMO NOTA

> **Un oráculo que fabrica evidencia en contra es peor que no tener oráculo**,
> porque convierte un defecto mío en un hallazgo del proyecto.

Y hay una consecuencia de método que va más allá de esta herramienta: cuando dos
oráculos independientes **coinciden**, la tentación es leerlo como confirmación y
pasar al siguiente. Aquí coincidían en la conclusión **por dos razones, y una
era un error mío**. Si solo hubiera mirado el número, `129 vs 11` habría pasado
por "consistencia aproximada" y el hallazgo `1062` habría salido con una corroboración
débil que nadie iba a cuestionar.

La comprobación que faltaba era barata: **mirar las once filas una a una.** Nadie
las miró porque el total ya parecía bastante claro. Ese es el fallo de
procedimiento, y por eso el finding se escribe.

## 5 · LO QUE ESTO NO CAMBIA

`1062` sigue en pie: la convención `count + 2` está adjudicada por la teselación
exata del anillo real, que es un oráculo **geométrico** y no depende de este
contador en absoluto. Este hallazgo no lo refuta: le quita una corroboración
defectuosa y deja la que era buena, que es la de `vid.h` y `gfx_v7_0.c`.