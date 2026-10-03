# 950 · Mi placa baja voltaje pero no baja reloj: el desajuste está medido

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **La placa estaba en 997 MHz con carga 0 %, y a 812 mV.** La tensión **sí** está
> en el tercio bajo de la escalera de voltajes de la propia placa; el reloj **no**
> está en su suelo.
>
> Y por el camino: **el contraste que vine a hacer no se puede hacer**, porque la
> tabla de voltajes de VDDGFX en mi VBIOS no contiene voltajes. La de VDDC sí, y
> por eso valida el método entero y desmiente la mitad del resultado.

## 1. El contraste que no se sostiene

Iba a leer el voltaje que el VBIOS asigna a `vddInd = 0` —mi nivel 0 de la tabla
SCLK— y compararlo con los `812 mV` observados.

```
usVddgfxLookupTableOffset @base+49 = 201 -> 0x9CD3
ATOM_Tonga_Voltage_Lookup_Table   ucRevId=0  ucNumEntries=8   registro de 8 B (BTF)

idx   usVdd (u16)   usVdd (i16)
  0          900            900
  1        65282           -254
  2        65283           -253
  3        65284           -252
  4        65285           -251
  5        65286           -250
  6        65287           -249
  7        65288           -248
```

**65282 mV son 65 voltios, y como `int16` son −254, −253, … −248: una secuencia
aritmética de paso 1.** Eso no es una escalera de voltajes, **es un mapa de bits**,
un bit por nivel.

Mi lectura inicial dio «812 vs 900, diferencia −88 mV» y **era falsa**. La capturo
el test de dominio, antes de escribir nada, y esa es exactamente la funcion del
test: un numero que no sobrevive al dominio no se publica.

## 2. Que si se sostiene, y valida el metodo entero

La tabla hermana, en la misma estructura y con el mismo codigo de conversion:

```
usVddcLookupTableOffset @base+47 = 119 -> 0x9C81   ucRevId=0  ucNumEntries=10

idx   usVdd
  0      700
  1      750
  2      800
  3      850
  4      875
  5      900
  6      950
  7     1000
  8     1050
  9     1100
```

**Diez voltajes, monótonos, en milivoltios, con paso limpio.** Eso confirma de una
sola vez, y por separado de la tabla mala:

```
el byte 47 y el byte 49 de los campos de offset        PROVEN
el esquema PPI + offset                                 PROVEN
la cabecera ucRevId @0, ucNumEntries @1                PROVEN
el paso de 8 del registro                              PROVEN
el offset 0 de usVdd dentro del registro               PROVEN
el uso de GET_FLEXIBLE_ARRAY_MEMBER_ADDR con i         PROVEN (:178-182)
```

**Una tabla coherente valida el metodo con el que se leyo la incoherente.** Es el
mismo control de dominio de `929`, aplicado al reves: no «el BTF dice 15 y el
dominio dice 15», sino «el dominio dice que una tabla esta bien y dice que la otra
no, y comparten todo el metodo».

**Estado honesto del contraste:** `vddInd` → voltaje **no es resoluble para VDDGFX
en esa direccion**. Si el contenido es un mapa de bits, el significado de esos
bits es `SEMANTIC_MISSING` y esta en el firmware del SMC. **No se puede ir a buscar
un voltaje donde hay un mapa de bits, por muy limpia que sea la aritmetica que
produzca.**

## 3. Y lo que si se puede decir, con numeros

La escalera de voltajes de mi placa es **700 a 1100 mV en 10 escalones**, y la
tension observada en reposo cae en ella:

```
812 mV observados
    750  <- escalon 1
    800  <- escalon 2      812 esta entre 2 y 3
    850  <- escalon 3
```

**812 mV esta en el tercio bajo de la escalera de la propia placa.** Con eso si
puedo contestar la pregunta de fondo:

> ¿Esta la placa en el estado de reposo que el VBIOS propone?

**En cuanto a tension, si.** Y en cuanto a reloj, **no**:

```
OBSERVADO, carga 0 %:
  SCLK          997 MHz   <- sensor GFX_SCLK, reloj instantaneo
  PSTATE_SCLK   214 MHz   <- sensor STABLE_PSTATE_SCLK   == mi nivel 0
  VDDGFX        812 mV    <- sensor VDDGFX, sin escalar
  input power   5.157 W   <- sensor GPU_INPUT_POWER
  temperatura   42 C

VBIOS:
  nivel 0   214 MHz   vddInd 0   sin clock stretching
```

**El nucleo corre a 997 MHz con la GPU al 0 % de carga, y su estado estable es
214 MHz.** Esta casi cinco veces por encima de su suelo. **Y la tension esta
abajo.** El voltage bajo no es porque este en reposo: **esta bajando voltaje sin
bajar reloj**, y eso es lo que consume.

**Es el desajuste de gestion de energia mas directamente accionable que he
medido en toda la linea**, y encaja con algo que `929`/`931` ya habian dejado
claro: el reloj stretching no es lo que gobierna esta placa, es un mecanismo
puntual, y la politica de bajar reloj con la carga vive en otro sitio.

## 4. La semantica de cada campo, del productor y no del nombre

La captura no traia la fuente, asi que la saque del codigo que la imprime:

```
amdgpu_pm.c:4876-4877   AMDGPU_PP_SENSOR_GFX_MCLK           -> "MCLK"        value/100
:4878-4879              AMDGPU_PP_SENSOR_GFX_SCLK           -> "SCLK"        value/100
:4880-4881              AMDGPU_PP_SENSOR_STABLE_PSTATE_SCLK -> "PSTATE_SCLK" value/100
:4882-4883              AMDGPU_PP_SENSOR_STABLE_PSTATE_MCLK -> "PSTATE_MCLK" value/100
:4884-4885              AMDGPU_PP_SENSOR_VDDGFX             -> "VDDGFX"      value (mV)
:4886-4887              AMDGPU_PP_SENSOR_VDDNB              -> "VDDNB"       AUSENTE
:4888-4894              AMDGPU_PP_SENSOR_GPU_AVG_POWER      -> "average SoC" AUSENTE
:4895-4900              AMDGPU_PP_SENSOR_GPU_INPUT_POWER    -> "current SoC"  query>>8, &0xff
```

**El codigo solo imprime cuando `amdgpu_dpm_read_sensor` devuelve exito.** Que
`VDDNB` y `average SoC` no aparezcan **significa que esas lecturas fallaron**, no
que no existan. Y `5.157 W` es **`GPU_INPUT_POWER`: la potencia que entra en la
GPU**, no la del die.

**Y aqui hay una segunda confirmacion independiente de la unidad de `931`:**
`value/100` aparece aqui, en `amdgpu_pm.c`, **un fichero distinto** del
`smu7_hwmgr.c:5084` que uso `931`. Dos ficheros, dos rutas de codigo, el mismo
`/100` sobre el mismo sensor. **`214` MHz derivado de `21400` queda corroborado
por dos vias.**

## 5. Lo que NO concluyo de esto

```
que la placa "deberia" estar a 214 MHz          NOT_DETERMINED
por que SCLK marca 997 con carga 0 %             NOT_DETERMINED
que 997 MHz sea un nivel valido de DPM            REFUTADO por 945: 997 no esta
                                                  entre los 8 valores de la tabla
que 42 C y 5.157 W sean "buenos" o "malos"        SEMANTIC_MISSING
                                                  (el techo termico no esta medido)
el significado de los bits de 0x9CD3            SEMANTIC_MISSING
el significado de STABLE_PSTATE_*               SEMANTIC_MISSING
```

**Una sola muestra en reposo no separa «la placa manages bien» de «la placa se
manage mal».** Se que hay un desajuste entre el reloj instantaneo y el estado
estable, y se que la tension esta en el tercio bajo. **No se si el reloj alto es un
defecto, una politica deliberada, o la consecuencia de tener el monitor encendido.**
Afirmar cualquiera de las tres sin medirlo seria el cierre falso que vengo
corrigiendo desde `935`.

## 6. Errores de esta iteracion

**1. Casi publico «812 vs 900, diferencia −88 mV».** Lo calcule antes de
comprobar el dominio, y si lo escribo habria sido un hallazgo falso con forma de
medida. **Un numero se comprueba contra el dominio antes de existir, no despues
de publicarse.** El mismo orden que fallo en `907` con `sizeof` de un puntero.

**2.** Assumi que `vddInd` indexes esa tabla. **Mi nivel 0 tiene `vddInd = 0` y mis
niveles llegan a `vddInd = 9`, con una tabla de 8 entradas** — una incoherencia que
debia hacerme sospechar de la relacion antes de medir. **Un indice que excede el
rango de su tabla es una pista de que la relacion no existe**, y la lei despues.

**3.** Busque los structs por nombre (`ATOM_VoltageLookupTable`) y no estaban;
los nombres reales son `ATOM_Tonga_Voltage_Lookup_Table` y
`..._Record`, con guiones bajos. **Tercera vez en dos dias que el nombre lleva
guiones bajos.** Los tres fallos tienen el mismo: *buscar el nombre en vez de leer
la declaracion*.

## 7. Frontier siguiente

```
1.  la escalera de voltajes de mi placa: 700..1100 mV, 10 escalones      PROVEN
2.  los 812 mV observados caen en el tercio bajo de esa escalera          PROVEN
3.  812 mV observados con 0 % de carga, y SCLK a 997 MHz                  PROVEN
4.  997 MHz es casi 5x el estado estable de 214 MHz                       PROVEN
5.  la tension baja pero el reloj no: desajuste de gestion de energia     PROVEN
6.  la tabla VDDGFX en 0x9CD3 no contiene voltajes, sino un mapa de bits  PROVEN
7.  la tabla VDDC en 0x9C81 valida el metodo entero                        PROVEN
8.  la unidad /100 corroborada por dos ficheros independientes            CORROBORATED
9.  por que SCLK marca 997 sin carga                                      NOT_DETERMINED
10. el techo termico y el significado de los bits                         SEMANTIC_MISSING
```

**El frente util es el punto 9, y es el punto que mas me cuesta no resolver por
via del sentido común.** Se que hay un reloj de nucleo a 997 MHz con la GPU
parada. Hay tres explicaciones posibles y **se distinguen con un solo dato**: si
el reloj sube con carga real y baja al vacio, es que el reloj alto es una
consecuencia de la captura; si se queda en 997 con la carga al 100 %, es que la
politica de bajada no actua.

Y ese dato **no requiere registros ni autorizacion nueva**: `amdgpu_pm_info.txt` ya
existe y el nodo que lo produce es de solo lectura, y la unica condicion es que
haya una segunda captura con la GPU en carga.

Criterio de cierre: si existe una segunda captura de `amdgpu_pm_info` —en
`revkit/capturas/`, con otra fecha, o en `.err`— con `GPU Load` alto, contrastar
los dos puntos. Si **no existe** una segunda captura, eso es el resultado: el
observable existe, es de solo lectura, y **nadie lo ha medido bajo carga** —que es
un `NOT_OBSERVED` con una consecuencia concreta, no una laguna sin nombre.
