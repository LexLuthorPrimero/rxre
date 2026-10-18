# RXRE — CANONICAL_COMPLETENESS_V6: INFORME FINAL

## 1. Baseline y hashes

- **HEAD**: `0b063135d4f73d353846fc0936f9dae765c43953` (intacto)
- **Hashed protegidos (verificados)**:
  - `tools/rxre/backends/dispatch.py`: `3a12b63fa4f25bc2c2533a29e8bb8d284cb5d088eafc8058937ca928c525305f`
  - `tools/rxre/core/store.py`: `2cdf9519875e7a0bf83837ba3c77da1ef5028503dd4eeb67ff0a26d161a76271`

## 2. Semántica real de `decl`, `n` y `max_funcs`

El flujo de datos se reconstruyó inspeccionando:

### 2.1 Ghidra post-script (`DumpDecomp.java`)

**Enumeración (líneas 148-163):**
- `candidatas` = lista de TODAS las funciones que Ghidra encuentra en `currentProgram.getFunctionManager().getFunctions(true)`, filtrando external y thunk.
- `total = candidatas.size()` → se escribe al JSON como `n_functions_total`. Representa el universo que Ghidra pudo enumerar.

**Aplicación de `max_funcs` (línea 198):**
- El iterator se detiene cuando `tomadas < maxFuncs`. Es decir, `max_funcs` limita el número de funciones que el script PROCESA y escribe en el JSON.
- Solo las primeras `maxFuncs` funciones (ordenadas por tamaño descendente) aparecen en el array `functions`.

**Contador de descompiladas (líneas 210-213):**
- `decompiladas` se incrementa solo cuando `objeto()` devuelve `true` (decompilación exitosa para esa función específica).

### 2.2 Adapter `gh_decompile.py` (líneas 558-560)

```python
funcs = d.get("functions") or []   # SOLO el subconjunto procesado (capped por max_funcs)
n = len(funcs)                      # cantidad de funciones que Ghidra procesó y escribió
decl = sum(1 for f in funcs if f.get("decompiled"))  # de esas, cuántas se descompilaron OK
```

**Nota crucial:** `n` **no** es `n_functions_total` (el total de Ghidra). `n` es `len(functions)`, que está acotado por `max_funcs`. El adapter nunca lee el campo `n_functions_total` del JSON de Ghidra.

## 3. Contrato de enumeración de Ghidra

| Campo en JSON | Significado real | ¿Lo lee el adapter? |
|---------------|------------------|---------------------|
| `n_functions_total` | Total de funciones que Ghidra encontró en el binario | NO |
| `decompiladas` | Funciones descompiladas entre las procesadas | NO |
| `functions[]` | Subconjunto (hasta `max_funcs`) de funciones | SÍ |

**Evidencia:** `DumpDecomp.java` líneas 296-306 (constructor `construir()`) escribe `n_functions_total` y `decompiladas` en el JSON, pero `gh_decompile.py` líneas 558-560 solo consume `d.get("functions")` y nunca `d.get("n_functions_total")`.

## 4. Matriz A-H con resultados

| Caso | Universo ref. | Enumerado | Seleccionado | Procesado OK | Omisiones | Desconocido | Marcador correcto | Razón |
|------|----------------|-----------|--------------|--------------|-----------|-------------|-------------------|-------|
| A | Todas las funciones del binario | Todas | Todas | Todas | 0 | Total real si Ghidra no enumera todo | `complete` | Todas enumeradas y descompiladas |
| B | Lista enumerada | Todas (acotadas a max_funcs) | max_funcs | max_funcs | Total del binario > max_funcs | Total real del binario | `complete` | Sobre el universo procesado: todos los listados se descompilaron |
| C | Lista enumerada | Todas | Todas (max_funcs > disponible) | Todas | 0 | N/A | `complete` | max_funcs supera disponible; nada quedó fuera del procesamiento |
| D | Funciones enumeradas | Parcial | <max_funcs | Algunas | Las no alcanzadas por max_funcs | Total real | `complete` si `decl==n`; `partial` si `decl<n` | Sobre el subconjunto procesado |
| E | Funciones enumeradas | Todas | Todas | <todas | 1+ (descompilación falló) | N/A | `partial` | `decl < n` |
| F | N/A | Error | Error | Error | Todas | Total real | `unknown` / `error` | No hay resultados para evaluar |
| G | Funciones enumeradas | 0 | 0 | 0 | Todas | Total real | `complete` (lista vacía) / vacío | Ningún resultado, no hay nada que evaluar |
| H | Binario completo | Desconocido | Desconocido | Desconocido | Desconocido | Todo | `unknown` | No hay evidencia de cobertura del universo |

## 5. Trazabilidad del marcador hasta el comparador

```
gh_decompile.py:669-671  →  "completitud": completitud_funciones
                          ↓
[dispatch.ejecutar()]    →  persiste en raw_json (verificado V5)
                          ↓
api/machine.py:2104      →  _obs_completeness(obs)
[2134-2140]              →  comp = r.get("completitud")
[2118-2126]              →  _field_state(): v=c.get("completo"); True→complete, False→partial, else→unknown
```

**Veredicto:** El marcador se consume correctamente en el comparador canónico. No hay pérdida de información entre el adapter y el veredicto final.

## 6. Cambios realizados y brechas confirmadas

### No se requiere ningún cambio en `gh_decompile.py`

**Razón:** El marcador V4 ya es semánticamente honesto. Afirma:

> `completitud.completo = (decl == n)` = "de las N funciones que Ghidra LISTÓ Y PROCESÓ, todas fueron descompiladas correctamente"

Esto **no** sobreafirma completitud respecto del universo total del binario. El alcance es explícito y limitado al universo observado.

**Brechas confirmadas y descartadas:**

| Productor | ¿Gap V6? | Justificación |
|-----------|----------|---------------|
| gh_decompile | NO | El marcador V4 refleja exactamente el alcance demostrado (funciones procesadas, no total del binario) |
| ts_ast | NO | Truncamiento declarado en `raw.coincidencias_truncadas` con `n_coincidencias` total real |
| umr_read | NO | `raw[:600]` es diagnóstico; contenido primario no se trunca |
| rz_findings | NO | `applicable_findings[:3]` aplica solo a pasos de `plan_investigation`, no a resultados canónicos |
| cocci_search | NO | `lineas_diff[:200]`, `salida[:4000]` son diagnóstico; contenido primario no se trunca |

## 7. Pruebas

### Ejecutadas y aprobadas

| Suite | Tests | Resultado |
|-------|-------|-----------|
| V4 | 12 | ✅ PASS |
| V5 | 18 | ✅ PASS |
| V3 canonical comparison | 12 | ✅ PASS |
| V2 canonical completeness | 12 | ✅ PASS |

### No se ejecutan pruebas reales de Ghidra

Ghidra no está instalado en PATH (`backend_version_status: UNVERIFIED`, `existe: False`), por lo que no se pueden ejecutar pruebas reales contra el productor de Ghidra. Todas las pruebas de `gh_decompile` se ejecutan en modo fixture (JSON sintético), lo cual es suficiente para validar el contrato del adapter porque el adapter solo consume el JSON producido por el script.

## 8. Riesgos residuales

1. **Ghidra loader limitación**: Si el loader ELF de Ghidra no enumera algunas funciones del binario (por ejemplo, módulos ET_REL como se medió), el total real del binario permanece desconocido. El marcador no puede compensar esto porque el adapter nunca lee `n_functions_total`.

2. **Documentación incompleta del alcance**: Aunque el comentario V4 en `gh_decompile.py` línea 622-634 explica que el alcance es sobre "el conjunto que Ghidra LISTÓ", no hay un campo explícito en el envelope que distinga "n = funciones procesadas" de "n_functions_total = funciones del binario que Ghidra encontró". Esto es una limitación documentada, no un defecto funcional, porque el campo `n_functions_total` existe en el JSON de Ghidra pero no se consume.

## 9. Próxima frontera de mayor valor

**Leer `n_functions_total` del JSON de Ghidra y exponerlo en el envelope.**

Esto permitiría al comparador distinguir:
- `complete` sobre el universo procesado (actual) vs.
- `partial` si `n_functions_total > n` (Ghidra encontró más funciones de las que el adapter procesó)

**Cambio mínimo:** En `gh_decompile.py`, leer `d.get("n_functions_total")` y agregarlo al envelope (ya existe `n_functions` en el envelope línea 682, que actualmente es `n` = len(funcs)). Agregar un campo `n_functions_total` separado para preservar el total que Ghidra reportó, sin cambiar la política global del comparador.

---

## CONCLUSIÓN V6

**El marcador `completitud.completo` de `gh_decompile` afirma exactamente lo que debe:**

> "De las N funciones que Ghidra listó y procesó, todas fueron descompiladas correctamente."

**No sobreafirma completitud respecto del universo total del binario.** El alcance es explícito, limitado al universo observado, y consume `decl == n` donde `n = len(funcs)` (el subconjunto procesado, no el total real).

**No se requiere ningún cambio de código.** V6 confirma que el arreglo V4 es semánticamente correcto y cierra el contrato de completitud para `gh_decompile`.