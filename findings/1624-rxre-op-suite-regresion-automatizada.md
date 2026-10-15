# 1624 — RXRE: la suite de regresión como `op:suite` (y los bugs que destapó)

- Fecha: 2026-10-15
- Clasificación: **DEMOSTRADA** — `op:suite` corre las 39 suites en 169 s
  (3 jobs) y ahora están **39/39 verdes**.

## Qué era manual y ahora es una op

Hasta hoy, verificar la regresión era: descubrir `test_*.py` a mano,
lanzarlos en paralelo con DB aislada y TMPDIR seguro, y sumar rc. Trabajo
repetible que vivía en la memoria de una sesión, no en la CLI.

`{"op":"suite","jobs":3}` hace eso y devuelve JSON con rc, duración y el
**motivo** de cada fallo. Sobre `run_baseline.py` (que ya existía):

| | `run_baseline.py` | `op:suite` |
|---|---|---|
| directorio temporal | `tempfile.mktemp()` → `/tmp` (medido: tmpfs al 100%, revienta) | directorio con espacio medido |
| paralelismo | secuencial, 300 s por suite | paralelo, `jobs` configurable |
| salida | texto plano | JSON con `resultado/motivo/duración` |
| clasificación | PASS/FAIL | `ok` / `fail` / `entorno` / `timeout` |

`timeout` está separado de `fail` a propósito: MEDIDO, 120 s hacía que
`test_container1632` (análisis real de ~147 s) saliera como roto cuando solo
era **lento**.

## Los bugs que automatizar destapó (el valor real)

1. **`store.eventos_por_trace()` no existía.** La columna `trace_id` estaba
   escrita y NADIE la leía: `test_r001_trace_id` reventaba con
   `AttributeError`. Implementada (read-only).
2. **`evento_id` colisionaba.** 4 llamadas idénticas daban 3 eventos, porque
   `operation_id` sale como `"COLISION:res_..."` (result_id determinista, por
   diseño) y no distingue reintentos. El `trace_id` es justamente la unidad
   que varía por invocación: ahora entra en el hash.
3. **`op:run` no propagaba `trace_id`.** Ni a la respuesta ni al evento.
   Implementado: `env["trace_id"]` (una sola ruta, sin recalcular hashes).
4. **El fallo de la auto-correlación era INVISIBLE.** `registrar_investigacion`
   capturaba la excepción en `auto_correlacion_error` y `_handle_scan` no lo
   mostraba: `op:scan` devolvía `status: ok` con **0 correlaciones** durante
   días. Ahora viaja como `limitation`.
5. **Aserciones rancias.** El conteo de ops iba 13→14→15→16 y los tests
   seguían clavados en el número viejo; `dispatch.ADAPTERS` pasó de 12 a 26.
   Los dos fallaban sin medir nada del código.
6. **`test_umr_decode003` crasheaba** con `AttributeError: 'NoneType' object
   has no attribute 'startswith'`: `.get("operation_id", "")` devuelve `None`
   cuando la clave EXISTE con valor None. Un crash, no una aserción.

Del 2 al 6 ninguno era visible sin ejecutar la suite entera seguido.

## Lo que la suite clasifica como `entorno` (no código)

MEDIDO en este host: `spatch` (coccinelle) falla con
`Sys_error("No space left on device")` — escribe a `/tmp` internamente y el
tmpfs está al 100% (5,2G de una copia de trabajo de otro proceso). No es un
fallo de RXRE. `op:suite` acepta `entorno_declarado` para marcarlo sin
adivinar, y extrae el motivo de cada fallo para que el operador lo vea.

## Regresión

- `op:suite` → 39/39 ok, 0 fail, 0 entorno, 0 timeout (169 s, 3 jobs).
- `test_cli009` → 93/93 (el conteo de ops pasó a 16 con `suite`).
