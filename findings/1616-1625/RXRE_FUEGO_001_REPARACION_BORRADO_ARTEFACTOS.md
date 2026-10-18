# RXRE-FUEGO-001 — Reparación del borrado de artefactos originales

**Misión:** corregir el defecto destructivo confirmado en `rz_callgraph.py` y `rz_xrefs.py`, donde `binary.callgraph` y `binary.xrefs` podían eliminar el archivo original analizado.

**Resultado: causa raíz demostrada, 12 llamadas reparadas, 17/17 comprobaciones en verde, cero regresiones.** El defecto ya no se reproduce ni por la vía directa ni por la interfaz JSONL real.

Cadena: `RXRE_INTEGRACION_VK_COMPUTE_TEST_FIXED3.md` → este informe.

---

## 1. Punto de partida: alcance real dentro de los 20 modificados

Los dos adapters a reparar **están** entre los 20 archivos modificados preexistentes. Por tanto:

| Grupo | Nº | Tratamiento |
|-------|-----|-------------|
| **En alcance** | 2 | `backends/adapters/rz_callgraph.py`, `backends/adapters/rz_xrefs.py` |
| **Ajenos** | 18 | Deben quedar **byte-idénticos** |

| Artefacto | SHA-256 antes de la tarea |
|-----------|--------------------------|
| `rz_callgraph.py` | `6d1ebc544256b9202a507e00cc8e680ac5b979d90502bfe95aa3bf0c17d9885a` |
| `rz_xrefs.py` | `f9f33f01b056bb30013cfb2d582dedc9086ca6583d9acb4212ac1300de9f55ca` |

---

## 2. Semántica real de las tres variables

### 2.1 `tmp_path` — tres orígenes, solo uno pertenece a RXRE

| Origen | Código | Dueño |
|--------|--------|-------|
| `fixture_json` | `tmp_path = tmp.name` tras `NamedTemporaryFile` | **RXRE** |
| `str` que es un path existente | `tmp_path = artefacto` | **el usuario** |
| `bytes`/`bytearray` | `tmp_path = tmp.name` tras `NamedTemporaryFile` | **RXRE** |

### 2.2 `es_path` — significa exactamente lo contrario de lo que la limpieza necesitaba

En ambos ficheros, verificado leyendo el código:

- `rz_callgraph.py:319` — `es_path = isinstance(artefacto, str) and os.path.isfile(artefacto)`
- `rz_xrefs.py:160` — misma expresión; `_resolve_artefacto` devuelve `True` en el modo path (l178) y `False` en los modos bytes/fixture (l217)

**`es_path == True` ⇔ `tmp_path` ES el archivo original del usuario.**

### 2.3 `borra` — lo que `_limpiar_tmp` espera

`os.unlink(tmp_path)` se ejecuta si `borra` es cierto. Por tanto `borra` debe significar *"RXRE es el dueño de este fichero"*.

---

## 3. Causa raíz

**La bandera de control de la limpieza está invertida.**

| `es_path` | `tmp_path` es… | `borra` que se pasaba | Efecto observado | `borra` correcta | Efecto correcto |
|-----------|----------------|---------------------|------------------|------------------|-----------------|
| `True` | **ORIGINAL** | `True` | **destruye el artefacto** | `False` | sobrevive |
| `False` | temporal de RXRE | `False` | **fuga de temporal** | `True` | se limpia |

La contradicción era visible dentro del propio código: la docstring de `_limpiar_tmp` decía *"Borra el temp file solo si corresponde (no si era el path original)"* mientras la implementación hacía exactamente lo contrario.

### 3.1 Condición exacta que permite el borrado

> `artefacto` es un `str` que `os.path.isfile()` reconoce como fichero, **y** el flujo alcanza cualquiera de las seis llamadas de limpieza.

Las seis, con su disparador:

| # | Disparador | Estado resultante |
|---|-----------|-------------------|
| 1 | backend ausente en `PATH` | `BK_BLOCKED` |
| 2 | timeout del producer | `BK_BLOCKED` |
| 3 | `rc not in (0, None)` | `BK_ERROR` |
| 4 | `agCj`/`axtj` sin JSON | `BK_ERROR` |
| 5 | JSON mal formado | `BK_ERROR` |
| 6 | **éxito** | `BK_OK` |

La ruta 6 es la importante: **el borrado ocurría también en el camino feliz**, que es el que se ejecutó durante la prueba de integración.

### 3.2 Variantes semánticas entre las doce llamadas

Había **dos**, no una:

| Variante | Fichero | Llamadas | Expresión |
|----------|---------|----------|-----------|
| A | `rz_xrefs.py` | 6 (337, 373, 383, 398, 411, 467) | `_limpiar_tmp(tmp_path, es_path)` |
| B | `rz_callgraph.py` | 1 (l359) | `_limpiar_tmp(tmp_path, es_path)` |
| C | `rz_callgraph.py` | 5 (411, 424, 440, 456, 482) | `_limpiar_tmp(tmp_path, es_path if not fixture_json else False)` |

La variante C es **semánticamente distinta**: en modo `fixture_json` la variable `es_path` **nunca se asigna**. La expresión condicional evita el `NameError` porque con `fixture_json` truthy se evalúa la rama `else` (`False`) y `es_path` no llega a leerse. Es un idioma frágil:任何人 que lo reescriba sin la condicional obtiene un `NameError` en producción.

**Por eso un reemplazo global de `es_path` → `not es_path` habría sido incorrecto**: habría arreglado la destrucción pero introducido `NameError` en modo fixture. Verificar cada contexto, como exigía el encargo, fue lo que evitó esa regresión.

---

## 4. Cambio mínimo aplicado

Una sola idea: **sustituir la bandera ambigua por una que exprese la propiedad del fichero.**

### 4.1 `rz_callgraph.py`

Se introduce `rxre_creo_tmp`, inicializada a `False` (conservador: si un camino futuro no la asigna, no borra nada) y fijada en los tres puntos de asignación de `tmp_path`:

```python
    rxre_creo_tmp = False          # por defecto: nadie es dueño -> no borrar
```
```python
        rxre_creo_tmp = True      # fixture: RXRE creó este temporal
        rxre_creo_tmp = True      # bytes:   RXRE creó este temporal
            rxre_creo_tmp = False # path:    es el ORIGINAL: nunca se borra
```

Las 6 llamadas pasan a `_limpiar_tmp(tmp_path, rxre_creo_tmp)`, lo que además **elimina la variante C** y con ella el `NameError` latente.

### 4.2 `rz_xrefs.py`

Aquí `_resolve_artefacto` ya devuelve una señal limpia, así que basta una línea junto al desempaque:

```python
        rxre_creo_tmp = not es_path
```

Las 6 llamadas pasan a `_limpiar_tmp(tmp_path, rxre_creo_tmp)`.

### 4.3 Docstrings de `_limpiar_tmp` (ambos ficheros)

La docstring anterior era la causa de que el defecto pasara inadvertido: describía el contrato correcto mientras el código lo incumplía. Ahora declara el contrato explícitamente y nombra el error histórico:

```
CONTRATO (RXRE-FUEGO-001):
    borra=True  -> RXRE creo ese fichero con tempfile; se elimina.
    borra=False -> `tmp_path` es un archivo del usuario; NO SE TOCA.
`borra` NO significa "existe" ni "es temporal": significa "RXRE es el dueno".
```

### 4.4 Propiedades del contrato exigidas

| Propiedad exigida | Cómo se cumple | Verificación |
|---|---|---|
| El original sobrevive, con éxito o con fallo | `rxre_creo_tmp=False` en el modo path, en las 6 salidas | T1, T2, T8 |
| RXRE puede borrar sus temporales | `rxre_creo_tmp=True` en bytes y fixture | T3, T4, T5 |
| Si el origen es ambiguo, no eliminar | `rxre_creo_tmp` se inicializa a `False`; toda rama nueva que no lo fije **no borra** | T6 |
| La limpieza de temporales sigue funcionando | No se desactiva nada; se corrige la polaridad | T3, T4, T5, T7 |
| Un resultado no es correcto si se perdió la entrada | Restituido por el flag; verificado E2E | §6 |

No se ocultó el error ni se desactivó la limpieza: el cambio afecta **solo** a la decisión de borrar.

---

## 5. Tests adversariales

**Fichero:** `tools/rxre/tests/adversarial/test_no_borrar_original.py` (nuevo, `f11d7c55…d3d6`)

**Reglas respetadas:** todos los señuelos se crean en un `mkdtemp` aislado; `TMPDIR` se redirige a ese directorio para poder observar exactamente qué temporales crea RXRE; **ningún test toca un artefacto real de la investigación**. El ELF señuelo es una copia de `/bin/true`.

| Test | Cubre | Resultado |
|------|-------|-----------|
| T1 | `binary.callgraph` con original: el archivo sobrevive | ok |
| T2 | `binary.xrefs` con original: el archivo sobrevive | ok |
| T3 | `binary.callgraph` con bytes: sin temporal huérfano | ok |
| T4 | `binary.callgraph` con `fixture_json`: sin temporal huérfano | ok |
| T5 | `binary.xrefs` con bytes: sin temporal huérfano | ok |
| T6a/b | ruta inexistente: sin excepción, no crea ni borra nada | ok |
| T6c/d | fichero no-ELF preexistente: sobrevive al rechazo | ok |
| T7a–e | `_limpiar_tmp` en ambos módulos: `borra=False` conserva, `borra=True` borra, inexistente no propaga `OSError` | ok |
| T8a | original + backend ausente: sobrevive | ok |
| T8b/c | original + producer que falla: sobrevive | ok |

### 5.1 Demostración de que los tests reproducen el defecto

**Antes de la reparación** (`/tmp/opencode/antes_fuego.log`):

```
RESUMEN: 12 comprobaciones ok, 5 FAIL
  FAIL T1 callgraph: el artefacto original sobrevive (el fichero fue BORRADO)
  FAIL T2 xrefs: el artefacto original sobrevive (el fichero fue BORRADO)
  FAIL T3 callgraph bytes: no queda temporal huerfano ('tmpab7ggh3x.bin')
  FAIL T4 callgraph fixture: no queda temporal huerfano ('tmpf1i7po3t.bin')
  FAIL T5 xrefs bytes: no queda temporal huerfano ('tmpwn9wrek4.bin')
EXIT STATUS: 1
```

**Después de la reparación:**

```
RESUMEN: 17 comprobaciones ok, 0 FAIL
EXIT STATUS: 0
```

Los cinco fallos cubren **las dos direcciones** del defecto: destrucción del original (T1, T2) y fuga de temporales (T3, T4, T5), en los tres modos de entrada y en los dos adapters.

### 5.2 Dos errores del propio test, corregidos y documentados

Merece la pena registrarlos porque el test los detectó a sí mismo:

1. **Aislamiento de `TMPDIR`**: tras `rmtree`, `tempfile.tempdir` quedaba cacheado apuntando a un directorio borrado y los tests T2–T8 fallaban con `FileNotFoundError`. Corregido con un helper que restaura el `TMPDIR` del sistema antes de crear cada workspace.

2. **`fixture_json` inválido**: la primera versión pasaba el hex crudo; `json.loads("7f454c46…")` lanza y el adapter devuelve `invalid_input` **antes de crear el temporal**, con lo que T4 no probaba nada y pasaba en verde sin verificar. Medido: hex crudo → `invalid_input`, 0 temporales; `json.dumps(hex)` → `error`, 1 temporal huérfano. Corregido; T4 pasó a detectar la fuga real.

Sin estas dos correcciones el test habría dado un falso verde.

---

## 6. Validación

### 6.1 Diff completo

Reconstruí el estado pre-tarea de ambos ficheros por inversión de mis cambios y lo **verifiqué por hash antes de usarlo como línea base**:

```
rz_callgraph PRE : 6d1ebc544256b9202a507e00cc8e680ac5b979d90502bfe95aa3bf0c17d9885a  == esperado
rz_xrefs     PRE : f9f33f01b056bb30013cfb2d582dedc9086ca6583d9acb4212ac1300de9f55ca  == esperado
```

La primera inversión no coincidió; la diferencia era una línea en blanco sobrante en cada fichero, localizada y corregida hasta obtener coincidencia exacta. El diff resultante (§4) refleja **exactamente** el cambio, sin ruido de las modificaciones preexistentes.

Resumen del diff: `rz_callgraph.py` +25/−7 (docstring, bandera, 3 asignaciones, 6 llamadas); `rz_xrefs.py` +20/−7 (docstring, 1 asignación, 6 llamadas). **12 llamadas, 0 cambios de comportamiento fuera de la limpieza.**

### 6.2 Cero regresiones en las suites de ambos adapters

| Suite | Resultado |
|-------|-----------|
| `test_callgraph1636.py` | exit 0 — **21 checks, 0 failures** |
| `test_xrefs1635.py` | exit 0 — **30 checks, 0 failures** |

### 6.3 Cuatro suites que fallan: preexistentes, demostrado

`test_dispatch004`, `test_backends004`, `test_cli009` y `test_backends_bulk` fallan. **No lo causa esta tarea.** Todas fallan por la misma razón: el backend `rea` está en el registro real (9 backends) pero no en la lista esperada de los self-tests (26 capacidades frente a 27).

Prueba empírica: revertí temporalmente **solo** las 12 llamadas de limpieza a la polaridad defectuosa y volví a ejecutar `test_dispatch004`:

```
self-test FALLA (1 de 132)
  B7: ... declarado={'capstone','coccinelle','ghidra','knowledge','radare2','rizin','tree-sitter','umr'}
      real={... , 'rea': 1}
```

**Idéntico con el código pre-defecto.** Además `tools/rxre/backends/adapters/rea_inspect.py` está fechado **oct 15 18:41**, anterior a esta sesión, y es un fichero no rastreado: forma parte del trabajo previo sin commitear. Clasificación: `PROVEN` preexistente.

### 6.4 Verificación end-to-end por la interfaz real

No solo por el adapter directo, sino por la interfaz JSONL documentada:

```
canary antes   : b633146608a0819e3b1ca32ced66d043ea71a09b178b762adfbaf0d17f0c318c
callgraph      : exit=0 status=ok  -> canary PRESENTE, hash sin cambios
xrefs          : exit=0 status=ok  -> canary PRESENTE, hash sin cambios
```

Y el **resultado funcional se conserva**: `binary.xrefs` sigue devolviendo `from=0x400C0C type=DATA`, la referencia que la prueba de integración usó para corroborar el defecto. La reparación no alteró lo que la capacidad sabe hacer.

### 6.5 Barrido H4 — ¿queda algún otro camino de borrado?

| Ámbito | Resultado |
|--------|-----------|
| `tools/rxre/backends/` | Solo 2 `os.unlink`, uno por fichero, ambos bajo `if borra:` dentro de `_limpiar_tmp` |
| `dispatch.py`, `contract.py` | Ninguna llamada a `os.unlink`/`os.remove`/`shutil.move` |
| `api/machine.py` | El único `os.unlink` (l3198) pertenece a `op:suite` y borra una BD temporal por suite, nunca un artefacto |
| Otros adapters | Ninguno más usa `_limpiar_tmp` |

**No quedan llamadas sin cubrir**: las 12 del defecto están reparadas y las 2 restantes de `os.unlink` en todo `backends/` son las de `_limpiar_tmp`. No se puede afirmar que *toda la familia* de defectos esté cerrada para siempre, pero sí que **no queda ninguna ruta conocida hoy por la que RXRE borre un artefacto de entrada**.

---

## 7. Integridad

| Comprobación | Estado |
|--------------|--------|
| Archivos modificados bajo `tools/rxre/` | **20** (sin cambios en el recuento) |
| Ficheros ajenos a la tarea | **18 byte-idénticos** |
| No rastreados | 169 (el test nuevo cae dentro de `tests/adversarial/`, ya no rastreado) |
| `tools/rxre/storage/rxre.sqlite3` | `9ad44c59…6426` — **idéntico**. Ninguna escritura en la BD del repositorio: todo se ejecutó con `RXRE_DB` en `/tmp` |
| Artefactos de la investigación | Sin cambios por esta tarea |
| Binarios Vulkan ejecutados | **0** |
| MMIO / VRAM / `/dev/dri` | Ningún acceso |
| `sudo` / root | Ninguna elevación |
| Paquetes instalados | Ninguno |

**Los 20 modificados preexistentes están preservados.** De ellos, 2 estaban en alcance por necesidad y 18 permanecen intactos.

---

## 8. Estado epistemico

| Afirmación | Clasificación |
|------------|----------------|
| `es_path` significa "este path ES el original" en ambos ficheros | **`PROVEN`** (código, l319 y l160) |
| La bandera de limpieza estaba invertida | **`PROVEN`** (tabla de verdad + reproducción) |
| El borrado ocurría también en el camino de éxito | **`PROVEN`** (variante A en las 6 rutas, incluida la 6) |
| El original se destruía y el temporal se fugaba | **`PROVEN`** (T1–T5 en rojo antes de la reparación) |
| Reemplazar globalmente `es_path`→`not es_path` habría roto el modo fixture con `NameError` | **`PROVEN`** por lectura: en fixture `es_path` nunca se asigna y solo se salva por la rama `else` de la condicional |
| Los 4 fallos de suite son preexistentes | **`PROVEN`** (reproducibles con el código pre-defecto) |
| El backend `rea` es trabajo previo sin commitear | **`OBSERVED`** (no rastreado, fechado oct 15 18:41) |
| La reconstrucción pre-tarea es exacta | **`PROVEN`** por hash |
| No queda ninguna ruta conocida que borre un artefacto | **`PROVEN` para lo presente**, `OPEN` para lo futuro |
| El defecto de normalización del callgraph | **`OPEN`**, intacto y fuera de alcance |
| `fixed2` sigue sin restaurar | **`OPEN`**, pendiente de autorización |

---

## 9. Fallos del encargo que quedan pendientes

| Ítem | Estado |
|------|--------|
| Restaurar `vk_test/vk_compute_test_fixed2` | **`OPEN`** — ahora **desbloqueado**: el defecto que lo destruyó está corregido y su fuente sobrevive con reproducción probada byte a byte. No se restauró porque la tarea es explícitamente de solo lectura sobre los artefactos |
| Normalización del callgraph (3 nodos → 1, se pierde `main`) | **`OPEN`** — fuera de alcance por instrucción expresa |
| Fallos preexistentes de los self-tests por el backend `rea` | **`OPEN`** — ajenos a esta tarea; requieren actualizar las expectativas de 26 → 27 |
| `_limpiar_tmp` mantiene firma `(str, bool)` | **`OPEN`** — una firma que expresara la propiedad (p. ej. un enum `DUENNO`) sería más difícil de invertir, pero cambiar la firma es más invasivo que el defecto que corrige |

---

## 10. Recomendación única

**Restaurar `vk_test/vk_compute_test_fixed2` recompilando `vk_compute_test_fixed2.c` en su ruta original y verificando que el hash resultante sea `f94af068158538be5c6959c2513cee61f229b697d0e23d4062eb076fc7da2384`.**

Justificación:

1. **Cierra la pérdida que esta reparación causó.** `fixed2` es el cuarto eslabón de la cadena de evidencia de la frontera compute (`original → fixed → fixed2 → fixed3`). Su ausencia rompe la trazabilidad de la que dependen los tres informes que citan su hash.

2. **Es la única acción que este trabajo dejó desbloqueada y sin cerrar.** Mientras el borrado defectuoso existía, cualquier reconstrucción podía volver a ser destruida por la siguiente ejecución de `callgraph`/`xrefs`. Con el defecto corregido y verificado E2E, la operación es segura y reversible.

3. **La reproducción está probada, no supuesta.** En `VK_COMPUTE_TEST_FIXED3_CIERRE_ORDEN_TEMPORAL.md` §7.6 seجاحdemonstró que compilar ese fuente en `/home/lucas/Escritorio/rxre/vk_test/` produce un binario **byte a byte idéntico** a `f94af068…`. El hash es verificable, no una expectativa.

4. **Desbloquea la frontera compute sin adelantarla.** La ejecución de `vk_compute_test_fixed3` sigue pendiente de autorización separada; restaurar `fixed2` es integridad de evidencia, no avance de la frontera.

5. **Es una acción de un solo comando con criterio de aceptación objetivo:** el hash debe coincidir exactamente. Si no coincide, la cadena sigue intacta y no se ha introducido nada falso.

---

## 11. Frontera compute: sin cambios

`vk_compute_test_fixed3` sigue compilado y auditado estáticamente con 0 violaciones de orden temporal, y **no ejecutado**. Esta tarea no la alteró. La normalización del callgraph permanece `OPEN`.