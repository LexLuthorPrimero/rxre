# 1559 — PARTE 2: hay dos resets con el mismo nombre, y el único que resetea de verdad es el que casi nadie mira

```text
AGENCIA=RX550-INVESTIGACION · PARTE=2/RESET-RECOVERY · HALLAZGO 4 de la parte
CLASSIFICATION=SEPTIMO-HOMONIMO+CADENA-CERRADA+AUTOCORRECCION-DECISIVA
TRACK=STATIC · CERO HARDWARE · Intel no tocada
GENERADO=2026-10-05
AFECTADO=1557 (lo completa) · 1551 · 1555 · 107 (arte previo, y lo afina)
ESTADO=PROBADO · en un cuelgue, el driver intenta el SOFT RESET antes que nada, y se intenta
       por defecto (amdgpu_gpu_recovery = -1, que en C es verdadero)
       · el soft reset es el unico de los caminos de reset de esta placa que ESCRIBE registros
       · su postcondicion es REAL: vuelve a leer SRBM_STATUS y si sigue ocupado se declara fallido
       · y si el soft reset falla, el respaldo es el reset COMPLETO, que el 1557 probo que no
         hace nada y devuelve exito
       · AUTOCORRECCION:Hipote que iba a publicar ("la mascara se muestrea en el arranque con
         los buses ociosos, luego no hay soft reset") era FALSA.  Se muestrea en la RECUPERACION.
         Lo verifique antes de escribir, y por eso esta seccion es la que mas valor tiene.
```

## 1. La lectura del 107 me contradicted a mí mismo, y por eso lo leí

El 107 es el unico hallazgo previo de esta parte y dice, textual:

> *"El driver da por hecho que un reset de GPU vacía los TLBs"* — `amdgpu_gmc.c:722-727`
> *"el reset de esta placa **no escribe `VM_INVALIDATE_REQUEST`**"* — solo pone y quita
> `SRBM_SOFT_RESET`, en `gmc_v8_0.c:1343-1370`

Y el `1557` que escribi ayer dice que el reset **MODE1 no hace nada**. Los dos son ciertos y son
incompatibles como frase, porque **"el reset" son dos mecanismos distintos con el mismo nombre.**

> **SEPTIMO HOMONIMO DEL PROYECTO.** `reset` = (1) el reset COMPLETO, a nivel PCI, elegido por
> `soc15_asic_reset_method`; (2) el SOFT RESET, a nivel de registro, por bloque IP. Los cinco
> anteriores: `num_banks` (1528), `prt` (139), `SMU74_SoftRegisters` (1540), `CHMAP`/`CHREMAP`
> (1522), `UpH`/`UpHyst` (1544), y el sexto fue BACO del `1551` (metodo de reset frente a modo de
> runtime pm).

El 107 no estaba equivocado: midio el soft reset. Lo que no podia saber, porque hace falta el otro hallazgo, es
que **el otro no hace nada**.

## 2. El orden real en un cuelgue

```c
  /* amdgpu_device.c:5127-5142 */
  if (!amdgpu_sriov_vf(adev)) {

          if (!need_full_reset)
                  need_full_reset = amdgpu_device_ip_need_full_reset(adev);

          if (!need_full_reset && amdgpu_gpu_recovery &&
              amdgpu_device_ip_check_soft_reset(adev)) {          /* (A) */
                  amdgpu_device_ip_pre_soft_reset(adev);
                  r = amdgpu_device_ip_soft_reset(adev);
                  amdgpu_device_ip_post_soft_reset(adev);
                  if (r || amdgpu_device_ip_check_soft_reset(adev)) {   /* (B) */
                          dev_info(adev->dev,
                                   "soft reset failed, will fallback to full reset!\n");
                          need_full_reset = true;
                  }
          }
          ...
          if (need_full_reset)
                  r = amdgpu_device_ip_suspend(adev);
```

**El soft reset va primero**, y el completo es el **respaldo**, no la via normal.

## 3. El gate, y se intenta por defecto

```c
  /* amdgpu_drv.c:206 */
  int amdgpu_gpu_recovery = -1; /* auto */
```

El gate de la linea 5133 es `amdgpu_gpu_recovery` a secas, sin comparar contra nada. **En C, `-1` es
verdadero.** Con el default de fabrica, `-1`, **el soft reset se intenta siempre que se cuelgue la
GPU y `need_full_reset` venga falso.**

Esto es un parametro de modulo, o sea que **alguien lo puede cambiar sin recompilar**, y ahi si
habria un comportamiento distinto. No lo mido: es lectura del default, y cambiarlo seria
intervencion.

## 4. Y el soft reset si escribe: ahi esta el unico mecanismo real

```c
  /* gmc_v8_0.c:1302-1326, check_soft_reset — el que DECIDE que bits */
  static bool gmc_v8_0_check_soft_reset(struct amdgpu_ip_block *ip_block)
  {
          u32 srbm_soft_reset = 0;
          u32 tmp = RREG32(mmSRBM_STATUS);

          if (tmp & SRBM_STATUS__VMC_BUSY_MASK)
                  srbm_soft_reset = REG_SET_FIELD(srbm_soft_reset,
                                                  SRBM_SOFT_RESET, SOFT_RESET_VMC, 1);

          if (tmp & (SRBM_STATUS__MCB_BUSY_MASK | SRBM_STATUS__MCB_NON_DISPLAY_BUSY_MASK |
                     SRBM_STATUS__MCC_BUSY_MASK | SRBM_STATUS__MCD_BUSY_MASK)) {
                  if (!(adev->flags & AMD_IS_APU))
                          srbm_soft_reset = REG_SET_FIELD(srbm_soft_reset,
                                                          SRBM_SOFT_RESET, SOFT_RESET_MC, 1);
          }
          if (srbm_soft_reset) { adev->gmc.srbm_soft_reset = srbm_soft_reset; return true; }
          adev->gmc.srbm_soft_reset = 0;
          return false;
  }
```

Y el que los aplica:

```c
  /* gmc_v8_0.c:1343-1370, soft_reset */
          if (!adev->gmc.srbm_soft_reset)
                  return 0;
          srbm_soft_reset = adev->gmc.srbm_soft_reset;
          tmp  = RREG32(mmSRBM_SOFT_RESET);
          tmp |= srbm_soft_reset;
          dev_info(adev->dev, "SRBM_SOFT_RESET=0x%08X\n", tmp);    /* <-- la unica
                                                                          escritura real */
          WREG32(mmSRBM_SOFT_RESET, tmp);
          udelay(50);
          tmp &= ~srbm_soft_reset;
          WREG32(mmSRBM_SOFT_RESET, tmp);
```

Nota sobre el guard `if (!adev->gmc.srbm_soft_reset) return 0;`: **aqui no es una salida silenciosa
peligrosa**, porque en este camino el valor lo acaba de calcular la llamada inmediata anterior,
(A). Solo seria un no-op si `soft_reset` se llamara sin un `check_soft_reset` antes. Lo dejo dicho
porque ayer lo lei al reves y quiero que el razonamiento que lleva al hallazgo correcto tambien
deje escrito el que no.

## 5. El postcondicion del soft reset es REAL, y el del completo no

Comparando los dos oraculos, que es lo que el 1557 dejo abierto:

```text
  SOFT RESET    postcondicion:  volver a leer SRBM_STATUS.  Si los buses SIGUEN ocupados,
                                el reset no ha surtido efecto y se dice:
                                    "soft reset failed, will fallback to full reset!"
                                -> DISCIMINANTE.  Distingue "ha funcionado" de "no".

  COMPLETO      postcondicion:  get_memsize() != 0xffffffff, o sea "el ASIC se puede leer".
                                Un ASIC al que no se reseteo TAMBIEN se puede leer.
                                -> VACIO.  No distingue nada.  (1557)
```

> **PROBADO: de los dos caminos de reset de esta placa, solo el soft reset tiene una
> postcondicion con poder de falsar la propia hipotesis.** El completo no.

## 6. La cadena completa de un cuelgue en esta placa

```text
  cuelgue
    |
    +-- amdgpu_gpu_recovery (= -1, verdadero)  -> se intenta el soft reset
    |     |
    |     +-- check_soft_reset: lee SRBM_STATUS con los buses ocupados
    |     |     -> VMC/MC busy -> fija gmc.srbm_soft_reset
    |     +-- soft_reset: ESCRIBE mmSRBM_SOFT_RESET       <-- UNICA escritura real
    |     +-- check_soft_reset de nuevo
    |           |
    |           +-- sigue ocupado  -> "soft reset failed, will fallback to full reset!"
    |                                  need_full_reset = true
    |
    +-- reset COMPLETO  (el respaldo)
          -> soc15_asic_reset_method = MODE1                (1551)
          -> is_support_sw_smu = false                      (1555)
          -> psp_gpu_reset: load_type(SMU) != PSP -> return 0 sin resetear  (1557)
          -> las 3 verificaciones pasan igual
          -> return 0                                       EXITO, sin haber reseteado
```

> **PROBADO por lectura de codigo: el respaldo de la recuperacion de esta placa es un reset que no
> resetea nada y reporta exito.** Y el 107 se apoya justamente en este: el driver da por hecho que
> un reset vacia las TLB, y en la rama del reset completo **no hay reset**.

## 7. La autocorreccion, que es lo mas util de este hallazgo

Iba a titular: *"la mascara de soft reset se muestrea al arrancar con los buses ociosos, luego
esta tarjeta nunca hace soft reset"*. Sonaba muy bien y encajaba con `gmc_v8_0_check_soft_reset`
leyendo `SRBM_STATUS` una sola vez.

**Es falso, y lo vi un paso antes de escribirlo.** `check_soft_reset` se llama desde
`amdgpu_device.c:5134`, **dentro de la recuperacion**, no del arranque. El contexto de la funcion es
`... Dumping IP State ...`, `soft reset failed, will fallback to full reset`. O sea: se muestrea
**cuando la GPU esta colgada**, que es exactamente cuando los buses estan ocupados. La hipotese
era plausible por el `return false` del final, y estaba dirigida al archivo equivocado.

Tres cosas que la evitaron:

```text
  1  lei el que llama antes de decir cuando corre  -- el producer, no el codigo
  2  el parametro de modulo me decia -1, y -1 es verdadero: mi hipotese exigia que fuera 0
  3  volvi a mirar :5134 porque el nombre de la funcion no cuadraba con mi cronologia
```

La leccion es la misma del `1555` y del `1557`, y ya la he escrito tres veces, asi que la escribo
distinta: **esta vez el fallo no fue no leer, fue leer el archivo equivocado y no askarse de si el
sitio era el correcto.** El `check_soft_reset` esta en `gmc_v8_0.c`, que es donde yo mire, y el que
decide cuando corre esta en `amdgpu_device.c`, que es donde no mire hasta el final.

## 8. Donde queda la parte 2

```text
  metodo de reset                     PROBADO  MODE1                    1551
  ramas de BACO como reset            INALCANZABLES                  1551
  modo de runtime pm                  PROBADO  BACO                    1551
  implementacion de MODE1             PROBADO  rama PSP, no-op         1555 1557
  el respaldo no resetea              PROBADO  return 0 sin escribir   1557
  que va PRIMERO en un cuelgue        PROBADO  el soft reset           este
  el soft reset escribe               PROBADO  mmSRBM_SOFT_RESET       este
  el soft reset se intenta            PROBADO  por defecto, -1         este
  su postcondicion                    PROBADO  real, re-lee STATUS    este
  el 107 y el 1557                    AFINADO  dos resets, no uno
  los TRES: TLB, contexto, RING       SIN MIRAR.  Que se restaura si el reset no resetea?
  la recuperacion de PSP              SIN MIRAR.  Sin PSP, ¿hay vuelta atras en el respaldo?
  amdgpu_device_reinit_after_reset    SIN MIRAR.  Siguiente.
RIESGO        ninguno.  Cero escrituras, cero sysfs, cero modulos.
LIMITE        toda la conclusion es por lectura de codigo.  Que un cuelgue real produzca esta
              cadena no se ha observado: exigiria colgar la GPU, que esta prohibido.
LIMITE        que asic_ops siga sin determinarse (1557), asi que la entrada al camino completo
              no esta probada, solo su cuerpo.
```

## 9. Decision log (§103)

```text
DECISION    publicar la cadena de recuperacion completa, con la rama de respaldo declarada inutil
WHY         cada eslabon esta citado y verificado, y la conclusion —que el unico reset real es el
            soft reset y que su respaldo no hace nada— no depende de ningun dato que no tenga
            producer.  Es la clase de conclusion que §62 pide.
ALTERNATIVA  publicar solo "hay dos resets".  Descartada: es cierto y es menos de la mitad.  El
            valor esta en el orden y en el respaldo.
ALTERNATIVA  bajar la conclusion a "probablemente el soft reset no se intenta".  Descartada: el
            default es -1 y -1 es verdadero.  No hace falta "probablemente".
DISCriminANTE  para confirmar en runtime haria falta un cuelgue real, que no puedo provocar.
            Lo declaro DEFERRED, no NOT_DETERMINED: el codigo ya dice cual es el camino, lo que
            falta es la observacion del evento.
CONSECUENCIA  la parte 2 tiene ya el mecanismo completo de recuperacion y sabe cual es su parte
            hueca.  Lo siguiente es el que se restaura cuando el reset no resetea: reinit.
REVERSIBLE  si alguien carga el modulo con amdgpu_gpu_recovery=0, el soft reset no se intenta y
            solo queda el respaldo, que es peor.  Eso es configurable, no fijo.
```

## 10. Una cosa que este hallazgo deja uncomfortable

El respaldo de la recuperacion es el camino que se usa **cuando el camino bueno ha fallado**. Es
decir: el momento en que la GPU esta peor, es el momento en que el driver hace menos.

Y no lo hace por un bug tonto: lo hace porque el ASIC no tiene a quien pedirle un reset por
registro, y su unico encargo de reset se fue a la rama del PSP, que no existe en este chip. **El
1555 lo explico como una consecuencia de que MP1 no este, y lo es. Pero no es solo eso: es que el
respaldo se eligió precisamente porque se apoyaba en la ruta que la propia placa no tiene.**

Eso no lo arregla un parche de una linea en este controlador. Es una decision de diseno del
upstream que se apoya en una precondicion —PSP presente— que esta tarjeta no cumple. Y para un
driver propio, es exactamente el tipo de cosa que hay que saber **antes** de escribir el reset, no
despues: porque significa que el reset de esta tarjeta hay que hacerlo con los registros que usa
el soft reset, y no con la llamada que el driver hace por defecto.

Lo dejo escrito porque es la clase de conclusion que §111 quiere: no un driver que funciona igual
que el de arriba, sino un driver que sabe por que esta tarjeta es distinta.