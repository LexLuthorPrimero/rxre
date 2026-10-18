# RXRE-AUTONOMY-001 — De ocho mecanismos sueltos a un sistema conectado

**Fecha:** 2026-10-14 · **Base:** el árbol que dejó RXRE-ARCH-EXEC-002 (commit de trabajo d754f2c, sin commits nuevos, sin ramas, sin worktrees)
**Alcance de esta iteración:** hardware real de la RX550, FIRE reescrito, WATER con memoria que se puede medir.

Este documento no es un plan. Describe lo ejecutado, lo medido y lo que queda
abierto. Donde una cifra no está medida, se dice que no lo está.

---

## 0. RESUMEN EJECUTIVO

| | antes | ahora |
|---|---|---|
| `gpu.register_read` | `NOT_DETERMINED`, sin producer verificado | **`AVAILABLE`, lectura real del ASIC medida 41 veces** |
| Lecciones con check ejecutable | 0 (el campo no existía) | **7 de 7 (100 %)** |
| `op: experiment` | comparaba `len(results)` y emitía `keep`/`reject` | **exige predicción falsable; 4 veredictos honestos** |
| Superficie JSONL | un `int` en stdin mataba el proceso | **responde y sigue** |
| Versiones de backend verificadas | UMR `False`, ghidra `False` | **UMR, rizin, radare2, coccinelle, capstone, knowledge `True`** |
| Suites ejecutadas | — | **19, con 15 en verde** |

Lo más importante no es una cifra. Es esto:

> Este árbol arrastró **meses** con tres afirmaciones falsas escritas en prosa —
> flags de UMR que no existen, y un nombre de registro que nunca existió. Nadie
> las ejecutó. Ninguna memoria impedía copiarlas. La lección que sale de ahí no es
> "ser más cuidadoso": es que **un ejemplo ejecutable que nadie ejecuta no es
> memoria, es decoración**, y que la única memoria que impide una reincidencia es
> el *check*. Eso es lo que se ha construido: `op: lessons` mide, con nombres,
> cuántas lecciones dependen de que alguien las lea.

---

## 1. BODY → EARTH. `gpu.register_read` contra el ASIC real

El bloqueo que arrastraba ARCH-EXEC-002 ("requiere root") **está resuelto**: existe
una vía autorizada y segura. Lo que costó fue descubrir que el adapter estaba roto
de tres maneras y que ninguna se parecía al motivo declarado.

### 1.1 Tres formas que UMR v1.0.0 no acepta (medido)

| lo que hacía el adapter | lo que responde UMR en este host |
|---|---|
| `umr -O no_colour` | `error: Unknown option [no_colour]` — rc=1 |
| `umr -g polaris12@0` | `[ERROR]: ASIC not found or compatible (instance=0, did=ffffffffffffffff)` — rc=1 |
| validar el nombre solo por forma | `polaris12.smc.gpu_length`, el ejemplo del docstring, **no existe** |

**Por qué el segundo importa más de lo que parece.** Con auto-detect UMR funciona,
así que el arreglo fácil era quitar el flag. Se eligió `-g =<pci>` en su lugar por
una razón que no es comodidad: con el auto-detect **elige UMR**; con `-g =<pci>`
elige el device que la allow-list ya validó. La restricción de seguridad sobrevive
hasta la invocación.

### 1.2 Contradicción registrada, no resuelta

El espacio de nombres de la base de datos de UMR para esta GPU es `polaris12.*`, y
las lecturas funcionan con `polaris12.gfx800.*`. Pero `-g polaris12@0` **no**
resuelve el ASIC (`did=ffffffffffffffff`). El nombre con el que UMR nombra la base
de datos y el nombre que UMR acepta para `-g` **no coinciden en esta máquina**.
Se registra como contradicción abierta; la vía de trabajo es la selección por PCI,
que sí está medida.

### 1.3 El precheck estático (lo que convierte "formato" en "existe")

`_registro_existe_en_bd()` consulta `/usr/share/umr/database` **antes** de invocar
nada. No cuesta privilegios — la BD es un fichero. Ahora el motivo del rechazo dice
qué hay:

```
polaris12.smc.gpu_length
  -> invalid_input
     el IP 'smc' no existe en polaris12.asic.
     IPs reales: bif510, dce1120, gfx800, gmc810, oss300, smu713, uvd600, vce300
```

Y los nombres reales llevan **prefijo de tipo de dos caracteres** (`mm`, `ix`, `dc`,
`ad`). `polaris12.gfx800.mmGRBM_STATUS` sí existe y sí lee.

### 1.4 Privilegios: declarados, nunca automatizados

Sin root, UMR responde `[ERROR]: UMR was not invoked as root`. El adapter exige que
el operador **declare** la escalada con `RXRE_ESCALATE="sudo -n"` (o ejecutar con
euid=0), lo registra en el precheck, y si no está declarado responde `blocked` con
el prerrequisito exacto:

```
export RXRE_ESCALATE='sudo -n'
```

**Ninguna contraseña se guarda en el árbol ni se pide por código.** MEDIDO:
`/etc/sudoers` de esta máquina **no tiene NOPASSWD**; `sudo -n` solo funciona
dentro de la ventana del ticket. La vía fiable es `euid=0`.

### 1.5 Lo que se lee, y lo que eso significa

```
polaris12.gfx800.mmGRBM_STATUS       => 0x00003028    (dec 12328)
polaris12.gmc810.mmMC_VM_FB_LOCATION => 0xf47ff400    (dec 4102026240)
```

**El valor de un registro NO es un hecho fijo.** 41 lecturas dieron cuatro valores:

| valor | lectura | lectura | |
|---|---|---|---|
| `0x00003028` | 38 | motor quieto | |
| `0xa0003028` | 1 | `GUI_ACTIVE`=1, `CP_BUSY`=1 | |
| `0xe5d04028` | 1 | `TA/SX/SPI/BCI/SC/DB/CP/CB_BUSY` | |
| `0xe5d05028` | 1 | variante posterior | |

Los nombres de bit no están inventados: salen de la definición del registro en la
propia BD de UMR (`ip/gfx_8_0_0.reg`, sub-campos `NOMBRE lsb msb`). El bit 31 es
`GUI_ACTIVE`. Los bits altos se mueven porque el motor estaba encendido.

> **Consecuencia asumida en el sistema:** un hallazgo sobre el valor de un registro
> tiene que llevar su ventana, su número de muestras y la lista de valores. Por eso
> `value_hex` conserva el ancho tal como lo emitió UMR (`0x00003028`, no `0x3028`).
> Un check que exigiera un valor fijo fallaría al primer uso real, y por eso
> `test_registro_variabilidad002.py` **no** comprueba un valor: comprueba que la
> lectura es real, que el ancho se conserva y que la variabilidad es observable.

---

## 2. AIR. Tres defectos reales en el camino productor → consumidor

### 2.1 La superficie JSONL se moría con una línea rara

```
AttributeError: 'int' object has no attribute 'get'
  File "api/machine.py", line 599, in procesar_linea
      op = req.get("op")
```

No era un fallo del que mandara un JSON: era un fallo del **consumidor**. Se
disparó de verdad, porque `sudo -S` lee la contraseña de stdin **solo si la pide**:
con el ticket cacheado no lee nada y la línea se cuela en el stdin del proceso como
`123456`, que es un entero perfectamente válido. Una superficie JSONL que se muere
ante una línea rara no es una superficie. Ahora comprueba el **tipo** antes de usarlo.

### 2.2 `sudo` se llevaba por delante la configuración — y nadie lo decía

```
RXRE_DB=/tmp/x.sqlite3 sudo -S python3 tools/rxre/api/machine.py
→ dentro del proceso, RXRE_DB no existe
```

`sudo` arranca con `env_reset` y solo conserva lo que está en `env_keep`. La
ejecución con privilegios escribía en la **base por defecto** y respondía
`persistido: true`, mientras la verificación miraba otra base y concluía —falsamente—
que la evidencia se había perdido. **Cruzar un límite de privilegios no es
transparente**: las dos partes tienen éxito, y por eso el fallo es silencioso. El
adapter reenvía ahora la configuración de RXRE de forma explícita.

### 2.3 `Backend.version()` ignoraba el `argv` que el registry declara

La lista de flags estaba fija (`-v`, `-V`, `--version`) y lo que el registry declara
por backend no se llegaba a probar. UMR declara `['--help']`, que es la **única**
sonda que funciona:

```
umr -v / -V / --version  ->  [ERROR]: ASIC not found ...   (rechazado, correctamente)
umr --help              ->  "User Mode Register debugger v1.0.0"   rc=0
```

Se prueba primero lo declarado y **después** las genéricas, sin fallback no se
arreglaba UMR pero se rompían rizin y radare2. Ahora los seis verifican.

---

## 3. WATER. Memoria que se puede medir

### 3.1 El campo nuevo: `check_ejecutable`

Una reflexión escrita es un texto. `check_ejecutable` la enlaza con un fichero de
test que la vigila, y `op: reflect` dice explícitamente si queda vigilada:

```json
{"op": "reflect", ..., "check_ejecutable": "test_umr_hardware002.py"}
→ {"status": "ok", "vigilada": true,  "check_ejecutable": "test_umr_hardware002.py"}
```

### 3.2 `op: lessons` separa lo escrito de lo vigilado

Tres categorías que se confunden al decir "aprendí":

- `vigiladas` — tienen un check que existe (y, con `ejecutar`, que **pasa**)
- `sin_check_detalle` — escritas y nada más
- `checks_que_no_sostienen` — un check que no existe, **o que falla**

Lo importante: **un check roto no cuenta como vigilancia.** Un sistema que cuenta
los checks sin comprobarlos no es distinto de uno que no los cuenta; solo tiene más
números.

Estado medido de la memoria real de RXRE:

```
lecciones: 7 | con check: 7 | sin check: 0 | cobertura: 100 %
ejecutando los checks: 7/7 exit=0
```

Las 7 lecciones registradas hoy, cada una con su check y todas verificadas por
ejecución real.

---

## 4. FIRE. El experimento que había que tirar

La primera versión de `op: experiment` —escrita en esta misma sesión— comparaba
`len(results)` y decidía:

```
más filas  -> keep        menos filas -> reject
```

**Eso no es un experimento.** §48 pide un discriminante antes de ejecutar, y contar
filas no separa nada que importe: 84 nodos de CFG contra 85 pueden ser lo mismo con
ruido o una pérdida de contenido, y el recuento no sabe distinguirlo. Pero emitía un
veredicto con nombre, y un agente lo leía como una conclusión. **Un mecanismo que
produce veredictos sin poder equivocarse no es un mecanismo: es un generador de
confianza falsa.** Se quitó.

El contrato ahora exige `question` y `prediction`; sin predicción **no se ejecuta
nada**, porque un experimento sin predicción declarada no puede refutar nada. Y hay
**cuatro** veredictos:

| veredicto | cuándo |
|---|---|
| `sostenida` | el brazo modificado dio el valor esperado declarado |
| `refutada` | difiere, y el motivo dice en qué |
| `no_separable` | los brazos **no se distinguen** con ese observable |
| `no_observable` | el observable no existe en los brazos, o solo en uno |

`no_observable` es un arreglo que un test forzó: antes, un path mal escrito producía
`no_separable`, que es mentira — dos brazos "iguales" porque no hay nada que
comparar. Un path mal escrito no puede parecerse a un experimento sin información.

El experimento cierra en MIND: el veredicto entra en `reflexiones` con su
conclusión, y `replicas: 1` se declara como limitación, no se oculta.

---

## 5. Lo que NO se ha hecho, y por qué

### 5.1 `binary.decompile` sigue bloqueada — causa exacta localizada

```
backends/scripts/  ->  NO EXISTE
DumpDecomp.java    ->  NO EXISTE
javac 25.0.4.1     ->  presente
/usr/lib64/ghidra  ->  presente, 202 jars
```

**La causa no es de compilación: falta el fuente.** `javac` y los 202 jars de Ghidra
están; lo que no existe es `backends/scripts/DumpDecomp.java`. Es viable escribirlo
y es la vía más corta para que `binary.decompile` funcione de verdad. Queda como
frontera abierta con prerrequisito exacto, no como "problema de entorno".

### 5.2 Tres suites sin versionar fallan (no tocadas por esta iteración)

| suite | motivo verificado |
|---|---|
| `test_p004.py` | `ModuleNotFoundError: core.target` — el módulo no existe en el árbol |
| `test_p003.py` | espera una base de registros desde cabeceras AMD `gfx_8_0_d.h`; no está cableada |
| `test_p0_2_conflict014.py` | sale con rc=1 sin línea `FAIL` (excepción al final) |

Las tres están **untracked** y **no aparecen en `git diff`**. La atribución a
"preexistente" no viene del informe anterior: viene de que son ficheros que esta
iteración no ha modificado y que referencian módulos ausentes del árbol.

### 5.3 SOUL sigue siendo el eslabón más débil

Existe el mecanismo (`missions`, `research.next_actions`, `plan` consulta reflexiones
previas). **No existe una función de valor** que ordene el trabajo por contribución,
dependencia, información esperada, coste o reutilización. Lo que hay ahora es
prioridad por estructura, no por valor. No se declara implementado.

---

## 6. Matriz de los ocho principios, según comportamiento observado

| | mecanismo | estado real | lo que falta |
|---|---|---|---|
| **BODY** | `gpu.register_read` con allow-list, precheck estático, selección por PCI | **medido contra el ASIC** | semántica de bitfields más allá de la decodificación de UMR |
| **MIND** | `reflect` sugerido en fallo; `plan` consulta reflexiones de la capability | funciona | no se ha medido que una reflexión **cambie** una decisión concreta |
| **SOUL** | `missions`, `research.next_actions` | estructura, **no valor** | función de prioridad por valor; ausente |
| **EARTH** | `operations → results → edges`; `explain` sobre lectura de hardware | funciona, y **la divergencia silenciosa está encontrada y corregida** | invalidación automática cuando la evidencia caduca |
| **FIRE** | `experiment` con predicción falsable y 4 veredictos | **reescrito; el anterior era falso** | réplicas e intercalado de brazos (hoy `replicas=1` declarado) |
| **AIR** | superficie JSONL; consumidor ya no muere; config preservada al escalar | funciona | traza encadenada productor→transformación→consumidor como evento único |
| **WATER** | `reflexiones` + `check_ejecutable` + `op: lessons` | **7/7 vigiladas y verificadas por ejecución** | priorización por utilidad demostrada |
| **AETHER** | `saturate` evalúa condiciones observables | funciona | no emite todavía la alternativa cuando una frontera se satura |

---

## 7. Cambios en el árbol

**Modificados (12 ficheros, +606 / −121):**
`contract.py` · `decision.json` · `registry.py` · `dispatch.py` · `store.py` ·
`machine.py` · `umr_read.py` · `test_backends004.py` · `test_backends_bulk.py` ·
`test_callgraph1636.py` · `test_dispatch004.py` · `test_ext002_umr.py` ·
`test_xrefs1635.py` · `rz_callgraph.py` · `rz_findings.py` · `rz_xrefs.py`

**Nuevos:**
`test_autonomy003.py` · `test_lecciones006.py` · `test_umr_hardware002.py` ·
`test_registro_variabilidad002.py`

Sin commits, sin ramas, sin worktrees, sin agentes duplicados.

### Nota sobre `decision.json`

`capacidades_cerradas_por_backend.umr` pasó de `0` a `1`, y **no porque se
actualizara a mano**: el vector B7 de `test_dispatch004.py` comparó el registro
declarado con el real, falló, y el fallo era correcto. Ese fichero existe para
detectar exactamente esto.

### Nota sobre `test_dispatch004`

El caso "capacidad `NOT_DETERMINED` → no ejecutable" **dejó de tener sujeto**:
al promover `gpu.register_read` a `AVAILABLE`, ya no queda ninguna capability
bloqueada por estado. Se sustituyó por la invariante que ahora es cierta y que
volvería a fallar si alguien degrada una capacidad — que es lo que mantiene el
hueco visible.

---

## 8. Siguiente paso, por valor

1. **Escribir `backends/scripts/DumpDecomp.java`.** Es la vía más corta para que
   `binary.decompile` funcione: `javac` y los 202 jars ya están, solo falta el
   fuente. Desbloquea decompilación de `amdgpu.ko`, que es la entrada real del
   objetivo.
2. **Cablear la base de registros desde cabeceras AMD** (`gfx_8_0_d.h`), que es lo
   que pide `test_p003.py` y que convertiría `test_p004.py` y `test_p0_2_conflict014.py`
   de módulos ausentes en suites ejecutables.
3. **La función de valor de SOUL**, si el trabajo pasa a ser más que cerrar lo que
   ya está a medias.

Nada de esto se declara hecho. Está medido, no completado.