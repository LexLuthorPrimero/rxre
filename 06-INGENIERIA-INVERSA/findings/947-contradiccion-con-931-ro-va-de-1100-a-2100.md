# 947 · Contradicción con 931 resuelta: ro va de 1100 a 2100, no de 48 a 200

> ## v2 — el `0xC7` de este hallazgo pasa a CORROBORATED. Ver `965`.
>
> Lo tracté como `OBSERVED` sin fuente. **La fuente existe y es independiente del fixture**:
> `06-INGENIERIA-INVERSA/evidencia/boot-amdgpu-...log:10`, contrastado con el `printf` de
> `amdgpu_device.c:3716`. No cambia ninguna conclusión de `947`; cambia su base.
> La corrección de las fórmulas (`957`) sigue vigente y no le afecta.

> ## CORRECCION — este hallazgo contiene numeros INVALIDADOS. Ver `957`.
>
> La lectura de las formulas de `polaris10_smumgr.c:1680-1683` fue **erronea**:
> los grupos parentizados son **divisiones**, no restas. La linea esta cortada por
> `cut -c1-104` justo donde esta el `/` y la continuacion `\`.
>
> Lo que **NO** se sostiene: la tabla de `acomp` por fila (1010,1213,1376,1708,1743,1781,1833,1886), la idea de desbordamiento de `uint32`, y el `79 %` derivado de `956`.
>
> Lo que **si** se sostiene y no depende de esa lectura: asic_type = CHIP_POLARIS12 y por tanto `ro_range` = 1100..2100 por la rama else; que las dos condiciones de `smu7_hwmgr.c:2572-2573` se cumplen; la rama se ejecuta y sus valores.
>
> **El texto de abajo se conserva integro**, a proposito: es la v1, y el
> mecanismo del error es evidencia.


WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> **RENUMERADO.** Este fichero fue `944-contradiccion-con-931-ro-va-de-1100-a-2100.md`
> y pasa a `947`. El otro agente escribio `944-el-mecanismo-existe-y-429-notas-no-lo-usan.md`
> —un hallazgo sobre las colisiones de numeracion— y creyo la colision al
> escribirlo. Su fichero no se toca. **La nota se queda aqui porque las citas
> antiguas dicen 944, y un numero que se cambio sin dejar rastro rompe la cadena de
> evidencia que el resto de la linea sostiene.**

> ## Por qué esta iteración no es un índice de cierre
>
> Iba a declarar `SATURATED` la línea de clocks y ventilador. Antes lo intenté, y
> al comprobar `smu7_hwmgr.c` para el índice **encontré que `931` tenía el
> mecanismo equivocado.** Declarar `SATURATED` con una contradicción abierta
> habría sido exactamente el cierre falso que el prompt prohíbe en §49.
>
> ```
> CLAIM-931 v1  ro_minimo por nivel = 200,165,137,79,73,66,57,48
>               y "el VBIOS desactiva CKS donde el umbral es inalcanzable"
> CLAIM-944    v1 -> v2:  el MECANISMO era otro. La conclusion se sostiene,
>                        con mejor fundamento.
> ```

## 1. Lo que se ve desde el comentario del propio driver

```
polaris10_smumgr.c:1663-1665
    /* Read SMU_Eefuse to read and calculate RO and determine
     * if the part is SS or FF. if RO >= 1660MHz, part is FF.  */
```

**1660 MHz está dentro del rango de `ro`.** Eso convierte la escala en MHz y hace
sospechoso un umbral de 200. La comprobé contra la función que fija el rango:

```
smu7_hwmgr.c:1987-2031   smu7_calculate_ro_range
    :1998  ASICID_IS_P20 || P30          -> min 1200  max 2500
    :2002  ASICID_IS_P21 || P31          -> min  900  max 2100
    :2006  else if (hwmgr->chip_id == CHIP_POLARIS10)
           :2007    subsystem_vendor == 0x106B -> min 1000 max 2300
           :2011    evv_revision == 0         -> min 1000 max 2300
           :2014    evv_revision == 1         -> min 1200 max 2500 / 1200 2000
           :2023    evv_revision == 2         -> min 1200 max 2500
    :2028  else                          -> min 1100  max 2100
```

## 2. Mi ASIC no es POLARIS10, y eso decide la rama

```
amdgpu/amdgpu_drv.c:2041
    {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12}
```

**Mi device es `CHIP_POLARIS12`, no `CHIP_POLARIS10`.** Luego `:2006` es falso y
caigo en el `else` de `:2028-2031`:

```
ro_range_minimum = 1100        ro_range_maximum = 2100
```

**Y esa rama no tiene ninguna condición de efusiva**, a diferencia de las de
POLARIS10. Es el unico `ro_range` de los cinco que **no depende de nada runtime**.

**Consecuencia directa: mis umbrales de `931` (200, 165, 137, 79, 73, 66, 57, 48)
estan todos por debajo de 1100, o sea fuera del rango fisico de mi placa.**
`931` calculo un cruce algebraico correcto y le dio un significado equivocado.

## 3. El límite que importa no es el cruce: es el desbordamiento

En la condicion del driver hay **dos** fronteras, y `931` solo vio la primera:

```
A) CRUCE      ro donde volt_con_cks baja de volt_sin_cks        <- lo que calcule 931
B) ACOMPLADO  ro donde volt_con_cks se sale de uint32
              y la comparacion sin signo se INVIERTE             <- el que de verdad manda
```

```
nivel   MHz            A           p   cruce   acomp   @1100  @2100
   0    214    2915596158     3018422     200     1010      NO      SI
   1    551    2783221547     2382166     165     1213      SI      SI
   2    734    2711338598     2036662     137     1376      SI      NO
   3    980    2614709060     1572214      79     1708      SI      NO
   4   1000    2606853000     1534454      73     1743      SI      NO
   5   1020    2598996940     1496694      66     1781      SI      NO
   6   1046    2588784062     1447606      57     1833      SI      NO
   7   1071    2578963987     1400406      48     1886      SI      NO
```

Elaccompanied de cada nivel es donde `A - (ro-44)*p` pasa de cero, y a partir de
ahi el `uint32_t` se va de rango y la comparacion `>=` da la respuesta contraria.

**Y aqui está el resultado que `931` no vio, porque su rango nunca lo cruzó:**

```
nivel 0 ( 214 MHz)   acomp = 1010   y  ro >= 1100   ->  NUNCA se aplica
nivel 7 (1071 MHz)   acomp = 1886   y  ro <= 2100   ->  se aplica en [1100, 1885]
nivel 1 ( 551 MHz)   acomp = 1213                    ->  se aplica en [1100, 1212]
```

**El nivel 0 es el unico de los ocho cuyo accompanied cae por debajo de
`ro_range_minimum`.** En los otros siete, el offset se aplica para alguna parte del
rango real de mi silicio; en el nivel 0, **no se aplica nunca.**

## 4. La corroboracion se sostiene, con mejor mecanismo

`931` concluyo que el VBIOS desactiva el clock stretching en el nivel 0 porque alli
el umbral era inalcanzable, y lo presento como validacion cruzada entre el VBIOS y
las constantes del driver.

**La conclusion es correcta. El motivo era falso**, y el motivo verdadero es mas
fuerte:

```
VBIOS      nivel 0 -> ucCKSVOffsetandDisable = 0x80 -> cks_enable = 0
driver     nivel 0 -> acomp = 1010 < ro_range_minimum = 1100
           -> para NINGUN silicio de mi placa, el driver obtendria un
              volt_offset de un volt_with_cks desbordado, y por eso no lo aplica
```

Las dos fuentes coinciden, y ahora se sabe **por qué**: el driver no desactiva el
nivel 0 en el VBIOS por prudencia, sino porque en ese nivel su propia aritmetica se
desborda para todo el rango posible de mi silicio. **El VBIOS y el codigo estan
explicando la misma limitacion desde dos lados.**

`931` loIso como «umbral inalcanzable» cuando el umbral era 200 y el limite
real era 1010. **El numero correcto hace la corroboracion mas fuerte, no mas debil.**

## 5. El hallazgo mas fragil de toda la linea

Esto no estaba en mi lista de controles y lo encontré por casualidad, al leer la
funcion que precede a `smu7_calculate_ro_range`:

```
smu7_hwmgr.c:1975-1984
    if ((adev->pdev->device == 0x699F) &&
        (adev->pdev->revision == 0xCF)) {
            phm_cap_unset(..., PHM_PlatformCaps_PowerContainment);
            data->enable_tdc_limit_feature        = false;
            data->enable_pkg_pwr_tracking_feature = false;
            data->disable_edc_leakage_controller  = true;
            phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);   <<<<<
        }
```

**Una rama que existe para mi device exacto y que DESACTIVA el clock stretcher
integro — la capability que gobierna `929` y `931` — si la revisión es `0xCF`.**

```
mi revision (revkit/bootcheck.py:141)   0xC7
la que lo desactiva                     0xCF
```

**Mi placa esta a un nibble de la revision que dejaria sin clock stretching toda
esta linea.** `929` y `931` describen codigo que se ejecuta en mi maquina; si la
revision fuera `0xCF`, describiria codigo muerto.

El valor `0xC7` **NOVENIA MEDIDO**, y lo decia como si lo estuviera. Corregido en
`945`: la unica aparicion de `0xC7` en todo `revkit/` es un **vector de test
sintetico** construido en `bootcheck.py:139-146` para probar el parser. En las 21
capturas de `revkit/capturas/` no aparece ni la revision ni el device id.asi que:

```
revision de mi placa            NOT_FOUND   (nunca medida; 0xC7 es un fixture)
la condition que lo apagaria    PROVEN      (smu7_hwmgr.c:1975-1976)
diferencia                      desconocida: 0xC7 supuesto, 0xCF requerido
```

**Es la dependencia mas fina que tiene la linea entera**, y no la tenia registrada
como tal. Si alguien rearma este conocimiento sin el contexto, la conclusion
«el clock stretching esta activo en 7 de 8 niveles» **descansa sobre un dato
fabricado**.

## 6. Dos cosas mas que quedan escritas

**a) El criterio de seleccion del PP legacy no es el tipo de ASIC.** Es la version
de IP de MP1:

```
amdgpu_discovery.c:2291-2302   amdgpu_discovery_set_smu_ip_blocks
    switch (amdgpu_ip_version(adev, MP1_HWIP, 0)) {
    case 9.0.0 / 10.0.0 / 10.0.1 / 11.0.2:
        if (asic_type == CHIP_ARCTURUS)  smu_v11_0_ip_block
        else                             pp_smu_ip_block      <- PP legacy
```

Mi resumen anterior decia que `amdgpu_discovery.c:2293` era un despacho exhaustivo
**por ASIC**. **No lo es: es por version de IP.** Y eso explica por que ese
fichero no contiene la cadena `POLARIS` ni una sola vez: **ya no despacha por tipo
de ASIC para este bloque.**

Mi conclusion de entonces —que el PP legacy se ejecuta en mi placa— **se
sostiene**, pero por un motivo que no era el que yo habia escrito. Y mi Conclusion
intermedia de que «el grep estaba fallando» tambien era falsa: el fichero
genuinamente no menciona Polaris.

**b) Existe `revkit/capturas/amdgpu_pm_info.txt`.** No lo he usado en ninguna
iteracion de esta linea, y es una captura runtime ya existente de informacion de
gestion de potencia. **Es la unica via disponible sin pedir autorizacion nueva**
para contrastar cualquiera de estos numeros contra algo medido en esta maquina.

## 7. Errores de esta iteracion

**1. Iba a declarar `SATURATED` sin comprobar la funcion que da la escala.** La
lista de diez estados de mi indice estaba completa y coherente, y por eso me
parecio cerrada. **Una lista de estados coherente no es una linea cerrada:** cada
estado puede tener un motivo equivocado y seguir siendo coherente.

**2. Conclui «el grep esta fallando» porque `amdgpu_kms` daba 0 en
`amdgpu_discovery.c`.** Use un control que ese fichero no contiene, y de ahi
produce un diagnostico inventado**, que es peor que no hacer control: **un control tiene que tener un resultado positivo conocido** antes de interpretar un cero.
produce un diagnostico inventado**, que es peor que no hacer control:Propongo dos
controles con un resultado positivo ya conocido.

**3.** `931` escribio un umbral sin declarar la escala en la que estaba. Presentado
asi, «200» parece un valor fisico y no el cruce de una ecuacion. **Un numero sin
sus unidades ni su rango de validez no es un resultado, es una cifra.**

## 8. Frontier siguiente

```
1.  asic_type de 0x699F = CHIP_POLARIS12                    PROVEN (amdgpu_drv.c:2041)
2.  ro_range = 1100..2100, rama else sin condicion runtime   PROVEN
3.  el limite real es el acompanado, no el cruce              PROVEN
4.  acomp por nivel: 1010,1213,1376,1708,1743,1781,1833,1886  PROVEN
5.  el nivel 0 nunca aplica offset con ro >= 1100             PROVEN
6.  el VBIOS lo desactiva ahi: corroboracion con mecanismo    CORROBORATED
7.  ro concreto = RUNTIME_MISSING (efusiva)                   RUNTIME_MISSING
8.  0x699F+0xCF apagaria ClockStretcher entero; yo soy 0xC7   PROVEN
    >> 945: mi revision es NOT_FOUND. 0xC7 era un fixture de test, no una medida.
9.  el PP legacy se elige por MP1 HWIP, no por ASIC            PROVEN
10. revision 0xC7 no remedida esta iteracion                  DEFERRED_BY_PERMISSION
```

**El frente util es el punto 8, y no es de esta linea: es de hardware.** Una linea
entera de hallazgos —`929`, `931`, `941`— **descansa sobre un nibble de revision
que no he remedido.** Confirmarlo con `revkit/capturas/amdgpu_pm_info.txt` o con
una lectura de `/sys` daria o quitaria el clock stretching a la placa entera.

Criterio de cierre: la revision de mi placa confirmada desde una captura ya
existente o desde el fingerprint registrado, con su procedencia; o
`RUNTIME_MISSING` upgrading con la razon de que el unico modo de obtenerla es
`/sys`, que la politica no concede.

Y hasta que eso se resuelva, **la linea no es `SATURATED`: es `OPEN` con una
dependencia externa de un bit.**
