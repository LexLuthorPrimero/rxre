# 1557 — PARTE 2: el reset de esta placa termina en un no-op que devuelve éxito, y sus tres verificaciones no lo pueden detectar

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 3 de la parte
CLASSIFICATION=CADENA-CERRADA+HUEGO-DE-CORPUS-DECLARADO+VACIO-DETECTADO
TRACK=STATIC + UNA LECTURA de lspci · CERO ESCRITURA · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1551 (metodo) · 1555 (implementacion) · 1418 (bloques IP) · 1435 (ruta smu7)
ESTADO=PROBADO · el reset MODE1 de esta placa NO resetea: psp_gpu_reset devuelve 0 sin hacer
       nada, porque load_type = AMDGPU_FW_LOAD_SMU y el guard pide FW_LOAD_PSP
       · las TRES comprobaciones posteriores pasan sin haber reseteado nada
       · el oraculo final no comprueba "se reseteo" sino "el dispositivo se puede leer"
       · y un dispositivo al que no se reseteo se puede leer
       · DECLARADO: que asic_ops/nbio.funcs ata Polaris12 NO es determinable de este corpus
```

## 1. De donde vengo

`1551` dio el metodo (MODE1). `1555` dio la implementacion (la rama PSP, no la del SMU). Y el
`1555` dejo escrito, textual, el siguiente pregunta: que hay en `psp_gpu_reset`.

Es la funcion. Y a tres hallazgos de esta parte, el 1555 dejo la pregunta abierta:
que hay dentro de `psp_gpu_reset`. Y no tiene cuerpo util para esta placa.

## 2. El guard, y la pregunta que responde mal

```c
  /* amdgpu_psp.c:3420 */
  int psp_gpu_reset(struct amdgpu_device *adev)
  {
          int ret;
          if (adev->firmware.load_type != AMDGPU_FW_LOAD_PSP)
                  return 0;                       /* <-- aqui se sale */
          mutex_lock(&adev->psp.mutex);
          ret = psp_mode1_reset(&adev->psp);
          mutex_unlock(&adev->psp.mutex);
          return ret;
  }
```

**Devuelve 0 —que es exito— sin resetear nada**, si el firmware no lo cargo el PSP. Y el PSP no
existe en esta placa (`1418`: nueve bloques, ninguno PSP; y el `1555`/`1551` ya usamos que MP1
ausente). Falta el valor de `load_type`.

## 3. `load_type` en esta placa, y es SMU

Solo hay **dos** asignaciones a `adev->firmware.load_type` en todo el driver. La que manda:

```c
  /* amdgpu_device.c:1598 */
  adev->firmware.load_type = amdgpu_ucode_get_load_type(adev, amdgpu_fw_load_type);
```

```c
  /* amdgpu_ucode.c:555-584 */
  enum amdgpu_firmware_load_type
  amdgpu_ucode_get_load_type(struct amdgpu_device *adev, int load_type)
  {
          switch (adev->asic_type) {
          ...
          case CHIP_POLARIS10:
          case CHIP_POLARIS11:
          case CHIP_POLARIS12:          /* :582 */
          case CHIP_VEGAM:
                  return AMDGPU_FW_LOAD_SMU;
```

Con el enum de `amdgpu_ucode.h:562-566`:

```text
  0  AMDGPU_FW_LOAD_DIRECT
  1  AMDGPU_FW_LOAD_PSP
  2  AMDGPU_FW_LOAD_SMU              <-- esta placa
  3  AMDGPU_FW_LOAD_RLC_BACKDOOR_AUTO
```

> **PROBADO: en esta placa `load_type == AMDGPU_FW_LOAD_SMU` (2), y el guard de `psp_gpu_reset`
> exige `FW_LOAD_PSP` (1). El guard es verdadero y la funcion se sale.**

Y esto encaja con lo demas, que ya estaba medido: el firmware lo carga el **SMC legacy**
(`1435`: la ruta de potencia es smu7 y no swsmu), y el `1555` ya habia visto que
`is_support_sw_smu` es falso justamente por eso. **La misma causa, el `load_type`, decide el
guard del reset.**

## 4. Y despues hay tres verificaciones que no pueden verlo

```c
  /* amdgpu_device.c:5026-5057 */
  if (ret)
          goto mode1_reset_failed;

  /* enable mmio access after mode 1 reset completed */
  adev->no_hw_access = false;
  smp_mb();

  amdgpu_device_load_pci_state(adev->pdev);
  ret = amdgpu_psp_wait_for_bootloader(adev);          /* (a) */
  if (ret)
          goto mode1_reset_failed;

  /* wait for asic to come out of reset */
  for (i = 0; i < adev->usec_timeout; i++) {
          u32 memsize = adev->nbio.funcs->get_memsize(adev);
          if (memsize != 0xffffffff)                    /* (b) */
                  break;
          udelay(1);
  }
  if (i >= adev->usec_timeout) { ret = -ETIMEDOUT; goto mode1_reset_failed; }

  if (adev->bios)
          amdgpu_atombios_scratch_regs_engine_hung(adev, false);
  return 0;                                            /* (c) exito */
```

Las tres pasan sin que haya ocurrido nada:

**a) `amdgpu_psp_wait_for_bootloader` — tercera llamada a PSP, y tambien salida silenciosa**

```c
  int amdgpu_psp_wait_for_bootloader(struct amdgpu_device *adev)
  {
          struct psp_context *psp = &adev->psp;
          int ret = 0;
          if (!amdgpu_sriov_vf(adev) && psp->funcs && psp->funcs->wait_for_bootloader != NULL)
                  ret = psp->funcs->wait_for_bootloader(psp);
          return ret;
  }
```

Sin PSP, `psp->funcs` no se rellena, luego el `&&` corta y **devuelve 0**. Igual que el guard
anterior: la ausencia de PSP se traduce en "todo bien".

**b) El oraculo no es "se reseteo", es "se puede leer"**

El comentario dice *"wait for asic to come out of reset"*, y lo que se mira es
`memsize != 0xffffffff`. Eso es una lectura de NBIO. **Un ASIC al que no se le ha reseteado
contesta bien a esa lectura**, asi que el bucle sale en la iteracion 0 y el driver concluye que
el ASIC ha salido del reset. El test es **vacio para este caso**: no distingue "reseteado" de
"nunca reseteado".

**c) Devuelve 0.**

> **PROBADO por lectura de codigo: `amdgpu_device_mode1_reset` puede devolver 0 —exito— sin haber
> reseteado nada, y sus tres comprobaciones no tienen forma de notarlo.** El unico sintoma observable
> seria el log, y el log es el unico que no se mira.

## 5. Y el scratch se alterna igual

```c
  /* :5005-5006, al entrar */
  if (adev->bios)
          amdgpu_atombios_scratch_regs_engine_hung(adev, true);      /* engine HUNG = 1 */
  ...
  /* :5054-5055, al salir */
  if (adev->bios)
          amdgpu_atombios_scratch_regs_engine_hung(adev, false);     /* engine HUNG = 0 */
```

El driver pone "motor colgado", hace su no-op, y limpia el flag. **La contabilidad del scratch del
BIOS queda como si el reset hubiera ido bien.** Ese es el scratch que el `1555` dejo pendiente, y
resulta que es la unica *evidencia* que el reset deja: y es una evidencia que se escribe sola.

## 6. DECLARADO: un hueco de corpus, y no lo disimulo

Para saber **cual tabla de operaciones se le asigna a Polaris12** —y con ella si
`adev->nbio.funcs` es `&nbio...` de NBIO o de una tabla legacy— hay que ir a
`amdgpu_discovery.c`. Y ese fichero esta **podado** en este corpus:

```text
  casos CHIP_ en amdgpu_discovery.c:            13
  CHIP_POLARIS10 / POLARIS11 / POLARIS12 / NAVI10:   0  0  0  0
```

**Cero ocurrencias.** Las asignaciones a `adev->nbio.funcs` que si estan (13, en
`amdgpu_discovery.c:3132-3193`) no se pueden aplicar a esta placa sin la tabla que falta.

> **NOT_DETERMINED: que asic_ops y que nbio.funcs se instalan en Polaris12 en este corpus.**
> No lo afirmo en ningun sentido. No es que sean NULL, ni que falten, ni que el camino no se recorra.

**Lo que si puedo afirmar, y por que el hueco no me lo impide:**

`adev->nbio.funcs->get_memsize(adev)` es un **desreferimiento incondicional**. Si `nbio.funcs`
fuese NULL en una placa que llega ahi, el driver habria reventado antes de poder imprimir nada. Y
el driver imprime, porque el log tiene las tres lineas. Luego:

> **PROBADO por propio diseno del codigo: cualquier placa que llegue a esa linea tiene
> `nbio.funcs` no-NULL.** El hueco de corpus no puede cambiar la semantica del oraculo — solo
> cual registro concreto lee. Y la semantica del oraculo es lo que estoy afirmando.

Eso es lo que §16 pide cuando el scope no da para el detalle: no concluir el detalle, concluir lo
que el detalle no puede cambiar.

## 7. Lo que si esta probado sobre el binding, y por una via distinta

El binding del ASIC no viene de `amdgpu_discovery.c`, viene de la tabla de IDs PCI, que si esta:

```c
  /* amdgpu_drv.c:2033-2041 */
  /* Polaris12 */
  {0x1002, 0x6980, ..., CHIP_POLARIS12},
  {0x1002, 0x6995, ..., CHIP_POLARIS12},
  {0x1002, 0x6997, ..., CHIP_POLARIS12},
  {0x1002, 0x699F, ..., CHIP_POLARIS12},     /* :2041  <-- esta tarjeta */
```

Y medido en esta maquina, lectura pura:

```text
  01:00.0  VGA compatible controller: Lexa PRO [Radeon 540/540X/550/550X / RX 540X/550/550X]
           [1002:699f] (rev c7)
```

> **PROBADO por dos vias: `0x699F` esta en la tabla de `amdgpu_drv.c:2041` como
> `CHIP_POLARIS12`, y la tarjeta de esta maquina es `1002:699f`.** Eight IDs distintos comparten
> ASIC; el nuestro es uno de los ocho.

## 8. Donde queda la parte 2

```text
  metodo de reset                    PROBADO  MODE1                     1551
  ramas de BACO como reset           INALCANZABLES                   1551
  modo de runtime pm                 PROBADO  BACO                     1551
  implementacion de MODE1            PROBADO  rama PSP                1555
  load_type de esta placa            PROBADO  AMDGPU_FW_LOAD_SMU      este
  el cuerpo del reset                NO OP, por el guard              este
  las 3 verificaciones               VACIAS para este caso           este
  el scratch, como evidencia         SE ESCRIBE SOLO                 este
  que asic_ops / nbio.funcs          NOT_DETERMINED, corpus podado   este
  la recuperacion de un cuelgue real  SIN MIRAR.  Si el reset no hace nada, ¿que
                                      hace el otro camino de recuperacion, y cual
                                      de los dos se elige?  Siguiente.
  DRIVER_SCRATCH                     SIN MIRAR
RIESGO        ninguno.  Un lspci de lectura.  Cero escrituras, cero sysfs, cero modulos.
LIMITE        el cuerpo de MODE1 esta probado por lectura; que se RECORRA en esta maquina
              depende de la tabla de ops, que el corpus no tiene.  El finding dice lo que
              pasa SI se recorre, y no afirma que se recorra.
```

## 9. Decision log (§103)

```text
DECISION    publicar que el reset es un no-op, y declarar a la vez el hueco de corpus
WHY         el no-op esta probado por lectura del codigo, sin ambiguedad.  El alcance del
            "si se recorre" depende de una tabla que no esta, y eso se dice, no se tapa.
            Un hallazgo que afirma mas de lo que sabe es peor que uno que se queda corto:
            §62 pide scope suficiente, y el scope aqui es asimetrico.
ALTERNATIVA  no publicar hasta resolver la tabla de ops.  Descartada: el hallazgo del guard
            y del oraculo vacio es cierto con independencia de cual tabla se instale, y
            retrasarlo por un hueco de corpus que no cambia la semantica seria §13 trazado
            como parálisis.
ALTERNATIVA  publicar "el reset no existe en esta placa".  Descartada por imprecisa: el
            reset no se ejecuta; el resto del camino si corre y limpia flags.
DISCriminANTE  para el alcance: falta `amdgpu_discovery.c` completo.  Para el guard: ninguno,
            ya esta cerrado.
CONSECUENCIA  la parte 2 ya tiene metodo, implementacion, y ahora el comportamiento real.  La
            siguiente pregunta —que pasa en un cuelgue, cuando el reset no hace nada— es la
            que de verdad importa para un driver propio.
REVERSIBLE  no depende de nada mutable.  Si el corpus se completa y la tabla resulta ser otra,
            este finding sigue valiendo para la rama PSP; lo unico que habria que revisar es
            si se recorre.
```

## 10. Lo que esto dice de mi propio metodo, sin adornos

Tres hallazgos seguidos en esta parte y los tres salieron de **leer una funcion entera en vez de
leer el `grep`**. El 1551 fue un switch. El 1555 fue una cadena de cuatro. Este fue un `return 0`
en la cuarta linea de la funcion.

Y en los tres casos, la conclusion que importa —el no-op— estaba a cuatro lineas del punto donde
yo ya me habia parado. **No era difficult. Era que no segui leyendo.**

Es la misma clase de fallo que el `<< 16` del 1555 y que el `loEncryption` inyectado del 1555: no me falta
conocimiento, me falta terminar la lectura. Y el arbol ya no lo disimula: por eso esta seccion
existe en cada hallazgo. Es lo unico que separa un hallazgo de una opinion.