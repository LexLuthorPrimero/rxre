# 1511 — la ruta A no puede contribuir nada en esta placa, y por eso el 64 salió de la ruta B

```text
AGENCIA=RX550-INVESTIGACION · PARTE=1/MC-MEMORIA · FASE=0
CLASSIFICATION=EVIDENCIA-DE-ROM + REFUTACION-DE-HIPOTESIS-PROPIA + CIERRE-DE-NOT_DETERMINED
TRACK=STATIC · CERO HARDWARE · 0000:01:00.0 no tocada · Intel no tocada
GENERADO=2026-10-05
AFECTADO=911, 923, 1468   NO los reabre: los estrecha
ESTADO=PROBADO · la ruta A devuelve 0 en esta placa, por ausencia de tabla, no por la formula
       · por el ELIMINADO, el 64 lo produjo la ruta B. 923 lo dejo NOT_DETERMINED; aqui queda
       · y aparece un TERCER mecanismo para el 64 de la ruta B, que 923 no habia listado
```

## 0. Lo que NO hace este hallazgo

**El 64 contra el 128 ya estaba resuelto.** El `911` lo closed textualmente: *"el campo del
driver está mal y el VBIOS tiene razón. El bus es de 128 bits"*, y el `923` mapeó las dos rutas
de `gmc_v8_0_mc_init` y concluded que **ninguna** lee `ucMemBusWidth`.

Yo llegué aquí believing que tenía un problema nuevo, y lo tenía: **a punto de publicar un cuarto
take sobre algo ya cerrado tres veces.** Se paró al leer el titulo del `911`. Lo que sigue es el
incremento pequeño que queda, y es real, pero es pequeño y hay que decirlo antes de que nadie lo
lea como una resolucion.

## 1. El hueco exacto que queda, textual

Del `923`, linea 51-53, sin parafrasear:

> `numchan=1, chansize=64` da exactamente el 64 que informa `vram_bit_width`. También lo da
> `numchan=2, chansize=32`. **El mecanismo exacto de la ruta que produjo este 64 concreto es
> `NOT_DETERMINED`**; que ninguna de las dos sea correcta es `PROVEN`.

O sea: el `923` enumerable las dos rutas y probó que las dos están mal, pero **no respondió de
cual de las dos escribio el numero que el kernel publico**. Ese es el hueco, y es un `NOT_DETERMINED`
declarado, no una ausencia mia.

## 2. La ruta A no puede contribuir: la tabla no esta

`amdgpu_atombios_get_vram_width` depende de una tabla que se lee por indice. El indice no lo
supongo: sale del layout del struct, porque `GetIndexIntoMasterTable` es literally una division de
`offsetof` entre `sizeof(USHORT)` (`atombios.h:7151`).

`ATOM_MASTER_LIST_OF_DATA_TABLES` tiene 35 entradas, todas `USHORT`, y `IntegratedSystemInfo` es la
**indice 30**. Con el puntero maestro de datos en `base+0x20 = 0x97F2`, y leyendo con
`tools/atom_chain.py`:

```text
   idx  nombre                       offset
  ------------------------------------------------
    28  VRAM_Info                    0xA30A     presente
    29  MemoryTrainingInfo           0x0000     AUSENTE
  > 30  IntegratedSystemInfo         0x0000     AUSENTE
    31  ASIC_ProfilingInfo           0x0000     AUSENTE
```

Y la guarda que convierte ese `0x0000` en un fallo esta en `atom.c:1650`:

```c
  1646   int offset = index * 2 + 4;
  1647   int idx = CU16(ctx->data_table + offset);
  1648   u16 *mdt = (u16 *)(ctx->bios + ctx->data_table + 4);
  1650   if (!mdt[index])
  1651       return false;
```

Consecuencia, sin paso intermedio:

```text
  mdt[30] == 0x0000                       MEDIDO
    -> amdgpu_atom_parse_data_header      devuelve false     atom.c:1651
    -> el if de atombios.c:779 no se toma
    -> return 0                           atombios.c:792
    -> !adev->gmc.vram_width  es CERO     gmc_v8_0.c:516
    -> el respaldo se ejecuta             gmc_v8_0.c:517
```

**La ruta A no puede haver escrito el 64 en esta placa.** No es que su formula sea conceptualmente
equivocada —el `911` y el `923` ya probaron eso— es que aqui **no llega ni a evaluarse**, porque la
tabla que pretendia leer no esta en el ROM.

> **PROBADO:** en esta placa la ruta A de `adev->gmc.vram_width` retorna 0, y el valor publicado lo
> produjo la ruta B. El `NOT_DETERMINED` del `923` queda cerrado por eliminacion.

## 3. El tercer mecanismo, que el 923 no habia listado

El `923` ofrece dos candidatas para el 64 de la ruta B: `numchan=1 × chansize=64` y
`numchan=2 × chansize=32`. Hay una tercera que no es un par de valores sino una **causa**, y se ve en
el orden de fases:

```text
  sw_init   gmc_v8_0.c:1143   gmc_v8_0_init_microcode()      carga el blob de disco a memoria
  sw_init   gmc_v8_0.c:1149   gmc_v8_0_mc_init()             LEE RAMCFG y CHMAP  -> vram_width
  hw_init   gmc_v8_0.c:1210   gmc_v8_0_mc_program()           programa el controlador
  hw_init   gmc_v8_0.c:1221   gmc_v8_0_polaris_mc_load_microcode()  escribe el ucode de MC
```

Y el dato que lo hace mecanismo y no coincidencia:

```text
  WREG32(mmMC_SHARED_CHMAP ...)   0 apariciones en todo el arbol amdgpu
  WREG32(mmMC_ARB_RAMCFG  ...)   0 apariciones en todo el arbol amdgpu
```

El driver **solo los lee**. Quien los programa es `gmc_v8_0_mc_program` y el firmware de MC, y ambos
corren en `hw_init`, despues de la lectura. Asi que el par que se leyo en `sw_init` es un **residuo
previo a la configuracion**, no la configuracion.

Y hay un cuarto detalle que la convierte en hipoteesis con mas fuerza y no solo una mas:

```c
  527  switch (REG_GET_FIELD(tmp, MC_SHARED_CHMAP, NOOFCHAN)) {
  528  case 0:
  529  default:
  530      numchan = 1;
```

El `default` devuelve 1. O sea: **si el driver no sabe interpretar el `NOOFCHAN` que lee, produce 1
canal en vez de un error**, y `1 × 64 = 64` sale plausible y silencioso. Un residuo no
configurado es exactamente el caso en el que un registro no interpretado cae al `default`.

> **NOT_DETERMINED, y con nombre:** cual de las tres Produce el 64. Las tres son compatibles con el
> corpus y **ninguna se puede separar sin leer los dos registros**, que es hardware y ahora esta
> prohibido. Lo que SI queda probado es que el valor no puede ser la configuracion final del
> controlador, porque en el momento de la lectura ese controlador todavia no estaba programado.

## 4. Corroboracion del censo del 1468, y un error mio

`atom_chain.py` con `--self-test` primero: **79 casos, 0 fallos**. Usado despues.

```text
  datos      21 presentes de 35     el 1468 dice 21 de 35     CORROBORADO
  comandos   62 presentes de 81     el 1468 dice 62 de 81     CORROBORADO
  SetEngineClock   0xAD2A           el 1468 dice 0xAD2A        coincide
  SetMemoryClock   0xAED6           el 1468 dice 0xAED6        coincide
```

**Mi error, declarado.** La primera vez que conte los comandos salio **58 de 81** y medi una
contradiccion con el `1468` que no existia. La causa fue mia: indexe la tabla **de comandos** con el
puntero maestro de **datos** (`base+0x20` en vez de `base+0x1E`). El sintoma que lo delata es que
`SetMemoryClock` salio en `0x9B3E`, que es exactamente `VRAM_UsageByFirmware` — indice 11 de
datos. Mismo indice, mismo offset: estaba leyendo la tabla equivocada. Con el puntero correcto:
62. **El `1468` estaba bien y mi comprobacion estaba mal.** Sin este dato el proyecto registra una
contradiccion falsa y la siguiente sesion la persigue.

## 5. Lo que este hallazgo NO abre ni cierra

```text
NO ABRE   cual de numchan=1×64 / 2×32 / residuo produjo el 64.  Requiere leer los registros.
NO ABRE   el ancho real de bus.  Eso lo cerraron 911 y 923: 128 bits, con el ROM como testigo.
NO ABRE   la geometria de VRAM (item 2 de la definicion de cierre).  Es fase 2 y tiene su propia via.
LIMITE    el valor `RAM width 64bits` viene de dmesg, NO de revkit/capturas/.  No hay artefacto
          guardado de esa linea.  Procedencia DADA pero no ARTIFACTO: queda como deuda de custodia.
LIMITE    `MemoryTrainingInfo` ausente (indice 29) es un hecho medido, no una conclusion sobre
          training.  Que el training lo haga el firmware de MC en vez de una tabla del ROM es
          plausible y NO esta probado.  No lo escribo como cerrado.
RIESGO    ninguno.  Cero escrituras, cero sysfs, cero modulos, cero contextos graficos.
```

## 6. Donde queda la parte 1

```text
item 1, identidad de memoria       el ancho REAL ya no es duda: 128 (911/923).  Este hallazgo fija
                                  que el 64 impreso no puede ser la configuracion final.
item 4, orden de inicializacion    ABRIERTO con una cadena probada de 4 pasos, y con el dato de que
                                  el driver no escribe ninguno de los dos registros que lee.
item 2, geometria de VRAM          sin tocar.  Pero ya se ve por donde: ATOM_VRAM_MODULE_V8 declara
                                  usMcRamCfg (NOOFBANK/NOOFRANKS/NOOFROWS/NOOFCOLS) y
                                  ulChannelMapCfg (que el header identifica como mmMC_SHARED_CHREMAP).
                                  Ojo: CHREMAP en el header, CHMAP en la lectura del driver.  Si son
                                  registros distintos, la ruta B lee el equivocado y eso DECIDE el
                                  punto 3.  Es la primera pregunta de la fase 2.
```

## 7. Decision log (§103)

```text
DECISION    publicar el incremento del 923 como hallazgo propio, sin reabrir el 911
WHY         el NOT_DETERMINED estaba declarado y es cerrable por eliminacion con una medicion
            de ROM que no hacia falta hardware
ALTERNATIVA no publicar nada y anotarlo como nota del 923.  Descartada: un cierre con productor
            verificable pertenece a un hallazgo, no a una nota
DISCriminante el indice 30 sale del layout del struct, no de memoria; el offset sale de una
            herramienta con autotest; la guarda de atom.c:1650 cierra la cadena logica
CONSECUENCIA  el 923 puede pasar su mecanismo de NOT_DETERMINED a dos candidatos vivos en vez de
            tres, y queda un discriminante nombrado para cuando se permita hardware
REVERSIBLE  si inseparable, el 1511 cae y el 923 sigue como estaba
```

## 8. La regla que casi me salvo

El `911` se llama *"el vbios dice 128 y el driver informa 64"*. **Era literalmente mi pregunta,
escrita en el titulo, desde hacia tres hallazgos.** No lo lei antes de escribir porque estaba
resuelto y porque las herramientas dan la sensacion de avanzar rapido.

> Un hallazgo cuenta como trabajo solo si **cierra** algo. Añadir un cuarto take sobre un tema ya
> cerrado no es trabajo: es ruido con numero nuevo. Y el numero nuevo hace que el contador suba y
> parezca progreso, que es exactamente lo que hidaba el problema que meoplasteaste.

Regla que queda para esta parte: **antes de reservar numero, `grep` por el tema en
`06-INGENIERIA-INVERSA/findings/`. Si ya hay tres hallazgos sobre el mismo nodo, el trabajo
obligatorio es leer los tres y decir que queda abierto. No repetir la pregunta.**
