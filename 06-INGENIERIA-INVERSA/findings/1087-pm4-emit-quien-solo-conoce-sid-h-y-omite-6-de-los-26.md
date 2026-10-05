# 1087 — `pm4_emit --quien` solo conoce los 119 paquetes que define `sid.h` y **omite en silencio 6 de los 26 que GFX8 sí emite**: el recuento "20 alcanzables en esta placa" es 26, y los seis ausentes son precisamente los tres con defectos de layout

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-SIDE-PM4ALCANCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 · RUNTIME=NOT_RUN
ESCRITOS_POR_ESTA_ITERACION   ninguno: solo lectura de pm4_emit.py y del corpus
MODIFICADO_NADA_EXISTENTE    pm4_codec.py, pm4decode.c, pm4_emit.py y
                          doclint.py quedan intactos; los defectos se
                          REPORTAN, no se reparan (ver §No reparado)
AUTOR=AGENTE-INSTR
CLASSIFICATION=MEASUREMENT+DEFECT · TRACK=STATIC
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=08-ARQUITECTURA/tools/pm4_emit.py:877-935  (quien_usa)
        Concretamente, lineas 899-905: la poblacion se construye desde sid.h
ALCANZADO=la salida de --quien, 136 lineas · 0 escrituras en el arbol
ESTADO=PROBADO · NO reparado (ver §6)
herramienta  08-ARQUITECTURA/tools/pm4_emit.py  (existente; NO se ha modificado)
```

## 0 · El resultado, primero

```
$ python3 08-ARQUITECTURA/tools/pm4_emit.py --quien
PAQUETES DEFINIDOS EN sid.h : 119
A. lo emite gfx_v8_0.c -- alcanzable en esta placa    : 20
```

**El número real es 26.** `gfx_v8_0.c` emite **26** tipos de paquete distintos, y
**6 de ellos no aparecen en ninguna de las 136 líneas de la salida**:

```
PACKET3_MAP_QUEUES         aparece 0 veces    emission real: gfx_v8_0.c:4345
PACKET3_UNMAP_QUEUES       aparece 0 veces    emission real: gfx_v8_0.c:4773
PACKET3_SET_RESOURCES      aparece 0 veces    emission real: gfx_v8_0.c:4331
PACKET3_RELEASE_MEM        aparece 0 veces    emission real: gfx_v8_0.c:6239
PACKET3_ACQUIRE_MEM        aparece 0 veces    emission real: gfx_v8_0.c:6776
PACKET3_SET_UCONFIG_REG    aparece 0 veces    emission real: gfx_v8_0.c:850
```

Contraste de control, que demuestra que la búsqueda funciona:

```
PACKET3_COPY_DATA          aparece 1 vez      (esta en sid.h)
PACKET3_EVENT_WRITE        aparece 1 vez      (esta en sid.h)
```

## 1 · EL MECANISMO, LITERAL

`pm4_emit.py:899-905`:

```python
sid = os.path.join(AMD, "sid.h")
with open(sid, ...) as fh:
    defined = set(re.findall(r"^#\s*define\s+(PACKET3_\w+)\b", fh.read(), re.M))
uso = dict((d, []) for d in defined)
call_re = re.compile(r"PACKET3\(\s*(PACKET3_\w+)")
for name in sorted(os.listdir(AMD)):
    if not name.endswith(".c"): continue
    for ln, line in enumerate(fh, 1):
        for m in call_re.finditer(line):
            if m.group(1) in uso:            # <-- AQUI SE CAEN LOS 6
                uso[m.group(1)].append((name, ln))
```

**La población se construye desde `sid.h` y solo desde `sid.h`.** Cualquier
`PACKET3_X` emitido por el driver pero definido en otra cabecera **no está en
`uso`**, y la línea `if m.group(1) in uso` lo descarta sin contarlo y sin dejar
rastro.

`gfx_v8_0.c` **sí** los escribe: la línea 4345 es
`amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_MAP_QUEUES, 5));`. El texto está
ahí. Lo que falta es la clave.

## 2 · LA MAGNITUD DEL HUECO

```
definidos en sid.h                        : 119
definidos en vid.h                        : 156
definidos en vid.h y NO en sid.h          :  69
```

De esos 69, la mayoría son macros de campo (`PACKET3_MAP_QUEUES_QUEUE`,
`PACKET3_UNMAP_QUEUES_PASID`, …), pero **6 son opcodes reales**, y esos 6 los
emite GFX8.

**El subconjunto `sid.h` es el equivocado para esta placa.** `vid.h` es, según
medí en `R2-PM4OPS`, la **única** cabecera de opcodes que `gfx_v8_0.c` alcanza
(141 ficheros alcanzables; `nvd.h`, `soc15d.h` y `gfx_v12_1_pkt.h` no lo son).
Eligiendo `sid.h` como catálogo, la herramienta se queda con la cabecera que
**GFX8 no compila**.

## 3 · POR QUÉ NO ES «UNA LIMitación MÁS»: AFECTA A LAS CUATRO CATEGORÍAS

`--quien` no solo da un recuento: reparte cada opcode en cuatro cubos, que son
la base del modelo de frontera del proyecto para lo que esta placa puede
ejecutar.

```
A. lo emite gfx_v8_0.c -- alcanzable en esta placa
B. otro motor de GCN3, no el anillo GFX
C. solo generaciones ANTERIORES a GCN3 -- no en GFX8
D. solo generaciones POSTERIORES a GCN3 -- no en GFX8
E1. OPCODE real que NADIE emite en amdgpu
E2. ...
```

**Los cinco cubos se calculan iterando sobre `defined`, que viene de `sid.h`.**
Los 6 paquetes omitidos no están mal clasificados: **no están en ningún cubo**.
Eso significa que **ninguno de los cinco cubos es interpretable** para un opcode
definido solo en `vid.h`, porque la pregunta nunca se le hizo.

Y hay un caso donde el efecto es actively misleading: el cubo `E1` se titula
*"OPCODE real que NADIE emite en amdgpu — los usa Mesa, el firmware, o no los usa
nadie"*. `MAP_QUEUES` **sí lo emite `gfx_v8_0.c`**. No aparece en `E1` por
construcción, pero el lector que busque «qué paquetes están muertos» y no lo
encuentre concluirá razonablemente que está en ese cubo.

## 4 · LA IRONÍA QUE SÍ SE MIDE

De los seis paquetes invisible, **tres son exactamente los de los hallazgos
`1061`, `1073` y `1082`**:

| invisible para `pm4_emit` | defecto que ya tiene |
|---|---|
| `PACKET3_MAP_QUEUES` | `1082`: `CONTROL2` sin `queue`, `pipe` ni `me` |
| `PACKET3_SET_RESOURCES` | `1073`: aprobado por el verificador y con los campos donde no tocan |
| `PACKET3_CP_DMA` *(visible, pero `0x41` mal nombrado en `pm4decode.c`)* | `R2-PM4OPS`: `PREAMBLE_*` donde vale `COPY_DATA`/`CP_DMA` |

**El recuento de alcance y el análisis de layout usaron poblaciones
incompatibles.** `layoutcross` mide sobre la población de `vid.h`; `pm4_emit`
recoge sobre la de `sid.h`. Los dos están «bien» y por eso las cifras no casan:
`26` contra `20`, y tres paquetes con defectos que la herramienta de alcance no
menciona.

## 5 · LA LIMITACIÓN QUE EL TOOL DECLARA, Y LA QUE NO

`pm4_emit.py:893-896` declara, y con acierto:

> LIMITACION DECLARADA: es un escaneo de texto sobre `"PACKET3(PACKET3_X"`, y no
> ve un opcode en variable. […] Se declara; no se disimula.

Esa es una limitación **correcta y honesta**. Pero **no es la que está causando el
fallo**. La que causa el fallo es otra y no está en ninguna parte:

```
LIMITACION NO DECLARADA
  el catalogo de opcodes es sid.h, y la placa objetivo NO compila sid.h
  todo opcode definido fuera de sid.h se descarta sin contarse y sin aparecer
  en la salida, con lo que la ausencia es indistinguible de la no-emision
```

El propio `pm4_emit` razona sobre esta distinción en otra parte — su categoría
`E1` es literalmente *«definición muerta, o la usa el firmware»* — así que la
diferencia entre «definido y no emitido» y «ni siquiera registrado» está dentro
de su propio modelo dePensamiento, y en este punto no la aplica.

### La distinción de fondo: catálogo derivado frente a catálogo escrito

El bug no es «se equivocó de fichero». Es que **el catálogo está escrito a mano**:

```python
# pm4_emit.py:899
sid = os.path.join(AMD, "sid.h")
```

Un catálogo escrito a mano **no puede ser correcto para otra placa por
construcción**, y este proyecto es explícitamente de una sola placa (§2, §5: sin
portabilidad por defecto). Es la razón por la que el fallo es silencioso: quien
lo escribió no tenía forma de notar que la lista estaba incompleta, porque la
pregunta que lo habría delatado —*¿de dónde sale esta lista y por qué esa?*— no
está planteada en ninguna parte del fichero.

El contraste con la herramienta hermana es el que lo deja claro:

```
tools/pm4ops.py:72
    HEADERS_OPCODE = ["sid.h", "vid.h", "cikd.h", "nvd.h", "soc15d.h", ...]
```

Catálogo **derivado** — y además la asimetría `sid.h`/`vid.h` está tratada
explícitamente en `pm4ops.py:596` (*«están en sid.h y NO en vid.h: no existen
para GFX8»*). Ese instrumento **no** tiene este fallo, y la razón es
estructural: su población sale del **cierre de includes** de la generación
objetivo, así que si la cabecera de la placa cambia, la población cambia sola. Un
catálogo escrito a mano no puede tener esa propiedad.

## 6 · LO QUE NO ESTÁ HECHO, Y POR QUÉ

**No he modificado `pm4_emit.py`.** Es de otra sesión activa.

**No he calculado el alcance "real" más allá de 26.** He contado los tipos de
paquete distintos que `gfx_v8_0.c` escribe. Si el mismo opcode se emite en dos
sitios con semántica distinta —`RELEASE_MEM` se usa para fences y para
`cp_dma`, por ejemplo— el número 26 es un recuento de **tipos**, no de
**situaciones de emisión**, y no lo presento como la frontera real.

**No hemirado si el fallo se propaga a otros modos de `pm4_emit`.** He medido
`--quien`. Los modos `--func`, `--control` y `--frame-size` pueden tener el mismo
origen o no, y no lo he comprobado.

## 7 · EL CONTRATO DE LA REPARACIÓN, PARA QUE NO SE PIERDA

```
REPARACION  la poblacion de --quien deja de venir de sid.h y pasa a ser la
            UNION de las cabeceras de opcodes alcanzables desde la generacion
            objetivo. Medido: para GFX8, sid.h + vid.h.
            Nada mas: la regex, los cuatro cubos y la salida siguen iguales.
ALCANCE     despues, el recuento de A debe decir 26, y MAP_QUEUES,
            UNMAP_QUEUES, SET_RESOURCES, RELEASE_MEM, ACQUIRE_MEM y
            SET_UCONFIG_REG deben aparecer en el cubo A
TEST        positivo: --quien | grep PACKET3_MAP_QUEUES -> 1 linea, cubo A
            negativo: el recuento de "definidos" pasa de 119 a la cardinalidad
                      de la union, y se declara cual es la union
            ronda:     las 136 lineas actuales siguen siendo subconjunto del
                      resultado nuevo; ningun opcode visibile se pierde
INVARIANTE  la categoria que coloca COPY_DATA en A no cambia
LIMITACION  la de "opcode en variable" se mantiene y se anade la del catalogo,
            que es la que faltaba
```

## 8 · PROCEDENCIA

```text
mecanismo   pm4_emit.py:899-905   defined <- sid.h ; uso se indexa por defined ;
                                 `if m.group(1) in uso` descarta el resto
poblacion   sid.h 119 opcodes · vid.h 156 · solo en vid.h 69
emisiones   gfx_v8_0.c: 26 tipos distintos
              20 visibles para pm4_emit   6 invisibles
salida      --quien -> 136 lineas; los 6 ausentes aparecen 0 veces
control     COPY_DATA y EVENT_WRITE (en sid.h) aparecen 1 vez cada uno
alcance     cierre de includes ya medido en R2-PM4OPS: de 141 ficheros
            alcanzables desde gfx_v8_0.c, vid.h es el unico con opcodes
encargos    /tmp/opencode/quien.out
escrituras  0 ficheros de otros agentes
```

**Lo que este documento NO prueba.** No prueba que los 6 packets no se ejecuten:
prueba que `gfx_v8_0.c` los escribe y que `pm4_emit --quien` no los ve. No prueba
que el recuento correcto sea 26 como «frontera»: es 26 **tipos distintos
emitidos**, y un tipo puede emitirse con semántica distinta en sitios distintos. No
afecta a la corrección de los otros modos de la herramienta, que no he medido.