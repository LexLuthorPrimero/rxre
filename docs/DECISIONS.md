# DECISIONS — decisiones con su motivo y su reversibilidad

> Una decisión sin motivo escrito se vuelve leyenda. Cada entrada dice qué se decidió,
> por qué, con qué evidencia, y **si es reversible**.
> `MODEL_CHOICE` != `DERIVATION`: una decisión que el hardware no obliga se marca como
> tal, porque es la que un driver propio puede cambiar.
>
> Fuentes: `08-ARQUITECTURA/decisions/DECISIONS-F4.md`,
> `PROYECTO_STATUS.md` §Decisiones arquitectónicas, `04-IMPLEMENTACION/*/README.md`,
> `opencode.json`, `07-DRIVER/kernel/Makefile`.
> `LAST_SCAN: 2026-10-01 11:20 -03:00`

---

## D-01 · La RX550 es GPU secundaria, sin salida de vídeo

```
TIPO        POLICY
ESTADO      VIGENTE desde el principio del proyecto
DECISIÓN    El display va por la Intel HD 4600 (0000:00:02.0, i915, card0).
            La RX550 (0000:01:00.0, amdgpu, card1) no tiene salida de vídeo.
MOTIVO      Decisión deliberada de seguridad. Con el display en la iGPU, perder la
            sesión gráfica NO exige tirar la RX550
CONSECUENCIA POSITIVA  es lo que hace viable todo el resto. Si la RX550 llevara el
                        display, ningún experimento de runtime podría ejecutarse sin
                        arriesgar la sesión
CONSECUENCIA NEGATIVA  las Measurements de display (WSI, frame time) son de la Intel,
                        no de la RX550. No se pueden atribuir a la RX550
REVERSIBLE  sí, y es caro: exige reconfigurar eludor de vídeo y reiniciar
SI SE CAMBIA  todo lo que mida frame time deja de ser válido para esta GPU
```

## D-02 · `AD-10` · `RX550_ALPHA_INSET_STEPS = 0`

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE · commit f870e8e
DECISIÓN    sin inset de endpoints alfa
MOTIVO      mismo PSNR (±0.01 dB) y 2.8x más rápido
EVIDENCIA    PSNR medido en los cuatro perfiles: reference 28.78 · smooth 19.59 ·
             pure noise 13.65 · adversarial 10.90 dB
REVERSIBLE  sí, trivially: es una constante
NOTA        "2.8x más rápido" es un número de la versión del comparador, no de hoy.
             El speedup de la línea B entero es NOT_CONCLUYENTE [NR-11]. El 2.8x
             compara el algoritmo con inset contra el mismo sin inset, que es una
             comparación distinta de la de speedup C-vs-AVX2, y no la invalida.
             No confundir los dos
```

## D-03 · `AD-11` · Interpolación BC3 con redondeo `+3`/`+2`

```
TIPO        DERIVATION de la especificación Microsoft D3D9
ESTADO      VIGENTE, con una reserva explícita
DECISIÓN    la rampa alfa se decodifica con redondeo, no con truncamiento
MOTIVO      la especificación Microsoft D3D9 lo dice
EVIDENCIA    26/26 checks. Dos transcripciones independientes de la spec.
             Capacidad de fallo demostrada: check-ramp-discriminates rechaza el
             mutante conocido (65536/65536 discrepancias, exit 1)
LA RESERVA, y es el punto entero
  AD-11 dice lo que la ESPECIFICACIÓN dice. AD-12 pregunta qué hace el HARDWARE.
  Son preguntas distintas. Si el sampler de esta GPU trunca, AD-11 es incorrecto para
  esta placa y hay que revertirlo. Frontera F2, sin ejecutar
REVERSIBLE  sí, y es lo caro: revertir reabre la divergencia contra bcdec v0.985
LO QUE ESTÁ PROHIBIDO    una prueba de que la especificación dice +3/+2 y presentar
                          eso como respuesta a AD-12. El agreement test actual NO puede
                          responder AD-12: compara contra el decodificador PROPIO, que
                          deriva de las MISMAS decisiones. Un round-trip propio oculta
                          el error por construcción
```

## D-04 · `AD-12` · El comportamiento del sampler del hardware

```
TIPO        HYPOTHESIS
ESTADO      NOT_DETERMINED  (frontera F2)
DECISIÓN    ninguna todavía
POR QUÉ NO ES DECISIÓN    porque la única respuesta posible sería revertir AD-11, y
                          revertir algo medida exige el dato, no una preferencia
EXPERIMENTO  escrito, con autovalidación, sin ejecutar. Texto en F2
BLOQUEO     ninguno técnico. Es un experimento de usuario vía Mesa
VALOR       la única frontera del proyecto cuya respuesta puede obligar a deshacer
             una decisión tomada
```

## D-05 · `D19a` · Convención BC3 `a0 = max, a1 = min`

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE · commit 44bc133
DECISIÓN    el endpoint a0 es el MAYOR y a1 el MENOR
CONSECUENCIA la rama /7 del interpolador va de 0 a 59 de 64. Con la convención
            contraria el rango sería inverso y los bloques no serían los mismos
REVERSIBLE  sí
```

## D-06 · `AD-13` · Los tres defectos del shader se corrigieron; Fase 2 `COMPLETE`

```
TIPO        IMPLEMENTATION + TEST
ESTADO      VIGENTE
DEFECTOS    1) índice de color: `& 0xFFu` donde el C lee 2 bits; el `& 3u` posterior
               recortaba a los dos bits ALTOS del byte. Los píxeles 2 y 3 de cada grupo
               de 4 tomaban el índice de otro píxel. La rama `else` además leía fuera
               del bloque para p=8..15 (c_idx son 4 bytes, una palabra, no dos como el
               array de 6 del alfa)
            2) faltaba `vkCmdPushConstants`: el shader acotaba el dispatch leyendo
               `params.num_blocks` de memoria no inicializada
            3) `DISPATCHES` mal calculado: `ceil(64/256) = 1` cuando el shader mapea una
               invocación a un PÍXEL. Un workgroup de 256 cubre 16 bloques; hacen falta 4
POR QUÉ NO SE VIERON DESDE CPU  `shader_vs_c` dio 0/4096 con los TRES presentes, porque
               modela la aritmética en C y NO compila el GLSL. No puede ver una llamada
               de Vulkan ausente, un dispatch mal contado, ni una lectura fuera de límites
LA PRIMERA CORRIDA NO ERA UNA MEDICIÓN   3197 bytes erróneos. Con basura grande no escribía
               nada; con basura pequeña se ejecutaba por suerte. Se había reportado como
               OBSERVED cuando era una ejecución afortunada. Eso está escrito en el commit
VALIDACIÓN DE LA SALIDA, que es lo que hace que el resultado sea evidencia
  un dispatch que no corre deja el buffer inicializado, y comparado contra la referencia
  da cero discrepancias y un PASS. Las dos comprobaciones —salida no trivial, ningún
  patrón 0xDEADBEEF— son lo que convierte el resultado en evidencia. Sin ellas el defecto
  2 habría producido un PASS vacío
REVISIBLE  sí, y con historial documentado: la referencia del test_alpha_ramp comparaba
           contra bcdec v0.985 (que trunca) y fallaba con 54300/65536. Ahora compara
           contra la spec. El cambio de referencia es correcto dado AD-11, y la capacidad
           de fallar se comprobó DESPUÉS del cambio
```

## D-07 · `AD-14` · `spirv-cross` no es una opción

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE
MOTIVO      no está disponible en este host
REVISIBLE   sí
```

## D-08 · `AD-15` · Orden de fases: el shader va antes que `unbind`

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE PERO CON UNA ADENDA QUE LO CORRIGE
LO QUE DICE  AD-15 aplica a la Fase 3 de medición, y presupone que no se puede medir
            hasta hacer `unbind`
LA ADENDA   F4-AD-20: es INCORRECTA, y se verificó antes de aceptar la tarea.
            `vkcube --gpu_number 1` y `DRI_PRIME=1 glxgears` funcionan en RADV
CONSECUENCIA  AD-12 NO está bloqueada por `unbind`. Es ejecutable hoy con el host como
              está. F2 no necesita ninguna preparación adicional
LO QUE ESTÁ MAL EN EL ARGUMENTO  "si Fase 3 responde truncamiento, F4-AD-12 hay que
            revertirla" mezcla dos cosas distintas: el diseño del shader, y el hecho medido
            de que el hardware usa AD-11. Ver DECISIONS.md F4-AD-12 línea 311
```

## D-09 · `F4-AD-12` · El shader se escribe en OpenCL C

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE
REVISABLE   sí
```

## D-10 · `F4-AD-13` · El firmware se carga desde userspace

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE (Opción A)
REVISABLE   sí
```

## D-11 · `014-q1` · La geometría GPUVM de Q1 — REFUTADA

```
TIPO        DERIVATION que resultó incorrecta
ESTADO      REFUTED por commit 2599c65 (2026-10-01 10:52)
DECISIÓN ORIGINAL   BITS_PER_LEVEL=9 · GPUVA_WIDTH_BITS=30 · MIN_VIABLE_ASPACE=2 MiB
                    los tres como PROVEN
DECISIÓN CORRECTA   block_size=10 · PTB=1024 entradas (8 KiB) · PDB0=16384 (128 KiB)
                    GPUVA=36 bits · unidad mínima 4 MiB
POR QUÉ EL ERROR PASÓ, y es la parte instructive
  (a) fragment_size = 9 también es un 9, y convive con block_size en el MISMO dev_info,
      así que "9" parecía confirmado dos veces
  (b) con max_level=1 la aritmética del tamaño pediría 2 niveles, luego "9 porque 2^9"
      parecía derivar
  (c) se citationó la rama `else if (num_level > 1) block_size = 9;`, que NO corre
QUIÉN LO REFUTÓ  gfx8vmgeom, una herramienta escrita ese mismo día, que contrasta la
      cadena derivada contra la línea que el host imprimió en el boot
COMPROBACIÓN  la cadena derivada coincide con la observada caracter por caracter
HISTÓRICO    `014` mantiene su texto. Este registro y `C-005` son los que lo corrigen
```

## D-12 · `024` §4 · El `-9` de `PAGE_TABLE_BLOCK_SIZE` es `MODEL_CHOICE`, no convención de hardware

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE (con la salvedad de D-11)
DECISIÓN    el offset de 9 en `block_size - 9` es del driver
MOTIVO      el hardware NO lo declara, y lo REDEFINE entre generaciones:
              GFX8   gmc_8_2_sh_mask.h:6543-6544   MASK 0xf000000  SHIFT 0x18
              GFX9   mmhub_1_0_sh_mask.h:8073,8092 MASK 0x78       SHIFT 3
            4 bits en ambos, encoding distinto
CONSECUENCIA  el driver propio puede escribir `block_size` directamente si su convención
              lo permite, y DEBE elegirlo conscientemente
LO QUE SIGUE SIENDO HIPÓTESIS  que el hardware lea el campo como "block_size". La
             arked 4 del propio finding: el valor que llega al registro es PROVEN; su
              interpretación es HYPOTHESIS, sostenida por que el driver escriba el -9 en
              todas las generaciones, no por el hardware
APLICABILIDAD  independiente del error de D-11: §4 no usa block_size
```

## D-13 · El cerrojo de write es `mkdir` sobre un directorio

```
TIPO        POLICY — ley operativa, en COORDINACION.md
ESTADO      VIGENTE Y PARCIALMENTE REFUTADO
LO QUE FUNCIONA  mkdir como exclusión atómica para el MISMO nombre de lock: dos sesiones,
                  misma ruta, una gana. PROVEN
LO QUE NO FUNCIONA
  · el cerrojo raíz no excluye a las sesiones de ámbito  [NR-10] REFUTED
  · el ámbito no desplaza a la raíz, ni la bloquea        [NR-10] REFUTED
  · el test de liveness por /proc/$pid                    INCONCLUSIVE: el PID que
    escribe el protocolo es el del shell que hizo el mkdir, no el del proceso agente
  · git status como árbitro                               REFUTED, y el propio protocolo
    lo dice desde COORDINACION.md:15-19
CONSECUENCIA REAL  dos colisiones el 2026-10-01, y la segunda vez el ÍNDICE NUMÉRICO
                  también colisionó: dos sesiones eligieron 022, dos eligieron 021
LO QUE EL PROTOCOLO YA RECONOCE  "Un `git commit` recién hecho no es un turno libre.
                  El cerrojo, no el árbol, arbitra" (regla 5). Y que un cerrojo
                  abandonado no es permiso para tomarlo (línea 160)
CORRECCIÓN PENDIENTE  frontera F10. Dos arreglos, ambos de un cambio pequeño:
  (a) antes de mkdir .write-lock/<ámbito>, comprobar que .write-lock no existe
  (b) hacer que el owner que escribe el protocolo contenga el token pid= que su propio
      preflight busca  [C-008]
QUIÉN LO APLICA  decisión humana. COORDINACION.md es ley operativa
LO QUE SE PAGÓ  dos pérdidas reales de trabajo, documentadas en COORDINACION.md:9-12.
               Una fue una reversión completa de AD-12 y D13; la otra, un fichero de 787
               líneas sobrescrito por una reescritura que ni compilaba
```

## D-14 · `insmod`/`rmmod` pasan de `deny` a `ask`

```
TIPO        POLICY
ESTADO      VIGENTE desde 65447aa (2026-10-01 06:39)
QUÉ CAMBIA  la política deja de IMPEDIR cargar un módulo y lo PIDE
LO QUE NO ES  una autorización concedida. "ask" significa que el agente pregunta
NO SE HA HECHO  no se ha cargado ningún módulo. La GPU sigue intacta
PENDIENTE   el "experimento B" no está definido en el árbol de forma localizable.
            Faltan sus criterios PASS/FAIL y su prueba de recuperación. Ver EXPERIMENTS §5
```

## D-15 · Se mantiene `rx550.ko` aunque no sea driver PCI

```
TIPO        MODEL_CHOICE
ESTADO      VIGENTE por defecto, PENDIENTE de decisión (frontera F4)
LO QUE DICE EL MAKEFILE  "SE MANTIENE, pero ya no es el camino principal: no es un driver
            PCI (no tiene struct pci_driver, no se registra con pci_register_driver,
            verificado con nm sobre el .ko) y un char device no puede dar a userspace
            un BAR mapeado, que es lo que un driver de GPU necesita"
POR QUÉ SE MANTIENE  dos razones, ambas reales: para que su código no se pudra, y porque
            `rx550_pm4.c` tiene una suite de pruebas que depende de él
REVISABLE   sí
LO QUE ESTÁ VERIFICADO  que rx550_drv.ko SÍ es driver PCI y rx550.ko NO, por `nm`, con
            control negativo en cada comprobación
LO QUE FALTA  la decisión. Está escrita la razón de mantenerlo, no la de retirarlo
```

## D-16 · `NO_HISTORICAL_INHERITANCE`

```
TIPO        POLICY
ESTADO      VIGENTE (estaba en la cabecera del AGENTS.md anterior)
TEXTO       "ninguna decisión de implementación de otro driver se incorpora al diseño
            propio por mera existencia, precedencia, antigüedad, complejidad o aparente
            importancia. Toda decisión heredada debe justificarse por un requisito
            verificable, una restricción del hardware, un requisito del ABI o una
            evidencia experimental"
POR QUÉ IMPORTA  es lo que convierte D-04/AD-12 en una frontera y no en un supuesto.
            La autoridad del proyecto es EVIDENCIA → SEMÁNTICA → MODELO → TEST
            DISCRIMINANTE → IMPLEMENTACIÓN → VALIDACIÓN. Nunca al revés
CONCRETO     D-12 es la aplicación: el `-9` del driver de referencia no se hereda porque
            el driver de referencia lo haga, sino porque el hardware REDEFINE el campo
            entre generaciones y por tanto el offset no puede leerse como estable
CONTRAPUNTO QUE EL PROYECTO YA CAYÓ EN
  dos veces: D-11 (se heredó la rama que no corre) y C-005 (se heredó la cifra del
  documento que ya estaba refutada). Los dos son el mismo error: tomar una afirmación
  de un driver o de un documento como si fuera una propiedad del hardware
```

## D-17 · No borrar historia científica

```
TIPO        POLICY
ESTADO      VIGENTE
REGLA       un cambio de conclusión no borra la anterior. Se marca:
              PROVEN -> REFUTED
              PROVEN -> SUPERSEDED
            y se registra QUÉ CAMBIÓ, POR QUÉ, con QUÉ EVIDENCIA NUEVA, y a QUIÉNES
            AFECTA
CÓMO SE APLICA EN ESTE TRABAJO
  · 022 §4 conserva su afirmación original sobre dw4, con la marca CORRECCION (ronda 023)
  · PROYECTO_STATUS.md conserva el texto literal de las 4 limitaciones, tachadas y con
    el commit y la hora que las deja obsoletas
  · 014-q1 conserva sus tres cifras, con la corrección en C-005
  · 00-INDICE/MASTER-RESEARCH-STATUS.md NO se borra: contiene el histórico R-4B/D6 y
    nadie ha decidido que se descarte
  · 04-FINAL-RESEARCH-STATUS.md se conserva marcado HISTORICAL_SNAPSHOT por su propio
    autor, con una nota de precedencia que apunta a 01-README.md
POR QUÉ NO ES SENTIMENTALIDAD  sin el estado anterior no se puede reconstruir cómo
  llegó el conocimiento al actual, y una contradicción que se "resuelve" borrando una
  de las dos partes se repite dentro de seis meses
```

## D-18 · El diagnóstico sólo-lectura se puede ejecutar sin cerrojo

```
TIPO        POLICY
ESTADO      VIGENTE (COORDINACION.md §Excepciones)
TEXTO       "READ_ANALYSIS con cerrojo ajeno -> permitido, y es lo normal"
LO QUE HIZO ESTE TRABAJO  todo lo que hay en docs/ se produjo en READ_ANALYSIS o bajo
            cerrojo de ámbito propio: `docs/` y `rootmd`, PIDs 55320 y 56795, ambos
            liberados al terminar
LO QUE NO HIZO  no tomó ningún cerrojo ajeno, no borró ningún `owner`, y no commiteó
            ficheros de otras sesiones
```

## Resumen: qué decisiones tienen más consecuencia si se rethink

| ID | Decisión | Reversible | Consecuencia de revertir |
|---|---|---|---|
| D-03 / AD-11 | redondeo `+3`/`+2` | sí | reabre la divergencia contra bcdec; el encoder emitiría bloques que la GPU decodifica distinto |
| D-01 | RX550 sin display | sí, caro | invalida toda medición de frame time |
| D-06 / AD-13 | los tres defectos corregidos | sí | el agreement test vuelve a fallar |
| D-14 | `insmod` en `ask` | sí | cambia la política de seguridad del harness |
| D-13 | cerrojo por `mkdir` | sí | **las dos colisiones del 2026-10-01_PASSARÍAN a ser la norma** |
| D-11 | geometría de Q1 | ya revertida | — |
| D-02 | `inset 0` | sí, constante | — |
| D-15 | mantener `rx550.ko` | sí | requiere mover la suite de `rx550_pm4.c` |