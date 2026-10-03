# 965 · La revisión es 0xC7, y estaba en el repo desde el principio

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Qué cambia aquí
>
> **Un byte que toda la línea de clocks daba por no medido sí estaba medido**, en un log
> de arranque del propio proyecto, y su valor es `0xC7` y no `0xCF`.
>
> Eso **deja el ClockStretcher encendido** en mi placa y **refuta `945`**.

## 1. La pregunta, y por qué era la que gatesaba todo

`smu7_hwmgr.c:1975-1984` tiene una rama que **apaga el ClockStretcher entero**:

```c
    if ((adev->pdev->device == 0x699F) &&
        (adev->pdev->revision == 0xCF)) {
        phm_cap_unset(..., PHM_PlatformCaps_PowerContainment);
        data->enable_tdc_limit_feature = false;
        data->enable_pkg_pwr_tracking_feature = false;
        data->disable_edc_leakage_controller = true;
        phm_cap_unset(..., PHM_PlatformCaps_ClockStretcher);
    }
```

El `device` ya estaba `PROVEN` (`0x699F` → `CHIP_POLARIS12`). **El otro operando no.** Y mientras
no estuviera, las notas `929` `931` `957` y la tabla de dependencia SCLK entera dependían de una
suposición no declarada.

## 2. La revisión: `0xC7`, observada

```
06-INGENIERIA-INVERSA/evidencia/boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log:10

  oct 02 00:10:30 kalm kernel: amdgpu 0000:01:00.0: initializing kernel modesetting
  (POLARIS12 0x1002:0x699F 0x1002:0x0B04 0xC7).
```

Ese log tiene 89 líneas y 70 de ellas son de `amdgpu 0000:01:00.0`. Es evidencia almacenada: leerla
no es tocar hardware.

## 3. El contraste que la hace `PROVEN` y no `OBSERVED`

Un log puede estar bien escrito y estar mal. Lo decisivo es que **el formato del mensaje lo
imprime el driver**, y los campos encajan uno a uno:

```
amdgpu_device.c:3716
  "initializing kernel modesetting (%s 0x%04X:0x%04X 0x%04X:0x%04X 0x%02X).\n"
        │          │        │          │        │        │
        │          │        │          │        │        └─ 0xC7   REVISION
        │          │        │          │        └────────── 0x0B04  (funcion de audio)
        │          │        │          └─────────────────── 0x699F  DEVICE
        │          │        └────────────────────────────── 0x1002  VENDOR
        │          └─────────────────────────────────────── POLARIS12  ASIC
        └──────────────────────────────────────────────────
```

**Cinco especificadores, cinco campos, en el mismo orden.** `0x0B04` es la función de audio HDMI
del propio RX 550, lo que confirma que el `device` del log es el de mi placa y no el de otra.

Si la revisión fuera `0xCF`, la línea del log sería la misma con `0xCF` al final. No lo es.

## 4. Consecuencia: el ClockStretcher queda ENCENDIDO

```
device == 0x699F      PROVEN
revision == 0xC7      PROVEN   <- nuevo, y es lo que faltaba
revision == 0xCF      REFUTADO para esta placa

    => la rama de smu7_hwmgr.c:1975 NO se toma
```

Y por lo tanto, para mi placa:

```
PHM_PlatformCaps_ClockStretcher      PERMANECE ACTIVO   (no se hace unset)
PHM_PlatformCaps_PowerContainment    PERMANECE ACTIVO
enable_tdc_limit_feature             true
enable_pkg_pwr_tracking_feature      true
disable_edc_leakage_controller       false
```

**Esto encaja con lo que ya estaba medido y no encaja si la rama se tomara:**

- `usClockStretchAmount = 2` en la PowerTune de mi VBIOS (`502`).
- CKS `masterEn` activo en 7 de los 8 niveles de mi tabla de SCLK, con `cks_voffset = 0`.
- `polaris10_smumgr.c:1698` escribe `ClockStretcherAmount` cuando el cap está puesto.

Con `revision == 0xCF` las tres cosas serían inexplicables. Con `0xC7` son consecuencia de una
sola rama.

## 5. Lo que se refuta, y por qué se refutó: el alcance de la búsqueda

`945` dice, en su §1, que **la revisión no está medida en ninguna parte de este proyecto**. Es
falso, y el motivo del error es instructive:

```
945 §44   "revkit/ en general, buscando 0xC7 / 0xCF"
```

**La búsqueda se limitó a `revkit/`.** La evidencia estaba en
`06-INGENIERIA-INVERSA/evidencia/`. Una búsqueda con alcance acotado se convirtió en una afirmación
de ausencia **sobre todo el proyecto**.

Eso es exactamente lo que `AGENTS.md` §13 (READ SCOPE GATE) y mi regla `TRUNCATION_AS_ABSENCE`
prohíben, y no lo detecté porque el resultado era `0` y un `0` con un control de positivo parece
convincente: el `0xC7` que `945` rechaza correctamente **como fixture** le dio la sensación de
haber seguido el valor hasta el final. **Correcto sobre el fixture, y por eso mismo no buscó más
lejos.**

**Y el matiz que hay que conservar:** el `0xC7` de `revkit/bootcheck.py:141` **sigue siendo un
fixture**. Lo que cambia no es el valor del fixture —que era correcto— sino que **el valor correcto
tenía detrás una fuente real, y esa fuente era el log**. El fixture no era la prueba; era una copia
sin respaldo. `947` lo tenía como `OBSERVED`: pasa a `CORROBORATED`, por fuente independiente.

## 6. Corroboración de paso: el duplicado de `959` es real

```
959-el-barrido-como-suite-y-los-dos-fallos-de-su-verdicto.md
959-el-barrido-como-suite-y-los-tres-fallos.md
```

Dos ficheros con el mismo número y el mismo prefijo. No es una hipótesis sobre el choque de la banda
`9xx`: es un hecho, y es exactamente el daño que `963` describe. Corrobora la recomendación de
salir de una banda compartida, y confirma que `integridad.py` debe seguir marcando la banda.

## 7. Errores de esta iteración

1. **Busqué `pm/smu7_hwmgr.c` y no `pm/powerplay/hwmgr/smu7_hwmgr.c`.** Di por inexistente un
   símbolo que estaba, 15 veces, en el fichero correcto. No fue un cero el que me.paró: fue mi
   conclusión. Si no llego a reintentar con el árbol entero, habría registrado `NOT_FOUND` sobre
   algo presente — que es el peor resultado posible, porque además es creíble.
2. **`grep` sobre `revkit/capturas/` en lugar de `evidencia/`.** La repetición del error de `945`,
   con el mismo patrón: buscar donde ya se buscó en vez de donde puede estar.
3. Cuatro hallazgos no autorizan la generalización, pero **tampoco la contradiccióncita la
   generalización inversa.** Sabía que la revisión faltaba y por eso la busqué donde era
   fácil; lo que no hice fue barrer el árbol entero.

## 8. Estado

```
1.  revision == 0xC7                                        PROVEN   <- nuevo
2.  la rama de smu7_hwmgr.c:1975 NO se toma                 PROVEN   <- nuevo
3.  ClockStretcher queda ACTIVO en mi placa                  PROVEN   <- nuevo
4.  PowerContainment queda ACTIVO                            PROVEN   <- nuevo
5.  enable_tdc_limit_feature == true                         PROVEN   <- nuevo
6.  la tabla de SCLK, 929/931/957, ya no dependen de una
    suposicion de revision                                   CORROBORATED
7.  945: "la revision nunca se midio"                        REFUTADO
8.  945: "0xC7 de bootcheck.py es un fixture"                PROVEN (sigue siendo cierto)
9.  947: 0xC7 como OBSERVED                                 CORROBORATED
10. ro concreto: sin determinar                              RUNTIME_MISSING (sin cambio)
11. 0x699F + 0xCF apagaria ClockStretcher                    PROVEN pero NOT_APPLICABLE
12. dos ficheros 959, duplicados en la banda                 PROVEN
```

**El punto 11 es el que más fácil malinterpreta.** La rama existe y es real; **no es la de mi
placa**. `PROVEN` sobre una condición que mi hardware no cumple, sin decirlo, es un claim que
viaja mal. Va marcado `NOT_APPLICABLE` y no como pendiente.

**Y con esto la frontera del proyecto se estrecha de golpe:** los 8 bits de la efusiva (`ro`) eran
el dato que no se puede obtener sin hardware, y la revisión —que parecía el otro hueco del mismo
gate— sí estaba. Queda una sola palabra de 4 bytes pendiente en este gate, no dos.

Criterio de cierre: registro la corrección en `945` y en `947` por versión, sin borrar su historia.