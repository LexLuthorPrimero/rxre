# 1079 — el primer censo con denominador: 99 campos de procedencia en 42 documentos, y 51 de los 99 son afirmaciones que no se sostienen

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=ADJUDICACION · TRACK=STATIC+GIT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=docs/EVIDENCE-MATRIX.md · findings/*.md · 08-ARQUITECTURA/artifacts/*/HALLAZGOS.md
ORIGEN=1059 §5 (mi censo no tenia denominador) -> 1070 (6 documentos invisibles)
ESTADO=PROBADO · censo PARCIAL por 5 documentos · NO he corregido nada
herramienta   tools/sello_prov.py 1.3.0
```

## 0 · El censo, y por qué el denominador es lo primero

Los cuatro censos anteriores de este trabajo, y el último antes de éste:

| | errores de parseo | bloques | campos | ficheros |
|---|---|---|---|---|
| 1059 | — | 16 | 39 | 15 |
| 1070 antes | **6** | 41 | 89 | 34 |
| 1070 después | 0 | 45 | 93 | 37 |
| **este** | **0** | **51** | **99** | **42** |

**99 campos de procedencia declarados en 42 documentos.** Y de esos 99:

```text
COINCIDE  18   el hash se recalcula y es ese
DIVERGIO   9   el fichero ha evolucionado (§ del 1071)
DIFIERE   15   el hash NO es el del fichero citado
ROTO      14   el fichero citado no existe
MALFORMADO 7  la linea no es un hash
AMBIGUO    2  el mismo digest declara varios ficheros (§ del 1058)
EXISTE    31  el fichero existe (complementa a los anteriores)
```

**Sólo 18 de 99 son afirmaciones que se sostienen tal como están escritas.** 31 son
`EXISTE`, que es una comprobación de existencia y no un cotejo de valor — la
distinción que el `1057 §1` hizo — y por eso no cuentan a favor.

**Y esto sólo es el censo de 42 de 47 documentos con vallas.** Los otros 5 están
`PARCIAL` por valla sin cerrar y siguen entrando en el recuento como incompletos. El
número real es **mayor que 99**, y no lo sé: `LIMITACION`, no `PROVEN_ABSENT`.

## 1 · Los 5 documentos que todavía no entran, y por qué es un `NOT_AVAILABLE`

```text
06-.../063-memoria-sesion-smu-estado-persistente.md   valla abierta en la 5180
06-.../083-sg-cache-coherency-l1-l2-y-asimetria.md   valla abierta en la 136
06-.../1000-de-pci-enumeration-a-gpu-r…                valla abierta en la 461
docs/MASTER-RESEARCH-STATUS.md                        valla abierta en la 391
```

Son **5**, no 6: `docs/EVIDENCE-MATRIX.md` salió al arreglar el conteo de
backticks. Y el `063` tiene 403 vallas, con las 402 anteriores ya contadas.

**El coste de no contarlos:** el `063` es el documento de sesión-SMU más largo del
árbol, 232 KB, y el `EVIDENCE-MATRIX.md` es el índice de evidencia del proyecto.
Que dos de los cinco sean precisamente esos dice algo del instrument, no de los
documentos: **la observabilidad y la importance no están correlacionadas**, y un
instrumento que pierde los ficheros grandes pierde justo lo que más importa.

## 2 · Los 15 `DIFIERE`, y POR QUÉ NO SON TODOS IGUALES

Esta es la parte que hace el censo útil y la que lo hace peligroso, y la
distinción es la del `1058`: **¿fue el hash verda alguna vez?**

### 2.1 Los míos por haber movido la herramienta — **9 `DIVERGIO` + sus `DIFIERE`**

```text
1057:12  DIVERGIO  1.0.0 -> 1.1.0   la herramienta evolucionó
1057:13  DIFIERE   7d2bcc1f…        consecuencia del anterior
1058:12  DIVERGIO  1.0.0 -> 1.1.0   ídem
1058:13  DIFIERE   9bc06ad8…        ídem
1062:10  DIVERGIO  (pm4ops)        ídem
1062:11  DIFIERE
1063:10  DIVERGIO  (pm4dec)         ídem
```

**Son consecuencia de mi propiaactividad**, y son `DIVERGIO` porque el fichero
evolucionó, no porque nadie lo tocara en silencio. Es exactamente el caso que el
`1071` nombró y que, sólo con `DIFIERE`, era indistinguible de un dedo ajeno.

### 2.2 Los que son de otra sesión y están en vuelo — **NO ADJUDICO**

```text
1061:189  ROTO   fuente
1063,1067,1068,1082  DIVERGIO / ROTO
R5a-PROSA:20  MALFORMADO   reproducible
R6-PM4TILA:15  MALFORMADO  reproducible
```

**Un `DIFIERE` sobre un fichero que se está escribiendo no es interpretable**
(§50 CONFOUNDERS). La otra sesión reservó `1063`–`1068` en lotes y sigue
produciendo hallazgos. Medir su material en vuelo es medir una carrera.

**Lo que sí es un resultado, y no depende de quién escribió qué:** el instrumento
**los ve**. Antes del `1070` no los veía. Su silencio se parecía a un expediente
limpio.

### 2.3 Los que sí son compuestos míos — **2, y son los interesting**

```text
977:318  DIFIERE   rx550_vmid0_gart.h   -> DECAY (03eb79c, 28f1c47)
977:322  DIFIERE   tests/Makefile       -> NACIÓ FALSO (0 commits, renumeración 968->977)
```

Ya adjudicados en el `1058 §1`. Los cito para que se vea que el censo los vuelve a
encontrar **sin ningún conocimiento del `1058`**: son los mismos dos, por las mismas
razones, y el instrumento no sabe nada de la renumeración.

### 2.4 Los 2 `AMBIGUO` — el caso que el `1058` no tenía

```text
977:326  AMBIGUO   0280d616a3dd774c…  declara gate-run-1.txt
977:328  AMBIGUO   0280d616a3dd774c…  declara gate-run-2.txt
```

**El mismo digest declara dos ficheros distintos y cumple en ambos.** Los valores
son correctos —`COINCIDE`— y sin embargo **el hash no distingue ninguno de los
dos**, porque las dos salidas de la puerta tienen el mismo contenido. Una
afirmación de procedencia que se apoya en un valor que no discrimina es
`COINCIDE` y no es una verificación.

**El `1058 §3 B2` lo señaló como riesgo y aquí está medido por primera vez como
veredicto propio.**

## 3 · Los 14 `ROTO`, y por qué 11 son culpa mía

```text
ATOMBIOS-DECODER.md:527-537   6   cites drivers/gpu/drm/amd/... que existe en
                                   RESEARCH/baseline/linux-7.1.3/ (maxdepth 13)
401:134                       1   cita amdgpu/gfx_v8_0.c, que no existe con ese nombre
resto                         7   de documentos en vuelo de otra sesión
```

Los 6 de `ATOMBIOS-DECODER.md` son **mis falsos positivos**, y ya los había
adjudicado el subagente `explore` del `1059`: el fichero existe, a profundidad 13, y
mi instrumento resuelve contra la raíz del proyecto. **No he arreglado la raíz de
resolución**, porque hacerlo requiere decidir cuál es la raíz de un documento que
cita un árbol con prefijo — y esa decisión no es sintáctica.

`401:134` sigue `NOT_DETERMINED` desde el `1059`. No lo he tocado.

## 4 · Lo que este censo NO es

- **No es una puerta.** No está en `check.sh`, no está en `pipeline.py`, no hay
  hooks ni CI. MEDIDO en el `1059 §5` y **sigue siendo cierto**. Publicar el
  instrumento sin conectarlo es el `tool theater` de §99, y no lo he hecho porque
  conectarlo con `rc=4` sobre 42 documentos **puede poner el pipeline entero en
  rojo** por 14 `ROTO` que son míos y por material en vuelo de otra sesión. **Un
  gate que se enciende con falsos positivos entrena a ignorar sus propios rojos.**
- **No es una auditoría de los 42.** Es una **clasificación**. El catálogo de cada
  veredicto no limpio está en el JSON, y adjudicarlos uno a uno es trabajo humano.
- **No cubre el sello de evidencia.** Eso es `sello.py`, y va por otro camino
  (`1059`, `1060`).
- **No cubre `archive/`**, que usa el layout `sha256sum` clásico y está excluido
  del barrido por volumen.
- **Medido sobre un árbol que se está escribiendo.** Las cifras son de un instante.

## 5 · Procedencia

```text
artefacto    /tmp/opencode/censo6.json   (51 bloques · 99 campos · 42 ficheros · 5 parciales)
herramienta  tools/sello_prov.py 1.3.0   57 vectores, 0 fallos, 27 mutaciones
censo        rc=2, por 5 documentos PARCIAL  -- no es un veredicto favorable ni desfavorable
sello        revkit/sello.py  OK 177 · MOVIDO 68 · ROTO 0 · rc=1
adjudicados  1058 §1 (los 2 de 977) · 1059 (los 30 SELLADO_PERDIDO) · 1069 (los 2 .mod.c)
escrituras   0 en el árbol. Nada re-sellado. Nada commiteado de la otra sesión.
```

**Lo que este documento NO prueba.** No prueba que los 51 no limpios sean defectos:
prueba que **no son afirmaciones que se sostienen tal como están escritas**, que es
otra cosa y más pequeña. No prueba nada sobre el hardware, el driver ni el
rendimiento. Y el denominador —99— **no es el número de declaraciones que hay en el
árbol**: es el de las que este instrumento puede leer.