# 1529 — `amdioread.py` tiene los dos nodos DRM invertidos, y su control negativo está invertido *y* nunca se ejecuta

```text
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 10:32 -03
TIPO=FACT + CONTRADICTION + ERROR (de ORIGEN FISICO, no de escritura)
ESTADO=PROVEN los dos hechos, por ejecución
ALCANCE=08-ARQUITECTURA/tools/amdioread.py.  SOLO LECTURA: ioctl
  AMDGPU_INFO_DEV_INFO, que escribe cero registros.  GPU INTACTA.
CAUSA=1521 (la iGPU desaparece del bus)  ->  este es su Radio de impacto
FRONTERA_DURA=NO se ha violado, y se dice por que en una seccion propia
```

## El hallazgo con más consecuencia de seguridad de la sesión

`1526` traités de los vectores inertes, `1527` de que el detector no los ve. Los
dos son defectos de validación. Este es un defecto que **apunta una protección
en la dirección contraria**, y aunque hoy no rompa nada, es el único de estos
cuatro que roza la frontera dura de AGENTS.md.

## Lo medido

```text
$ ls -la /dev/dri/
crw-rw----+ 1 video  226,   1 card1
crw-rw-rw- 1 render 226, 128 renderD128

$ readlink -f /sys/class/drm/renderD128
/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0/drm/renderD128
$ cat .../renderD128/device/uevent | grep PCI_ID
PCI_ID=1002:699F
```

**Solo hay un nodo de render, y es la RX 550.** `renderD129` no existe.

Y las constantes de la herramienta:

```python
68: RENDER_AMD   = "/dev/dri/renderD129"
69: RENDER_INTEL = "/dev/dri/renderD128"
```

| constante | lo que la herramienta cree | lo que es |
|---|---|---|
| `RENDER_AMD` | la RX 550 | **no existe** |
| `RENDER_INTEL` | la Intel | **`0000:01:00.0` = la RX 550** |

Las dos invertidas. Y su docstring afirma lo contrario con toda seguridad:

```text
- No abre /dev/dri/renderD128 a proposito. Ese es el Intel. Confundir los dos
  nodos es el mismo error que card0 con card1, documentado en
  HARDWARE-FINGERPRINT.md seccion 6, y aqui el fallo seria silencioso porque
  el ioctl de Intel devuelve algo y no un error.
```

El ioctl de Intel devuelve algo, sí. **Ese "algo" es la RX 550.**

## El control negativo, que está invertido dos veces

```python
if d:
    ...
    # control negativo: el mismo probe contra el nodo de Intel tiene que fallar
    di, ei = leer(RENDER_INTEL)
    c.append(("el nodo de la Intel no devuelve la RX 550",
              di is None or como_int(di.get("device_id")) != ESPERADO_DEVICE_ID,
              ...))
```

Dos defectos en cinco líneas.

**El primero: la afirmación es falsa sobre el nodo que abre.** El control asegura
que *«el nodo de la Intel no devuelve la RX 550»*, y el nodo que abre creyendo
Intel **es** la RX 550. Forzado a ejecutarse:

```text
  RENDER_INTEL = /dev/dri/renderD128
  leer(RENDER_INTEL) -> device_id = 0x699F
  ESPERADO_DEVICE_ID  = 27039          (= 0x699F)

  su veredicto sobre el nodo REAL: FALLA
```

Falla, y falla por la razón correcta: el nodo que la herramienta llama Intel
devuelve la RX 550.

**El segundo, y es el que lo esconde: está dentro de `if d:`**, y `d` es `None`
porque el nodo de la AMD no existe. **El control invertido nunca se ejecuta.**

```text
$ python3 08-ARQUITECTURA/tools/amdioread.py --self
    la cabecera uapi esta instalada                      OK  ok
    el probe lee el nodo de la AMD                       FALLA  open: No such file or directory
  1 de 2 pasan  <-- HAY FALLOS
rc=1
```

Dos vectores, ninguno sobre la inversión. El fallo que se reporta es un
`open:` genérico, que no dice *«estás mirando el nodo equivocado»* — y el
vector que sí lo diría está en la rama que no se toma.

> un control negativo que la falla previa salta es un control que no existe

## Por qué NO lo escribí yo: la causa es `1521`

Esto no es un error de escritura. Es la consecuencia directa del `TARGET_MISMATCH`
de `1521`.

Con la Intel presente, la enumeración PCI pone `00:02.0` antes que `01:00.0`, así
que los nodos de render se asignan **Intel → `renderD128`, AMD → `renderD129`**.
Las constantes eran **correctas**.

Cuando la Intel desaparece del bus —`1521`— queda una sola GPU, y se queda con
`renderD128`. Las constantes no se actualizaron porque **no hay nada que
actualizar: el cambio no es un cambio de índices, es la desaparición del
dispositivo que los fijaba.**

Por eso la reparación correcta **no es intercambiar las constantes**. Sería
volver a fijar la posición, y quedaría bien hasta el próximo cambio de hardware.

La reparación es **resolver por identidad PCI, no por índice**, que es
exactamente lo que dice el docstring de la otra herramienta:

```text
Y el dispositivo GPU NO se localiza por indice de bus: se busca por clase y por
identidad PCI. El indice 01:00.0 es una convencion de esta maquina, no una
propiedad del hardware, y hardcodearlo es exactamente el tipo de generalizacion
que este proyecto no quiere.
```

**El proyecto tiene dos convenciones opuestas para localizar la GPU, y la frágil
rompió cuando el hardware cambió.**

## El radio de impacto, medido

```text
19 ficheros tocan indices DRM; de ellos 8 dependen del indice y 11 resuelven por
identidad (con matiz: resolver la identidad a traves de un indice literal sigue
siendo depender del indice).
```

Los que dependen del índice: `revkit/gputel.py`,
`04-IMPLEMENTACION/c1_isolation_automator.py` (+ su test),
`04-IMPLEMENTACION/rx550-torneo` no, `tools/rxre.py`, y cuatro de
`01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/`.

**Y `amdioread.py` no está en `run_all.py`.** Su `rc=1` es invisible para el
corredor, que es el mismo hueco que `1526`. De aquí ya se sabe que su `rc` no lo ve nadie.

## Por qué NO se ha violado la frontera dura

AGENTS.md prohíbe escribir sobre `0000:00:02.0`, sobre i915, y *trabajar sobre
un nodo DRM que pertenezca a `0000:00:02.0`*. Lo que ocurrió aquí:

- **No se escribió nada.** El ioctl `AMDGPU_INFO_DEV_INFO` es una lectura, y el
  fichero lo documenta: *«AMDGPU_INFO_DEV_INFO se pide sin root y sin MMIO»*.
  Cero registros tocados. `GPU INTACTA`.
- **No se tocó la Intel**, porque no existe. El nodo abierto es la RX 550, que
  está bajo autorización explícita del propietario.
- **Lo que está mal es la ETIQUETA**, no el dispositivo. La herramienta cree
  estar midtermiendo una GPU que no ha tocado.

Dicho sin adornos: **no hubo violación**, y el riesgo es prospectivo. Si la
Intel vuelve, las constantes vuelven a ser correctas por casualidad, y la
herramienta parecerá estar bien sin que nadie haya comprobado por qué.

## Procedencia

- **Ejecución, no lectura**, para lo central: `leer(RENDER_INTEL)` ejecutado y su
  `device_id` leído (`0x699F`), y el control forzado a ejecutarse para ver su
  veredicto.
- `CROSS-CHECK` del nodo: por **tres vías independientes** — `readlink -f` del
  symlink de sysfs, `uevent`'s `PCI_ID`, y la salida del propio ioctl de la
  herramienta. Las tres dicen `0000:01:00.0` / `1002:699F`.
- `NEGATIVE_RESULT` de la frontera dura: **no hubo violación**, registrado como
  tal en vez de dejarse implícito.
- **Cero escrituras en hardware, cero cambios en ficheros.** Este turno es solo
  lectura y medición; `amdioread.py` está intacto.

## Lo que NO se ha hecho, y por qué

- **No he intercambiado las constantes.** Sería volver a fijar la posición.
- **No he arreglado el control negativo.** Su forma correcta no es invertir el
  signo: es no tener un control sobre un nodo cuya identidad no se ha
  establecido, sino resolver la identidad primero y después comprobar.
- **No he tocado los otros ocho ficheros** con índices. Son el mismo defecto
  latente, y arreglarlos todos en un turno sin medir cada uno es exactamente lo
  que `1527` acaba de documentar que no hay que hacer.
- **No he añadido `amdioread.py` a `run_all.py`.** Su fallo actual es real y
  añadirlo lo haría visible —que es el orden correcto—, pero el corredor ya
  tiene 12 vectores que no pueden fallar (`1526`), así que añadir otro no
  garantiza que nadie lo note. **Arreglar eso va primero.**

## La nota

Los tres hallazgos de esta racha (`1526` `1527` y este) salen de lo
mismo: **preguntar quién mira el resultado.** Nadie miraba el `rc` de
`fingerprint.py`; nadie miraba que `mutscore` no cubría el corredor; y el
`amdioread.py` tenía un self-test que pasa por los dos vectores que le importan
y falla por un `open:` que no nombra la causa.

Y el último matiz, que es el que más cuesta aceptar: **el defecto no lo escribió
nadie hoy.** Lo escribió la desaparición de una GPU, y ningún commit lo refleja
porque el hardware cambió sin que cambiara una línea del proyecto. Eso es lo
que significa que un proyecto mida su target: no para saber si el kernel es el
correcto, sino para saber **qué más dejó de ser verdad sin que nadie lo notara.**

> Si el fingerprint de `1524` hubiera tenido el eje `kernel` hace un mes, esto se
> habría visto antes de tocar un solo ioctl. Y si hubiera tenido un eje que
> dijera «la iGPU está presente», lo habría dicho hace un mes también. Ese
> segundo eje es el que falta.