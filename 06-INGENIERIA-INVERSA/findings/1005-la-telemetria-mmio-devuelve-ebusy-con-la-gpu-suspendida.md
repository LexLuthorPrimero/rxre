# 1005 · Toda la telemetría MMIO devuelve EBUSY si la GPU está suspendida, y el guard de numeración ya no llega al 1000

```
CLASSIFICATION=DOCUMENTATION+CONTRADICTION+TOOL_DEFECT · TRACK=RUNTIME+STATIC
CORPUS_A=RESEARCH/working/linux-7.1.3   (kernel en ejecución, amdgpu_pm.c sha256 a7565ad4b4c47f8300fb8d4dc6acc8031668b5cda75e36e3b85523dd13fcf3ee)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 [1002:699f] rev c7 · WORK_CLASS=READ_ONLY/EVIDENCE
KERNEL=7.1.3-200.nobara.fc44.x86_64 · WRITE_EXECUTION=NONE · MODIFICATIONS=0 en el corpus
GPU INTACTA · AGENTE=AGENT-29 (RENDIMIENTO) · ESTADO=RESUELTO
```

## 1. El hecho que sepakaba

Al empezar a medir, **todos** los atributos de telemetría que dependen de MMIO
devolvían `EBUSY`, y lo hacen de forma reproducible:

```text
gpu_busy_percent          → EBUSY
mem_busy_percent          → EBUSY
hwmon1/power1_input       → EBUSY
pp_dpm_sclk               → EBUSY
pp_dpm_mclk               → EBUSY
pp_power_profile_mode     → EBUSY
fan1_input, in0_input, freq1_input, freq2_input → EBUSY
```

Y en cambio se leen sin problema los que **no** tocan MMIO:

```text
mem_info_vram_total = 2147483648     OK
mem_info_gtt_total  = 6194638848     OK
hwmon1/power1_label = PPT            OK   (etiqueta estática)
hwmon1/temp1_crit   = 97000          OK   (límite estático)
```

La línea divisoria no es el archivo, ni el bus, ni los permisos: es **MMIO sí o
no**. Eso ya descarta "permisos" y "GPU caída" como explicación, y obliga a
preguntarse qué tiene de distinto leer `mem_info_vram_total` (OK) frente a
`gpu_busy_percent` (EBUSY).

## 2. La cadena causal, desde la fuente primaria

El consumidor es `amdgpu_get_gpu_busy_percent()`
(`drivers/gpu/drm/amd/pm/amdgpu_pm.c:1449`), que no va directo al sensor:

```c
/* amdgpu_pm.c:1449-1458 */
static ssize_t amdgpu_get_gpu_busy_percent(struct device *dev, ...)
{
        r = amdgpu_pm_get_sensor_generic(adev, AMDGPU_PP_SENSOR_GPU_LOAD, &value);
        if (r)
                return r;          /* el errno se propaga tal cual al read() */
```

`get_sensor_generic` mete una puerta de acceso **antes** de tocar el sensor:

```c
/* amdgpu_pm.c:1423-1436 */
static int amdgpu_pm_get_sensor_generic(struct amdgpu_device *adev, ...)
{
        r = amdgpu_pm_get_access_if_active(adev);   /* <-- la puerta */
        if (r)
                return r;
        r = amdgpu_dpm_read_sensor(adev, sensor, query, &size);
```

Y esa puerta decide así:

```c
/* amdgpu_pm.c:150-155 */
static int amdgpu_pm_get_access_if_active(struct amdgpu_device *adev)
{
        int ret;

        /* Ignore runpm status. If device is in suspended state, deny access */
        ret = amdgpu_pm_dev_state_check(adev, false);
```

```c
/* amdgpu_pm.c:109-121 */
static int amdgpu_pm_dev_state_check(struct amdgpu_device *adev, bool runpm)
{
        bool runpm_check = runpm ? adev->in_runpm : false;
        bool full_init   = (adev->init_lvl->level == AMDGPU_INIT_LEVEL_DEFAULT);

        if (amdgpu_in_reset(adev) || !full_init)
                return -EBUSY;

        if (adev->in_suspend && !runpm_check)
                return -EBUSY;

        return 0;
}
```

La cadena completa, entonces:

```text
runtime PM suspende el dispositivo (adev->in_suspend = true, power_state = D3hot)
   ↓
amdgpu_get_gpu_busy_percent()            amdgpu_pm.c:1449
   ↓
amdgpu_pm_get_sensor_generic()           amdgpu_pm.c:1423
   ↓
amdgpu_pm_get_access_if_active()         amdgpu_pm.c:150
   ↓
amdgpu_pm_dev_state_check(adev, runpm=false)
   ↓
adev->in_suspend && !runpm_check → return -EBUSY     amdgpu_pm.c:117-118
   ↓
read() de sysfs devuelve EBUSY (errno 16)
   ↓
cualquier arnés de benchmark que sontee sysfs pierde la telemetría
```

**No es un fallo del hardware y no es un bug: es una puerta deliberada.** La
comentación del propio driver lo dice sin rodeos — *"If device is in suspended
state, deny access"*. La lección para el proyecto es que **la telemetría de la
RX550 tiene una precondición de energía que ningún documento del proyecto
declaraba**, y que se cumple o no según si el benchmark la mantiene despierto.

## 3. El discriminante, y por qué es H1 y no H3

Dos hipótesis competían:

- **H1 — estado de energía**: EBUSY es consecuencia de `in_suspend`, y se
  levanta en cuanto el dispositivo vuelve a D0.
- **H2 — avería / reset / init incompleto**: el dispositivo está en
  `amdgpu_in_reset()` o `init_lvl != DEFAULT` y por eso devuelve EBUSY
  independientemente de la energía.

Ambas predicen EBUSY, así que EBUSY por sí solo **no las separa**. El
discriminante es lo que la anterior ya daba por hecho y esta no: si es H1, el
cambio de D3hot→D0 debe accompanies de EBUSY→lectura válida **en el mismo
muestreo**. Y el estado de energía se cambia sin escribir ningún registro,
abriendo un cliente Vulkan, que dispara el resume del runtime PM.

Artefacto: `03-EXPERIMENTOS/EBUSY-TELEMETRIA/runs/run-004.tsv`
(sha256 `38e384c72dd465183526d69eb9615fbfa0535c93d5238e9a21457740717299ee`),
11 muestras, precondición **verificada antes** de arrancar (no supuesta):

| fase | `runtime_status` | `power_state` | `gpu_busy` | `mem_busy` | `power1_uW` | `pp_dpm_sclk` |
|---|---|---|---|---|---|---|
| A (5/5) | `suspended` | `D3hot` | **EBUSY** | **EBUSY** | **EBUSY** | **EBUSY** |
| B (3/3) | `active` | `D0` | OK `0` | OK `0` | OK `3196000` | OK `*1: 551Mhz` |
| C (3/3) | `active` | `D0` | OK `0` | OK `0` | OK `3196000` | OK `*1: 551Mhz` |

11 de 11 muestras coherentes dentro de su fase; 0 contradictorias. La única
variable manipulada es el estado de energía. **H1 PROVEN. H2 REFUTADA.**

Que B y C devuelvan además valores *plausibles y estables* (3.196000 W, SCLK
en el nivel 1 = 551 MHz, busy 0/0 con `vulkaninfo`, que no carga la GPU) es lo
que separa "ahora se lee" de "ahora se lee basura".

## 4. Lo que esto invalida, y lo que no

**Lo que sí queda tocado:**

- Cualquier cifra de potencia, SCLK/MCLK o `*_busy_percent` tomada con el
  dispositivo suspendido **no es cero, es `NOT_AVAILABLE`**. El
  `c1_observer.py` del proyecto (§ `read_optional`) marca `NOT_AVAILABLE` y no
  inventa un 0, lo cual es correcto; pero su CSV se filtra por
  `gpu_busy ≥ 95`, así que una sesión con la GPU dormida produce **conjunto
  vacío y salida 0**. Eso es exactamente el `empty log ≠ successful
  experiment`: unBenchmark "verde" sin una sola fila válida.
- Los experimentos previos (`ESCALADO-E03`, FASE-R4C) corrieron con la GPU
  ocupada, luego están **afectados?** no: la precondición se cumplía sola. Lo
  que no estaba escrita es la precondición.

**Lo que NO queda tocado:** ninguna de las cifras ya publicadas. El
`power1_input` en reposo que se lee ahora (3.196 W, D0, nivel SCLK 1) es
compatible con los ~3.7 W de `EXP-F3-A`. `gpu_busy=0` con `vulkaninfo` en
mano es lo correcto: enumerar no es trabajar.

## 5. El defecto de la herramienta que casi hace esto invisible

El primer lector que escribí etiquetaba EBUSY como `ERR(1)`, y el segundo
`EBUSY` pero rompía las filas del TSV. La causa del primero no fue el driver:

> **`cat` no propaga `errno`.** Devuelve `1` para *cualquier* error, así que
> `cat f || echo EBUSY` no puede distinguir EBUSY de EACCES de EIO. Un lector
> así "funciona" y fabrica una etiqueta inventada — el peor resultado posible
> en un instrumento cuya razón de ser es distinguir estados.

Por eso existe `readattr.py`: abre el fichero y captura `OSError.errno`, que sí
es el número real. Autotest con vectores conocidos, los cinco correctos:

| vector | esperado | obtenido |
|---|---|---|
| `/etc/hostname` | `OK` | `OK kalm` |
| `/no/existe` | `ENOENT` | `ENOENT` |
| `/tmp` (directorio) | `EISDIR` | `EISDIR` |
| `mem_info_vram_total` (cacheado) | `OK` | `OK 2147483648` |
| `gpu_busy_percent` **con GPU dormida** | `EBUSY` | `EBUSY` |

El quinto vector es el que importa: es el caso que se quiere clasificar, y se
clasifica bien. Un instrumento que no tiene ese vector no está validado para
esto, por muchos que tenga.

## 6. El guard de numeración ya no cubre el rango en el que estamos

Al reservar número para este hallazgo:

```text
$ python3 tools/nextnum.py --reservar 1003 --json
{ "n": "1003", "estado": "MALO", "motivo": "el numero debe ser de 3 cifras" }
```

`nextnum.py` valida con `^\d{3}$` (`tools/nextnum.py:149` y `:488`), o sea
**exatamente tres dígitos**. El corpus ya está en 1002. Consecuencias medidas,
no supuestas:

- **No se puede reservar ningún hallazgo ≥ 1000.** El guard rechaza justo el
  rango en el que vive el corpus actual.
- Su censo de colisiones **no ve el 1002**: de 508 ficheros, cuenta 408 números
  distintos de 3 dígitos y **no registra ninguno de 4 dígitos**. El único
  fichero de 4 dígitos (`1002-…`) es invisible para su detector.

Es decir: el guard que existe para impedir colisiones de numeración ha dejado de
cubrir la numeración que se está usando.

### Y no es hipotético: ocurrió mientras se escribía esto

No lo he reparado — es territorio de tooling, no de rendimiento — pero el
defecto **se reprodujo en vivo durante la redacción de este documento**, que es
la mejor evidencia que se puede tener de él:

```text
1. python3 tools/nextnum.py --reservar 1003  →  MALO ("debe ser de 3 cifras")
2. find . -name "1003-*"                    →  vacío        (libre, comprobado)
3. se escribe el hallazgo con número 1003
4. find . -name "1003-*"                    →  DOS ficheros  (colisión real)
```

El segundo `1003` es `1003-no-hay-allocateur-de-vmid-y-el-fsm-que-pide-el-
mandato-no-es-el-que-existe.md`, creado por otro autor entre los pasos 2 y 4.
Porque el guard no puede concessionar números ≥1000, el número se elige a mano,
y dos autores eligen el mismo. El corpus ya arrastra además **dos `999`**.

Este documento se ha renumerado a **1005**, verificado libre en todo el árbol
antes de escribir:

```text
$ find . -name "1005-*" -not -path "./.git/*" | wc -l   →  1
```

La lección operativa, que es más útil que el hallazgo: **mientras `nextnum.py`
siga validando con `^\d{3}$`, cualquier hallazgo ≥1000 se numera a mano y las
colisiones son esperadas, no improbables.**

## 7. Qué toca a un driver propio

La precondición no es una incomodidad del benchmarking: es una restricción de
diseño que el driver propio hereda si quiere usar la misma interfaz.

1. **La puerta es una política, no un accidente.** `get_access_if_active()`
   deniega en `in_suspend` mientras que `get_access()` (con `runpm=true`) hace
   `pm_runtime_resume_and_get()`. El mismo driver tiene **las dos**Policies: la
   que reanuda y la que no. Para un driver propio la decisión es explícita:
   ¿un `sclk` de sysfs debe **despertar** la GPU o **negarse**? Negarse cuesta
   una corrección de medición; despertar cuesta energía. El upstream eligió
   negarse para el sensor, y esa elección es coherente con no gastar en una
   lectura.
2. **Un telemetrista que no declare la precondición produce `NOT_AVAILABLE`
   silencioso**, no un error. Cualquier arnés propio que mida sobre esta tarjeta
   necesita comprobar `runtime_status` **antes** de muestrear y declarar la
   sesión inválida si no está en `active` — no acumular filas vacías.
3. **Medir el reposo de esta GPU exige despertarla**, y entonces el número que
   sale ya no es el de reposo: es 3.196 W **en D0, nivel SCLK 1**, no en D3hot.
   Son dos cosas distintas y no deben mezclarse en la misma serie.

## 8. Alcance y límites

- Alcance: **esta** GPU, **este** kernel (7.1.3-200.nobara.fc44.x86_64),
  **este** árbol. No se afirma nada sobre otros kernels, otros ASIC, ni sobre
  `amdgpu` fuera de `RESEARCH/working/linux-7.1.3`.
- `B` y `C` usan `vulkaninfo`, que **no carga la GPU**: sirven para probar
  legibilidad, **no** para medir rendimiento. No se ha medido aquí potencia en
  régimen, ni ancho de banda, ni occupancy. Siguen abiertos.
- `sudo` no disponible en esta sesión: `amdgpu_pm_info` y `amdgpu_benchmark`
  en debugfs siguen sin leerse, como ya estaba registrado en `EXP-F3-A`.
- **No se ha escrito ningún registro.** La única acción con efecto fue abrir un
  cliente, que reanudó el runtime PM; el autosuspend (5000 ms) lo devolvió solo,
  y así consta en el artefacto (fase A empieza con `runtime_status=suspended`
  verificado).

## 9. Reproducir

```bash
cd 03-EXPERIMENTOS/EBUSY-TELEMETRIA
sha256sum -c <<'EOF'
825471194deb41ce227f5a93836fc546d89b57466185c85e993b31789750567b  probe.sh
5600ac5a4e0dc3ab519b397e152e9e6e882ff9e956de3c0e29dae58507962a34  readattr.py
EOF
SAMPLES=5 INTERVAL=1 ./probe.sh        # ~15 s, solo lectura
```

Condición de passage: fase A con ≥5/5 muestras en `suspended` y las cuatro
atributos MMIO en `EBUSY`. Si la fase A no arranca en `suspended`, el propio
arnés sale con código 3 y la corrida es **inválida**: no es un resultado
negativo, es una sesión mal montada.

## 10. Procedencia

| pieza | valor |
|---|---|
| herramienta | `03-EXPERIMENTOS/EBUSY-TELEMETRIA/probe.sh` sha256 `82547119…50567b` |
| lector | `readattr.py` sha256 `5600ac5a…62a34` |
| artefacto | `runs/run-004.tsv` sha256 `38e384c7…299ee` |
| fuente primaria | `RESEARCH/working/linux-7.1.3/…/amd/pm/amdgpu_pm.c` sha256 `a7565ad4…fcf3ee` |
| líneas citadas | 109-121, 117-118, 1423-1436, 1449-1458, 150-155 (verificadas con `sed`) |
| target | `0000:01:00.0` `[1002:699f]` rev c7, `Lexa PRO` |
| kernel | `7.1.3-200.nobara.fc44.x86_64` |
| navegador | RADV, Mesa 26.2.3, `VK_ICD_FILENAMES` por defecto |
| entradas previas | `runs/run-001..003.tsv` — tres corridas **descartadas**, con dos defectos de instrumento (ver §5) |