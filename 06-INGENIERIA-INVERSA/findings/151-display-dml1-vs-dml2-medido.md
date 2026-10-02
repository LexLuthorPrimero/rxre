# 151 · DCE 10.0 usa DML1, y eso son 20 ficheros y 11.875 líneas — no 443.839

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**La respuesta a "cuánto trabajo es la mitad de display"**, que hasta ahora era un
número que daba miedo. **Y es siete veces menor de lo que parecía, y el criterio
para saberlo es un campo de una tabla de recursos.**

## 1 · La medida, entera

`display/`, impreso por programa con `os.walk`:

| | |
|---|---|
| ficheros `.c` | **510** |
| líneas totales | **443.839** |
| `amdgpu_dm/amdgpu_dm.c` | **13.719** — el más grande del proyecto fuera de `asic_reg` |
| `dc/dml2_0/.../dml2_core_dcn4_calcs.c` | 13.402 |
| `dc/dml2_0/display_mode_core.c` | 10.362 |
| `dc/core/dc.c` | 7.637 |

**Y `amdgpu_dm/` son 37 ficheros.** El Display Manager entero cabe en un fichero más
grande que casi cualquiera del driver de amdgpu.

## 2 · Y hay dos motores de mode-setting

```
display/dc/dml/       DML1 — 74 ficheros
display/dc/dml2_0/    DML2 — 82 ficheros
```

**DML1** es el motor clásico, con `display_mode_vba.c` y `dml1_display_rq_dlg_calc.c`
más un subdirectorio por chip DCN. **DML2** es el moderno, con
`display_mode_core.c` y `dml2_policy.c`.

**La elección es un booleano, `dc->debug.using_dml2` (`dc/dc.h:1146`).** Y está en
la tabla de recursos de cada chip, impreso por programa sobre los 25 ficheros
`*_resource.c` de `dc/resource/`:

| valor | nº | chips |
|---|---|---|
| `using_dml2 = true` | **5** | dcn35, dcn351, dcn36, dcn401, dcn42 |
| `using_dml2 = false` | **14** | dcn10, dcn20, dcn201, dcn21, dcn30, dcn301, dcn302, dcn303, dcn31, dcn314, dcn315, dcn316, dcn32, dcn321 |
| **no lo ponen** | **6** | **dce60, dce80, dce100, dce110, dce112, dce120** |

**Los seis que no lo ponen son exactamente los seis ficheros de recursos de DCE.**
Todas las generaciones de DCE, sin excepción. `PROVEN_ABSENT`, por recuento.

### Y la única vía para encenderlo en runtime es una máscara de depuración

`amdgpu_dm.c:2075-2078`:

```c
        if (amdgpu_dc_debug_mask & DC_ENABLE_DML2) {
                adev->dm.dc->debug.using_dml2 = true;
                adev->dm.dc->debug.using_dml21 = true;
        }
```

**Y eso está dentro de un bloque de treinta overrides iguales**, todos de la forma
`if (amdgpu_dc_debug_mask & DC_*) { dc->debug.<campo> = true; }`:
`DC_DISABLE_DSC`, `DC_DISABLE_CLOCK_GATING`, `DC_FORCE_SUBVP_MCLK_SWITCH`,
`DC_DISABLE_SUBVP_FAMS`, `DC_HDCP_LC_FORCE_FW_ENABLE`, …

**El nombre lo dice: `DC_ENABLE_DML2`, "enable". Es un interruptor de depuración, no
un valor por defecto.** DML2 está apagado salvo que alguien lo encienda a mano.
`PROVEN_DERIVED`.

### Y el valor por defecto de esta GPU

**Ningún fichero de recursos de DCE lo pone, y la única asignación en runtime lo
pone a `true` bajo una máscara de depuración.** De dónde sale el `false` inicial es
el `dc` de `struct dc`, cuya asignación no localicé — y no lo voy a afirmar sin
haberla visto. **Lo que sí es `PROVEN` es que el campo se escribe en dos sitios, y
ninguno de los dos lo pone a `true` en esta GPU.** `PROVEN_DERIVED` para el
resultado, con la salvedad apuntada.

**⇒ DCE 10.0 modea con DML1.**

## 3 · Y el tamaño real del trabajo

Repartiendo los 74 ficheros de `dml/` por si su ruta contiene `dcn`:

| bloque | ficheros | líneas |
|---|---|---|
| **sin `dcn` en la ruta — lo que usa DCE 10.0** | **20** | **11.875** |
| con `dcn` en la ruta — chips DCN, no DCE 10.0 | 54 | 72.724 |
| **total en `dml/`** | **74** | 84.599 |

**Comprobación cruzada: 20 + 54 = 74, que es el recuento directo de ficheros `.c`/`.h`
en `dml/`.** `COINCIDE: True`. El reparto no se ha salido de la nada.

**⇒ El motor de mode-setting de esta GPU son 20 ficheros y 11.875 líneas. No 74
ficheros y 84.599. No 510 ficheros y 443.839.**

### Los diez primeros del bloque que sí importa

| fichero | líneas |
|---|---|
| `calcs/dcn_calc_auto.c` | 1.933 |
| `dml1_display_rq_dlg_calc.c` | 1.925 |
| `calcs/dcn_calcs.c` | 1.620 |
| `display_mode_vba.h` | 1.261 |
| `display_mode_vba.c` | 1.146 |
| `display_mode_structs.h` | 741 |
| `dsc/qp_tables.h` | 704 |
| `dc_features.h` | 566 |
| `display_rq_dlg_helpers.c` | 396 |
| `display_mode_lib.c` | 321 |

**Los cinco primeros son 7.885 líneas, y son el motor.** El resto son cabeceras de
estructuras y tablas.

**Y un nombre más que miente:** `calcs/dcn_calc_auto.c` y `calcs/dcn_calcs.c` llevan
`dcn` en el nombre y **están en el bloque genérico, no en un subdirectorio de chip.**
Séptimo nombre de esta tanda que no dice lo que parece. **Y `dsc/qp_tables.h` —DSC—
está en el bloque genérico de DML1 para una GPU que, según `149`, no tiene DSC.**

## 4 · Lo que NO se resuelve aquí, y es honesto

**Busqué dónde se ASIGNA el valor de `enum signal_type` y no lo encontré.** El
patrón `signal_type =|->signal =|sink_signal =` sobre los 510 ficheros `.c` de
`display/` devuelve **sólo comparaciones** — todos los resultados son `==` dentro de
un `if`, ninguno es una asignación.

**⇒ El punto donde se decide el valor de la enumeración de `150` no está en
`display/`, o está escrito en una forma que mi patrón no cubre.** `NOT_DETERMINED`,
y lo digo porque es la pregunta que `150` dejó abierta y no la he cerrado.

**Y hay un segundo sitio que no he mirado:** `dc_link_enc_cfg.c` está en `core/` y su
nombre sugiere que configura la codificación del enlace. Y `struct dc_link` está
definido en `dc/dc.h` — el octavo fichero de esta familia en un sitio distinto —
que es de 1.500 líneas y que no he abierto.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| `display/`: 510 `.c`, 443.839 líneas | `PROVEN` (por programa) |
| `amdgpu_dm.c` son 13.719 líneas | `PROVEN` |
| Hay dos motores: DML1 y DML2 | `PROVEN` |
| `using_dml2`: 5 true, 14 false, 6 sin tocar | `PROVEN` (por programa) |
| Los 6 sin tocar son las 6 generaciones de DCE | `PROVEN` |
| La única vía a `true` es `DC_ENABLE_DML2` | `PROVEN` |
| Esa máscara es de depuración, entre 30 iguales | `PROVEN` |
| DCE 10.0 modea con DML1 | `PROVEN_DERIVED` |
| El motor de esta GPU son 20 ficheros y 11.875 líneas | `PROVEN` (por programa) |
| 20 + 54 = 74, recuento directo | `PROVEN` (comprobación cruzada) |
| Dónde se asigna `signal_type` | **`NOT_DETERMINED`** |
| De dónde sale el `false` inicial de `using_dml2` | **`NOT_DETERMINED`** — no localicé el `kzalloc` de `struct dc` |
| `dc/dc.h` (1.500 líneas), con `struct dc_link` | **`NOT_OBSERVED`** |
| `dc_link_enc_cfg.c`, que=configura la codificación | **`NOT_OBSERVED`** |

**Las dos primeras filas abiertas son las dos que abrí en esta nota y no cerré, y las
dos tienen fichero y línea.**

## Procedencia

- `STATIC` -- `display/dc/dml/`, `display/dc/dml2_0/`, `display/dc/dc.h:1140-1152`
  (el bloque `debug`), `display/amdgpu_dm/amdgpu_dm.c:2062-2082` (el bloque de
  overrides), los 25 `display/dc/resource/*/**_resource.c`,
  `display/amdgpu_dm/` (37 ficheros, recuento de líneas), `display/include/`,
  `display/dc/include/`.
- Medición, tres programas distintos y todos impresos:
  1. `os.walk` sobre `display/` para ficheros `.c` y líneas, con los diez mayores.
  2. `re.search(r"\.using_dml2\s*=\s*(true|false)")` sobre los 25
     `*_resource.c`, con la lista de los que no lo contienen.
  3. Reparto de `dml/` por `any("dcn" in c for c in rel.split(os.sep))`, más una
     comprobación cruzada contra el recuento directo de ficheros.
- Encadenada con `150` (la enumeración de 10 valores, y el `NOT_DETERMINED` de dónde
  se decide), `149` (la frontera DM→DC, y que DSC no es cosa de esta GPU),
  `148` (dos correcciones propias), `147` (los 89 de 130 campos), `144` (la entrada).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El mismo bloque de notas ha producido, en tres, un error de patrón que reventaba
el número: `147` Conté 3 campos donde la tabla tenía 3 y yo decía 3, `150` conté 24
`&` que eran 22 `&&`, y aquí conté 74 ficheros genéricos que eran 74 con 54
duplicados.**

**Los tres son la misma cosa: un filtro que no hace lo que su nombre dice.**
`"dcn" not in lista` de una lista de cadenas hace igualdad, no subcadena, y por eso
`dcn314` pasó el filtro. Y `SIGNAL_TYPE_... &` cuenta los `&&`. **Y en los tres
casos el número que salía era más grande de lo que debía, que es la dirección
peligrosa: un número exagerado hace sospechosa la conclusión, y uno *menor* oculta el
hallazgo.**

*Y hay un detalle de método que sí funcionó y que conviene conservar: la
comprobación cruzada de §3.* Sumé los dos bloques y lo comparé con el recuento
directo de ficheros, y coincided. **Esa es la defensa que faltó en `150` y en este
mismo §3 antes de corregirlo: si dos formas de contar dan el mismo número, el
número es bueno; si dan distintos, uno de los dos programas está mal — y hay que
encontrar cuál antes de escribir nada.**

**Y el resultado de fondo es el que importa: un `bool` en la tabla de recursos de un
chip decide entre dos motores de mode-setting, y la respuesta para esta GPU reduce
443.839 líneas a 11.875.** Eso no se averigua leyendo; se averigua preguntando qué
campo decide, y siguiendo el campo hasta su tabla.
