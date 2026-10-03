# 925 · `a0..a2` sí son coeficientes, y la corrección va contra `926`

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **Tengo que corregir a `926`, y esta vez va contra su afirmación central.**
> Escribí que `a0..a2` **no son coeficientes de una curva**. Es falso.
>
> ```
> GB_VDROOP_TABLE_t   a0  a1  a2  spare      cuatro int32
> ```
>
> Y el driver los copia **sin transformar** a la tabla, con el nombre del campo
> destino igual al del origen:
>
> ```
> :1838-1840   BTCGB_VDROOP_TABLE[0].a0/a1/a2  <- ulGB_VDROOP_TABLE_CKSON_a0/a1/a2
> :1841-1843   BTCGB_VDROOP_TABLE[1].a0/a1/a2  <- ulGB_VDROOP_TABLE_CKSOFF_a0/a1/a2
> ```
>
> **Son los coeficientes de la curva cuadrática de droop.** No hay conversión ni
> offsets de por medio.

## 1. Lo que se sube, con la rama POLARIS12 aplicada

```
BTCGB_VDROOP_TABLE[0]   CKSON   del VBIOS en 0xA6E4
    a0 = -112,329,504    a1 = 200,456    a2 = 1,625

BTCGB_VDROOP_TABLE[1]   CKSOFF  sobrescrito por el driver (:1820-1822)
    a0 = -156,228,387    a1 = 196,702    a2 = 100,959

AVFSGB_VDROOP_TABLE[0]  CKSON   del VBIOS
    m1 = 958   m2 = 65,164   b = 56     m1_shift = 24   m2_shift = 12

AVFSGB_VDROOP_TABLE[1]  CKSOFF  sobrescrito (:1823-1825)
    m1 = 789   m2 = 65,233   b = 59     m1_shift = 24   m2_shift = 12
```

Los dos objetos caen dentro del rango `108..1883` que `:2118` copia:
`BTCGB_VDROOP_TABLE` en el **byte 1828** y `AVFSGB_VDROOP_TABLE` en el **byte
1860**, con tamaños medidos de 16 y 12 bytes. **Sí llegan al SMC.**

## 2. El discriminante que faltaba

`922` dejó los números como `NOT_DETERMINED` porque tres números y una hipótesis
de unidad no bastan. `926` los descartó por la magnitud de `a0`. **Los dos
veredictos eran prudentes y los dos equivocados**, y el discriminante no estaba
en los números: estaba en **comparar las dos curvas entre sí**.

```
AVFSGB_VDROOP  m2:   CKSON 65,164   vs   CKSOFF 65,233   ->   0.1 % de diferencia
BTCGB_VDROOP   a1:   CKSON 200,456  vs   CKSOFF 196,702  ->   2   % de diferencia
```

Dos curvas de droop calculadas **con y sin clock stretching** tienen que coincidir
en la pendiente y separarse en la constante: el clock stretching cambia el punto
de operación, no la forma de la curva.

**Eso es exactamente lo que miden estos números**, y vienen de **fuentes
independientes**: `CKSON` del VBIOS, `CKSOFF` de las constantes que el driver
tiene escritas. Si no fueran coeficientes de la misma curva, no podrían coincidir
así.

Y el signo ayuda: **`a0` es negativo en las dos**, que es lo propio de un término
constante de una curva que baja.

## 3. Lo que sigue sin saberse, y por qué no lo fuerzo

**La fórmula en punto fijo.** El driver fija `m1_shift = 24` y `m2_shift = 12`, así
que el firmware evalúa una expresión con esos desplazamientos. **La fórmula
exacta no está en este corpus**: es código del firmware del SMC, que no tengo.

Podría ajustarla hasta que salieran milivoltios razonables, y eso sería
exactamente el «número plausible» que el proyecto prohíbe: encajar la unidad a
la lectura en lugar de medirla. Queda `NOT_DETERMINED`, con el discriminante
nombrado en el frontier.

**`usPSM_Age_ComFactor`** sigue `NOT_DETERMINED`: no localicé su offset en el BTF
y **no lo estimé**, aunque `:1859` lo mete en `AVFS_meanNsigma`.

## 4. Lo que `926` acertó, y sigue en pie

**Que el driver sobrescribe `CKSOFF` con los mismos valores que trae el VBIOS.**
`:1820-1822` pone `0xF6B024DD / 0x3005E / 0x18A5F`, idénticos a los leídos en
`0xA6E4`. Y ahora además sabemos **que esos valores son los coeficientes de la
curva**, no un marcador.

**Que el driver fuerza `ucEnableApplyAVFS_CKS_OFF_Voltage = 1`** en `:1803`.

## 5. Corrección a `926`

| afirmación de `926` | estado real |
|---|---|
| «`a0..a2` no son coeficientes de una curva» | **`REFUTED`**: son `BTCGB_VDROOP_TABLE[1].a0..a2` |
| «tampoco son offsets al ROM» | **`CORROBORATED`**: el driver los copia como coeficientes |
| «son parámetros opacos cuya unidad no está en el código» | **parcial**: la unidad exacta no está, la **forma** sí |
| «el driver sobrescribe CKSOFF con los mismos valores del VBIOS» | **`PROVEN`** |
| «fuerza `ucEnableApplyAVFS_CKS_OFF_Voltage = 1`» | **`PROVEN`** |

## 6. Por qué fallé dos veces con los mismos números

Los dos errores comparten causa: **tratar un número aislado como si dijera algo
sobre su función.**

En `922` me dije «tres números no bastan» y los dejé sin decidir. Prudente, pero
incompleto: no busqué **otro conjunto de números del mismo tipo** con el que
compararlos.

En `926` vi `a0 = 0xF6B024DD`, lo comparé con `AConstant[0..2] = 279 / 1186 / 446`
y concluí que era demasiado grande para un coeficiente. **Estaba comparando
coeficientes de dos curvas distintas**: `Aconstant` es el de la curva media/sigma,
que `Platform_sigma = 0` deja **inactiva**, y `a0` es el de la curva VDROOP, que
es la que manda.

**Un número no significa nada sin saber de qué curva sale.** Y tenía las dos
curvas a la vista y comparé la que no toca con la que sí.

## 7. Frontier siguiente

**Fijar la escala de la curva usando `b`, el único término que no depende de
sigma.**

```
AVFSGB_VDROOP_TABLE[0]   CKSON    b = 56
AVFSGB_VDROOP_TABLE[1]   CKSOFF   b = 59
```

`b` es el término independiente de la curva, y **los dos son enteros pequeños y
próximos**, con la misma relación que `a1` y `m2`: coinciden casi igual y se
separan un poco. Si la curva devuelve milivoltios, `b` está cerca de la tensión
en el punto de referencia, y 56 y 59 apuntarían a una escala en decenas de
milivoltios.

Eso, junto con `Platform_mean = 500 mV` y `MaxVoltage = 1075 mV`, cerraría la
escala con **tres puntos independientes** en vez de con uno.

Criterio de cierre: la escala de `b` deducida de los dos valores y contrastada con
`Platform_mean` y `MaxVoltage`, o `NOT_DETERMINED` con el motivo exacto. Con eso
la regulación de tensión de mi placa queda **medible de punta a punta**: qué curva
se sube, con qué coeficientes y con qué escala.