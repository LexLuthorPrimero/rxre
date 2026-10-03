# 603 · `SMU74_Discrete_DpmTable` no tiene relleno: `502` queda confirmado, y el método era el correcto

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0

> ## Resultado
>
> El riesgo que abrí en `601` —«si el struct tiene relleno, el layout de `502`
> está desplazado»— queda **cerrado en contra**:
>
> ```
> sizeof(SMU74_Discrete_DpmTable) alineado   = 1884
> sizeof(struct __DpmTable_packed)           = 1884
> relleno que mete el compilador             = 0
> offsetof(SystemFlags)                      = 108   en ambos
> ```
>
> Y la generalización a las tablas que **sí** se leen del VBIOS da **3 de 4 con
> relleno**, incluida la tabla SCLK de `267`. Pero `267` la decodificó **por el
> VBIOS**, no por el struct, y **acertó**.

## El riesgo de `601` queda cerrado

Compilé el struct dos veces: verbatim y con `__attribute__((packed))`, en el mismo
`main`, con el mismo resto de tipos.

**Cero relleno.** `1884` en ambos casos, y `offsetof(SystemFlags) = 108` en ambos.

El hallazgo `502` —los 95 campos, el rango `108..1883`, los 22 en cero, las 16
puertas— **queda confirmado**. El criterio que declaré era «si difieren, `502` se
reabre con el rango corregido», y la medición dice que no se reabre.

## Y una corrección de encuadre que me estaba haciendo falta

En `601` escribí que el desacuerdo de la tabla PCIe «no se transfiere» al DPM, y lo
dije de pasada. Ahora lo hago con la medición delante, porque **son dos clases
distintas y yo las estaba mezclando**:

| clase | quién escribe | qué tiene que coincidir |
|---|---|---|
| **tablas que el driver lee del VBIOS** | el firmware de la placa | formato empaquetado del VBIOS vs `sizeof` de C |
| **tablas que el driver construye** (`smc_state_table`) | el driver | `sizeof` de C vs lo que espera el firmware |

La tabla DPM es de la **segunda**. Se rellena campo a campo desde
`polaris10_init_smc_table` y se copia entera al SMC: **nada de ella viene del
VBIOS**, así que el hallazgo de la tabla PCIe no le afecta. Su coherencia depende
de que el firmware espere el mismo layout, y eso **no es determinable estáticamente
desde mi corpus** (`EVIDENCE_MISSING`).

El `sizeof` de C es la autoridad para la segunda clase y para nada más.

## La generalización: 3 de 4 tablas del VBIOS tienen relleno

```
ATOM_Polaris10_PCIE_Table        alineado=4   empaq=2   *** DIFIEREN ***
ATOM_Tonga_PCIE_Table            alineado=2   empaq=2   COINCIDEN
ATOM_Polaris_SCLK_Dependency_Table alineado=4  empaq=2   *** DIFIEREN ***
ATOM_Tonga_SCLK_Dependency_Table alineado=4   empaq=2   *** DIFIEREN ***
```

Y los registros:

```
ATOM_Polaris_SCLK_Dependency_Record   alineado=16   empaq=15   *** DIFIEREN ***
ATOM_Tonga_SCLK_Dependency_Record     alineado=12   empaq=11   *** DIFIEREN ***
ATOM_Polaris10_PCIE_Record            alineado=8    empaq=8    coinciden
```

**Solo `ATOM_Tonga_PCIE_Table` coincide**, y es porque su registro no tiene `ULONG`.
El resto, no.

Eso **cuantifica el hallazgo de `601`**: no es una rareza de una tabla, es **la
regla general** para los structs del VBIOS que contienen un `ULONG`. El compilador
alinea, el formato empaquetado no, y el código lee con el del compilador.

## Y lo importante: `267` la hizo bien, y por el método correcto

La tabla SCLK **también** tiene relleno: registro 16 alineado, 15 empaquetado.

`267` decodificó la tabla SCLK usando entradas de **15 bytes**, y lo validé con
`0x9D15 + 8×15` — o sea, **contra el VBIOS**. No contra el struct.

**Acertó.** Y acertó por el motivo correcto: el tamaño de entrada se derivó de los
datos, no de la cabecera. Si hubiera usado `sizeof(ATOM_Polaris_SCLK_Dependency_Record)`
— 16 — las ocho entradas habrían caído en 8 bytes desplazados cada una, y la tabla
habría salido mal **sin ningún aviso**: el compilador no protesta, simplemente
devuelve 16.

La diferencia entre `267` y el caso PCIe es **una sola cosa**: si validé el tamaño
contra el VBIOS o me fié del struct. En `267` validé. En la PCIe no tenía forma de
validarlo sin medir el contenido, y lo medí después — y ahí se rompió.

## La regla que sale de las dos, y que es lo que me llevo

> **Para una tabla que el driver lee del VBIOS, el `sizeof` del struct es una
> hipótesis, no una medida. La única medida es contra los bytes del VBIOS.**

Y el test que funciona es el mismo en los dos casos, y ya lo he hecho dos veces:

1. Extraer la tabla del VBIOS con una alineación **supuesta**.
2. Comprobar que los valores decodificados son **plausibles** en su dominio —
   carriles 1..16, relojes 1..400 MHz, índices de generación pequeños.
3. Si no lo son, probar la alineación siguiente.

En `267` el paso 2 fue implícito: la curva de relojes de `214/551/734/980/1000/
1020/1046/1071 MHz` **no podía salir de una lectura desplazada**. En la PCIe el
paso 2 es el `lanes = 0` de `601`. **El mismo discriminante, aplicado al dominio
correcto.**

Lo que me faltaba en el caso PCIe no era método: era **aplicarlo**. Y lo que me
faltaba en general era no haber medido esto antes de usar los offsets.

## Tres errores míos en esta iteración, todos de la misma familia

**1. Un número falso enorme.** Calculé «1280 bytes de relleno» en la tabla DPM
buscando huecos entre offsets consecutivos. Salió de que mi probe imprime
`sizeof(miembro[0])` — el **elemento** del array — y yo lo comparé contra el span
del **array**. `GraphicsLevel@236+56` con 8 elementos de 56. Los huecos de 392,
112, 84… eran míos. **Un número plausible y falso, y del tamaño del que precisamente
intentaba detectar.**

**2. `%s` en una cadena C dentro de un `%` de Python.** El generador de mi probe
consumió el `%s` de un `printf` como formato propio y la línea se partió al instante.
Cuatro intentos seguidos por esa causa, y dos de ellos silenciosos: el fichero se
escribía mal y el error salía en gcc, lejos de la causa.

**3. Cerré `main` en la primera línea generada.** Puse `}` al final de cada `printf`,
así que la segunda tabla estaba fuera de la función y gcc se quejaba de
`expected declaration specifiers` en una línea que parecía correcta.

Los tres son **el mismo error**: un artefacto generado por mí que produce algo
plausible pero falso, y que solo se detecta mirando la salida con la unidad y el
significado a la vista. El `1280` era el peligroso, porque tenía la forma exacta
del hallazgo que buscaba.

## Lo que NO afirmo

- **NO** afirmo nada sobre las demás tablas del VBIOS que he decodificado —
  PowerTune, FirmwareInfo, AVFS, VoltageObjectInfo, ASIC_InternalSS. **No les he
  medido el relleno**, y este hallazgo dice que es probable que lo tengan. Sus
  decodificaciones son **`NOT_VERIFIED` hasta que se mida**, y eso incluye el
  PowerTune de `505`, del que sale `usClockStretchAmount = 2`.
- **NO** afirmo que el firmware espere el layout que el driver construye para la
  tabla DPM. No es medible desde aquí.
- **NO** he medido hardware. `B_RUNTIME = NOT_EXECUTED`.

## Frontier siguiente

**Medir el relleno de las cinco tablas del VBIOS que ya he decodificado**, que es
exactamente el mismo probe y el mismo criterio, y que **incluye el PowerTune de
`505`**.

Es una continuation mecánica de esta iteración y tiene un rendimiento alto: si
alguna tiene relleno, **todas las cifras que saqué de ella están desplazadas**, y
`505` apoya una puerta de las 16 sobre un valor leído con un offset que podría estar
mal. `505` es la conclusión más reciente y la más frágil, y por eso va primero.

Criterio de cierre: para cada una de las cinco, `sizeof` alineado contra empaquetado,
y el veredicto de si mis offsets previos eran válidos. Y si PowerTune tiene relleno,
**releer `usClockStretchAmount` con el offset correcto**, que puede mover el valor
de 2 a otra cosa y con él la puerta de `:2005`.

Es también la comprobación que **debí hacer antes de usar cualquier offset del
VBIOS**, y que ahora está automatizada en tres líneas de probe. Lo que no está
automatizado es **recordar ejecutarla**, y eso es lo único que ha fallado en todo
este tramo: no el método, la disciplina de aplicarlo.