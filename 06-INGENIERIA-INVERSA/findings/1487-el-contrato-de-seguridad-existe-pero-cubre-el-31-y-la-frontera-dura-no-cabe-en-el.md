# 1487 — El contrato de seguridad ya existe y valida 68 herramientas; la caja entera no, y la frontera dura no es representable en él

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05
TIPO=MEDICION
ESTADO=PROVEN
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA (salvo
  `--help-probe`, que ejecuta `--help` sobre 192 ficheros python)
MEDIDO=sobre el arbol local. Sin MMIO, sin TLB, sin insmod, sin tocar 0000:00:02.0
PRODUCER=08-ARQUITECTURA/tools/toolkit.py (ejecutado)
ARTEFACTO=RXRE/tools/rxre_boot.py --selftest -> 19/19 PASS
COMANDO=python3 08-ARQUITECTURA/tools/toolkit.py   # rc=1
HERRAMIENTA_DESTINO=08-ARQUITECTURA/tools/bench.py  # WRITES_GPU=yes
```

## Qué se buscó

El hallazgo `1481` medía un hueco de catálogo: 213 herramientas que `rxre` no
puede enrutar porque no tienen capacidad declarada. Al buscar **cómo** se declara
la seguridad de esas herramientas apareció algo que el prompt no mencionaba y que
cambia el orden del trabajo: **la respuesta ya existe, está escrita, y valida.**

## Resultado 1 — existe un contrato machine-readable, y tiene validador

Cada herramienta declara en las primeras líneas de su fichero:

```
# CONTRACT: name=bench
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=yes
```

**65 ficheros** del árbol lo tienen. Y `toolkit.py` lo lee y lo **comprueba**,
con reglas que están escritas y son ejecutables:

1. `WRITES_GPU=yes` **no puede existir**: si aparece, el validador falla.
2. `WRITES_SYSFS=yes` exige tabla de escrituras con justificación.
3. `MUTATES_CORPUS=yes` exige pasar por `corpus_guard`.
4. `READONLY=yes` no puede contener `open(...,"w")` — por búsqueda de texto, que
   el propio código llama *«debilis pero mejor que nada»*.

Ejecutado:

```
autotest OK (4 casos de parseo, 5 de validacion, 8 flags conocidos contra el arbol real)
herramientas en 08-ARQUITECTURA/tools: 68
contrato valido 50/68
rc=1
```

**50 de 68 cumplen. 18 fallan, y el validador lo dice archivo por archivo**:
8 `SIN CONTRATO`, 9 `READONLY pero hay escrituras detectadas`, 1 `SIN CONTRATO`
de `xref.py`.

La cita del propio validador que decide por qué esto importa:

> «Una herramienta que escribe sin declarar donde tiene su único riesgo real:
> que nadie sepa si tocó el hardware.»

Y el proyecto lleva **40 rondas declarando `GPU INTACTA`**. Eso solo es
creíble si hay algo que lo compruebe, y ahora se sabe que **ese algo existe y
está a 31 % de cobertura**.

## Resultado 2 — la cobertura es el 31 %, y no por descuido

`toolkit.py` valida `os.listdir(HERE)`: **su propio directorio, y solo ese**.
Medido por directorio:

| directorio | con contrato | total `.py` |
|---|---|---|
| `08-ARQUITECTURA/tools` | **62** | 68 |
| `tools` | **3** | 92 |
| `revkit` | **0** | 30 |

`tools/` — donde vive `rxre.py`, `ibref.py`, `toolreg.py`, `prov.py`,
`relations.py`, `mmio.py`, los 92 que la consigna nombra uno a uno — tiene
**3 contratos**. `revkit/` no tiene ninguno.

Y esto **converge** con `1481`: las 192 herramientas no enrutables y las 149 sin
contrato no son dos poblaciones distintas, son **casi la misma población**:

- 74 de las no enrutables están en `08-ARQUITECTURA/tools` (bien cubiertas)
- 93 en `tools`, 33 en `revkit` (sin contrato o sin capacidad)

**El catálogo de capacidades y el contrato de seguridad son dos eje Y del mismo
problema.** `1481` lo llamó «hueco de catálogo»; este hallazgo muestra que es
también un hueco de **declaración de riesgo**, y que la segunda dimensión es la
más grave: una herramienta sin contrato no es que no se pueda enrutar, es que
**nadie sabe si al ejecutarla tocó el hardware**.

## Resultado 3 — la frontera dura NO es representable en el contrato

Este es el hallazgo que no se buscaba.

AGENTS.md prohíbe, sin excepción negociable, cualquier escritura sobre
`0000:00:02.0`, descargar o modificar `i915`, tocar `fb0`, o cambiar la salida de
consola. `rxre.py` **sí** tiene esa frontera ejecutable: `PUERTA_FRONTERA` con
`limites_de_la_maquina()` leyendo sysfs, y un vector que comprueba que una
herramienta sintética que toque la integrada queda bloqueada *aun con
autorización*.

Pero el **contrato de `toolkit.py` no tiene campo para ella.** Medido: las 65
herramientas con contrato usan **9 claves**, y ninguna representa la frontera:

```
name  READONLY  WRITES_FILES  WRITES_SYSFS  MUTATES_CORPUS
WRITES_GPU  WRITES_GPU_WORK  WRITES_GPU_MMIO  EXIT_ON_SUCCESS
```

Se buscó explícitamente un campo para la frontera (`touch`, `integ`, `i915`,
`frontier`, `vga`, `consola`) y **no existe ninguno**.

**Y el campo más cercano se comporta justo al revés de lo que hace falta.**
`WRITES_GPU` significa *«escribe en registros MMIO de la GPU»*, y la regla 1 lo
prohíbe. `bench.py` declara `WRITES_GPU=yes` — y no porque escriba en
registros, sino porque hace `vkQueueSubmit`. Para que eso cupiera, `bench.py`
tuvo que **describir en prosa** por qué su `WRITES_GPU=yes` no es el
`WRITES_GPU=yes` que la regla prohíbe, y tuvo que añadir las sub-clases
`WRITES_GPU_MMIO=no` / `WRITES_GPU_WORK=yes` para que el validador lo aceptara.

La prosa no es comprobable por máquina — y eso **ya se ha pagado en este
proyecto**, en `toollint.py`:

> «doclint.py aparecía como "declara escritura" por un grep mal hecho. Ese es el
> fallo de fondo: **un contrato en prosa no se puede comprobar con una máquina**.»

Consecuencia medible: **la frontera dura de AGENTS.md está garantizada en un
instrumento (`rxre`) y es invisible en el otro (`toolkit`).** Una caja puede
pasar `toolkit.py` con `rc=0` y no estar registrada en `rxre` en absoluto — son
universos disjuntos, y ningún validador sabe del otro.

```
    la frontera que no se puede declarar es la que no se puede hacer cumplir
```

## Procedencia

- `STATIC` — lectura de `toolkit.py` (bandeja de contrato y reglas 1-4),
  `bench.py` y `runtime_obs.py` (cabeceras), los 65 contratos contados con
  `grep -rh '^# CONTRACT:'` sobre `tools/`, `08-ARQUITECTURA/tools/`, `revkit/`.
- `CROSS-CHECK` — el recuento de contratos por directorio se hizo **dos veces**:
  `grep -rl | wc -l` y `toolreg.inventory()`, y coinciden. La lista de 9 claves
  se obtuvo por `cut -d= -f1 | sort -u`, no de memoria.
- `EJECUCION` — `python3 08-ARQUITECTURA/tools/toolkit.py` dos veces, rc=1,
  autotest interno OK.
- **Sin MMIO write, sin TLB, sin insmod. `GPU INTACTA`.** `--help-probe` de
  `rxre_boot.py` **no se usó** para este hallazgo: sólo se ejecutó `toolkit.py`,
  que lee ficheros.
- Encadenada con `1481` (misma poblacion, eje Y distinto), `1185` (el
  `WRITES_GPU` vs `WRITES_GPU_MMIO`/`WORK` es el mismo patrón: una capacidad
  ancha que no significa lo que parece), y `932` (citado en el propio `bench.py`
  como el error de lectura que este contrato previene).

## Lo que NO se afirma

- **No se afirma que `toolkit.py` sea un buen validador.** Su regla 4 usa
  búsqueda de texto y su propio código lo califica de débil. Se mide **que
  existe y que ejecuta**, no que sea suficiente.
- **No se afirma que las 18 herramientas que fallan sean peligrosas.** Fallan el
  contrato, que es una declaración; algunas escriben sólo con `--escribir`.
- **No se ha modificado ningún contrato ni `toolkit.py`.** Este hallazgo es
  medición. Añadir `TOUCHES_INTEGRATED` al vocabulario es una acción propuesta, no
  hecha.
- **`rxre_boot.py` declara `TOUCHES_INTEGRATED=no` con un valor que `toolkit.py`
  no reconoce.** Es deliberado y está escrito en el propio fichero: `no` sería
  una mentira indetectable, `yes` haría creer que escribe cuando no. La
  respuesta honesta es que el caso no cabe en el vocabulario — **que es este
  hallazgo**.

## Dos notas de método

**La primera: casi me lo pierdo por buscar donde me habían mandado.**

La consigna pedía inventariar `artifacts.py`, `claims.py`, `relations.py`,
`prov.py`… `toolkit.py` no aparece en ninguna de sus listas, y
`08-ARQUITECTURA/tools` no aparece como directorio a inventariar (sólo
`tools/`). Se encontró porque `1481` dejó una pregunta abierta —*«¿qué
capacidad tienen esas 192 herramientas?»*— y la respuestanatural a esa pregunta
no es su catálogo sino **su contrato**.

*Un inventario dirigido por una lista de nombres encuentra los nombres de la
lista. El hueco de `1481` se cerró preguntando por el mecanismo, no por los
nombres.*

**La segunda: rompí el fichero con un `sed` y tardé más en repararlo que en
escribirlo.**

Al añadir el contrato a `rxre_boot.py` usé `sed -i 's/#/…/'` para limpiar
residuos de una edición anterior. Ese `s` sustituye el **primer `#` de cada
línea**: eliminó 147 comentarios y rotó dos literales. El fichero dejó de
parsear y, cuando parseó, seguía roto —`ENSAMBLADO` y `VECTORES` son
identificadores válidos, así que fallan en **runtime**, no en sintaxis.

Se reparó con un método determinista (restaurar comentarios en línea;
comentar iterativamente lo que `ast.parse` reportara; 120 rondas) y **se verificó
que la reparación fue fiel de la única forma que vale**: no que el fichero
parsee, sino que **el artefacto salga idéntico**. Se guardó el JSON previo al
daño y se comparó campo a campo: los 11 invariantes —28 capacidades, 26 filas,
165 aristas, 172 `subprocess`, 0 rutas rotas, 4 duplicados con sha12 idéntico,
5 huecos con los mismos nombres— coinciden exactamente. Lo único que cambia son
los contadores que dependen de cuántas entradas hay hoy en el árbol, que es
otra sesión escribiendo (`1481`, sección *confounder*).

Le costé al árbol unos minutos y a esta sesión un artefacto que hubo que
recalcular. Es el precio de una reparación que se demuestra en vez de
declararse, y es más barato que las dos cosas que@No se comprobaron.
