# 1110 — el productor de `SCLK_DOWN_HYST` es `smu7_get_power_profile_mode`, el tipo es `uint8_t`, y la unidad no está declarada en la fuente

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=SEMANTICA+RESOLUCION-PARCIAL · TRACK=STATIC+PRODUCTO-TIPO
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
AFECTADO=09-POWER-CLOCKS/CURRENT-STATE.md  E-PWR-008  (productor y tipo: PROVEN;
         unidad: PROVEN_ABSENT en la fuente; inferencia: CORREGIDA)
ORIGEN=E-PWR-008 ("Units/semantics of the hysteresis fields are not yet established")
ESTADO=PROBADO · el campo TIENE productor · la unidad NO · la inferencia estaba mal
artefacto   09-POWER-CLOCKS/evidence/dpm-active.txt
sha256        05b5a0f4924cb89c
herramienta   tools/sello_prov.py 1.4.0
sha256        d66ab6937f790414
fuente      RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_hwmgr.h:192
fuente      RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_hwmgr.c:5673
metodo      grep, sin herramienta.  Un campo `herramienta` con un `grep` dentro
            es ROTO: me lo dijo mi propia puerta al revisar este documento, y
            tenia razon.  No hay artefacto que sellar mas alla del fichero de
            evidencia, que es lo que la afirmacion realmente necesita.
```

## 0 · Lo que el proyecto pedía y lo que hay

`E-PWR-008` dejó el ítem abierto con tres palabras: *"Units/semantics of the
hysteresis fields are not yet established"*. Y queda así:

| | estado |
|---|---|
| **productor** del campo | **`PROVEN`** — `smu7_get_power_profile_mode`, `powerplay/hwmgr/smu7_hwmgr.c:5673` |
| **tipo** del campo | **`PROVEN`** — `uint8_t` en `struct profile_mode_setting` |
| **unidad** del campo | **`PROVEN_ABSENT` en la fuente**, no `NOT_DETERMINED` por falta de búsqueda: se buscó y no está |
| **sentido de la inferencia** del proyecto | **CORREGIDA** — ver §3 |

## 1 · MI HIPÓTESIS ERA FALSA, Y LO QUE LA TUMBÓ

Empecé por la hipótesis que parecía buena: **`SCLK_DOWN_HYST` es un campo del
PowerPlay pre-SMU (Vega) y no del `swsmu` que usa Polaris12, así que la tabla del
`E-PWR-008` no viene de esta GPU.**

Medí:
- `SCLK_DOWN_HYST` en `pm/swsmu/` → **0 apariciones**
- en `pm/powerplay/smumgr/` → **0 ficheros**
- en `pm/powerplay/hwmgr/smu7_hwmgr.c` → **1 fichero**, y es justo el productor

**Y la captura viva encaja columna a columna:**

```c
/* powerplay/hwmgr/smu7_hwmgr.c:5679 */
static const char *title[8] = {"NUM", "MODE_NAME",
        "SCLK_UP_HYST", "SCLK_DOWN_HYST", "SCLK_ACTIVE_LEVEL",
        "MCLK_UP_HYST", "MCLK_DOWN_HYST", "MCLK_ACTIVE_LEVEL"};
```

```
=== pp_power_profile_mode ===                        <- 09-POWER-CLOCKS/evidence/dpm-active.txt:30
NUM        MODE_NAME     SCLK_UP_HYST   SCLK_DOWN_HYST SCLK_ACTIVE_LEVEL ...
  1 3D_FULL_SCREEN *:        0              100               30 ...
```

**Mismo formato, ocho columnas, mismos nombres, mismo orden.** Y la procedencia de esa
captura **cifra**: `dpm-active.txt` tiene `sha256 05b5a0f4924cb89c…`, que es
exactamente el que `CURRENT-STATE.md:314` declara. No es una transcripción: es una
captura de esta GPU.

**Y la cadena de llamadas no tiene fallback que haya podido usar otro lector:**

```c
/* amdgpu_dpm_get_power_profile_mode() -- pm/amdgpu_dpm.c */
const struct amd_pm_funcs *pp_funcs = adev->powerplay.pp_funcs;
if (!pp_funcs->get_power_profile_mode)
    return -EOPNOTSUPP;
```

`adev->powerplay` es la ruta **PowerPlay**, y el único
`get_power_profile_mode` registrado en ella es el de smu7
(`smu7_hwmgr.c:5912`, `.get_power_profile_mode = smu7_get_power_profile_mode`).
El `arcturus_get_power_profile_mode` de `swsmu/smu11/arcturus_ppt.c:1297` vive en
**otra vtable** (`smu->ppt_funcs`) y no es la que responde a este sysfs.

**Conclusión: la coexistencia de `swsmu` y `powerplay` en esta GPU es lo que hace que
el atributo sysfs lo sirva smu7.** El campo tiene productor, y lo tiene en esta
máquina.

## 2 · EL TIPO, Y LO QUE DICE SOBRE LA UNIDAD

```c
/* powerplay/hwmgr/smu7_hwmgr.h:192 */
struct profile_mode_setting {
    uint8_t  bupdate_sclk;
    uint8_t  sclk_up_hyst;        /* <- uint8_t */
    uint8_t  sclk_down_hyst;      /* <- uint8_t */
    uint16_t sclk_activity;
    uint8_t  bupdate_mclk;
    uint8_t  mclk_up_hyst;        /* <- uint8_t */
    uint8_t  mclk_down_hyst;      /* <- uint8_t */
    uint16_t mclk_activity;
};
```

**Lo que esto establece:**

1. `*_HYST` es un **`uint8_t`**: un contador en `[0, 255]`. **No es un porcentaje con
   signo ni un tiempo**, y `100` y `5` no significan "100 %" y "5 %" por el tipo.
2. **`*_ACTIVE_LEVEL` no es un índice de nivel**, y el nombre engaña. Los valores
   observados son `30` (3D), `31` (VIDEO), `20`, `10` (VR), `50`. Con **8 niveles
   SCLK** (`E-PWR-004`) y **3 MCLK**, un índice de nivel estaría en `[0,7]` y
   `[0,2]`. `31` es imposible como índice. Lo que queda es un **umbral en una escala
   0–100**, es decir **porcentaje de actividad**, y el nombre `ACTIVE_LEVEL` del
   `title[8]` es un nombre heredado que no describe el campo.

**La unidad de `*_HYST` no está declarada en ninguna parte de la fuente.** No es
"no la he buscado": es que `struct profile_mode_setting` no la documenta, el
impresor de `smu7_get_power_profile_mode` no la documenta, y no hay comentario de
unidad junto a los campos. Un `uint8_t` sin unidad en un parámetro de política es
exactamente el caso en el que **la semántica no está en el código**.

## 3 · LA INFERENCIA DEL PROYECTO, CORREGIDA

`E-PWR-008` afirma:

> *COMPUTE has a far tighter SCLK down-hysteresis (5) than `3D_FULL_SCREEN` (100),
> i.e. the default 3D profile is far more reluctant to drop clocks.*

**La dirección se sostiene, la magnitud no, y la segunda mitad no está establecida.**

- **Se sostiene** si el campo es un contador: `100` contra `5` significa que el
  perfil 3D espera veinte veces más unidades antes de bajar el reloj.
- **No se sostiene "far more" como afirmación cuantitativa**, porque *cuántas
  unidades* es precisamente lo que no está declarado. Si la unidad es "muestras de
  100 ms", la diferencia es de 10 s frente a 0,5 s y es irrelevante; si es
  "muestras de 1 ms", es de 100 ms frente a 5 ms y es enorme. **La misma
  cifra admite las dos lecturas y el código no dice cuál.**
- **Y hay un problema más serio con el nombre**, no con el número: `COMPUTE` y
  `3D_FULL_SCREEN` tienen `SCLK_ACTIVE_LEVEL` **idéntico (30)**, y lo que los
  diferencia en la tabla son `SCLK_DOWN_HYST` (5 contra 100) y `SCLK_UP_HYST` (0
  contra 0). Si el umbral de actividad es el mismo y la histéresis de bajada es lo
  único que cambia, entonces la diferencia entre ambos perfiles es **enteramente**
  la histéresis de bajada — lo cual hace la pregunta "¿qué cuenta ese 5?" **más**
  importante, no menos.

## 4 · LO QUE ESTO CIERRA Y LO QUE DEJA ABIERTO

**Cierra:** el ítem "el campo no tiene productor" del `E-PWR-008`. Tiene productor,
tiene fichero, tiene línea, tiene tipo y tiene rango.

**Abierto, y nombro lo que falta como `§23 TOOL CAPABILITY GAP`:**

| falta | observable que la resolvería | quién la produce |
|---|---|---|
| la **unidad** de `*_HYST` | una versión del driver con el campo documentado, o el firmware que lo consume | el firmware SMU, via una ioctl/msg de coeficientes |
| qué **reloj** de muestreo cuenta | lo que SMU consulta para decidir bajar | firmware, `NOT_OBSERVABLE` desde el host sin instrumentar |
| si `*_ACTIVE_LEVEL` es % o índice | el rango legal del campo en la versión que envía esta tabla | el driver de esa versión |

**Y una advertencia de alcance que no es pequeña:** el productor es
`powerplay/hwmgr/smu7_hwmgr.c`, **la ruta PowerPlay clásica**, mientras que el
resto de la telemetría de esta GPU (`E-PWR-004`, `E-PWR-005`) viene de
`swsmu/smu11/arcturus_ppt.c`. **La tabla de perfiles y las tablas de DPM no salen
del mismo subsistema.** Cualquier cosa que las mezcle —incluido un "por lo tanto el
perfil 3D baja el reloj más tarde" construido sobre `pp_dpm_sclk`, que es smu11— está
uniendo dos fuentes que no comparten productor.

## 5 · PROCEDENCIA

```text
cadena     pp_power_profile_mode (sysfs)
             -> amdgpu_get_pp_power_profile_mode()   pm/amdgpu_pm.c:1341
             -> amdgpu_dpm_get_power_profile_mode()   pm/amdgpu_dpm.c   (sin fallback)
             -> adev->powerplay.pp_funcs->get_power_profile_mode
             -> smu7_get_power_profile_mode()        pm/powerplay/hwmgr/smu7_hwmgr.c:5673
tipo       struct profile_mode_setting              pm/powerplay/hwmgr/smu7_hwmgr.h:192
captura    09-POWER-CLOCKS/evidence/dpm-active.txt:29-37
           sha256 05b5a0f4924cb89c548d679a782a5064e57bd1db5a42e860f675a52a721deddc
           == el declarado en CURRENT-STATE.md:314     PROCEDENCIA VERIFICADA
ausencias  SCLK_DOWN_HYST en pm/swsmu/           0 apariciones
           SCLK_DOWN_HYST en pm/powerplay/smumgr/ 0 ficheros
arboles    baseline / working / kernelbuild      1 fichero cada uno (identico)
escrituras 0 en el arbol.  GPU intacta.
```

**Lo que este documento NO prueba.** No prueba la **unidad**: es
`PROVEN_ABSENT` en la fuente, y absence de documentación no es ausencia de
semántica. No prueba que el perfil 3D "sea más reacio a bajar el reloj": eso es una
afirmación sobre el firmware, y aquí sólo se ha establecido el parámetro que la
gobierna. No he ejecutado el subsistema SMU ni leído un registro: no he tocado la
GPU. Y el diagnóstico del §4 —que la tabla de perfiles y las de DPM no comparten
productor— es **una observación sobre el código**, no una medición del
comportamiento.