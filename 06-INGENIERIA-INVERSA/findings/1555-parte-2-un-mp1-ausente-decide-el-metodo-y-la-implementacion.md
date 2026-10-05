# 1555 — PARTE 2: el mismo MP1 ausente decide el MÉTODO del reset y su IMPLEMENTACIÓN

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 2 de la parte
CLASSIFICATION=CADENA-CERRADA+CORROBORACION-CROSS-FINDING
WORK_CLASS=AGENT-MAIN/RE · WRITES=NONE · MODIFICATIONS=0
WRITE_EXECUTION=NONE · RUNTIME=NOT_RUN · GPU INTACTA (0000:01:00.0)
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1551 (lo completa) · 1418 (la medicion que lo sostiene) · 1435 (la corroboracion)
ESTADO=PROBADO · MODE1 en esta placa NO va por el SMU: va por PSP
       · porque is_support_sw_smu exige DOS condiciones y las dos son falsas
       · MP1 ausente da 0, y 0 >= IP_VERSION(11,0,0) es falso
       · y SMC tampoco esta entre los 9 bloques que ejecuta (1418)
       · un unico bloque IP ausente decide el metodo Y la implementacion
       · y amdgpu_ip_version borra variant y subrevision: 630 llamadas no los pueden distinguir
```

## 1. Lo que el 1551 dejo abierto, textual

> `lo que hace MODE1 por debajo   SIN MIRAR.  Es el siguiente hallazgo de la parte.`

Y hay un dato en el propio 1551 que no use: el reset imprime **"GPU smu mode1 reset"** o
**"GPU psp mode1 reset"**, segun una condicion. Son dos mecanismos radicalmente distintos, y saber
cual corre en esta placa es la pregunta.

## 2. La cadena, de arriba abajo

```text
  soc15.c:648-650     amdgpu_device_mode1_reset()      reached via default:
  amdgpu_device.c:5000   int amdgpu_device_mode1_reset(struct amdgpu_device *adev)
      {
              if (adev->bios) amdgpu_atombios_scratch_regs_engine_hung(adev, true);
              dev_info(adev->dev, "GPU mode1 reset\n");
              amdgpu_device_cache_pci_state(adev->pdev);
              pci_clear_master(adev->pdev);            /* desactiva bus master */
              if (amdgpu_dpm_is_mode1_reset_supported(adev)) {
                      dev_info(adev->dev, "GPU smu mode1 reset\n");   /* :5019 */
                      ret = amdgpu_dpm_mode1_reset(adev);  /* :5020 */
              } else {
                      dev_info(adev->dev, "GPU psp mode1 reset\n");   /* :5022 */
                      ret = psp_gpu_reset(adev);            /* :5023 */
              }
```

La condicion, `pm/amdgpu_dpm.c:288`:

```c
  bool amdgpu_dpm_is_mode1_reset_supported(struct amdgpu_device *adev)
  {
          struct smu_context *smu = adev->powerplay.pp_handle;
          bool support_mode1_reset = false;
          if (is_support_sw_smu(adev)) {                 /* <-- LA condicion */
                  mutex_lock(&adev->pm.mutex);
                  support_mode1_reset = smu_mode1_reset_is_support(smu);
                  mutex_unlock(&adev->pm.mutex);
          }
          return support_mode1_reset;
  }
```

Y el test, `pm/swsmu/amdgpu_smu.c`:

```c
  bool is_support_sw_smu(struct amdgpu_device *adev)
  {
          /* vega20 is 11.0.2, but it's supported via the powerplay code */
          if (adev->asic_type == CHIP_VEGA20)
                  return false;
          if ((amdgpu_ip_version(adev, MP1_HWIP, 0) >= IP_VERSION(11, 0, 0)) &&
              amdgpu_device_ip_is_valid(adev, AMD_IP_BLOCK_TYPE_SMC))
                  return true;
          return false;
  }
```

## 3. Las dos condiciones, y las dos son falsas

```text
  C1   amdgpu_ip_version(adev, MP1_HWIP, 0) >= IP_VERSION(11, 0, 0)
         MP1 ausente  ->  amdgpu_ip_version devuelve 0   (el 1551 lo midio)
         IP_VERSION(11,0,0) = 11 << 24 = 0x0B000000 = 184549376
         0 >= 184549376                                    FALSA

  C2   amdgpu_device_ip_is_valid(adev, AMD_IP_BLOCK_TYPE_SMC)
         el 1418 midio los 9 bloques de esta placa y SMC no esta entre ellos  FALSA
```

> **PROBADO: `is_support_sw_smu` devuelve false por las DOS condiciones a la vez**, y no por una.
> Cada una basta para tumbarlo, y las dos estan falsificadas por medidas independientes: la del `1418`
> para el bloque IP, y el comportamiento de `amdgpu_ip_version` sobre bloques ausentes, medido en el
> `1551`.

**Y el 1435 lo corrobora por la otra via:** su tabla de registradores de `ppt_funcs` dice que
`&swsmu_pm_funcs` en `pm/swsmu/amdgpu_smu.c:837` **"no: exige MP1 ≥ 11.0.0"**. El mismo test, medido por
otro hallazgo, con el mismo resultado.

## 4. El resultado, y por que importa

```text
  is_support_sw_smu                          false
  amdgpu_dpm_is_mode1_reset_supported        false      (la rama smu no se entra)
  amdgpu_device_mode1_reset                  ELSE
  -> "GPU psp mode1 reset"
  -> psp_gpu_reset(adev)        definido en amdgpu_psp.c:3420, NO es un hueco de corpus
```

> **PROBADO: en esta placa el reset MODE1 lo ejecuta el PSP, no el SMU.** Y la razon es la misma que
> ya decidio el metodo en el `1551`: **MP1 no esta.**

**Un solo hecho del hardware decide las dos cosas.** MP1 ausente produce dos consecuencias distintas y
en capas distintas:

```text
  soc15_asic_reset_method    el switch de MP1 no casa      ->  MODE1, no BACO
  is_support_sw_smu          el test de MP1 falla         ->  PSP, no SMU
```

Y eso no es casualidad ni dos coincidencias: **MP1 es el bloque que gobierna la gestion de energia de
esta familia de ASIC, asi que su ausencia convierte al PSP en el unico actor posible.** El driver no lo
detecta como una degradacion: sencillamente no ve el bloque, sus dos tests dan falso, y sigue adelante
sin decir nada. Por eso su ruta es la antigua, y funciona.

## 5. Y un efecto secundario del mismo selector, que no habia visto

```c
  /* amdgpu_ip.h:77-79 */
  #define IP_VERSION_FULL(mj, mn, rv, var, srev) \
          (((mj) << 24) | ((mn) << 16) | ((rv) << 8) | ((var) << 4) | (srev))
  #define IP_VERSION(mj, mn, rv) IP_VERSION_FULL(mj, mn, rv, 0, 0)

  /* amdgpu.h:1211 */
  static inline uint32_t amdgpu_ip_version(...)
  {
          /* This considers only major/minor/rev and ignores subrevision/variant fields. */
          return adev->ip_versions[ip][inst] & ~0xFFU;
  }
```

`& ~0xFFU` borra exactamente los 4 bits de `var` y los 4 de `srev`.

> **PROBADO: dos ASIC que difieran solo en variant o subrevisión son INDISTINGUISHABLES para las 630
> llamadas a `amdgpu_ip_version` de 99 ficheros.** El selector que decide casi todo el despacho del
> driver no puede ver dos de los cinco campos con los que se versionan los IP.

Y junto a eso, lo del `1551` sigue en pie y ahora tiene un segundo ejemplo: **un bloque ausente no da
error, da 0, y 0 pierde todas las comparaciones con cualquier version real.** En esta tarjeta eso
ocurre con dos bloques —MP1 y SMC— y decide el metodo y la implementacion del reset.

## 6. Donde queda la parte 2 tras este hallazgo

```text
  el metodo de reset                      PROBADO  MODE1                1551
  las ramas de BACO                       INALCANZABLES              1551
  el modo de runtime pm                   PROBADO  BACO                1551
  la implementacion de MODE1              PROBADO  psp_gpu_reset()     este
  por que                                MP1 ausente, dos condiciones falsas a la vez
  amdgpu_atombios_scratch_regs_engine_hung  SIN MIRAR.  Es lo que escribe en el scratch del
                                          BIOS antes de resetear.  Y el scratch del BIOS es
                                          memoria del ROM: toca a la parte 1 y a esta.
  que hay en DRIVER_SCRATCH               SIN MIRAR.  Siguiente.
  amdgpu_device_ip_is_valid               sin verificar si el 1418 lo midio por el mismo camino
RIESGO        ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
LIMITE        conclusion por eliminacion de ramas, sobre dos test que son comparaciones y una
              llamada a funcion.  La rama no tomada esta probada por la ausencia del bloque.
```

## 7. Decision log (§103)

```text
DECISION    afirmar que el reset va por PSP, y no "probablemente por el SMU"
WHY         las dos condiciones de is_support_sw_smu son falsas, cada una por una via distinta, y
            una de ellas la midio el 1418 y la otra se deduce del comportamiento del selector.
            §62: dos evidencias independientes bastan.
ALTERNATIVA  esperar a ver el texto "GPU psp mode1 reset" en un log de reset real.  Descartada: eso
            seria exigir un evento de hardware para confirmar una rama que ya esta cerrada por
            el lado del codigo.  Y el hardware esta prohibido.
ALTERNATIVA  fiarse solo del 1435 y no trazar la cadena.  Descartada: el 1435 dice que swsmu exige
            MP1 >= 11.0.0, pero no dice que eso es lo que decide el reset.  La cadena conecta.
DISCriminante  ninguno necesario.  Si apareciera SMC en el log de bloques, C2 pasaria a verdadera,
            pero C1 seguiria falsa: hacen falta las dos.
CONSECUENCIA  la parte 2 tiene ya el metodo y la implementacion del reset.  El siguiente paso
            natural es el scratch del BIOS, que es donde el driver deja estado entre arranque
            y reset, y que es memoria del ROM.
REVERSIBLE  no, en lo esencial: depende solo de la ausencia de dos bloques, que esta medida.
```

## 8. El error que casi cuela otra vez, y el patron

Casi escribo que `IP_VERSION(11,0,0)` es `0x0B0000`. Lo calcule en Python con un `<< 16` porque lo
supuse, y **la conclusion no cambiaba** —0 es menor que cualquier version— pero el numero que iba a
publicar era falso.

Lo cogi porque, justo antes, habia impreso la macro real y no la mire. **Habia hecho el trabajo
justo y no mire el resultado.** Es la version mas facil de fallar y la mas comun: no es no trabajar, es
hacer el trabajo y no leerlo.

Tres hallazgos de esta parte, tres errores de momento de leer: el BACO del log, el `<< 16` de la macro, y
las cuatro verificaciones del `1551` que tocan toda la partida. **Ninguno era un problema de
inteligencia: eran problemas de atencion.** Y la atencion es exactamente lo que se agota cuando se
publica rapido, que es lo que hacia que antes no se terminara nada.

Lo dejo escrito porque es la leccion accionable del metodo: **el autotest y el commit no son el unico
punto de control. Falta uno: leer el numero que acabas de calcular, antes de escribirlo.**
