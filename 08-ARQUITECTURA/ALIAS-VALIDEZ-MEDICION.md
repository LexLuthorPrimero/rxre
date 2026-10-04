# ALIAS-VALIDEZ-MEDICION — ¿están multiplicados los recuentos del proyecto?

```
NODE            ALIAS-VALIDEZ-MEDICION
AGENCIA         RX550-INVESTIGACION-WORKSPACES/01-COORDINACION
CLASS           auditoria-de-instrumentacion · SOLO LECTURA
WORK_CLASS      validacion-de-recuentos
GPU             INTACTA · no se ha tocado
ESCRITURAS      1 fichero nuevo, este. Ningun otro cambio en el arbol.
MEDICION        2026-10-04T11:43:06Z · kernel 7.1.3-200.nobara.fc44.x86_64
HERRAMIENTAS     os.lstat / os.walk / /proc/self/mountinfo · python3, sin grep
```

## 0. Veredicto en una línea

**La multiplicación por alias es REAL y está MEDIDA (×6), pero NO toca a las
herramientas que produceron los números publicados, porque ninguna de ellas
mira el contenedor de alias.** El daño no estaba donde se sospechaba: no es un
`×7` silencioso, es un `×6` que solo se activa si alguien apunta una
herramienta a `RX550-INVESTIGACION-WORKSPACES`, y un `0` silencioso si se
apunta a un subárbol que bajo ese contenedor no existe.

**Y hay una corrección de partida: el enunciado affirmaba «no hay montajes
separados». Eso es FALSO, y la herramienta que debía saberlo ya lo sabía.**

---

---

## 0-bis. `DRIFT_DETECTED` — dos ficheros moveidos mientras medía

Disciplina: no se afirma nada sin medida, y la medida incluye su hash. Al
verificar las citas `fichero:línea` contra el contenido actual, **dos de los
ficheros que cito habían cambiado** respecto a cuando los leí. No los escribí yo
(`git status` los muestra ` M`, de otra sesión).

```
MEDIDO  tools/check_num_unico.py
        al inventariarlo:  1359 lineas
        al citar lineas :  1431 lineas   (sha16 actual 7ef0a10d27d9c1a3)
        DRIFT -> las citas :363-365 / :616 / :1356 quedaron CADUCAS
        CORREGIDAS a las de la version vigente:
          :385-386  def proyecto()  = dirname(dirname(abspath(__file__)))
          :637      for dp, dn, fn in os.walk(raiz)
          :1422     r = medir(proyecto(), a.alcance, a.max_ficheros)

MEDIDO  08-ARQUITECTURA/tools/toalaudit.py
        verificado tres veces en 3 s: 915 / 915 / 915 lineas, sha16 9f3b6a73aa35e779
        leído por otro script 30 s despues: 727 lineas, sha16 a98162c22675aa59
        DRIFT -> el fichero esta SIENDO EDITADO en este momento
        ESTADO: las citas :70 / :234 / :446 / :479 / :653 valen para
                sha16 9f3b6a73aa35e779 (915 lineas). Para otra version, estan
                sin verificar: NO_VERIFICABLE, no "confirmado".
```

**Qué no cambia por esto:** el contenido medido —raíz única, `os.walk`, clave por
`realpath`— se reverificó sobre la versión vigente y sigue siendo cierto. Lo que
cambia es la **numeración de línea**, y por eso todas las citas de este
documento van acompañadas de su hash en §10: una cita sin hash no es
reproducible, y esta auditoría acaba de demostrar por qué.

**Y una corroboración afortunada:** el `sha16` de
`08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md` que medí es
`36cf982390574084`, que es exactamente el prefijo del `sha256`
`36cf982390574084c3d5…` que me dieron por adelantado. El dato de partida era
correcto y queda verificado de forma independiente.


## 1. Corrección al hecho de partida: sí son montajes

El enunciado dice *«No hay montajes separados (`df` da el mismo `/dev/sdb3` a
los dos)»*. `df` coincide en dispositivo **y el montaje sigue existiendo**: un
`bind mount` comparte `st_dev` con su origen por definición. La fuente
correcta es `/proc/self/mountinfo`, y ahí está escrito:

```
MEDIDO  /proc/self/mountinfo, 33 lineas con "RX550" en el punto de montaje:
  103  44 8:19 /home/lucas/Escritorio/RX550-INVESTIGACION  .../WORKSPACES/01-COORDINACION
  493  44 8:19 /home/lucas/Escritorio/RX550-INVESTIGACION  .../WORKSPACES/02-SOFTWARE-GPU
  645  44 8:19 /home/lucas/Escritorio/RX550-INVESTIGACION  .../WORKSPACES/03-GPU-SEMANTICS
  720  44 8:19 /home/lucas/Escritorio/RX550-INVESTIGACION  .../WORKSPACES/04-RUNTIME-PROBING
  810  44 8:19 /home/lucas/Escritorio/RX550-INVESTIGACION  .../WORKSPACES/05-TOOLING-AUTOMATION
  915  44 8:19 /home/lucas/Escritorio/RX550-INVESTIGACION  .../WORKSPACES/06-DRIVER-C-ASM-PERFORMANCE
  (+ 27 montajes de FICHERO, todos con destino .../AGENTS.md)
```

El **campo 4** (`root`) de esas líneas es la raíz del árbol montado — la prueba
de que el origen es el proyecto principal, no una copia. El mecanismo es
`mount --bind`, no symlinks ni hard links de directorio:

- **MEDIDO** 0 symlinks en las 6 entradas alias (`.store`, `bin`, `systemd` y
  los 6 directorios son entradas normales de directorio).
- **MEDIDO** los 99 symlinks que hay dentro del proyecto están **todos** en
  `RESEARCH/kernelbuild/linux-7.1.3/` (árbol de kernel upstream: `include/`,
  `scripts/`, `arch/*`). Ninguno participate del mecanismo de alias.
- **MEDIDO** `git worktree list` → 1 sola entrada. No son worktrees.
- **MEDIDO** `tools/mountcheck.py:19-22` ya declaraba `B STACKING … MEDIDO: 33
  montajes RX550, con 6 capas sobre el mismo AGENTS.md`. El 33 coincide con lo
  que yo cuento. **El mecanismo ya era un hallazgo del proyecto; lo que no
  existía era la consecuencia sobre los recuentos.**

### 1-bis. Un hecho adicional que nadie había medido: `AGENTS.md` está apilado DENTRO del proyecto

```
MEDIDO  /proc/self/mountinfo, montajes cuyo PUNTO DE MONTAJE esta dentro de MAIN: 6
  187 557 663 739 830 936 ->  destino = /home/lucas/.../RX550-INVESTIGACION/AGENTS.md
        origen  = /home/lucas/Escritorio/RX550-AGENT-DEFINITIONS/<0N>/AGENTS.md
MEDIDO  os.lstat(MAIN/AGENTS.md).st_ino = 2008260
      = os.lstat(RX550-AGENT-DEFINITIONS/01-COORDINACION/AGENTS.md).st_ino
```

`MAIN/AGENTS.md` **no es un fichero del proyecto**: es un overlay de un árbol
vecino, con 6 capas apiladas sobre el mismo punto de montaje. Cualquier
herramienta que hashee o cuente ficheros dentro del proyecto cuenta un objeto
que vive fuera. Las 7 vistas del árbol ven el mismo inodo (2008260), así que
esto **no** se multiplica — pero significa que `MAIN` no es un árbol
autocontenido y que un `sha256sum` recursivo sobre él incluye materia externa.

---

## 2. El mapa de alias, completo y medido

Criterio de alias: **igualdad de inodo** (`os.lstat().st_ino`), que es lo único
que prueba identidad. Recorrido acotado a `MAIN` profundidad 2 y `WORKSPACES`
profundidad 3 — suficiente y declarado, porque los alias son todos hermanos de
primer nivel.

| # | Subárbol | `st_ino` | Rutas distintas al mismo inodo |
|---|----------|---------:|------------------------------:|
| a | raíz del proyecto | `28966954` | **7** |
| b | `08-ARQUITECTURA/` | `7232747` | **7** |
| c | `06-INGENIERIA-INVERSA/findings/` | `7232740` | **7** |
| d | `tools/` | `6423689` | **7** |
| e | `04-IMPLEMENTACION/rx550-driver/` | `7346839` | **7** |

Las 7 rutas de (a) son `RX550-INVESTIGACION` más `WORKSPACES/{01-COORDINACION,
02-SOFTWARE-GPU, 03-GPU-SEMANTICS, 04-RUNTIME-PROBING, 05-TOOLING-AUTOMATION,
06-DRIVER-C-ASM-PERFORMANCE}`. Para (b)–(e) son las 6 rutas `WS/<alias>/<sub>`
más la canónica `RX550-INVESTIGACION/<sub>`.

Entradas propias de `WORKSPACES` que **no** son alias (19 ficheros, 5
directorios): `.store/agents/AGENT-0{1..6}.md`, `.store/occlude-empty/`,
`bin/` (6 scripts), `systemd/` (1 unidad), `ARCHITECTURE.md`, `ROLES.md`,
`VALIDATION.md`, `README.md`, `FINDING-ROLLBACK-NOOP.md`, y el fichero
`04-RUNTIME-PROBIGACION-PLACEHOLDER` (con `G` de más).

### 2-bis. La identidad aritmética que prueba que son copias exactas

Si `WORKSPACES` fuese 6 copias exactas más sus propias entradas, los totales
casarían de forma exacta. Casan:

```
MEDIDO  MAIN :  8044 dirs, 117408 ficheros
MEDIDO  WS   : 48270 dirs, 704467 ficheros

  6 x 117408 + 19 = 704467   IDENTICO
  6 x   8044 +  6 = 48270   IDENTICO
```

(los +19 y +6 son las entradas propias de `WORKSPACES`, medidas una a una).
Coincide cero veces hasta el último fichero: no hay un solo fichero compartido
entre las seis vistas. **Copia exacta, seis veces.**

### 2-bis-bis. LA MEDIDA QUE CAMBIA EL DIAGNÓSTICO

`os.walk` **no ve los alias desde dentro del proyecto**, porque los alias viven
en un directorio *hermano*, no dentro:

```
MEDIDO  os.walk(MAIN) -> 8044 dirs, 117407 ficheros, entradas-alias encontradas: 0
MEDIDO  os.walk(WS)   -> 48270 dirs, 704467 ficheros
MEDIDO  os.walk(~/Escritorio) -> 59299 dirs, 858707 ficheros, 0 errores de recorrido
```

Y con un fichero sonda (`tools/check_num_unico.py`, `ino=6422804`) como
contador de ocurrencias:

| Raíz del recorrido | veces que se alcanza el sonda |
|--------------------|-----------------------------:|
| `RX550-INVESTIGACION` | **1** |
| `WS/01-COORDINACION` (y las otras 5) | **1** cada una |
| `WS` (el contenedor) | **6** |
| `~/Escritorio` | **7** |

**Ésta es la tabla que decide todo lo demás:** cualquier raíz única —canónica o
de alias— ve el proyecto **una** vez. Sólo `WS` lo ve 6 veces y `~/Escritorio`
7. La Nota sobre el coste: `os.walk(MAIN)` completo tarda **0,3 s**. El miedo a
agotar el tiempo con los ~110 000 ficheros de `RESEARCH/` era infundado; el
recorrido no se recortó porque no hizo falta. **Corte declarado: ninguno.**

> **Autorretracción obligatoria.** Mi primera medición de `~/Escritorio` dio
> 63 directorios y 0 ocurrencias del sonda. Era **falla mía**, en el predicado
> de poda que escribí, no un hecho del árbol. La repetí con `onerror` collecting
> y sin poda: 59 299 directorios, 7 ocurrencias, 0 errores. **El número
> descartado era el que casi publico.** Se registra porque es exactamente el
> modo de fallo que esta auditoría audita: `os.walk` se traga los errores en
> silencio si no le pasas `onerror`.

---

## 3. Auditoría de las herramientas que cuentan

**Alcance:** 194 ficheros `.py` en `tools/`, `revkit/` y
`08-ARQUITECTURA/tools/`. 138 recorren el árbol (`os.walk` / `rglob` /
`scandir` / `listdir` / `glob`). Los 56 restantes no recorren y quedan fuera.
Los 138 se clasificaron por **origen de la raíz**, leyendo el código; los de
raíz ambigua se leyeron uno a uno.

### 3.0 El discriminante, y por qué `realpath` no sirve

| Primitive | ¿Deduplica un bind mount? | MEDIDO |
|---|---|---|
| `os.path.realpath` / `Path.resolve()` | **NO** | ver abajo |
| `os.path.samefile` | **SÍ** | `samefile(canonico, alias) = True` |
| `st_ino` + conjunto de vistos | **SÍ** | base de la puerta de §5 |
| `followlinks=False` de `os.walk` | **NO** (aquí no hay symlinks) | 0 symlinks en los alias |
| `git ls-files` / `ls-tree` | **SÍ**, por construcción | 1 solo `.git`, ver §3.4 |

```
MEDIDO  os.path.realpath(".../RX550-INVESTIGACION/tools/check_num_unico.py")
      = /home/lucas/Escritorio/RX550-INVESTIGACION/tools/check_num_unico.py
MEDIDO  os.path.realpath(".../WS/05-TOOLING-AUTOMATION/tools/check_num_unico.py")
      = /home/lucas/Escritorio/RX550-INVESTIGACION-WORKSPACES/05-TOOLING-AUTOMATION/tools/check_num_unico.py
MEDIDO  los dos st_ino = 6422804  ·  os.path.samefile = True
```

Dos cadenas **distintas** para el mismo inodo. Un bind mount es transparente a la
resolución de rutas: el núcleo atraviesa la tabla de montajes sin reescribir la
ruta. Por eso `realpath` es peor que inútil como criterio — **parece** una
deduplicación y no lo es.

### 3.1 Las nueve herramientas nombradas, una a una

| Herramienta | Raíz (evidencia) | Recorre | ¿Puede ver >1 ruta? | Veredicto |
|---|---|---|---|---|
| `tools/check_num_unico.py` | `check_num_unico.py:385-386` `proyecto()` = `dirname(dirname(abspath(__file__)))`; usada en `:1422` | `:637 os.walk(raiz)` (árbol entero) | No: raíz única. **MEDIDO**: MAIN=2222, alias=2222, alias=2222 (idéntico bit a bit) | **LIMPIA** |
| `tools/artifacts.py` | `__file__`-derivada (8 sitios de recorrido: `:105,185,233,286,441,574,874,1395`) | árbol y subárboles | No: raíz única | **LIMPIA** |
| `tools/dupenum.py` | `__file__`-derivada; `:150 os.walk(raiz)` | árbol | No: raíz única | **LIMPIA** |
| `tools/git_sano.py` | `:90 base = <repo>/.git/objects`, repo = `__file__`-derivado | sólo el almacén de objetos de git | No, y **estructuralmente inmune**: hay **1 solo `.git`** en todo el proyecto (`ino=28970904`), y el almacén de objetos no tiene copia por alias | **LIMPIA** |
| `tools/reservas_gate.py` | `:99 RAIZ = dirname(dirname(abspath(__file__)))` | `:183,213` `listdir` de subárboles del proyecto | No: raíz única | **LIMPIA** |
| `revkit/cn8.py` | `:33 AQUI = dirname(abspath(__file__))` | `:502,537` `listdir` de un directorio de docs | No: raíz única | **LIMPIA** |
| `revkit/huerfanos.py` | `:124 raiz = dirname(dirname(abspath(__file__)))`; `:175 --raiz` | `:145,218 os.walk` de 4 corpus | No por defecto. **MEDIDO** con raíz `WS`: las 4 rutas no existen → 0 ficheros leídos | **LIMPIA** (+ falla a cero, §4.2) |
| `08-ARQUITECTURA/tools/reenvio_gate.py` | `:101 HERE = dirname(abspath(__file__))` | `:372 listdir` de `findings/` | No: raíz única | **LIMPIA** |
| `08-ARQUITECTURA/tools/reenvio_freeze.py` | `:141 HERE = dirname(abspath(__file__))` | **ninguno** (`walk_sites=0`) | n/a | **LIMPIA** (no recorre) |

**Ninguna de las nueve está contaminada en su raíz por defecto.** Las nueve
resisten. Éste es el hallazgo central y es un resultado **negativo medido**, no
una suposición.

### 3.2 El generador de `08-ARQUITECTURA/RE-INDEX.md`

```
MEDIDO  RE-INDEX.md existe: ino=7251083, 111681 B, 1934 lineas, RASTREADO por git
MEDIDO  tools/ revkit/ 08-ARQUITECTURA/tools/ : 0 ocurrencias de "RE-INDEX" que la ESCRIBAN
        (las 6 menciones lo LEEN: tools/rx550/report.py:238, o lo citan en prosa)
MEDIDO  08-ARQUITECTURA/tools/findings_index.py:655 escribe REENVIO_MD, no RE-INDEX.md
```

**No existe generador de `RE-INDEX.md` en el árbol de herramientas.** Es un
documento curado a mano y versionado. Por tanto sus cifras (133 sesiones, 165
accesos, 53 de 496, 481 de 496, 92 ficheros…) **no son NO_VERIFICABLES por
alias** —no se produceron recorriendo el árbol— pero **tampoco son
reproducibles**, y eso es un agujero distinto. Se marca
`NO_VERIFICABLE` por origen, no `CONTAMINADA`.

### 3.3 Las seis que sí pueden contaminarse

| Herramienta | Vector | Evidencia | Estado |
|---|---|---|---|
| `tools/rx550/alcance.py` | `RX550_ROOT` por entorno | `:4 RX550_ROOT = os.environ.get("RX550_ROOT", ".../RX550-INVESTIGACION")` | **CONTAMINABLE** |
| `tools/rx550/contract.py` | ídem | `:4` (además `RX550_ARQ` `:5`) | **CONTAMINABLE** |
| `tools/rx550/crosscheck.py` | ídem | `:32` | **CONTAMINABLE** |
| `tools/rx550/funcspan.py` | ídem | `:4-5` | **CONTAMINABLE** |
| `tools/rx550/mandato.py` | ídem | `:4-5`, `:504` (`RX550_SANDBOX_ROOT`) | **CONTAMINABLE** |
| `tools/rx550/report.py` | ídem | `:33` | **CONTAMINABLE** |

Con `RX550_ROOT=/…/RX550-INVESTIGACION-WORKSPACES` estas seis caminan el árbol
6 veces. **No lo he ejecutado**: cinco de las seis escriben en el árbol, y este
nodo no escribe. El factor 6 de §4.1 está medido con una herramienta que sí
produce el mismo tipo de cifra; el número exacto para estas seis es
**`NOT_MEASURED`**, y no se estima.

### 3.4 Las que dependen del directorio de trabajo

| Herramienta | Dependencia | Evidencia |
|---|---|---|
| `revkit/sello.py` | `os.getcwd()` | `:1` bucket `ARGV,CWD,SELF_ROOT` |
| `08-ARQUITECTURA/tools/bench.py` | `os.getcwd()` | idem |
| `tools/evidence_search.py` | `os.getcwd()` | `:15` el propio documen depende «del cwd» |
| `tools/ipsolve.py` | `os.getcwd()` | `:1108` imprime rutas relativas al cwd |
| `08-ARQUITECTURA/tools/h1_stale.py` | **ruta relativa** | `:84 FINDINGS = os.path.join('06-INGENIERIA-INVERSA','findings')` |

Las cinco son sensibles al cwd. Con un cwd de alias único siguen viendo el
proyecto una vez (limpio); con cwd = `WS` o `~/Escritorio` verían 6 o 7 veces.
Clasificadas **`CONTAMINABLE` por cwd**, que es un vector que ninguna puerta
actual cubre.

### 3.5 Inmunidades estructurales (por qué ciertas cifras no pueden moverse)

```
MEDIDO  1 solo directorio .git en todo el proyecto: MAIN/.git ino=28970904
        WS/.git no existe; WS/05-TOOLING-AUTOMATION/.git SI existe (es el mismo inodo)
MEDIDO  revkit/integro.py:172   git -C raiz ls-files      -> si raiz=WS, NO_REPO: falla ruidoso
MEDIDO  tools/docscan.py:355,368  git -C repo_root ls-files / log -> idem
MEDIDO  08-ARQUITECTURA/tools/findings_index.py:279  git ls-tree HEAD -> rutas, no inodos
```

Todo lo que cuenta **contra el índice de git** es inmune por construcción: el
índice de git es un conjunto de rutas canónicas, y hay una sola copia de él.
`integro.py` es además el que mejor se protege: su oráculo (git) **falla en voz
alta** si le dan una raíz mala.

### 3.6 Una deduplicación que no deduplica

```
MEDIDO  08-ARQUITECTURA/tools/toolaudit.py:234  clave = os.path.realpath(p)
MEDIDO  08-ARQUITECTURA/tools/toolaudit.py:446,479,653  {os.path.realpath(i["path"]) …}
```

`toalaudit.py` deduplica por `realpath`, que §3.0 demuestra ciego al bind mount.
**Parece protegido y no lo está.** No lo marco `CONTAMINADA` porque su raíz es
única (`toolaudit.py:70 PROJECT = …/RX550-INVESTIGACION`), pero si alguna vez se
le pasa `--raiz WS` su deduplicación no lo salvará y **no dará ninguna señal de
que no funcionó**. Ése es el peor de los dos modos: no multiplica y no avisa.

### 3.7 Inventario completo por firma de raíz

Los 138 que recorren, agrupados por cómo obtienen la raíz:

| Firma | N | Archivos |
|---|--:|---------|
| `__file__`-derivada (raíz única) | 57 | `artifacts.py`, `check_num_unico.py`, `dupenum.py`, `reservas_gate.py`, `huerfanos.py`, `cn8.py`, `reenvio_gate.py`, `reenvio_freeze.py`, `findings_index.py`, `smc_copy_scope.py`, `smc_layout.py`, `lint.py`, `claims.py`, `govcheck.py`, `drift`… (los 57 están en §3.1 y en el detalle de abajo) |
| sin raíz detectable en módulo (parámetro de función) | 33 | `asic_resolver.py`, `cap_census.py`, `citas.py`, `citations.py`, `claim.py`, `contradict.py`, `docscan.py`, `git_sano.py`, `round.py`, `snapshot.py`, `struct_layout.py`, `xref.py`, `regs.py`, `verdiff.py`, `runtime_obs.py`, `binfacts.py`… — **leídos uno a uno**: todos reciben la raíz por parámetro y todosolithalvienen de una raíz única |
| literal `…/RX550-INVESTIGACION` | 16 | `causal_map.py`, `contract_exec.py`, `corpus_guard.py`, `doclint.py`, `regdb.py`, `scopeguard.py`, `smumsg.py`, `toalaudit.py`, `toolaudit.py`, `btfq/sweep.py`… |
| literal MAIN + `__file__` | 8 | `causal.py`, `citecheck.py`, `hdrmap.py`, `xref.py` (08-ARQ), `correlate.py`, `scan.py` |
| `argv` + `__file__` | 6 | `huerfanos.py`, `nextnum.py`, `pipeline.py`, `flags_inventory.py`, `citas_prosa_census.py`, `dires.py` |
| `argv` solo | 5 | `msg_census.py`, `trace_path.py`, `cidx.py`, `integro.py`, `rx550/regctx.py` |
| **`RX550_ROOT` por entorno** | **6** | §3.3 |
| **`os.getcwd()`** | **5** | §3.4 |
| `WS` como literal | 2 | `envcheck.py:446`, `mountcheck.py:343` — **ninguna de las dos cuenta ficheros del proyecto**: `mountcheck.py:343` construye la lista de workspaces **para contar montajes**, y `envcheck.py:161` usa `raices = ["/home/lucas/Escritorio/RX550-INVESTIGACION"]` (la canónica) |

**Cero herramientas|USO por defecto.**

---

## 4. Los números: cuánto se multiplica, medido sin reescribir nada

Regla que me impuse y que se cumple: **si no se puede medir, no se estima.**

### 4.1 Clase A — raíz = proyecto entero: SE MULTIPLICA. Medido ×6,07.

`tools/check_num_unico.py`, función `citas_por_numero` (la que produjo las
`2152`), llamada a través de su propia API con la misma `por_num` y raíz
distinta:

| `raiz` | `citas_por_numero_a_duplicado` | `numeros_duplicados_citados` | ficheros leídos | tiempo |
|---|---:|---:|---:|---:|
| `RX550-INVESTIGACION` (canónica) | **2222** | 74 | 2520 | 1,8 s |
| `WS/01-COORDINACION` | **2222** | 74 | 2520 | 1,8 s |
| `WS/06-DRIVER-C-ASM-PERFORMANCE` | **2222** | 74 | 2520 | 2,1 s |
| `WS` (contenedor) | **13482** | 74 | 15132 | 10,5 s |

```
MEDIDO  factor = 13482 / 2222 = 6,065
MEDIDO  6 x 2222 = 13332;  el exceso de 150 son las citas de los 19 ficheros
        propios de WORKSPACES (11 .md legibles).  O sea: el ×6 es exacto y el
        resto es contenido real, no duplicado.
```

Las dos filas de alias son **idénticas bit a bit** a la canónica. Eso es la
prueba directa de que **invocar una herramienta por una ruta de alias no
contamina nada**.

### 4.2 Clase B — raíz = subárbol del proyecto: NO se multiplica, **se anula**. Medido 0.

`revkit/huerfanos.py`, `_recorre` con las mismas 4 rutas de corpus Spellingbajo
cada base:

| base | raíces existentes | ficheros leídos | nombres definidos | nombres usados |
|---|--:|--:|--:|--:|
| `RX550-INVESTIGACION` | 4/4 | **1219** | 2304 | 2651 |
| `WS` | **0/4** | **0** | **0** | **0** |

Bajo el contenedor de alias, `WS/04-IMPLEMENTACION/...` **no existe**, y
`huerfanos.py:143-144` hace `if not os.path.isdir(raiz): continue` — se salta
la raíz en silencio. El resultado es **«cero símbolos huérfanos»**, que es un
veredicto falso y peligroso. La propia herramienta lo anticipa en su
docstring (`huerfanos.py:182-183`): *«recorrido 0 ficheros devolvía "NINGUNO",
que es el peor resultado posible: un corpus no recorrido se lee como un corpus
completo»*.

**El modo de fallo del alias no es multiplicar. Son dos: multiplicar (raíz del
proyecto) y anular en silencio (subárbol).** El segundo es peor, porque el
primero al menos da un número imposible.

### 4.3 Clase C — el mismo defecto, en un tercer modo: `None` → «sin problemas»

```
MEDIDO  tools/docscan.py measure_findings(MAIN) -> {"total": 547, "untracked": 0, "dupes": […74…], …}
MEDIDO  tools/docscan.py measure_findings(WS)   -> None
MEDIDO  tools/docscan.py:398-399  if not m: return []      <- None se traduce en «cero problemas»
```

`measure_findings` devuelve `None` si el directorio de hallazgos no existe
(`docscan.py:379-380`), y `check_findings_unindexed` convierte ese `None` en
lista vacía (`:398-399`). Apuntar `docscan` al contenedor de alias no da error:
**da «ningún hallazgo sin indexar»**. Es el mismo género que el defecto ya
registrado como `1043-la-puerta-de-cabeceras-duplicadas-compara-texto-y-no-identidad.md`
— una comprobación que no puede distinguir «no hay» de «no miró».

### 4.4 Clase D — conjuntos: inmunes por construcción

```
MEDIDO  tools/docscan.py _basename_index(MAIN) -> |set| = 85034
MEDIDO  tools/docscan.py _basename_index(WS)   -> |set| = 85051     (Diferencia: +17)
```

Un `set` de nombres no se multiplica. Los +17 son los 19 ficheros propios de
`WORKSPACES` menos 2 cuyos basenames ya existían. **Mi script imprimía
literalmente la palabra «identicos» como cadena fija, sin derivarla de la
comparación: la medición los desmintió y esa etiqueta era mía, no del dato.
Queda aquí la cifra real, 85034 vs 85051, no la que yo anticipated.**

Regla general que se desprende, y que sí es una clasificación y no un
número: **`set`/`dict` de nombres → inmune. `Counter`/lista/`+= 1` → se
multiplica.**

### 4.5 La generalización, que no necesita ninguna herramienta

El ×6 no es una property de `check_num_unico`: es una property de la raíz. Y
queda probada sin ejecutar nada (§2-bis): `WS` contiene exactamente 6 copias
íntegras y 19 ficheros propios, y la puerta de §5 cuenta **125 464 inodos
alcanzados por más de una ruta** bajo `WS`. Cualquier contador que camine el
árbol entero desde `WS` los cuenta seis veces. Punto.

### 4.6 Nota de alcance: el corpus estaba creciendo mientras medía

```
MEDIDO  2026-10-04 ~11:2xZ  MAIN = 117408 ficheros
MEDIDO  2026-10-04 ~11:3xZ  MAIN = 117419 ficheros
MEDIDO  2026-10-04 11:43:06Z MAIN = 117426 ficheros
```

Otros agentes están escribiendo. Las cifras absolutas de este documento son de
un instante; **los factores (6, 6,065, 6×2222+150) son ratios dentro de la misma
medida y no se ven afectados**. Coherente con §4.1: mi corrida da 2222 donde el
documento publicado dice 2152/2230, y esa diferencia es deriva entre corridas
ya registrada en `CITAS-POR-NUMERO-DECLARACION.md:8,104`, no efecto de alias.

---

## 5. La puerta

**Construida, ejecutada y validada.** Ubicación real:

```
/tmp/opencode/aliasgate/aliasgate.py     (fuera del arbol: este nodo solo puede
                                          escribir 08-ARQUITECTURA/ALIAS-VALIDEZ-MEDICION.md)
```

**No está instalada en `tools/`** porque mi alcance es un único fichero. Eso es
una decisión de alcance, no una imposibilidad: instalar esto es mechanically
trivial y queda como acción de otro nodo.

### Qué tiene que poder fallar

`PASS` ⇔ **ningún inodo del árbol se alcanza por más de una ruta**. `FAIL` si
hay alguno, con los primeros cinco y sus rutas. `ERROR_DE_OBSERVABILIDAD`
(`rc=2`) si el recorrido falló — porque *un recorrido que no pudo hacerse no es
un recorrido limpio*, y `exit 0 ≠ resultado válido* (`AGENTS.md` §26).

### Control negativo (lo que la hace una puerta y no un script)

Tres controles, todos ejecutados, todos `OK`:

1. **Detección real sin privilegios.** Se construye un árbol temporal con un
   **hard link** a un fichero: misma unidad física, dos rutas. El detector
   **FALLA** como debe. Un hard link es la misma condición lógica que un bind
   mount y se puede construir sin `sudo`.
2. **No falso-positivo.** El mismo detector sobre la rama `a/` (una sola rama)
   **PASA**.
3. **`realpath` no sirve, demostrado dentro de la puerta.** El mismo par de
   ficheros da **dos** cadenas `realpath` distintas para **un** inodo. El
   criterio queda fijado en inodo, y el por qué queda escrito en el código.
4. **Control de observabilidad.** Auditar una raíz inexistente devuelve `rc=2`,
   nunca `PASS`.

```
MEDIDO  python3 aliasgate.py --selftest                -> RESULT: PASS  (rc=0)
MEDIDO  aliasgate.py .../RX550-INVESTIGACION          -> 117419 ficheros, 125465 inodos
                                                          unicos, 0 con >1 ruta   rc=0  PASS
MEDIDO  aliasgate.py .../WS/05-TOOLING-AUTOMATION     -> 117419 ficheros, 125465 inodos
                                                          unicos, 0 con >1 ruta   rc=0  PASS
MEDIDO  aliasgate.py .../RX550-INVESTIGACION-WORKSPACES
        704533 ficheros, 125495 inodos unicos, 125464 con >1 ruta   rc=1  FAIL
        ino=28966954 x6  ->  WS/{01..06}-*
```

El par `PASS, PASS, FAIL` sobre tres raíces del mismo árbol **es** la prueba de
que la puerta discrimina. Si devolviera `PASS` sobre `WS`, la puerta sería
inválida y no serviría.

*(El fuente completo va en §7 de este documento.)*

---

## 6. Veredicto de validez sobre los recuentos ya publicados

**No reescribo ningún número. Los marco.**

### RESISTEN — la herramienta produce el número desde una raíz única, y está medido que un alias da el mismo resultado

| Número | Dónde | Herramienta | Por qué resiste |
|---|---|---|---|
| `2152` / `2230` citas por número sobre duplicado | `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md:82,104` | `tools/check_num_unico.py` (A3, `citas_por_numero`) | Raíz `__file__`-derivada única (`check_num_unico.py:385-386,1422`). **MEDIDO**: MAIN = 2222 = alias `01` = alias `06`, idéntico. La deriva 2230↔2152 que el propio documento registra (`:8`) es de otra causa |
| `45,7 % [26,0 ; 65,4]` | `CITAS-POR-NUMERO-DECLARACION.md:85` | el mismo, vía A1 | Derivada de la misma población. Resiste **como cifra relativa**; el documento ya dice (`:94-95`) que el margen es de 40 puntos y que usarla como puntual sería mentir |
| `74` números duplicados | `CITAS-POR-NUMERO-DECLARACION.md`, citado en `findings/1044:129` | `check_num_unico.py fs_indice()` | Dict sobre nombres de fichero en `findings/`, raíz única. **MEDIDO en mi corrida: `dups=74`** — coincide |
| `132` adjudicaciones | `findings/1044:124` | artefacto verificado por hash | El estado no depende de ningún recorrido |
| `201` filas de herramientas | `findings/1044:129` | `tools/mountcheck.py:130-136` (`RE_FILA`) | Parsea **una tabla markdown**, un solo fichero. No hay multiplicación posible. *No verifico si 201 es el número vigente: eso es freshness, no alias* |

### NO RESISTEN — marcados, no reescritos

| Número | Por qué |
|---|---|
| `16 703` nombres de registro | **NO_VERIFICABLE.** Aparece una sola vez en todo el árbol (`findings/1044:128`) y **no he identificado la herramienta que lo produce**. Sin productor identificado no hay veredicto de validez que emitir. *Abierto.* |
| Las cifras de `08-ARQUITECTURA/RE-INDEX.md` (133 sesiones, 165 accesos, 53/496, 481/496, 92 ficheros) | **NO_VERIFICABLE por origen.** No hay generador (§3.2): documento curado a mano. No pueden estar *multiplicados por alias* —no hubo recorrido— pero tampoco son reproducibles. `NO_VERIFICABLE` no es `CONTAMINADO`: es un agujero distinto |
| Cualquier cifra producida con `RX550_ROOT` / cwd / `--raiz` apuntando a `WS` o `~/Escritorio` | **CONTAMINABLE.** Vector real y medido en su arquetipo (§4.1: ×6,065), pero **no sé que ninguna cifra publicada se produjera así**: no hay registro de invocación que lo acuse ni lo descarte |

### El hallazgo colateral, confirmado y ya cerrado

Las «6 copias» de `CITAS-POR-NUMERO-DECLARACION.md` **no eran 6 ficheros**, y
esto queda confirmado por la vía que faltaba en la auditoría original:WS es una
cuarta vista más de ese mismo fichero. Anyadir «una copia por subárbol» a un
recuento de redundancia es, como ya dijo `findings/1044:113-116`, un error de
conteo. **Cerrado, y el mecanismo (bind mount, no copias) queda ahora
identificado.**

---

## 7. Fuente de la puerta

Instalable como `tools/aliasgate.py` sin cambios. Es lo que se ejecutó en §5.

```python
#!/usr/bin/env python3
"""aliasgate -- ninguna herramienta que produzca un recuento recorre dos rutas
al mismo inodo.

Criterio de alias: IGUALDAD DE INODO, no igualdad de ruta. `realpath()` NO
sirve: un bind mount es transparente a la resolucion de rutas, asi que realpath
de un alias y del canonico son cadenas DISTINTAS para el MISMO inodo.

Salida: 0 = PASS · 1 = FAIL · 2 = ERROR_DE_OBSERVABILIDAD.
"""
import os, sys


def recorre(raiz, onerror=None):
    vistos, errs, nf, nd = {}, [], 0, 0
    for dp, dn, fn in os.walk(raiz, onerror=lambda e: errs.append(repr(e))):
        nd += 1
        try:
            vistos.setdefault(os.lstat(dp).st_ino, []).append(dp)
        except OSError as e:
            errs.append(repr(e))
        for f in fn:
            p = os.path.join(dp, f)
            nf += 1
            try:
                vistos.setdefault(os.lstat(p).st_ino, []).append(p)
            except OSError as e:
                errs.append(repr(e))
    return vistos, nf, nd, errs


def audit(raiz):
    vistos, nf, nd, errs = recorre(raiz)
    if errs:
        print("ERROR_DE_OBSERVABILIDAD: %d errores de recorrido" % len(errs))
        for e in errs[:5]:
            print("   ", e)
        return 2, None
    colisiones = {i: ps for i, ps in vistos.items() if len(ps) > 1}
    print("raiz               %s" % raiz)
    print("ficheros           %d" % nf)
    print("dirs               %d" % nd)
    print("inodos unicos      %d" % len(vistos))
    print("inodos con >1 ruta %d" % len(colisiones))
    if not colisiones:
        print("PASS: ningun inodo se alcanza por mas de una ruta")
        return 0, None
    print("FAIL: %d inodos alcanzados por mas de una ruta" % len(colisiones))
    shown = 0
    for ino, ps in sorted(colisiones.items(), key=lambda kv: -len(kv[1])):
        if shown >= 5:
            break
        shown += 1
        print("   ino=%d  x%d" % (ino, len(ps)))
        for p in sorted(ps)[:7]:
            print("        %s" % p)
    return 1, colisiones


def selftest():
    """CONTROL NEGATIVO: el detector DEBE encontrar una duplicacion que se
    construye sin privilegios. Un hard link es la misma condicion logica que un
    bind mount y no necesita sudo."""
    import tempfile, shutil, os as _os
    fallos = [0]

    def vec(nombre, cond, det=""):
        print("  %-4s %s %s" % ("OK" if cond else "FAIL", nombre, det))
        if not cond:
            fallos[0] += 1

    d = tempfile.mkdtemp(prefix="aliasgate-")
    try:
        a, b = _os.path.join(d, "a"), _os.path.join(d, "b")
        _os.mkdir(a); _os.mkdir(b)
        f1, f2 = _os.path.join(a, "x.md"), _os.path.join(b, "y.md")
        with open(f1, "w") as fh:
            fh.write("contenido\n")
        _os.link(f1, f2)                      # mismo inodo, dos rutas
        rc, _ = audit(a)
        vec("una sola rama -> PASS", rc == 0, "rc=%s" % rc)
        rc2, col2 = audit(d)
        vec("hard link a/ y b/ -> FAIL", rc2 == 1, "rc=%s" % rc2)
        vec("y el inodo duplicado es el del fichero", col2 is not None and len(col2) == 1)
        rp = {_os.path.realpath(f1), _os.path.realpath(f2)}
        vec("realpath ve DOS cadenas para el MISMO inodo (por eso no sirve)",
            len(rp) == 2, str(sorted(rp)))
        rc3, _ = audit(_os.path.join(d, "no-existe"))
        vec("raiz ilegible -> ERROR_DE_OBSERVABILIDAD, nunca PASS", rc3 == 2, "rc=%s" % rc3)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("RESULT: %s" % ("PASS" if not fallos[0] else "FAIL (%d)" % fallos[0]))
    return 1 if fallos[0] else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if len(sys.argv) < 2:
        print("uso: aliasgate.py <raiz> | --selftest")
        sys.exit(2)
    sys.exit(audit(sys.argv[1])[0])
```

**Lo que esta puerta NO cubre, y hay que decirlo:** comprueba que una raíz es
singly-rooted. No comprueba que una herramienta *use* esa raíz, ni que no la
cambie por entorno en tiempo de ejecución (`RX550_ROOT`). Para eso hace falta
una segunda comprobación, estática, sobre el origen de la raíz de cada
herramienta — que es §3.3–§3.4 de este documento, y que está **pendiente**.

---

## 8. Lo que queda abierto, con nombre

| # | Cosa | Por qué está abierta | Qué la cerraría |
|---|---|---|---|
| 1 | `16 703` nombres de registro | No sé qué herramienta lo produce. Búsqueda por el número en 194 herramientas: sin productor | Identificar el productor y auditar su raíz como en §3.1 |
| 2 | Factor exacto de las 6 herramientas con `RX550_ROOT` | No las ejecuté: cinco escriben en el árbol y este nodo no escribe | Repetir §4.1 con `RX550_ROOT=WS` desde un nodo con escritura permitida, en sandbox |
| 3 | ¿Se invocó alguna vez con raíz `WS` o `~/Escritorio`? | No hay registro de invocación en el árbol. Ni acuse ni descargo | Un log de invocaciones por herramienta con raíz resuelta, como campo obligatorio |
| 4 | Puerta no instalada | Mi alcance es un único fichero | Copiar §7 a `tools/aliasgate.py` y añadirla al registro con `--selftest` |
| 5 | Segunda puerta: origen de la raíz estático | §7 no la cubre | Parsear las 138 herramientas y afirmar `raiz == f(__file__)` porStatic, fallando si aparece `WORKSPACES`, `~` o `getcwd()` sin comprobar |
| 6 | `MAIN/AGENTS.md` es un overlay de un árbol vecino con 6 capas | §1-bis. No multiplica, pero `MAIN` no es autocontenido | Decisión de política: ¿deja de ser un fichero del proyecto? |
| 7 | Cifras de `RE-INDEX.md` | Sin generador (§3.2) | Decidir si se versiona a mano —y entonces no son reproducibles— o se genera |

---

## 9. Reglas que se pueden aplicar

1. **Un recuento es una MEDIDA con una raíz, no un invariante.** El número no
   es la verdad: *número + raíz + fecha* lo es. `2152` sin la raíz con que se
   caminó no es un dato, es un recuerdo.
2. **La identidad es de inodo.** Ruta igual no es contenido igual; y `realpath`
   no es identidad. Si el criterio de unicidad es una cadena, hay alias que no
   se ven.
3. **`followlinks=False` no protege de un bind mount**, porque un bind mount no
   es un symlink: es una entrada de directorio normal. Una herramienta puede
   tener `followlinks=False`, `realpath` en la clave, y seguir contando seis
   veces.
4. **Un `set` de nombres es inmune; un `Counter` no.** La misma herramienta con
   la misma raíz puede ser sana en un número y contaminada en otro, según lo que
   acumule. Clasificar la acumuladora, no sólo la raíz.
5. **«Cero» y «no miró» hay que separarlos siempre.** Los tres fallos
   observados aquí —×6, 0, `None`→[]— son el mismo defecto de tres formas. Un
   `None` que se traduce en lista vacía es una puerta que no puede fallar.
6. **`os.walk` se come los errores.** Sin `onerror`, un recorrido parcial se
   lee como un recorrido completo. Me pasó a mí en esta auditoría y el número
   que casi publico era el del predicado de poda equivocado (§2-bis-bis).

---


---

## 10. Proveniencia: hash de cada fichero citado

Una cita `fichero:línea` sin hash no es reproducible: `check_num_unico.py` y
`toolaudit.py` se movieron durante esta auditoría (§0-bis). Con el hash, una
cita caducada se **detecta** en vez de colarse. Regenerado el
2026-10-04T11:43Z.

| Fichero | sha16 | lineas | bytes |
|---|---|--:|--:|
| `tools/check_num_unico.py` | `7ef0a10d27d9c1a3` | 1430 | 70243 |
| `revkit/huerfanos.py` | `385975dc568b4646` | 294 | 12789 |
| `revkit/cn8.py` | `5112da78600f4081` | 591 | 28763 |
| `tools/artifacts.py` | `0c08da6bf4bfca7a` | 1511 | 73680 |
| `tools/dupenum.py` | `67181553b9d31cee` | 585 | 24638 |
| `tools/git_sano.py` | `9fb6868eb21c4daa` | 319 | 13349 |
| `tools/reservas_gate.py` | `01f3ab850e27eb6b` | 2012 | 97455 |
| `08-ARQUITECTURA/tools/reenvio_gate.py` | `a4bab464ee5c1c13` | 893 | 45921 |
| `08-ARQUITECTURA/tools/reenvio_freeze.py` | `f2de8f21efc97287` | 1287 | 64505 |
| `tools/mountcheck.py` | `564afa2f3d3141c2` | 378 | 14699 |
| `tools/docscan.py` | `889f990c117e4fc6` | 1212 | 51821 |
| `revkit/integro.py` | `639f64a07d08ae12` | 548 | 23342 |
| `08-ARQUITECTURA/tools/toolaudit.py` | `9f3b6a73aa35e779` | 915 | 42450 |
| `08-ARQUITECTURA/tools/findings_index.py` | `fb2fe26eb3700634` | 922 | 43469 |
| `tools/rx550/alcance.py` | `267608aab4c9edfd` | 685 | 32687 |
| `tools/rx550/contract.py` | `38c5a0091e1ce8f4` | 978 | 45146 |
| `tools/rx550/crosscheck.py` | `3be0712033fe24e8` | 455 | 21311 |
| `tools/rx550/funcspan.py` | `b54e564398877ea6` | 832 | 36268 |
| `tools/rx550/mandato.py` | `d56b2d8f4952c835` | 838 | 40210 |
| `tools/rx550/report.py` | `c348972c2893725b` | 430 | 18927 |
| `revkit/sello.py` | `2460eb540d953352` | 421 | 16728 |
| `08-ARQUITECTURA/tools/bench.py` | `4fb5b397f9eb9a39` | 1621 | 81556 |
| `tools/evidence_search.py` | `f364ac1465a51ab8` | 1129 | 47196 |
| `tools/ipsolve.py` | `ca359fdaead32560` | 1221 | 49953 |
| `08-ARQUITECTURA/tools/h1_stale.py` | `bc460762e6b785df` | 242 | 9979 |
| `tools/envcheck.py` | `be6e1e2a07afce17` | 494 | 21971 |
| `08-ARQUITECTURA/RE-INDEX.md` | `3042163520f3cc99` | 1934 | 111681 |
| `06-INGENIERIA-INVERSA/findings/1044-dos-negativos-falsos-en-una-sesion.md` | `616727586035cff1` | 176 | 9065 |
| `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md` | `36cf982390574084` | 290 | 15123 |

Ficheros citados **sin** hash aqui porque son o bien el objeto del
documento (`ALIAS-VALIDEZ-MEDICION.md`), o bien fuentes de mechanism que
se citan por su ruta y no por su linea:
`/proc/self/mountinfo` (sistema), `RX550-INVESTIGACION-WORKSPACES/bin/rx550-ws-targets.sh`,
y las seis herramientas de `WS/bin/` + `WS/systemd/`.

```
FIN DE ALIAS-VALIDEZ-MEDICION
Lo cerrado:  el mapa de alias (7 rutas, 5 subarboles, mecanismo = bind mount),
             la auditoria de 138 herramientas que recorren, 0 contaminadas en su
             raiz por defecto, el factor x6,065 medido, y una puerta con control
             negativo validado.
Lo abierto:  7 puntos, con nombre, en section 8. El mas caro es el 1: hay un numero
             publicado (16 703) sin productor identificado.
Correccion de partida: si habia montajes. mountinfo los lista; df no los ve.
```
