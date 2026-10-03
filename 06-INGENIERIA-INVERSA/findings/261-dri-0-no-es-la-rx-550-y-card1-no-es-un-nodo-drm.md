# 261 · `dri/0` no es la RX 550, y `card1` no es un nodo DRM

```
CLASSIFICATION=MEASUREMENT+ERROR+CORRECTION+TOOLING · TRACK=VERIFICATION
CORPUS=NINGUNO (todo del HOST) · HARDWARE_SCOPE=READ_ONLY
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=READ_ONLY (sysfs) · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`258` encontró que la RX 550 es `card1` y que `herramientas.md` mandaba leer sus
registros en `dri/0`, que es la Intel. Eso parecía un fallo de una línea.

**No lo era.** Es una clase de error con 23 apariciones en el proyecto, y encima
el patrón "obvio" para buscarla —`card1`— no sirve: `card1` aparece 537 veces y
casi ninguna es un nodo DRM.

## 1 · El recuento que parece obvio está mal

```
  card1   537 apariciones      <-- NO son nodos DRM
  card0    75
  cardN    73                  <-- notacion generica
  GPU_CARD_NODE  34
  card_clients  61             <-- interno de amdgpu

  dri/0     24                 <-- esto si
  dri/1     22                 <-- esto si
  dri/0000:01:00.0  15
  dri/129   10                 <-- MINOR de render, otra cosa
```

En este proyecto `card1` es sobre todo un **registro del ASIC** — `VM_CARD1`,
`MC_CARD1`, `GPU_CARD_NODE` — y `cardN` es la notación genérica. Un buscador de
`cardN` reporta seiscientos falsos positivos y esconde los veintitrés que sí
importan.

```
  un nombre que se busca aparece tambien en el sitio que explica por que se
  busca. Por eso VM_CARD1 no se busca, y por eso diriroute.py se excluye a si
  mismo: sus dos apariciones de "dri/0" son la EXPLICACION del error.
```

## 2 · La medición, hecha cada vez que se ejecuta

```
  /sys/class/drm/card1/device -> vendor 0x1002 device 0x699f   amdgpu
  /sys/class/drm/card0/device -> vendor 0x8086 device 0x0412   i915

  por tanto  /sys/kernel/debug/dri/1/  es la AMD
             /sys/kernel/debug/dri/0/  es la integrada
```

La herramienta **mide** el índice en cada ejecución y **no lo guarda**. Un índice
guardado es exactamente el error que hay que cazar: el día que cambie el orden de
probe, un valor almacenado sigue diciendo lo mismo y con la misma seguridad.

Y se identifica la AMD por **device id**, no por "la segunda GPU que salga": el
orden de enumeración es justo lo que este hallazgo demuestra que no es un
criterio.

## 3 · El estado real, por clase

```
  AMD_BDF_ROBUSTO   15   dri/0000:01:00.0   no cambia con el probe
  AMD_CORRECTO      22   dri/1
  INTEL_INCORRECTO  17   dri/0
```

De los 17 que apuntan a la Intel: **14 en hallazgos** y **3 en documentos que
registran lo observado**.

## 4 · La corrección, y por qué solo se corrigió una parte

```
  SE CORRIGE, porque es una INSTRUCCION hacia delante
    08-ARQUITECTURA/tools/runtime_obs.py:19
    03-EXPERIMENTOS/.../EXP-F3-A-BANDWIDTH-REAL.md:24,25
    docs/OPEN-FRONTIERS.md:71,79,80

  SE DEJA, porque es un REGISTRO de lo observado
    docs/CURRENT-STATE.md:459     "dri/0 no existe. Es EACCES"
    docs/NEGATIVE-RESULTS.md:965  "anote que dri/0 no existe, porque stat..."
    docs/CHANGELOG-RESEARCH.md:2302   recuento de lo que quedo anotado
```

La distinción es la de siempre y aquí **decide**:

```
  una instruccion dice "usa esta ruta"        -> si la ruta es la de otra GPU,
                                                  se corrige
  un registro dice "accede a esta ruta y vio esto" -> lo que se ACCEDIO importa,
                                                  no la ruta; cambiar el texto
                                                  fabricaria la observacion
```

`CURRENT-STATE.md:459` documenta que `dri/0` dio `EACCES`. Eso es cierto y lo
sigue siendo. Cambiar el `0` por un `1` no corrige nada: convierte un registro de
un acceso en otro acceso que nunca ocurrió.

## 5 · La incoherencia interna que lo hizo evidente

El fichero que mejor lo demuestra es el propio `runtime_obs.py`:

```
  L16   /sys/class/drm/card1/device/uevent    LEGIBLE   (y es la AMD)   <- correcto
  L19   /sys/kernel/debug/dri/0/...            NO        (debugfs...)   <- la Intel
```

**El mismo fichero decía las dos cosas.** No era un error de conocimiento del
proyecto: era un fichero que se contradecía a sí mismo, y eso se ve en dos líneas
contiguas.

## 6 · Los cuatro errores de `driroute.py` al salir por primera vez

```
  1  tres vectores fallaron a la vez porque las cadenas de prueba eran "dri/129"
     sin barra inicial y los tres patrones exigen "/dri/". Los patrones estaban
     bien: los vectores MENTIAN sobre lo que comprobaban.

  2  el regex del indice llevaba (?<!\\d), un lookBEHIND, donde hacia falta
     (?=\\d). Tras \\d+ el caracter anterior es siempre un digito, y el lookbehind
     es falso SIEMPRE: el patron no casaba con nada. Con \\\\d+ y el limite de una o
     dos cifras, el indice de card, el minor de render y la BDF quedan separados
     por construccion y no por un filtro posterior.

  3  se contaba a si mismo: sus dos apariciones de "dri/0" son la explicacion del
     error. Un escaner que no se excluye reporta sus propios ejemplos.

  4  un except que faltaba, que hacia el fichero no compilar.
```

Los cuatro tienen vector o son de compilación. El del lookbehind es el que más
enseña: **un patrón que nunca casa no da ningún error**, da cero resultados, y
cero resultados se parece a "no hay ninguno".

## 7 · Lo que NO se establece

```
  el contenido real de /sys/kernel/debug/dri/1/   BLOCKED_BY_PERMISSION: debugfs
    no esta montado y no se monta. Lo que se corrige es el NOMBRE de la ruta;
    que amdgpu_vm_info exista ahi NO esta comprobado, y sigue en la lista de
    pendientes con la ruta ya correcta
  si el orden de probe puede cambiar en otra kernel
    es una afirmacion sobre el kernel, no medida aqui. Lo medido es que en ESTE
    arranque la integrada salio antes
  los 14 hallazgos con dri/0                  NO se corrigen, y el motivo esta
    arriba y no es que no se pueda
```

## 8 · Trazabilidad

```
  tools/driroute.py                  la herramienta, 10 comprobaciones, --json
  /sys/class/drm/card{0,1}/device/   quien es quien, medido
  08-ARQUITECTURA/tools/runtime_obs.py    corregido, con la incoherencia anotada
  03-EXPERIMENTOS/.../EXP-F3-...         2 rutas de instruccion corregidas
  docs/OPEN-FRONTIERS.md                  3 rutas pendientes corregidas
  herramientas.md                         3 rutas, corregidas en 258
  findings/258                            el descubrimiento
```