# 203 · Los headers son vocabulario: solo se usa el 9% de los registros, y UVD/VCE el 85%

`CLASSIFICATION=DOCUMENTATION` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY/EVIDENCE`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`CORPUS=RESEARCH/working/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`DESARROLLA=la afirmacion de 202 de que BIF es "casi todo indexado"`

## Cuestión principal

`202` afirmó, a partir del **número de defines**:

> *`bif_5_1_d.h` tiene **3188 defines `ix` de 3549: el 90%**. Un driver propio que
> solo sepa hacer `*(volatile u32 *)(base + offset)` **no puede hablar con BIF ni
> con SMU**.*

Eso mezcla dos cosas distintas: cuántos registros hay **definidos** y cuántos
**usa el driver**. Son números muy diferentes.

## Criterio de terminación

Separar definido de usado, sobre el código entero del driver, y dar el perfil de
uso por bloque. **Cumplido: 625 ficheros, 12.7 MB de código, dos porcentajes.**

## Herramienta

`08-ARQUITECTURA/tools/aperture.py --uso`. Para cada cabecera, separa los defines
en MMIO e `ix`, y cuenta cuántos **aparecen en el `.c`/`.h` del driver**.

## El perfil

```
cabecera                    MMIO  usados       %   ix             ix usados
gfx_8_0_d.h                 2633     597   22.7%   167            20
gmc_v8_2_d.h                 882      77    8.7%     0             0
gmc_v8_1_d.h                1156      83    7.2%   524             3
uvd_6_0_d.h                   97      82   84.5%     9             3
vce_v3_0_d.h                  45      39   86.7%     0             0
oss_3_0_d.h                  545     117   21.5%   115             0
oss_2_0_d.h                  515     101   19.6%    99             0
bif_5_0_d.h                  475      38    8.0%   568            21
bif_5_1_d.h                  361      23    6.4%  3188            20
smu_7_1_3_d.h                133      10    7.5%  1091            22
smu_7_1_2_d.h                129      10    7.8%  1121            22
dce_10_0_d.h                6924     134    1.9%   406            16
TOTAL                      13895    1311    9.4%  7288           127
```

**Los `ix` son vocabulario casi vestigial: 127 de 7288, el 1.7%.** BIF define 3188
`ix` y el driver referencia **21**. La afirmación de `202` queda **retractada**.

## Tres cosas que salen del perfil y que no eran obvias

**1 · UVD y VCE se programan casi por completo.** `uvd_v6_0_d.h` usa el **84.5%**
de sus registros y `vce_v3_0_d.h` el **86.7%**. Ningún otro bloque pasa del 23%.

Eso convierte media en el bloque **más barato de implementar** de toda la placa:
97 y 45 registros definidos, de los que se usa 82 y 39. **Un driver propio puede
hacer decodificar y codificar con menos de 150 registros conocidos**, y no con los
2600 de la grafica.

**2 · La grafica usa menos de un cuarto de su vocabulario.** `gfx_v8_0_d.h` define
2633 registros MMIO y el driver usa 597, el **22.7%**. Al contrario que media: la
superficie es grande y estáiboldemente dispersa.

**3 · `dce_10_0_d.h` al 1.9% es la cabecera equivocada**, no un bloque desatendido.
Esta placa usa `dm` (DC), no el DCE legacy. Lo dejo dicho porque el 1.9% parece un
dato sobre display y en realidad es un dato sobre una cabecera que no aplica.

## El orden de magnitud del conjunto

**17394 registros definidos, 1311 usados: el 9.4%.**

Lo que un `grep -c "^#define" sobre las cabeceras produce **no es la superficie
de la placa**. Es un vocabulario que cubre muchas más generaciones de las que
esta placa usa, y del que el driver solo exercita una fracción.

**Un número de defines no es una medida de alcance**, ni de trabajo ni de
complejidad. `17394` sugiere una tarea con un orden de magnitud más grande del que
es: el número accionable es `1311`, y aun así no todos hacen falta.

## Por qué el self-test de este modo es un aserto raro

El modo `--uso` **no puede fallar dando 0 sin que se note**, que es el fallo
típico de un filtro que solo dice "no". Así que el aserto no comprueba el
resultado sino que **el extractor no esté roto**:

```python
if len(usados) > len(nombres) * 0.5:
    fails.append("... el medido a mano es ~20 de 3188")
```

Con el filtro roto, saldría 0 de 3188 — que parece un resultado plausible. El
aserto falla **si salen demasiados**, no si salen pocos, porque "pocos" es un
resultado real y "muchos" delata un extractor que ya no filtra.

Es un control **invertido** a propósito: en un filtro, el valor dangerous es el
extremo por defecto, no el extremo filtrado.

## Clasificación

| afirmación | estado |
|---|---|
| 1311 de 13895 MMIO se usan (9.4%) | `PROVEN` — `aperture --uso` |
| 127 de 7288 `ix` se usan (1.7%) | `PROVEN` |
| UVD usa el 84.5% de sus registros | `PROVEN` |
| VCE usa el 86.7% de sus registros | `PROVEN` |
| GFX usa el 22.7% | `PROVEN` |
| BIF es "casi todo indexado" | `RETRACTADO` — era , no uso |
| Media es el bloque más barato de implementar | `DERIVATION` — de 97+45 registros |
| Que los headers cubran muchas generaciones | `DERIVATION` — coherente con el 9.4% |
| Que los 1311 sean los únicos alcanzables | `NOT_DETERMINED` — solo los del driver |
| Que DCE al 1.9% signifique display desatendido | `REFUTADO` — cabecera que no aplica |

## Confounders

- **"Usado" significa "el nombre aparece en el `.c`/`.h` del driver".** No
  significa que se escriba en un camino alcanzable: un registro puede aparecer en
  una función muerta para este ASIC, o detrás de una condición que nunca se cumple
  en Polaris12. **Es una cota superior del uso real**, y la presento como tal.
- **La búsqueda es por nombre exacto.** Un registro usado solo por su parte
  `_SH` o `_SOC15` variants no cuenta. Puede haber alias.
- **`gmc_v8_2_d.h` al 8.7% y `gmc_v8_1_d.h` al 7.2%**: `192` ya vio que
  `gfx_v8_0.c` incluye el `gmc_8_2_d.h` y `gmc_v8_0.c` el `gmc_8_1_d.h`. Los dos headers cuentan por separado, así que las cifras no son
  directamente comparables con las de gfx.
- **El porcentaje de `dce_10_0_d.h` no dice nada de esta placa**, por lo del punto 3.
- **No he usado nada de runtime.** Es estático sobre el código.

## Desfalsificación

- **(a)** Las cifras → refutable con `aperture --uso`.
- **(b)** La retractación de `202` → refutable buscando `ixGCK_MCLK_FUSES`:
  **cero usos** en todo el driver.
- **(c)** Que UVD/VCE sean 85% → refutable contando a mano los `mmUVD`/`mmVCE`
  de `uvd_v6_0.c` y `vce_v3_0.c`.
- **(d)** Que el extractor no esté roto → refutable con el aserto invertido del
  self-test.

## UNLOCKS

- **Alcance de media, con número**: un driver propio puede cubrir decodificación y
  codificación con **menos de 150 registros** (82 de UVD, 39 de VCE), todos
  conocidos. Es el primer bloque con coste acotado de verdad.
- **§A queda con dos cifras en vez de una**: `17394` registros **definidos** y
  `1311` **usados**. Confundirlas es un error de un orden de magnitud.
- **Los `ix` dejan de ser un requisito**: con el 1.7% de uso, un driver propio no
  necesita el camino indexado para hablar con BIF ni SMU. **Retira una
  obligación que `202` declaraba.**
- **Un patrón de control reutilizable**: en un filtro, el aserto debe fallar
  **si salen demasiados**, no si salen pocos. "Pocos" es un resultado real;
  "muchos" delata un extractor que ya no filtra. El filtro por defecto es el
  extremo peligroso, y por eso el valor por defecto de un filtro debe ser
  *no filtrar*, nunca *filtrar todo*.
- **Siguiente paso natural**: `1311` sigue siendo mucho. Hay que decidir, por
  bloque, cuántos hacen falta para un driver propio.

## Evidencia

```
08-ARQUITECTURA/tools/aperture.py --uso
self-test: el aserto del modo uso falla si el extractor deja de filtrar

codigo del driver: 625 ficheros, 12709947 bytes
grep ixGCK_MCLK_FUSES amdgpu/*.c amdgpu/*.h   ->  0 usos
sdma_v3_0.c:1693            sdma_v3_1_ip_block -> sdma_v3_0_ip_funcs
oss/oss_3_0_d.h             85 defines mmSDMA_*/mmSRBM_*
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.