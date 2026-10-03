# 970 · `runtime_obs.py` falla en silencio: 5 defectos, 3 de ellos demostrados con control negativo

```text
CLASSIFICATION=ERROR+MEASUREMENT+NEGATIVE_RESULT · TRACK=TOOLING
CORPUS=ninguno
HARDWARE_SCOPE=amdgpu 1002:699f rev c7 (esta maquina, solo lectura)
WORK_CLASS=READ_ONLY/EVIDENCE+WRITE_LOCAL
WRITE_LOCAL=PROPIOS
MODIFICATIONS_COUNT=2
WRITE_EXECUTION=NONE
AUTHORIZATION=NONE
AUTORIA=AGENTE-SMU
RUNTIME=READ_ONLY_SYSFS+JOURNALCTL   (sin debugfs, sin MMIO, sin escritura)
GPU INTACTA
CERROJOS=0
TOOL=tools/runtime_obs.py
     sha256 c002e8024e67d996c2dc5466e802c1c70bc40a64091663360e398b7996f73dfe
     (estado ACTUAL. El instrumento SI fue editado durante este nodo: solo
      comentario/cabecera, por autorizacion expresa del coordinador en la
      segunda pasada. Ver §13 para la historia de tres estados.)
TOOL=tools/_selftest_runtime_obs.py  (NUEVO, este nodo)
     sha256 64723084d61794b518117dcc35d645a0055a9d30504557fb739d8cfad75ec356
```

Fecha de la medicion: 2026-10-03. Kernel `7.1.3-200.nobara.fc44.x86_64`.
Python 3.14.7. uid 1000, **sin privilegio**.

## Qué resuelve

La pregunta era doble y las dos mitades tienen respuestas distintas:

1. ¿`runtime_obs.py` produce evidencia OBSERVED sobre este ASIC? **Sí, parcialmente.**
   16 lecturas vivas y 6 lineas de log, con valores que corroboran el target.
2. ¿Puede FALLAR cuando debe? **No, en el plano que importa.**

La segunda mitad es la que invalida la primera como evidencia admisible, y es
la que se responde aqui.

## Veredicto de instrumento

```
DEGRADED
```

No `INVALID`, porque **observa de verdad** y sus valores son correctos. No
`SELF_TESTED`, porque sus controles negativos no discriminan en el plano de
observacion: acepta estimulos que deberia rechazar y devuelve `rc=0`.

Lo que queda probado es esto, y es la formulacion exacta:

> El instrumento **distingue** «lei» de «no lei» **en el texto** — marca los
> fallos con `<errno N>` — pero **no los distingue en el veredicto**: el
> código de salida es 0 haya leido 16 valores o 0. Un consumidor que mire el
> `rc` no puede saber cual de las dos cosas pasó.

## 1 · Lo que SI observa (OBSERVED, no privilegiado, esta maquina)

Ejecutado el 2026-10-03 con `python3 runtime_obs.py`. Valores literales:

```
vmid       10 atributos LEIDOS, 0 con error, 14 inexistentes
  pp_dpm_sclk                     0:214 1:551 2:734 3:980* 4:1000 5:1020 6:1046 7:1071 Mhz
  pp_dpm_mclk                     0:300* 1:625 2:1500 Mhz
  power_dpm_force_performance_level  auto
  mem_info_vram_total             2147483648      (2 GiB exactos)
  mem_info_vram_used              269012992       (cambia entre ejecuciones)
  mem_info_vis_vram_total          268435456       (256 MiB = tamano de BAR)
  max_link_width                   8
  revision                        0xc7
  vbios_version                   xxx-xxx-xxx
module     5 LEIDOS:  vm_size=-1  vm_fragment_size=-1  vm_block_size=-1
                     vm_update_mode=-1  srcversion=D68004925455E20A24C2B87
bootlog    6 lineas, entre ellas:
  amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit
  amdgpu 0000:01:00.0: [drm] Detected VRAM RAM=2048M, BAR=256M
```

Tres corroboraciones cruzadas, con fuentes independientes:

- `revision 0xc7` (sysfs) = `rev c7` (`lspci`).
- `mem_info_vram_total 2147483648` = 2 GiB, y `mem_info_vis_vram_total 268435456`
  = 256 MiB = el `BAR=256M` del log de arranque.
- La linea `vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9-bit`
  es **exactamente** la cita que el hallazgo `024` (§9, linea 37) ya usa como
  evidencia para cerrar `vm_size = 64`.

La ultima corroboracion tiene una consecuencia incomoda para la tesis de la
herramienta, y se desarrolla en §5.

Los 14 `None` de `vmid` **no** son fallos: son atributos que este ASIC no
expone (`gfx_busy_percent`, `pp_thermal_percent`, `vram_total`…). El
instrumento los distingue bien de un error (`null` frente a `"<errno>"`), y eso
si es correcto: `ACCESSOR_MISSING` y `ACCESSOR_PRESENT` quedan separados.

## 2 · Defecto 1 — la seccion `pci` esta muerta y no lo dice

**El mas grave, porque descarta observaciones que si existian.**

```
$ python3 runtime_obs.py pci ; echo RC=$?
=== pci ===
  config_space     <errno 2>
  vendor           <errno 2>
  device           <errno 2>
  revision         <errno 2>
  ...  (12 de 12 con marcador de error)
RC=0
```

**Las 12 lecturas fallaron. El rc es 0.** La seccion se imprime con 12 lineas,
con nombres de campo convincentes, y parece poblada.

La causa son **dos** defectos que se componen:

**D1 · `runtime_obs.py:180`** — la regex no puede extraer un BDF:

```python
m = re.search(r"pci[0-9a-f:]+/([0-9a-f:]+)$", real)
GPU = m.group(1) if m else real          # linea 181: la reserva se ejecuta SIEMPRE
```

Un realpath de sysfs tiene **dos** `/` despues del puente:

```
/sys/devices/pci0000:00 / 0000:00:01.0 / 0000:01:00.0
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

El patron espera **una**. Asi que despues de `pci[0-9a-f:]+` y su `/`, el resto
contiene otro `/`, que no esta en la clase de caracteres, y el patron nunca
llega al `$`. La rama de reserva se ejecuta siempre y **`GPU` nunca es un BDF**.

**D2 · `runtime_obs.py:243`** — la reserva produce una ruta imposible:

```python
p = f"/sys/bus/pci/devices/{GPU}/config"
```

`GPU` ya es una ruta absoluta, de modo que se concatena sobre una base fija y
sale:

```
/sys/bus/pci/devices//sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0/config
```

que no existe (`stat` → `errno 2`).

**Lo que se estaba perdiendo.** Comprobado de forma independiente, sin el
instrumento: `/sys/bus/pci/devices/0000:01:00.0/` es legible en esta maquina.
Con una sola linea cambiada (`re.match(r".*/([^/]+)$", real)`), la seccion
entera revive:

```
vendor              0x1002
device              0x699f
subsystem_vendor    0x1002
subsystem_device    0x0b04        <- coincide con lspci [1002:0b04]
revision            0xc7
class               0x030000
resource            0x00000000e0000000 0x00000000efffffff ...   (BAR0 256 MiB)
current_link_speed  5.0 GT/s PCIe
current_link_width  4
max_link_speed      8.0 GT/s PCIe
max_link_width      8
```

**12 observaciones disponibles, perdidas, y recuperables con un caracter.**
Ese es el coste medido del defecto.

**D3 · `errno 2` no esta clasificado.** `ERRNO_NAME` (`runtime_obs.py:187-193`)
cubre 13, 16, 19, 22 y 5. **No cubre 2 (ENOENT)**. De ahi que se imprima el
marcador crudo `<errno 2>`, sin texto. Un lector no puede distinguir «el
fichero no existe» de «la ruta esta mal construida» de «no hay permiso»:
los tres colapsan en la misma cadena opaca. Es el caso exacto que la propia
docstring de `rd()` (lineas 196-210) dice querer evitar.

### La leccion de los mutantes, incluida la refutacion de mi propia hipotesis

La primera explicacion que tuve fue «la clase de caracteres no incluye el `.`,
que es obligatorio en un BDF». **Es falsa**, y un mutante de un caracter la
refuto en un comando: cambiar `[0-9a-f:]` por `[0-9a-f:.]` deja los 3/3
rutas sin coincidir, porque el `/` intermedio es la causa que domina. Hacen
falta las dos correcciones, o simplemente el ultimo componente del realpath.

Se deja escrito porque el valor de un control esta en **medir si el mutante lo
mueve**, no en que la explicacion suene plausible.

## 3 · Defecto 2 — `EACCES` reportado como «no montado»

```
$ python3 runtime_obs.py debugfs ; echo RC=$?
  estado   debugfs NO montado: esta fuente no existe aqui
RC=0
```

Eso es una **afirmacion falsa sobre la maquina**, y es el defecto con mas
consecuencias para el proyecto. La causa, `runtime_obs.py:281`:

```python
if not os.path.isdir("/sys/kernel/debug/dri"):
    return {"estado": "debugfs NO montado: esta fuente no existe aqui"}
```

`os.path.isdir()` devuelve `False` **por `EACCES`**, no por inexistencia. Hechos
medidos por separado:

| Comprobacion | Resultado |
|---|---|
| `/proc/mounts` contiene `debugfs` | **si** — `debugfs /sys/kernel/debug ... rw` |
| `stat("/sys/kernel/debug")` | ok, modo `0700` |
| `stat("/sys/kernel/debug/dri")` | **errno 13 (EACCES)** |
| `os.path.isdir(...)` | `False` |

El discriminante esta en el errno: **13 = permiso, 2 = ausente**. Aqui es 13.
El instrumento convierte `NO_ACCESO` en `ACCESSOR_MISSING`, que son dos hechos
con consecuencias opuestas: uno dice «no hay dato»; el otro dice «el dato
existe y hay que pedir privilegio».

**Por que esto importa mas que los otros.** Si una seccion afirma que una
fuente «no existe aqui», cualquier nodo posterior marcara
`NOT_AVAILABLE` o `PROVEN_ABSENT` para toda observacion MMIO de GFX8 — que es
justo la frontera abierta de Q5. Se cerraria una frontera con un **permiso
falso**.

Ademas la cabecera de la propia herramienta (linea 24) dice
`/sys/kernel/debug/dri/1/... NO (debugfs sin montar)`, en presente. Hoy es
falso: debugfs **esta** montado. Es evidencia historica presentada como
actual (§86), y no se revalida nunca porque la cabecera no es codigo.

## 4 · Defecto 3 — no puede detectar un ASIC distinto

La cabecera afirma (linea 44) y la funcion `detect()` repite (linea 155):

```
"Se autodetecta por PCI_ID y no se codifica a mano."
```

**Es falso.** `detect()` filtra **solo** por nombre de driver:

```python
pid = re.search(r"PCI_ID=(\S+)", ue)          # linea 171: se parsea...
if drv and drv.group(1) == "amdgpu":           # linea 173: ...pero no se usa
    found.append((c, dev, pid.group(1) if pid else "?"))
CARD, DEV, _gpuid = found[0]                   # linea 177: la PCI_ID se DESCARTA
```

El identificador `699f`/`1002` aparece en el fichero **solo en prosa**
(linea 43), nunca en codigo. Comprobado:

```
$ grep -n '699f\|1002\|PCI_ID\|_gpuid' runtime_obs.py
43,44,155,171,177     -> ningun uso de la PCI_ID como criterio
```

Control negativo C3, con un arbol `/sys/class/drm` falso y **verificado** como
entregado:

```
nodo amdgpu con PCI_ID 1002:687F (Vega10, ASIC distinto)
  -> detect() ACEPTO el nodo: card=card0 gpu=.../0000:03:00.0
     La PCI_ID 1002:687F NO es 1002:699F y no se ha comparado.
  veredicto: NO_PUEDE_FALLAR
```

Consecuencia: en una maquina con otra GPU bajo `amdgpu` (Vega10, Navi…), esta
herramienta la adoptaria en silencio y **todas** sus secciones se atribuirian a
un ASIC que no es el objetivo. El instrumento cuya razon de ser es observar
*este* ASIC no implementa la comprobacion de `TARGET_MISMATCH` que §4 del
proyecto exige.

Añado: `found[0]` sin comprobacion de ambiguedad. Dos nodos `amdgpu` → elige el
primero en silencio.

## 5 · Defecto 4 — `--json` no produce JSON

```
$ python3 runtime_obs.py --json > out.json ; echo RC=$?
RC=0
$ python3 -c "import json;json.load(open('out.json'))"
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

Causa: `runtime_obs.py:357` imprime la cabecera `nodo amdgpu detectado: ...`
**incondicionalmente**, antes del `json.dumps` de la linea 397. El modo
documentado en la cabecera (linea 48) es inválido, y el `rc` es 0.

Es exactamente el patron de §27: productor `rc=0` + artefacto de tipo
inesperado + consumidor que aborta. `run_all.py:153` no usa `--json`, asi que
esto **nunca se ha detectado**.

## 6 · Defecto 5 — una validacion muerta (NO EJERCITADA)

`runtime_obs.py:337-338`, dentro de `do_write`:

```python
if what == "power_dpm_force_performance_level" and value not in SAFE_ACTIONS:
    pass
```

Detecta un valor fuera de `SAFE_ACTIONS` y **no hace nada**. Es una barrera
anunciada que no frena nada.

**NO SE EJERCITO.** `--write` queda fuera del alcance de este nodo, y asi se
declara: el comportamiento en runtime de la rama de escritura es
`NOT_DETERMINED` por restriccion, no por medida. Lo unico afirmable es el
hecho estatico: el codigo de la validacion no tiene efecto. Notese que
`run_all.py` solo invoca la seccion `module`, de modo que **la rama de
escritura no tiene ninguna cobertura automatica en este proyecto**.

## 7 · Los controles negativos, y por que el self-test no es decoracion

`runtime_obs.py` **no tenia self-test** y nunca produjo un artefacto en este
repositorio. Este nodo anade `_selftest_runtime_obs.py` (6 controles), que
devuelve `rc=1`:

```
C1  seccion inexistente            -> rc=1, ERROR explicito     CONTROL_OK
C2  /sys/class/drm sin amdgpu      -> detect() aborta            CONTROL_OK
C3  amdgpu con otro ASIC           -> lo ACEPTO                  NO_PUEDE_FALLAR
C4  `pci` con 12/12 lecturas mal   -> rc=0                       NO_PUEDE_FALLAR
C5  debugfs montado pero EACCES    -> rc=0, dice "NO montado"    NO_PUEDE_FALLAR
C6  la regex extrae un BDF         -> 0/3                        CLAIM_REFUTADA

RESULTADO: TOOL_INVALID -- falla en silencio ante fallo de observacion.
           NOTA: esto NO dice que no observa nada. Dice que no
           distingue 'lei' de 'no lei'.
```

**El instrumento puede fallar, pero solo en el plano de los argumentos.** C1 y
C2 lo demuestran. Lo que no puede es fallar cuando el hardware o el sistema
de ficheros no cooperan: ahi es donde estan los tres defectos que importan.

Cada control lleva su **refutacion** (que observacion lo invalidaria), porque
un control que no puede fallar es indistinguible de uno que pasa. Y eso no es
teorico: **la primera version de este mismo self-test sufrio el defecto**.

> El shim de `open()` de C3 delegaba por defecto en el fichero **real**. El
> `uevent` que el codigo bajo prueba acabo leyendo era el del Intel de verdad
> (`DRIVER=i915`), no el Vega10 falso, y por eso `found` salio vacio y C3
> reporto un **PASS FALSO**: el control no podia fallar por la razon
> equivocada. Se corrigio con una clase `Sandbox` que resuelve **todo** lo que
> cae bajo `/sys/class/drm/` contra el arbol falso y **se niega** a caer al
> sistema si ahi no existe, mas un `sb.vio()` que imprime que leyo el codigo
> bajo prueba.

Se documenta porque es la misma clase de defecto que este hallazgo audita,
apuntada ahora contra el propio auditor: un self-test que no puede fallar
**y ademas miente** es peor que uno que no puede fallar, porque certifica al
defecto que deberia encontrar.

### Mutacion: el control se mueve

| Mutante | Cambio | `pci` |
|---|---|---|
| original | — | 0/12, rc=0 |
| M1 | `[0-9a-f:]` → `[0-9a-f:.]` (un caracter) | **0/12, rc=0** — no arregla nada |
| M2 | `re.match(r".*/([^/]+)$", real)` | **12/12**, valores reales |

M1 no mueve el control y **si** desmiente la explicacion inicial. M2 lo mueve y
recupera las 12 observaciones. Los controles no estan permanentemente rojos.

## 8 · Cuantos `NOT_DETERMINED` cierra de verdad, y cuales

La tesis de la cabecera es «25 hallazgos acaban en `NOT_DETERMINED -- requiere
hardware`». Recuento real sobre `06-INGENIERIA-INVERSA/findings/` (482 `.md`):

| Metodo | Ficheros |
|---|---|
| contienen la frase «requiere hardware» | **12** |
| marcan `NOT_DETERMINED` en cualquier parte | 332 |
| marcan `RUNTIME=NOT_RUN` | 229 |
| union de los tres | **386** |
| *(la cabecera afirma)* | *25* |

**Ningun metodo reproduce el 25.** El mas cercano es 12 ficheros / 18
ocurrencias. La cifra de la cabecera es `NOT_CORROBORATED`; queda como
afirmacion historica no verificable, no como error probado — no puedo saber si
se conto otra vez, con otra vocabulary, o si simplemente esta desfasada.

**Y el hallazgo mas importante de esta seccion: la clase que la herramienta si
cierra ya estaba cerrada.**

`024` §9 cita **literalmente** la linea de bootlog que produce `--section
bootlog`, y anota que el cierre fue «Lectura de sysfs, sin privilegio, sin
RUNTIME». Es decir: lo que `runtime_obs.py` propone hacer, ya estaba hecho a
mano con los mismos ficheros. La tesis de la cabecera («esa frase es casi
siempre incorrecta») es correcta **como principio** y **obsoleta como
diagnostico**: esos 12 no estaban bloqueados, era que nadie los habia leido.

**La clase que la herramienta NO puede cerrar es la que el proyecto quiere.**
Muestreando los 12:

- `034`: lo que queda abierto es `payload de COND_EXEC` y
  `payload de VM_INVALIDATE / INT_SEL`, y el propio hallazgo dice «Ningun
  registro obtenido de MMIO… `GPU INTACTA`». Eso es **captura de paquetes PM4**.
  `runtime_obs.py` no tiene ninguna primitiva de captura PM4, ni con `root`:
  lee ficheros, no el bus de comandos.
- `031`: el discriminante es insertar `wmb()` entre dos escrituras y comparar.
  Es un experimento de compilacion, no una lectura.

Asi que la capacidad real de la herramienta es:

| Capacidad | Estado |
|---|---|
| estado de sysfs expuesto por DRM (`vmid`) | `OBSERVED` — 10 valores |
| parametros de modulo (`module`) | `OBSERVED` — 5 valores |
| log de arranque (`bootlog`) | `OBSERVED` — 6 lineas |
| espacio de configuracion PCI e identidad de link | `ACCESSOR_PRESENT` pero el instrumento no lo lee (D1/D2) |
| registros MMIO / `amdgpu_regs` | `READABLE_BUT_PRIVILEGED` |
| PTE/PDE en VRAM, estado de GPUVM | `NOT_AVAILABLE` a traves de esta herramienta (no existe la primitiva) |
| anillos IB, paquetes PM4 | `NOT_AVAILABLE` a traves de esta herramienta |

**Conteo final de la cobertura:** de 386 hallazgos marcados, la herramienta
cierra hoy **una clase estrecha** de estado en reposo expuesto por sysfs, y esa
clase **ya estaba cerrada**. De los 12 que dicen literalmente «requiere
hardware», los que se han inspeccionado son de captura PM4 y de experimento de
compilacion: **ninguno lo cierra esta herramienta, ni con `root`**. La
afirmacion de la cabecera de que la herramienta cierra la clase
`requiere hardware` es `REFUTED` en su parte sustantiva.

## 9 · El limite debugfs/root, separado en tres estados

Esto es lo que **no** se debe colapsar:

- **`OBSERVED`, sin privilegio, ahora** — los 21 valores de §1. Ficheros
  sysfs y `journalctl`, que si es legible por uid 1000.
- **`READABLE_BUT_PRIVILEGED`** — `amdgpu_regs` y el resto de
  `/sys/kernel/debug/dri/1/`. Requiere `root`. En esta maquina:
  ```
  $ sudo -n true ; echo rc=$?
  sudo: a password is required
  rc=1
  ```
  El precondition **no se cumple** de forma no interactiva, asi que no se pide
  una contrasena a un humano y se sigue por la via sin privilegio.
- **`NOT_DETERMINED`** — si `/sys/kernel/debug/dri/` contiene las entradas de
  amdgpu. **No se afirma que las contenga ni que no.** `stat` da `EACCES`, que
  no distingue las dos cosas. Lo resuelve un unico comando con `root`; hasta
  entonces el estado correcto es `NOT_DETERMINED`, no `PROVEN_ABSENT`.

Y la negacion que este hallazgo deja escrita, porque es la que el defecto 2
invita a escribir: **«debugfs no montado» y «no legible por mi usuario» no son
lo mismo, y el instrumento las hatreat como lo mismo.**

## 10 · Lo que este hallazgo NO dice

- No dice que `runtime_obs.py` no observe. Observa 21 valores correctos.
- No dice que el target no sea el correcto. `TARGET_MATCH` se confirmo por
  via independiente (`lspci`: `[1002:699f] rev c7`, subsystem `[1002:0b04]`,
  driver `amdgpu`).
- No dice que los 386 hallazgos sean falsos. Dice que la herramienta no es el
  camino para cerrarlos.
- No dice que `--write` este roto. No se toco. Lo unico medido es que su
  validacion es codigo muerto, por lectura estatica.

## 11 · Lo siguiente, en orden de poder discriminante

1. **Cablear el self-test en `run_all.py`** con su rc esperado. Hoy
   `run_all.py:153` espera `rc=0` de un instrumento que no puede fallar: ese
   semaforo no mide lo que su comentario dice que mide.
2. **Una linea**: `re.match(r".*/([^/]+)$", real)` en la 180. Recupera 12
   observaciones ya disponibles. Es la mejor relacion valor/riesgo del proyecto.
3. **Decidir si `debugfs` es `NO_ACCESO` o `AUSENTE`**, y que el instrumento
   lo diga asi. Si `sudo` no esta disponible de forma no interactiva, la
   honestidad es un `NO_ACCESO` explicito, no un «no existe».
4. **Un unico comando con `root`** que cierre el `NOT_DETERMINED` de §9, o
   declararlo `DEFERRED` por dependencia externa.
5. **Preguntarse si `runtime_obs.py` es el instrumento correcto para Q5.** Q5
   pide «efecto observable en la GPU», y eso es MMIO/PM4. Esta herramienta lee
   ficheros de configuracion. Quizá el instrumento que falta no es una version
   mejorada de este, sino otro con primitivas de registro.

## 12 · Procedencia

```
NODO              N-969  (ver nota de numeracion en §14)
INSTRUMENTO       08-ARQUITECTURA/tools/runtime_obs.py
                  sha256 c002e8024e67d996c2dc5466e802c1c70bc40a64091663360e398b7996f73dfe
                  mtime  2026-10-03 11:09:09   <- estado ACTUAL (estado C)
                  el instrumento SI fue editado en este nodo, en la segunda
                  pasada, por autorizacion expresa del coordinador.
                  Solo docstring/comentario. Ver §13.
SELF-TEST NUEVO   08-ARQUITECTURA/tools/_selftest_runtime_obs.py
                  sha256 64723084d61794b518117dcc35d645a0055a9d30504557fb739d8cfad75ec356
                  RECOMPUTADO en la reparacion de este hallazgo: IDENTICO.
                  rc=1  (TOOL_INVALID)
ARTEFACTOS        08-ARQUITECTURA/artifacts/N969/
                  run1_full.txt run1_full.err run1_full.rc
                  nc1.out nc1.err nc1b.out nc1b.err nc2.out nc3.out nc4.out
                  nc3.postedit.* nc4.postedit.*   (reejecuciones post-edicion)
                  nc5.out nc5.err nc5.rc  nc6.out nc6.err nc6.rc
                  run_full.json run_full.json.err
                  selftest_run.txt   selftest_run2.txt   selftest_run3.txt
                  mutant/mutant_runtime_obs.py      (mutante M1)
                  mutant/mutant2_runtime_obs.py     (mutante M2)
MODIFICADO        _selftest_runtime_obs.py  (nuevo)
                  runtime_obs.py              (cabecera, pasada 2)
                  este hallazgo                          (nuevo)
                  artifacts/N969/**                     (nuevo)
ESCRITURAS        0 hacia GPU, MMIO, sysfs o debugfs.
                  `runtime_obs.py` no fue invocado con --write, --ref ni
                  --restore en ningun momento de este nodo.
MODULO            amdgpu sin tocar: no hubo insmod, rmmod ni takeover.
```

**Lo que una version anterior de esta seccion afirmaba, y era falso.** Decía
`NO MODIFICADO runtime_obs.py — verificado identico por sha256 antes y despues`,
citaba `140161fe…b23` como hash de inicio de nodo, atribuia el `mtime` a
`2026-10-02 17:35`, y concluia `byte-identico a su estado de inicio de nodo`.
Las cuatro son falsas: el instrumento **si** fue modificado en este nodo.
Medido ahora:

```
$ sha256sum 08-ARQUITECTURA/tools/runtime_obs.py
c002e8024e67d996c2dc5466e802c1c70bc40a64091663360e398b7996f73dfe
$ stat -c 'mtime=%y' 08-ARQUITECTURA/tools/runtime_obs.py
mtime=2026-10-03 11:09:09
```

El `mtime` es de HOY y posterior al resto de artefactos del nodo. La razon es
que la segunda pasada sirvio para una correccion autorizada de la cabecera, y el
hash de la cabecera de este bloque (linea 17) ya reflectia ese estado: por eso
el documento se contradecía a sí mismo, diciendo en la línea 17 una cosa y en
§12 la contraria. Ahora §12 dice lo mismo que la línea 17.

### La regla, y su aplicacion corregida

La regla original era correcta y se conserva:

> un instrumento reparado mientras se le juzga no puede ser citado como evidencia
> del defecto.

Lo que **no** describía este nodo es la premisa que la Activaba: «el
instrumento no fue tocado». Aquí el instrumento fue tocado — a propósito, en
pasada 2, por autorizacion del coordinador — y aun así la regla sigue aplicando,
porque se cumple su sustancia:

- **El defecto que este hallazgo juzga NO fue reparado.** La rama de codigo que
  decide que `debugfs` esta o no accesible sigue siendo la misma: `section_debugfs()`
  sigue usando `os.path.isdir()`, que devuelve `False` ante `EACCES` igual que
  ante `ENOENT`, y por eso la herramienta sigue emitiendo `debugfs NO montado`
  con `rc=0`. La pasada 2 corrigio **el texto que describe** el estado y **no** el
  **codigo que lo decide**; el propio texto nuevo lo dice, en el punto de uso,
  con una `ADVERTENCIA, sin resolver`.
- Por tanto el defecto 2 sigue **vivo y medible**, y las mediciones de este
  hallazgo lo confirman: los controles negativos `nc3` / `nc4` se repitieron
  **despues** de la edicion (`*.postedit.*`) y con el mismo resultado. La
  reparacion de la cabecera no altero ningun resultado experimental.

### El matiz que ya estaba bien, con un tercer estado

La distincion «difiere del ultimo commit» ≠ «cambiado por este nodo» era
correcta y sigue siendo correcta. Lo que le faltaba era un tercer estado: hay
**tres**, no uno, y el segundo no es de este nodo mientras que el tercero sí.
Ver §13.

Lo relevante para el veredicto no cambia: ninguno de los tres estados toca la
linea 281 ni `section_debugfs()`. La correccion de la cabecera cambia
`dri/0`→`dri/1` y reetiqueta la linea de `debugfs`; la **logica** que decide si
`debugfs` se declara montado es identica en A, B y C. El defecto 2 sigue
intacto en los tres.

## 13 · Historia de tres estados de `runtime_obs.py`

Medido con `sha256sum`, `stat` y `git diff` en la reparacion de este hallazgo.
`HEAD` entonces era `58244a8`; ahora es `3d89682`, con **un** commit entre
ambos y el blob del fichero **sin cambiar** (`git cat-file` sobre `58244a8` y
sobre `HEAD` devuelve el mismo sha256 de contenido), asi que A sigue siendo A.

| | sha256 | `dri` en cabecera | texto de `debugfs` | origen |
|---|---|---|---|---|
| **A** HEAD | `c9bbe06bf4c232c297730920b0be64123eda67943b49ed026f1fffd0c267dbf6` | `dri/0` | `NO (debugfs sin montar)` | commit `58244a8`, blob `f1d5c36a` |
| **B** inicio de nodo (pasada 1) | `140161fed697cdbe55f0fa4d03421c550b496422d685f070a57c281d521c2b23` | `dri/1` | `NO (debugfs sin montar)` | correccion **sin commitear de otra sesion**, anterior a este nodo |
| **C** ACTUAL | `c002e8024e67d996c2dc5466e802c1c70bc40a64091663360e398b7996f73dfe` | `dri/1` | `MONTADO, SOLO ROOT (EACCES sin privilegio)` + `ADVERTENCIA, sin resolver` | **este nodo, pasada 2, por autorizacion del coordinador** |

**Estado B no tiene artefacto sobreviviente.** El hash `140161fe…b23` no
aparece en ningun fichero del repositorio mas alla de las dos menciones de este
propio hallazgo (las que se corrigen aqui). No hay copia, ni hash guardado en
`artifacts/N969/`, ni entrada en ningun manifiesto. Se registra como
**AFIRMADO SIN ARTEFACTO INDEPENDIENTE**: el contenido de B se infiere de A
mas el cambio `dri/0`→`dri/1` que el comentario «CORREGIDO:» del propio fichero
describe, no de un hash verificable que sobreviva. La cadena de estados que
sostiene B es una, no dos.

**La edicion de la pasada 2 fue solo docstring/comentario.** Verificado, no
supuesto. `git diff HEAD -- runtime_obs.py` da **+23 −1**, un solo hunk
(`-U0`: dos, contiguos), y todas las lineas tocadas caen entre las 17 y la 41
del fichero. El docstring de modulo va de la linea 8 (`r"""RUNTIME OBS…`) a la
70 (`"""`). `WRITES = {` esta en la 85 y `MODULE_WRITES = {` en la 115: fuera
del docstring y **sin tocar**. No hay ninguna linea de codigo ejecutable
añadida, quitada ni alterada.

*Observacion que refutaria esto:* una sola linea `+`/`-` del diff fuera del
rango 8..70, o cualquier diff en las lineas 85 y 115. Comprobado con
`git diff -U0` filtrando las que no son comentario ni prosa del docstring: cero.

**Conteo de hunks.** Una version anterior de §12 citaba el `git diff` mostrando
un unico cambio. El diff real no muestra uno: contiene el bloque «CORREGIDO»
de `dri/0`→`dri/1`, la reetiqueta de la linea de `debugfs`, y el bloque
`ADVERTENCIA`. Medido con el diff por defecto fusiona en **un** hunk porque los
tres cambios son contiguos; con `-U0` son **dos** encabezados `@@`
(`@@ -16,0 +17,7 @@` y `@@ -19 +26,16 @@`), no tres. Se registra el numero
medido, no el supuesto.

### Clase de defecto, sin editorializar

Misma clase que el hallazgo 968: **un sha256 escrito a mano que queda obsoleto
en cuanto el fichero se mueve**. aqui el hash se escribio al principio de la
pasada 1 y no se reviso al terminar la pasada 2. Reproducido dentro de 970
minutos despues de que 970 se escribiera sobre integridad de hashes.

## 14 · Maquinaria de numeracion: tres defectos distintos, registrados sin reparar

Medido en la reparacion de este hallazgo. **No se repara nada aqui**: el
diagnostico es de otra sesion. No se renombro, renumero, movio ni borro
ningun fichero de hallazgo; no se toco `_reservas/*.res`,
`FINDINGS-RENUMERACIONES.md` ni `findnum.py`.

**Rutas reales.** Las reservas no viven en `_reservas/` en la raiz sino en
`06-INGENIERIA-INVERSA/findings/_reservas/`. Hay **24** ficheros `*.res`.

### Defecto 1 · `COLLISION 968` — dos ficheros, una reserva

```
06-INGENIERIA-INVERSA/findings/_reservas/968-reservado.res   (59 B, 09:44)
    RESERVADO numero=968 pid=724760
    --help
    2026-10-03T09:44:09
```

Contra **dos** ficheros que declaran el mismo numero, ambos con sello 10:50:

```
968-el-documento-que-declara-que-manda-declara-una-version-que-no-existe.md    6622 B
968-q5-universo-de-tablas-gfx8.md                                           24417 B
```

Una reserva, dos autores. Ninguno de los dos reservo ese numero.

### Defecto 2 · `ORPHAN 969` — fichero sin reserva

```
_reservas/969-reservado.res                    DOES NOT EXIST   (ls: No existe)
969-el-control-marca-como-contaminacion-la-declaracion-correcta.md   9550 B  11:12
```

Un hallazgo **numero 969 sin ninguna reserva que lo respalde**, escrito a las
11:12 —despues de que este nodo consumiera su turno— y **pertenece a otra
sesion**. Se registra; no se toca.

### Defecto 3 · `findnum.py --help` CONSUME UN NUMERO DE HALLAZGO

De los 24 `.res`, **8** tienen `--help` como linea de invocacion:

```
280  283  287  288  290  501  968  970
```

Esto incluye la reserva **de este mismo hallazgo**: `970-reservado.res` nacio de
una sonda `--help`.

- **TIPO**: defecto de instrumento. Una invocacion de autoayuda de la
  herramienta de numeracion queda registrada igual que una reserva real y
  consume un numero.
- **ALCANCE MEDIDO**: 8 de 24 = un tercio de las reservas del directorio.
- **COMO CONTRIBUYENTE PLAUSIBLE** al dano de numeracion conocido del proyecto
  (42 renumeraciones, 1028 referencias colgantes): la tasa es alta y el
  mecanismo encaja, asi que **es una hipotesis con respaldo countable**.
- **LO QUE NO SE AFIRMA**: que sea **la causa**. El conteo 8/24 establece
  coocurrencia y magnitud, no causalidad. Sin un registro de *por que* se
  invoco `--help` ocho veces, la atribucion es `HYPOTHESIS`, no `CONCLUSION`.
- **LO QUE LO REFUTARIA**: los 8 `.res` con `--help` fechados **despues** de
  que su numero se liberara o se reasignara; o evidencia de que `--help` se
  puede resolver sin reservar numero; o un recuento de las 42 renumeraciones en
  el que ninguna coincida con un numero de esta lista de 8.
