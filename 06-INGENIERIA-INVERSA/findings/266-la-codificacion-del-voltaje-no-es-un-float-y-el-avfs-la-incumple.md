# 266 · La codificacion del voltaje no es un float, y la tabla AVFS la incumple

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado en una linea
>
> `SMU_VoltageLevel` es un `uint32_t` con tres campos empaquetados por
> desplazamiento, **no un float**. Y los ocho valores `MinVoltage` de
> `avfs_graphics_level_polaris10` **no decodifican a milivoltios validos** con
> esa codificacion: todos dan cifras no enteras o absurdas.

## La codificacion, del propio codigo que escribe

`smu74.h:342`:

```c
typedef uint32_t SMU_VoltageLevel;
```

Mi hipotesis previa —que era un float IEEE754— queda **`REFUTED`**: al
decodificarla asi salen ceros negativos y cifras de 10^30.

Las constantes (`smu74.h:336-340`, `hwmgr.h:38`):

```
VOLTAGE_SCALE = 4    VDDC_SHIFT = 0    VDDCI_SHIFT = 15    PHASES_SHIFT = 30
```

Y la construccion, en `polaris10_get_dependency_volt_by_clk` (`:367-392`):

```c
*voltage  = (entries[i].vddc  * VOLTAGE_SCALE) << VDDC_SHIFT;
*voltage |= (vddci              * VOLTAGE_SCALE) << VDDCI_SHIFT;
*voltage |= 1 << PHASES_SHIFT;
```

Tres campos: VDDC en bits 0..14, VDDCI en 15..29, bit 30 de habilitacion de
fases. Es empaquetado de bits, no aritmetica de punto flotante.

## La verificacion, y por que un negativo necesita mas cuidado que un positivo

Aplico esa codificacion a los ocho `MinVoltage` del AVFS
(`polaris10_smumgr.c:83-90`):

```
0x100ea446  0x400ea446  0x740ea446  0xa40ea446
0xd80ea446  0x3c0fa446  0x6c0fa446  0xa00fa446
```

Resultado, campo por campo:

| comprobacion | resultado |
|---|---|
| 16 bits bajos | `0xa446` **identico en los 8 niveles** |
| VDDC = raw / 4 | **2321.5 mV en los 8** — imposible, y con decimales |
| ¿existe vddc entero con `vddc * 4 = 0xa446`? | **NINGUNO** |
| VDDCI = raw / 4 | 2055.2 / 7.2 / 6663.2 / 4615.2 / 3079.2 / 7687.8 / 5639.8 / 4103.8 mV |
| bit 30 (PHASES) | 0,1,1,0,1,0,1,0 — alternando sin criterio |

Cuatro comprobaciones independientes, las cuatro negativas:

1. **Un voltaje minimo por nivel no puede ser constante.** Si los 8 niveles
   comparten `MinVoltage`, el campo no esta CODIFICANDO un voltaje por nivel.
2. **2321.5 mV** no es un voltaje de ASIC, y el `.5` viola la propia regla de
   que `vddc * VOLTAGE_SCALE` con escala entera da enteros.
3. **No existe ningun `vddc` entero** que produzca `0xa446` con escala 4. O sea
   que los bits bajos **no son un campo VDDC** de esta codificacion.
4. Los valores de VDDCI (7 mV, 6663 mV) estan fuera de todo rango fisico.

## Que significa

La tabla `avfs_graphics_level_polaris10` **no esta escrita en la codificacion que
este mismo fichero usa para escribir el campo**. Es un dato de otra epoca, o de
otra generacion, o de otra convencion de firmware.

Hay una explicacion que no puedo cerrar desde aqui: que las constantes sean
antiguas y el layout de `SMU_VoltageLevel` haya cambiado despues. Eso es
`NOT_DETERMINED` con este corpus. **Lo que si es `PROVEN` es la incompatibilidad
en este camino**, y da igual cual de las dos sea: el dato no es utilizable tal
cual.

## Encadenado con 263 y 265

Esto **refuerza** la conclusion de `265` en vez de suavizarla. La ruta AVFS
presenta tres defectos independientes, y los tres verificados:

| | defecto | estado |
|---|---|---|
| `263` | se sobrescribe: el orden de init la pisa | `PROVEN` |
| `265` | `SclkFrequency` distinto del VBIOS, cociente no constante | `PROVEN` |
| `266` | `MinVoltage` no decodifica a voltajes validos | `PROVEN` |

Y se suma el de nombre: la constante es `..._polaris10` y la usa Polaris12.

**Consecuencia practica:** `polaris10_setup_graphics_level_structure` escribe una
tabla que ni llega al hardware. Y cuando llegase, seria incoherente con lo que
declara. Es codigo muerto en esta placa. No es una mejora que corregir: es una decision de diseño sobre cual es la fuente de verdad, y en
esta ruta la fuente de verdad es el VBIOS.

## Lo que NO afirmo

- **NO** afirmo que los valores AVFS sean "erroneos" en un sentido que pueda
  corregir. No tengo la convencion del firmware que los produjo, y sin ella
  cualquier "arreglo" seria inventar.
- **NO** he medido voltajes. `B_RUNTIME = NOT_EXECUTED`. Todo esto es lectura de
  fuente mas aritmetica verificada.
- **NO** he tocado hardware ni firmware.

## Lo que queda abierto, y es lo util

La **curva V-f real** de mi placa sigue sin determinar, y ahora se por que:
`polaris10_get_dependency_volt_by_clk` la construye desde
`table_info->vdd_dep_on_sclk` del VBIOS usando `entries[i].vddc`, y **yo todavia
no he decodificado ese campo de mi captura**.

Ese es el camino correcto y el pendiente real: leer los 8 registros SCLK de
`0x9D15` (15 bytes cada uno, segun `121`), sacar `usVddc` de cada uno, y con eso
tener la curva V-f en milivoltios. Con la curva, el techo de 1071 MHz deja de ser
"lo que declara el VBIOS" y pasa a ser "1071 MHz con el voltaje que el VBIOS
declara para ese reloj".

Discriminante: el layout del registro. ~~`ATOM_Tonga_SCLK_Dependency_Record`
**no existe** con ese nombre~~ — **CORREGIDO en `267`: si existe**, en
`pm/powerplay/hwmgr/pptable_v1_0.h:185`, no en `atombios.h` como busque. El
layout esta resuelto y el resultado es `267`.