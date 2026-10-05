# 1188 — La escalera V0→V6 no se implementa como tabla: sería un dato falso con forma de dato. Lo que sí es medible es **qué queda por hacer a mano**. Y los huecos dicen que las capacidades más valiosas del proyecto **no existen**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=TOOL-ENGINE + GAP-ANALYSIS
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 ni 0000:00:02.0
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (121 -> 136 vectores, rc=0)
CLASE=TOOL-FACTORY · GAP-DETECTION · ESTADO=PROBADA_OK
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · Lo que NO se hizo, y por qué es la decisión principal

La propuesta incluye una escalera V0→V6 con **porcentajes de capacidad**
(`V6 100%`, `V5 80%`…) y un ranking con estrellas. Es un **marco narrativo**, y
por eso **no se implementó como tabla**.

```text
IMPLEMENTARLO COMO TABLA     una intuicion convertida en dato, con formato
                             de dato. Y este proyecto ya ha pagado varias
                             veces por "numero plausible y equivocado".

LO QUE SI SE PUEDE MEDIR   para cada capacidad: ¿la hace rxre, o tiene que
                           hacerla la IA a mano?
```

Esa reformulación es la que da contenido al requisito de la escalera —"qué
todavía tiene que hacer la IA"— y es comprobable.

## 1 · LA REGLA QUE LO IMPIDE INFLARSE

```python
UNA CAPACIDAD NO SE DECLARA AUTOMATIZADA SIN UN VECTOR QUE LA EJERCITE.
```

Sin vector, `residual` no puede estar vacío: tiene que decir qué mano queda. Y
eso se **prueba con un vector que mete una capacidad falsa**:

```text
MADUREZ["PRUEBA_SIN_VECTOR"] = ("V9", True, "", "")
madurez("PRUEBA_SIN_VECTOR")
  -> automatizada = False
  -> residual = "NO HAY VECTOR que lo demuestre: se degrada a manual"
```

Una capacidad "automatizada" sin prueba es exactamente la clase de cosa que este
proyecto ha pagado. La puerta está puesta antes de necesitar.

## 2 · EL SALDO REAL

```text
$ rxre madurez

MANIFIESTO DE MADUREZ  19 capacidades
  automatizadas (con vector): 13

  pendientes de la IA:
    TOOL_EXECUTE       V2  rxre PLANIFICA y SONDA, pero no ejecuta el pipeline
    RESULT_NORMALIZE   V2  cada herramienta devuelve texto distinto; no hay un
                            registro comun
    EVIDENCE_RECORD    V1  rxre no crea entradas de evidencia
    KNOWLEDGE_GRAPH    V4  no hay grafo de relaciones del corpus
    PROVENANCE_GRAPH   V1  la hay por resultado de cache, no por afirmacion
    AUTONOMOUS_RE      NO  el agente decide que investigar, cuando y cuando parar
```

**Seis de diecinueve capacidades las tiene que hacer la IA a mano.** Y una de
ellas —`AUTONOMOUS_RE`— es la que da nombre a todo lo demás.

## 3 · LOS HUECOS, Y LO QUE DICEN

```text
$ rxre huecos

HUECOS  4 capacidades que nadie puede dar
  ISA_ANALYZE          candidatas=rga      ninguna viva: ausentes, fallidas o vetadas
  RUNTIME_CLOCK        candidatas=rocm-smi ninguna viva: ausentes, fallidas o vetadas
  RUNTIME_INSPECT      candidatas=drgn     ninguna viva: ausentes, fallidas o vetadas
  STRUCT_OFFSET_LIVE   candidatas=drgn     ninguna viva: ausentes, falladas o vetadas
```

Las cuatro son de una sola herramienta, y esa herramienta no está.

Y hay un hueco **mayor** que no sale de `huecos`, porque `huecos` solo mira
capacidades **declaradas**. Estas ni siquiera están declaradas:

```text
VMID        ausente        GART        ausente        PDE_PTE     ausente
PDB0        ausente        PAGE_WALK   ausente        REGISTER_DB ausente
```

El proyecto se describe —en su propia narrativa y en la lista de herramientas—
como teniendo "RX-TOOLS-04..10: VM Walk, PDE/PTE Decoder, GART Analyzer, VMID
Analyzer, PDB0 Tracker, Register Database". **Ninguno existe.** El ranking que las
coloca como las de mayor valor las señala y ninguna está hecha.

> El hueco más grande de este proyecto no es una herramienta que falle. Es un
> **conjunto de herramientas que se nombran y no se han empezado**.

## 4 · DOS VECTORES QUE APUNTABAN MAL, Y QUE DECIR ESO ES EL RESULTADO

El primero:

```text
"huecos: ISA_DECODE de GFX8 esta SIN CUBRIR"      ->  FALLA
```

Mi expectativa era que `ISA_DECODE` estuviera sin cubrir, porque `llvm-mc` no
desensambla. **Falsa**: la cubre `llvm-objdump`, y de la forma menos evidente que
hay —`1185` midió que desensambla GFX8 **solo sobre un objeto**, no sobre bytes
sueltos—. Que exista una ruta de cobertura no quiere decir que sea la evidente, y
el hueco se calcula sobre **quién cubre**, no sobre quién se supone que debería.

El segundo falló por otro motivo: `huecos(objetivo)` mira **solo las capacidades
que encajan con la pregunta**, así que con "en vivo: inspecciona el kernel" solo
se pedía `RUNTIME_TRACE` y `RUNTIME_INSPECT` no aparecía. Los huecos de todo el
catálogo se ven con `huecos()` sin objetivo. Ninguno de los dos fallos era de la
herramienta: eran **expectativas mías que no seaban**.

## 5 · SOBRE LA DESCOMPOSICIÓN EN PAQUETES

La propuesta pide `rxre/core/`, `rxre/adapters/`, `rxre/rx550/`, `rxre/cli/`.

**No se hace ahora, y es una decisión con motivo:**

```text
tools/rxre.py   1806 lineas, 136 vectores, un solo punto de entrada

PARTIR AHORA cuando el problema NO es el tamaño, sino que:
  - el nucleo (registry, capability, planner, gates) ya esta separado por
    FUNCION y por comentario, no por fichero
  - `toolreg` ya es un modulo aparte con su propia puerta de selftest
  - partir por CARPETAS crea seis ficheros que se importan entre si, y el
    unico cambio observable es donde vive cada funcion
```

El umbral honesto para partir es "un módulo que se pueda testear por separado sin
arrastrar a los demás". `toolreg` ya lo cumple; el núcleo todavía no lo necesita.
Decirlo es más útil que hacerlo por simetría con el diagrama.

## 6 · Procedimiento

```text
anadido     MADUREZ    manifiesto por capacidad, con version y residual
            madurez()  y la REGLA: sin vector, se degrada a manual
            manual_pendiente()  el saldo de lo que queda para la IA
            huecos()    capacidades que NADIE puede dar, con motivo y candidatas
            CLI madurez / huecos

medido      rxre 136 vectores rc=0
            automatizadas 13 de 19; 6 las hace la IA
            huecos 4 (ISA_ANALYZE, RUNTIME_CLOCK, RUNTIME_INSPECT,
                      STRUCT_OFFSET_LIVE)
            capacidades nombradas y ausentes: VMID, GART, PDE_PTE, PDB0,
                                             PAGE_WALK, REGISTER_DB
            work_scan: 669 ficheros, 568 distintos, 101 repetidos, mas alto 1466

no hecho    ejecucion real del pipeline, normalizacion por herramienta, grafo
            de relaciones, descubrimiento en el sistema de ficheros, y el
            modulo V6. Declarados arriba, no dibujados.

escrituras  0 ficheros de otros agentes; nada commiteado
runtime     RUNTIME=NOT_RUN. Ni la RX550 ni la Intel.
```