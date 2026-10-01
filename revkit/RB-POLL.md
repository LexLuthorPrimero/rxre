# CP_RB: el ring buffer de GFX8, y por qué el polling cambia de ASIC

## Qué se obtiene de las herramientas

`./causa.py descubrir gfx_v8_0` marca `mmCP_RB_WPTR_POLL_ADDR_LO` como
**solo-escrito**: el driver lo escribe y nunca lo lee. Ese es el frente
abierto del dominio 18 (rings / scheduling) sin observabilidad directa.

Lo interesante es lo que aparece al mapearlo:

```
gfx_v8_0.c:4263   WREG32(mmCP_RB_WPTR_POLL_ADDR_LO, lower_32_bits(wptr_gpu_addr))
gfx_v9_0.c:3426   WREG32_SOC15(GC, 0, mmCP_RB_WPTR_POLL_ADDR_LO, ...)
gfx_v10_0.c:6539  WREG32_SOC15(GC, 0, mmCP_RB_WPTR_POLL_ADDR_LO, ...)
```

Y el matiz que hay que comprobar, porque el nombre del par invita a
confundirlos:

```
mmCP_RB_WPTR_POLL_ADDR_LO   SOLO ESCRITO   (no se lee nunca)
mmCP_RB_WPTR_POLL_CNTL      SI SE LEE       (RREG en gfx_v7_0 y gfx_v10_0)
```

`WPTR_POLL_CNTL` se lee, se modifica y se escribe: es un
leer-modificar-escribir normal. `WPTR_POLL_ADDR` no tiene lectura en ninguna
generación. **No son el mismo caso**, aunque esten en la misma pareja y el
mismo mecanismo.

## El detalle que importa: no es un registro, es un banco

`WREG32` en GFX8 **no** escribe un registro. Es un acceso al **banco CP_RB**,
con el número de registro codificado en la propia macro. `WREG32_SOC15` de
gfx9/10 hace lo mismo y se le pasa el banco explícitamente.

Lo que se ve:

- **GFX8** usa `WREG32(REG, valor)`: el banco es implícito.
- **GFX9 en adelante** usa `WREG32_SOC15(GC, 0, REG, valor)`: el banco es
  explícito.

Eso es una diferencia **de acceso**, no de hardware. GFX8 no tiene SOC15, que es
la infraestructura de registros deNavi/Vega10 en adelante. `WREG32_SOC15` es
literalmente la macro que GFX8 no puede usar.

**Para un driver propio:** en GFX8 hay que usar `WREG32` con los `mm*` del banco
CP_RB. Copiar la forma de Vega (`WREG32_SOC15`) no compila contra GFX8, y si se
"adapta" a mano es fácil equivocarse de banco, que produce escrituras a un
registro equivocado sin error visible.

## El WPTR_POLL: qué es

El par `WPTR_POLL_ADDR` + `WPTR_POLL_CNTL` es el mecanismo por el que el
hardware de graphics **notifica que el ring está lleno**, para que el driver
pueda insertar un fence. Es lo que permite que el CP no escriba más allá de lo
que el buffer tiene.

En GFX8 (`gfx_v8_0.c:4263`):

```c
WREG32(mmCP_RB_WPTR_POLL_ADDR_LO, lower_32_bits(wptr_gpu_addr));
```

y el registro de control, `gfx_v8_0.c:3990`:

```c
WREG32_FIELD(CP_RB_WPTR_POLL_CNTL, IDLE_POLL_COUNT, 0x60);
```

Ese `0x60` es un **número de comandos**, no un intervalo de tiempo.
`IDLE_POLL_COUNT` es la frecuencia con la que el ME comprueba si el ring está
lleno.

Y aquí hay que ser preciso con lo que dice el corpus, porque **el valor cambia
con la generación**:

```
gfx_v8_0.c:3990   WREG32_FIELD(CP_RB_WPTR_POLL_CNTL, IDLE_POLL_COUNT, 0x60)
gfx_v9_0.c:2962   /* init IDLE_POLL_COUNT = 60 */
gfx_v10_0.c:8037  /* set IDLE_POLL_COUNT(0x00900100) */
```

En gfx10 el comentario cita `0x00900100`, que es el campo entero con su
máscara, no `0x60` suelto. Puede ser la misma codificación vista de otra
manera, o un valor distinto. **No lo decido aquí**, y la razón está en la
sección siguiente.

Lo que sí se puede decir: `0x60` no es un intervalo de tiempo. Si lo fuera,
gfx9 y gfx10 lo habrían puesto distinto, y no lo han hecho. Es un conteo.

## Lo que NO se puede determinar

Que `IDLE_POLL_COUNT = 0x60` y que eso sea un conteo de paquetes está en el
código del driver, no en el hardware. **Si el hardware lo cuenta en paquetes o
en ciclos es `NOT_DETERMINED`.** Es la diferencia entre "cada 96 paquetes" y
"cada 96 ciclos", que afecta a cómo de rápido un ring lleno bloquea.

Con runtime se distinguiría leyendo `CP_RB_STATUS` con el poll puesto y sin
ponerlo, viendo si el conteo avanza con el trabajo emitido o con el reloj.

## Clasificación

| Afirmación | Estado |
|---|---|
| `WPTR_POLL_ADDR` se escribe y no se lee, en ninguna generación | **PROVEN** — enumeración |
| `WPTR_POLL_CNTL` **sí** se lee (RMENW en gfx7, gfx10) | **PROVEN** — `RREG32` en :3819 y :8038 |
| GFX8 usa `WREG32`, no `WREG32_SOC15` | **PROVEN** — `WREG32_SOC15` aparece en v9-v12 y 0 veces en `gfx_v8_0.c` |
| `IDLE_POLL_COUNT` se pone a `0x60` en GFX8 | **PROVEN** — `gfx_v8_0.c:3990` |
| Que `0x60` es un conteo y no un intervalo | **PROVEN_DERIVED** — si fuera tiempo, gfx9/gfx10 lo habrían cambiado |
| Que gfx10 usa el mismo valor o uno distinto | **NOT_DETERMINED** — `0x00900100` puede ser el campo con máscara o un valor distinto |
| Que el hardware lo cuente en paquetes o ciclos | **NOT_DETERMINED** |
| Que un valor de poll mayor dé más margen | **NOT_DETERMINED** — no hay lectura de `ADDR` |

La ausencia de lectura es lo que hace que esto sea `NOT_DETERMINED`: sin
observable, el corpus no puede decir qué hace el hardware con el valor.

## Reproducir

```sh
./causa.py mapa mmCP_RB_WPTR_POLL_ADDR_LO
./causa.py descubrir gfx_v8_0
./cidx.py use WREG32_SOC15      # no existe en GFX8
```

Sin root. `GPU INTACTA`, `WRITE_EXECUTION NONE`.