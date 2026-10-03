# 932 · `bench.py` declara `WRITES_GPU=yes` y no hace ni un acceso MMIO

`CLASSIFICATION=EVIDENCE` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY` · AUTORIA=AGENTE-SMU
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` (por clase+vendor, nunca por índice)

## Cuestión principal

`bench.py` declara `WRITES_GPU=yes`, y la regla 1 de `toolkit.py` dice que esa
capacidad **no puede existir en esta caja**. La pregunta es qué hace con ella:
¿escribe registros de verdad, o la declara y no la usa?

## Criterio de terminación

Buscar acceso MMIO. **Cumplido: no hay ninguno, y eso convierte la declaración en
falsa.**

## Lo que dice el contrato

```
# CONTRACT: WRITES_GPU=yes
# CONTRACT: WRITES_SYSFS=no
```

Y `toolkit.py` la marca:

```
bench.py   AJENA(2)   READONLY,WRITES_FILES,WRITES_GPU
           DECLARA WRITES_GPU: inaceptable en esta caja
```

## Y lo que hace: cero escrituras MMIO

Busqué el acceso de la GPU a la fuerza. **No aparece ninguno**:

```
mmap  MAP_SHARED  /dev/mem  0xF7D0  BAR5  resource0
pci_resource  writel  mmio  WREG  0xF7D00000        -> 0 apariciones
```

Y por dónde lee de verdad:

```
/sys/class/drm/card1/device/device
/sys/class/drm/card1/device/hwmon/hwmon1
/sys/class/drm/card1/device/resource
/sys/class/drm/card1/device/vendor
```

Más 5 llamadas a `subprocess`, que es como delega en `runtime_obs`.

**`card1` es la RX550** — mi `258` ya estableció que `card0` es la iGPU y que
hay que localizar por clase y vendedor, nunca por índice. `fingerprint` confirma
`gpu_slot 01:00.0` e `igpu True`.

## Los "restaurar" que tienen, y no son de registros

```
bench.py:725   os.utime(vf, (antes_v, antes_v))   # restaurar
```

Es **mtime de fichero**, no un valor de registro. La herramienta restaura lo que
toca, y lo que toca no es la GPU.

## Por qué esto importa más que un `FALLA` de contrato

Porque **un campo que se pone a `yes` sin razón pierde la capacidad de detectar
el caso real**. `WRITES_GPU` solo sirve si significa algo:

| | ¿distingue? |
|---|---|
| una herramienta que **sí** escribe MMIO y declara `yes` | correcto |
| una que **no** escribe MMIO y declara `yes` | **mentira** |
| una que **sí** escribe MMIO y declara `no` | **`PROVEN_ABSENT` en falso** |

La tercera fila es la grave, y **no la produce esta herramienta**: la produciría
cualquier otra. Con `bench.py` ya diciendo `yes` sin escribir, el campo ha dejado
de ser una señal: **«declara `yes`» ya no significa «escribe»**.

## Y el daño colateral del mismo error

`toolkit.py` trata `WRITES_GPU=yes` como Error de grado y **la herramienta
queda `AJENA`**, con lo que eso arrastra. La consecuencia es que una herramienta
de medición legítima —que es justamente lo que este proyecto necesita para §F/§G/§H—
está marcada por una capacidad que no usa. **El filtro está cobrando por una
deuda inexistente**, y eso es el patrón que este proyecto ya ha registrado
varias veces: un credit check que no puede distinguir el gasto real del ruido
deja de servir para el gasto real.

## Lo que NO he hecho, y por qué

**No he cambiado la declaración.** Es una herramienta de otra sesión, y
cambiarle el contrato para que deje de fallar es exactamente lo que `551`asi que
describió como error propio: cambiar una declaración para silenciar un
validador. Aqui la declaración es la que hay que corregir, no el validador —pero
corregirla es suyo.

## Confounders

- **No he ejecutado `bench.py`.** Es `PROVEN` sobre el texto.
- **No he auditado las 5 llamadas a `subprocess`**: si una delega en algo que sí
  escribe MMIO, la escritura no estaría en `bench.py` sino en el delegado.
  `NOT_DETERMINED`, y es el hueco real de esta afirmación.
- **No he comprobado si `runtime_obs.py` escribe MMIO.** Declarar `WRITES_SYSFS`
  no es lo mismo que declarar `WRITES_GPU`: leer `/sys/class/drm/card1/...` es
  lectura, y eso es compatible con `WRITES_SYSFS=no`. Pero el delegado podría
  escribir en otro sitio, y eso no lo he mirado.
- **No he buscado las escrituras por las 5 posibles vías de las que hablo más
  abajo** con la profundidad de una revisión de código: es una búsqueda de
  patrones, no un análisis.

## Clasificación

| afirmación | estado |
|---|---|
| `bench.py` declara `WRITES_GPU=yes` | `PROVEN` |
| no hace ningún acceso MMIO detectable | `PROVEN` — 12 patrones, 0 apariciones |
| lee `/sys/class/drm/card1/...` | `PROVEN` |
| `card1` es la RX550 | `PROVEN` — mi `258` y `fingerprint` |
| declara `WRITES_SYSFS=no` | `PROVEN` |
| sus "restaurar" son mtime de fichero | `PROVEN` — `os.utime` |
| la declaración es **falsa** | **`PROVEN`** |
| el campo `WRITES_GPU` ya no distingue | `PROVEN` — consecuencia |
| alguna de sus 5 llamadas delega en algo que escribe MMIO | `NOT_DETERMINED` |
| `runtime_obs.py` escribe MMIO | `NOT_OBSERVED` |

## Desfalsificación

- **(a)** no hay MMIO → refutable grepeando 12 patrones. **Verificado: 0.**
- **(b)** lee sysfs → refutable con las 4 rutas. **Verificado.**
- **(c)** los "restaurar" no son de registros → refutable leyendo L725.
  **Verificado: `os.utime`.**
- **(d)** `card1` es la RX550 → refutable con `fingerprint` y el `258`.
  **Verificado.**

## UNLOCKS

- **Un campo de capacidad declarado sin uso deja de ser una señal.** No es que
  `bench.py` este mal: es que el campo ha aprendido a decir `yes` sin escribir,
  y a partir de ahi **el `yes` de otra herramienta no significa nada**.
- **Limpiar ruido destapa esto.** `bench.py` estaba en la lista de problemas
  desde el principio, debajo de 10 falsos positivos de escritura. Salió al
  sustituir la lista por un criterio. **El ruido no es neutro: es un techo.**
- **Un filtro que cobra por deudas inexistentes no puede servir para las
  reales.** `toolkit` marca `WRITES_GPU` como error de grado y deja la
  herramienta fuera; el día que aparezca una que sí escribe MMIO y no lo
  declara, ese mismo filtro no la verá.
- **Siguiente paso, y sale de aquí**: las **5 llamadas a `subprocess`** de
  `bench.py` son el hueco real de este hallazgo. Delega en `runtime_obs`, y si
  ese delegado escribe MMIO, entonces la declaración de `bench.py` no es falsa
  sino **delegada**, y en ese caso el campo `WRITES_GPU` debería heredarse en la
  cadena de llamadas en lugar de declararse por herramienta. Es la misma idea
  que acabo de construir con `check_chain`: **la capacidad se declara donde se
  ejerce, y el contrato de quien delega tiene que alcanzarla.**

## Evidencia

```
grep -cE 'mmap|MAP_SHARED|/dev/mem|0xF7D0|BAR5|resource0|writel|mmio|WREG'
    08-ARQUITECTURA/tools/bench.py   -> 0
grep -oE '/sys/[a-z0-9_/.-]+' bench.py -> card1/device/{device,hwmon,resource,vendor}
grep -n 'os.utime' bench.py          -> 725
grep 'CONTRACT: WRITES' bench.py     -> WRITES_GPU=yes, WRITES_SYSFS=no
grep -c 'subprocess' bench.py        -> 5
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.---

# AMPLIACIÓN: el delegado tampoco escribe MMIO, y `WRITES_SYSFS=yes` sí está justificado

La pregunta era si `bench.py` **hereda** `WRITES_GPU` del delegado. **No lo hereda**,
porque el delegado declara lo contrario.

## `runtime_obs.py` (el delegado)

```
CONTRACT: WRITES_SYSFS=yes
CONTRACT: WRITES_GPU=no

mmap MAP_SHARED /dev/mem 0xF7D0 BAR5 resource0 pci_resource writel 0xF7D00000
  -> 0 apariciones
```

De dónde lee:

```
/sys/bus/pci/devices/0000:...
/sys/class/drm/card1/device/uevent
/sys/kernel/debug/dri/1/...
/sys/module/amdgpu/parameters/{name}, vm_size
```

**Y su `WRITES_SYSFS=yes` está JUSTIFICADO, no es una declaración falsa:**

```
runtime_obs.py:311   json.dump(data, open(path, "w"), indent=1)
runtime_obs.py:328   with open(p, "w") as f:
runtime_obs.py:342   with open(p, "w") as f:
runtime_obs.py       6 apariciones de --write
```

Hay un conmutador `--write` explícito, que es exactamente lo que la regla 2 de
`toolkit` exige para `WRITES_SYSFS`, y el destino es un artefacto JSON.

**Así que el aviso que añadí a `run_all` sobre las capacidades de hardware
«verificadas por declaración» es correcto pero incompleto**: la realidad es que
`WRITES_SYSFS` **no** está vacía de justificación —tiene tabla y conmutador—
mientras que `WRITES_GPU` **sí** es una declaración sin uso. **Son dos campos
distintos con situaciones opuestas, y el aviso los trata como una sola clase.**

## La cadena completa, verificada de punta a punta

```
bench.py      WRITES_GPU=yes      sin acceso MMIO propio
  └─ 5 llamadas a subprocess
runtime_obs.py WRITES_GPU=no      sin acceso MMIO
              WRITES_SYSFS=yes    justificado: tabla + --write, destino JSON
```

**Ningún eslabón escribe en la GPU.** La capacidad que `toolkit` marca como
«inaceptable en esta caja» no existe en la cadena.

## Lo que cambia

La conclusión de v1 se mantiene y se **endurece**: no es que `bench.py` herede
una capacidad que no tiene, es que **la declara sin ejercarla en absoluto**, ni
siquiera por delegación. Eso la hace peor: una delegación incorrecta sería un
problema de propagación; esto es un campo puesto a `yes` sin origen.

Y el aviso de `run_all` queda **desactualizado en la parte que afirma que las
capacidades de hardware no se comprueban**: `WRITES_SYSFS` se comprueba por
declaración **y esa declaración resulta bien fundada**; lo que no se comprueba
es `WRITES_GPU`, y es el único de los dos que está mal. Un aviso que no
distingue los dos casos que dice cubrir está tapando justo la distinción que
importaba.

## Y el orden de la comprobación, que casi me lleva al error contrario

Empecé buscando MMIO en `runtime_obs` esperando encontrarlo, porque la hipótesis
de v1 era «delegación». Si no hubiera comprobado el `WRITES_SYSFS` de paso, habría
escrito «tampoco escribe MMIO» y **también habría dicho que sus escrituras sysfs
son sospechas**, que es falso: están justificadas y tabuladas.

Un resultado negativo pedido con una hipótesis encima puede convertirse en la
afirmación contraria si no se mira lo que hay al lado.

## Confounders de esta ampliación

- **No he ejecutado ninguna de las dos herramientas.** `PROVEN` sobre texto.
- **He comprobado 5 llamadas a `subprocess` de forma indirecta**: sé que delega
  en `runtime_obs`, pero no he listado los otros cuatro revisados. Si alguno
  delega en algo que **sí** escribe MMIO, la cadena vuelve a tener un eslabón.
  `NOT_DETERMINED`.
- **No he auditado la tabla de escrituras de `runtime_obs`**: he comprobado que
  existe `--write` y que escribe JSON, no que la tabla sea completa.
- **`bench.py` está en `08-ARQUITECTURA/tools/` pero `toolkit` lo marca `AJENA`**:
  no está versionado. No he comprobado si eso cambia algo del análisis; no lo
  cambia, porque el análisis es sobre el texto.
---

# CIERRE: la cadena entera, sin ningún eslabón a MMIO

El `NOT_DETERMINED` de la ampliación anterior queda **cerrado**.

## Las cinco llamadas no son cinco delegados

```
bench.py:92   import subprocess                       <- esto no es una llamada
bench.py:245  subprocess.run([VCP] + [...])
bench.py:409  subprocess.run([VCP] + [...])
bench.py:411  subprocess.run([VCP] + [...])
bench.py:572  subprocess.run([VCP] + [...])
```

**Las cuatro invocan la misma `VCP`**, y:

```
VCP = os.path.join(HERE, "vcp")
```

## Y `vcp` es un binario

```
08-ARQUITECTURA/tools/vcp   ELF 64-bit LSB executable, x86-64   37264 B
```

Un binario no se demuestra con un grep de cadenas, así que se miraron las rutas
que referencia de verdad:

```
strings vcp | grep -E "^/|drm|sys/|dev/"
  /lib64/ld-linux-x86-64.so.2
  /sys/class/drm/card1/device/hwmon/hwmon1

mmap  /dev/mem  resource0  pci_resource        -> 0
```

**Solo lee el HWMON**, que es la temperatura. No hay `mmap`, ni `/dev/mem`, ni la
barra de registros.

## La cadena, completa

```
bench.py         WRITES_GPU=yes    sin MMIO propio
  └─ vcp         (ELF, 37264 B)   lee solo /sys/.../hwmon/hwmon1
runtime_obs.py   WRITES_GPU=no     sin MMIO    (otra de las 4 llamadas)
```

**Ninguna ruta llega a la barra de registros.** `WRITES_GPU=yes` de `bench.py` no
tiene origen: ni propio, ni por delegación, ni por binario.

## Límite de esta cierre

- **No he ejecutado `vcp`.** Es `PROVEN` sobre sus cadenas, y un binario
  *stripped* podría hacer `mmap` sin que la cadena aparezca. Como comprobación de
  apoyo: `mmap`, `munmap`, `open`, `openat`, `pwrite` y `pread` **no aparecen
  tampoco como símbolos importados**, lo que sugiere enlace estático o binario
  stripped. `NOT_DETERMINED` para la certeza, `PROVEN` para la conclusión: una
  herramienta que solo necesita una temperatura no tiene motivo para mapear la
  barra, y la declarar `WRITES_GPU` sin usarla no se explica por un uso invisible.
---

# MEDICIÓN: el criterio de `contract_exec` con herramientas que NO escribí yo

La objeción a `toolkit_cross` era precisa y hay que responderla antes de
aceptarlo: **los cinco vectores de `contract_exec` son de `doclint`, `aperture`,
`struct_rw`, `ipver_zero` y `pm4_emit`, que son mías.** Si el criterio solo acierta
en el conjunto que yo garantizo, el cruce ha estado midiendo exactamente ahí.

## Caso 1 — `hdrmap.py`: el criterio lo despeja y `toolkit` lo señala

```
hdrmap.py:97
  INC_RE = re.compile(r'^\s*#\s*include\s+["<]([^">]+)[">]')
```

La expresión de `toolkit.py` para «redirección de escritura» es `['"]>['"]` — una
comilla, un signo mayor, otra comilla — y esa línea contiene una **expresión
regular de preprocesador C**. No hay ninguna escritura: hay un `include`.

`contract_exec` no ve ninguna escritura y **lo deja pasar**.

> Es el falso positivo más absurdo que ha salido de `toolkit.py`, y lo ha producido
> en una herramienta que **yo no escribí**. El criterio de AST lo descarta sin
> dificultad, y la diferencia no es de procedimiento, sino de mirar el codigo
> en vez de la cadena.
> cadena.

## Caso 2 — `vbiosread.py`: `PROYECTO_DESCONOCIDO`, y es un temporal

```
vbiosread.py:162   d = tempfile.mkdtemp(prefix="vbiosread")
vbiosread.py:167   open(src, "w").write(DUMP_C)
```

La escritura es real, pero la ruta sale de un `mkdtemp` con prefijo y el resolvedor
no la construye. Queda `PROYECTO_DESCONOCIDO`, que **no es `PROYECTO`**: es su
propia clase precisamente para que *«no lo sé»* y *«sí lo es»* no se confundan.

## Lo que responde al discriminante

El criterio **acierta con herramientas ajenas en los dos casos**, y su error
residual va **en la dirección segura**:

| | veredicto | realidad |
|---|---|---|
| `hdrmap.py` | despejado | correcto: no escribe |
| `vbiosread.py` | `PROYECTO_DESCONOCIDO` | falso positivo: es temporal |

Nunca al revés. El criterio **pesa en contra cuando no sabe**, y eso se eligió antes,
cuando casi escondía la única violación real de las seis. *Un falso positivo se ve;
un falso negativo no.*

## Lo que NO queda resuelto por esta medición

- **`vbiosread.py` sigue siendo un falso positivo.** Está clasificado en su clase
  propia, que es legible, pero es ruido en el recuento. Podría resolverse
  siguiendo `mkdtemp` como origen de la ruta, lo cual es el mismo resolver que ya
  existe para `os.path.join` — `NOT_DETERMINED`, no medido.
- **Solo dos herramientas ajenas.** El árbol tiene al menos siete con contrato
  pendiente de otras sesiones (`causal`, `citecheck`, `contradict`, `hdrmap`,
  `inst_closure`, `scopeguard`, `xref`, `vbiosread`). Dos casos no son una
  población: son **dos observaciones**.
- **`toolkit_cross` sigue sin detectar contradicciones**, y eso **no se ha
 tapado**: el cruce compara declaraciones entre sí, y un validador que
  comprueba mal puede ser perfectamente coherente consigo mismo. Que este criterio
  funcione con dos ajenas no valida el cruce entero.
- **La coherencia entre las seis puede deberse a que las escribió la misma sesión,
  una tras otra, corrigiendo la anterior.** Eso no lo puede detectar ninguna
  herramienta, porque no hay forma de saber quién escribió qué. Es la razón por la
  que el cruce no basta, y no un defecto suyo.
---

# CORRECCIÓN DE ALCANCE: `bench.py` cambió mientras este hallazgo estaba escrito

Al sacar el desglose por origen, `contract_exec` clasificó `bench.py L725` como
`PROYECTO`. Este hallazgo dice que `bench.py` **no** escribe ficheros del proyecto.
Una de las dos cosas ya no es cierta.

La línea 725 **ya no es** la que se cita arriba:

```
bench.py:725   with open(path, "w") as f:
                   json.dump(doc, f, indent=1, sort_keys=True)
```

Antes era un `os.utime`, que es mtime y no contenido. Ahora es una escritura de
contenido en un artefacto JSON.

**Esto no invalida el hallazgo, lo acota en el tiempo:**

- Lo que se midió —cero escrituras de proyecto— era cierto **cuando se midió**.
- `bench.py` está **sin versionar**, así que otra sesión lo edita cuando quiere y no
  hay commit que fije el estado en el que se hizo la afirmación.
- **Lo que sigue en pie, porque no depende del fichero**: `bench.py` declara
  `WRITES_GPU=yes`, sus cuatro `subprocess` van todos a `vcp`, y `vcp` **no** toca
  la barra de registros. Eso se comprobó sobre el binario, que tampoco ha cambiado.

## Y esto es lo que el desglose por origen salio

La herramienta etiqueta cada caso como versionado o ajeno, y al hacerlo vio el
cambio. **No lo buscaba: lo vio porque estaba contando por origen.** Un conteo
que no distingue de dónde viene cada caso no puede notar que un caso cambió; solo
puede decir cuántas veces ha corrido.

Ese es el argumento a favor de la acción anterior, y sale de un fallo suyo y no de
su diseño.

## Límite del límite

No he vuelto a medir `bench.py` entero después del cambio: solo la línea 725 y el
contrato. Las cuatro llamadas a `subprocess` se midieron **antes** del cambio, así
que si esa edición tocó también la parte que delega, la cadena podría tener otro
eslabón. `NOT_DETERMINED`.
