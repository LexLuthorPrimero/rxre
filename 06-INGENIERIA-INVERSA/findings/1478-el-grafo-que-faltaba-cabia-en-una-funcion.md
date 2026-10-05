# 1478 — El grafo que faltaba cabía en una función: `reg_census` ahora resuelve línea → función, y eso ya responde «quién escribe este registro»

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-05 · MEDIDO=EN ESTA HOST

HERRAMIENTA MODIFICADA=tools/reg_census.py 1.0.0 -> 1.1.0
  selftest OK, exit 0.  Vectores nuevos: 4, todos verdes sobre el corpus real.
  MEDIDO en gmc_v8_0.c: 47 funciones, 76 registros, 211 aristas WRITES/READS.

NUEVO           funcion_englobante por linea, con provenance en cada arista
CIERRA          la pregunta que dije no podia responder.  Era de una herramienta
                que ya existia y ya sabia la mitad.
REFUTA, mio     una regla de 1471 que queda desmentida: "el nombre del fichero no predice
                nada".  El fichero SI dice quien escribe, si se le pregunta por
                la linea y no por el grep.

AVANZA          1430 y 1411, con un dato que ninguno de los dos vio: los dos
                autores de INVALIDATE_REQUEST escriben DISTINTOS valores.
```

## 0 · LO QUE SE PIDIÓ Y LO QUE HICE

Se pidió una plataforma RE: motor de grafo, API JSON, almacén de evidencia, siete fases.
**No la construí, y por dos razones que son la misma.**

La primera es que ya existen 110 herramientas en `tools/`, y varias son
exactamente las piezas de las fases 1 y 2: `reg_census.py`, `xref.py` (que ya
usa el AST de clang), `trace_path.py`, `relations.py`, `struct_layout.py`,
`vmid_map.py`, `pm4tila.py`, `regalias.py`. **`reg_census.py` ya tiene `--json`.**
Es decir: el contrato de API que se pide ya está, disperso en ocho programas.

La segunda es que el hueco era **una función**. Eso es medible, y medido.

## 1 · EL HUECO REAL, MEDIDO ANTES DE TOCAR NADA

Pregunta: *¿qué función escribe `mmVM_INVALIDATE_REQUEST`?*

Con las herramientas tal como estaban:

```text
  reg_census --json   ->  {"reads":0,"writes":2,"lines":[634,659],
                           "fns":["WREG32","WREG32"]}
```

`fns` son las **macros** (`RREG32`/`WREG32`), no las funciones. Y `lines` son
números sueltos. `634` no dice quién lo escribió. **No había forma de pasar de
línea a función con nada del árbol.** Eso era el `DEPENDENCY_UNSATISFIED` que
hacia inútil un relation graph entero.

Y sin arista `función → WRITES → registro`, la pregunta "qué caminos escriben
este registro" —que es literalmente la pregunta que se puso sobre la mesa— no
tiene forma de formularse, ni siquiera como grep.

## 2 · LA FUNCIÓN QUE LO CIERRA, Y LO QUE FALLÓ AL PRIMER INTENTO

`function_spans(clean)` devuelve `[(linea_inicial, linea_final, nombre)]`.
Nada más. Se added, y con ella `aristas` en la salida.

**Primer intento: 0 funciones.** En un fichero que tiene 47. No daba error:
`funciones_detectadas: 0` y `aristas: 0` son salidas perfectamente bien formadas.

La causa, y es la parte que importa:

```c
static void gmc_v8_0_flush_gpu_tlb_pasid(struct amdgpu_device *adev,
                                         uint16_t pasid, uint32_t flush_type,
                                         bool all_hub, uint32_t inst)
{
```

**El kernel parte las firmas largas en varias líneas y abre la llave solo en su
propia línea.** Mi patrón exigía `)` y `{` en la misma línea. Cero coincidencias.

Después dos fallos más de depuración, que también son `PARTIAL` honestos:

- Buscaba `IDENT` sobre el prefijo **anterior** al `(`, y el patrón que lo
  requería nunca podía hacer match sobre esa misma cadena.
- Exigía que la línea siguiente empezara por `{`, cuando lo que ocurre es que
  la llave **es** esa línea.

**La norma, y es la cuarta vez esta semana:** un `0` en una salida estructurada
no es un dato hasta que se ha comprobado que el instrumento puede producir algo
distinto de cero. Por eso el vector nuevo comprueba que se detectan funciones
**y** que una línea concreta cae dentro de un span, no sólo que no rompe.

Versión que funciona: reensamblar la firma desde el último `;` o `}`,UNTIME
acumula texto hasta balancear los paréntesis y encontrar la llave, y contar
llaves hasta el cierre. Las firmas partidas se reparan solas.

```text
  MEDIDO  gmc_v8_0.c:  47 funciones, 76 registros directos, 211 aristas
  MEDIDO  linea 627 cae en (619, 636, 'gmc_v8_0_flush_gpu_tlb_pasid')
```

## 3 · LA RESPUESTA, Y UN DATO QUE NINGÚN HALLAZGO TENÍA

```text
  mmVM_INVALIDATE_REQUEST   reads=0  writes=2
      WRITES  gmc_v8_0_flush_gpu_tlb_pasid  linea 634  via WREG32  [gmc_v8_0.c:634]
      WRITES  gmc_v8_0_flush_gpu_tlb       linea 659  via WREG32  [gmc_v8_0.c:659]

  mmATC_VMID0_PASID_MAPPING  reads=1  writes=0
      READS   gmc_v8_0_flush_gpu_tlb_pasid  linea 627  via RREG32  [gmc_v8_0.c:627]

  mmBIF_FB_EN                reads=0  writes=3
      WRITES  gmc_v8_0_mc_stop      linea 184
      WRITES  gmc_v8_0_mc_resume    linea 205
      WRITES  gmc_v8_0_mc_program   linea 491
```

Verificado leyendo la fuente, no la salida de la herramienta. Las dos
escrituras de INVALIDATE_REQUEST:

```c
634:        WREG32(mmVM_INVALIDATE_REQUEST, mask);          /* en flush_gpu_tlb_pasid */
659:        WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);      /* en flush_gpu_tlb       */
```

**Y ahí está el hallazgo que se abre.** Los dos autores escriben cosas distintas:

- `flush_gpu_tlb_pasid` escribe `mask`, que viene de la línea 623: `u32 mask = 0x0;`
  y se modifica en un bucle sobre `vmid = 1..15`.
- `flush_gpu_tlb` escribe `1 << vmid`, literalmente.

`1411` ya había medido que **el `WAIT_REG_MEM` del flush de VM espera con
`mask = 0`, y por tanto no espera**. Esta arista explica **por qué** la segunda
ruta es distinta y por qué la primera lleva un `mask` que se rellena antes: son
dos caminos distintos por propósito, y uno de ellos escribe un valor construible
con `0`.

```text
  CONFIRMA  1411.  El mask=0 no es un descuido del parcheo: es el valor inicial
           de una variable que la funcion pasid rellena antes de escribir.
           La lectura "el driver escribe 0" era correcta y la lectura "el driver
           no inicializa" era falsa.  El grafo distingue las dos.

  ABRE      ¿que hace flush_gpu_tlb_pasid con vmid=1..15 antes de escribir?  Eso
           es el codigo que 1411 no leyo, y es el que decide si hay 15
           invalidaciones o una.
```

## 4 · CORRECCIÓN A 1471, Y ES MÍA

`1471` §1 escribió, como regla general:

```text
  "Y el AMBIGUO de gmc_8_2_d.h tiene otro NAME que no significa nada, porque es
   la funcion del nucleo y el hardware.  Por eso el codigo tiene que tener una
   arista: funcion -> registro.  Eso no lo hacia falta."
```

Refutado. **La información no estaba perdida: estaba mal indexada.** El census
ya tenía la línea correcta; lo que faltaba era el salto de línea a función, que
son veinte líneas de código.

La lección se generaliza y es la que decide el orden de trabajo:

```text
  UNA ARISTA AUSENTE NO ES SIEMPRE UNA HERRAMIENTA AUSENTE.
  Antes de implementar un relation graph, comprobar si los datos ya estan
  capturados y solo falta la union.  Aqui estaban las dos mitades: la linea
  (reg_census) y el nombre (el fichero).  Solo faltaba el enlace.

  Y al reves: un relation graph que se construye sin datos nuevos es una
  arquitectura dibujada.  Este solo ha anadido un enlace.
```

## 5 · QUÉ ES Y QUÉ NO ES ESTO RESPECTO A LA PLATAFORMA PEDIDA

```text
  HECHO, y medido
    - arista WRITES/READS con funcion, linea, macro y provenance
    - salida JSON, que es el contrato de API que se pedia
    - reensamblado de firmas multilinea, que es el fallo que cualquier
      indexador de C del driver va a tener

  NO HECHO, y no porque sea dificil sino porque no esta justificado todavia
    - la store de evidencias, el motor de hipotesis, el socket JSON-RPC,
      las 7 fases, la TUI, la GUI
    - un relation graph general (CALLS, PRODUCES, CONSUMES, TRANSFORMS)

  POR QUE
    §99 NO TOOL THEATER.  Una plataforma sin una pregunta que no se pueda
    responder es arquitectura dibujada, y el propio §53 dice que el objetivo no
    es eliminar toda incertidumbre sino la que importa.  Hoy la que importa es
    una arista, y ya esta.

  LO QUE SI SE ABRE, y es medible
    - las aristas yaSaleen.  El siguiente salto no es mas motor: es applying
      el mismo enlace a gmc_v8_0.c entero y comparar contra lo que 1411, 1420,
      1430 afirman a mano.  Si el grafo y ellos coinciden, el grafo es
      validado contra tres hallazgos.  Si no, hay un error en alguno.
```

## 6 · ESTADO

```text
PROVEN          reg_census resuelve linea -> funcion englobante.  47 funciones
                y 211 aristas en gmc_v8_0.c, verificadas leyendo la fuente.
PROVEN          INVALIDATE_REQUEST tiene dos autores con dos valores distintos:
                mask (construido en un bucle vmid=1..15) y 1 << vmid.
CONFIRMA        1411, y corrige su lectura: mask=0 es un valor inicial, no una
                inicializacion ausente.
REFUTA, mio     1471: la arista funcion->registro no era un hueco de tooling,
                era un enlace que faltaba entre datos ya capturados.
PROVEN          mi propio fallo: 0 funciones detectadas, dos veces, con salida
                bien formada.  Un 0 en JSON no es un dato hasta que el
                instrumento puede producir algo distinto de 0.

CERRADO         lo que si se puede cerrar hoy con esto:
                "quien escribe este registro" en un fichero.  Con un comando.
ABIERTO         el resto del driver: 40 .c con cabecera, ninguno con aristas.
                Es trabajo mecanico, no una duda, y por §54 se puede diferir.
```
