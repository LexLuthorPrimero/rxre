# 1039 · El repositorio tiene cinco objetos corruptos, y `fsck` sale con 0 al decirlo

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=N/A` · `HARDWARE_SCOPE=N/A` (ningún acceso a hardware)
`WORK_CLASS=READ_ONLY` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1`
`GPU INTACTA` · `MODIFIES_CODE=SI` (`tools/git_sano.py`)

---

## La pregunta

Un nodo concurrente intentó medir el historial de renumeraciones con
`git log --diff-filter=A -- 06-INGENIERIA-INVERSA/findings/` y el comando **murió**:

```
$ git log --oneline --diff-filter=A -- 06-INGENIERIA-INVERSA/findings/
fatal: archivo de objeto .git/objects/49/9bffcbd6f36… está vacío
```

Un objeto de 0 bytes no se descomprime: la cadena termina a media secuencia. Eso no
es un objeto vacío legítimo — `e69de29bb2d1…` es el blob vacío canónico de git y
está perfectamente formado — es un fichero **truncado en disco**.

La pregunta era: ¿es un caso aislado o el repositorio está dañado en general?

## MEDIDO

### Los cinco

```
$ find .git/objects -type f -size 0
729ab738dea2c67c28e065abbab87ec373d47141
4aebdccf2401289d61936c9b9b6afc79284af064
f5a80d162be89c1046b4f09d70eb4af8a182cdfb
499bffcbd6f36c3141f5c2497957e43f4e2c50d6
01361a2b7a9c669ab7f1cb53f97b15b64c5640c6
```

Cinco. Uno de ellos (`499bffcbd6f3`) es el blob del hallazgo `1011` — un fichero que
en el árbol de trabajo tiene **11 598 bytes** y que en git **no se puede leer**. Esos
11 598 bytes existen una sola vez, en el disco de trabajo, sin copia en el historial.

### `fsck` dice "error" y sale con 0

Esto es lo que hace que el hallazgo no sea solo "hay corrupción":

| invocación | rc | líneas "está vacío" | otras líneas |
|---|---|---|---|
| `git fsck --connectivity-only` | **0** | 14 | 238 |
| `git fsck --connectivity-only --no-dangling` | **0** | 2 | 1 |
| `git fsck --full` | **3** | 5 | 246 |

`--connectivity-only` es la bandera que se usa **por velocidad**: es la que permite
comprobar un repositorio grande en segundos. Y es exactamente la que **reporta la
corrupción en stderr y devuelve 0**.

El resultado es que la forma natural de usar la herramienta como puerta —`fsck` y
comprobar el código de salida— **no puede fallar**. Imita exactamente al defecto que
este proyecto lleva cinco commits corrigiendo: un control cuyo código de salida no
significa nada, ocupando el sitio de un control.

Lo verificado que sí funciona: `--full` da `rc=3`, y `--connectivity-only
--no-dangling` reduce el ruido de 238 líneas de "dangling" a 1, dejando las 2 que
importan.

### Qué comandos sobreviven y cuáles no

```
git log --oneline -3                                  rc=0     sobrevive
git rev-list --all --count                            rc=0     448 commits
git ls-tree HEAD <dir>                                rc=0     sobrevive
git log --oneline --diff-filter=R                     rc=128   MUERE
git log --oneline --diff-filter=A -- findings/        rc=128   MUERE
git fsck --connectivity-only                          rc=0     dice error
```

El patrón: sobreviven las operaciones que leen **dos árboles** (`ls-tree HEAD` contra
el árbol de trabajo) y mueren las que **recorren el historial**. Eso no es casualidad
— la corrupción está en objetos que sólo se alcanzan por recorrido.

Consecuencia ya medida en otro nodo: la procedencia `diff` del mapa de renumeraciones
**no puede volver a derivarse del historial**. Se conserva porque el árbol de trabajo
contra `HEAD` sí funciona, no porque el historial sea sano. Si alguien intentara
auditar esas 43 filas con `git log`, obtendría `rc=128` y una respuesta que parece
"no hay renumeraciones" en vez de "no se puede saber".

### Ninguna puerta del proyecto lo comprueba

Barrido de los 2 499 ficheros del alcance del proyecto, `.py` y `.sh`, buscando
`fsck`:

```
NINGUNA puerta usa fsck
```

O sea que la corrupción lleva tiempo ahí y no hay nada que lo haya notificado. No es
una puerta que dé un falso veredicto: es la ausencia de la puerta.

## LA PUERTA

`tools/git_sano.py`. Tres decisiones, y las tres son forzosas por lo medido:

1. **Usa `fsck --full`**, no `--connectivity-only`. Por lo de arriba: la bandera
   rápida es la que devuelve 0. Y **declara en su propio texto** por qué, con los dos
   números medidos, para que nadie la "optimice" dentro de seis meses.
2. **Cuenta los ficheros de 0 bytes por su cuenta**, con `stat`, y no se fía del
   código de salida de nadie. Es la misma disciplina que el resto del componente: la
   medida la hace el instrumento, no el informes de otro.
3. **Devuelve código distinto de 0 con el número de objetos en el mensaje**, para que
   quien lo ejecute no tenga que abrir un segundo comando para saber qué pasó.

Y tiene `--self-test` con la forma de la cadena: un `git init` de un temporal con un
objeto truncado inyectado a mano, que **debe** dar fallo. Una puerta que solo se
ejecuta sobre el repositorio real —donde hoy fallaría, sí, pero mañana puede no
fallar— no demuestra que sepa decir que no.

## LO QUE ESTO NO ARREGLA

- **Los 11 598 bytes de `1011` no se pueden recuperar de git.** No hay copia. El
  trabajo de trabajo los tiene; el historial no. Eso no lo arregla ninguna puerta:
  solo un commit futuro.
- **`git gc` no los arregla.** Eliminar objetos sueltos no-profundos está fuera del
  alcance de `gc` en las versiones actuales, así que los cinco siguen ahí y `gc` no
  los va a tocar. Repararlo requiere reescribir a mano el objeto afectado, lo que
  cambia su SHA y por tanto invalida cualquier referencia que lo contenga.
- **No he tocado el repositorio.** Ni `gc`, ni `prune`, ni `repack`. Todos ellos
  pueden empeorar el estado si se ejecutan a ciegas sobre objetos ya truncados, y la
  operación de rescate necesita decidir antes qué pasa con las referencias.
- **El alcance.** He contado objetos de 0 bytes en `.git/objects`, que es donde git
  guarda los objetos sueltos. No he auditado los packs (`.git/objects/pack/`), que
  son un almacén distinto. `fsck --full` sí los recorre, y da 5 — el mismo número —
  de modo que los cinco son sueltos y los packs están bien. Eso queda dicho para que
  conste, no como conclusión general sobre la integridad del repositorio.

## POR QUÉ ESTO ES DEL TIPO QUE ES

`exit 0 != resultado válido`, que es la regla 26 de `AGENTS.md`, escrita aquí porque
git la incumple en una bandera que la gente usa por rendimiento. Un `fsck` que dice
`error:` en stderr y devuelve 0 es peor que no ejecutar `fsck`: ocupa el sitio del
control, y quien lo lee se va tranquilo.

## LO QUE QUEDA

- Reparar los cinco objetos o declarar que el historial de `findings/` no es
  auditable y por qué.
- Auditar los packs, que aquí no se ha hecho.
- El segundo uso del mismo defecto — una tabla que confunde dos relaciones distintas
  bajo el mismo nombre de columna — está en el hallazgo contiguo.
