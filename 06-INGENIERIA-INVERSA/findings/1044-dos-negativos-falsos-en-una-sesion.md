# 1044 — dos negativos falsos en una sesión: el `exit 7` que "no existía" y el fichero que "se estaba borrando"

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-CITAS
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST, ESTE WORKING TREE
AFECTADO=08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARATION.md
          sha256=36cf982390574084c3d5aad59341648b079e11ce3d077e4f683519618f150398
          15123 B · 291 lineas · mtime 2026-10-04 06:36 SIN CAMBIOS
ESTADO=PROBADO (dos negativos falsos) · CAUSA_DEL_ENOENT=NOT_DETERMINED
         · PERDIDA_DE_DATOS=PROVEN_ABSENT (verificado)
```

## La afirmación

Dos veces en esta sesión afirmé una ausencia con una sola prueba, y las dos
veces era falso. La primeraBnunca@tuvo consecuencias. La segunda casi me hace
publicar una pérdida de datos que no ocurrió. **El defecto no es de la
herramienta: es de mi inferencia.**

## MEDIDO

### 1. Negativo falso nº1: `exit 7` "no existe"

Afirmé, textualmente: *«`exit 7` **no está implementado**»*, having medido with:

```python
re.search(r'(exit|return|raise)\b.*\b7\b', l)
```

El codigo de salida se define por una **constante con nombre**, no por un
literal `7`:

```
tools/check_num_unico.py:267   EXIT_CITAS_SIN_ADJUDICAR = 7
tools/check_num_unico.py:939   7: "hay citas por numero que el CENSO no ha adjudicado  "
```

El codigo existia, con su constante, su entrada en el diccionario de nombres y su
explicacion de por que ese diccionario es una lista que hay que mantener. Mi
regex buscaba la palabra `exit` seguida del digito `7`, y en un lenguaje donde
los codigos de salida se nombran, eso no encuentra nunca nada. **La regex
mala no produce un error: produce una ausencia, y una ausencia parece un
hecho.**

Corrijo explicitamente lo dicho en su momento: **si 7 existe, y existe desde el
commit `85ca0c5`.**

### 2. Negativo falso nº2: el fichero "se está borrando"

Secuencia real, en orden:

| # | Operacion | Resultado |
|---|---|---|
| 1 | `ls -la` | presente, 15123 B, mtime 06:36 |
| 2 | `open()` | **FileNotFoundError** |
| 3 | `os.listdir()` del padre | presente · `os.path.exists()` del hijo: **False** |
| 4 | desde otro `cwd`: `os.stat` + `open()` | `stat` OK 15123 · `open` leyó **15098 B** |
| 5 | `fuser` | *no existe* · `stat` en bucle: **FileNotFoundError** |
| 6 | 6 vueltas a 20 ms | estable, inodo 7252326, 15123 B |
| 7 | `cp` a evidencia | **no existe el origen** |
| 8 | 60 s a 20 ms | **AUSENTE, estable** |
| 9 | `find` en el segundo arbol | **6 rutas** al mismo nombre |
| 10 | las 6 rutas, leidas | **0 vivas de 10** |
| 11 | `os.stat` sobre el fichero principal | OK 15123 |
| 12 | `open()` | **FileNotFoundError** |
| 13 | 30 + 30 aperturas, literal y nombre-de-listdir | **30/30 y 30/30** |
| 14 | contenido | 15123 B · sha256 `36cf9823…f150398` · 291 lineas |

**El dato que decide y que no leí a tiempo: el `mtime` nunca cambió.** Un
fichero que se borra y se reescribe tiene `mtime` nuevo. Este tiene el de las
06:36 en las trece observaciones. **El fichero no se borró nunca.** Lo que
tuve fue una serie de `open()` fallidos, y de ahi construí: «borrado», «alguien
borra y recrea», «seis copias», «perdida recuperable», «perdida total».

### 3. Lo que refuté antes de mirar el `mtime`

Cada una con su prueba, y las cinco **quedaron refutadas**:

| Hipótesis | Prueba que la refuta |
|---|---|
| `git clean -fd` | Habría borrado **las 11** rutas no registradas en una pasada, incluidas `07-DRIVER/firmware/` y `06-INGENIERIA-INVERSA/protocol-dumps/`. **Las 11 siguen vivas.** |
| `git checkout` / `git restore` | El fichero **no esta registrado** (`git ls-files` no lo conoce, `git cat-file -e HEAD:…` falla, 0 objetos en `rev-list --objects --all`). No hay nada que restaurar. |
| Montaje overlay / fuse | `df -T` da `/dev/sdb3` **ext4** en las dos rutas; `stat -f` da `ef53`. Sin sysfiles, sin `/run/user/1000` en juego. |
| Symlinks en la ruta | `os.lstat` (que **no** sigue symlinks) dice `dir` en los cuatro componentes. |
| Inode borrado con fd abierto | Nadie tiene el inodo 7252326 abierto: 0 coincidencias en `/proc/*/fd`. |
| Daño del filesystem | Sin `ENOSPC` (279 GB libres, inodos al 7 %) y sin evento de E/S. |

**Lo que queda: `NOT_DETERMINED`.** No tengo trigger reproducible. En la
medicion final, el mismo path literal abrio **30 de 30**. No se reproduce, y
un defecto que no se reproduce no se repara a ciegas: se registra.

### 4. Lo que si|resultó ser cierto, y no lo sabia: el segundo arbol es el primero

`RX550-INVESTIGACION-WORKSPACES/` **no es un segundo proyecto**. Medido con
`lstat`:

```
RX550-INVESTIGACION                     ino=28966954  nlink=21  dir
RX550-INVESTIGACION-WORKSPACES/
  01-COORDINACION                       ino=28966954  nlink=21  dir   <-- el MISMO inodo
  01-COORDINACION/08-ARQUITECTURA       ino= 7232747  nlink=12  dir
RX550-INVESTIGACION/08-ARQUITECTURA     ino= 7232747  nlink=12  dir   <-- el MISMO inodo
```

Seis entradas —`01-COORDINACION`, `02-SOFTWARE-GPU`, `03-GPU-SEMANTICS`,
`04-RUNTIME-PROBING`, `05-TOOLING-AUTOMATION`, `06-DRIVER-C-ASM-PERFORMANCE`—
**son alias del arbol principal**. `git worktree list` devuelve **una sola**
entrada, luego no son worktrees. Y las entradas propias de WORKSPACES son
`bin`, `.store`, `systemd`, `ARCHITECTURE.md`, `ROLES.md`, `VALIDATION.md`,
`README.md`, `FINDING-ROLLBACK-NOOP.md` y el fichero
`04-RUNTIME-PROBIGACION-PLACEHOLDER` (con una `G` de mas en el nombre).

**Consecuencia directa sobre mi propia conclusion:** las «6 copias
identicas, sha `36cf9823…`» **no eran 6 ficheros**. Eran **6 rutas al mismo
inodo**. Un recuento de redundancia que cuenta rutas en vez de inodos
inventa una redundancia que no existe — y, por simetria, **puede perder una que
si existe**. `AGENTS.md` §91 dice *«No mantener un segundo arbol de proyecto
activo»*: aqui no hay segundo arbol, y por eso el Finder de ficheros muestra el
contenido del proyecto **siete veces**.

## Que se rompe por esto, y que no

- **`PROVEN_ABSENT` la perdida.** El artefacto esta integro y verificado por
  hash. El estado de las 132 adjudicaciones **no cambia**.
- **`NOT_DETERMINED` la causa del ENOENT.** Registrado, no resuelto.
- **Abierto y con nodo asignado:** si alguna herramienta que produce un
  recuento recorre mas de una ruta al mismo inodo, sus cifras estan
  multiplicadas. Este proyecto vive de contar —`2152` citas, `16 703`
  registros, `45.7 % [26.0 ; 65.4]`, 74 numeros duplicados, 201 filas de
  herramientas— y un factor de multiplicacion invisible no se distingue de un
  dato malo. Delegado en `ALIAS-VALIDEZ-MEDICION`.

## La leccion, en la forma que se puede aplicar

`AGENTS.md` §27 exige, antes de consumir un artefacto, demostrar `EXISTE +
COMPLETO + VALIDO + TIPO ESPERADO`. Ese regla es **simetrica**, y se me
escapo: tambien exige, antes de declarar una **ausencia**, demostrar que el
metodo de deteccion es capaz de detectarla.

Tres reglas, entonces:

1. **Un negativo necesita un positivo de capacidad.** Antes de decir «no
   existe», comprobar que el metodo **encuentra** lo que deberia. Un
   `find` que devuelve 0 sobre un arbol que se sabe que lo tiene, no
   demuestra que no este: demuestra que el `find` no sirve. En este caso:
   `find` encontro el fichero, `open` no. **Los dos se contradicen, y
   gano el que si tiene poder de observer.**
2. **Un `mtime` que no cambia refuta un «se esta reescribiendo».** Es la
   prueba mas barata del mundo y yo no la hice hasta la decima observacion.
   Con hindsight, era la unica que importaba.
3. **Verificar por hash en la PRIMERA lectura, no cuando se pierde.** Lei el
   fichero entero y no lo hasheé, porque todavia «no hacia falta». Ese fue el
   momento en que un defecto pasivo de lectura se volvio una perdida
   permanente. La regla no es «hashea lo que consumas»: es «hashea lo que
  dependas».

Y una cuarta, sobre el patron de fondo, porque se ha repetido en este proyecto
en el analisis de dos dominios distintos:

> **Una regex demasiado estrecha no falla: produce ceros.** Un `\d{3}` donde
> hacia falta `\d{3,4}` dejo 25 hallazgos invisibles en `artifacts.py` y en
> `dupenum.py`. Un `(exit|return|raise).*7` no encontro el codigo 7. **Los dos
> son el mismo defecto**, y el segundo es mio y es de hoy.

## Lo que NO se afirma aqui

- No se afirma que el ENOENT tenga una causa. Es `NOT_DETERMINED`.
- No se afirma que las seis rutas del workspace sean un mecanismo concreto.
  El **efecto** esta medido —mismo inodo, alcanzable por dos rutas—; el
  mecanismo por el que el kernel lo permite, no.
- No se culpa a ningun subagente. En la ventana en que aparecieron los
  `ENOENT` estaban en vuelo cinco nodos escribiendo en `08-ARQUITECTURA/`, y
  dos de ellos entregaron su fichero (`CENSUS-CAPACIDADES.md` a los 81 s,
  `MEMORIA-GFX8.md` a los 11 s). **No hay prueba de que ninguno escribiera
  este fichero**, y el `mtime` de las 06:36 es anterior a su lanzamiento. La
  hipotesis «lo borro un subagente» queda **sin medir** y no se sostiene ni se
  descarta: `NOT_DETERMINED`.