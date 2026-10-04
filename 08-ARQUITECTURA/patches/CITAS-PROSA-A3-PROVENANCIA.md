# PROVENENCIA —CITAS-PROSA-A3

Que este trabajo esta en el historial y con que mensaje, porque el mensaje **no**
es el suyo.

## Que paso

El nodo `CITAS-PROSA-A3` preparo ocho ficheros y los dejo en el indice de git con
`git add` de rutas explicitas.  No commiteo todavia.  Mientras tanto, otro nodo
commiteo con `git commit` **sin `--only`**, que commitea el indice entero.  Sus
ocho ficheros se fueron dentro del commit de ese otro nodo:

```
85dd997  gart_table: un SIZE_MAX propio que el kernel ya define, y que ademas
          estaba equivocado
```

Los ocho:

```
08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md
08-ARQUITECTURA/patches/citas-no-citas-y-A3-informativo.patch
08-ARQUITECTURA/patches/citas-registro-2-entradas.patch
08-ARQUITECTURA/validations/citas-prosa-censo-20261004.tsv.gz
08-ARQUITECTURA/validations/citas-prosa-muestra-20261004.json.gz
tools/citas_prosa_census.py
tools/citas_prosa_adjudicado.py
tools/citas_prosa_etiquetas.py
```

VERIFICADO que el contenido commiteado es identico byte a byte al del arbol de
trabajo: `git show HEAD:tools/citas_prosa_census.py` comparado con el fichero.

## Que NO se hace, y por que

**No se reescribe la historia.**  `85dd997` contiene tambien el trabajo del otro
nodo sobre `04-IMPLEMENTACION/rx550-driver/rx550_gart_table.h`.  Correr un
`rebase` para separate pondria ese trabajo en riesgo con otro agente activo en el
mismo arbol.  Un commit bien escrito no vale un commit destruido.

## Que se hace

Esto.  La declaracion de clases, la decision de la puerta y los dos parches ya
dicen que son; lo que no decia nadie es **bajo que commit estan**, y eso se
declara aqui una vez y no se propaga.

## La regla, para el siguiente

Cuando dos agentes van a commitear en el mismo arbol, `git add` **no** es un
candado.  Lo que es un candado es commitear con rutas explicitas:

```
git commit --only -F <mensaje> -- <mis rutas>
```

Y si ya se commiteo por error, la reparacion es declarar, no reescribir.