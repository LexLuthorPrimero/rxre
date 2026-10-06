# 1585 — La guarda por stepping `0x699F/0xCF` apaga cinco cosas en el `0xCF`; en esta placa `rev c7` **no se cumple**, y por qué no se sabe porque el código no lo dice

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=OBSEVABILIDAD-DE-POTENCIA
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CÓDIGO+LÍMITE-LOCALIZADO
MODIFICATIONS=1577 §4  (la pregunta que ese hallazgo abrio,  aqui cerrada)
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
CIERRA   la pregunta que 1577 abrió de paso
DEJA     NOT_DETERMINED  la motivacion del 0xCF,  por no estar en el arbol
```

## 1 · La guarda, tal como está en el código

```c
  smu7_hwmgr.c:1975-1984
      if ((adev->pdev->device == 0x699F) &&
          (adev->pdev->revision == 0xCF)) {
              phm_cap_unset(..., PHM_PlatformCaps_PowerContainment);
              data->enable_tdc_limit_feature     = false;
              data->enable_pkg_pwr_tracking_feature = false;
              data->disable_edc_leakage_controller = true;
              phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
      }
```

Sin comentario. Dos líneas de condición y cuatro de acción. **No dice por qué**, y
ninguna de las dos ramas explica.

## 2 · Qué apagan, campo a campo, consumidor a consumidor

**A · `PHM_PlatformCaps_PowerContainment`** → puerta a un bloque entero en
`smu7_powertune.c:1162`:

```text
  1164  smum_send_msg_to_smc(..., PPSMC_MSG_TDCLimitEnable, NULL)      <- TDC limit
  1176  smum_send_msg_to_smc(..., PPSMC_MSG_PkgPwrLimitEnable, NULL)   <- pkg power
```

**B · `enable_tdc_limit_feature` / `enable_pkg_pwr_tracking_feature`** → la misma
puerta, segundo juego de llaves (`:1163`, `:1174`). En una placa `0xCF` se apagan los
dos, por exceso.

**C · `disable_edc_leakage_controller = true`** →
```text
  smu7_hwmgr.c:2934   if (data->disable_edc_leakage_controller)
                          return 0;                       <- no programa EDC leakage
  smu7_hwmgr.c:1484   if (!data->disable_edc_leakage_controller && ...)
                          smu7_program_edc_didt_registers(...);
                          smum_send_msg_to_smc(..., PPSMC_MSG_EnableEDCController,...)
                      else
                          smum_send_msg_to_smc(..., PPSMC_MSG_DisableEDCController,...)
```

**D · `PHM_PlatformCaps_ClockStretcher`** → se quita del mapa.

## 3 · En esta placa, la guarda no se cumple

```text
  lspci medido en 1231:  01:00.0  1002:699f  rev c7      ->  pdev->revision = 0xC7
  la guarda pide:                                          pdev->revision == 0xCF
  0xC7 != 0xCF    ->  EL BLOQUE NO SE EJECUTA
```

**Consecuencia sobre esta GPU:**

```text
  TDC limit                      ACTIVO      (PPSMC_MSG_TDCLimitEnable se envia)
  package power tracking         ACTIVO      (PPSMC_MSG_PkgPwrLimitEnable se envia)
  EDC leakage controller         ACTIVO      (registros programados,  SMC habilitado)
  capability PowerContainment    anunciada
  capability ClockStretcher      anunciada
```

Por tanto en esta placa EDC leakage, TDC limit y package power tracking estan activos.  No es rescatable leer lo que ese bloque *haría* si la placa fuera
`0xCF`, porque **lo que hace es no enviar un mensaje al SMC**. La consecuencia de la
diferencia es de dominio de potencia, no de protocolo.

## 4 · El límite honesto

```text
  NO SE SABE,  desde este árbol:
      por que 0xCF desactiva EDC leakage,  TDC limit y clock stretcher
       - si hay un error de silicio en esos bloques  para ese stepping
       - si el 0xCF tiene un artivado de firmware distinto
       - si simplemente AMD cambio de criterio para esa revision
  Y ES  NOT_DETERMINED:  no hay comentario,  no hay condicion de feature
  distinta,  no hay referencia a un bug del driver.
```

Lo que sí se puede decir: **el criterio es un umbral exacto sobre un campo de revisión
de cuatro bits**, y este paso es `0xC7`. Si AMD pretendiera incluir `0xC7` en el
tratamiento, el código no lo refleja. Si no lo pretendiera, este hallazgo no cambia
nada en la placa. Ambas lecturas son coherentes con el código; no hay dato que las
separe.

## 5 · Procedimiento y alcance

```text
PREGUNTA   que hace el bloque por stepping de smu7_hwmgr.c:1975,  y si le aplica
           a esta placa
FUENTES    el bloque leido entero
           los tres consumidores de disable_edc_leakage_controller  y de los
           dos campos enable_*,  leidos enteros
           la condicion concreta leida de lspci en 1231:  rev c7
MEDIDO     la guarda apaga  PowerContainment,  ClockStretcher,  TDC limit,
           pkg power tracking  y el controlador EDC de fugas
     defaults en el camino que SI ejecuta esta placa:
           enable_tdc_limit_feature = true  ·  enable_pkg_pwr_tracking_feature = true
           disable_edc_leakage_controller se inicializa en 0 (kzalloc)
     en esta placa los tres siguen activos;  el bloque no ejecuta
DESVIO MIO  ninguno;  aunque anoto la tentacion de "arreglar" la guarda
            poniendo 0xC7 == 0xCF,  que no procede sin el motivo
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 6 · Lo que sigue

```text
  los Siete Huecos estan cerrados  y  este hilo tambien
  1555 al final:  todas las cadenas hacia soft_regs_start estan medidas
  (1577 ruta de dispatch · 1578 que struct · 1583 offsets del bloque),  y la
  unica incógnita abierta es el VALOR de SMC_RAM[0x20030].

  Para cerrarla hace falta ejecutar el driver sobre 0000:01:00.0.  Es el paso
  de riesgo distinto de cero  que mencione desde 1231:  escribir SMC_IND_INDEX_11,
  leer SMC_IND_DATA_11,  sobre la unica GPU de display.  Lo dejo para tu OK
  explicito.
```