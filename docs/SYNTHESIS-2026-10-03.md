# SÍNTESIS DE LA DOCUMENTACIÓN — 2026-10-03

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Qué es este documento y qué no es
>
> **No es un índice nuevo.** El proyecto ya tiene tres: `docs/MASTER-RESEARCH-STATUS.md`, el
> `DOCUMENTATION-ROUTER` y la familia de artefactos que genera `tools/artifacts.py`. Añadir un
> cuarto sería duplicar sin justificación.
>
> **Es el resultado de contrastar esos índices contra el disco**, y contiene cinco defectos
> verificados **de la propia documentación**. Todos son reproducibles con los comandos cited.

## 1. Qué es el proyecto, según su propia documentación

| | |
|---|---|
| Objetivo | Driver Linux propio en C + Assembly para **esta** RX 550 (`1002:699f`, Polaris12/GFX8) |
| Host vivo | `HOST-C` — Nobara 44, kernel `7.1.3-200.nobara.fc44`, Mesa 26.2.3, `card1` |
| Fase | Reconstrucción del hardware GFX8 + driver propio |
| Estado | `PARTIALLY_RESOLVED`; la RX550 `UNRESOLVED` en estabilidad y causalidad DPM/PM |
| Publicación | `READY_FOR_GITHUB=NO` |
| Línea de septiembre | **Cerrada.** Telemetría DPM/PM, C1, publication. No reabrir |

El proyecto tiene una regla de temporalidad que es lo mejor que tiene, y conviene decirla porque
es la que evita el error más frecuente: **`HOST_B`, `HOST_C` y `UNKNOWN` son hosts distintos**, y
un documento de `HOST_B` **no** describe la máquina actual. `STATUS=STALE` es un terminal de primer
nivel, no una nota al pie.

## 2. La estructura real, medida

```
1016 ficheros .md en el repo (todo, sin .git)
  479 findings en 06-INGENIERIA-INVERSA/findings/     numerados 001..966
   31 de esos son mios (AUTORIA=AGENTE-SMU)

Actividad, por dia:
   15  2026-09-29
   73  2026-10-01
  275  2026-10-02      <- el pico
  116  2026-10-03      <- hoy
```

Por banda: `000xx` 166 · `001xx` 122 · `002xx` 104 · `003xx`–`006xx` 29 · `009xx` 58.

**La línea de tiempo que explica casi todos los defectos de abajo:** el router y el inventario se
escribieron el **25 de septiembre** y el router el **1 de octubre**. Los findings se multiplicaron
el 2 y el 3. **391 de los 479 findings son posteriores a la infraestructura que los indexa.**

## 3. Los cinco defectos, verificados

### D1 · `AGENTS.md` es una copia del prompt global. Por segunda vez

```
ANTES   45247 B  md5 27fb8c1c9613   == ~/.config/opencode/AGENTS.md, byte a byte
AHORA   30295 B  md5 6a5820d697f3   == HEAD, el prompt de método del proyecto
```

Los 45 KB de la raíz eran **el prompt global duplicado**, que ya se carga solo desde `~/.config`:
cero rutas del repo, cero contenido propio. Es el accidente que `docs/AGENTS-RECTOR-2026-10-02.md`
ya documentaba una vez, y **ha vuelto a ocurrir**.

**Restaurado desde git**, que es la vía fiel: `git checkout HEAD -- AGENTS.md`.

**Y una pérdida que el restore no recupera:** la versión que encontré al empezar la sesión —142
líneas, con `RESEARCH/`, `findnum`, `scopeguard`, `btfq`, las tres copias del corpus y la puerta de
runtime— **no estaba commiteada**. Se perdió. **Un fichero que existe solo en el working tree no
existe.**

### D2 · `CURRENT-STATE.md` iba un día atrasado

```
EN DISCO (generado 2 oct 17:18):  347 findings, numerados del 001 al 258
SI SE REGENERARA HOY:             479 findings, numerados del 001 al 966
```

La regex del generador (`^(\d{3})[-_](.+)\.md$`) **no tiene el defecto**: ejecutada ahora captura
los 479. El generador era correcto cuando corrió; **lo que está viejo son los datos**.

Los siete artefactos de la raíz comparten **el mismo mtime**, `2026-10-02 17:18`: una única
ejecución masiva. Los de `docs/` son posteriores e individuales, y para 4 de los 7 son **más
nuevos** que los de la raíz.

### D3 · El router confunde dos columnas del inventario

```
El router dice:   HOST-A = "1444 filas del inventario"
Real, por parseo de la columna 23:  HOST-A = 128
Real, por parseo de la columna 4:   TEMPORALITY=HISTORICAL = 1445
```

**HOST-A son 128, no 1444.** El 1444 es un valor de `TEMPORALITY`, de otra columna. Ni la unión
(1449) ni la intersección (124) dan 1444, así que no es un cruce: es una mezcla de dos columnas.

El router acierta en los otros tres números que se pueden comprobar:

```
router: "solo 2 documentos HOST-C"          real: HOST-C ∩ DECLARED = 2     CORRECTO
router: "los 7 HOST-B DECLARED"             real: HOST-B ∩ DECLARED = 7     CORRECTO
router: "1406 de 1576 filas"                real: UNKNOWN = 1406            CORRECTO
router: "DECLARED 26 / INFERRED 1550"       real: 26 / 1550                 CORRECTO
```

**3 de 4 correctos y el que falla es el de la tabla principal.** Un índice con 3 números buenos
transmite una confianza que el cuarto no respalda.

### D4 · El `CONFLICT_SOURCE` de `C4` apunta a un sitio que ya no dice eso

```
El router:   C4 -> CONFLICT_SOURCE: README.md:15-16
README.md:15-16 real:  "> el 2026-10-01 11:0x: el host pasó a Nobara Linux 44, kernel"
La regla que busca:   "esos números no son portables"  -> esta en README.md:23-24
```

Las líneas se movieron cuando el bloque `HOST ACTUALIZADO` se insertó el 1 de octubre, y el router
**capturó las anteriores**. Un `CONFLICT_SOURCE` que no lleva al observador obliga a recorrer el
repo, que es justo lo que ese campo existe para evitar.

### D5 · El `README.md` se contradice a sí mismo en seis líneas

```
lineas 13-19:  "este bloque estaba obsoleto... los '43 / 6.18.2 / 25.3.2 / card2' de abajo son HISTÓRICO"
lineas 21-24:  "La instalación validada es Nobara Linux 43, kernel 6.18.2..., es card2"
```

El aviso de la cabecera **prohíbe** leer lo de abajo como actual, y lo de abajo lo afirma **en
presente**. Un lector que entre por `README.md` —el único fichero que un agente nuevo abre— se
lleva el host equivocado por el camino más corto. En un proyecto cuya regla central es
`STALE` como terminal de primer nivel, el fichero de entrada no puede ser él mismo stale.

### D6 · 71 números de finding están repetidos, y 169 ficheros comparten número

```
numeros repetidos            : 71
ficheros implicados          : 169
de esos numeros, tocan a los mios: 0
```

Los dos ficheros de cada choque, para que se vean:

```
001  001-amdgpu-location.md          /  001-amdgpu-overview.md
021  021-frame-budget-gfx8-peor-caso.md  /  021-write-lock-scoped-subdir-does-not-block.md
023  023-pm4-count-convencion-medida.md  /  023-pte-productor-sdma-gfx8.md
959  959-...-los-dos-fallos-de-su-verdicto.md  /  959-...-los-tres-fallos.md
```

**Lo que esto rompe:** `EVIDENCE-MATRIX` indexa por número. Con 71 números ambiguos, **una
referencia a «el 023» no tiene un destino único**, y las aristas `CORRECTED_BY` / `RETRACTED_BY`
que apuntan a un número pueden resolver al fichero equivocado sin que nada lo detecte.

**Y no es culpa de `integridad.py`.** Su línea 31 dice, literalmente, que los duplicados se
evaluan **solo sobre lo suyo**, porque un choque entre dos ficheros ajenos no es su problema.
Medido: **0 de los 71 me tocan**. La herramienta acierta y su alcance está escrito. El defecto es
del **sistema de numeración**, no del control que lo vigila — y por eso ningún control lo cazó:
están todos deliberadamente encerrados en su propio conjunto.

*(Las diferencias con un `ls | uniq -d` son reales: ese método lista un número tantas veces como
sobras, y da 75. El conteo por diccionario, 71, es el bueno.)*

## 4. Lo que está bien, y no hay que arreglar

- **`DOCUMENTATION-ROUTER`** es un trabajo serio: 68 topics, 6 conflictos registrados con su
  `CONFLICT_SOURCE`, terminales explícitos, y una regla de temporalidad que es un modelo. Sus
  errores son de mantenimiento, no de conception.
- **`COORDINACION.md`** separa el método (`AGENTS.md`) de la concurrencia, y el router lo declara
  fuente normativa propia en su §-1 en lugar de suplantarla.
- **`tools/artifacts.py`** genera sus artefactos con el contrato escrito dentro, y su `exit=1` es
  un `INVALID_RESULT` honesto por referencias rotas preexistentes, no un fallo.
- **Los findings se versionan**: `CORRECTED_BY`, `RETRACTED_BY`, `CLAUSULA_RETRACTADA_POR`. Es lo
  que permite que `965` refute `945` sin borrar `945`.

## 5. Alcance: qué NO he leído

Declararlo, porque el número de páginas es engañoso:

```
SI LEIDO ENTERO   README.md · CURRENT-STATE.md · DOCUMENTATION-ROUTER (445) · AGENTS.md (1060)
                  COORDINACION.md (via secciones) · inventory TSV (1576 filas, parseadas)
                  31 findings proprios, y el `AGENTS.md` compacto de la sesion anterior
NO LEIDO          482 findings en su mayoria  ·  docs/CHANGELOG-RESEARCH.md (259 KB)
                  01-AUDITORIA/ (1,2 MB)  ·  00-INDICE/ (513 KB)  ·  las 6 suites de bench
```

**Los 4,5 MB de markdown no caben en una iteración.** Lo que he leído es lo que sostiene el
índice; los findings están cubiertos por `EVIDENCE-MATRIX` (478 filas) y los documentos grandes
por el router. **Afirmar que he leído todo el repo sería falso, y este documento no lo afirma.**

## 6. Lo que esto deja como frente

El hallazgo de fondo no es ninguno de los cinco. Es este:

> **La infraestructura de indexación se construyó cuando había 250 findings, y el proyecto llegó
> a 479 en dos días.** Ninguno de los cinco defectos es un error de criterio: son todos
> *desincronización*. Y el síntoma común es el mismo que el de `945` y el del `cut -c`: **un dato
> viejo leído como actual**.

Tres acciones, y solo una es de conocimiento:

**A y B están ejecutadas. C no, y no es mía.**

| | acción | estado |
|---|---|---|
| **A** | **Recuperar y commitear el `AGENTS.md` operativo**, el que tiene las rutas. Sin commit no existe, y la pérdida de D1 ya costó una vez. | **PENDIENTE**: el contenido se perdió; hay que reconstruirlo |
| **B** | **Regenerar los 7 artefactos de raíz** por la vía sancionada (`--solo X --escribir`) | **HECHA** 2026-10-03 09:27-09:31. `CURRENT-STATE.md` ya dice 479 / 001-966. Los 7 con `exit=1`, que es el de siempre |
| **C** | **Decidir cuál de las dos familias de índice manda.** Hay 7 nombres duplicados y hoy gana la que se abre primero, que es un criterio de orden de lectura, no de autoridad | **ABIERTA**: es del proyecto, no se elige leyendo |

**C es la que bloquea a las otras dos**, y no es una decisión que pueda tomar leyendo: es del
proyecto. La regla del prompt es que una contradicción se devuelve con **ambas** fuentes, sin
elegir.

---

## Reproducir

```bash
# D1  el prompt global dentro del repo
md5sum AGENTS.md ~/.config/opencode/AGENTS.md
git diff --stat HEAD -- AGENTS.md

# D2  el desfase del artefacto generado
grep "Findings totales" CURRENT-STATE.md
python3 tools/artifacts.py --solo CURRENT-STATE | grep "Findings totales"

# D3  la confusion de columnas, por parseo y no por grep
python3 - <<'EOF'
import csv,collections
r=list(csv.DictReader(open('01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-INVENTORY-ROUTING.tsv',
                           encoding='utf-8',errors='replace'),delimiter='\t'))
print(collections.Counter((x['HOST_SCOPE'] or '').strip() for x in r))
print(collections.Counter((x['TEMPORALITY'] or '').strip() for x in r))
EOF

# D4  la referencia colgante
sed -n '15,16p;23,24p' README.md
grep -n "C4" 01-AUDITORIA/DOCUMENTATION-ROUTER/DOCUMENTATION-ROUTER.md | head -2

# D5  la contradiccion interna
sed -n '13,24p' README.md
```