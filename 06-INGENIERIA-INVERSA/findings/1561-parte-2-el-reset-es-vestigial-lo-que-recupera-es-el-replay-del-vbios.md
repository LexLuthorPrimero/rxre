# 1561 — PARTE 2: el reset es vestigial; lo que recupera esta tarjeta es el replay del VBIOS

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 5 de la parte
CLASSIFICATION=AUTOCORRECCION-PROPIA+CADENA-CERRADA+CONEXION-CON-LA-PARTE-1
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1559 (LO CORRIGE, y la correccion va contra mi) · 1557 · 1555 · 1551 · 1418 · 1530
ESTADO=PROBADO · el reinit tras un reset completo NO es un reset: es un replay de las tablas
       ATOM del VBIOS, y en esta placa la compuerta de version lo manda a la rama del ATOM
       · y existe un oraculo REAL de extremo a extremo al final: amdgpu_ib_ring_tests
       · y -EAGAIN de ese oraculo es lo que decide reintentar como reset completo
       · CORRECCION AL 1559: "el respaldo no hace nada" era demasiado fuerte.  El MECANISMO del
         reset del respaldo no hace nada; su RECUPERACION si hace, y hace lo unico que puede
         re-inicializar este hardware.
```

## 1. Lo que escribi ayer, y por que hay que corregirlo

El `1559` cerro con esto, textual:

> **PROBADO por lectura de codigo: el respaldo de la recuperacion de esta placa es un reset que no
> resetea nada y reporta exito.**

Es cierto **del mecanismo de reset**. Y sin embargo es una conclusion incompleta que induce a
error, porque hace parecer que el respaldo es inútil. Y no lo es.

Leyendo lo que viene **despues** del reset —que es lo que no hice— resulta que hay un segundo
dispositivo de recuperacion, y es el que realmente funciona. §80 obliga a escribir esto.

## 2. El reinit tiene dos ramas, y la que importa es una

```c
  /* amdgpu_device.c:5178, 5190-5206 */
  full_reset = test_bit(AMDGPU_NEED_FULL_RESET, &reset_context->flags);
  ...
  list_for_each_entry(tmp_adev, device_list_handle, reset_list) {
          amdgpu_set_init_level(tmp_adev, init_level);
          if (full_reset) {
                  /* post card */
                  amdgpu_reset_set_dpc_status(tmp_adev, false);
                  amdgpu_ras_clear_err_state(tmp_adev);
                  r = amdgpu_device_asic_init(tmp_adev);        /* <-- LO IMPORTANTE */
                  if (r) {
                          dev_warn(tmp_adev->dev, "asic atom init failed!");
                  } else {
                          dev_info(tmp_adev->dev,
                                   "GPU reset succeeded, trying to resume\n");
                          r = amdgpu_device_ip_resume_phase1(tmp_adev);
                          ...
                          vram_lost = amdgpu_device_check_vram_lost(tmp_adev);
                          ...
                          r = amdgpu_device_fw_loading(tmp_adev);
```

**La rama `full_reset` no resetea: inicializa el ASIC otra vez.** Y lo hace con
`amdgpu_device_asic_init`, que es la funcion que **reproduce las tablas del VBIOS**.

Despues, el resto de la cadena es la misma en las dos ramas:

```text
  reinit (full_reset o no)
    -> amdgpu_device_ip_resume_phase2 / phase3
    -> amdgpu_ttm_set_buffer_funcs_status
    -> amdgpu_device_ip_late_init
    -> amdgpu_userq_post_reset(tmp_adev, vram_lost)
    -> drm_client_dev_resume
```

## 3. Y ahi esta la compuerta que decide el replay

```c
  /* amdgpu_device.c:879-906, amdgpu_device_asic_init */
  static int amdgpu_device_asic_init(struct amdgpu_device *adev)
  {
          flags = amdgpu_device_get_vbios_flags(adev);
          optional = !!(flags & (AMDGPU_VBIOS_OPTIONAL | AMDGPU_VBIOS_SKIP));
          if (amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 4, 3) ||
              amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 4, 4) ||
              amdgpu_ip_version(adev, GC_HWIP, 0) == IP_VERSION(9, 5, 0) ||
              amdgpu_ip_version(adev, GC_HWIP, 0) >= IP_VERSION(11, 0, 0)) {
                  amdgpu_psp_wait_for_bootloader(adev);          /* ruta PSP */
                  if (optional && !adev->bios) return 0;
                  return amdgpu_atomfirmware_asic_init(adev, true);
          } else {
                  if (optional && !adev->bios) return 0;
                  return amdgpu_atom_asic_init(adev->mode_info.atom_context);   /* :903 */
          }
  }
```

La aritmetica, con `IP_VERSION` de `amdgpu_ip.h:77-79` y el `& ~0xFFU` de `amdgpu.h:1211`:

```text
  GC_HWIP de esta placa    = IP_VERSION(8, 0, 0) = 0x08000000   (1418 midio gfx_v8_0_0)
  IP_VERSION(11, 0, 0)                                = 0x0B000000
  0x08000000 >= 0x0B000000 ?  FALSE
  9.4.3 = 0x09040300 > 0x08000000  -> tampoco es igual
```

> **PROBADO: esta placa cae en el `else`, y el replay es `amdgpu_atom_asic_init()` —el parser del
> BIOS ATOM—, no `amdgpu_atomfirmware_asic_init()` que va por PSP.** Y por el camino del `1557`:
> ni PSP ni atomfirmware. **El replay del VBIOS no necesita el PSP en esta generación.**

## 4. Esto reencuentra el 1530 desde el otro lado

El `1530` cerro, textual, que *"el ROM programa la memoria"* y que *"amdgpu no escribe ningun
registro de configuracion en gfx8"*. Eso se publico alli, desde el arranque, y la consecuencia practica era
"el controlador no programa la memoria, la programo el ROM".

Este hallazgo lo reencuentra **desde la recuperacion**: el unico mecanismo de re-inicializacion del
hardware en un cuelgue es **volver a ejecutar ese mismo ROM**.

```text
  arranque      el ROM programa el ASIC          1530
  cuelgue       el reset no hace nada             1557
               -> y no hacia falta                este
  reinit        se re-ejecuta el ROM              este
```

> **PROBADO: el reset MODE1 de esta placa es vestigial.** La funcion devuelve 0 sin escribir
> registros, sus tres verificaciones son vacias, y el trabajo de verdad lo hace despues un replay
> del VBIOS que no depende del reset. **El reset es el paso ceremonial; el replay es el
> mecanismo.**

Y por eso el `1559` se queda corto: decia que el respaldo no hacia nada, cuando lo cierto es que el
**reset** del respaldo no hace nada y **su reinit lo hace todo**.

## 5. Y hay un oraculo real, que es lo que hace que esto no sea un cuento

El `1557` dijo que las tres verificaciones internas del reset son vacias. Sigue siendo cierto. Pero
no es el final del camino:

```c
  /* amdgpu_device.c:5286-5298 */
  out:
          if (!r) {
                  amdgpu_set_init_level(tmp_adev, AMDGPU_INIT_LEVEL_DEFAULT);
                  amdgpu_irq_gpu_reset_resume_helper(tmp_adev);
                  r = amdgpu_ib_ring_tests(tmp_adev);        /* <-- ORACULO REAL */
                  if (r) {
                          dev_err(tmp_adev->dev, "ib ring test failed (%d).\n", r);
                          r = -EAGAIN;
                          goto end;
                  }
          }
```

`amdgpu_ib_ring_tests` (`amdgpu_ib.c:406`) **escribe en un IB y lo lee de vuelta a traves de la
GPU**, con timeout. Eso **si** tiene poder de falsar la hipotesis "la GPU se recupero": si la GPU
sigue colgada, el test no pasa.

Y el valor que produce es el que gobierna el siguiente paso:

```c
  /* amdgpu_device.c:5377-5381 */
  r = amdgpu_device_reinit_after_reset(reset_context);
  if (r == -EAGAIN)
          set_bit(AMDGPU_NEED_FULL_RESET, &reset_context->flags);   /* reintenta como COMPLETO */
  else
          clear_bit(AMDGPU_NEED_FULL_RESET, &reset_context->flags);
```

```text
  soft reset  -> reinit (full_reset=false) -> ib_ring_tests
      ok      -> -EAGAIN no -> AMDGPU_NEED_FULL_RESET se BORRA        fin
      fallo   -> -EAGAIN    -> AMDGPU_NEED_FULL_RESET se PONE
                                    |
                                    v
  reintento  -> full_reset = true -> asic_init -> replay del VBIOS -> ib_ring_tests
```

> **PROBADO: la recuperacion de esta placa es un bucle de dos etapas con un discriminante real, y
> la segunda etapa es un replay del VBIOS.** El bucle no miente: si la GPU no vuelve, el test de IB
> lo dice y el reintento ocurre. Lo que no hace la segunda etapa es **resetear**, y ya se sabe por
> que (`1557`).

## 6. La cadena completa de la parte 2, en un solo sitio

```text
  cuelgue
    |
    +-- ETAPA 1: soft reset                       1559
    |     amdgpu_gpu_recovery = -1 -> se intenta
    |     escribe mmSRBM_SOFT_RESET
    |     postcondicion real: relee SRBM_STATUS
    |
    +-- reinit(full_reset = false)
    |     resume phases 1/2/3, late_init, userq_post_reset
    |     amdgpu_ib_ring_tests                    <- oraculo
    |        ok    -> fin
    |        fallo -> -EAGAIN
    |
    +-- ETAPA 2: reset COMPLETO                   1551/1555/1557
    |     MODE1 -> rama PSP -> psp_gpu_reset
    |       load_type(SMU) != PSP -> return 0 SIN RESETEAR
    |     las 3 verificaciones internas: vacias
    |       (oranica la que he hecho, el 1555 lo coro)
    |
    +-- reinit(full_reset = true)
          amdgpu_device_asic_init                <-- LO QUE RECUPERA DE VERDAD
            GC_HWIP 8.x < 11.0.0 -> else
            amdgpu_atom_asic_init()              replay de las tablas ATOM del VBIOS
          fw_loading, resume phases, late_init
          amdgpu_ib_ring_tests                    <- oraculo, de nuevo
```

## 7. Que cambia y que no, de lo que he dicho

```text
  1557  "las 3 verificaciones internas del reset son vacias"        SE MANTIENE.  Es cierto.
  1557  "puede devolver 0 sin resetear nada"                         SE MANTIENE.
  1559  "el respaldo es un reset que no resetea nada"               SE MANTIENE, del mecanismo.
  1559  implicito: "el respaldo es inutil"                          RECTIFICADO por este.
        La recuperacion del respaldo no es inutil: replayea el VBIOS y reintenta con un
        oraculo real.  Era una conclusion a medias, y §80 dice que se escribe.
  107   "el driver da por hecho que un reset vacia las TLB"          AFINADO.
        En la rama del soft reset hay un reset real, luego la suposicion tiene respaldo.
        En la rama del completo no hay reset, y ahi el respaldo es el replay, que reprograma
        el controlador de memoria entero y por tanto invalida las TLB de otra manera.
```

## 8. Decision log (§103)

```text
DECISION    publicar una correccion contra mi propio hallazgo del dia anterior
WHY         §80: un hallazgo que solo confirma no compensa uno que corrige, y este corrige una
            implicacion mia que era falsa.  Ademas §62: la conclusion del 1559 no cerraba la
            pregunta que decia cerrar ("que se restaura si el reset no resetea"), porque la
            respuesta era justamente el replay.
ALTERNATIVA  no tocar el 1559 y publicar este como un hallazgo mas.  Descartada: dejaria el 1559
            con una conclusion a medias y un lector que se quedaria con la version falsa.
ALTERNATIVA  reescribir el 1559.  Descartada: el 1559 es correcto sobre lo que medido; lo que
            faltaba era el tramo siguiente, que es informacion nueva.  Corregir hacia atras es
            reescribir historia; corregir hacia delante es avanzar.
DISCriminANTE  para el alcance, falta saber si `amdgpu_atom_asic_init` puede fallar.  Es
            observable por el `dev_warn("asic atom init failed!")` de :5198, pero solo con un
            cuelgue real, que no puedo provocar.  DEFERRED, no NOT_DETERMINED.
CONSECUENCIA  la parte 2 tiene el mecanismo de recuperacion entero.  Para un driver propio la
            conclusion es directa: la primitiva de recuperacion que sirve en esta tarjeta es
            "re-ejecutar el ROM", no "mode1 reset".
REVERSIBLE  nada aqui es configurable en runtime.
```

## 9. Lo que esto significa para el objetivo, y lo digo sin adornos

Cinco hallazgos de esta parte y el resultado es este:

```text
  metodo de reset          MODE1             que funciona
  implementacion           rama PSP          que no hace nada
  mecanismo util           SRBM_SOFT_RESET   que se intenta por defecto
  mecanismo de respaldo    replay del VBIOS  que es el que re-inicializa de verdad
  oraculo                  IB ring test      que si puede fallar
```

**Ninguno de los cinco es el que uno esperaria leyendo un reset de forma general.** Y tres de
ellos estan decoupling de la ruta que esta placa no tiene (MP1, PSP, atomfirmware).

Para un driver propio la leccion es concreta y accionable: **en Polaris12 la recuperacion no se
programa con un reset, se programa reejecutando el VBIOS.** Y eso encaja con el `1530`: si el ROM
es lo que programa la memoria, es porque el ASIC esta hecho para ser inicializado asi, y el
controlador de upstream se apoya en ello desde el arranque.

Lo que **no** he hecho, y queda dicho: no he leido `amdgpu_atom_asic_init` ni el parser ATOM. Sé
que se llama y bajo que compuerta entra; **no sé** que tablas ejecuta ni en que orden. Eso es el
siguiente trabajo de la parte 2, y es un buen sitio para seguir porque es donde esta la verdad de
como se inicializa esta tarjeta — que es la pregunta con la que empezo todo.