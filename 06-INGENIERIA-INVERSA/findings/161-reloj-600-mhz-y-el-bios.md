# 161 · El reloj de píxel de esta GPU es 600 MHz, y lo decide el BIOS

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**El techo de reloj de píxel, que es la tercera de las dos cifras que un driver propio
necesita.** `160` dio la banda —25,92 Gbps útiles—; falta el reloj, y resulta que es el
que manda.

**Y de paso un `NOT_IN_CORPUS` de clase nueva: en la familia DCE el driver no calcula el
reloj de display. Se lo pide al BIOS y el BIOS le devuelve el real. Eso es el octavo
punto de contacto con firmware del proyecto.**

## 1 · Las cinco filas que son todo el gestor de reloj de DCE 11.2

`display/dc/clk_mgr/dce112/dce112_clk_mgr.c` entero son **237 líneas**, y la tabla de
techos son cinco:

```c
dce112_clk_mgr.c:56   static const struct state_dependent_clocks dce112_max_clks_by_state[] = {
dce112_clk_mgr.c:58           { .display_clk_khz = 0,       .pixel_clk_khz = 0 },
dce112_clk_mgr.c:60           { .display_clk_khz = 389189,   .pixel_clk_khz = 346672 },
dce112_clk_mgr.c:62           { .display_clk_khz = 459000,   .pixel_clk_khz = 400000 },
dce112_clk_mgr.c:64           { .display_clk_khz = 667000,   .pixel_clk_khz = 600000 },
dce112_clk_mgr.c:66           { .display_clk_khz = 1132000,  .pixel_clk_khz = 600000 } };
```

| estado | display kHz | píxel kHz | ratio |
|---|---|---|---|
| Invalid | 0 | 0 | — |
| UltraLow | 389.189 | 346.672 | 1,123 |
| Low | 459.000 | 400.000 | 1,147 |
| Nominal | 667.000 | **600.000** | 1,112 |
| Performance | **1.132.000** | **600.000** | 1,887 |

**⇒ El techo de reloj de píxel es 600 MHz, y no sube en el estado Performance: el reloj
de display sube a 1.132 MHz y el de píxel se queda en 600.** `PROVEN`.

**Y el constructor de DCE 11.2 completo es esto:**

```c
dce112_clk_mgr.c:223   void dce112_clk_mgr_construct(...)
dce112_clk_mgr.c:227           dce_clk_mgr_construct(ctx, clk_mgr);          <- DCE 10.0
dce112_clk_mgr.c:229           memcpy(clk_mgr->max_clks_by_state,
dce112_clk_mgr.c:230                    dce112_max_clks_by_state, ...);      <- 5 filas
dce112_clk_mgr.c:233           clk_mgr->regs        = &disp_clk_regs;
dce112_clk_mgr.c:234           clk_mgr->clk_mgr_shift = &disp_clk_shift;
dce112_clk_mgr.c:235           clk_mgr->clk_mgr_mask  = &disp_clk_mask;
dce112_clk_mgr.c:236           clk_mgr->base.funcs   = &dce112_funcs;         <- 2 punteros
```

**El constructor de DCE 10.0, una tabla de cinco números, tres punteros y una tabla de
dos funciones.** `PROVEN`. **Y el fichero incluye `dce100/dce_clk_mgr.h` y
`dce110/dce110_clk_mgr.h` (`L31-32`): la herencia está escrita en los `#include`.**

### Y el único cambio funcional, un entero

| | divisor del suelo del PLL |
|---|---|
| `dce_clk_mgr.c:271` (DCE 10.0) | `dentist_vco_freq_khz / 64` |
| `dce112_clk_mgr.c:83` y `:137` | `dentist_vco_freq_khz / **62**` |

**El suelo del PLL de DCE 11.2 es 62 en lugar de 64, en las dos apariciones.** Con el
valor de reserva de `dentist_vco_freq_khz` que pone `dce_clk_mgr.c:317` —**360.000 kHz**—
el suelo pasa de **5,625 MHz** a **5,806 MHz**. `PROVEN`.

**⇒ De las 237 líneas del gestor de reloj de DCE 11.2, el cambio respecto a DCE 10.0 es
un divisor, de 64 a 62.** `PROVEN_DERIVED`.

## 2 · Y hay un colchón del 15% que hay que conocer

```c
dce112_clk_mgr.c:199   /*TODO: W/A for dal3 linux, investigate why this works */
dce112_clk_mgr.c:200   if (!clk_mgr_dce->dfs_bypass_active)
dce112_clk_mgr.c:201           patched_disp_clk = patched_disp_clk * 115 / 100;
```

**El reloj de display pedido se multiplica por 1,15 antes de programarlo, con un comentario
que dice literalmente «investigar por qué funciona».** `PROVEN`.

**Consecuencia para un driver propio: el reloj que se programa no es el que se pide, es
1,15 veces, salvo que `dfs_bypass_active` esté puesto. Un ahorro de reloj del 15% en las
trazas no es un ahorro: es el colchón.** `PROVEN_DERIVED`.

## 3 · El punto de contacto con firmware, y es un `NOT_IN_CORPUS` nuevo

Todo el camino de programmation del reloj, en `dce112_set_clock` (`:70-122`):

```c
dce112_clk_mgr.c:73    struct bp_set_dce_clock_parameters dce_clk_params;
dce112_clk_mgr.c:85    dce_clk_params.target_clock_frequency = requested_clk_khz;
dce112_clk_mgr.c:86    dce_clk_params.pll_id = CLOCK_SOURCE_ID_DFS;
dce112_clk_mgr.c:87    dce_clk_params.clock_type = DCECLOCK_TYPE_DISPLAY_CLOCK;
dce112_clk_mgr.c:89    bp->funcs->set_dce_clock(bp, &dce_clk_params);
dce112_clk_mgr.c:90    actual_clock = dce_clk_params.target_clock_frequency;
```

**Se escribe la frecuencia pedida en el mismo campo que luego se lee, a través de
`bp->funcs`, que es `struct dc_vbios_funcs`.** `PROVEN`.

**Y `set_dce_clock` está declarado en las dos tablas de comandos del BIOS:**
`display/dc/bios/command_table.h:98` y `display/dc/bios/command_table2.h:92`. `PROVEN`.

**⇒ El driver pide un reloj, el BIOS decide cuál se puede dar, y el driver se queda con
la respuesta. No hay aritmética de PLL en el camino.** `PROVEN_DERIVED`.

**Esto es un octavo punto de contacto con firmware, y es de una clase que no estaba en
la lista de los siete de `155`:** los otros siete eran *datos* que el firmware
entrega —polaridad, rutas, `MC_VM_FB_LOCATION`, identificadores—, y este es una
**operación**: el firmware elige el divisor del PLL. `PROVEN_DERIVED`.

**⇒ Para un driver propio, el reloj de display de una GPU de la familia DCE no se puede
calcular desde el corpus.** Se puede pedir, si hay BIOS, y se puede acotar con la tabla
de cinco estados. Eso es todo. `NOT_IN_CORPUS`, en sentido fuerte, con la causa
identificada: la aritmética del divisor está en el firmware, no en el árbol.

## 4 · Y la tercera tabla de punteros, con la curva más limpia de la tanda

`struct clk_mgr_funcs` (`display/dc/inc/hw/clk_mgr.h:299`) declara **25 miembros**. Hay
**18 tablas** de ese tipo en el árbol. Medidas:

| tabla | fichero:línea | entradas | cobertura |
|---|---|---|---|
| `dce_funcs` | `clk_mgr/dce100/dce_clk_mgr.c:461` | 2 / 25 | **8%** |
| `dce110_funcs` | `clk_mgr/dce110/dce110_clk_mgr.c:282` | 2 / 25 | **8%** |
| `dce112_funcs` | `clk_mgr/dce112/dce112_clk_mgr.c:218` | 2 / 25 | **8%** |
| `dce120_funcs` | `clk_mgr/dce120/dce120_clk_mgr.c:123` | 2 / 25 | **8%** |
| `dcn201_funcs` | `clk_mgr/dcn201/dcn201_clk_mgr.c:172` | 4 | 16% |
| `rv1_clk_funcs` | `clk_mgr/dcn10/rv1_clk_mgr.c:304` | 4 | 16% |
| `vg_funcs` | `clk_mgr/dcn301/vg_clk_mgr.c:481` | 6 | 24% |
| `dcn2_funcs` | `clk_mgr/dcn20/dcn20_clk_mgr.c:517` | 7 | 28% |
| `dcn314_funcs` | `clk_mgr/dcn314/dcn314_clk_mgr.c:764` | 7 | 28% |
| `dcn315_funcs` | `clk_mgr/dcn315/dcn315_clk_mgr.c:595` | 7 | 28% |
| `dcn316_funcs` | `clk_mgr/dcn316/dcn316_clk_mgr.c:570` | 7 | 28% |
| `rn_clk_funcs` | `clk_mgr/dcn21/rn_clk_mgr.c:563` | 8 | 32% |
| `dcn31_funcs` | `clk_mgr/dcn31/dcn31_clk_mgr.c:664` | 8 | 32% |
| `dcn35_funcs` | `clk_mgr/dcn35/dcn35_clk_mgr.c:1325` | 11 | 44% |
| `dcn42_funcs` | `clk_mgr/dcn42/dcn42_clk_mgr.c:1011` | 12 | 48% |
| `dcn3_funcs` | `clk_mgr/dcn30/dcn30_clk_mgr.c:487` | 14 | 56% |
| `dcn32_funcs` | `clk_mgr/dcn32/dcn32_clk_mgr.c:1125` | 15 | 60% |
| `dcn401_funcs` | `clk_mgr/dcn401/dcn401_clk_mgr.c:1531` | 16 | 64% |

**⇒ Las cuatro DCE están todas en 2 de 25, el 8%. Y la curva DCN sube de 16% a 64%.**
`PROVEN`.

**Y esto es el espejo exacto de la curva del codificador de stream de `158`:** allí el
codificador grew de 22 (DCE) a 35 (DCN); aquí el reloj crece de 2 (DCE) a 16 (DCN).
**Los dos gráficos cuentan la misma historia desde dos extremos, y la historia es la del
punto 3: en DCE el driver es cliente del firmware; en DCN es el autor.**

**Corroborado por el tamaño del fichero: `dce112_clk_mgr.c` son 237 líneas y
`dcn401_clk_mgr.c` son 2.106. Nueve veces más código para el mismo trabajo, porque el
DCN resuelve el reloj y el DCE lo pide.** `PROVEN_DERIVED`.

**Y las 23 entradas a NULL de la tabla de DCE incluyen `init_clocks`, `get_clock`,
`set_max_memclk`, `get_memclk_states_from_smu`, `is_smu_present`,
`get_dispclk_from_dentist`.** **La última es la que más dice: DCE no tiene solvedor de
divisor de PLL, y la función que se lo preguntaría al reloj no está.** `PROVEN_DERIVED`.

## 5 · Las dos cifras juntas, y qué techo resulta

Con `600 MHz` de píxel y `25,92 Gbps` útiles de `160`:

| modo | píxel MHz | Gbit/s | cabe en 600 MHz | cabe en 25,92 Gbps |
|---|---|---|---|---|
| 1920×1080@60 | 148,50 | 3,56 | sí | sí |
| 2560×1440@60 | 241,50 | 5,80 | sí | sí |
| 2560×1600@60 | 268,50 | 6,44 | sí | sí |
| **3840×2160@60 RGB 8bpc** | **533,25** | **12,80** | **sí (89%)** | **sí (49%)** |
| 3840×2160@60 RGB 10bpc | 533,25 | 16,00 | sí (89%) | sí (62%) |
| 3840×2160@75 | 800,00 | 19,20 | **no** | sí (74%) |
| 3840×2160@120 | 1.066,50 | 25,60 | **no** | sí (99%) |
| 5120×2880@60 | 1.180,00 | 28,32 | **no** | **no** |

**⇒ 4K60 cabe, y el límite que muerde es el reloj de píxel, no la banda: al 4K60 el
píxel está al 89% de su techo y la banda al 49%. Hay el doble de holgura de ancho de
 banda.** `PROVEN_DERIVED`.

**⇒ 4K75 y 4K120 ya no caben por reloj, no por banda. 5K60 no cabe por ninguna de las
dos.** `PROVEN_DERIVED`.

**Y el 4K60 con el colchón aplicado: 533,25 × 1,15 = 613,24 MHz, que pasa de 600.** Es
decir: **el modo más alto que esta GPU puede hacer de forma nativa es 4K60, y queda a
menos de un 3% del techo de reloj una vez aplicado el workaround del 15%.** El margen es
de 2,8 puntos. `PROVEN_DERIVED`.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| Techo de reloj de píxel 600 MHz | `PROVEN` |
| El de display llega a 1.132 MHz sin que el píxel suba | `PROVEN` |
| El constructor de DCE 11.2 es una tabla de 5 filas sobre DCE 10.0 | `PROVEN` |
| El único cambio funcional es el divisor 64 → 62 | `PROVEN` |
| Suelo del PLL 5,806 MHz con `dentist` = 360 MHz | `PROVEN` |
| Colchón del 15% en el reloj de display | `PROVEN` |
| El reloj lo elige el BIOS, no el driver | `PROVEN_DERIVED` |
| `set_dce_clock` en las dos tablas de comandos del BIOS | `PROVEN` |
| El reloj de display no es calculable desde el corpus | **`NOT_IN_CORPUS`** |
| `struct clk_mgr_funcs`: 25 miembros, 18 tablas, DCE al 8% | `PROVEN` |
| La curva del reloj es el espejo de la del codificador | `PROVEN_DERIVED` |
| `get_dispclk_from_dentist` a NULL en DCE = no hay solvedor | `PROVEN_DERIVED` |
| 4K60 es el techo nativo, con 2,8 puntos de margen | `PROVEN_DERIVED` |
| Qué reloj concede realmente el BIOS a esta placa | **`NOT_DETERMINED`** |
| Si con 8b/10b y 4 carriles el modo 4K60 pide 32,40 Gbps | **`NOT_DETERMINED`** — falta el reparto |
| Si la iGPU Intel compite por el PCIe para alimentar el pixel clock | **`NOT_DETERMINED`** |

**La primera de las abiertas es la última cifra de `display/` que se puede pedir, y es
la de un `RREG32` de PLL.** La tercera es la más interesante de las tres y es de
arquitectura, no de esta GPU: en DCE, alimentar el pixel clock desde un DUT de pantalla
externa es un problema de PCIe que nadie ha escrito en el árbol.

## Procedencia

- `STATIC` -- `display/dc/clk_mgr/dce112/dce112_clk_mgr.c:1-237` (el fichero entero),
  `:56-66` (los cinco
  estados), `:70-122` (`dce112_set_clock` y la llamada al BIOS), `:83` `:137` (el
  divisor 62), `:165-189` (`dce112_set_dprefclk`), `:191-216`
  (`dce112_update_clocks`), `:199-201` (el colchón del 15%), `:218-221` (`dce112_funcs`,
  dos entradas), `:223-237` (el constructor), `:31-32` (los dos `#include` heredados);
  `display/dc/clk_mgr/dce100/dce_clk_mgr.c:271` (el divisor 64), `:313-317`
  (`dentist_vco_freq_khz` y su reserva de 360.000), `:461` (`dce_funcs`);
  `display/dc/inc/hw/clk_mgr.h:299` (los 25 miembros), `:376`
  (`dentist_vco_freq_khz`); `display/dc/bios/command_table.h:98` y
  `display/dc/bios/command_table2.h:92` (las dos declaraciones de `set_dce_clock`).
- Medición por programa: las cinco filas de la tabla de estados y el máximo de cada
  columna; **los 25 miembros del `struct` y las 18 tablas con su cobertura, ordenadas**;
  la comparación de los divisores 64 y 62 y el suelo que producen con 360.000 kHz; la
  tabla de modos de vídeo con el píxel, los Gbit/s y los dos porcentajes de uso; el
  margen del 4K60 con el colchón aplicado.
- **Dos errores de ruta y de patrón propios, en calls consecutivos, y los dos por el
  motivo conocido:** (1) apunté a
  `display/clk_mgr/dce112/...` en vez de `display/dc/clk_mgr/dce112/...`; (2) el patrón
  `static const struct dc_clk_mgr_funcs` no existe —el tipo se llama `clk_mgr_funcs` y
  las tablas no son `const`—, y el primer intento imprimió un `FileNotFoundError` en
  vez de un resultado.
- **Y una colisión de nombres más, la octava, y de la misma forma que la séptima:**
  el directorio `clk_mgr/dce100/` contiene `dce_clk_mgr.c`, no `dce100_clk_mgr.c`; el
  directorio `dce110/` sí contiene `dce110_clk_mgr.c`, y el `dce112/` sí
  `dce112_clk_mgr.c`. **Busqué el fichero por el nombre de la función y el directorio me
  descolocó; el patrón correcto fue `static struct clk_mgr_funcs` sin `const` y sin el
  prefijo `dc_`.**
- Encadenada con `160` (**las 25,92 Gbps, y aquí el reloj que las acompaña**),
  `159` (**una de las 52 funciones de DCE 11.2 es el reloj, y son 237 líneas**),
  `158` (el espejo de la curva, tabla distinta), `157` (el patrón `if (funcs->X)`,
  aplicado aquí a 23 NULL), `156` (constructor y tabla, a la escala más pequeña
  vista: 5 filas y 2 punteros), `155` (**los siete puntos de firmware; esta nota añade
  el octavo, y es de otra clase**), `154` (la señal), `153` (los siete caminos).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**El hallazgo de esta nota no es la cifra de 600 MHz —eso es una lectura— sino que los
600 MHz y los 25,92 Gbps de `160` no son comparables sin una tabla, y la tabla dice que
el reloj manda con el doble de holgura de banda.**

*Porque un techo sin el otro techo no significa nada.* Con 25,92 Gbps, cualquier tabla
que diga «4K sí» está tomando el límite equivocado: el 4K60 consume 12,80 de 25,92
Gbps, o sea la mitad. **La pregunta útil no era «¿cuánta banda tiene?» sino «¿qué
techo se alcanza primero?», y esa respuesta necesita los dos números medidos en
notas distintas y restados en una tercera.** *Es la misma operación que produjo el 58%
de `157` — dos inventarios y una resta— aplicada a un problema de ingeniería en vez de
a una estructura de C.*

**Y el segundo hallazgo, que es un `NOT_IN_CORPUS` nuevo, salió de leer el camino entero
en vez de leer la función que me interesaba.** *Yo quería el techo de reloj, que está
en la tabla de cinco filas, y podía haberlo escrito con eso.* Pero la tabla de cinco
filas está pegada a un constructor que llama a `dce_clk_mgr_construct` —el de DCE 10.0—
y a un `set_dce_clock` que va al BIOS. **La cifra no está flotando: está colgada de un
firmware, y eso cambia lo que significa «conocer el techo».**

*La regla, y es la segunda de la tanda que sale de leer de más y no de leer de menos:*
**un techo de hardware no es una propiedad del hardware. Es una propiedad de un camino
de código, y el camino puede acabar en el firmware.** Los 600 MHz están en el árbol; el
divisor que los produce no.

**Y de paso queda formulada la observación que explica las dos curvas de `158` y de esta
nota, que es la misma leída por los dos extremos: en la familia DCE el driver tiene el
8% de la interfaz de reloj y el 58% de la de codificador, y en la familia DCN tiene el
64% y el 92%.** *En un caso el driver pide las cosas y en el otro las calcula, y esa
sola diferencia de actitud explica por qué el gestor de reloj de DCE 11.2 cabe en 237
líneas y el de DCN 4.01 en 2.106.* **Y explica por qué el camino de esta placa tiene un
salto en `137` y no tiene un paso más: el paso 13 de la lista de arranque, el del reloj,
no es un paso del driver, es una llamada al BIOS.**
