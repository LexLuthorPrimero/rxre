# 1510 — La GPU integrada ha desaparecido del sistema, y el instrumento lo reportado en vez de inventarla. `tools/` pasa de 3 a 39 contratos

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 04:10 -03
TIPO=MEDICION + CAMBIO DE ESTADO DE MAQUINA + ACCION
ESTADO=PROVEN (que card0 no existe) / NOT_DETERMINED (por qué desapareció)
ALCANCE=/home/lucas/Escritorio/RX550-INVESTIGACION, SOLO LECTURA
MEDIDO=integrada ausente de /sys; 36 contratos nuevos en tools/
PRODUCER=RXRE/tools/rxre_frontier.py (22 vectores) · rxre_contracts.py (17)
COMANDO=ls /sys/class/drm/ · grep ^i915 /proc/modules · lspci -nn
ENCADENA=1507 (el instrumento mintía) · 1505 (revkit 0→30) · 1501 (la frontera
  era legible) · 1487 (el campo no existe)
```

## Resultado 1 — la integrada ya no está, y hay que decirlo primero

Midiendo `tools/` para declararlo, el instrumento devolvió `integrada: None`.
Verificado **por fuera**, no leyendo su veredicto:

```
$ ls /sys/class/drm/
card1  card1-DVI-D-1  card1-HDMI-A-1  renderD128  version
      <-- NO hay card0, NO hay renderD129

$ cat /sys/class/drm/card0/device/vendor
cat: /sys/class/drm/card0/device/vendor: No existe el fichero o el directorio

$ grep ^i915 /proc/modules
(nada)

$ lspci -nn | grep -iE 'vga|display|3d'
01:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI]
        Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X] [1002:699f] (rev c7)
        <-- UNA sola GPU. La Intel no esta.

$ cat /sys/class/drm/card1/device/{vendor,device}
0x1002
0x699f
```

**La Intel HD 4600 ha desaparecido del sistema.** `i915` no está cargado, su nodo
sysfs no existe, y la única GPU presente es la RX550.

**No fue esta sesión.** No he ejecutado nada con privilegio: ni `sudo`, ni
`insmod`, ni `rmmod`, ni `modprobe`, ni escritura en sysfs. Todo lo que hice fue
`ls`, `cat`, `grep`, `lspci` y `python3`. Y AGENTS.md prohíbe precisamente eso:
tocar `i915` o el estado de la Intel. **Cumplí la frontera, y aun así la
integrada no está** — lo que significa que el cambio viene de fuera del árbol.

**Por qué: `NOT_DETERMINED`, y no se especula.** `dmesg` está restringido, así
que no se puede leer si hubo un `rmmod`, un apagado de la iGPU en BIOS/UEFI, o
un cambio de sesión. Hay tres hipótesis y **ninguna medida**.

### Y esto tiene una consecuencia que no es el Findings

AGENTS.md define la frontera dura como «cualquier escritura sobre
`0000:00:02.0`». **Ese dispositivo ya no está en esta máquina.** La frontera
sigue siendo una prohibición correcta, pero **hoy es vacía de objeto**: no hay
nada que no se pueda tocar porque no está.

El instrumento **no fingió lo contrario**. Devolvió `integrada: None` con su
motivo — *«la frontera NO se puede resolver y no se sustituye por una
suposición»* — en vez de quedarse con el `0x8086:0x0412` de las rondas
anteriores, que era lo que habría hecho un instrumento que recordara en vez de
leer.

> un instrumento que recuerda el estado de la máquina no mide la máquina

## Resultado 2 — dos vectores reescritos, y por qué no es relajarlos

Uno decía *«la identidad de la integrada SE RESUELVE en esta maquina»*, y lo
escribí en `1501` para cazar el error de `RAIZ`. Falló, y **el fallo es del
vector**:

> un vector que depende de que la máquina conserve una característica no mide
> el código: **mide el día**

Mezclaba dos cosas: que el instrumento funciona, y que esta máquina tiene una
Intel. Se reescribió para medir lo que sí es del código —que la identidad
**discreta** se resuelve, y sale del mismo sysfs que la otra. Si el instrumento
no pudiera leer sysfs, las dos serían `None` y el vector caería igual.

El segundo comparaba las claves de las dos ramas del informe, y restaba
`motivo` **sólo de un lado**:

> restar de un lado no es restar: es desplazar

Cuando la máquina cambió, **las dos** ramas cayeron en `NO_RESUELTO`, las dos
tenían `motivo`, y la resta lo dejaba en una sola. Ahora se compara lo común a
las dos.

Y apareció un fallo **real** en el camino: con la integrada ausente, el informe
no creaba `herramientas_que_la_nombran` ni `detalle`, y `--selftest` terminaba
en `KeyError` **justo cuando la máquina había cambiado** — que es el caso en el
que un instrumento tiene que funcionar mejor, no peor. Las dos ramas llevan ahora
las mismas claves, y hay un vector que lo comprueba.

**22 de 22 PASS.**

## Resultado 3 — `tools/`: de 3 a 39 contratos

Antes de declarar los 36 nuevos, encontré un defecto más en el criterio, y es el
segundo en el mismo eje con el signo **contrario** al de `1505`:

**La regla era demasiado débil.** `TEMPORAL_POR_TEMPFILE` clasificaba como
temporal cualquier escritura de un fichero que usara `tempfile` en *algún
sitio*. Es una inferencia sobre el **fichero**, no una observación de la
escritura. Verificado sobre `tools/pm4ops.py`: sus 16 escrituras **están** dentro
de `with tempfile.TemporaryDirectory(...)`, así que la clasificación era
correcta — **por un motivo que no la sostiene**.

> llegar a la verdad por una vía inválida no es medir: es la misma vía que llega
> a la mentira, sin dejar rastro

Se cambió por la regla del bloque: se recogen los rangos de línea de los `with`
cuyo contexto es `tempfile`, y una escritura es temporal sólo si cae dentro.

**Y esa regla resultó demasiado estrecha**, y produjo el error opuesto:
`tools/mmio.py`, `tools/layoutcross.py` y `tools/ibref.py` salieron
`FUERA_DE_TEMPORAL`. Sus escrituras son `with open(os.path.join(dt, ...))` donde
`dt = tempfile.mkdtemp(...)` **sin `with`**. Los tres son temporales de verdad, y
la regla nueva los declaraba lo contrario.

> una regla más estrecha no es una regla mejor: es otra regla

La segunda regla sí es observable y era la que faltaba: el **destino** de la
escritura menciona una variable a la que se asignó un `mkdtemp`. Se comprueba
sobre el nodo del destino, no sobre el fichero entero.

**Y el filtro no se disparaba ni una vez** sobre 192 herramientas. El patrón era
`"'id': '%s'"` y `ast.dump` escribe `id='dt'`, **sin comillas en la clave**:

> un filtro que nunca casa no es un filtro: es un error de dedo

Podía haberse leído como «el criterio no sirve». No servía el patrón; la regla
era correcta y no llegó a ejecutarse.

**Y ahí paro.** `tools/ibref.py` sigue sin resolverse: su destino es `cstub`, una
variable **más** de indirección (`cstub = os.path.join(tmp, ...)`). Un solo caso
no justifica una tercera regla (§40), así que queda `NO_DETERMINED` — y su
declaración de `1491`, verificada a mano, sigue en pie.

### Clases resultantes sobre 192 herramientas

```
TEMPORAL_EN_BLOQUE                    114   dentro de `with tempfile...`
FUERA_DE_TEMPORAL_PERO_USA_TEMPFILE    71   el fichero usa tempfile, la escritura no
DESCONOCIDO                            70   destino irresoluble, sin tempfile
TEMPORAL_POR_DESTINO                   20   el destino nombra la var de un mkdtemp
```

**37 declarables** como `READONLY=yes / WRITES_FILES=no` (36 nuevos + `mmio.py`).
Los 36 se declararon. Verificado por los dos caminos: los recuentos cuadran con
el detalle, y el detalle cuadra con las clases por fichero.

**Antes de escribir 36 bloques verifiqué tres a mano** — `contradict.py` L338,
`pm4ops.py` L1207, `prov.py` — porque hoy ya había encontrado un error de
clasificación y no iba a confiar en 36 fichas sin mirar ninguna.

`tools/`: **39 contratos de 93**. Los restantes son `NO_DETERMINED`, y su saldo
está en `resumen`: 58 `SIN_DECLARAR` en total del árbol, 45 pueden escribir
delegando.

## Procedencia

- `CROSS-CHECK` — la ausencia de `card0` se verificó por **cinco vías
  independientes**: `ls`, `cat`, `/proc/modules`, `lspci -nn`, y el propio
  instrumento. Ninguna lee el valor de otra.
- `EJECUCION` — 12 selftests de `tools/` tras el cambio: `mmio` 48 vectores,
  `layoutcross` 79, `claims` 21, `relations` 27, `toolreg` rc=0, `xref`,
  `dwarfx`, `reg_resolve`, `reg_census`, `trace_path` rc=0. `prov.py` necesita
  `--self-test` (con guion), no `--selftest`: rc=0.
- **93 de 93 ficheros de `tools/` parsean** tras los 36 contratos.
- **Sin MMIO, sin TLB, sin insmod. `GPU INTACTA`** — y ahora además sin integrada
  que tocar.
- **0 líneas de código** en los 36 contratos: `git diff` sobre `tools/` mezcla
  cambios de la otra sesión (`0x1537`, nodo `FILTROS-REPARO-2`), así que la
  verificación es bloque a bloque, y los 36 llevan exactamente 7 campos
  `CONTRACT:`.

## Lo que NO se afirma

- **No se afirma por qué desapareció la integrada.** Es `NOT_DETERMINED`. Tres
  hipótesis —`rmmod` externo, ajuste de BIOS/UEFI, otro agente— y ninguna medida.
  `dmesg` está restringido.
- **No se afirma que 39 contratos en `tools/` sean correctos.** 17 de `revkit`
  y varias de `tools/` son `indeterminado`/`NO_DETERMINED` por diseño.
- **No se ha añadido `TOUCHES_INTEGRATED` al vocabulario de `toolkit.py`.** 9
  ficheros lo declaran y ese validador sigue sin saber qué hacer con él.
- **La caída de `COINCIDE` de 44 a 40 no fue una corrección de contratos**: fue
  la regla temporal estrecha retirando 4 `NO_DETERMINED` mal clasificados, y la
  regla del destino recuperándolos. El saldo final (40) es menor porque hay más
  herramientas **mal o incompletamente** clasificadas que antes, no porque se
  haya perdido exactitud.

## Dos notas de método

**La primera: un instrumento tiene que funcionar peor cuando la máquina cambia.**

`rxre_frontier` dio `KeyError` cuando la integrada desapareció. No en la lógica
de la frontera —que degradationó correctamente— sino en el resumen, que leia
claves que la rama `NO_RESUELTO` no creaba. Un instrumento que funciona con la
máquina de hoy y revienta con la de mañana no mide la máquina: **mide una
configuración**.

Se añadió el vector que exige que **las dos ramas tengan las mismas claves**, y
ese vector sí habría atrapado el `KeyError` antes de que se ejecutara.

**La segunda: tres reglas para la misma pregunta, y paré en la tercera.**

`temporary_porque_el_fichero_usa_tempfile` → `dentro_de_un_with` →
`el_destino_nombra_la_variable`. Tres criterios para la misma pregunta de si una
escritura es temporal. El primero daba la respuesta correcta por la razón
equivocada; el segundo, la contraria; el tercero, la correcta por la razón
correcta.

Podía haber añadido una cuarta para `ibref.py` —una variable más de
indirección— y habría closes todos los `NO_DETERMINED` del árbol. **No se hizo**,
porque un solo caso no es un patrón (§40) y porque un resolutor de flujo de datos
ya es otro instrumento, no un criterion más.

> generalizar con un caso es adivinar con mejores modales
