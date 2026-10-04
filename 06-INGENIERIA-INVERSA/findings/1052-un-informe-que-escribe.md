# 1052 — `drift.py` sin banderas ejecuta la única escritura, y su propio `--help` dice que esa escritura es de `--seal`

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-TOOLDESIGN
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · el defecto lo cometí yo
AFECTADO=tools/drift.py:920-921 (el default)  ·  :924 (la rama de escritura)
DOCUMENTADO_EN_CONTRADICCION=tools/drift.py --help, línea de --seal
ESTADO=PROBADO · REPARADO · verificado por md5 del manifiesto antes y después
```

## El defecto, y cómo se encontró

Estaba buscando otra cosa —la dependencia del directorio de trabajo, hallazgo 1051— y
ejecuté `python3 tools/drift.py` dieciséis veces como si fuera un informe. **Escribió el
sello de evidencia en las dieciséis.**

El código:

```python
do = args.all or not (args.toolkit or args.activity or args.seal
                      or args.drift or args.territory)
...
if args.seal or do:
    path, n = seal(repo)
```

`do` significa *«no has dicho nada, hazlo todo»*. Y **«todo» incluía la escritura**. Sin
banderas: `do = True`, luego `if args.seal or do` es cierto, luego `seal(repo)` escribe.

Y el `--help` de **esa misma herramienta**, en la línea de `--seal`, dice:

```
--seal         write the evidence manifest. THE ONLY WRITE
```

> **El default de la herramienta contradice la documentación de la herramienta, en el mismo
> fichero y a noventa líneas de distancia.** Y el default es el que se ejecuta cuando
> alguien escribe el nombre del programa.

## MEDIDO: el daño

```text
docs/EVIDENCE-MANIFEST.sha256

  antes     245 ficheros
  despues   766 ficheros
  diff      587 inserciones, 66 supresiones

  Y 66 hashes CAMBIADOS de ficheros que yo no toqué:
    010-pgm-rsrc1-decoded.md
    013-real-submit-path-polaris12.md
    018-execution-order-invalidacion-gfx8.md
    ...
```

Restaurado con `git checkout -- docs/EVIDENCE-MANIFEST.sha256` y **verificado intacto**:
md5 `449f4583d79f910782a01a91d6768378` antes y después de la comprobación que sigue.

**Y una precisión que importa, porque el daño no era el que parecía.** El sello commiteado
**estaba viejo**, y eso es un hallazgo propio:

```
$ python3 tools/drift.py            # ya reparado: sólo informa
  sellados 245   sin cambio 180   modificados 65   borrados 0   nuevos 521
```

**65 ficheros modificados y 521 nuevos** desde el sello. O sea que mi re-selado
accidental habría producido un manifiesto *correcto*. **Y esa es exactamente la razón por
la que esto es un defecto y no un incidente menor**: la herramienta hacía algo que
resultaba bueno, sin que nadie lo pidiera, y quien lo hizo no lo sabía.

> Un accidente que sale bien enseña la lección equivocada. Un default que escribe cuando el
> usuario cree que está leyendo es la forma más común de que un agente destruya trabajo
> suyo y del ajeno creyendo que no hizo nada.

## Por qué no lo detecté antes: la puerta que debía verlo corre justo donde falla

`tools/toolreg.py:485` ejecuta **cada self-test con `cwd=os.path.dirname(t.path)`**:

```python
r = subprocess.run(argv, capture_output=True, text=True,
                   timeout=timeout, cwd=os.path.dirname(t.path))
```

Es decir: el proyecto **ya tiene** una puerta que corre cada herramienta en el contexto que
la delata. Lo que le faltaba era mirar el contenido de `docs/` después. Y el `--help` de
la herramienta, que sí declara `THE ONLY WRITE`, es la información que el `--help` de
`toolreg.py` no pedía.

Y lo que lo hace más grave:

> **`toolreg.py` tenía el mismo defecto y en la misma forma.** `tools/toolreg.py:1063`
> `add_argument("--repo", default=".")` y `:1077` `repo = os.path.abspath(args.repo)`.
> Es decir: **la puerta que ejecuta las herramientas en el contexto que las delata tenía
> el defecto, y por eso su `--repo` desde `tools/` era el inventario de `tools/`.**

Las dos cosas son el mismo hallazgo 1051 aplicado a tres ficheros, y las tres comparten
el mismo origen: **un valor por defecto que significa una cosa distinta según desde dónde
se escriba el comando, en un programa cuya forma exterior dice lo contrario.**

## Reparado

```python
do = args.all or not (args.toolkit or args.activity or args.seal
                      or args.drift or args.territory)
escribir = args.seal or args.all      # <-- separado: escribir exige pedirlo
...
if escribir:
    path, n = seal(repo)
```

Verificado:

| invocación | antes | después |
|---|---|---|
| `drift.py` sin banderas | **escribía** el manifiesto entero | rc=0, md5 del manifiesto **idéntico**, informe de 167 líneas |
| `drift.py --seal` | escribía | **sigue escribiendo** — el default anterior no lo habilitaba, `--seal` sí |

## Lo que este hallazgo dice de la clase, y es lo importante

Hallazgo 1048: *un filtro que excluye por construcción a la población que dice medir*.
Hallazgo 1050: *un filtro que devuelve vacío sin decirlo*. Hallazgo 1051: *un valor por
defecto que depende del cwd*. Hallazgo 1052: *un valor por defecto que hace una cosa
distinta de la que el `--help` promete*.

**Los cuatro son el mismo defecto con cuatro máscaras: el valor por defecto de un programa
no es una decisión, es una afirmación que nadie ha medido.** En los cuatro casos, lo que
faltaba era lo mismo: alguien ejecutando el programa **como lo ejecutaría un usuario**, y
no como lo ejecuta quien lo escribió.

Y esa es exactamente la prueba que ninguno de los cuatro self-tests contenía: **el
self-test se ejecuta como lo ejecuta el autor.** El proyecto lo dice en el comentario de
`tools/constmap.py:124`, y es la frase más útil de esta tanda:

> *«A self-test that only passes when invoked the way its author happens to invoke it is
> not a self-test.»*

Y aplicándola a esto: **una herramienta que se comporta de una manera cuando se la ejecuta
como su autor y de otra cuando se la ejecuta como un usuario necesita un self-test que se
la ejecute como un usuario.** No hace falta root, ni GPU, ni autorización: hace falta
`cwd=` y un `os.stat` antes y después.

## Lo que NO se afirma

- **No se afirma que el sello commiteado sea correcto.** Se afirma que está **viejo** —
  65 modificados y 521 nuevos — y que refrescarlo es una decisión deliberada que no he
  tomado. `docs/EVIDENCE-MANIFEST.sha256` está en su estado commiteado.
- **No se afirma que `drift.py --seal` esté probado.** La rama sigue siendo alcanzable y
  la he leído; no la he ejecutado después del cambio, porque ejecutarla escribe.
- **No he tocado `toolreg.py` más allá del `--repo` de 1051.** No he revisado si tiene
  otros default silenciosos.