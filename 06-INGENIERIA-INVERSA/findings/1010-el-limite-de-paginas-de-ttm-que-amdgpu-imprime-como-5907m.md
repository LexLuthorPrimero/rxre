# 1010 · El límite de páginas de TTM que amdgpu imprime como `5907M`: producer, cadena completa, y el error de unidad que dejó la pregunta abierta

```
CLASSIFICATION=DOCUMENTATION+REPAIR+MEASUREMENT · TRACK=STATIC+RUNTIME_LECTURA
AGENTE=AGENT-09 (GART) · FECHA=2026-10-03
CORPUS=RESEARCH/kernelbuild/linux-7.1.3 (amdgpu + drm/ttm, ver §1)
HARDWARE_SCOPE=RX 550 0000:01:00.0 Polaris12/GFX8
WORK_CLASS=READ_ONLY · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=READ_ONLY (/proc/meminfo, /sys/module/ttm, /sys/module/amdgpu, /sys/class/drm)
GPU INTACTA · uid 1000, sin sudo · sin MMIO, sin writes, sin insmod
```

## Qué resuelve

Dos cosas, y la segunda es la que importa.

1. `204` registró como **`NOT_DETERMINED`** — *"De dónde sale exactamente
   `ttm_tt_pages_limit`"* — con un motivo escrito: *"es una función de TTM que no
   está en este corpus"*. **Ese motivo era falsable, y es falso hoy.**
   `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/ttm/` existe. La cadena
   entera está trazada y **medida con residual 0**.

2. `204` dejó además una discrepancia sin resolver: *"el observado son 5.907; no
   es exactamente la mitad y la diferencia hay que explicarla"*. **La diferencia
   no había que explicarla: la creó un error de unidad del propio `204`.**

> **La pregunta que `204` dejó abierta no era una pregunta sobre la máquina.
> Era una pregunta sobre una aritmética equivocada que el propio `204` escribió.**

## 1 · El bloqueo de `204` era una afirmación, y las afirmaciones caducan

```
204 §"Lo que NO cierra":   "De dónde sale exactamente ttm_tt_pages_limit"  → NOT_DETERMINED
                           "es una función de TTM que no está en este corpus"   ← el motivo
```

Comprobado sobre el árbol, no sobre la memoria:

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/       →  amd            (sin ttm, sin scheduler)
RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/   →  amd  scheduler  ttm
```

**El corpus creció.** `working/` —la raíz que citan los hallazgos— sigue sin
`ttm/`, y `kernelbuild/` ya lo tiene. El `NOT_DETERMINED` no se hereda: se
reabre porque su **causa declarada** desapareció.

Esto no es una excepción. Es la categoría ordinary de `NOT_DETERMINED`: un estado
que nombra su propio bloqueo es un estado **revisable**, y revisar un bloqueo
cuando es barato es más barato que dejar una pregunta abierta.

## 2 · La cadena, producer → carrier → consumer

Tres ficheros, tres papeles, y el valor medio medido en runtime.

**PRODUCER** — `drivers/gpu/drm/ttm/ttm_device.c:88-92`:

```c
/* Limit the number of pages in the pool to about 50% of the total
 * system memory.
 */
num_pages = ((u64)si.totalram * si.mem_unit) >> PAGE_SHIFT;
num_pages /= 2;
```

**CARRIER** — `drivers/gpu/drm/ttm/ttm_tt.c:480-481` y `:532-536`:

```c
if (!ttm_pages_limit)
        ttm_pages_limit = num_pages;
...
unsigned long ttm_tt_pages_limit(void)
{
        return ttm_pages_limit;
}
```

`ttm_pages_limit` es además un `module_param_named(pages_limit, ..., 0644)`
(`ttm_tt.c:55`) — o sea **legible desde sysfs por cualquier usuario**.

**CONSUMER** — `drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.c:2140` y `:2160-2161`:

```c
gtt_size = ttm_tt_pages_limit() << PAGE_SHIFT;
...
dev_info(adev->dev, " %uM of GTT memory ready.\n",
         (unsigned int)(gtt_size / (1024 * 1024)));
```

**Y el observable, sin privilegio y sin riesgo:**

```
$ cat /sys/module/ttm/parameters/pages_limit
1512363
```

## 3 · La reproducción, con residual 0

Instrumento nuevo: **`tools/gttlimit.py`**, reejecutable, read-only. Tres
comprobaciones, tres `PASS`, **residuo cero en las tres**:

| # | Relación | Observado | Derivado | Residuo |
|---|---|---|---|---|
| 1 | `pages_limit == totalram_pages/2` | `1512363` | `1512363` | **0 páginas** |
| 2 | `mem_info_gtt_total == pages_limit << 12` | `6194638848` | `6194638848` | **0 bytes** |
| 3 | `(pages_limit<<12)/MiB` truncado == log de arranque | `5907M` | `5907` | **exacto** |

```
$ python3 tools/gttlimit.py
  OBSERVED_ttm_pages_limit                     1512363
  OBSERVED_totalram_pages                      3024726
  OBSERVED_mem_info_gtt_total_bytes            6194638848
  DERIVED_expected_pages_limit_half_of_totalram 1512363
  DERIVED_gtt_size_bytes                       6194638848
  DERIVED_gtt_mib_truncated                    5907
  RESIDUAL_limit_minus_half_totalram_pages     +0
  RESIDUAL_gtt_total_minus_derived_bytes       +0
  [PASS] x3      VERDICT: CLOSED      rc=0
```

**La cadena completa, de principio a fin, con el número en cada eslabón:**

```
si_meminfo().totalram   →  3 024 726 páginas      (OBSERVED, /proc/meminfo)
/ 2                      →  1 512 363 páginas      (DERIVED, ttm_device.c:92)
ttm_pages_limit         →  1 512 363              (OBSERVED, sysfs, idéntico)
<< PAGE_SHIFT           →  6 194 638 848 B        (DERIVED, amdgpu_ttm.c:2140)
mem_info_gtt_total      →  6 194 638 848 B        (OBSERVED, idéntico)
/ 1 MiB, truncado       →  5 907                  (OBSERVED en el log de arranque)
```

**Ningún eslabón es una aproximación.** Es la misma categoría de resultado que
`054` obtuvo con los cuatro números de VRAM/GART, y por la misma razón: la
fórmula del driver más el estado real de esta placa.

## 4 · El error del `204`, y por qué dejó una pregunta fantasma

`204` escribió, textualmente:

> *"El sistema tiene 11.542 MiB, y la mitad son 5.771; el observado son 5.907,
> así que no es exactamente la mitad y la diferencia hay que explicarla."*

**`204` tomó `MemTotal = 12098912 kB` y lo leyó como `11.542 MiB`. No lo es.**

```
12098912 kB  →  12098912 / 1024  =  11 815,34 MiB
                                      ^^^^^^^^
204 asserted 11 542 MiB   →  error de  273,34 MiB
```

Y la cuenta correcta **reproduce el observado exactamente**:

```
11 815,34 MiB / 2 =  5 907,67 MiB  →  truncado  5 907      = el log de arranque
```

**La "diferencia" de 136 MiB entre 5.771 y 5.907 era el error de conversión.**
No había nada que explicar en la máquina.

**Y el error tiene una causa identificable, que es la parte útil.** `204`
calculó dividiendo **MiB entre 2**, cuando el driver divide **páginas entre 2** y
luego convierte. Los dos dan el mismo resultado *si y solo si* `totalram` es un
múltiplo par de páginas y la conversión es exacta — y aquí lo es, pero por
casualidad de alineación, no por construcción. Dividir en páginas primero y
convertir después es lo que hace el código, y es lo único que sobrevive cuando
los dos caminos divergen.

Esto reencuadra la observación de `204 §4` — *"ningún número que decide una
conclusión se calcula mentalmente"* — y le añade el complemento: **tampoco se
convierte de unidad mentalmente**. `204` acierta la regla para la aritmética y
la incumple en la conversión, en el mismo documento, y el resultado es una
pregunta fantasma con cuatro meses de vida útil.

## 5 · Un `ERROR` del propio `204`, y su coste

| Afirmación en `204` | Estado real | Clase |
|---|---|---|
| "el sistema tiene 11.542 MiB" | 11.815,34 MiB | **`ERROR`** |
| "la mitad son 5.771" | 5.907,67 MiB | **`ERROR`** (derivado del anterior) |
| "no es exactamente la mitad, hay que explicarla" | **falso** | **`ERROR`** |
| "De dónde sale `ttm_tt_pages_limit` → `NOT_DETERMINED`" | cerrado, §3 | **resuelto, no contradictorio** |

**Esto no devalida `204`.** Todo lo demás de `204` que he re-verificado sigue en
pie: `gart_size = 256 MiB` escrito a fuego, el motivo *"all engines support
GPUVM"*, el clamp de `amdgpu_gmc.c:307` que no se dispara, `smu_prv_buffer_size
= 0`, GTT/GART/VRAM como tres magnitudes distintas, y la separación §F
entre traducción GPUVM y decodificación MC. **La cadena del GART queda
entera; lo que estaba sin cerrar era el otro lado de la frontera.**

Lo que sí quedaannotated: `204` escribió una fila `NOT_DETERMINED` cuyo motivo
era *"no está en este corpus"*. Motivos así son **caducables**, y este caducó.
Un `NOT_DETERMINED` con motivo estructural (`NOT_IN_SYS`, función de silicio
ausente) es sólido. Uno con motivo de inventario (`no está en el corpus`) es una
afirmación sobre un árbol de ficheros, y **los árboles crecen**.

## 6 · Lo que este hallazgo NO cierra

| Afirmación | Estado | Por qué |
|---|---|---|
| `ttm_tt_pages_limit` = `si.totalram/2` páginas | **`PROVEN`** | §2, tres ficheros |
| …y reproduce `5907M` y `mem_info_gtt_total` con residual 0 | **`PROVEN`** | §3, `tools/gttlimit.py` |
| El valor real de esta placa | **`OBSERVED`** | sysfs, `1512363` |
| `smu_prv_buffer_size` contributes 0 al GART | **`PROVEN_DERIVED`** | ya en `204`; coherente con 256 MiB justos |
| El GTT es RAM del host, no ventana de direcciones | **`PROVEN`** | ya en `204`; §3 lo confirma por la vía del `sysfs` |
| Si el GART puede crecer en runtime | **`NOT_DETERMINED`** | no tocado aquí |
| `gartsize` / `gttsize` reales de esta placa | **`NOT_READABLE`** | ver §7 |
| Por qué `usage` (59.9 MB) no cuadra con la suma de "used" | **`NOT_DETERMINED`** | sigue de `100`; fuera de este nodo |

## 7 · Un límite de permisos, registrado como lo que es

```
$ cat /sys/module/amdgpu/parameters/gartsize
cat: ... Permiso denegado
$ cat /sys/module/amdgpu/parameters/gttsize
cat: ... Permiso denegado
```

**Ambos existen.** Aparecen en el listado de `/sys/module/amdgpu/parameters/` y
son `module_param` de `0600`. Lo que falta es **permiso de lectura**, no el
parámetro. Es `READ_ONLY_BLOQUEADO_POR_PERMISO`, y se declara así para que nadie
lo lea como *"el driver no tiene ese parámetro"*.

> Nota de método, y es la segunda vez en este turno. Primeiro leí
> `/sys/module/amdgpu/parameters/gtt_size` y el `cat` falló; el nombre real es
> **`gttsize`**, sin el underscore. Un nombre mal escrito devuelve
> `ENOENT` y es indistinguible de "no existe". El directorio lo desambigua.
> **`NAME_NOT_FOUND` tratado como ausencia** es el error que este proyecto
> registra nueve veces, y loiréste otra vez por el mismo camino si no lo anoto.

`204` ni `100` pueden leerlo sin root. `977 §4` ya lo había marcado
como `DEFERRED_RUNTIME`; **sigue siendo `DEFERRED_RUNTIME`, y no lo
convierto en `PROVEN` porque nadie lo ha leído.** Lo único que queda establecido
es que la puerta existe, que su modo es `0600`, y que su valor en esta placa es
`NOT_READABLE` para uid 1000.

## 8 · El instrumento: un defecto mío, encontrado y corregido

`tools/gttlimit.py` en su primera versión **falló su propia comprobación 2** y
reportó `mem_info_gtt_total = UNREADABLE(No such file or directory)`.

Eso no era un hecho sobre la máquina. Era un defecto del selector: tomaba **el
primer `cardN`**, que es la **iGPU Intel**, que no tiene `mem_info_gtt_*` en
absoluto. El `ENOENT` era mío, y el `FAIL` que produjo era una afirmación
falsa sobre el hardware presentada con la autoridad de un resultado medido.

Se corrigió seleccionando por **la capacidad que la comprobación necesita** en
lugar de por posición. Re-medido: 3/3 `PASS`.

> Un instrumento que elige su objetivo por posición y no por capacidad
> convierte una diferencia de hardware en un `NOT_FOUND`, y un `NOT_FOUND` en
> un `FAIL`. Los dos pasos son falsos y ninguno se ve en el código.

**Validez del instrumento:**

```
Reproducibilidad   dos corridas --json, salida byte a byte identica
                   sha256 dc33f7427ec0c58e195133958eea282d7ba09251fb27c28673550c2f6ec6f4f9
                   (ambas)
Autocomprobacion   VERDICT propio: CLOSED→rc 0, NOT_CLOSED→rc 1. Con las tres
                   relaciones explicitadas, un CLOSED no puede venir de un
                   FAIL silencioso del generador.
Alcance            read-only. No abre /dev/dri, no escribe en la GPU,
                   no necesita privilegio. uid 1000.
```

## 9 · Un hueco de instrumento que encontre de paso: `nextnum.py` no pasa de 999

No es de mi subsystema, pero me impidió numerar este hallazgo y lo dejo escrito
porque **el próximo lo va a necesitar**:

```
$ python3 tools/nextnum.py --reservar 1000
  1000: MALO   el numero debe ser de 3 cifras

NUM_RX = re.compile(r'^(\d{3})[-_](.+)\.md$')
```

Consecuencias, medidas:

1. `--reservar` **no puede** asignar `>= 1000`. No es un límite blando: es un
   `rc=2`.
2. El índice de ocupación usa ese mismo `NUM_RX`, así que **un fichero de 4
   cifras es invisible para la herramienta que decide qué números están libres**.
   Verificado: `997-x.md` VISIBLE · `1000-z.md` **INVISIBLE**.
3. Pero `siguiente()` **propone** `1000`…`1005` como *"ninguno ocupado"*. Propone
   números que su propio índice no puede verificar y que su propio `--reservar`
   no puede asignar.

**Y el efecto compuesto es el que importa:** el numerado del proyecto **está en
su techo de 3 cifras** — `999` ya lo ocupan dos ficheros — mientras la
herramienta que reparte números anuncia cinco números siguientes que no puede
reservar ni auditar. La próxima sesión que numeré así choca, y el síntoma
aparecerá como *hallazgo duplicado*, que es exactamente la plaga que este
proyecto ya registra 72 veces.

**No lo corrijo aquí:** es trabajo de otro nodo, y `AGENTS.md` §COORDINACION
dice que un problema de otro es de otro. Lo que hago es **no depender de él**:
reservé `1010` a mano en `_reservas/`, verificado libre, y lo declaro.

## 10 · Procedencia, para que esto sea reproducible sin este fichero

```
STATIC  RESEARCH/kernelbuild/linux-7.1.3
        drivers/gpu/drm/ttm/ttm_device.c:88-92   producer, si_meminfo /2
        drivers/gpu/drm/ttm/ttm_tt.c:55,480-481,532-536   carrier + module_param 0644
        drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.c:2140,2160-2161   consumer + log
RUNTIME (READ_ONLY, uid 1000, sin sudo)
        /sys/module/ttm/parameters/pages_limit    → 1512363
        /sys/module/amdgpu/parameters/{gartsize,gttsize}  → Permiso denegado (existen, 0600)
        /sys/class/drm/card*/device/mem_info_gtt_total   → 6194638848
        /proc/meminfo MemTotal                     → 12098904 kB
INSTRUMENTO  tools/gttlimit.py  (nuevo)
FLAGS        python3 $(python3 -V 2>&1 | cut -d' ' -f2), sin flags
COMPILAR     cd /home/lucas/Escritorio/RX550-INVESTIGACION && python3 tools/gttlimit.py
```

**Nota sobre la deriva del observado.** `100` registró
`mem_info_gtt_total = 6194642944`; hoy es `6194638848`. La diferencia son
**exactamente 4096 bytes = 1 página**, y es la deriva normal de `si.totalram`
entre dos instantes. No es una contradicción y **no se anota como tal**: es el
mismo número con dos páginas de `totalram` de diferencia, y por eso la
comparación de este documento es contra `pages_limit` —el valor **congelado** en
sysfs— y no contra un `MemTotal` leído en otro momento.

**Encadenada con:** `204` (corrige su fila `NOT_DETERMINED` y su aritmética),
`100` (misma magnitud, mismo `sysfs`), `243` (los 5.907 MiB del GTT),
`067`, `054`, `164` (cadena GART), `081`/`088` (`SYSTEM_ACCESS_MODE`).

## 11 · Qué cambió de estado

```
ttm_tt_pages_limit: origen exacto                    NOT_DETERMINED → PROVEN
  motivo del NOT_DETERMINED ("no está en el corpus")  REFUTED (corpus núcleo lo tiene)
5907 vs "la mitad de MemTotal": discrepancia          ERROR → resuelto, era error de unidad
204 "el sistema tiene 11.542 MiB"                     ERROR (son 11.815,34)
204 "hay que explicarla la diferencia"                ERROR (no hay diferencia)
mem_info_gtt_total de 100 (6194642944) vs hoy         NO es contradiccion: deriva de 1 pagina
gartsize / gttsize de esta placa                      DEFERRED_RUNTIME → NOT_READABLE (0600)
GART: apertura, base, end, page size, BEST_FIT        sin cambios (067/054/164 intactos)
nextnum.py no puede asignar ni ver números >= 1000     hueco de instrumento, registrado
AGENT-09 · GART                                        sin cambio en su cadena: ya cerrada
```

**Y la conclusión de fondo, que es la que me traje:**

> **El `NOT_DETERMINED` de `204` sobre `ttm_tt_pages_limit` no era un hueco de
> conocimiento sobre la máquina. Era un hueco de inventario sobre el árbol de
> ficheros, y un error de conversión de unidades que lo disfrazaba de pregunta
> física.** El `NOT_DETERMINED` decía la verdad sobre sí mismo —"no está en el
> corpus"— y por eso se podía cerrar: un hallazgo que nombra su bloqueo es un
> hallazgo revisable. El que no nombra su bloqueo es el que se queda abierto
> para siempre.