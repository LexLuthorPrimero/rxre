# Reconciliación del nodo Q5-CORPUS-UNIVERSE — 2026-10-03

AUTORIA=global-coordinator · WORK_CLASS=reconciliación · WRITE_EXECUTION=1 fichero nuevo
RUNTIME=NOT_RUN · GPU=INTACTA · AUTHORIZATION=LOCK_TAKEOVER ("rompe todo", humano)

Este documento **no decide** el fondo de la cuestión. Registra lo que el coordinador
verificó por sí mismo sobre el resultado de un worker, y separa las tres cosas que en
este proyecto se confunden constantemente: lo que se **midió**, lo que el worker
**afirmó**, y lo que el coordinador **no pudo** corroborar.

---

## 1. Estado del nodo

```
NODE_ID        Q5-CORPUS-UNIVERSE
WORKER         sesion-missing
CERRADO POR    RESOLVED_WITH_RESIDUAL_UNIVERSE
ACEPTADO POR   global-coordinator = SI (verificado, no heredado)
```

Artefacto, con hash medido por el coordinador y no copiado del informe:

```
06-INGENIERIA-INVERSA/findings/968-q5-universo-de-tablas-gfx8.md
  sha256  f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2   COINCIDE
  bytes   24417     lineas 475     mtime 2026-10-03 10:50
```

## 2. Verificación independiente de las afirmaciones load-bearing

El informe del worker es evidencia sobre una medición. No es la medición. Estas cinco
se comprobaron por separado, y las cinco se sostienen:

| # | Afirmación del worker | Verificación del coordinador | Estado |
|---|---|---|---|
| V1 | `grep -c '^#define SQ_S_'` = 216 | 8 copias localizadas; **las 8 con 216** y sha `fa6b8ff974fccdd5` idéntico | CORROBORADO |
| V2 | La ISA que rotula las 5 tablas son 348 pp | `pdfinfo` → **348**; sha `8e49a3767b337ec8` | CORROBORADO |
| V3 | ASIC = `[1002:699f]` rev c7, Lexa PRO | dos vías: `lspci -d 1002:699f` → *Lexa PRO* rev c7, y `/sys/bus/pci/devices/0000:01:00.0/device` → `0x699f` | CORROBORADO |
| V4 | 967 y DRIVER-MISSION-STATE intactos | ambos sha idénticos al fijarlos, **después** del nodo y **después** del commit ajeno | CORROBORADO |
| V5 | El filtro del universo está declarado | §5 del artefacto, con comandos literales | ACEPTADO |

**La V3 tiene un matiz que el coordinador se anotó a sí mismo y que queda escrito
porque el error es fácil de repetir:** `lspci -nn 01:00.0` devolvió **vacío** en la
primera comprobación. No era que el ASIC no estuviera: era un argumento mal formado
(`-s` es el selector). Un `NOT_FOUND` por un comando mal escrito es un
`NOT_OBSERVED`, no un `PROVEN_ABSENT`. Queda registrado para que nadie lo lea como
prueba de que la GPU no estaba.

## 3. DRIFT sobre el sustrato — evaluado, no descartado

El `HEAD` se movió durante el nodo, por un commit que **no es de este trabajo**:

```
58244a8152c88dca641a38a878ab891d3b645e4b   (fijado en el despacho)
3d89682195b03f0244a5a2945f2a9567dff704eb   (HEAD al reconciliar)
  3d89682  docs/CHANGELOG-RESEARCH.md, revkit/{check.sh,selfcheck.py,emitref.py,ibtrace.py,cn-r8.fixture,PTEPDE-GFX8.md}
  7 ficheros, +1169 -73
```

Los tres inputs con hash del nodo siguen **byte-idénticos** (§2 V4). Y los 7 ficheros
del commit están fuera del universo declarado: ninguno es una cabecera ISA, ni un
corpus, ni un volcado BTF.

```
DRIFT_ON_HASHED_INPUTS   = NO
DRIFT_ON_DECLARED_UNIVERSE = NO, por contenido de los 7 ficheros
LIMITE                   = el universo se enumeró sobre plocate; plocate indexa con
                          retraso, asi que un fichero creado en los ultimos segundos
                          pudo no estar. Declarado, no medido como cero.
```

Por eso el nodo **no** se degrada, pero tampoco se declara limpio: se acepta **con
esa limitación escrita**, que es lo que el propio worker pidió para su `find /` de
120 s.

## 4. CONTRADICCIÓN ABIERTA — se registra con las dos fuentes, no se promedia

```
CONTRADICTION_ID   CONTRAD-Q5-AUSENCIA-TABLAS
AFIRMA             08-ARQUITECTURA/designs/DRIVER-MISSION-STATE.md:136-138
                   "4 de las 5 tablas de opcode GFX8 no están en el corpus …
                    NOT_AVAILABLE, con forma precisa"
                   sha256 21f8ca0e346ea271494b050bd5b9ef4e4c0370f604e9da3baf25c0dd9c9a661b

REFUTA             06-INGENIERIA-INVERSA/findings/968-q5-universo-de-tablas-gfx8.md
                   sha256 f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2

ALCANCE DEL REFUT   El *enunciado* de ausencia esta mal formado, por dos errores
                   independientes y ambos medidos:
                     (a) DE UNIDAD — las "5 tablas" no son 5 ficheros sino 5
                         subconjuntos del MISMO fichero. 5/5 presentes, 216/216.
                     (b) DE UNIVERSO — la fuente que si rotula las 5 tablas existe en
                         esta maquina y el proyecto ya la catalogo como M-01.
NO TOCA            El gate real. El bloqueo que sobrevive no es una tabla de opcode
                   ni de campos: es la CABECERA DE PAQUETE PM4 para el CP, que la
                   tabla que "faltaba" tampoco resolvia.
```

**Ninguno de los dos textos se modifica aquí.** El estado canónico sigue afirmando lo
que afirma; el finding sigue refutándolo. La contradicción queda viva y con las dos
fuentes, que es lo que §80 exige: no hay ganador intuitivo.

## 5. HALLAZGO PROPIO DEL COORDINADOR — la fuente decisiva está fuera del proyecto

Esto no lo yieldó el worker, y es la razón de que su siguiente paso no sea ejecutable
tal cual.

```
AFIRMACION DE ORIGEN   RESEARCH/polaris12xl/LIBRARY-CATALOG.md:630   (DENTRO del root)
                       M-01 | `RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf`
                       "AMD Graphics Core Next, Generation 3 ISA, 348 pp … GFX8 = GCN 3.
                        Es la ISA del objetivo"

COMPROBADO
  05-FUENTES-PDF/ dentro del root          NO EXISTE   (existe 05-FUENTES-EXTERNAS/)
  RX550-INVESTIGACION/ dentro del root      NO EXISTE   (la cita no resuelve desde el root)
  git log --all -- '*gcn3-isa*'             VACIO       (nunca estuvo versionado)
  unica copia en la maquina
    /home/lucas/Descargas/RX550-INVESTIGACION/05-FUENTES-PDF/gcn3-isa.pdf
      2 752 924 B   sha256 8e49a3767b337ec8…   348 pp
  ese arbol, su estado
    406 MB · 16 .md · 0 findings · ultimo mtime 2026-09-27 13:38

CLASIFICACION
  EN_EL_ROOT                NOT_FOUND        la cita M-01 no resuelve
  VERSIONADO                PROVEN_ABSENT    git log vacio, en toda la historia
  EN_FUERA_DEL_ROOT         OBSERVED         una copia, con hash
  FRESCURA_DE_EA_ARBOL      STALE            6 dias; §86 lo hace terminal de primer nivel
```

Por §91 el árbol activo es `~/Escritorio/RX550-INVESTIGACION`. La fuente primaria que
desbloquea Q5 vive en un **segundo árbol**, con seis días de retraso y sin versionar. El
índice que la declara obligatoria está dentro del root y apunta a una ruta que no
resuelve. Eso no es "la fuente está disponible": es **una cita rota que apunta a un
sitio real fuera del proyecto**.

## 6. CONSECUENCIA sobre el siguiente paso

El `NEXT_NODE` que devuelve el worker es `pdftotext -f 258 -l 288 gcn3-isa.pdf` →
tabla `{opcode → (valor, TABLA)}`, comprobando cobertura de los 216 `SQ_S_*`. El
discriminante es bueno y el coste es de segundos. Pero **tal como está escrito depende
de leer un fichero fuera del árbol activo, sin versionar y con el árbol de origen
obsoleto**: exactamente la condición que §91 exige identificar y trazar antes de
depender de ella.

```
DECISION PROPUESTA (NO EJECUTADA)
  Traer SOLO gcn3-isa.pdf (2,75 MB) al root, con su sha256, para que M-01 resuelva
  y la dependencia de Q5 quede dentro del proyecto y versionada.

  POR            §91 (trazabilidad de dependencias externas) + §37 (lineage del artefacto)
  ALTERNATIVA A   Dejarlo fuera y registrar la ruta + hash en el catálogo. Mas barato,
                 pero el próximo agente que lea M-01Tropezara igual que este.
  ALTERNATIVA B   Traer los tres PDF (144 MB, con king-2008-ocr.pdf de 140 MB).
                 Descartada: 140 MB de OCR para un nodo que no los necesita.
  DISCRIMINANTE   ¿el cap. 12 cubre los 216 opcode? Si cubre un subconjunto, el hueco
                 es de COBERTURA y se declara PARTIAL; nunca PROVEN_ABSENT.
  CONSECUENCIA    +2,75 MB en el repo; el catalogo pasa a ser resoluble.
  REVERSIBILIDAD  Total: es un fichero anadido, con hash; se borra sin dejar estado.

  NO SE EJECUTA EN ESTE TURNO porque PROJECT_ACTIVE_AGENT <= 1 esta ocupado por una
  segunda sesion viva (ver §7). No es una dependencia externa irreductible: es una
  espera con condicion de re-chequeo, y la condicion esta escrita mas abajo.
```

## 7. Entorno — dos hechos que hay que saber antes del próximo despacho

```
CERROJO RAIZ        TOMADO por esta sesion, con owner escrito.
                    Autorizacion: humano, "rompe todo".
                    Snapshot previo de todo lo no regenerable:
                      /var/tmp/rx550-rescue/20261003-102857/
                        uncommitted-tracked.patch   855 181 B  bde24dbd…
                        untracked-noncache.tar     12 728 320 B  eb892cef…
                        untracked-noncache.lst         38 135 B  acf195c2…
                        porcelain.txt                  34 336 B  8a639a69…
                      (740 ficheros no-cache, 227 .md. Los 6,2 GB de AST son
                       regenerables por run_all y se excluyeron a proposito.)

SESION CERRADA       PID 711877 (pts/5) — SIGTERM, terminada.
HUERFANO             PID 767112 seguia escribiendo revkit/check.sh tras morir el
                     padre: el porcelain subio 585 -> 586 durante la propia
                     comprobacion. MATADO. Sin el, la toma de turno no era real.

SEGUNDA SESION VIVA  hijos del servidor 825092 ejecutando tools/dupenum.py mientras
                     se reconciliaba. Ocupa PROJECT_ACTIVE_AGENT <= 1. Su trabajo
                     (numeracion duplicada) NO solapa con este nodo.

COLISION DE NUMERO   06-INGENIERIA-INVERSA/findings/ contiene DOS 968:
                       968-el-documento-que-declara-que-manda-…md   (6622 B)
                       968-q5-universo-de-tablas-gfx8.md              (24417 B)
                     No resuelta aqui: la otra sesion esta corriendo dupenum.py sobre
                     exactamente eso. Tocar la numeracion ahora seria pisarla.
```

## 8. Condición de re-chequeo para el siguiente despacho

No es "esperar". Es una condición comprobable:

```
DESPACHAR  cuando SE CUMPLAN LAS DOS:
  1  no hay ninguna sesion viva colgando del servidor opencode
  2  porcelain estable durante 3 minutos consecutivos
ENTONCES  nodo Q5-ISA-CAP12: extraer el cap. 12 de gcn3-isa.pdf a
          {opcode -> (valor, TABLA)} con procedencia, y medir la cobertura
          sobre los 216 SQ_S_*.  Coste: <10 s CPU, 1 fichero, sin GPU, sin sudo.
```

## 9. Lo que este documento NO dice

```
NO dice que la ISA se haya leido.        Solo que la pagina 348 y el hash son esos.
NO dice que el cap. 12 cubra los 216.    Nadie lo ha medido todavia.
NO dice que M-01 sea la fuente correcta. Es la fuente que el proyecto catalogo; que
                                         sea la que conviene para GFX8 es otra
                                         pregunta, y tiene contraejemplo vivo:
                                         vega-isa.pdf esta en la misma carpeta y es
                                         de otra generacion.
NO cierra la contradiccion CONTRAD-Q5- AUSENCIA-TABLAS. La deja viva y con las dos
                                         fuentes, que es lo que corresponde.
```

---
AUTORIA=global-coordinator
WORK_CLASS=reconciliación
WRITE_EXECUTION=1 fichero nuevo en 08-ARQUITECTURA/decisions/ bajo cerrojo recon-q5
RUNTIME=NOT_RUN · GPU=INTACTA · SIN SUDO · SIN COMMITS
INPUTS_VERIFICADOS  HEAD 3d89682195b03f0244a5a2945f2a9567dff704eb
                     STATE.md 21f8ca0e346ea271494b050bd5b9ef4e4c0370f604e9da3baf25c0dd9c9a661b
                     967      9266c886c0543d2b4fcab659409568c7f02a584d4464ff8324536cf95c5b3dc1
                     968      f46e67e251c0295545d2845893e2e009467e521db7dcfd56d23c0d544e14f8d2
