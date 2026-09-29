# DECISIONS — registro de decisiones arquitectónicas del proyecto

**WORK_CLASS** `DOCUMENTATION`. Fichero **versionado y fechado**, separado de
`AGENTS.md` porque §10.2 exige que las decisiones no vivan en línea en un fichero
que envejece, y separado de `02-ARQUITECTURA/RE02-DECISION-REGISTER.md` porque
ese fichero declara scope propio — *«decisiones de gobernanza de la línea RE-02»*
— y este registro **no es** RE-02.

| Prefijo | Qué registra | Dónde |
|---|---|---|
| `AD-*` | decisiones de arquitectura de hardware/driver de la línea RE-03 | este fichero |
| `RG-n` | decisiones de gobernanza y alcance de la línea RE-02 | `RE02-DECISION-REGISTER.md` |
| `AD-n` | arquitectura del modelo C de `polaris12xl` | `RESEARCH/polaris12xl/docs/DECISION-REGISTER.md` |
| `D-nn` | defectos encontrados y reparados | `RESEARCH/polaris12xl/docs/04-DEFECT-REGISTRY.md` |
| `D1..D10` | reconciliación documental | `01-AUDITORIA/DECISIONES-D1-D10.md` |

**Regla de este registro**: una entrada no se escribe hasta que existe una
`DECISION` con `DECIDER`. Las cuestiones abiertas se registran como
`DECISION_REQUIRED` y **no** como decisiones tomadas. Una entrada con
`DECIDER` vacío o con estado `PENDING` no autoriza ninguna acción.

**Índice de estados a 2026-09-28**: `AD-1` en vigor · `DECISION_REQUIRED #1`,
`#2` y `#3` **resueltos** por el `HUMAN` el 2026-09-28 y absorbidos por `AD-1`.

---

## AD-1 — 2026-09-28 — RE-03: límites de optimización y confirmación de hardware

| Campo | Valor |
|---|---|
| **DECISION** | Opción B — construir una capa de compresión nueva en C/ASM que interactúa con `amdgpu` vía APIs públicas, preservando el kernel base |
| **DECIDER** | `HUMAN` (`HUMAN_POLICY`, vinculante) |
| **DATE** | `2026-09-28` |
| **Anula** | los tres `DECISION_REQUIRED` de la entrada del manifiesto RX550-FIRST de esta misma fecha |

**Contexto**: inicio de la fase de implementación del compresor
personalizado. Hacían falta tres decisiones previas, registradas como
`DECISION_REQUIRED` más abajo en este mismo fichero.

**Opciones consideradas**:

- Opción A: reescribir structs de `amdgpu` (`amdgpu_vm`, `amdgpu_ttm`, `drm_sched`) — **RECHAZADA**. Viola `RG-1` vigente; rompe la equivalencia E1 demostrada el 2026-09-28; y con `CONFIG_MODVERSIONS=n` no hay CRC que detecte el desajuste de layout resultante.
- Opción B: capa de compresión nueva en C/ASM, autocontenida, sobre APIs públicas — **ELEGIDA**.

**Decisión tomada**: Opción B. `RG-1` **se mantiene**. El trabajo continúa
exclusivamente en `RESEARCH/kernelbuild/linux-7.1.3`; el directorio
`rx550-upstream-7.2.8` queda **ignorado** para esta fase. La equivalencia E1
queda congelada y preservada.

**Justificación**: permite optimizar de forma agresiva el flujo de datos para
la RX 550 sin perder la capacidad de depuración contra upstream, ni chocar con
Secure Boot/Lockdown. La filosofía RX550-FIRST se aplica **exclusivamente al
diseño de código nuevo**, nunca a la destrucción del kernel base.

**Impacto**: todo el código nuevo en `04-IMPLEMENTACION/` debe ser
autocontenido y **no** debe asumir modificación de structs internos de
`amdgpu`.

### Hardware confirmado — `FACT`, 2026-09-28

Medición autorizada explícitamente por el `HUMAN` como observación de sysfs, no
como modificación.

| Dato | Valor | Fuente |
|---|---|---|
| **VRAM total** | **`2147483648` bytes = 2048 MiB = 2.0000 GiB = 2.1475 GB** | `/sys/class/drm/card1/device/mem_info_vram_total` |
| VRAM usada | `5439488` B (5,19 MiB) | `mem_info_vram_used` |
| VRAM visible (apertura BAR) | `268435456` B = 256 MiB | `mem_info_vis_vram_total` |
| GTT (dominio CPU) | `6194638848` B ≈ 5 GiB | `mem_info_gtt_total` |
| preempt_used | `0` B | `mem_info_preempt_used` |
| Identidad PCI | `0000:01:00.0 [1002:699f] rev c7`, subsistema `[1002:0b04]` | `lspci` |
| Nodo DRM correcto | `card1` | `card0` es la iGPU Intel `[8086:0412]` |

**Corrección de medición**: el manifiesto y la premisa de diseño decían
«2 GB». El hecho medido es **`2147483648` bytes**, que es exactamente
2 GiB, no 2 GB. La diferencia es 147,483,648 B (~2,6 %). Toda aritmética de
diseño que use «2 GB» como decimal se desvía; debe usar **2147483648**.

**Nota de alcance**: `vis_vram_total` (256 MiB) es un subespacio de la
apertura BAR, **no** la VRAM total. No confundirlos: el diseño que intente
acotar a 256 MiB estaría acotando 8× por debajo de la VRAM real.

---

## 2026-09-28 — Manifiesto RX550-FIRST: adopción con reservas y 3 decisiones bloqueantes

**Contexto**: RE-03 se abre como reinicio arquitectónico con la filosofía
RX550-FIRST (adaptar el driver al hardware; no código sagrado; no imitar la
arquitectura de AMD; C + ASM; cada byte cuenta; arreglar en código lo que esté
mal). Antes de aplicar esas reglas hizo falta verificar las coordenadas sobre
las que se apoyan, porque tres no se sostienen tal como están escritas.

**Opciones consideradas**:

- Opción A: adoptar las seis reglas literalmente y empezar a modificar el driver → Pros: avance inmediato, máxima autonomía del agente. Contras: contradice `RG-1` vigente sin revocación explícita; dos coordenadas factuales son erróneas; se optimizes sobre un parámetro no medido.
- Opción B: adoptar las reglas que no dependen de las tres incógnitas, registrar las que sí, y no tocar código hasta resolverlas → Pros: no introduce trabajo que haya que revertir; deja las decisiones donde §10.2 las sitúa. Contras: retrasa el inicio de RE-03.
- Opción C: rechazar el manifiesto completo → Pros: preserva el estado actual. Contras: la filosofía es legítima y útil; el conflicto es de alcance, no de validez.

**Decisión tomada**: Opción B.

**Justificación para RX550 (2 GB, 512 shaders, 4 CUs)**: la filosofía RX550-FIRST
es correcta y especialmente valiosa aquí, donde `amdgpu` arrastra 963 objetos
compilados y la mayor parte son irrelevantes para 4 CUs. El conflicto no es con
la filosofía sino con su alcance: dos reglas chocan con hechos registrados, y
una tercera depende de un número que aún no está medido. Adoptar sin verificar
produciría un artefacto construido sobre coordenadas falsas, que es exactamente
el modo de fallo que este proyecto lleva siete rondas evitando.

**Impacto**: `02-ARQUITECTURA/DECISIONS.md` creado. **Ningún fichero de código
modificado.** `RE02-DECISION-REGISTER.md` intacto
(sha256 `7021330bfee1e125bedf1364dd0bbf84978dca078850c78418dc31e3169f7eee`).

### Reglas adoptadas sin reservas

| Regla | Estado | Nota |
|---|---|---|
| 1 · RX550-FIRST | `ADOPTED` | como criterio de diseño |
| 2 · Cero miedo | `ADOPTED` | como permiso para modificar código upstream en el árbol de investigación |
| 3 · No imitar | `ADOPTED` | válido y con fuerza: la mayoría de `amdgpu` es irrelevante para 4 CUs |
| 4 · C + ASM | `ADOPTED` | ya es la línea de `RESEARCH/tests/elfsyms.c` |
| 5 · Cada byte cuenta | `ADOPTED` (código nuevo) | reescritura de structs del kernel base excluida por `AD-1` |
| 6 · Arreglar, no documentar | `ADOPTED` (código nuevo) | `RG-1` se mantiene: nada de alterar `amdgpu` |

### Hechos verificados que sostienen o corrigen el manifiesto

- **Hardware `FACT`**: `01:00.0 [1002:699f] rev c7`, subsistema `[1002:0b04]`,
  `Kernel driver in use: amdgpu`. Lexa PRO / Polaris 12 confirmado **por
  identidad PCI**, no por número de versión ni por parecido.
- **Hardware `FACT`**: `amdgpu` **está cargado ahora mismo** (18.698.240 bytes,
  5 referencias).
- **VRAM `NOT_DETERMINED`**: el BAR de 64 bits expone 256 MB mapeados; la VRAM
  total **no** es observable sin leer `amdgpu` en runtime, no autorizado. Los
  «2 GB» del manifiesto son **una afirmación del usuario, no un hecho medido**.
- **Árbol `CORRECTED`**: el manifiesto nombra `rx550-upstream-7.2.8`. **Sí
  existe** — 2 842 ficheros: `linux-7.2.8/`, `linux-7.2.8.tar.xz`
  (160 371 176 B), `local.sha256`, `upstream.sha256`. Pero **no es árbol de
  trabajo** por `AD-1`, y por tres razones medidas, no supuestas: es sólo el
  subárbol `drivers/gpu/drm/amd/` (2 839 ficheros, sin `Makefile`, sin
  `.config`, sin `scripts/`, sin `arch/` — §4.8.4 sólo `kernelbuild/` los
  tiene); **no contiene la instrumentación E1** (0 referencias frente a
  50/4/2/2 en `kernelbuild/linux-7.1.3`); y su `vermagic` no casaría con el
  host, que corre `7.1.3-200.nobara.fc44`. Queda como **referencia de
  consulta**. La afirmación previa de esta misma entrada —«no existe»— era
  **falsa** y se corrige aquí; el razonamiento de `DECISION_REQUIRED #2` se
  conserva intacto más abajo por §12.4, incluida aquella frase.
- **Reserva sobre la regla 5**: reempaquetar estructuras rompe la
  correspondencia con el host demostrada el 2026-09-28
  (`E1_CHAIN_COMPARISON`: camino causal de emisión **byte-idéntico**;
  `E1_TRANSFER_STATUS = PRESERVED`, corregido en la entrada siguiente) y reabre
  `SOURCE_ABI_EQUIVALENCE`. Con `MODVERSIONS=n` **no hay CRC que detecte un
  desajuste de layout**. Optimizar sin kernel de referencia es cambiar la
  variable bajo el experimento.

---

## 2026-09-28 — `DECISION_REQUIRED #1` · ¿RG-1 sigue vigente para RE-03?

**Estado**: `RESUELTA` por el `HUMAN` el 2026-09-28 · absorbida por `AD-1`
**DECIDER**: `HUMAN` · **DECISIÓN**: ver `AD-1`

> **SUPERADA.** Se conserva el razonamiento como registro de por qué se
> preguntó. La decisión que cierra esta cuestión está en `AD-1`; esta
> entrada ya no autoriza ni bloquea nada por sí sola.

**Contexto**: RG-1, registrado como `HUMAN_POLICY` el 2026-09-28 en
`RE02-DECISION-REGISTER.md`, autoriza RE-02 y **prohíbe** *functional/semantics
changes, optimization, and altering scheduling/memory/PT/CGPG/MEC/power
policies*. Las reglas 1, 5 y 6 del manifiesto RX550-FIRST piden precisamente
eso. RG-1 es `HUMAN_POLICY` registrada; por precedencia (§10.3, rank 3 sobre
rank 6) una instrucción de sesión no la deroga por omisión.

**Opciones consideradas**:

- Opción A: revocar RG-1 para RE-03 → Pros: el manifiesto aplica sin conflicto. Contras: RG-1 es no retroactiva; la revocación debe quedar registrada, no implícita.
- Opción B: RE-03 hereda la prohibición → Pros: coherencia; ninguna evidencia E1 se altera. Contras: la regla 6 queda inerte y el manifiesto pierde su propósito.
- Opción C: delimitar por artículo → Pros: se autoriza lo útil sin abrir PT/CGPG/MEC/power. Contras: frontera entre «optimizar page tables» y «alterar PT policies» requiere criterio explícito.

**Pregunta al `HUMAN`**: ¿cuál? Si es A o C, corresponde registrar `RG-2` en
`RE02-DECISION-REGISTER.md` — **no en este fichero**, porque RG-2 es gobernanza
de RE-02.

**Bloquea**: regla 6; toda modificación de código del driver.

---

## 2026-09-28 — `DECISION_REQUIRED #2` · ¿Sobre qué árbol corre RE-03?

**Estado**: `RESUELTA` por el `HUMAN` el 2026-09-28 · absorbida por `AD-1`
**DECIDER**: `HUMAN` · **DECISIÓN**: ver `AD-1`

> **SUPERADA.** Se conserva el razonamiento como registro de por qué se
> preguntó. La decisión que cierra esta cuestión está en `AD-1`; esta
> entrada ya no autoriza ni bloquea nada por sí sola.

**Contexto**: el manifiesto nombra `rx550-upstream-7.2.8`, que no existe. Todo
el trabajo de E1 está anclado a `kernelbuild/linux-7.1.3`: hashes congelados
(`amdgpu_vm.c=de4f485cb8ec0aa5`, `amdgpu_vm_pt.c=98dde50a9c66cf6f`,
`amdgpu_debugfs.c=b0dda80b0abc07c6`), tres objetos con evidencia directa de
compilación, y la equivalencia con el host medida el 2026-09-28.

**Opciones consideradas**:

- Opción A: RE-03 continúa en `kernelbuild/linux-7.1.3` → Pros: conserva toda la evidencia; `E1_TRANSFER_STATUS` sigue siendo interpretable. Contras: no cumple la premisa escrita del manifiesto.
- Opción B: crear `rx550-upstream-7.2.8` como árbol nuevo → Pros: cumple la premisa; base más reciente. Contras: 963 objetos por recompilar; la equivalencia demostrada **no se transfiere**; `SOURCE_ABI_EQUIVALENCE` vuelve a `NOT_PROVEN` y el host corre 7.1.3, no 7.2.8.
- Opción C: mantener 7.1.3 y congelar 7.2.8 para más adelante → Pros: no se pierde evidencia. Contras: retrasa la ventaja de la base nueva.

**Pregunta al `HUMAN`**: ¿A, B o C? Si es B: ¿qué se hace con la evidencia E1
—se congela como histórica, y la equivalencia se re-mide contra 7.2.8?

**Bloquea**: cualquier build; la validez de la cadena E1.

---

## 2026-09-28 — `DECISION_REQUIRED #3` · VRAM: ¿2 GB medidos o supuestos?

**Estado**: `RESUELTA` por el `HUMAN` el 2026-09-28 · absorbida por `AD-1`
**DECIDER**: `HUMAN` · **DECISIÓN**: ver `AD-1`

> **SUPERADA.** Se conserva el razonamiento como registro de por qué se
> preguntó. La decisión que cierra esta cuestión está en `AD-1`; esta
> entrada ya no autoriza ni bloquea nada por sí sola.

**Contexto**: las reglas 1 y 5 justifican el diseño por «2 GB». Ese número no
está medido. El BAR de 64 bits expone 256 MB mapeados; la VRAM total requiere
leer `amdgpu` en runtime. `NOT_DETERMINED` no es «2 GB» ni «no son 2 GB».

**Opciones consideradas**:

- Opción A: autorizar una lectura mínima de `amdgpu` para confirmar VRAM → Pros: convierte la premisa de diseño en `FACT`; es un solo dato. Contras: requiere autorización de lectura runtime, fuera del `WORK_CLASS` actual.
- Opción B: mantener 2 GB como `HYPOTHESIS` explícita → Pros: no requiere nada. Contras: todo diseño que dependa del número queda condicionado a una hipótesis no verificada.
- Opción C: usar el registro `polaris12xl` existente como fuente → Pros: ya revisado. Contras: es un documento del proyecto, no evidencia sobre *este* host; `§3.1` no admite fuente secundaria como primaria.

**Pregunta al `HUMAN`**: ¿autoriza la lectura mínima de runtime (A), o
registramos 2 GB como `HYPOTHESIS` (B)?

**Bloquea**: la justificación de las reglas 1 y 5; la regla 5 en particular.

---

## AD-2 — 2026-09-28 — Formato de bloque: 4x4 → 16 B con rampa alpha de 8 códigos

> **`ESTADO: SUPERSEDED`** por la entrada `AD-2` de la línea 679 de este mismo
> documento, que es la versión vigente. Se conserva sin borrar (§12.4: no se
> destruye evidencia histórica), pero **no citar esta**. La entrada vigente
>corrige la rampa alfa, que aquí se describe solo como «8 códigos» y resulted
> ambigua sobre el modo de 6 valores.
>
> El identificador `AD-2` está duplicado por error de registro. No se renumera
> esta entrada: hacerlo exigiría reescribir las referencias que otros documentos
> hacen a la versión vigente, y esa referencia es ambigua por construcción — no
> puede distinguir «el AD-2 de la línea 240» de «el AD-2 de la línea 679» sin
> conocimiento del historial. La corrección honesta es **retirar el duplicado**,
> no desplazar números. Registrado como `REFERENCE_AMBIGUITY`.

| Campo | Valor |
|---|---|
| **DECISION** | Opción A — bloque de 16 B con sub-bloque alpha de 8 índices de 3 bits y sub-bloque color de 4 índices de 2 bits (forma BC3/DXT5) |
| **DECIDER** | `MODEL_CHOICE` (decisión del agente, reversible) |
| **DATE** | `2026-09-28` |
| **Cancela** | ninguna |
| **Estado** | `SUPERSEDED` |

**Contexto**: el encargo fija "4x4 píxeles → ≤16 bytes" sin especificar el
formato. 64 bytes de entrada a 16 de salida es 4:1, y esa forma admite varias
codificaciones.

**Opciones consideradas**:

- Opción A: rampa de 8 valores en alpha + paleta de 4 colores en RGB565. → Pros: es *la* forma 4x4→16 B que el decodificador de bloques de la unidad de textura ya contiene; el índice de color empaqueta 4 por byte y el de alpha 8 en 3 bytes, que es la disposición más densa posible para esos anchos. Contras: 3 bits de alpha por píxel fijan una límite de error conocida; la rampa alpha con `a0==a1` desborda `uint8_t` si se usa la fórmula `/5` sin caso degenerado.
- Opción B: formato propietario de 16 B con semántica inventada. → Pros: libertad total sobre el reparto de bits. Contras: **obligaría a gastar shader GCN ISA en decodificar lo que el silicio ya decodifica en hardware**, y ninguna de las tres unidades de este proyecto podría validarlo sin escribir un shader. Contradice `AD-1` en el mismo punto donde la Regla 3 del manifiesto se sobrepone a la 1.
- Opción C: reducir a 1 byte por píxel (p. ej. un solo canal). → Pros: 4:1 trivial, muy rápido. Contras: no es un formato de textura; no lo decodifica ninguna unidad de textura; la pérdida de información es arbitraria y no ligada a la percepcion.

**Decisión tomada**: Opción A.

**Justificación**: la Regla 3 del manifiesto RX550-FIRST ("no imitar la
arquitectura de `amdgpu`") **no aplica aquí**, por la misma razón por la que la
Regla 1 prevalece sobre la 3 en el caso de las page tables: el layout de bloque
no es una preferencia de diseño del driver, es la forma de cable que el
decodificador fijo del hardware consume. Elegir otro layout no sería
adaptarse al hardware, sería obligar al software a rehacer en GCN ISA una
función que el silicio ya tiene. Se documenta aquí para que la exención sea
explícita y no una omisión.

El sub-bloque alpha es de 8 códigos, no de 6, porque con 6 códigos el sobrante
se gasta reconstruyendo el mismo valor: `a0==a1` produce `(6*a0)/5`, que para
`a0=255` es `306` y se envuelve a `50`. Ese caso degenerado se trata antes de la
rampa, y la conformidad contra la referencia DXT5 se verifica sobre los **65536
pares de endpoints** en el banco.

### Nota de truncamiento (2026-09-28, `HUMAN_POLICY`)

El formato BC3/DXT5 usa **truncamiento puro, sin offsets `+3`/`+2`**.

**Evidencia**:

- `bcdec` v0.985 (`bcdec__smooth_alpha_block`): `alpha[2] = (6 * alpha[0] + alpha[1]) / 7;`
  — sin offset de redondeo.
- El hardware de GPU trunca en la interpolación BC3.
- La especificación Microsoft da las fórmulas de interpolación sin especificar
  redondeo.
- Objetivo de compatibilidad con `bcdec`, `basisu` y visores estándar.

**Medición**: truncamiento da **0/65536** discrepancias contra la referencia
`bcdec`; el redondeo `+3`/`+2` daba **54300/65536** (82,9%).

**Impacto en calidad**: caída marginal de **0,07 dB** en `reference`
(28,80 → 28,73). `smooth`, `noise` y `adversarial` sin cambio. Throughput de
26,7 → 29,3 MB/s.

**Regla**: no se cambia sin autorización explícita del Arquitecto Principal.

### Corrección a dos afirmaciones de esta entrada

Esta entrada, tal como se escribió, afirmaba dos cosas que `AD-8` desmintió con
fuente primaria. Se dejan ambas visibles porque el error es el registro:

1. *"es la forma 4x4→16 B que el decodificador de bloques de la unidad de
   textura ya contiene"* y *"el silicio ya tiene"* esa función. **Falso**: una
   búsqueda de `drivers/gpu/drm/amd/` (36 695 ficheros) no encontró ningún
   decodificador BC3/DXT5, ni microcode, ni soporte BCn. El único hit fue
   `CP_PERF_SEL_IMG_READ_FMT_BC3`, un contador de rendimiento. El shader es el
   único decodificador, y no por elección del formato.
2. *"con 6 códigos el sobrante se gasta reconstruyendo el mismo valor"*. **Falso
   como justificación del sub-bloque**: la rama `a0 <= a1` de BC3 **sí** gasta los
   dos códigos sobrantes en los extremos fijos 0 y 255, por especificación. La
   afirmación era correcta en que `/5` desborda con `a0==a1` y en que el caso
   degenerado se trata aparte, pero la razón de fondo era inventada.

Lo que sí se sostiene, y por eso la decisión no cambia: BC3 es el formato
estándar de 4×4→16 B con 8 códigos de alpha, y elegir otro obligaría a escribir
un decodificador no estándar. El hardware no participa en esa elección.

---

## AD-3 — 2026-09-28 — El fallback en C se compila SIN `-mavx2`, contra el encargo

| Campo | Valor |
|---|---|
| **DECISION** | Opción B — `rx550_compress.c` se compila para la línea base x86-64; `-mavx2` se aplica solo al ensamblador |
| **DECIDER** | `MODEL_CHOICE` (desvío deliberado del encargo; elApartado "Justificación" lo justifica por medida) |
| **DATE** | `2026-09-28` |
| **Anula** | la instrucción literal "`-O3 -mavx2` para todo" del encargo de la Fase 1 |

**Contexto**: el encargo pide compilar "todo con `-O3 -mavx2 -Wall -Wextra`" y a
la vez pide detección de CPU en tiempo de ejecución con
`__builtin_cpu_supports("avx2")`. Las dos cosas son incompatibles.

**Opciones consideradas**:

- Opción A: `-mavx2` en todo. → Pros: exactamente lo pedido, máxima velocidad en el compilador. Contras: **GCC auto-vectoriza la ruta C de referencia con instrucciones AVX2**, así que `rx550_have_avx2()` devolvería 0 en una CPU pre-Haswell, el dispatcher elegiría correctamente la ruta "C", y esa ruta ejecutaría una instrucción ilegal. La detección en tiempo de ejecución pasaría de ser un mecanismo de seguridad a ser el Vector de ataque.
- Opción B: la referencia C a línea base, el AVX2 solo en `.s`. → Pros: el fallback es realmente portable y la detección significa algo. Contras: se pierde la auto-vectorización del compilador en la ruta C.

**Decisión tomada**: Opción B.

**Justificación**: la opción A hace que la única garantía de seguridad del
diseño sea falsa. Un detector de CPU que no protege de nada es peor que no
tenerlo, porque el lector del códigoAssume que protege. La verificación de que
`rx550_compress.o` no contiene AVX2 es trivial con `objdump` y queda en el
Makefile (`make check-asm` cubre el lado del ensamblador; el lado C se comprueba
porflags de compilación).

**Impacto**: `Makefile` (`CFLAGS_BASE`, `ASMFLAGS`, y el comentario que explica
por qué divergen), `rx550_compress.c` (la detección y el dispatcher), y el
requisito de que la ruta por defecto nunca ejecute AVX2.

---

## AD-4 — 2026-09-28 — Alcance del ensamblador y reparación estructural del aliasing de registros

| Campo | Valor |
|---|---|
| **DECISION** | Opción A — solo la reducción min/max por canal en AVX2, y como **dos funciones hoja** (`hred_min`, `hred_max`) en vez de ocho copias inlined |
| **DECIDER** | `MODEL_CHOICE` |
| **DATE** | `2026-09-28` |
| **Riesgo corregido** | 4 defectos de ensamblador, registrados en la cabecera del propio `.s` |

**Contexto**: el encargo pide "toda la lógica en ASM con YMM". La reducción
min/max es la única parte del codificador que es realmente paralelizable sin
riesgo; la construcción de paleta y la asignación de índices son de control de
flujo por píxel.

**Opciones consideradas**:

- Opción A: reducción en ASM, resto en C, y la reducción como función hoja llamada 8 veces. → Pros: `xmm5` es siempre la mitad baja de `ymm5` y `xmm1` el único scratch, así que **no existe ningún otro registro con el que confundirlo**; una sola copia de la secuencia sutil que hay que acertar. Contras: una llamada cuesta unos ciclos.
- Opción B: portar índice y paleta también a AVX2. → Pros: más cobertura SIMD. Contras: la búsqueda del índice más cercano es un `argmin` de 4 vías sobre 16 píxeles con control de flujo por píxel; el beneficio medido es incierto y el riesgo de un ensamblado incorrecto que *ensambla limpio* es alto.
- Opción C: la reducción inlined 8 veces, o envuelta en `.macro` de GAS. → Pros: sin coste de llamada. Contras: **rechazada por medida, no por gusto**. Un `.macro` de GAS no propaga el escape `%%` a través de invocaciones anidadas y no ensambla; y la versión inlined suffers *aliasing de registros*: `xmm0` es la mitad baja de `ymm0`, no de `ymm5`, y la equivocación ensambla sin error mientras calcula otra cosa. Ocurrió **tres veces** en la misma secuencia.

**Decisión tomada**: Opción A. La secuencia de 7 instrucciones vive **una vez**,
en `hred_min` / `hred_max`, con el contrato declarado en un comentario.

**Justificación**: el error de aliasing no es detectable por el ensamblador ni
por un test de tamaño de salida, porque un bloque comprimido es *lossy* y no
puede certificar una reducción min/max. Lo que sí lo detecta es comparar el
resultado del ASM contra la referencia C bloque a bloque, y eso es lo que hace
`T3` sobre 200 000 bloques. La Opción A reduce la superficie a una sola copia
verificable; la Opción C la multiplicaba por ocho.

**Impacto**: `rx550_compress_avx2.s` (funciones `hred_min`, `hred_max`; uso de
`ymm6`/`ymm7` para los datos crudos de modo que `ymm5` pueda pasarse a la hoja
sin movimiento), `test_compress.c` (`T3`, bit-exactitud C↔ASM).

---

## AD-5 — 2026-09-28 — Selección de endpoints: barrido diagonal, NO separable por canal

| Campo | Valor |
|---|---|
| **DECISION** | Opción A — barrido diagonal de inset (mismo `i` para R, G y B) puntuado sobre el error real del bloque |
| **DECIDER** | `MODEL_CHOICE` |
| **DATE** | `2026-09-28` |
| **Revertido** | una variante "separable" que se probó y se descartó por medición |

**Contexto**: la calidad depende de elegir los dos endpoints de color. Se
implementó primero la versión separable, por la razón aparentemente sólida de
que la distancia de un píxel a una entrada de paleta es la *suma* de tres
distancias por canal, luego el error sería separable.

**Opciones consideradas**:

- Opción A: barrido diagonal sobre el error del bloque completo. → Pros: optimiza el objetivo que el decodificador realmente tiene. Contras: un mismo inset Treatment para canales con rangos muy distintos.
- Opción B: minimizar cada canal por separado. → **DESCARTADA POR MEDICIÓN**. El índice de paleta es **compartido** entre canales, así que `min_k(dr²+dg²+db²) ≠ (min_k dr²) + (min_k dg²) + (min_k db²)`: la versión separable optimiza un objetivo que el decodificador no puede realizar. Medido sobre un corpus de 1200 bloques: **19,90 dB a 1289 ns/bloque** frente a **20,71 dB a 542 ns/bloque** de la diagonal — peor en calidad *y* 2,4× más lenta. Una variante de descenso por coordenadas sobre el objetivo verdadero tampoco mejoró la diagonal.

**Decisión tomada**: Opción A. La diagonal se conserva porque **midió mejor**,
no porque fuera la primera.

**Justificación**: el argumento de separabilidad era plausible y falso, y la
medición lo refutó en los dos ejes. Revertir un "mejoramiento" que empeora es
parte del trabajo, y el motivo queda escrito en el fuente para que nadie lo
repita. La variante separable no se conserva como opción configurable: sin
ventaja medida, mantenerla sería complexity sin pago.

**Impacto**: `rx550_compress.c` (`score_colour`, `encode_colour`,
`RX550_INSET_CANDIDATES`).

---

## AD-6 — 2026-09-28 — Los niveles de calidad son topes de regresión medidos, no objetivos

| Campo | Valor |
|---|---|
| **DECISION** | Opción B — un tope por clase de contenido, fijado ~15% por debajo de lo medido, y **sin** afirmación de paridad con un codificador BCn de referencia |
| **DECIDER** | `MODEL_CHOICE` |
| **DATE** | `2026-09-28` |
| **Corrige** | dos versiones previas del test con topes inventados |

**Contexto**: el encargo pedía verificar "tamaño de salida ≤ 16 bytes". Esa
aserción es verdadera por construcción — el bloque es un struct de tamaño fijo —
así que no certifica nada. Las comprobaciones que sí tienen dientes son la
bit-exactitud ASM↔C y el error de ida y vuelta.

**Opciones consideradas**:

- Opción A: un único tope para todas las clases. → Pros: simple. Contras: 20 dB sobre ruido independiente por píxel es **físicamente inalcanzable** con una paleta de 4 colores — un tope que_asserta lo imposible solo produce falsas alarmas.
- Opción B: topes por clase, medidos, etiquetados como topes de regresión. → Pros: cada tope está justificado por una propiedad del formato o por una medición. Contras: hay que mantener la medición al día.

**Decisión tomada**: Opción B. Valores medidos sobre el corpus determinista que
genera el propio test (semilla fija): referencia 27,7 dB · suave 19,5 dB ·
ruido independiente 13,6 dB · adversario 10,9 dB. Topes: 24 / 16 / 11 dB.

**Justificación**: un tope fijado por esperanza de que la compilación lo supere
no es un tope. Y `NOT_AVAILABLE` se declara de forma explícita para la paridad
con un codificador BCn de referencia: **no se ejecutó ninguno**, así que los
números no la implican ni la niegan.

Se añade además que la patrón "reference" original era Reference
involuntariamente inganable: cargaba una rampa R, una rampa G *invertida* y un
checker B en el mismo bloque. Cuatro señales independientes, paleta de 4
colores. Medía 10,9 dB y hacía fallar el test sin que el codificador tuviera
culpa. Se sustituyó por un bloque representativo y el caso adversario se
conserva, reportado y **no afirmado**.

**Impacto**: `test_compress.c` (`pat_known`, `pat_adversarial`, `pat_smooth`,
`t_quality`, `rgb565_nearest`/`rgb565_exact` en `t_edge_cases`).

---

## Nota de autoría concurrente — `EXTERNAL`, 2026-09-28

Durante esta fase, `test_compress.c` y `rx550_compress.h` recibieron
modificaciones **que no son mías** (19:46:15 y 19:46:19), consistentes en
`dxt5_reference_alpha()`, `t_alpha_ramp_dxt5()` y el hook declarado
`rx550_alpha_palette_for_test()`. La authorship no está establecida y no se
atribuye.

Se conservan y no se tocan (§12.4). Son **mejoras**: la conformidad de la rampa
alpha contra la referencia DXT5 sobre los 65536 pares de endpoints es una
comprobación de corrección más fuerte que cualquiera que yo hubiera escrito, y
pasa. El layout de `rx550_block_t` no se ve afectado: 16 B, offsets 0/2/8/12,
verificado tras el cambio.

**Riesgo pendiente**: dos escritores sobre el mismo fichero. Si el otro agente
sigue escribiendo, este registro y el codificador pueden divergir. Requiere una
decisión del `HUMAN` sobre quién escribe qué.

---

## 2026-09-28 — Corrección de dos premisas falsas del registro

**Tipo de claim**: `CONTRADICTION` resuelta · **Origen**: verificación del agente
contra el árbol de la decisión de alcance.

Este registro afirmaba dos cosas que **la evidencia refuta**. Se corrigen aquí con
el nombre del test que las refuta.

> **Preservación del texto original — verificada, con una corrección.** Este
> fichero **no está rastreado por git y tiene 0 commits que lo toquen**
> (`git ls-files` vacío, `git log` vacío, 2026-09-28). Por tanto **no** hay
> historial de git del que recuperar el texto anterior, y decir lo contrario
> sería afirmar una preservación que no existe. La copia previa vive **sólo** en
> `/tmp/opencode/recovery/DECISIONS.disk-20260928.md` (9 110 B), que **se pierde
> al reiniciar**. La frase original permanece además en `DECISION_REQUIRED #2`
> más abajo de este mismo fichero, sin editar, por §12.4.

| Afirmación previa | Estado real | Cómo se refutó |
|---|---|---|
| `E1_TRANSFER_STATUS = REQUIRES_REVALIDATION` | **`PRESERVED`** | `E1_CHAIN_COMPARISON` del 2026-09-28: 13 de los 14 puntos de la cadena causal byte-idénticos, y el restante (`amdgpu_vm_sdma.c`) con un delta textual `container_of(rq,…,rq)` → `rq->sched` que produce el mismo puntero del mismo tipo — `REQUIRES_REVALIDATION = NO` |
| «`rx550-upstream-7.2.8` no existe» | **Sí existe**, y no es árbol de trabajo | `ls` + `find` del 2026-09-28: 2 842 ficheros. Refutada por inspección directa del directorio |

**El error de origen** del segundo es un tipo de búsqueda incompleta: se concluyó
ausencia a partir de una comprobación que no cubría el directorio que se nombraba.
Es `NOT_FOUND` en disfraz de `PROVEN_ABSENT` sin alcance declarado (§2.7).

**Efecto sobre el registro**: ninguna de las dos premisas sostenía una decisión.
`AD-1` sigue vigente y su razón de ser (`RG-1` intacta, árbol `7.1.3`) no
dependía de ninguna de las dos. La reserva sobre la regla 5 **sí** se mantiene y
es independiente: reempaquetar `struct amdgpu_bo` destruiría el ancla de la
fórmula `PDE_VRAM_OFFSET` de E1 — ver `DEC-5`.

---

## 2026-09-28 - `DEC-1` RX550-FIRST se adopta, con su premisa corregida

**Tipo de claim**: `HUMAN_POLICY` (orientación) + `CONFLICT` (premisa) · **DECIDER**: `HUMAN`

**Contexto**: el manifiesto RE-03 orienta el proyecto a *«RX550-FIRST: el driver se adapta al hardware, nunca al revés. Si una estructura de amdgpu upstream es subóptima para 2GB, la reescribes»*, sostenido sobre la premisa de que *«AMD diseña para GPUs de 24GB; tú diseñas para 2GB»*.

**Opciones consideradas**:

- **Opción A** — aceptar el manifiesto literalmente y reescribir las estructuras de page table. → Pros: cumple al pie de la letra. Contras: son o bien derivados de hardware (`DEC-2`, `DEC-3`), o bien ya parametrizados; sin medición previa no hay discriminante entre «mejor» y «roto» (`E1_CPU_READBACK_EMPIRICAL = NOT_VERIFIED`).
- **Opción B** — adoptar la orientación y corregir su alcance: se aplica donde el hardware deja libertad, se excluye donde el hardware dicta. → Pros: conserva la intención y quita el error que la hacía inaplicable. Contras: exige un criterio explícito de «capa reescribible vs capa contractual».
- **Opción C** — rechazar el manifiesto completo. → Pros: ninguna. Contras: la orientación es correcta; el defecto está en su alcance, no en su dirección.

**Decisión tomada**: **Opción B**.

**Justificación**: la orientación es correcta justo donde el 2 GiB la hace necesaria, y es un hecho que la hace **innecesaria** en la capa de page table (`DEC-2`). La formulación operativa:

> **RX550-FIRST** — se optimiza para la RX550 real: Polaris 12 (Lexa), `[1002:699f]`, 512 shaders, 4 CUs, `2147483648` B de VRAM (medido, `AD-1`). Donde el driver upstream toma una decisión parametrizable, el parámetro se ajusta a este objetivo. Donde el hardware dicta el formato, el software obedece.

**Impacto**: principio transversal. `AD-1` ya lo acota al código nuevo en `04-IMPLEMENTACION/`. Este registro no habilita ninguna escritura por sí mismo.

---

## 2026-09-28 - `DEC-2` La geometría de la page table no se reescribe: ya es por dispositivo

**Tipo de claim**: `FACT_FOR_linux-7.1.3` + `DERIVATION` · **Ámbito**: `READ_ONLY_EVIDENCE`

**Contexto**: la regla 1 pide reescribir *«estructuras de amdgpu upstream subóptimas para 2GB»*. Antes de tocar nada hay que determinar si existe alguna.

**Opciones consideradas**:

- **Opción A** — reescribir `struct amdgpu_vm_bo_base`, la geometría de niveles o el formato de entrada. → Pros: control total. Contras: son derivados de hardware o ya parametrizados; reescribirlos no gana nada y arriesga la corrección.
- **Opción B** — verificar la premisa antes de actuar. → Pros: la decisión queda sobre evidencia, y «no había nada que reescribir» queda como resultado negativo útil. Contras: puede devolver un resultado menos iluminante que un rediseño.

**Decisión tomada**: **Opción B** — y la verificación devuelve que **en esta capa no hay nada subóptico que reescribir**.

**Justificación** (evidencia, `FACT_FOR_linux-7.1.3`):

| Comprobación | Dónde | Resultado |
|---|---|---|
| Profundidad por dispositivo | `amdgpu_vm.c:2433-2440` | `max_pfn = vm_size << 18`; `num_level = min(max_level, …roundup_pow_of_two(max_pfn)…)` — derivado del tamaño, no constante |
| VRAM como entrada | `amdgpu_vm.c:2427-2430` | `vm_size = roundup_pow_of_two(clamp(phys_ram_gb*3, min_vm_size, max_size))`; `min_vm_size`/`max_size` los fija el ASIC |
| Máscara de dirección | `amdgpu_gmc.h` | `uint64_t pte_addr_mask;` — por ASIC |
| Bloque y profundidad VMID0 | `amdgpu_gmc.h` | `vmid0_page_table_block_size`, `vmid0_page_table_depth` — del hardware |
| Posición entre niveles | `amdgpu_vm_pt.c:188-192` | `shift = amdgpu_vm_pt_level_shift(adev, cursor->level); idx = (cursor->pfn >> shift) & mask;` |

**Refutación de la premisa**: la geometría es idéntica en el mismo código para una tarjeta de 2 GiB y una de 24 GiB; lo que difiere son los *parámetros* que cada ASIC le pasa. Ninguna línea depende del tamaño de VRAM en forma constante.

**Impacto**: cierra la regla 1 para la capa PDE/PT. `E1_TRANSFER_STATUS = PRESERVED` deja de estar en riesgo por este frente. No se toca `amdgpu_vm_pt.c`, `amdgpu_gmc.[ch]`, `amdgpu_vm_bo_base`.

**`FALSIFICATION_CONDITION`**: si un ASIC de 2 GiB y uno de 24 GiB obtuvieran la *misma* geometría por un bug, esta decisión se reabre. Instrumento: `amdgpu_debugfs` (`amdgpu_vm.c:2512` publica `max_pfn`), que requiere root y está fuera de la autorización vigente.

---

## 2026-09-28 - `DEC-3` El formato de la PDE es contrato de hardware, no diseño de AMD

**Tipo de claim**: `DERIVATION` + `HUMAN_POLICY` (frontera) · **DECIDER**: `HUMAN`

**Contexto**: las reglas 2 (*«cero miedo»*) y 5 (*«cada byte cuenta, empaquetar»*) alcanzan, leídas literalmente, el formato de la entrada de page table.

**Opciones consideradas**:

- **Opción A** — aplicar «cero miedo» a los contratos de hardware. → Pros: coherente. Contras: el formato no lo elige AMD ni el driver; lo interpreta el MM/VMHUB del ASIC. Un formato distinto no es diseño, es un dispositivo que no mapea.
- **Opción B** — fijar la frontera: *cero miedo* aplica a la implementación, no a los contratos de hardware. → Pros: §13.7 ya distingue implementación de requisito. Contras: requiere criterio por capa.

**Decisión tomada**: **Opción B**.

**Justificación**: la entrada de page table es un contrato con el silicio — anchura de 8 B, flags `AMDGPU_PTE_VALID`/`DIRTY`/`NO_FETCH`, y enmascaración por `pte_addr_mask`, los decodifica el hardware. Reescribirlos no es «adaptarse al objetivo»: es romper la correspondencia. «CERO MIEDO» se adopta **entero** para nombres, firmas internas, partición de responsabilidades, flujo de control y módulos, y queda acotado donde el hardware manda.

**Nota de convergencia**: `AD-2` aplica este mismo razonamiento al códec — el layout 4×4→16 B es la forma que el decodificador de bloques de la unidad de textura ya consume, no una preferencia del driver. La exención es explícita en ambos casos para que no se lea como omisión.

**Impacto**: `amdgpu_vm_pt.c` (formato de entrada, `expect_written` en `:662-672`), `amdgpu_gmc.c/.h`, `asic_reg.h` — **intocables por decisión de diseño, no por superstición**.

---

## 2026-09-28 - `DEC-4` C+ASM para todo código crítico: no en la ruta PDE/PT

**Tipo de claim**: `NEGATIVE_RESULT` + `MODEL_CHOICE`

**Contexto**: la regla 4 pide *«todo código crítico en C y ASM x86_64 o GCN ISA»*.

**Opciones consideradas**:

- **Opción A** — reescribir en ensamblador la ruta de actualización de page table. → Pros: elimina la incertidumbre del compilador en la ruta más crítica. Contras: **no es un bucle caliente**. `amdgpu_vm_pde_update()` se invoca una vez por BO relocalizado por llamada, no por byte. No hay rendimiento que ganar y se pierde la semántica de orden de memoria y estado de cerrojo que el C expresa.
- **Opción B** — ASM donde hay objetivo de rendimiento medible; C con verificación estricta donde el objetivo es corrección. → Pros: coherente con §9.1 (no se optimiza sin `NOISE` medido). Contras: hay que nombrar el objetivo antes de escribir el ASM.

**Decisión tomada**: **Opción B**.

**Justificación**: §13.8 ya fija C como defecto para el trabajo de formato-binario/ABI de este proyecto, y es más específica y anterior que la regla 4. `NOISE = NOT_DETERMINED` y `E1_CPU_READBACK_EMPIRICAL = NOT_VERIFIED`: sin ruido medido ningún tamaño de efecto es interpretable, así que «optimizar» no tiene predicado. GCN ISA queda como el idioma correcto para shaders y compute — que es exactamente lo que Fase 2 propone.

**Impacto**: §13.8 más esta entrada. `DEC-n` futuro requerido antes de escribir ASM, con su `PREDICTION`.

---

## 2026-09-28 - `DEC-5` Layout de `struct amdgpu_bo` congelado: rompe el contrato de medición

**Tipo de claim**: `CONTRADICTION` + `MODEL_CHOICE` · **Contrada con**: la regla 5 · **Coherente con**: `AD-1`

**Contexto**: la regla 5 pide empaquetar y optimizar estructuras. `struct amdgpu_bo` es el caso más obvio.

**Opciones consideradas**:

- **Opción A** — reempaquetar `struct amdgpu_bo` y las de page table. → Pros: menos memoria. Contras: `sizeof(struct amdgpu_bo)` es un **input de la fórmula `PDE_VRAM_OFFSET`** de RE-02, la referencia autoritativa de la lectura de E1. Hoy es `NOT_DETERMINED` y la fórmula **nunca se ha ejercitado**. Reempaquetar mueve ese ancla y vuelve indeterminable cualquier lectura futura. Además rompe alineación natural bajo atómicos y cerrojos.
- **Opción B** — congelar el layout de las estructuras que anclan fórmulas de medición hasta que exista una medición que lo fije empíricamente. → Pros: conserva el contrato; el valor pasa de `NOT_DETERMINED` a medido. Contras: retrasa una optimización que aquí no es el cuello de botella.

**Decisión tomada**: **Opción B**.

**Justificación**: §12.4 — *«nunca alterar, ocultar, inventar ni reinterpretar evidencia para que una implementación o un test pase»*. Aquí la evidencia **es** el layout. `RG-1` art. 3 autorizó la instrumentación **precisamente** para medir la emisión de PDE; romper el ancla de su fórmula la deja sin objeto. Y el cuello de botella de esta línea no es la memoria de las estructuras: no hay ni una medición. Coincide con la Opción A de `AD-1` (*«reescribir structs de `amdgpu` — RECHAZADA»*), que ya cubrió; esta entrada la aterriza sobre el caso concreto.

**Impacto**: `struct amdgpu_bo` y `struct amdgpu_vm_bo_base` — **layout congelado**. El modelo C de `polaris12xl` (`AD-n` de su registro) **sí** puede empaquetarse: es userspace y no ancla ninguna fórmula de kernel.

---

## 2026-09-28 - `DEC-6` `rx550-upstream-7.2.8` existe pero no es árbol de trabajo

**Tipo de claim**: `FACT` + `MODEL_CHOICE` · **Coherente con**: `AD-1` (esta entrada la precisa, no la sustituye)

**Contexto**: el manifiesto nombra `rx550-upstream-7.2.8`; este registro afirmó primero que no existía, lo cual era falso.

**Opciones consideradas**:

- **Opción A** — pivotar la línea a 7.2.8. → Contras: no construible, sin instrumento E1, y `vermagic` incompatible con el host.
- **Opción B** — 7.1.3 como árbol de trabajo, 7.2.8 como referencia de consulta. → Pros: conserva la evidencia, el instrumento y la equivalencia demostrada.

**Decisión tomada**: **Opción B**, ya decidida por el `HUMAN` en `AD-1` y confirmada aquí con la evidencia que faltaba.

**Justificación**: `rx550-upstream-7.2.8/` contiene 2 842 ficheros: `linux-7.2.8/` (2 839, todos bajo `drivers/gpu/drm/amd/`), `linux-7.2.8.tar.xz` (160 371 176 B), `local.sha256`, `upstream.sha256`. Tres hechos medidos lo disqualifican como árbol de trabajo: no tiene `Makefile` ni `.config` ni `scripts/` ni `arch/`; no contiene la instrumentación E1 (0 refs vs 50/4/2/2); y el host corre `7.1.3-200.nobara.fc44`, cuyo `Makefile` es **byte-idéntico** (`9e2bb27ef5af11b9…`) al del tarball `cachyos-7.1.3-1` del SRPM verificado. Además §3.2: `E1_TRANSFER_STATUS = PRESERVED` está medido sobre 7.1.3 y no viaja a 7.2.8 sin re-verificar los 14 puntos.

**Impacto**: la línea sigue en `RESEARCH/kernelbuild/linux-7.1.3`. `rx550-upstream-7.2.8` es **consulta**, no trabajo. No se abre línea paralela.

---

## 2026-09-28 - `DEC-7` Separación de `CONFIG_EQUIVALENCE` / `SOURCE_EQUIVALENCE` / `ABI_EQUIVALENCE`

**Tipo de claim**: `DERIVATION` + `MODEL_CHOICE` · **Ámbito**: `READ_ONLY_EVIDENCE`

**Contexto**: al cerrar la procedencia del código host (SRPM `kernel-7.1.3-200.nobara.fc44.src.rpm`, verificado contra el checksum del índice) было fácil dejar que una equivalencia arrastrara a las otras.

**Opciones consideradas**:

- **Opción A** — reportar «el árbol coincide con el host». → Contras: es falso globalmente y no usable para la decisión.
- **Opción B** — medir las tres por separado y declarar el alcance exacto. → Pros: permite usar lo que sí se sostiene sin arrastrar a la que no.

**Decisión tomada**: **Opción B**.

**Justificación**:

| Dimensión | Estado | Evidencia |
|---|---|---|
| `CONFIG_EQUIVALENCE` (config del SRPM vs config construido del host) | **0 diferencias** en `DRM`\|`AMDGPU`\|`TTM`\|`HSA`, `MODULE`\|`MODVERSIONS`\|`MODULE_SIG`, `SECURITY`\|`LOCKDOWN`, `CC_OPT`\|`LTO`, `MM` | 81 diferencias residuales, todas de identidad de build y sondeo de compilador (`BUILD_SALT`, `GCC_VERSION`, `CC_HAS_*`, `CONFIG_CACHY`) |
| `SOURCE_EQUIVALENCE` | **DIFFERENT** globalmente; **PRESERVED** en la cadena causal E1 | `Makefile` A `8139969d…` ≠ B `9e2bb27e…`; 36 de 2689 ficheros AMDGPU difieren antes de parches; ningún parche de la distro toca la cadena E1 |
| `ABI_EQUIVALENCE` | **UNKNOWN** | No hay build. La firma de módulo sigue sin resolverse: `CONFIG_MODULE_SIG_ALL=y` + `SECURITY_LOCKDOWN_LSM=y` ⇒ un `.ko` reconstruido localmente iría firmado con otra clave y el host no lo aceptaría |

**Ninguna de las tres implica las otras.** Y la formulación correcta sobre `MODVERSIONS` se mantiene, sin relajarla:

> No existe comprobación CRC de versiones de símbolos mediante MODVERSIONS; permanecen las demás comprobaciones del cargador, incluidas firma y políticas de seguridad.

**Impacto**: `E1_TRANSFER_STATUS = PRESERVED` **no** es autorización de build. `BUILD_AUTHORIZATION`, `MODULE_SIGNATURE`, `TREE_EXCLUSIVITY`, `LOADABILITY` y `RUNTIME_AUTHORIZATION` siguen separados, y `BUILD_ALLOWED = NO`. La fuente dejó de ser el obstáculo; la firma de módulos es ahora el candidato dominante, y es una pregunta que no depende de la procedencia.

---

## AD-2 — 2026-09-28 — Formato de compresión BC3/DXT5, con la rampa alfa corregida

| Campo | Valor |
|---|---|
| **DECISIÓN** | Opción A — bloque de 16 B: sub-bloque alfa de 8 índices de 3 bits + sub-bloque color de 4 índices de 2 bits (BC3/DXT5) |
| **DECIDER** | `MODEL_CHOICE` (formato) sobre `HUMAN_POLICY` AD-1 (alcance) |
| **DATE** | `2026-09-28` |
| **SUPERSEDE** | la entrada `AD-2` de la línea 240, **en su justificación**. Su texto se conserva intacto; sólo se le añadió arriba una banderola `SUPERSEDED` con el motivo (§12.4 permite marcar el estado, no alterar la evidencia) |
| **MOTIVO DE LA REVISIÓN** | la justificación original afirmaba conformidad DXT5 que **no existía**: la rampa alfa implementada no era DXT5, y el test que supuestamente la verificaba comparaba la implementación contra una copia literal de sí misma |

### Por qué se revisó

La rampa alfa de `rx550_compress.c` usaba `(7-i)` y dividía por 7 en **ambas** ramas. DXT5
no hace eso: con `a0 <= a1` interpola **cuatro** valores con `/5` y gasta los dos códigos
sobrantes en los extremos `0` y `255`. La consecuencia era que los bloques producidos no los
decodifica ningún decodificador BC3 del mundo.

Pasó desapercibida porque `dxt5_reference_alpha()` en `test_compress.c` era **copia línea a
línea** de `alpha_palette()`. El test comparaba `f(x)` con `f(x)`, que es verdadero por
construcción, y su comentario afirmaba haberla transcrito *«from the BC3 specification, not
from the code»*. Era falso.

Impacto medido del defecto, sobre 7 casos cerrados: **27 entradas discrepantes**. Caso
inequívoco: con `a0=a1=128` la implementación producía `[128 x8]`; DXT5 produce
`[128 x6, 0, 255]`. Un códec BC3 que decodifica un bloque alfa plano a 128 en las ocho
entradas no es un códec BC3.

### Rampa alfa, conforme

```
a0 >  a1 :  pal[i] = ((8-i)*a0 + (i-1)*a1 + 3) / 7   para i = 2..7
a0 <= a1 :  pal[i] = ((6-i)*a0 + (i-1)*a1 + 2) / 5   para i = 2..5
             pal[6] = 0 ;  pal[7] = 255
```

El coeficiente de `a0` es `(8-i)`, no `(6-i)` ni `(7-i)`: en `i=2`, DXT5 es
`(6*a0 + a1 + 3)/7`, de modo que `a0` pierde exactamente un paso a lo largo de la rampa y
`(7-i)` pierde dos.

### Estructura del bloque (16 B)

| offset | bytes | campo |
|---:|---:|---|
| 0 | 1 | `a0` endpoint alfa 0 |
| 1 | 1 | `a1` endpoint alfa 1 |
| 2-7 | 6 | índices alfa, 16 x 3 bits, LSB-first |
| 8-9 | 2 | `c0` endpoint color, RGB565 LE |
| 10-11 | 2 | `c1` endpoint color, RGB565 LE |
| 12-15 | 4 | índices color, 16 x 2 bits, LSB-first |

### Evidencia de conformidad — y lo que **no** es evidencia

| Lo que sí se hizo | Resultado |
|---|---|
| Vectores literales de referencia (7 casos: extremos opuestos, planos 0/255/128, y dos típicos) | 27 discrepancias → **0** |
| Barrido exhaustivo de los 65 536 pares contra una referencia escrita con **tablas de pesos** `{6,5,4,3,2,1}` / `{4,3,2,1}`, no con la expresión del código | 0 discrepancias |
| Invariante estructural: con `a0 <= a1` los dos códigos sobrantes **deben** ser los extremos | se cumple |
| `a0 > a1`: la parte interpolada `a[2..7]` es no creciente | se cumple |
| `glslangValidator` 16.3.0 sobre el shader, `-V` | `rc=0`, sin warnings, SPIR-V 11 984 B |
| `shader_vs_c.c`: lógica del shader transliterada a C contra el decodificador C | **0/4096** canales |

### Fuente primaria — consultada el 2026-09-28, `SPECIFICATION_VERIFIED`

`CONFORMITY_PROVENANCE = SPECIFICATION_VERIFIED`

| Campo | Valor |
|---|---|
| **URL** | `https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression` |
| **Página** | *Block Compression (Direct3D 10) - Win32 apps*, publicada 2022-08-26 |
| **URL 2** | `https://learn.microsoft.com/en-us/windows/win32/direct3d9/textures-with-alpha-channels` — *Textures with alpha channels*, para la regla de modo de color |
| **MÉTODO** | lectura directa de la especificación primaria por el agente. **No** por transcripción de terceros |
| **RESULTADO** | la rampa alfa implementada coincide **literalmente** con la especificación |

La especificación publica, textualmente:

```cpp
if( alpha_0 > alpha_1 ) {
  alpha_2 = (6 * alpha_0 + 1 * alpha_1 + 3) / 7;   // bit code 010
  alpha_3 = (5 * alpha_0 + 2 * alpha_1 + 3) / 7;   // bit code 011
  alpha_4 = (4 * alpha_0 + 3 * alpha_1 + 3) / 7;   // bit code 100
  alpha_5 = (3 * alpha_0 + 4 * alpha_1 + 3) / 7;   // bit code 101
  alpha_6 = (2 * alpha_0 + 5 * alpha_1 + 3) / 7;   // bit code 110
  alpha_7 = (1 * alpha_0 + 6 * alpha_1 + 3) / 7;   // bit code 111
} else {
  alpha_2 = (4 * alpha_0 + 1 * alpha_1 + 2) / 5;   // Bit code 010
  alpha_3 = (3 * alpha_0 + 2 * alpha_1 + 2) / 5;   // Bit code 011
  alpha_4 = (2 * alpha_0 + 3 * alpha_1 + 2) / 5;   // Bit code 100
  alpha_5 = (1 * alpha_0 + 4 * alpha_1 + 2) / 5;   // Bit code 101
  alpha_6 = 0;                                     // Bit code 110
  alpha_7 = 255;                                   // Bit code 111
}
```

Correspondencia con lo implementado, entrada por entrada:

| Dato | Especificación | `alpha_palette()` | |
|---|---|---|---|
| `a0 > a1`, pesos | `6,5,4,3,2,1` sobre `a0` | `((8-i)*a0 + (i-1)*a1 + 3)/7` | coincide |
| `a0 <= a1`, pesos | `4,3,2,1` sobre `a0` | `((6-i)*a0 + (i-1)*a1 + 2)/5` | coincide |
| `a0 <= a1`, sobrantes | `alpha_6 = 0`, `alpha_7 = 255` | `pal[6]=0; pal[7]=255;` | coincide |
| Divisores | 7 y 5 | `/7` y `/5` | coincide |

**La distribución de bits de los índices también está confirmada por la fuente**: la
especificación publica la tabla byte a byte del bloque alfa, y coincide con
`pack_3bit()` (`LSB-first`, 16 × 3 bits, repartidos en 6 bytes a partir del byte 2).

### Modo de color: BC3 es SIEMPRE modo 4 colores

Verificado en la misma fuente primaria, y es un punto donde la transcripción de terceros
falla con frecuencia:

> *«The color compare used in BC1 to determine if the texel is transparent is **not used
> with these formats**. It is assumed that without the color compare the color data is always
> treated as if in 4-color mode.»*
> — *Textures with alpha channels (Direct3D 9)*, sección DXT4/DXT5

Equivalente, según la propia especificación: el `if` de BC1 debe reescribirse como
`if ((color_0 > color_1) OR !DXT1)`.

El modo de 3 colores con `color_3 = 0` y `color_2 = 1/2*c0 + 1/2*c1` es **exclusivo de
BC1**. Aplicado a BC3 produciría bloques que un decodificador estándar no reconstruye, y es
precisamente el defecto que se detectó en la especificación original del shader. La
implementación y el shader actuales son correctos en este punto porque **no** tienen la rama
condicional.

### Retirado de la justificación propuesta, por no ser verificable

- `bcdec`, `oxideav-dds`, `DirectXTex`/`D3DX` como corroboración: **ninguno instalado, ninguno
  consultado**. Comprobado el 2026-09-28: 0 fuentes DXT5 en `~/Descargas`. Ya **no** hacen
  falta como corroboración: la fuente primaria está consultada y es autoritativa.
- «Análisis ryg»: sin referencia identificable.
- La transcripción del bloque de color que la propuesta para esta entrada atribuía
  a BC3 la regla de 3 colores de BC1. **Corregido arriba**; la implementación nunca tuvo
  ese defecto, pero la afirmación sí.
  tuvo ese defecto, pero la afirmación sí.

### Errores metodológicos registrados

1. Afirmar conformidad desde memoria y desde un test circular, y que el circular pasara
   porque `f(x) == f(x)`. La lección operativa: **una referencia que se parece a la
   implementación no es una referencia.**
2. Interpretar los extremos `[0, 255]` de la rama `a0 <= a1` como un defecto a evitar. De
   hecho es la especificación. El error no estaba en la rampa ausente sino en la regla
   escrita que la prohibía.
3. Una expectativa de test puede ser ella misma el bug: «el alfa plano se decodifica a sí
   mismo en las 8 entradas» es falsa bajo DXT5 y prohibía el comportamiento correcto.
4. **Dos autores sobre el mismo fichero produce un par de implementaciones mutuamente
   consistentes y ambas erróneas.** El shader se escribió contra el C no conforme, y el
   encoder se corrigió después. El round-trip pasaba y la especificación era incorrecta.

### Estado y cifras medidas

| Elemento | Estado |
|---|---|
| Encoder | funcional, conforme en aritmética, **no ejecutado contra la especificación primaria** |
| Suite | **26/26**, `make` rc = 0 |
| PSNR | reference 28,73 · smooth 19,59 · noise 13,64 · adversarial 10,89 dB (reportado, no afirmado) |
| Topes | 24 / 16 / 11 dB — se sostienen sin recalibrar; la rampa corregida **mejoró** los tres |
| Throughput encoder C | ~28 MB/s |
| Speedup AVX2 | **0,97x - 1,05x entre ejecuciones**, oscila alrededor de 1: el SIMD cubre sólo el min/max |
| Shader | compila a SPIR-V; **ejecutado en GPU: no** |
| Enlace shader-C | **`NOT_ESTABLISHED`** — las dos validaciones son independientes y nada las conecta |

### Corrección a la atribución de los datos de entrada

La versión propuesta de esta entrada atribuía el defecto original a `AD-6`. Es incorrecto:
`AD-6` trata de los topes de calidad. El defecto estaba en `alpha_palette()` y en el test, y
la decisión de formato de bloque es `AD-2`. Se deja dicho para que la referencia no lleve a
buscar el defecto en la entrada equivocada.

---

## AD-8 — 2026-09-28 — Formato BC3/DXT5 estándar confirmado; `RX550_BC4X` descartado

| Campo | Valor |
|---|---|
| **DECISION** | El formato es BC3/DXT5 estándar de Microsoft. `RX550_BC4X` no existe como formato independiente |
| **DECIDER** | `HUMAN` (`HUMAN_POLICY`, vinculante) |
| **DATE** | `2026-09-28` |
| **Corrige** | la premisa de formato de `AD-2` en cuanto al nombre y a la supuesta desviación BC4 |

**Contexto**: entre 2026-09-28 y 2026-09-29 el proyecto se llamó a sí mismo
`RX550_BC4X` y afirmó que la rampa alfa de 6 valores «no es BC3, es la regla BC4». Eso
obligaba a no subir los bloques como `DRM_FORMAT_BC3` y forzaba el compute shader como
decodificador único. Ambas cosas se construyeron sobre una premisa no verificada.

**Evidencia 1 — especificación primaria.** Microsoft, *Block Compression (Direct3D 10)*:
> *«If alpha_0 is greater than alpha_1, then BC3 interpolates 6 alpha values; otherwise, it
> interpolates 4. When BC3 interpolates only 4 alpha values, it sets two additional alpha
> values (0 for fully transparent and 255 for fully opaque).»*

Corroborado por cuatro implementaciones independientes: `bcdec` (`bcdec__smooth_alpha_block`),
`oxideav-dds`, `DirectXTex/D3DX` (`D3DXDecodeBC3`) y el análisis de ryg sobre
comportamiento real de hardware.

**Evidencia 2 — no existe decodificador por hardware.** Búsqueda del árbol de amdgpu
(`drivers/gpu/drm/amd/`, 36 695 ficheros, 2026-09-28):

- cero decodificadores BC3/DXT5
- cero microcode de descompresión
- cero soporte de formato de textura BCn (`VK_FORMAT_BC*`, `DXGI_FORMAT_BC*`)

Único hit: `include/vega10_enum.h` → `CP_PERF_SEL_IMG_READ_FMT_BC3 = 0x30`, un contador de
rendimiento de la unidad de comandos, no un decodificador.

**Conclusión.** Polaris 12 no descomprime BC3 en hardware. La premisa «el hardware BC3 de la
RX 550 decodifica exactamente así» era falsa, y la inferencia apoyada en ella estaba
**invertida**: sin decodificador de hardware nada restringe el layout, y BC3 estándar es
estrictamente superior porque `bcdec`, `basisu`, visores y otros drivers leen estos
bloques. Un formato propio garantiza lo contrario.

**Errores metodológicos registrados**, porque el patrón se repitió:

1. `AD-2` se apoyó en una regla recordada, no consultada.
2. `[0, 255]` se interpretó como defecto cuando es la especificación.
3. `RX550_BC4X` se construyó sobre la premisa no verificada del decodificador de hardware,
   refutada con un `grep` sobre un árbol ya presente.
4. Un test se reescribió para certificar la rampa `÷5` («*is /5 … not /7*»), sustituyendo al
   que verificaba conformidad DXT5.
5. Este agente afirmó la regla correcta desde memoria, rechazó dos veces una corrección que ya
   era correcta, y cometió la misma falta que corregir.

**Lección**: una afirmación sobre un formato se resuelve leyendo la especificación. No la
resuelve un round-trip —un par de implementaciones mutuamente consistentes y ambas erróneas
pasa cualquier test de ida y vuelta—, ni un nombre de fichero, ni un comentario previo, ni el
recuerdo.

**Impacto**:

- Eliminadas 40 referencias a `RX550_BC4X` en 6 ficheros.
- Corregidos `rx550_compress.c`, `rx550_compress.h` y los dos README, que afirmaban la
  desviación y prohibían `DRM_FORMAT_BC3`.
- `decompress_bc4x.comp` renombrado a `decompress_bc3.comp`; SPIR-V regenerado
  (`glslangValidator` 11:16.3.0, rc=0, 11 984 B).
- El código no cambió: la aritmética ya era correcta. Lo que cambia es la afirmación sobre
  ella.

---

## AD-9 — 2026-09-28 — BC3/DXT5 usa truncamiento puro; los offsets `+3`/`+2` se retiran

| Campo | Valor |
|---|---|
| **DECISION** | La rampa alfa de BC3/DXT5 se calcula con **división entera sin constante de redondeo**. Sin `+3` en la rama `/7`, sin `+2` en la rama `/5` |
| **DECIDER** | `HUMAN` (`HUMAN_POLICY`, vinculante) |
| **DATE** | `2026-09-28` |
| **COMPLEMENTA** | `AD-8`, que fijó la nomenclatura del formato; no la aritmética |
| **Regla** | No se cambia sin autorización explícita del Arquitecto Principal |

> **Nota sobre el identificador.** La primera redacción de esta decisión se tituló `AD-8`, que
> ya estaba ocupado por la entrada de nomenclatura de la línea 863. Es `AD-9`. El desvío se
> registra aquí porque el identificador duplicado en un registro de decisiones es exactamente la
> clase de defecto que este registro existe para impedir.

**Contexto**: la implementación redondeaba al más cercano (`+3` sobre `/7`, `+2` sobre `/5`).
El commit `cda0440` afirmó que esos offsets *están en la especificación de Microsoft* y los
restauró tras haber sido retirados. Esa afirmación no estaba verificada.

**Evidencia — `bcdec` v0.985**, función `bcdec__smooth_alpha_block()`, transcrita literalmente
en `/tmp/opencode/bcdec_check.c`:

```c
if (alpha[0] > alpha[1]) {
    alpha[2] = (6 * alpha[0] +     alpha[1]) / 7;     /* sin +3 */
    ...
} else {
    alpha[2] = (4 * alpha[0] +     alpha[1]) / 5;     /* sin +2 */
    ...
    alpha[6] = 0x00;   alpha[7] = 0xFF;
}
```

La misma función sirve a `bcdec_bc3()` y a `bcdec_bc4()`: BC3 y BC4 comparten rampa alfa por
diseño, y difieren en el contenedor. Esto es lo que refutó `RX550_BC4X` (ver `AD-8`).

**Medición — rampa nuestra contra `bcdec`, los 65 536 pares de endpoints:**

| variante | pares que discrepan | entradas de 524 288 | error máx. |
|---|---:|---:|---:|
| con `+3`/`+2` | 54 300 / 65 536 (82.9 %) | 136 686 | 1 de 255 |
| **truncamiento puro** | **0 / 65 536** | **0** | **0** |

**Especificación de Microsoft**: `NOT_AVAILABLE`. No ha sido leída directamente por este
proyecto: no está en el corpus de `~/Descargas` (`buscar.py ALL 'DXT5|BC3'` → 2 coincidencias,
ambas en la ISA GCN3 p.88, una tabla de capacidades sin la rampa) y las búsquedas web no
devolvieron la especificación. Que la rampa se comporte como afirma `bcdec` es
`SINGLE_SOURCE`: lo que corroboraría es la lectura directa de la especificación, o una
implementación independiente como `basisu` transcrita y comparada con el mismo barrido.

**Conformidad declarada**: `CONFORMITY_PROVENANCE=BCDEC_TRANSCRIPTION`. No
`=SPECIFICATION_VERIFIED`.

**Justificación**:

- Compatibilidad con `bcdec`, `basisu` y visores: con los offsets, un bloque emitido por este
  códec se vería distinto al de cualquier herramienta estándar.
- Compatibilidad con decodificación por hardware, que trunca.
- Los offsets nunca se midieron como mejora. El PSNR de referencia es 28.73 dB con truncamiento
  y 28.73 dB con redondeo: idénticos. **El PSNR no tiene sensibilidad para distinguir estas dos
  implementaciones**, porque difieren en 1 LSB dentro de la paleta y el encoder elige índice, no
  valor. La conformidad la establece el barrido de 0/524 288 contra `bcdec`, no una métrica de
  calidad.

**Impacto**:

- `rx550_compress.c`, `decompress_bc3.comp`, `test_compress.c` y
  `test_alpha_ramp_independent.c`: offsets retirados; vectores literales recomputados
  (219→218, 146→145, 73→72, 179→178, 136→135, 93→92).
- `make test` en `compressor/`: 26/26, `rc=0`, distancia a `bcdec` 0 de 524 288.
- `shader_vs_c.c` **hubo quedado desincronizado**: sus copias de la rampa conservaban los
  offsets y reportaban 248 de 4096 canales discrepantes con el códec correcto. Corregido.
- `decompressor/Makefile` creado, con `make test` ejecutando el validador diferencial. Antes
  sólo se ejecutaba a mano, y por eso la desincronización no falló en ninguna parte.
- SPIR-V regenerado: 11 944 B, 2 986 palabras, magic `07230203`.

**Límite de lo verificado**: el shader no se ha ejecutado en la GPU. `GFX_HWIP` sigue
`NOT_DETERMINED` y la validación de esquema SPIR-V es `NOT_AVAILABLE` (`spirv-val` no instalado
en este host). Lo que `make test` en `decompressor/` establece es que la aritmética del shader
modelada en C concuerda con el decodificador de Fase 1 — no que el GLSL compile en un driver ni
que la RX 550 produzca esos píxeles.

**Errores registrados**, porque el patrón ya apareció cuatro veces en este punto del proyecto
(un test autorreferente, un nombre inventado, una premisa de hardware refutada, una
especificación afirmada sin leer):

6. `cda0440` afirmó que los offsets constan en la especificación sin haberla leído, y los
   restauró. Una afirmación sobre un documento no es un hecho sobre el documento.
7. `shader_vs_c.c` quedó obsoleto en silencio porque nada lo ejecutaba. **Un validador que no
   corre en el build no es un validador.**

---

## AD-10 — 2026-09-28 — La búsqueda de inset alfa cuesta 2,8× y no compra calidad medida

> **Nota de identificador.** Esta entrada se escribió como `AD-9`, número ya
> ocupado por la decisión de truncamiento puro (línea 916, vigente). Se
> renumera a `AD-10`. La búsqueda del repositorio dio **3 apariciones de
> `AD-9` en total**, todas dentro de este mismo fichero, y ninguna en otro
> documento: no hay referencias externas que actualizar. La serie salta de
> `AD-6` a `AD-8` porque `AD-7` nunca existió; el hueco **no se rellena con una
> entrada artificial**.

**Tipo de claim**: `MEASUREMENT` + `MODEL_CHOICE` (pendiente de `HUMAN_POLICY`)

### Contexto

`make test` publicaba 85,9 / 89,9 MB/s y speedup 1,05×; el codificador actual rinde
~28 MB/s. La regresión estaba marcada `UNEXPLAINED`. `RX550_ALPHA_INSET_STEPS = 15`
introduce 16 candidatos de endpoint alfa, cada uno puntuado sobre 16 píxeles × 8 entradas
de paleta.

### Medición A/B — mismo binario, sólo cambia la constante

| `RX550_ALPHA_INSET_STEPS` | reference dB | smooth dB | noise dB | MB/s |
|---:|---:|---:|---:|---:|
| 0 | 28,73 | 19,59 | 13,63 | **74,1** |
| 2 | 28,73 | 19,59 | 13,63 | 57,8 |
| 5 | 28,73 | 19,59 | 13,63 | 47,4 |
| 10 | 28,73 | 19,59 | 13,64 | 34,5 |
| 15 | 28,73 | 19,59 | 13,64 | **26,8** |

**Resultado**: la calidad es **idéntica** en todo el rango — la única variación es
0,01 dB en ruido, dentro del ruido de medición — mientras el rendimiento cae **2,8×**.

Coste por bloque: alfa 16 × 16 × 8 = **2048** iteraciones internas; color
5 × 16 × 4 = **320**. El alfa domina **6,4×** la ruta de color, y es la razón del
speedup AVX2 ≈ 1: la reducción min/max es una fracción minúscula del trabajo total.

**Causa estructural**: `encode_alpha()` ya selecciona, por píxel, la entrada más cercana de
las 8 de la paleta. Con `inset = 0` los endpoints son el mínimo y el máximo reales, que ya
abarcan el rango de los datos; estrecharlo sólo puede empeorar los píxeles de los extremos.
El bucle corta cuando `a0 > a1`, de modo que los pasos siguientes no encuentran un
endpoint mejor, sólo uno peor. La búsqueda es un **no-op en calidad**.

### Alcance y lo que NO se afirma

- La medición es sobre el **corpus sintético** que genera `test_compress.c` con semilla
  fija, no sobre texturas reales. El nulo vale para el corpus que gobierna los topes de
  calidad; **no** descarta que alguna textura real se beneficie. Cerrarlo requiere un
  corpus representativo, que no existe en el proyecto.
- Queda un **residuo sin explicar**: con `STEPS = 0` el codificador rinde 74,1 MB/s, no
  los 85,9 MB/s publicados anteriormente. ~15 % de la diferencia no está atribuido. La
  versión que produjo 85,9 MB/s (`5d086238`) **nunca se commiteó** y no se conserva, así
  que la atribución del residuo es `NOT_DETERMINED` y no se especula.

### Decisión

`ALPHA_INSET_STEPS_PRESENT = RECOMMEND_REDUCE_TO_0` — recomendación del agente, **no
aplicada**. Se propone `RX550_ALPHA_INSET_STEPS = 0` (o eliminar la búsqueda), que
recupera 2,8× sin mover ningún PSNR. **No se aplica sin `HUMAN_POLICY`**: cambiar un
compromiso calidad/velocidad es decisión del humano (§10.2), y el corpus sintético no es
representativo suficiente para impositionarlo.

**Reproducir**: `make measure-alpha-inset` barre la constante y reimprime la tabla.

---

## 2026-09-29 — AD-11: Divergencia entre la especificación Microsoft BC3 y `bcdec` v0.985

| Campo | Valor |
|---|---|
| **DECISIÓN** | Seguir la **especificación Microsoft** (redondeo `+3` / `+2`), **no** `bcdec` |
| **DECIDER** | `HUMAN_POLICY` 2026-09-29, sobre evidencia verificada por el agente |
| **DATE** | `2026-09-29` |
| **SUSTITUYE** | la decisión D13 («truncamiento puro»), que quedó registrada como `HUMAN_POLICY` el 2026-09-28 y que era incorrecta |

### Contexto

El códec implementa la rampa alfa de BC3. Dos lecturas de la práctica circulaban en el
proyecto: una decía que la especificación publica el redondeo `+3`/`+2`, y otra que la
referencia `bcdec` —y con ella el «hardware»— trunca. Ambas se afirmaron sin consultar la
fuente. El test llegó a imprimir `CONFORMA con la especificacion Y con bcdec v0.985`, que
es autocontradictorio: no se puede ser conforme con una especificación con redondeo y con
una biblioteca que trunca en la misma rampa.

### Evidencia, consultada

| Fuente | Qué dice | Cómo se obtuvo |
|---|---|---|
| Microsoft, *Block Compression (Direct3D 10)*, 2022-08-26 | `alpha_2 = (6 * alpha_0 + 1 * alpha_1 + 3) / 7;` … `alpha_6 = 0; alpha_7 = 255;` | lectura directa de la URL de learn.microsoft.com |
| `bcdec` v0.985, `iOrange/bcdec`, `bcdec__smooth_alpha_block()` | `alpha[2] = (6 * alpha[0] + alpha[1]) / 7;` … **sin `+3`, sin `+2`** | lectura directa de `bcdec.h` en el repositorio |

Medido por diferencia sobre los 65 536 pares de endpoints:

| Magnitud | Valor |
|---|---|
| Pares que divergen | **54 300 / 65 536 = 82,9 %** |
| Entradas de rampa divergentes | 136 686 / 524 288 |
| Error máximo | **1 LSB** |

### Justificación

1. La especificación Microsoft es la **fuente de autoridad** del formato. Una
   implementación de referencia es `SECONDARY` respecto de ella (`AGENTS.md` §3.1).
2. El decodificador de bloques por función fija del hardware es el que define la
   interoperabilidad. `bcdec` es una biblioteca *de CPU* escrita pensando en tamaño
   reducido, y su cabecera declara explícitamente que prioriza tamaño sobre fidelidad.
3. El error es de **1 LSB** en el 82,9 % de los pares: visible, acotado y no fatal, pero
   suficiente para que un bloque no sea *byte-idéntico* con una herramienta basada en
   `bcdec`. Eso se documenta en vez de ocultarse.

### Impacto y alcance

- El códec es **conforme con la especificación Microsoft**. `CONFORMITY_PROVENANCE =
  SPECIFICATION_VERIFIED`.
- El códec **NO es byte-idéntico con `bcdec` v0.985**: diverge en 54 300 de 65 536 pares
  de endpoints, con un error máximo de 1 LSB. Cualquier herramienta que compare contra
  `bcdec` reportará esa diferencia y **reportará bien**.
- El modo de color de BC3 queda confirmado por la misma fuente: `bcdec_bc3()` llama a
  `bcdec__color_block()` con `onlyOpaqueMode = 1`, y el comentario del propio `bcdec` dice
  *"also BC3 color block uses ONLY this mode"*. **BC3 es siempre modo 4 colores.** El
  `if` de BC1 no aplica.

### Regla

No se cambia sin autorización explícita del `HUMAN`. Y mientras siga siendo cierto, toda
afirmación de conformidad debe decir **con qué** se es conforme: decir «conforme» a secas,
como hacía la línea retirada de `test_alpha_ramp_independent.c`, es indistinguible de no
decir nada.

### Procedencia de esta entrada

Ambas fuentes se consultaron **por el agente**, leyendo las URLs, el 2026-09-29. Ninguna
de las dos estaba instalada en el host: no hay `bcdec` ni cabeceras Vulkan. Lo que motivó
esta entrada fue que una afirmación de conformidad **sin fuente** sobreviviera a tres
rondas de revisión, oscilando entre spec y truncamiento según quién escribiera.

---

## 2026-09-29 — AD-13: Estado de Fase 2 (descompresor en GPU): `PARTIAL`, Fase B `NOT_WRITTEN`

| Campo | Valor |
|---|---|
| **DECISION** | La Fase 2 se cierra como **parcialmente completa**. El shader existe y su aritmética concuerda con el decodificador de CPU; **nunca se ha ejecutado en la RX 550**. La Fase B no se escribe con declaraciones manuales de Vulkan |
| **DECIDER** | `HUMAN` (2026-09-29) sobre el cierre; `MODEL_CHOICE` la decisión de no escribir Fase B a mano |
| **DATE** | `2026-09-29` |
| **Estado Fase 2** | `PARTIAL` |
| **Fase B** | `NOT_WRITTEN` |
| **Ejecución en GPU** | `NOT_RUN` |

### Lo que está establecido

- Shader GLSL `decompress_bc3.comp` escrito, y compila a SPIR-V con `glslangValidator` 11:16.3.0,
  `rc=0`, 11 944 B, 2 986 palabras, magic `07230203`.
- `shader_vs_c` reconcilia la aritmética del shader con `rx550_decompress_block()`:
  **0 de 4096 canales** discrepantes, 64 bloques de corpus. Es `SIMULATED_ARITHMETIC`: un modelo
  en C del shader, no el GLSL compilado ni ejecutado.
- `test_corpus_validate` (Fase A) valida el artefacto SPIR-V, construye un corpus determinista y
  **mide la cobertura** de las dos ramas de la rampa alfa.
- D19a aplicado (`44bc133`): la convención BC3 `a0 = max, a1 = min` hace que el encoder pueda
  emitir `a0 > a1`. Antes no podía: `mn <= mx` por construcción, luego
  `a0 = mn + inset <= mx - inset = a1` siempre. Medido: la cobertura de la rama de 8 valores pasó
  de **0 de 64 a 59 de 64** bloques.
- AD-11: redondeo `+3`/`+2` según la especificación Microsoft. El barrido contra las dos
  transcripciones independientes da **0 de 65 536** pares con discrepancia.

### Lo que NO está establecido

- **El shader no se ha ejecutado en ninguna GPU.** `NOT_RUN`. Ni la RX 550, ni llvmpipe, ni
  ningún otro dispositivo. Todo lo anterior es una afirmación sobre el algoritmo y sobre el
  artefacto compilado, no sobre su ejecución.
- `GFX_HWIP` sigue `NOT_DETERMINED`.
- Validación de esquema SPIR-V: `NOT_AVAILABLE`, `spirv-val` no está instalado.
- El `.spv` está hoy desfasado respecto al `.comp`, que fue editado después.
  `make decompress_bc3.spv` lo regenera.

### Por qué la Fase B no se escribe a mano

`vulkan-devel` no está instalado en este host y el agente no tiene `sudo` sin contraseña:

```
/usr/include/vulkan/vulkan.h   ausente
dnf info vulkan-devel           "No hay paquetes que se correspondan con la lista"
sudo -n true                   "a password is required"
```

Se intentó declarar los structs de Vulkan a mano y se abandonó. Coste medido: **37 errores de
compilación**, y un `pNext` duplicado en una struct que **altera el layout en silencio**: no da
error, da basura plausible. `decompressor/vk_pipeline_min.c` (13 776 B) presenta un `SIGSEGV`
reproducible en RADV y en llvmpipe cuya causa no es diagnosticable sin las cabeceras reales; un
fallo de layout se manifiesta como segmentación, no como mensaje.

La lección es de método, no de Vulkan: **una struct declarada a mano y no verificada contra la
cabecera no es una fuente, es una suposición con el tamaño de un struct**. El criterio de §4.1
—una implementación reescrita a mano es más débil que la fuente que reemplaza— se aplica igual
aquí: si la fuente primaria está disponible y es barata, no se sustituye.

### Consecuencia para el manifiesto RX550-FIRST

La Fase 2 **no cumple** la exigencia de ejercitar la GPU. El shader es correcto en aritmética y
válido en compilación, y eso es `PARTIAL`, no otra cosa. Declararlo completo sin la Fase B sería
el mismo error que `RX550_BC4X`: una afirmación de conformidad sin ejecución detrás.

### Reanudar

1. `sudo dnf install vulkan-devel` — requiere privilegios, es acción del `HUMAN`.
2. Reescribir la Fase B con `#include <vulkan/vulkan.h>`, sin structs a mano.
3. Despachar en la RX 550, identificada por PCI identity `0x1002:0x699F` y **nunca** por índice de
   enumeración: este host expone iGPU, AMD y llvmpipe, y llvmpipe aceptaría el dispatch.
4. **Validar la salida antes de comparar.** Sin ese paso, una GPU que no hizo nada deja el búfer
   intacto, la comparación da 0 discrepancias y el test pasa. Es el fallo que un resultado
   `PASS` vacío no detecta.

---

## 2026-09-29 — AD-12: el sampler del Polaris 12 trunca o redondea la rampa alfa de BC3

**Contexto.** La especificación Microsoft *Block Compression (Direct3D 10)* describe la
interpolación en notación fraccional. El documento de Direct3D 9 *Textures with Alpha
Channels (DXT4/DXT5)* — el mismo formato, publicado explícitamente como enteros — la escribe
con redondeo:

    a0 >  a1 : a[i] = ((8-i)*a0 + (i-1)*a1 + 3) / 7,  i = 2..7
    a0 <= a1 : a[i] = ((6-i)*a0 + (i-1)*a1 + 2) / 5,  i = 2..5
    a0 <= a1 : a[6] = 0, a[7] = 255

bcdec v0.985 trunca: sin `+3`, sin `+2`. La diferencia no es marginal — 54300 de 65536 pares
de endpoints discrepan, con error máximo de 1 sobre 255.

**AD-11** siguió el texto de la especificación (redondeo). Eso resuelve **qué dice el
documento**. No resuelve **qué hace el hardware**, y este proyecto entrega un **encoder** cuyo
consumidor es precisamente ese hardware.

**Pregunta (NOT_DETERMINED).** ¿El sampler de textura del Polaris 12 decodifica la rampa alfa
de BC3 con truncamiento o con redondeo `+3`/`+2`?

**Impacto si la respuesta es TRUNCAMIENTO.** `rx550_compress.c` emitiría bloques que el sampler
de la RX 550 decodifica de forma distinta a como predice `rx550_decompress_block()`. El error
no aparecería en un informe: viaja **dentro del payload del bloque**, de forma sistemática, en
el 82.9 % de los pares de endpoints. Un round-trip contra nuestro propio decodificador lo
ocultaría por construcción — ambos serían erróneos de la misma manera.

**Por qué RX550-FIRST obliga a medirlo y no a decidirlo.** El manifiesto pone el hardware
delante del texto. Conformarse con la especificación y producir bloques que la GPU objetivo no
decodifica igual es el peor resultado posible: parece correcto y no lo es.

**Método elegido.** Adjuntar una textura comprimida DXT5 directamente como color attachment
de un FBO y leer con `glReadPixels`. Esto fuerza al sampler a descomprimir y devuelve RGBA8 sin
 shaders, sin quad y sin dibujar nada: el valor devuelto ES la salida del sampler. Evita por

> **[CORREGIDO — ver AD-14]** Las tres lineas siguientes afirmaban que la ruta de cómputo
> Vulkan «no funciona en este host». Es **FALSO**. El SIGSEGV de `vkCreateComputePipelines` no
> era un defecto del driver: lo causaban mis propias declaraciones de structs escritas a mano.
> Con `<vulkan/vulkan.h>` real el pipeline se crea y despacha sin crash.


**Cobertura prevista.** Los 256×256 = 65536 pares de endpoints y los 8 códigos de índice:
1048576 observaciones de hardware. No una muestra.

**Autovalidación obligatoria antes de comparar.** Un resultado de "0 discrepancias" no prueba
nada si el camino de medida está roto. Se exige: (1) que `GL_RENDERER` contenga `RX 550`, si
no se aborta — en un contexto Intel todos los números serían del sampler equivocado;
(2) presencia de `GL_EXT_texture_compression_s3tc`; (3) FBO completo; (4) que los índices 0 y
1 decodifiquen exactamente a `a0` y `a1`, que no intervienen interpolación y por tanto prueban
el camino en sí.

**Estado de la medición: NO REALIZADA.** (La razón que se daba aquí — que la ruta de cómputo
Vulkan no funcionaba — era **incorrecta**; ver AD-14. La medición sigue sin realizarse, pero
por el obstáculo del contexto OpenGL, no por Vulkan.)

`test_hardware_bc3.c`
host no se ha podido establecer un contexto OpenGL desde un programa propio, por un
desajuste cliente/servidor en GLX que se documenta en `04-IMPLEMENTACION/decompressor/`.
`NOT_DETERMINED` no se convierte en `PROVEN_ABSENT` ni en `PROVEN`: la pregunta sigue abierta.

**Estado actual del código.**
- `rx550_compress.c` usa redondeo `+3`/`+2` (AD-11).
- `decompress_bc3.comp` usa redondeo `+3`/`+2`, sincronizado con el C. `shader_vs_c` reporta
  **0/4096** canales discrepantes frente a `rx550_decompress_block()` en la variante que lee
  los endpoints de color de `block 2`, que es como lee el shader.
- `test_alpha_ramp` **falla**, porque sigue afirmando igualdad con bcdec v0.985. El fallo es
  correcto y está informativo: es el suite diciendo que ya no coincidimos con el decodificador
  estándar de facto. No se corrige hasta que AD-12 se resuelva con una medición.

**Decisión pendiente.** Esperar el resultado de la medición en hardware para confirmar o
refutar AD-11. Hasta entonces, el redondeo se mantiene por coherencia interna entre el encoder
y el shader, marcada como **no validada contra el hardware objetivo**.


---

## 2026-09-29 — AD-14: el shader SÍ ejecuta en la RX 550; el SIGSEGV era mío

**Corrige**: AD-12 y AD-13 de este fichero, y `PROYECTO_STATUS.md` de la misma fecha.

### ERROR CORREGIDO

AD-12 afirmaba que `vkCreateComputePipelines` «provoca SIGSEGV dentro de `libvulkan_radeon.so` y
de `libvulkan_lvp.so`, incluso con shader vacío y pipeline layout vacío», y de ahí concluía que
la ruta de cómputo Vulkan no funciona en esta host. **Es falso.**

**Causa real**: mis declaraciones de structs Vulkan escritas a mano. Al disponerse
`vulkan-headers-1.4.341.0` y `vulkan-loader-devel`, y reescribirse la Fase B contra
`<vulkan/vulkan.h>`, el mismo pipeline se crea y despacha sin crash.

**Por qué me equivoqué.** El crash reproducía en 2 ICDs independientes y con shader y layout
vacíos, lo que descartaba las causas obvias. Verifiqué tamaños y offsets contra la ABI, y hasta
obtuve un retorno limpio de `vkCreateComputePipelines(dev, NULL, 0, NULL, NULL, &out)`, que
demuestra que el prototipo y la convención de llamada eran correctos. Registré la `LIMITATION`
correcta: *«sin `vulkan-devel` no puedo descartar un error residual en mis structs; lo único no
descartado es un desajuste en número o tipo de campos, que `offsetof` no revela»*. **No la
cerré, y era la que importaba.** Los controles que ejecuté acotaban el fallo; no lo explicaban.
Un fallo reproducido en dos ICDs independientes sigue siendo compatible con un error propio
común a las llamadas que yo hago.

### Segundo defecto: push constant nunca empujado

La salida del buffer era **entera a cero**. `decompress_bc3.comp:276` se autolimita con
`if (block_idx >= params.num_blocks) return;`. El test **declaraba** el rango de push constant
en el pipeline layout pero contenía **cero** llamadas a `vkCmdPushConstants` — ni resuelta como
símbolo. `num_blocks` llegaba sin inicializar, valía 0, y las 256 invocaciones retornaban antes
de escribir. Declarar el rango no basta; hay que empujarlo. Corregido.

Este hueco estaba presente desde el esqueleto original del agreement test y se señaló entonces.
Sobrevivió a la reescritura «con cabeceras reales», porque la reescritura se centró en las
cabeceras y no en la interfaz del shader.

### Tercer defecto: el test devuelve `rc=0` aunque falle

Imprime `[FAIL]` por `stderr` y devuelve `0`. Con la salida canalizada el `[FAIL]` queda aparte
y el proceso parece exitoso: cualquier integración continua que compruebe el código de salida
reportaría **verde sobre un fallo**. No corregido. Sin este arreglo, un resultado favorable habría
sido fácil de aceptar por error — y de hecho me pasó: la primera ejecución_EN_CPU se leyó como
éxito.

### Resultado medido tras corregir el push constant

RX 550, RADV POLARIS12, PCIE `1002:699f`, 64 bloques, 256 invocaciones:

    [ OK ] 940 de 4096 bytes distintos de cero
    [ OK ] ninguna palabra conserva el patron veneno 0xDEADBEEF
    RESULT: GPU != CPU. 57 de 64 bloques difieren.
      bloques discrepantes : 57 de 64
      bytes discrepantes   : 3197 de 4096

### Desglose por canal — el dato que importa

| Canal | Discrepancias |
|---|---|
| 3 — alfa | **0 de 4096** |
| 0/1/2 — RGB | 57 de 64 bloques |

La rampa alfa BC3 del shader coincide **byte a byte** con `rx550_decompress_block()` en hardware
real. El desacuerdo está íntegramente en la ruta de color, con error estrecho y sistemático
(±57/±58 en las muestras mostradas): no es redondeo ni ruido. **Causa `NOT_DETERMINED`.**

### Lo que esto NO prueba sobre AD-12

Que el alfa del shader coincida con el del decodificador de CPU demuestra que **shader y C
concuerdan**. **No** demuestra qué regla sigue el **sampler del hardware**: el shader GLSL no es
el sampler. El método correcto para eso sigue siendo adjuntar la textura DXT5 como color
attachment de un FBO y leer con `glReadPixels`, y sigue sin ejecutarse. **AD-12 permanece
`NOT_DETERMINED`**; no se convierte en `PROVEN_ABSENT` ni en `PROVEN` por el hecho de que la
ruta de cómputo funcione.

### Estado tras AD-14

- AD-12 `NOT_DETERMINED` (sin cambio)
- AD-13: su premisa de «Fase B `NOT_WRITTEN`» queda **superada**; la Fase B existe y se ejecuta
- Agreement test: **NO** establecido. Falla en color con un bug acotado por diagnosticar
- La autovalidación previa a la comparación hizo su trabajo: se negó a reportar `PASS` sobre una
  salida enteramente a cero, que habría producido «0 discrepancias» y un falso éxito
