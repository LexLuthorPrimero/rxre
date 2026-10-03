# 949 · De 24 mensajes de consulta, el host usa 3, y el del offset de voltaje existe sin usarse

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **El SMC de mi placa tiene un mensaje para consultar el offset de voltaje.
> Está definido en la ABI. Ningún driver de ningún ASIC lo llama nunca.**
>
> Eso convierte mis cuatro `RUNTIME_MISSING` de «irrecuperables porque están en
> registros que reinician la máquina» en **«accesibles por una interfaz que ya
> existe y que el host simplemente no usa»**.

## 1. El inventario, con alcance

```
smu7_ppsmc.h (el de smu7, mi ASIC)   276 PPSMC_MSG definidos
de los cuales son de consulta       24
ficheros .c recorridos en powerplay/ 52
```

Los 24 mensajes de consulta y **su uso real por coincidencia de identificador
exacta**, no de subcadena:

```
PPSMC_MSG_API_GetSclkFrequency    0x200    2 usos   smu7_hwmgr.c
PPSMC_MSG_API_GetMclkFrequency    0x201    2 usos   smu7_hwmgr.c
PPSMC_MSG_GetCurrPkgPwr           0x282    3 usos   smu7_hwmgr.c:2, vega10_hwmgr.c:1
----------------------------------------------------------------------------------
PPSMC_MSG_GetVidOffset_1          0x196    0 usos
PPSMC_MSG_GetVidOffset_2          0x208    0 usos
PPSMC_MSG_API_GetAsicPower        0x204    0 usos
PPSMC_MSG_API_GetSclkBusy         0x202    0 usos
PPSMC_MSG_API_GetMclkBusy         0x203    0 usos
PPSMC_MSG_GetEnabledPsm           0x400    0 usos
PPSMC_MSG_ReadVftCell             0x404    0 usos
PPSMC_MSG_GetData                 0x801    0 usos
PPSMC_MSG_GetUcodeVersion         0x25B    0 usos
PPSMC_MSG_GetTelemetry1Slope      0x266    0 usos
PPSMC_MSG_GetTelemetry1Offset     0x267    0 usos
PPSMC_MSG_GetTelemetry2Slope      0x268    0 usos
PPSMC_MSG_GetTelemetry2Offset     0x269    0 usos
PPSMC_MSG_{M,L,S,UVD,SAMU,ACP,VCE,PCIE}DPM_GetEnabledMask  0x160..0x168   0 usos
```

**3 de 24 los usa el host. 21 no los usa nadie.**

## 2. La respuesta a la pregunta que me hice

Buscaba un mensaje que expusiera `ro`, el voltaje actual, o el offset de clock
stretching aplicado.

```
dato que necesito                         expositor en la ABI de consulta
ro (frecuencia del oscilador de anillo)    NINGUNO.  No existe ningun mensaje
offset de clock stretching aplicado        NINGUNO con ese nombre
voltaje actual                            NINGUNO explicito; el mas proximo es
                                           GetVidOffset_1/2, defined y sin usar
potencia actual                           SI:  GetCurrPkgPwr (0x282), en uso
```

**`ro` no es observable por esta vía, en ninguna forma.** Ninguno de los 24 lo
expone y ninguno lleva un nombre ni una semántica que se le parezca. Eso **no
cambia**: `ro` sigue siendo `RUNTIME_MISSING`, y ahora con un motivo mejor
—«no hay mensaje que lo exponga» en vez de «no sé dónde mirar».

**Pero el offset de voltaje sí tiene su mensaje, y está muerto:**

```
smu7_ppsmc.h:324-325   PPSMC_MSG_GetVidOffset_1   0x196
                        PPSMC_MSG_GetVidOffset_2   0x208
```

Y no es un mensaje de una generación: **existe con los mismos dos códigos en
tres generaciones de SMC** —smu7, tonga y fiji—, y **ninguna lo llama**.

**Eso es un hecho de arquitectura, y es accionable.** Para un driver propio, la
interfaz que expondría el offset de voltaje al host **ya está implementada en el
firmware del SMC de mi placa**. No hace falta hardware nuevo, no hace falta risky
registros, y no hace falta que exista. Solo hace falta que alguien pregunte.

## 3. El unico camino vivo, y por que importa mas de lo que parece

```
smu7_hwmgr.c:4053-4064
    /* PPSMC_MSG_GetCurrPkgPwr is not supported on:
     *  - Hawaii
     *  - Bonaire
     *  - Fiji
     *  - Tonga
     */
    if ((adev->asic_type != CHIP_HAWAII) &&
        (adev->asic_type != CHIP_BONAIRE) &&
        (adev->asic_type != CHIP_FIJI) &&
        (adev->asic_type != CHIP_TONGA)) {
            smum_send_msg_to_smc_with_parameter(hwmgr, PPSMC_MSG_GetCurrPkgPwr, 0, &tmp);
```

**POLARIS12 no esta en la lista de exclusion, luego el mensaje se envia en mi
placa.** Y `smu7_hwmgr.c` lo usa dos veces.

Eso demuestra **tres cosas a la vez**, y las tres son las que `946` dejo abiertas:

1. **La via de mensajes al SMC funciona en mi ASIC.** Es la misma via que produjo
   `PSTATE_SCLK = 214 MHz` en `amdgpu_pm_info.txt`, que corrobora `945`.
2. **La lectura de potencia instantanea es posible por mensaje**, no por registro.
   Y la potencia sostenida es **exactamente** la variable que toda esta linea
   identifica como el techo del rendimiento.
3. **La lista de ASIC excluidos es una lista de la epoca, no de mi placa.** El
   criterio real de seleccion es la version del SMC, no el nombre del ASIC, y
   por eso un nombre propio no basta para decidir si un mensaje funciona aqui.

**Y esa tercera es la que hay que retener: durante seis hallazgos he viene
respondiendo «¿esto corre en mi ASIC?» mirando el nombre del ASIC, y este
comentario demuestra que ese no es siempre el criterio.**

## 4. Lo que queda de la pregunta original

```
ro                                       NOT_FOUND con ambito
                                         24 mensajes de consulta, 52 .c, smu7_ppsmc.h
                                         ninguno lo expone, y no hay otro nombre
voltaje actual                           CANDIDATO: GetVidOffset_1/2 (0x196, 0x208)
                                         definido en 3 generaciones, nunca invocado
offset de CKS aplicado                   NOT_FOUND con ambito
potencia instantanea                     PROVEN que hay via viva: GetCurrPkgPwr
                                         excluye HAWAII/BONAIRE/FIJI/TONGA,
                                         POLARIS12 no esta excluido
```

**Y una conclusion de metodo que me cuesta mas que el resultado:** la pregunta
que me hice —«¿hay un mensaje que exponga `ro`?»— era una pregunta sobre el
**nombre** de los mensajes. Un mensaje que exponiera `ro` sin llamarse `ro`
habria pasado desapercibido, igual que un campo que se llamara asi y no lo
expusiera. **La busqueda por nombre y la busqueda por semantica no son la misma
busqueda**, y solo la segunda responde a la pregunta. En este corpus, la segunda
requiere el firmware, que no tengo: **por eso el resultado es `NOT_FOUND` con
ambito y no `PROVEN_ABSENT`.**

## 5. Errores de esta iteracion

**1. Mi primer bucle de conteo se contradijo a si mismo**: imprimio
`NO LO USA (2)` en la misma linea. Era un fallo de etiquetado en el script de
shell, no de los datos, pero **un contador que no puede estar de acuerdo consigo
mismo no se puede reportar**: si la salida es coherente ya no significa nada. Lo
reehice en Python con coincidencia de identificador exacta y volvi a validar.

**2.** Busque los mensajes con el patron `_Get` y perdi los `API_GetSclkFrequency`
y `API_GetMclkFrequency`, que son precisamente los dos que si se usan. **Un
patron demasiado estrecho produce el mismo `0` que una busqueda en el fichero
equivocado**, y por eso el `0` inicial de `smu7.h` no significaba nada: el
fichero estaba mal elegido, no vacio.

**3.** Di por hecho que `GetCurrPkgPwr` devolveria una unidad que yo reconozco, y
estuve a punto de escribir «watts» porque lo leo en el nombre. **El nombre de un
mensaje no es su unidad**, igual que el nombre de un campo no es su unidad. Lo
dejo sin unidad, `SEMANTIC_MISSING`.

## 6. Frontier siguiente

```
1.  24 mensajes de consulta, 52 .c, smu7_ppsmc.h          PROVEN (alcance)
2.  el host usa 3: Sclk, Mclk, CurrPkgPwr                   PROVEN
3.  21 no los usa nadie, incluidos 2 de voltaje             PROVEN
4.  GetVidOffset_1/2 (0x196, 0x208) en smu7+tonga+fiji,
    nunca invocados                                          PROVEN
5.  ningun mensaje expone ro                                 NOT_FOUND con ambito
6.  GetCurrPkgPwr excluye H/B/F/T, POLARIS12 no:
    el mensaje se envia en mi placa                           PROVEN
7.  la via de mensajes al SMC funciona en mi ASIC             PROVEN (via 945)
8.  la unidad de GetCurrPkgPwr                                SEMANTIC_MISSING
```

**El frente util ya no es el `RUNTIME_MISSING`: es un dato que el host ya tiene y
yo no he mirado.** `amdgpu_pm_info.txt` dio `5.157 W (current SoC)` — y ese
numero lo produce `GetCurrPkgPwr` por la via de mensajes. **La lectura de
potencia de mi placa ya esta hecha y guardada en un fichero de 1731 bytes que
llevo siete hallazgos sin abrir.**

Y con el tense de `PSTATE_SCLK` y el consumo, la captura puede ya decirme si mi
nivel de reposo es el que el VBIOS propone. Son dos numeros en un fichero que
existe, y responderian la pregunta de «¿que margen compra el clock stretching en mi
placa?» por el lado del consumo, que es el unico lado que todavia no tengo.

Criterio de cierre: el consumo y la temperatura en los estados de reposo de
`amdgpu_pm_info.txt` contrastados con lo que el VBIOS predice para el nivel 0
—`vddInd = 0`, sin clock stretching, `usFanGainEdge = 100`— y si el consumo
observado es coherente con el voltaje minimo del nivel o revela que la placa esta
mas alla del reposo en VBIOS.
