# 005 — Amendment: Citación de procedencia para datos cruzados

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 7
**Tipo**: regla de equipo, no de proceso
**Estado**: `DECIDIDO`

---

## 1. Qué problema resuelve

Tres IAS escribiendo en paralelo en un mismo árbol `git`. Los conflictos de **fichero** los
resuelve `git merge`. Los de **contenido** no.

Ejemplo real de este proyecto:

> IA-3 escribe «el blob mide 12 692 B», tomado de un documento de IA-1.
> IA-2 lo descomprime y el resultado son 12 700 B.
> `git merge` no dice nada. **El documento de IA-3 queda mintiendo y nadie se entera.**

Ese es el fallo. No es raro: es el comportamiento normal cuando varias personas toman notas
sobre el mismo tema y no se citan entre sí.

## 2. La regla

> **Un dato que provenga del trabajo de otra IA debe citarse con su commit de origen.**
>
> Si no lo mediste o verificaste tú mismo en esta ronda, **no lo escribas como hecho absoluto** en
> tu documento.

Forma correcta:

```
Según IA-1 (commit abc123), el blob ocupa 12 692 B.
No he verificado ese tamaño yo mismo; si cambió, este documento está obsoleto.
```

Forma incorrecta:

```
El blob mide 12 692 B.
```

La segunda forma es la que falla sin ruido. La primera falla **ruidosamente**: quien la lee sabe
que hay que ir a comprobarlo.

## 3. Tres grados, no dos

No todo tiene el mismo riesgo. La regla distingue:

| Grado | Qué es | Cómo se escribe |
|---|---|---|
| **Medido por mí** | lo verifiqué en esta ronda | afirmación directa, con el comando que lo demuestra |
| **Citado** | viene de otra IA | «Según IA-X (commit `abc123`), …» |
| **Supuesto** | nadie lo ha medido | `NOT_DETERMINED`, con la razón |

El tercero es el que se olvida y es el que más caro sale. `F4-AD-22` ya lo exige para capacidades
del host; aquí se extiende a **cualquier dato**.

## 4. Ejemplos reales de este proyecto

| Dato | Grado | Cómo se cita |
|---|---|---|
| `VK_FORMAT_BC3_UNORM_BLOCK = 137` | **medido por mí** | `vulkan_core.h:1945`, Vulkan 1.4.341 |
| `.text` del decodificador = 0x0aac B | **medido por mí** | `llvm-objdump-22 -h d.o` |
| blob SDMA = 12 692 B | **citado** | Según IA-2 (`e4e9c7d`); medido por mí: 12 692 B, sha256 `e27b3ec9…` |
| conjunto de reubicaciones que **necesita el hardware** | **supuesto** | `NOT_DETERMINED`, pendiente de `P-6` |
| `PGM_RSRC1` en `gfx_8_0_d.h` | **medido por mí** | el fichero existe y contiene el símbolo |
| offset de `PGM_RSRC1` correcto para Polaris 12 | **supuesto** | `NOT_DETERMINED` |

**El caso del blob es el ejemplo bueno**: lo cita IA-2, y además yo lo verifiqué, así que el
documento dice las dos cosas y queda claro cuál es cuál.

## 5. El aviso que hoy está costando tiempo

Esto no es teórico. En este proyecto, dos veces un dato quedó obsoleto sin que nada lo indicara:

| Qué pasó | Consecuencia |
|---|---|
| `b8294b1` afirmaba que la ruta de cómputo Vulkan no funcionaba | **falso**: era un bug mío de structs, no del driver. Corregido en `AD-14` |
| `test_alpha_ramp` afirmaba conformidad con bcdec | AD-11 cambió la regla de la rampa y `test_alpha_ramp` quedó obsoleto |

En ambos casos el documento se queda con toda la confianza y sin ninguna marca de que su premisa
había caducado. **Un hash de commit es la marca de caducidad**: si el commit que citaste cambió,
tienes que revisarlo.

## 6. Cómo se aplica en la práctica

**Al escribir un documento de arquitectura**: todo dato de otra IA va con commit.

**Al revisar un documento de otra IA**: si un dato va sin commit, es una afirmación, no un dato
verificado. Trátalo como hipótesis.

**Al terminar un turno**: `git log` sobre los ficheros que he citado. Si alguno cambió desde que
lo escribí, o corrijo la cita o la marco como obsoleta. Esto son treinta segundos.

## 7. Lo que esta regla NO es

- **No** es burocracia de proceso. No requiere ceremonies, ni turnos, ni esperas.
- **No** impide trabajar en paralelo. Solo cambia una línea de cómo se escribe un dato.
- **No** sustituye a medir. Solo hace visible cuándo un dato no se ha medido.

Es la única defensa posible contra la contradicción silenciosa: `git merge` detecta ficheros,
`grep` no detecta mentiras.

## 8. Aplicación inmediata

Al retirar el cerrojo del protocolo, **esta regla se queda**. Es lo que impide que el trabajo en
paralelo produzca un repositorio lleno de afirmaciones que nadie puede fechar.

## 9. Referencia

Reglas relacionadas:

- `F4-AD-22` — medir antes de aceptar la premisa (capacidades del host)
- `F4-AD-23` — el probe aborta si no encuentra el dispositivo objetivo
- `AGENTS.md` §Evidencia — vocabulario de estados; esta regla es su versión operativa para datos
  cruzados entre IAS
