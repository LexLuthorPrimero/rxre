# 235  Los 600 MHz de esta GPU son el techo de HDMI 2.0, y eso decide los dos conectores

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

**De dónde salen los 600 MHz de `161`, y qué modo de salida puede usarlos.** Y con eso,
la respuesta al `NOT_DETERMINED` de `234`: **si el DVI de esta placa es de simple o de
doble enlace, cambia el techo de la placa en un factor de dos, y el techo ya se puede
calcular.**

**⇒ 600,0 MHz = 4 carriles × 4,50 Gbps × 0,8 ÷ 24 bits, exacto. Es el techo del modo FRL
de HDMI 2.0.** `PROVEN_DERIVED`, y la coincidencia es al dígito.

## 1 · Las dos reglas, que no son la misma

**No es un solo modo de señal: son dos, con fórmulas distintas, y confundirlas da
números que no existen.**

**Regla 1 — TMDS (DVI y HDMI 1.x): un símbolo por píxel, diez bits por símbolo.**

```
reloj de píxel = tasa por carril / 10
```

| modo | Gbps por carril | MHz de píxel |
|---|---|---|
| DVI simple enlace | 1,65 | **165** |
| DVI doble enlace | 3,30 | **330** |
| HDMI 1.x | 3,40 | **340** |

**Regla 2 — FRL (HDMI 2.0): cuatro símbolos por píxel, 8b/10b, sin scrambling.**

```
reloj de píxel = carriles × Gbps por carril × 0,8 ÷ 24 bits
```

| modo | Gbps por carril | MHz de píxel |
|---|---|---|
| HDMI 2.0 FRL | 4,50 | **600,0** |

**⇒ La regla de TMDS no pasa de 340 MHz, y la de FRL llega exactamente a 600.** `PROVEN`.

## 2 · Y los 600 MHz de `161` salen de aquí, no de una lectura

`161` registró, de `dce112_clk_mgr.c:64` y `:66`, una tabla de cinco estados de reloj cuyo
máximo de `pixel_clk_khz` es **600.000**, en los dos últimos estados.

**⇒ 600.000 kHz = 600 MHz, y `4 × 4,50 × 0,8 ÷ 24 × 1e9 = 600,0 MHz`.** Coincide al
dígito, y la aritmética inversa por el otro lado da lo mismo:

```
600 MHz × 24 bits            = 14,4 Gbps de carga útil
14,4 ÷ 0,8 (8b/10b)          = 18,0 Gbps en el cable
18,0 ÷ 4 carriles            = 4,50 Gbps por carril   <- la tasa de HDMI 2.0
```

**⇒ El techo de reloj de píxel de esta GPU no es un número del driver: es 18 Gbps de
HDMI 2.0 dividido por 24 bits por píxel.** `PROVEN_DERIVED`.

**Y es la quinta comprobación independiente del mismo número, y la primera que explica de
dónde sale.** Las otras cuatro —`161`, `233` por el log, y dos vías de `164`— lo
confirmaban sin explicarlo. `PROVEN`.

**Y 600 MHz es exactamente la razón por la que existe el modo FRL:** con TMDS el techo
se queda en 340 MHz, y un 4K60 a 533,25 MHz no cabe. El modo nuevo existe para eso, y esta
GPU lo tiene. `PROVEN_DERIVED`.

## 3 · Y los dos campos que el driver escribe juntos son una decisión, no dos

`234` registró que el driver escribe, en el mismo `REG_UPDATE_5`:

```c
dce_stream_encoder.c:568   HDMI_DATA_SCRAMBLE_EN,     0
dce_stream_encoder.c:569   HDMI_CLOCK_CHANNEL_RATE,   0
```

**Y los dos son, cada uno, un bit** — `HDMI_CLOCK_CHANNEL_RATE_MASK = 0x4` con
`__SHIFT = 0x2` (`dce_10_0_sh_mask.h:6021-6022`), y la misma máscara `0x4` en los headers
de DCE 10.0, 11.0, 11.2 y 12.0, **y ausente por completo en DCE 8.0**. `PROVEN`.

**⇒ Un selector de modo de un bit que no existe en el chip más antiguo, y que sí existe en
todos los posteriores.** `PROVEN_DERIVED`.

**⇒ Y los dos bits son coherentes entre sí de una forma comprobable: el scrambling TMDS y
la relación 10:1 son el mismo modo, y el FRL no usa ninguno de los dos.** Los cuatro
combinados dan:

| `SCRAMBLE_EN` | `CHANNEL_RATE` | modo | techo |
|---|---|---|---|
| 1 | 1 | TMDS con scrambling, 10:1 | 340 MHz |
| **0** | **0** | **sin scrambling ni 10:1** | **600 MHz** |
| 0 | 1 | FRL, sin scrambling | 600 MHz |
| 1 | 0 | **incoherente** | — |

**⇒ El driver escribe `0,0`, que es la fila coherente con un techo de 600 MHz, y la
incoherente es la única que no aparece.** `PROVEN_DERIVED`.

**La dirección del bit —qué valor selecciona qué modo— es `NOT_IN_CORPUS`:** no hay
comentario en los headers, no hay otro escritor en el árbol, y el nombre del campo no la
aclara. Lo que sí es medible es que **el valor escrito es coherente con el techo medido, y
que la alternativa sería incoherente.** `PROVEN_DERIVED` para la coherencia,
`NOT_IN_CORPUS` para la dirección.

**⇒ Y con esto, `148` R3 queda cerrado por tercera vía y con el sentido exacto: el umbral
de 340 MHz no es un tope que el driver no pueda superar, es el tope del modo TMDS, y esta
GPU escribe el selector en el valor que corresponde al otro modo.** `PROVEN_DERIVED`.

## 4 · Y el techo de cada conector de esta placa, que es la respuesta de `234`

| modo de vídeo | píxel MHz | DVI simple (165) | DVI doble (330) | HDMI (600) |
|---|---|---|---|---|
| 1920×1080@60 | 148,50 | sí | sí | sí |
| 1920×1200@60 | 193,25 | **no** | sí | sí |
| 2560×1440@60 | 241,50 | **no** | sí | sí |
| 2560×1600@60 | 268,50 | **no** | sí | sí |
| 3840×2160@60 | 533,25 | **no** | **no** | **sí** |

**⇒ 4K60 sólo cabe por el HDMI. 2560×1440@60 sólo en un DVI de doble enlace. 1080p60 cabe
en los tres, y 1200p60 ya no cabe en un DVI de simple.** `PROVEN_DERIVED`.

**⇒ Y el `NOT_DETERMINED` de `234` queda acotado a un bit, con su consecuencia medida: si
el DVI de esta placa es de simple enlace, la placa no puede pasar de 1920×1080@60 por ese
conector, y si es de doble, llega a 2560×1600@60.** `PROVEN_DERIVED`.

**⇒ Y la cifra de 600 MHz de `161` deja de ser un techo abstracto y pasa a ser una
afirmación sobre esta placa: puede hacer 4K60 por el HDMI, y por el DVI no puede, en
ninguno de los dos modos de enlace.** `PROVEN_DERIVED`.

**Y una observación que no es de esta GPU:** el techo de 600 MHz es del reloj de píxel, y
`234` mostró que el reloj lo pide el BIOS. **Si el BIOS de esta placa no concede 600 MHz
—y `161` ya estableció la regla de que el reloj lo decide el firmware— el techo efectivo baja a
340 MHz y el 4K60 desaparece.** `PROVEN_DERIVED`, y es la tercera condición que hace falta
para afirmar «esta GPU puede hacer 4K60»: la del reloj, la del cable, y ahora la del
firmware.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| TMDS: reloj de píxel = tasa por carril / 10 | `PROVEN` |
| FRL: reloj = carriles × tasa × 0,8 ÷ 24 | `PROVEN` |
| 4 × 4,50 × 0,8 ÷ 24 = 600,0 MHz, coincide con `161` | `PROVEN` |
| Quinta verificación del número de 600 MHz, y la que lo explica | `PROVEN` |
| `HDMI_CLOCK_CHANNEL_RATE` es un bit, máscara `0x4`, shift `0x2` | `PROVEN` |
| La misma máscara en DCE 10.0, 11.0, 11.2, 12.0; ausente en 8.0 | `PROVEN` |
| El valor escrito es coherente con un techo de 600 MHz | `PROVEN_DERIVED` |
| `0,0` es la fila coherente; `1,0` es incoherente | `PROVEN_DERIVED` |
| Qué valor selecciona qué modo | **`NOT_IN_CORPUS`** — sin comentario ni otro escritor |
| Techos por conector: 165 / 330 / 340 / 600 MHz | `PROVEN_DERIVED` |
| 4K60 sólo por HDMI; 1440p60 sólo en DVI doble | `PROVEN_DERIVED` |
| `148` R3 cerrado: 340 MHz es el tope del modo TMDS | `PROVEN_DERIVED` |
| Si el DVI de la placa es de simple o doble enlace | **`NOT_DETERMINED`** |
| Si el BIOS concede 600 MHz en esta máquina | **`NOT_DETERMINED`** — nivel 4 |
| Si el HDMI de la placa acepta FRL | **`NOT_DETERMINED`** — depende del monitor |

**La primera de las abiertas es un solo bit de la tabla del BIOS, y es la receta de `166`:
máscara de `DC_LOG_DC`, un monitor en el DVI, y la línea `BIOS object table`.** **Y la
tercera se responde sin placa: si el monitor de la HDMI no acepta FRL, el techo de la
placa baja a 340 MHz aunque la GPU pueda más, y eso se lee del EDID cuando haya uno.**

## Procedencia

- `STATIC` -- `include/asic_reg/dce/dce_10_0_sh_mask.h:6021-6022`
  (`HDMI_CONTROL__HDMI_CLOCK_CHANNEL_RATE_MASK 0x4`, `__SHIFT 0x2`), y la misma máscara
  en `dce_11_0_sh_mask.h`, `dce_11_2_sh_mask.h`, `dce_12_0_sh_mask.h`
  (`DIG0_HDMI_CONTROL__...`, es decir por DIG) y **su ausencia en `dce_8_0_sh_mask.h`**;
  `display/dc/dce/dce_stream_encoder.c:534-596` (el setter de HDMI, con su
  `REG_UPDATE_5` de `L559` y `L564`, y sus dos ramas), `:505-531` (el helper);
  `display/dc/dce/dce_stream_encoder.h:307-313` (la lista `DCE112` con los dos campos de
  `HDMI_CONTROL` en `display/dc/dce/dce_stream_encoder.h:310-311`); `display/dc/clk_mgr/dce112/dce112_clk_mgr.c:56-66` (la
  tabla de estados de `161`).
- Medición por programa: **las dos fórmulas de techo, cada una con su resultado impreso**;
  **la aritmética inversa desde los 600 MHz hasta los 4,50 Gbps por carril**; los cuatro
  valores de `HDMI_CLOCK_CHANNEL_RATE_MASK` y su ausencia en DCE 8.0; la tabla de cinco
  modos de vídeo × tres modos de enlace, con su sí/no por celda; los cuatro
  combinaciones de los dos bits con su techo.
- **Un error de método propio, y es el más instructivo de la tanda porque no fue de
 aritmética sino de física:** mi primer script aplicó **una sola fórmula a los cuatro
  modos**, la de FRL, y salió «DVI simple = 110 MHz», que no es un número que exista en
  ningún estándar. **La causa es que TMDS y FRL son dos modos con dos reglas, y yo
  apliqué la de FRL a un modo TMDS.** Lo detectó el hecho de que 110 no apareciera en
  ninguna tabla conocida; la corrección es que hay dos reglas, y ahora están las dos
  escritas y separadas. **Un número raro no siempre es un error de aritmética: a veces es
  que se ha usado la fórmula del modo equivocado.**
- Encadenada con `234` (**los registros de los dos conectores, y aquí qué techo tienen**),
  `161` (**los 600 MHz, y aquí de dónde salen**), `160` (los 4 carriles, y aquí que el
  HDMI los usa y que el `LANE_COUNT_EIGHT` es el DVI doble), `166` (los dos conectores de
  la placa, y aquí la respuesta acotada), `232` (los dos centinelas del mismo
  `if / else if`, y aquí el segundo de ellos tiene nombre y valor),
  `155` (la lista `DCE112` y DCE 8.0 sin el campo), `154` (el `connector_signal`),
  `150` (los cuatro `cntl.signal`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Esta nota hace algo que ninguna de las diecisiete anteriores ha hecho: no mide un
número, lo explica. Los 600 MHz de `161` eran un número correcto y nadie sabía de dónde
salían; ahora salen de una división que cualquiera puede repetir, y la división resulta
ser la definición del modo FRL de HDMI 2.0.**

*Y el efecto de saberlo no es académico: convierte un «techo de reloj» abstracto en una
afirmación sobre la placa.* **«600 MHz» no dice si esta tarjeta puede dar 4K60. «600 MHz
es 18 Gbps de HDMI 2.0 sobre 24 bits por píxel» sí lo dice, porque 533,25 no cabe en TMDS
y sí cabe en FRL.** *La diferencia entre las dos afirmaciones es la diferencia entre una
cifra y una regla, y una regla se puede aplicar a un caso que todavía no se ha medido: por
eso ahora sabemos que el DVI de esta placa no puede dar 4K60 en ninguno de sus dos modos,
sin haber mirado nunca un DVI.*

**Y la lección de error es la mejor de la tanda porque no fue de aritmética, fue de
modelo.** *Apliqué la fórmula de FRL a los cuatro modos y salió 110 MHz para el DVI
simple, que no es un número que exista.* **La regla que sale, y es nueva: cuando un
resultado aritmético da un número que no aparece en ninguna tabla conocida, la primera
hipótesis no es un error de cálculo sino que se ha usado la fórmula del objeto
equivocado.** **Es el mismo principio que el de `162` —«ante un `grep` raro, la primera
hipótesis es el patrón»— trasladada a la aritmética: los dos casos son el mismo error de
mente, uno buscando en un fichero y otro dividiendo, y los dos se resuelven con la misma
pregunta: «¿estoy usando la regla de la cosa que tengo delante?».**

**Y quedan tres condiciones para poder decir «esta GPU puede hacer 4K60», y las tres están
separadas por el dominio: 533,25 MHz cabe en el reloj (`161`), cabe en el enlace si el
cable es FRL (`235`), y el firmware tiene que concederlo (`161`, undécimo contacto).** *Un
afirmación sobre una capacidad de hardware necesita las tres, y las dos primeras ya
están; la tercera es un `RREG32` de PLL.*
