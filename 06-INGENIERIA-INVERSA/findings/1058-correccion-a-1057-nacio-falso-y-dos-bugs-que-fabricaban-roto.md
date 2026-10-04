# 1058 · Corrección a `1057`: uno de los dos hashes que "se quedaban viejos" nació falso, y el Instrumento tenía dos bugs que fabricabanIROTO

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-VALIDITY
CLASSIFICATION=CORRECTION+VALIDATION · TRACK=STATIC+MUTATION
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=1057 §4 y §5 (CORREGIDO) · tools/sello_prov.py 1.0.0 -> 1.1.0
         06-INGENIERIA-INVERSA/findings/977-...md:318 y :322
         .git/objects  (5 objetos vacios -- ver §4)
CORRECTS=1057-la-receta-de-reproducible-existia-y-mi-instrumento-la-declaraba-inexistente.md
ESTADO=PROBADO · REFUTADO-POR-ADVERSARIO · 50 vectores · 14 mutaciones detectadas
herramienta   tools/sello_prov.py 1.1.0
sha256        9bc06ad8598daa6c
```

## 0 · Qué queda en pie y qué no

`1057` afirmaba, y lo sostuve con la tabla que no construí:

> 2 de 6 sha256 del bloque §10 del `977` son afirmaciones falsas. Y el dato que lo
> convierte en hallazgo y no en sospecha es que para los dos, `sha256(HEAD:file) ==
> sha256(file)`: el fichero no se ha movido. […] Dos commits posteriores al `10a798d`
> movieron los dos ficheros.

**Una de las dos mitades es falsa, y el oráculo que yo di por decisivo no puede
distinguir los dos casos.**

| el oráculo que di | lo que realmente dice |
|---|---|
| `sha256(HEAD:f) == sha256(f)` | "el fichero no se ha movido **hoy**". Es cierto para casi todo fichero versionado sin modificar: **no lleva información ninguna** sobre si un documento se quedó viejo |
| `sha256(decl) == sha256(<commit que introdujo el documento>)` | **este** es el que separa "se quedó viejo" de "nació falso" |

Yo ejecuté el primero y no el segundo. La tabla de resultados la monté sin ejecutarla.

## 1 · LA SEPARACIÓN, Y LA REPARTO 1 + 1

Recorriendo **todos** los commits alcanzables (`git rev-list --all`) y hasheando
`04-IMPLEMENTACION/rx550-driver/tests/Makefile` en cada uno:

```
commits en los que ese fichero tuvo el contenido declarado: 0
```

**Ninguno. Ni uno, en ningún commit que haya existido en este repositorio.**

| fichero | declarado | ¿fue verdad alguna vez? | causa |
|---|---|---|---|
| `rx550_vmid0_gart.h` | `ad2c5958…` | sí, en `10a798d` | **DECAY**: `03eb79c` y `28f1c47` movieron el contenido |
| `tests/Makefile` | `28e3b582…` | **no, en ninguno** | **NACIÓ FALSO** |

Y la causa del segundo no es la que conté. El blob cuyo sha256 es `28e3b582…`
(`ceb1bb30`, 6105 B) es del contenido del Makefile **cuando el hallazgo se llamaba
`968`**. La diferencia con el commiteado son **una línea**:

```
linea 19
  commiteado : #   06-INGENIERIA-INVERSA/findings/977-suite-gart-no-compila-y-no-era-un-maximo.md
  declarado  : #   06-INGENIERIA-INVERSA/findings/968-suite-gart-no-compila-y-no-era-un-maximo.md
```

**Una pasada de renumeración reescribió un lado de un par de referencias cruzadas y
no el otro**: cambió el `968` por `977` dentro del Makefile, renombró el documento, y
no recalculó el hash que ese documento lleva dentro. `FINDINGS-RENUMERACIONES.md`, en
este mismo árbol, ya avisaba de que esa operación es **sin registrar y sin commit**.

Corroboración que no es casualidad: de los seis ficheros citados, `tests/Makefile` es
**el único** que menciona el hallazgo por su nombre. Los otros cinco no tienen
referencia cruzada, y por eso ninguno se rompió.

**Consecuencia para el remedio que yo propuse, y es la importante:** una puerta que
reescribiera el digest declarado al valor de `HEAD` **empeoraría el documento**. Le
haría afirmar una procedencia sobre un Makefile que **no es** aquel sobre el que se
midió el hallazgo. Convertiría una afirmación falsa en otra afirmación falsa. **La
regla de invalidación que falta no es "recalcular"**: es que un hash declarado **no se
puede recalcular jamás sin perder lo que afirmaba**, porque lo que afirmaba es el
estado en el momento de la medición.

## 2 · MI GENERALIZACIÓN ERA `n=1`, Y NO LO SABÍA

Escribí *"los bloques de procedencia no tienen regla de invalidación, y por eso se
convierten solos en afirmaciones falsas"*. Cuantificador universal, un solo bloque.

Bajo mi propio instrumento, sobre `findings/`:

```
bloques 9 · campos 14 · rc=2 (CENS0 INCOMPLETO: 3 documentos sin auditar)
```

**Las seis declaraciones de sha256 de fichero entero que el instrumento puede resolver
en todo `findings/` están todas en ese documento.** No hay una segunda instancia en
560 ficheros. El estado honesto es `NOT_DETERMINED`, no `PROVEN`: no hay evidencia a
favor ni en contra más allá de un bloque.

Y mi cifra de §5 era además **un censo de un subconjunto no declarado**, porque el
instrumento abortaba sobre 3 documentos. Censo independiente, todos los layouts:

```
43 declaraciones de sha256 de 64 hex, en 27 de 560 documentos, 30 valores distintos
  19  coinciden con un fichero que existe hoy
  11  no coinciden con nada del arbol:
        1  = ad2c5958  ->  DECAY, confirmado
        1  = 28e3b582  ->  nació falso, confirmado
        9  ->  no coinciden con ningún fichero NI con ningún objeto del repo
```

**De los 11 que no pude resolver, 2 resultaron defectos reales: 18 %.** Un 18 % de
acierto sobre "no verificable" es un argumento fuerte para `NOT_DETERMINED`, y yo los
archivé como *"límites de mi vocabulario"*. Eso no es una clasificación de los
documentos: es una conjetura de mi parser.

## 3 · LOS TRES BUGS DEL INSTRUMENTO, Y UNO ERA MENTIRA CON `rc=0`

El adversario encontró tres. Los tres eran reales, y el primero lo describio como
"12 ROTO falsos de 14 campos":

| # | bug | cómo se manifestaba | detectado por |
|---|---|---|---|
| B1 | `--raiz` se derivaba de `--arbol` | un comando plausible daba 12 ROTO falsos, `COINCIDE 0` | adversarial-reviewer |
| B2 | el mismo digest para varios paths se contaba `COINCIDE` | el hash **no distingue**; en el `977` el mismo valor declara `gate-run-1.txt` y `gate-run-2.txt` y cumple en ambos | adversarial-reviewer |
| B3 | layout `sha256 <path> <digest>` (hallazgo `970`) | **silencio**: ni un veredicto | adversarial-reviewer |

**B3 es el peor de los tres por una razón que no es de código.** Un campo que no se
reporta parece un campo que no existe. Un `ROTO` equivocado se discute; un silencio
se acepta. B1 lo introduced yo al **arreglar** B1: separé las dos raíces y seguí
abriendo los documentos contra la raíz equivocada, con lo que un censo entero salía
como `ilegible` — un censo vacío disfrazado de censo.

**Y el self-test no lo veía porque no había ni un vector con dos raíces distintas.**
Eso es la lección, y no es el bug: *un self-test que solo ejercita el caso trivial de
la opción para la que existe la opción no cubre la opción*. Añadido `V21`/`V21d`.

### El defecto que más me importa, porque no lo encontró nadie más

Mutación `M14`: reabrir los documentos contra la raíz de resolución en vez de la de
barrido. **Pasaba 49 de 49 vectores.** La rama es alcanzable solo por la API, no por
la CLI, y yo escribí *"no lo detecta la CLI"* como si fuera *"no lo detecta nadie"*.
Añadido `V21d`, y ahora `M14` falla.

## 4 · `[01]` HALLAZGO NUEVO, Y NO ESTÁ EN MI HALLAZGO: EL OBJECT STORE ESTÁ DAÑADO

Lo encontré por un error de un comando mío, y lo cuento así porque es lo que pasó.

`git log --all --find-object=ceb1bb30` falló:

```
fatal: unable to read 499bffcbd6f36c3141f5c2497957e43f4e2c50d6
```

**`.git/objects` tiene 5 objetos sueltos de tamaño cero.** `git fsck` los reporta, y
además:

```
error: refs/heads/main: entrada de log de referencias inválida 729ab738dea2c67c28e065abbab87ec373d47141
```

Estado medido:

| pregunta | respuesta |
|---|---|
| ¿grafo de commits intacto? | **sí** — `HEAD` = `6e68f57`, legible; conectividad sin más errores |
| ¿cuántas entradas de reflog dañadas? | **una** — `.git/logs/HEAD` (551 líneas) nombra un objeto vacío, 2 veces |
| ¿algún commit pierde contenido? | no |
| ¿qué se rompe? | `git fsck`, y todo comando que consulte el reflog |
| ¿otros 4 objetos vacíos? | referenciados por nada visible |

**Por qué importa y no es un detalle de higiene.** El árbitro de todo el §1 —"¿fue
alguna vez verdad?"— es un recorrido del historial. Si el recorrido **falla a mitad**,
el árbitro miente, y miente en la dirección dangerous: un `--find-object` que aborta
devuelve "no lo encuentro", que es idéntico a "nunca existió". Con el store sano, el
`0 commits` de §1 es un hecho; con el store dañado, es un hecho **hasta donde llegó
el recorrido**. No he medido hasta dónde llegó.

### El efecto secundario que YO produje, y que no estaba buscado

`git fsck` **no es de solo lectura cuando encuentra corrupción**. Salió `actualizando
blob …` y estaba **escribiendo en `.git/objects`**. No lo sabia y no lo intente: lo
lancé para medir el alcance del daño y así amplié el daño. Debí haberlo comprobado
antes (§42 INTERVENTION GATE: el gate va antes de la acción, no después).

Lo que **no** he hecho, y es deliberado: **no he reparado nada.** El arreglo
canónico —`git reflog expire --expire-unreachable=now`— **destruye el registro de las
posiciones pasadas de HEAD**, que es lo único que deja ver quién commiteó qué, y es
un repositorio **compartido con otra sesión activa**. Eso es `DESTRUCTIVE` /
`IRREVERSIBLE` en la escalera de §42, y la decisión no es mía. Queda `DEFERRED` al
dueño del árbol.

## 5 · LO QUE EL INSTRUMENTO SIGUE SIN HACER, Y ES LA FRONTERA

`sello_prov.py` es `SELF_TESTED`, con 50 vectores y 14 mutaciones deliberadas
detectadas. **No es `VALIDATED`**, y ahora se sabe por qué no puede serlo todavía:

1. **No es una puerta.** MEDIDO: `grep -rn sello_prov` sobre el árbol solo devuelve
   aciertos dentro del propio `1057`. No está en `revkit/check.sh`, ni en
   `pipeline.py`, ni en `govcheck.py`. **No hay hooks activos ni CI.** Nada lo
   ejecutará nunca, y mi commit no cambia ni una línea de comportamiento por
   defecto. Publicar una herramienta sin conectarla es exactamente el `tool theater`
   de §99.
2. **El mecanismo que yo dije que no existia, existe y está en rojo.**
   `revkit/sello.py` + `docs/EVIDENCE-MANIFEST.sha256` sellan **134** ficheros de
   `findings/`, están cableados en `revkit/check.sh:504`, y ahora mismo:
   ```
   rc=1   OK 177 · MOVIDO 68 · ROTO 0      findings 23 · tools 28 · other 17
   ```
   **23 documentos de hallazgo sellados se han movido.** Un 28 % de deriva sobre el
   manifiesto de evidencia, ya medido, ya en una puerta, y **no lo mencioné** en
   `1057`. Lo que sí es cierto, y lo reduzco a lo medido: `sello.py` y `drift.py`
   sellan el **documento entero**; ninguno parsea los digests **declarados dentro**.
   Eso sí lo comprobé, contra ocho candidatos más la puerta.
3. **El layout `sha256sum` clásico** (`<hex>  <size>  <path>`, hex al principio) está
   en `archive/`, que excluyo del barrido. No implementado.
4. **Los 9 digests colgantes** no están adjudicados. `NOT_DETERMINED`.

## 6 · PROCEDENCIA

```text
herramienta   tools/sello_prov.py 1.1.0
sha256        9bc06ad8598daa6c
selftest      50 vectores, 0 fallos, rc=0
mutaciones    14 deliberadas, 14 detectadas.  Las nuevas de esta iteracion:
              M12  la ambiguedad se ignora                      -> V19
              M13  --raiz vuelve a derivarse de --arbol         -> comando real (no el selftest)
              M14  documentos reabiertos contra la otra raiz    -> V21d  (tras anadirlo)
verificacion cruzada  adversarial-reviewer (refuto 1057 §4 entero y encontro B1-B3)
                     explore (localizo RESEARCH/baseline/linux-7.1.3 a maxdepth 13)
contramedida  la separacion DECAY vs NACIO FALSO por `git rev-list --all`, rehecha por mi
```

**Lo que este documento NO prueba.** No prueba el mecanismo de los 9 colgantes. No
prueba que `rx550_vmid0_gart.h` sea el único caso de decay: con el object store dañado,
el recorrido de §1 no tiene alcance probado. No toca la GPU. Y no repara nada: el
object store sigue como estaba.