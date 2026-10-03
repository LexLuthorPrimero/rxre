# 926 · El driver sobrescribe AVFS con los mismos valores que ya trae el VBIOS

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## CORREGIDO POR `925` — mi veredicto central era falso
>
> Escribí que `a0..a2` **no son coeficientes de una curva**. **Son exactamente
> eso**: van a `BTCGB_VDROOP_TABLE[1].a0..a2` por copia directa, sin convertir, y
> el nombre del campo destino es el del origen.
>
> | afirmacion de `923` | estado real |
> |---|---|
> | «no son coeficientes de una curva» | **`REFUTED`** |
> | «tampoco son offsets al ROM» | **`CORROBORATED`** |
> | «son parametros opacos, unidad desconocida» | la unidad exacta sigue sin estar; la **forma** si |
>
> El error fue comparar `a0` con `AConstant[0..2]`, que son coeficientes de **otra
> curva**: la de media/sigma, que `Platform_sigma = 0` deja inactiva. `a0` es el de
> la curva VDROOP, que es la que manda.
>
> Y el discriminante que hacia falta no estaba en los numeros sino en comparar las
> dos curvas entre si: `m2` coincide al 0.1 % entre CKSON y CKSOFF, y vienen de
> fuentes independientes.


> ## Resultado
>
> `a0..a2` queda **decidido**, y además **corrijo a `922`**, que se equivocó en
> una cosa y por el camino hallé una coincidencia.
>
> **Los tres NO son coeficientes de una curva.** Y para mi placa el driver
> **reescribe `ulGB_VDROOP_TABLE_CKSOFF_a0..a2` con exactamente los mismos
> valores que yo leí del VBIOS**, así que la sobrescritura es un **no-op**.
>
> Y el driver **fuerza `ucEnableApplyAVFS_CKS_OFF_Voltage = 1`**, con lo que la
> conclusión de `922` de que «mi placa no aplica AVFS con CKS off» **es
> incorrecta**.

## 1. Los macros, evaluados para mi ASIC

```c
amdgpu/amdgpu.h:742
#define ASICID_IS_P20(did, rid)  (((did == 0x67DF) && ...) ||
                                  ((did == 0x6FDF) && ...))
#define ASICID_IS_P21(did, rid)  (((did == 0x67EF) && ...) ||
                                  ((did == 0x67FF) && ...))
#define ASICID_IS_P23(did, rid)  (((did == 0x6987) && ...) ||
                                  ((did == 0x6981) && ...))
```

Con `did = 0x699F`, `rid = 0xC7`:

| macro | exige | veredicto |
|---|---|---|
| `ASICID_IS_P20` | `0x67DF` o `0x6FDF` | **`FALSE`** |
| `ASICID_IS_P21` | `0x67EF` o `0x67FF` | **`FALSE`** |
| `ASICID_IS_P23` | `0x6987` o `0x6981` | **`FALSE`** |

**`0x699F` no aparece en ninguno de los tres.** Buscado en `amd/` completo
(2689 ficheros, `exit=0`): 3 definiciones, **0 ocurrencias de `0x699F`**.

## 2. Qué hace el driver entonces

```
:1800   if (IS_P20 ||                                   ->  FALSE
:1801       ((chip_id == CHIP_POLARIS12) && !IS_P23) || ->  TRUE  && TRUE  = TRUE
:1802       IS_P21) {                                  ->  FALSE
:1803       avfs_params.ucEnableApplyAVFS_CKS_OFF_Voltage = 1;    SE EJECUTA

:1819   } else if (chip_id == CHIP_POLARIS12 && !IS_P23(...)) {   TRUE
:1820       a0 = 0xF6B024DD;  a1 = 0x3005E;  a2 = 0x18A5F;        SE EJECUTA
:1823       m1 = 0x315;  m2 = 0xFED1;  b = 0x3B;                  SE EJECUTA
```

Solo la rama `:1819` aplica. La `:1806` exige `0x67EF rev 0xE5` o `0x67FF rev
0xEF`, y la `:1826` es `IS_P20`. Ninguna es mía.

## 3. La coincidencia, y lo que significa

```
leído del VBIOS en 0xA6E4     a0=0xF6B024DD   a1=0x3005E   a2=0x18A5F
driver, rama POLARIS12 :1820  a0=0xF6B024DD   a1=0x3005E   a2=0x18A5F
```

**Idénticos los tres.** No es que «encajen»: son los mismos números, en mayúsculas
y minúsculas.

Eso no es casualidad de mi medición, y se explica de una manera limpia: **este
VBIOS se generó con las constantes de la propia ruta de reserva de AMD para
Polaris12.** El driver las pone como red de seguridad por si el VBIOS no las trae;
este VBIOS ya las trae.

## 4. El veredicto sobre `a0..a2`

**No son tres coeficientes de una curva de dropout.** `a0 = 0xF6B024DD` es
incompatible con un coeficiente: los coeficientes de la misma familia, en
`Aconstant[0..2]`, valen 279, 1186 y 446, tres órdenes de magnitud por debajo.

**Tampoco son offsets al ROM**, aunque es tentador decirlo porque
`a1 = 0x3005E` y `a2 = 0x18A5F` caen dentro de los 58880 bytes. La tentación no
sostiene: **el driver no los usa como direcciones**, los copia tal cual a
`avfs_params` y de ahí al SMC. Que coincidan en rango es casualidad numérica.

**Son parámetros opacos que consume el firmware**, con una unidad que no está en
el código. `NOT_DETERMINED` en cuanto a la unidad, y no la fuerzo: para
determinarla haría falta observar al SMC, que es la línea B.

Y para mi placa, la unidad **es irrelevante**, porque el valor que llega al SMC es
el mismo venga del VBIOS o del `case`.

## 5. Corrección a `922`

`922` concluyó, de leer `ucEnableApplyAVFS_CKS_OFF_Voltage = 0` en el VBIOS, que
mi placa no aplica AVFS con clock stretching off.

**Eso es cierto del VBIOS y falso del driver**, porque `:1803` lo fuerza a 1 con
independencia total del valor del VBIOS. El `if` no consulta
`ucEnableApplyAVFS_CKS_OFF_Voltage`: solo mira el ASIC y la revisión.

Lo que sí queda de `922` **correcto**: `Platform_sigma = 0` con bytes `00 00`
crudos, y `Platform_mean = 2000` = 500 mV. Eso no lo toca el driver.

## 6. Los errores de esta iteración

**1. Casi reporto un bug de precedencia inexistente.** Al leer `:1800-1802` con
`cut -c1-102` la línea se cortó justo donde estaba el `||`, y leí

```
((chip_id == CHIP_POLARIS12) && !ASICID_IS_P23(...))
 ASICID_IS_P21(...))
```

como un `&&` sin `||` mal colocado. Con `cat -A` la línea entera aparece:

```
^I^I    ((... == CHIP_POLARIS12) && !ASICID_IS_P23(...)) ||
^I^I    ASICID_IS_P21(adev->pdev->device, adev->pdev->revision)) {
```

**El `||` está, fuera del paréntesis.** El código es correcto y mi lectura no.

Es la **quinta vez hoy** que un `cut` me produce una ausencia o un defecto, y la
peor de todas: **no me daba un cero, me daba un bug imaginario en el driver.**

Y el daño concreto: una línea de 116 caracteres con un operador lógico partido, es
justo el caso donde un recorte de columna **no es un recorte de pantalla**, es un
cambio de significado.

**2. El primer grep de los macros salió vacío** porque usé `../../include/*.h` y
`../../amdgpu/*.h`, rutas que no existen desde donde estaba. Repetido en `amd/`
completo: 3 definiciones.

Los dos son el mismo error que ya había escrito tres veces hoy. **La regla no es
que esté escrita: es que se cumpla antes de decir nada.**

## 7. Frontier siguiente

**Cerrar la unidad de `a0..a2` por la vía que queda: el firmware del propio VBIOS,
no el driver.**

`Platform_sigma = 0` con `Platform_mean = 500 mV` deja la media/sigma degenerada, y
los coeficientes que sí están informados (`Aconstant[0..2] = 279 / 1186 / 446`) son
de una curva que **no está activada**. La regulación real va por la tabla
cuadrática VDROOP con CKS.

La pregunta que decide el resto: **¿de dónde saca el SMC su curva de dropout?**
Si de `a0..a2`, son tres parámetros y no necesito la unidad para usarlos. Si de una
tabla del ROM, esa tabla es localizable y es lo que gobierna el voltaje.

Y hay una pista medible en el propio struct: el BTF da
`SMU74_Discrete_DpmTable` con **`BTCGB_VDROOP_TABLE`** en el **byte 1828**,
`struct GB_VDROOP_TABLE_t[2]`, 32 bytes, y **`AVFSGB_VDROOP_TABLE`** en el **byte
1860**, `struct SMU_QuadraticCoeffs[2]`, 24 bytes. **Esos sí son coeficientes, y
están en el rango que `:2118` copia al SMC.** Ahí está la curva que manda.

Criterio de cierre: el contenido de `BTCGB_VDROOP_TABLE` y `AVFSGB_VDROOP_TABLE` en
la copia de 1776 bytes, con el criterio de plausibilidad en el dominio de una
curva de dropout, y si son o no los que el firmware usa.
