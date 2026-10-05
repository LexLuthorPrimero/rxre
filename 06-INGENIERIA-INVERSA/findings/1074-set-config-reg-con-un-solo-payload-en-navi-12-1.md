# 1074 — `PACKET3_SET_CONFIG_REG` lleva un solo payload en NAVI 12.1, donde las otras nueve generaciones ponen dos

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=rx550-upstream-7.2.8/.../amdgpu/gfx_v12_1.c:3440-3441   [NAVI 12.1]
         contraste: gfx_v8_0.c:6126-6128                          [GFX8, ESTA RX550]
ESTADO=PROVEN-DISCREPANCIA-EN-CORPUS · NO es un defecto de GFX8 · NO es del ASIC objetivo
herramienta   tools/pm4tila.py 1.1.0
```

## 0 · POR QUÉ ESTE HALLAZGO NO ES SOBRE NUESTRA GPU

**NAVI 12.1 no es el ASIC de este proyecto.** GFX8 es. Y en GFX8 el paquete se
escribe **correctamente**, con dos payload (`gfx_v8_0.c:6126-6128`). Lo que sigue
es una discrepancia del corpus que afecta a **otra generación**, y se registra
porque el instrumento que la detectó es de este nodo y porque un(driver con una
discrepancia así) es exactamente el tipo de cosa que otro agente encontrará y
merece saber antes de perder una hora.

## 1 · EL HECHO

`gfx_v12_1.c:3440`, dentro de la función que escribe
`ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID`:

```c
  amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
  amdgpu_ring_write(ring, regGDS_COMPUTE_MAX_WAVE_ID);
```

**Un** dword de payload con `n = 1`.

Y el mismo paquete en **nueve** sitios más del mismo corpus, con **dos**:

```c
  amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
  amdgpu_ring_write(ring, mmGDS_COMPUTE_MAX_WAVE_ID - PACKET3_SET_CONFIG_REG_START);
  amdgpu_ring_write(ring, ring->adev->gds.gds_compute_max_wave_id);
```

El segundo dword es **el dato**; el primero es el **valor del registro**.

## 2 · MEDIDO SOBRE LAS DIEZ GENERACIONES

```
  fichero         linea  payload  veredicto
  gfx_v6_0.c       1867      2     n+1
  gfx_v6_0.c       1899      2     n+1
  gfx_v7_0.c       2246      2     n+1
  gfx_v8_0.c       6126      2     n+1   <-- ESTA RX550 (Polaris12)
  gfx_v9_0.c       5567      2     n+1
  gfx_v9_4_3.c     2941      2     n+1
  gfx_v10_0.c      8699      2     n+1
  gfx_v11_0.c      6049      2     n+1
  gfx_v12_1.c      3440      1     n       <-- LA EXCEPCION UNICA
```

**Nueve de diez.** Y es la **misma función** en todos los casos: la que escribe
el flag `AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID`, con el mismo comentario sobre
Wave ID mismatch entre ME y GDS. No son dos cosas parecidas: es un bloque de
código copiado de una generación a otra, y una copia se quedó a medias.

## 3 · NO ES UN ERROR DE VERSIÓN — MEDIDO EN LOS TRES ÁRBOLES

```
rx550-upstream-7.2.8/.../gfx_v12_1.c:3440   payload=1
RESEARCH/working/linux-7.1.3/.../gfx_v12_1.c:3371   payload=1
RESEARCH/baseline/linux-7.1.3/.../gfx_v12_1.c:3371   payload=1
```

El mismo payload de uno en 7.1.3 y en 7.2.8. **La discrepancia persiste**, así
que no es un descuido transitorio de un árbol: está en el upstream, en las dos
ramas que este proyecto tiene.

## 4 · LO QUE NO SE AFIRMA, Y ES TAN IMPORTANTE COMO LO QUE SÍ

**No se afirma que sea un bug.** Tres razones por las que no:

1. **No es del ASIC objetivo.** El target es Polaris12/GFX8, y ahí el paquete
   está bien escrito. Esto no toca nuestro hardware.
2. **No se compila para GFX8.** MEDIDO por R2: el grafo de includes de
   `gfx_v8_0.c` no alcanza `gfx_v12_1.c`. Es código muerto **para esta
   generación**, y un código que no se compila no puede estar exercising el
   hardware de esta tarjeta.
3. **No hay lectura de hardware que lo confirme.** Nadie ha visto a NAVI 12.1
   emitir este paquete en una GPU real de este proyecto, porque no hay ninguna.
   Sin eso, "el driver escribe un paquete raro" es una afirmación sobre **el
   texto del driver**, y no sobre el hardware.

Lo que **sí** se afirma, y es lo único: **nueve de diez generaciones del corpus
escriben este paquete con dos payload y una con uno, y las tres ramas del
proyecto coinciden en la excepción.** Eso es `PROVEN` sobre el corpus y
`NOT_DETERMINED` sobre si el hardware de NAVI lo acepta.

## 5 · POR QUÉ SE REGISTRA AUNQUE NO SEA DE NUESTRA GPU

Porque es el **residuo** de la ampliación del oráculo, y el residuo es la parte
que hay que enseñar. Al subir la corroboración de 129 a 222, los dos votos que
quedan en contra son los únicos que **podrían** desmentir `1062`. Y tras
adjudicarlos uno a uno, los dos son de alcance, no de fondo: uno es de
NAVI, y el otro (`RUN_CLEANER_SHADER`) es un emisor que escribe el payload por
una vía que mi contador todavía no reconoce.

Un residuo que se publica y se explica es un residuo controlado. Uno que se
redondea a «cero discrepancias» es una mentira, aunque el número redondeado
sea el que uno quiere oír.

## 6 · CONEXIÓN CON 1068

Este hallazgo es el mismo modo de fallo que `1068`, visto desde el otro lado:
en `1068` un oráculo **fabricó** evidencia en contra y yo lo corregí; aquí un
oráculo **produjo** evidencia en contra que resultó ser real, y la dejé.

La asimetría es la misma en los dos casos y es la regla del instrumento:
**el sesgo va hacia "no se puede concluir", nunca hacia "acuso".** En `1068` eso
significaba no contar 11 votos falsos; aquí significa no descartar 2 votos
verdaderos hasta haberlos adjudicado.