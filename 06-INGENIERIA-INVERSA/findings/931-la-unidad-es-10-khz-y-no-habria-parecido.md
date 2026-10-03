# 931 · La unidad de `clk` es 10 kHz, y el umbral de `ro` por nivel

> ## CORRECCION — este hallazgo contiene numeros INVALIDADOS. Ver `957`.
>
> La lectura de las formulas de `polaris10_smumgr.c:1680-1683` fue **erronea**:
> los grupos parentizados son **divisiones**, no restas. La linea esta cortada por
> `cut -c1-104` justo donde esta el `/` y la continuacion `\`.
>
> Lo que **NO** se sostiene: `ro_minimo` por nivel (200,165,137,79,73,66,57,48) y la idea de que sea un umbral alcanzable.
>
> Lo que **si** se sostiene y no depende de esa lectura: la unidad de `clk` = 10 kHz leida de la cadena de formato del kernel; los ocho niveles 214..1071 MHz; clock stretching activo en 7 de 8; `cks_voffset` = 0 en todos.
>
> **El texto de abajo se conserva integro**, a proposito: es la v1, y el
> mecanismo del error es evidencia.


WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **Los ocho niveles de SCLK de mi placa, en MHz reales: de 214 a 1071.**
> La unidad no la supuse: la leí de la cadena de formato del propio kernel.
>
> Y con ella, el dato que decide el rendimiento sostenido: **el valor de `ro` a
> partir del cual el clock stretching compensa**, uno por nivel. Va de **200** en
> el nivel más bajo a **48** en el más alto, y **el VBIOS desactiva el clock
> stretching justo en el nivel donde el umbral es inalcanzable.**

## 1. El anclaje: la unidad estaba escrita en el kernel

Buscaba un discriminante independiente de mi hipótesis de "10 kHz". Lo encontré sin
salir del corpus, y no es una convención: es una cadena de formato.

```c
smu7_hwmgr.c:5082-5086
    for (i = 0; i < sclk_table->count; i++)
        size += sysfs_emit_at(buf, size, "%d: %uMhz %s\n", i,
                              sclk_table->dpm_levels[i].value / 100,
                              (i == now) ? "*" : "");
```

El kernel **divide por 100 y etiqueta el resultado `Mhz`**. Por tanto
`dpm_levels[i].value` está en unidades de **10 kHz**. No hay ambigüedad posible:
es una división y una etiqueta en la misma expresión.

**Y ese `value` es la misma magnitud que `entries[i].clk` de mi tabla.** La cadena
es corta y no tiene ningún paso supuesto:

```
amdgpu_pm.c:1079           amdgpu_get_pp_dpm_clock(dev, PP_SCLK, buf)
amd_powerplay.c:711-724    pp_dpm_emit_clock_levels -> hwmgr_func->emit_clock_levels
smu7_hwmgr.c:5056-5086     smu7_emit_clock_levels  -> value / 100  ==  MHz
polaris10_smumgr.c:976     polaris10_get_dependency_volt_by_clk(hwmgr, vdd_dep_table, clock, ...)
polaris10_smumgr.c:369     if (dep_table->entries[i].clk >= clock)
```

`:369` compara `entries[i].clk` contra **el mismo `clock`** que llega desde el
nivel DPM. Es literalmente el mismo valor que el kernel etiqueta como MHz tras
dividir por 100. **PROVEN.**

## 2. Los ocho niveles

```
rec  clk(raw)     MHz   vddInd   cks_enable
  0      21400    214        0        0
  1      55100    551        2        1
  2      73400    734        2        1
  3      98000    980        5        1
  4     100000   1000        6        1
  5     102000   1020        7        1
  6     104600   1046        8        1
  7     107100   1071        9        1
```

**1071 MHz es el reloj de impulso de fábrica de muchas RX 550.** El rango
214-1071 MHz es el esperado para Polaris12. La lectura está corroborada por el
dominio **y** por la etiqueta del kernel.

Y **`vddInd = 0` en el nivel 0**, el índice de voltaje más bajo, mientras que los
siete restantes van 2,2,5,6,7,8,9. El nivel 0 es el estado de más bajo voltaje
**y** el más bajo reloj: **los dos a la vez.**

## 3. El umbral de `ro`: el número que faltaba

`volt_with_cks` depende de `ro`, que es runtime. Pero **`ro` aparece solo
linealmente**, así que puedo despejar el valor exacto a partir del cual el clock
stretching empieza a compensar, y eso no necesita conocer `ro`:

```c
volt_without_cks = 2416794800U + (clk/100)*1476925/10 - (2625416 - (clk/100)*1258)
volt_with_cks    = 2999656000U - (clk/100)*392803 - (ro - 44) * (3422454 - (clk/100)*1888)

condicion del driver:  volt_without_cks >= volt_with_cks
```

Los dos lados comparten unidad, así que **despejando:**

```
rec     MHz   volt_sin_cks   volt_con_cks(44)   d(volt)/d(ro)   ro_minimo
  0      214     2446044791         2915596158          3018422        200
  1      551     2496241109         2783221547          2382166        165
  2      734     2523499051         2711338598          2036662        137
  3      980     2560140874         2614709060          1572214         79
  4     1000     2563119884         2606853000          1534454         73
  5     1020     2566098894         2598996940          1496694         66
  6     1046     2569971607         2588784062          1447606         57
  7     1071     2573695369         2578963987          1400406         48
```

Comprobado con aritmética entera de 32 bits sin signo y el mismo orden de
precedencia que el fuente. Los valores van de 2.44e9 a 2.57e9, todos por debajo
de 4.29e9: **no hay desbordamiento**, la aritmética de `uint32_t` no distorsiona
el resultado.

## 4. La corroboración que importa

**El umbral cae monótonamente con la frecuencia**: 200, 165, 137, 79, 73, 66, 57,
48. Cuanto más alto el reloj, menos `ro` hace falta para que el clock stretching
sea rentable. Es lo esperable: a más carga, más[currentes] hay que recortar y más
margen aporta estirar el reloj.

**Y el nivel 0 exige `ro >= 200`, mientras que el VBIOS pone `cks_enable = 0`
justo ahí.** El umbral del nivel más bajo es alcanzable sólo con un silicio
atípico, y el VBIOS de esta placa lo sabe: **lo desactiva.**

Esto es una **corroboración cruzada entre dos fuentes independientes**: los datos
del VBIOS en `0x9D15` y las constantes del driver en `polaris10_smumgr.c`. No son
un eco la una de la otra — el VBIOS no contiene esas constantes, y el driver no
contiene los valores del VBIOS. **Los dos coinciden en que el clock stretching es
inútil en el estado de reposo.** Ese es el resultado, y es una validación
mutua de los dos caminos.

## 5. Por qué esto conecta con el ventilador

`907` midió que el driver **no** logra entregar al SMC los 96 bytes de
`pp_advance_fan_control_parameters`: copia 8, el tamaño de un puntero.

Ahora se ve el mecanismo por el que ese defecto se paga:

- **En reposo** la placa está en el nivel 0: 214 MHz, `vddInd = 0`, sin clock
  stretching. Es el estado más frío y más barato, y **no necesita ventilador**.
- **Al despertar** salta a uno de los siete niveles con stretching, de 551 a
  1071 MHz, y ahí es donde el calor se genera y **donde el ventilador tiene que
  actuar**.
- El driver **escribe** el voltage offset de esos niveles —el `Sclk_voltageOffset`
  sí llega al SMC — pero **no** los parámetros de ventilador.

Es decir: **la ruta de tensión está completa, la de refrigeración está rota.** La
placa puede correctamente bajar voltaje antes de subir reloj, y al hacerlo subir
por debajo de laxrefa que el driver pretendía, porque el ventilador no está bajo
su control. El clock stretching es el mecanismo que compra margen térmico; **el
margen existe, pero el ventilador que lo aprovecha no lo dirige el driver.**

Y para un driver propio esto es una lección de arquitectura, no un detalle: **la
tabla de tensión y la de ventilador son rutas independientes que llegan a campos
distintos del mismo `smc_state_table`, y una puede estar bien mientras la otra
está rota sin que nada lo indique.**

## 6. Qué sigue sin determinarse

```
1.  el valor real de ro: RUNTIME_MISSING (efusiva del ASIC).
    ro = ((efuse * (ro_range_max - ro_range_min)) / 255) + ro_range_min
    y ro_range_max/min tambien salen de la efusiva, en smu7_calculate_ro_range.
2.  la unidad de volt_without_cks / volt_with_cks: SEMANTIC_MISSING.
    No la necesito para el umbral, porque ambos lados la comparten.
3.  que nivel DPM corresponde a cada nivel de esta tabla: NOT_DETERMINED.
    No hay correspondencia uno a uno escrita en el corpus, y las dos tablas
    tienen perfiles distintos: esta es 214/551/734/980/1000/1020/1046/1071 y
    la tabla AVFS de :80 va en codificacion fraccionaria con paso constante
    0x1027. Son escalas distintas y no las debo fusionar.
```

El punto 3 es una tentación que evito: **parecen la misma cosa y no lo son.** La
tabla de dependencia SCLK y la tabla de niveles DPM sirven para propositos
distintos y tienen codificaciones distintas. Unirlas por parecido numerico seria
exactamente el tipo de cierre falso que `929` §2 evita.

## 7. Errores de esta iteración

**1. Casi concluyo `NOT_DETERMINED` por la vía corta.** Segui la cadena de
`entries[i].clk` -> `clock` -> niveles DPM -> VBIOS, y como el VBIOS no trae
ninguna frecuencia en kHz, parecia que no habia anclaje absoluto. **Lo habia, en
la ruta que no estaba mirando**: el kernel renderiza esos mismos niveles a sysfs
dividiendo por 100 y etiquetando `Mhz`. **El anclaje no estaba en los datos de
entrada, estaba en la presentacion de salida.**

Es la version de `TRUNCATION_AS_ABSENCE` para unidades: **no encontrar una escala
en los datos no significa que la escala no exista.**

**2.** Perdi cuatro llamadas a `grep` buscando `amdgpu_power.c` en un directorio
donde no esta, y luego `pp_dpm_sclk_show`, que ya no existe con ese nombre. La
interfaz de sysfs legacy **se movio** en este kernel: ahora vive en
`pm/amdgpu_pm.c` con el prefijo `amdgpu_`. **Un nombre que no aparece no prueba
que la capacidad no exista.** Si me hubiera parado en el primer `0`, habria
concluido que no hay interfaz de reloj exposed, que es falso.

**3.** Verifique que el arbol estaba completo antes de concluir la ausencia de
`amdgpu_power.c` (103617 ficheros, Kconfig y Makefile presentes, 304 `.c` en
`amdgpu/`). Sin ese control, "no existe" habria sido una conjetura sobre un
checkout parcial. Y la ausencia **si** es real: el fichero se elimino.

## 8. Frontier siguiente

**Cerrada la linea SCLK por completo.** Con esta medicion queda:

```
1.  8 niveles: 214, 551, 734, 980, 1000, 1020, 1046, 1071 MHz   PROVEN
2.  unidad = 10 kHz, del propio kernel, no supuesta               PROVEN
3.  clock stretching activo en 7 de 8; desactivado en el 0       PROVEN
4.  ro_minimo por nivel: 200,165,137,79,73,66,57,48              PROVEN
5.  el VBIOS desactiva CKS donde el umbral es inalcanzable       CORROBORADO
6.  nivel 0 = reposo: menor reloj Y menor voltaje a la vez       CORROBORADO
7.  ro real = RUNTIME_MISSING; unidad de volt = SEMANTIC_MISSING
```

**La conexion con el ventilador es ahora mecanica, no analogica**, y eso deja un
frente nuevo y concreto: **los 96 bytes que `907` demostro que no llegan.** Ya se
sabe que el driver escribe 8 bytes de un puntero donde el firmware espera 96, y ya
se sabe que el clock stretching compra el margen termico que esos 96 bytes
deberian: en mi placa el margen existe pero no lo aplica quien deberia.

El frente util es la direccion: **mirar que hay al otro lado de ese campo en el
SMC**, es decir, si esos 96 bytes son leidos por firmware SMC o por un SMC externo,
y si hay en el corpus alguna lectura de esa zona. Eso es estatico.

Criterio de cierre: identificar el consumidor de los 96 bytes en el corpus, o
`NOT_FOUND` con el ambito exacto de la busqueda y el motivo por el que no puede
existir.
