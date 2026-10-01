# CP_RB: el ring buffer de GFX8, y una corrección sobre `IDLE_POLL_COUNT`

## Qué se obtiene de las herramientas

`./causa.py descubrir gfx_v8_0` marca `mmCP_RB_WPTR_POLL_ADDR_LO` como
**solo-escrito**: el driver lo escribe y nunca lo lee. Ese es el frente
abierto del dominio 18 (rings / scheduling) sin observabilidad directa.

```
gfx_v8_0.c:4263   WREG32(mmCP_RB_WPTR_POLL_ADDR_LO, lower_32_bits(wptr_gpu_addr))
gfx_v9_0.c:3426   WREG32_SOC15(GC, 0, mmCP_RB_WPTR_POLL_ADDR_LO, ...)
gfx_v10_0.c:6539  WREG32_SOC15(GC, 0, mmCP_RB_WPTR_POLL_ADDR_LO, ...)
```

Y el matiz que la herramienta obliga a comprobar, porque el nombre del par
invita a confundirlos:

```
mmCP_RB_WPTR_POLL_ADDR_LO   SOLO ESCRITO   (no se lee nunca)
mmCP_RB_WPTR_POLL_CNTL      SI SE LEE       (RREG en gfx_v7_0 y gfx_v10_0)
```

`WPTR_POLL_CNTL` se lee, se modifica y se escribe: es un
leer-modificar-escribir normal. `WPTR_POLL_ADDR` no tiene lectura en ninguna
generación. **No son el mismo caso**, aunque estén en la misma pareja y el
mismo mecanismo.

## `WREG32` en GFX8 no es un registro: es un banco

`WREG32` en GFX8 **no** escribe un registro. Es un acceso al **banco CP_RB**,
con el número de registro codificado en la propia macro. `WREG32_SOC15` de
gfx9/10 hace lo mismo y se le pasa el banco explícitamente.

```
gfx_v8_0.c        WREG32(REG, valor)                  banco implicito
gfx_v9_0 en aden  WREG32_SOC15(GC, 0, REG, valor)     banco explicito
```

Verificado por enumeración: `WREG32_SOC15` aparece en `v9`, `v10`, `v11`,
`v12` y **cero veces** en `gfx_v8_0.c`. GFX8 no tiene SOC15 y no puede usar esa
forma.

**Para un driver propio:** copiar la forma de Vega es un error que no da fallo
visible si se «adapta» a mano. Es exactamente el modo de fallo del que ya hay
varios casos en este proyecto.

## CORRECCIÓN: `0x60` es `POLL_FREQUENCY`, no `IDLE_POLL_COUNT`

Este documento se corrigió después de escribirlo. La primera versión afirmaba
que `0x60` era el conteo de inactividad. **Es falso**, y `regs.py` lo detecta.

El registro tiene **dos** campos que lo ocupan entero:

```
CP_RB_WPTR_POLL_CNTL:
    POLL_FREQUENCY       16 bits @  0     mask 0x0000ffff
    IDLE_POLL_COUNT      16 bits @ 16     mask 0xffff0000
```

Y el código hace:

```c
gfx_v8_0.c:3990   WREG32_FIELD(CP_RB_WPTR_POLL_CNTL, IDLE_POLL_COUNT, 0x60);
```

`WREG32_FIELD(REG, CAMPO, VALOR)` computa
`(REG & ~MASK_CAMPO) | (VALOR << SHIFT)`. Con el shift de `IDLE_POLL_COUNT`
en 16 y el valor `0x60`:

```
resultado = (0 & ~0xffff0000) | (0x60 << 16)
          = 0x00000000 | 0x00600000
          = 0x00600000
```

**El valor acaba en `POLL_FREQUENCY`.** No es una confusión de lectura: el
nombre del campo en el código induce a creer que se configura el conteo, y lo
que se configura es la frecuencia del poll.

Decodificado, y el valor **sí** cambia con la generación:

| generación | valor | `POLL_FREQUENCY` | `IDLE_POLL_COUNT` |
|---|---|---|---|
| `gfx_v8_0` | `0x60` | **96** | 0 |
| `gfx_v9_0` | `0x60` | **96** | 0 |
| `gfx_v10_0`+ | `0x00900100` | 256 | **144** |
| `gfx_v9_4_3` | `0x33450100` | 256 | **13125** |

(`./verdiff.py doc IDLE_POLL_COUNT` da la tabla de arriba: los valores vienen
de comentarios de upstream en ambas versiones.)

**Consecuencia para un driver propio: GFX8 no configura el conteo de
inactividad en absoluto, solo la frecuencia del poll.** gfx10 y posteriores
escriben los dos campos. Replicar el código de Vega escribiría un campo que en
GFX8 no está en uso.

## Lo que se retira

La primera versión deducía que «`0x60` es un conteo y no un intervalo, porque
si fuera tiempo gfx9 y gfx10 lo habrían cambiado». **Esa deducción se retira.**

El razonamiento fallaba: gfx10 sí cambió el valor, pero lo hizo **en otro
campo**. La aparente confirmación era casualidad del campo equivocado. Es un
buen ejemplo de por qué una corroboración aparente puede no ser tal: la
predicción se cumplió por una razón distinta a la que se hipotetizó, y eso la
deja sin valor como corroboración.

## Clasificación

| Afirmación | Estado |
|---|---|
| `WPTR_POLL_ADDR` se escribe y no se lee, en ninguna generación | **PROVEN** — enumeración |
| `WPTR_POLL_CNTL` **sí** se lee (RMENW en gfx7, gfx10) | **PROVEN** — `RREG32` en :3819 y :8038 |
| GFX8 usa `WREG32`, no `WREG32_SOC15` | **PROVEN** — 0 apariciones en `gfx_v8_0.c` |
| El registro tiene 2 campos que lo ocupan entero | **PROVEN** — `regs.py` |
| `0x60` acaba en `POLL_FREQUENCY`, no en `IDLE_POLL_COUNT` | **PROVEN_DERIVED** — aritmética del shift |
| GFX8 escribe 96 como frecuencia de poll | **PROVEN** — `gfx_v8_0.c:3990` |
| GFX8 no configura `IDLE_POLL_COUNT` | **PROVEN_DERIVED** |
| gfx10+ configuran los dos campos | **PROVEN** — comentarios upstream en ambas versiones |
| Que `0x60` sea un conteo y no un intervalo | **REFUTADO** — la deducción era inválida |
| Qué hace el hardware con `POLL_FREQUENCY = 96` | **NOT_DETERMINED** |
| Si el poll es en ciclos, paquetes o tiempo | **NOT_DETERMINED** |
| Por qué `gfx_v9_4_3` usa 13125 | **NOT_DETERMINED** |

## Lo que NO se puede determinar

La ausencia de lectura de `WPTR_POLL_ADDR` es lo que mantiene esto abierto: sin
observable, el corpus no puede decir qué hace el hardware con el valor escrito.

Cerrarlo requiere runtime: escribir el registro, ejecutar trabajo hasta llenar
el ring, y leer `CP_RB_STATUS` para ver si el conteo de poll coincide con los
comandos emitidos. Es un discriminante limpio y está especificado, pero
necesita root.

## Reproducir

```sh
./causa.py mapa mmCP_RB_WPTR_POLL_ADDR_LO
./causa.py descubrir gfx_v8_0
./regs.py CP_RB_WPTR_POLL_CNTL --asic gfx_8_0
./verdiff.py doc IDLE_POLL_COUNT
./cidx.py use WREG32_SOC15
```

Sin root. `GPU INTACTA`, `WRITE_EXECUTION NONE`.