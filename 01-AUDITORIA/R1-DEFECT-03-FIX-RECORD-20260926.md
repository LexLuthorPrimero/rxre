# R1 DEFECT-03 FIX RECORD — cierre real del fallo de ámbito en `observe()`

```
DEFECT_03=CLOSED
DEFECT_SCOPE=closure scoping in main() > observe()
HASH_BEFORE=ae115054a89a51944362d812412886c1901eabcd139e801495a979440cca19e7
HASH_AFTER=1078cc7c7c2e39308300f86ae17d8a075eb2624410eb26156c2d4525041b5121
BEHAVIOURAL_TEST=ADDED  test_defect03_behavioral.py  9 tests  PASS
AFFECTED_SUITE=154/154 PASS
FULL_SUITE=163/163 PASS
PREVIOUS_FIX_SUFFICIENT=NO
PRIVILEGED_EXECUTION=NO   SUDO_INVOKED=0   R1_EXECUTED=0
GPU_WRITES=0  STORAGE_WRITES=0  SYSTEMD_CHANGES=0  SYSTEM_CHANGES=0
COLLECTOR_PROVENANCE=GIT_INDEX_STAGED_NOT_IN_HEAD
```

**Fecha de las verificaciones:** 2026-09-26T02:40:21Z (`2026-09-25T23:40:21-0300`), host `kalm`,
kernel `7.1.3-200.nobara.fc44.x86_64`, `HOST_SCOPE=HOST-C`.
**Momento del cambio en el collector:** 2026-09-25 23:37:40 -0300 (mtime del fichero).
**Momento del test conductual:** 2026-09-25 23:38:26 -0300 (mtime del fichero).

**Fichero modificado (único):** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/privileged_read_collector.py`
**Test creado (único):** `01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/test_defect03_behavioral.py`

---

## 1. El defecto original

La ejecución R1 `R1-20260926T005434Z` abortó en el primer PID del barrido. Evidencia preservada e
intacta: `01-AUDITORIA/OWNERSHIP-AUDIT-HOST-C/R1-20260926T005434Z.json`
(sha256 `aa388953680134458046d07c5f92f189d9dd2fa6922a20cfbecf3d2f2898248f`).

```
collector_error: UnboundLocalError: cannot access local variable 'root_fd_error_count'
                 where it is not associated with a value

  File ".../privileged_read_collector.py", line 2022, in main
    pid_records[str(pid)] = observe(pid)
  File ".../privileged_read_collector.py", line 1959, in observe
    root_fd_error_count += int(fd.get("error_count", 0))
UnboundLocalError: cannot access local variable 'root_fd_error_count'
```

Consecuencia: **el barrido de `/proc` nunca se completó en ninguna de las dos ejecuciones de R1.**
El run 1 abortó antes, en identidad (DEFECT-01/02). El run 2 murió en el primer PID, aquí.

## 2. Causa raíz, demostrada

`observe()` está definida **anidada dentro de `main()`** (`def observe` en L1930, `col_offset=4`).
Hace una asignación aumentada (`+=`) sobre cinco contadores que pertenecen al ámbito de `main`:

```python
root_process_error_count += 1        # L1941
root_fd_permission_denied += 1       # L1950
root_fd_disappeared += 1             # L1953
root_fd_other_errors += 1            # L1956
root_fd_error_count += int(fd.get("error_count", 0))   # L1959
```

En Python, una asignación aumentada dentro de una función anidada convierte el nombre en
**local de esa función**. La lectura anterior a la asignación lanza `UnboundLocalError`. El archivo
no declaraba `nonlocal` en ninguna parte: **`nonlocal` = 0 ocurrencias**.

La sentencia de L1959 está al **nivel superior del cuerpo de `observe`**, fuera de toda rama
`if`/`for`. Corre en cada PID, con cualquier fixture, incluso con `fd["status"] != "OK"`. Por eso
no hay forma de esquivarla con datos: el fallo ocurre en la primera iteración.

## 3. Por qué la corrección anterior no lo corregía

La corrección registrada consistía en mover la inicialización al ámbito de `main`:

```
    root_fd_error_count = 0        # L1900, dentro de main
```

**Eso no arregla el defecto.** Inicializar un nombre en el ámbito padre no lo hace visible a una
función anidada que lo trata como local. La falta es `nonlocal`, y `nonlocal` no estaba.

Dos pruebas independientes de que la corrección previa era insuficiente:

1. **Reproducción del patrón, sin el collector:**
   ```python
   def main_like():
       root_fd_error_count = 0                       # init en el padre
       def observe(pid, late=False):
           error_count = 0
           root_fd_error_count += int(error_count)  # sin nonlocal
           return root_fd_error_count
       return observe(1)
   ```
   → `UnboundLocalError: cannot access local variable 'root_fd_error_count'`

2. **Inspección del archivo real:** `nonlocal` = 0 ocurrencias; `main` inicializa los cinco
   contadores; `observe` los aumenta; sin enlace entre ambos.

### Por qué ningún test lo detectó

`test_T31`, en `test_r1_defects.py`, es la prueba que el registro daba por cubre DEFECT-03:

```python
main_src = inspect.getsource(collector.main)
self.assertIn("root_fd_error_count += int(fd.get(\"error_count\", 0))", main_src)
```

Es una **comprobación de texto fuente**, no de ejecución. La línea que exige existe **con y sin el
defecto** — el fallo estaba en la inicialización, que el test nunca comprueba. Su mtime es
`2026-09-25 21:42:35`, **75 segundos después** del collector corregido (`21:41:20`): se escribió
después del cambio y no podía fallar. Reportaba cobertura verde sobre un defecto vivo.

## 4. Corrección aplicada

Una sentencia, primera tras el docstring de `observe()`:

```python
nonlocal root_fd_error_count, root_fd_permission_denied, \
    root_fd_disappeared, root_fd_other_errors, root_process_error_count
```

Se declaran los **cinco**, no solo el que seCITó en el traceback: los cinco tienen el mismo
defecto y una corrección parcial habría dejado cuatro vivos.

### Diff exacto

```diff
--- collector.HASH_BEFORE
+++ collector.HASH_AFTER
@@ -1929,6 +1929,8 @@

     def observe(pid, late=False):
         """Read one PID and account for it exactly once."""
+        nonlocal root_fd_error_count, root_fd_permission_denied, \
+            root_fd_disappeared, root_fd_other_errors, root_process_error_count
         meta = proc_meta(pid)
         fd = scan_fds(pid, devices)
         maps = scan_maps(pid)
         item = dict(meta)
```

`+2` líneas, `0` eliminadas. `2764 → 2766` líneas, `110351` bytes.
Ningún otro cambio en el archivo, y ningún otro archivo del repositorio modificado.

### Verificación de los cinco enlaces, por AST

| Conjunto | Contenido |
|---|---|
| `observe` hace `+=` sobre | `root_fd_disappeared`, `root_fd_error_count`, `root_fd_other_errors`, `root_fd_permission_denied`, `root_process_error_count` |
| `main` los inicializa | los mismos cinco |
| `observe` declara `nonlocal` | los mismos cinco |
| `augmented == nonlocal == init` | **True** |

`root_fd_errors` **no** se incluye: es una lista y `observe` la usa con `.append`, que no crea un
enlace local. Excluirla es correcto.

## 5. Test conductual A/B

`test_defect03_behavioral.py` — sha256
`6c923822d3ac5b976116a25a0dcc27d2acf1a734866d1762c3c1fc5b43192342`, 276 líneas, 11552 bytes.

El test **no** usa `inspect.getsource` ni inspección de texto como sustituto de ejecución
(`inspect` no se importa; la única mención está en el docstring que describe `T31`). Extrae el
`FunctionDef` real de `observe` y las inicializaciones reales de `main` por AST, los anida en un
arnés que reproduce el ámbito, y **los ejecuta**. Solo se sustituyen las fuentes de datos que
`observe` consume; la sentencia defectuosa es código real sin stub.

### Discriminación, medida fuera de `unittest` para no depender del propio test

| Caso | Fuente | Resultado |
|---|---|---|
| **A** | real, con `nonlocal` | **PASS** — devuelve el registro con `fd_scan`, `maps`, `_relevant`, `_observed_late` |
| **B** | real, borrando **solo** la sentencia `nonlocal` | **FAIL** — `UnboundLocalError: cannot access local variable 'root_fd_error_count' where it is not associated with a value` |

La única diferencia entre A y B es la sentencia `nonlocal`: 2 líneas de diferencia. Sin el caso B,
un caso A en verde no probaría nada.

### Cobertura de los 9 tests

| Grupo | Tests | Qué comprueba |
|---|---:|---|
| T35 | 3 | **guardián de regresión**: un PID por el cuerpo real no debe lanzar. Un PID con el `nonlocal` eliminado sí lanza. `main` inicializa los cinco y `observe` los enlaza |
| T36 | 2 | el caso A pasa; A y B difieren solo en la sentencia `nonlocal` |
| T37 | 4 | invariantes: `observe` es `def` anidada de `main`; declara `nonlocal` exactamente una vez y para exactamente los cinco, como primera sentencia tras el docstring; hace `+=` sobre los cinco; la sentencia está al nivel superior del cuerpo |

## 6. Resultados de ejecución

Comandos, resultados, duración y código de salida, medidos en el entorno:

```
$ python3 -m unittest test_defect03_behavioral -v
Ran 9 tests — OK            exit 0    0.29 s

$ python3 -m unittest test_collector_failure_modes test_med_review_classifications \
      test_medium_fixes test_privileged_read_collector test_r1_defects
Ran 154 tests — OK          exit 0    1.09 s

$ python3 -m unittest discover -p 'test_*.py'
Ran 163 tests — OK          exit 0    1.29 s
```

`163 = 154` preexistentes `+ 9` nuevos. La suite preexistente no se modificó.

## 7. Verificación de hash por dos métodos

| Fichero | `sha256sum` | `hashlib` (Python) | Resultado |
|---|---|---|---|
| `privileged_read_collector.py` (después) | `1078cc7c7c2e39308300f86ae17d8a075eb2624410eb26156c2d4525041b5121` | idéntico | **COINCIDEN** |
| `test_defect03_behavioral.py` | `6c923822d3ac5b976116a25a0dcc27d2acf1a734866d1762c3c1fc5b43192342` | idéntico | **COINCIDEN** |

`HASH_BEFORE=ae115054a89a51944362d812412886c1901eabcd139e801495a979440cca19e7` era el collector al
final de la fase MED y antes de este arreglo. Sigue siendo un valor histórico válido: el registro
`R1-MEDIUM-FIX-RECORD-20260926.md` lo cita junto a `lines = 2597 -> 2764`, que era la longitud
correcta en ese momento. **Ese registro no se modificó**: sigue describiendo el estado post-MED,
que es lo que documenta.

## 8. Ausencia de efectos operativos

| | |
|---|---|
| `SUDO_INVOKED` | **0** — el test no invoca sudo; el collector no lo invoca por diseño |
| `GPU_WRITES` | **0** |
| `STORAGE_WRITES` | **0** |
| `SYSTEMD_CHANGES` | **0** — `systemctl` no se ejecutó |
| `SYSTEM_CHANGES` | **0** |
| `C1_EXECUTED` / `R1_EXECUTED` | **0** / **0** — R1 no se ejecutó |
| GPU / sysfs / servicios | **sin tocar** |
| `.opencode/` · `STATE/` | no existen |
| `staged` · `HEAD` · `commits` | `360` · `c614678` · `8` — sin cambios |
| `staged=360` | el índice ya estaba separado de `HEAD` antes de este arreglo |

El test no hace sondas al host: sustituye las fuentes de datos de `observe` con stubs y ejecuta
solo el cuerpo real de la función. No invoca `sudo`, ni `systemctl`, ni C1, ni lee `/proc` real.

## 9. Estado final y siguiente paso

`DEFECT_03=CLOSED`. El fallo de ámbito está corregido y demostrado por ejecución, no por
inspección de texto. La ruta del barrido de `/proc` puede ahora completar su primera iteración.

**Siguiente paso: R1 run 3**, con el collector `1078cc7c7c2e39308300f86ae17d8a075eb2624410eb26156c2d4525041b5121`.

Ninguna de las dos ejecuciones anteriores alcanzó el final del barrido, así que el run 3 es la
primera ejecución cuyo resultado diga algo sobre el estado de propiedad del host. La autorización
para ejecutarlo es una decisión aparte y no está contenida en este registro.
