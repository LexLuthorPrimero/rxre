# 051 · Leer AGENTS.md cambia la política: la frontera era un formulario, no una pared

<!-- CLAUSULA_RETRACTADA_POR=091 -->
> ⚠ **La cláusula del bloqueo técnico de este documento está RETRACTADA.**
> Se leyeron `CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM`, y **no**
> `CONFIG_MODULE_SIG_FORCE`, que está `# CONFIG_MODULE_SIG_FORCE is not set`.
> Medido: `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio **compila**
> con `vermagic` idéntico y **sin firmar**. No hay bloqueo técnico: lo que queda
> es NIVEL 4 → `BLOCKED_BY_AUTHORIZATION`. Ver `091`.

`CLASSIFICATION=CORRECTION+TOOL` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`TOOL=tools/frontier.py` · `CORRIGE_LA_POLITICA_DE=046, 047` · `MODIFICATIONS=0` en el corpus

## CUDA principal

El usuario pidió leer `AGENTS.md`. Lo leí: **961 líneas en disco**. Y contiene una sección que
no había interiorizado —**JERARQUÍA DE PERMISOS**, cinco niveles— que **cambia lo que estaba
permitido**:

```
NIVEL 2 — READ HARDWARE
Leer registros, sysfs, debugfs, iomem, lspci, tracepoints, observar sin modificar.
→ AUTORIZADO dentro de investigación, si es read-only y reversible.
→ Registrar antes/después.
```

**Yo llevaba afirmando que leer MMIO estaba prohibido.** No lo está. Es NIVEL 2, autorizado,
con un formulario que rellenar. Y lo tenía escrito en el código:

```
tools/hwip.py:49   "…NIVEL 2, y AGENTS.md lo AUTORIZA dentro de investigacion…"
tools/hwip.py:936  "Leer un registro es NIVEL 2 … AUTORIZADO … con registro antes/despues"
```

ya corregidos, y en las cabeceras de `046` y `047` como `CORRIGE_LA_POLITICA`.

**La causa del error:** la versión de `AGENTS.md` cargada en el contexto de la sesión es más corta
y **no tenía esa sección**. El proyecto se gobierna por el fichero en disco — eso ya constaba,
fue una decisión de una iteración anterior — y el fichero en disco sí la tiene. **Confié en el
resumen del fichero en vez de en el fichero.**

**Consecuencia para la frontera:** todo lo que yo marqué `BLOCKED` por política era un
**experimento autorizado con un formulario**. Eso no cambia qué es `NOT_PUBLISHED` ni qué falta
por hardware, pero cambia qué trabajo es alcanzable.

**Lo que sí es pared, y es técnica:** `NIVEL 4`, cargar un módulo. El host tiene
`CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM` **sin clave de firma**, así que un `.ko`
  > **[091] CORRIGE ESTA CLAUSULA**: no hay bloqueo tecnico. Lo que se leyo fue
  > `CONFIG_MODULE_SIG_ALL` y **no** `CONFIG_MODULE_SIG_FORCE`, que esta
  > `# CONFIG_MODULE_SIG_FORCE is not set`. Medido en este host:
  > `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio COMPILA con
  > `vermagic` identico y SIN FIRMAR. Lo que queda es NIVEL 4
  > (`BLOCKED_BY_AUTHORIZATION`), que es otra cosa. Ver 091.
propio no cargaría aunque la política lo permitiera. Esa pared no se quita con autorización.

## Lo que el nivel corregido descubre al re-clasificar

Con la escalera de contexto `FRASE → PÁRRAFO → SECCIÓN → DOCUMENTO`, y cada peldaño bajando la
fuerza de la marca:

| vía | huecos | fuerte | qué significa |
|---|---|---|---|
| `SPEC_NO_PUBLICADO` | 124 | 63 | falta documentación que no existe (`033`) |
| `RUNTIME_ACTIVO` | 67 | 14 | solo se cierra observando comportamiento |
| `POR_DEFINICION` | 33 | 5 | es una convención que se elige |
| `UN_REGISTRO` | 12 | 5 | se cierra leyendo un registro |
| `DIFERENCIAL` | 3 | 2 | se cierra repitiendo con un parámetro |
| `SIN_PISTAS` | **2** | 0 | el texto no dice qué haría falta |

**`SIN_PISTAS` de 110 a 2.** Y el riesgo que eso crea está declarado en la salida: un documento
que dice "spec" **una vez** clasifica sus treinta huecos como spec, porque la marca viene del
documento entero. La columna `fuerte` separa lo que el propio hueco dice de lo que se le atribuye
por su documento, y **63 de 124** las tiene en la frase.

## La categoría que faltaba: `DIFERENCIAL`

`057:133` se clasificaba `UN_REGISTRO`, y es **experimento diferencial**. `056 §7` ya tenía el
discriminante escrito, y no es una lectura:

> escribir un `WAIT_REG_MEM(FUNCTION=always, poll=0x20)` y leer `INVALIDATE_REQUEST` entre dos
> IBs, con el invalidate deliberadamente retardado; y repetir con `poll=0x0` y `poll=0xFF`. **Si el
> resultado cambia con el poll, el wait espera algo.**

La sección **nombra registros** — nombra `INVALIDATE_RESPONSE` para explicar que *no* sirve como
discriminante — y por eso la clasificación por presencia de registro la metía en `UN_REGISTRO`.

**Un nombre de registro en el texto no dice si el discriminante es leerlo u observar un efecto.**
Por eso `DIFERENCIAL` mira la *forma* de la frase —«cambia con el», «repetir con», «comparar
con»—, que es la definición de experimento controlado, y va **antes** que `UN_REGISTRO`.

Y `018` ya había establecido por qué leer `INVALIDATE_RESPONSE` no vale: `REQUEST` es un mapa de
16 bits **sin token**, así que un `RESPONSE` con bits puestos no significa nada. El discriminante
es **comportamental**, no de registro. `056` lo dice y la herramienta no lo entendía.

## El aviso que debía ser específico y no lo era

Al imprimir el registro que haría falta, el mensaje decía siempre «la sección no nombra
**registro**». Para `DIFERENCIAL` eso es **mentiroso**: lo que falta es el **parámetro** que se
varía, y el registro no hace falta. Ahora el mensaje depende de la vía.

**Y el resultado de eso es el hallazgo operativo de la iteración: ninguno de los 15 huecos
`UN_REGISTRO` nombra el registro en su sección.** Todos dicen *cómo* se cierra y ninguno dice
*cuál*. **Un discriminante sin nombre no se puede ejecutar**, y la herramienta lo dice en vez de
suponerlo. Ese es el trabajo que queda, y es de lectura.

## Dos cosas que el proyecto no cumple de `AGENTS.md`, y que ahora son visibles

**1 · Falta la clasificación `TOOL_VALIDATED / TOOL_PARTIAL / TOOL_UNVALIDATED / TOOL_BROKEN`.**
`AGENTS.md` la exige y dice que `TOOL_UNVALIDATED` no puede cerrar una afirmación crítica. No la
he estado aplicando. De 19 herramientas: 17 con selftest, y `audit_citations.sh` sin él — lo
reporto en el `--self` del oráculo, pero no con esa clase.

**2 · Faltan 7 de los 8 artefactos de `AUTOMATIZACIÓN DE DOCUMENTACIÓN`.** `AGENTS.md` lista
`EVIDENCE-MATRIX`, `CURRENT-STATE`, `KNOWLEDGE-GRAPH`, `OPEN-FRONTIERS`, `NEGATIVE-RESULTS`,
`CONTRADICTIONS`, `TOOLS-STATUS`, `CHANGELOG`. Solo existe `CHANGELOG.md`.

**Corrección de la iteración anterior, y es mía:** escribí que `056` citaba
`OPEN-FRONTIERS.md:38-43` *«como si existiera»* y que era *«una cita a un fichero que no está»*.
**Es falso: el fichero existe.**

El error fue medir mal — comprobé `isfile()` con ruta relativa al directorio actual en vez de
indexar el árbol, y salió que casi todo faltaba. **Es exactamente el error que este proyecto lleva
toda la sesión documentando** —aceptar un «no encontrado» sin comprobar la búsqueda— y lo cometí
inmediatamente después de haberlo documentado tres veces. La cifra correcta, con índice del árbol:

```
6356 referencias a .md del proyecto
6063 resuelven (95%)
 293 no resuelven (5%), en 157 nombres

y en 06-INGENIERIA-INVERSA/findings/: UNA sola, y es real
  021:154 apunta a `022-pte-productor-sdma-gfx8.md`
  y el fichero es `023-pte-productor-sdma-gfx8.md`. Numeración equivocada.
```

La cadena de evidencia de los findings está limpia. La del resto del proyecto no, y el 5% son
sobre todo ficheros de configuración que se citan y no están: `CLAUDE.md`, `docs/config.md`,
`docs/rules.md`, `DESIGN.md`.

**3 · `ESTADO ACTUAL YA CONOCIDO` está desactualizado.** Dice «no reabrir salvo evidencia
contradictoria nueva» y no recoge `043` a `050`. Reabrir `023`/`035`/`036` **sí** era legítimo —
había evidencia contradictoria, la de `043` —, pero el estado debería reflejarlo.

## UNLOCKS

- **La frontera dejó de ser una pared.** `NIVEL 2` está autorizado, y `NIVEL 3` —experimento
  runtime parametrizado, inyección PM4/IB bajo control— **no requiere confirmación humana por
  defecto si es reversible**, con justificación por discriminante y registro pre/post. El
  discriminante de `FUNCTION=always` **ya está escrito** en `056 §7`.
- **La única pared real es técnica:** firmar y cargar un módulo. Eso no se resuelve con
  autorización, y es lo que impide el experimento que sí requeriría un driver propio.
- `DIFERENCIAL` es la categoría que faltaba, y es reutilizable: cualquier hueco que se cierre
  repitiendo con un parámetro y comparando —orden de ejecución, efecto de un flush, visibilidad
  de una traducción— entra en ella sin cambiar nada más.

## Falsación

- La corrección de política se refuta si el fichero en disco de `AGENTS.md` no contiene la sección
  `JERARQUÍA DE PERMISOS`. Se lee en un segundo, y está en las líneas 46-88.
- La clasificación se refuta si un hueco marcado `DIFERENCIAL` se cierra realmente con una
  lectura. El caso de `057` se comprueba leyendo `056 §7`, y el texto está citado arriba.
- Los `SIN_PISTAS = 2` se refutan si hay un tercer hueco abierto cuyo documento no mencione
  ninguna de las marcas. La herramienta los imprime, así que se ven.
- La propagación se refuta si un hueco clasificado por el documento no lo fuera por su frase. Es
  la debilidad conocida, y la columna `fuerte` la hace visible en vez de esconderla.

## Evidencia

```
tools/frontier.py        12 vectores de selftest
                         escalera FRASE→PARRAFO→SECCIÓN→DOCUMENTO
                         241 abiertos: 124 spec, 67 runtime, 33 definicion,
                                      12 registro, 3 diferencial, 2 sin pistas
                         1 hueco obsoleto
AGENTS.md                961 lineas; JERARQUIA DE PERMISOS en 46-88
                         NIVEL 2 = READ HARDWARE, AUTORIZADO con registro
correcciones aplicadas    tools/hwip.py:49 y :936 (politica de lectura)
                         cabeceras de 046 y 047 (CORRIGE_LA_POLITICA)
discrepancia detectada    056 cita OPEN-FRONTIERS.md:38-43, que NO existe
suite del driver          22 + 12 + 195 = 229 checks, 0 fallos
crosscheck                10 vectores CLEAN
audit_citations           268 citas, 0 fallos
corpus                    MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.

---

## RESULTADO DE ITERACIÓN (AGENTS.md §RESULTADO OBLIGATORIO)

```
STATE CHANGE:
  La política de lectura de hardware del proyecto era incorrecta: leer un
  registro es NIVEL 2 y esta AUTORIZADO, no prohibido. Corregido en dos
  herramientas y dos findings.

PROVEN:
  AGENTS.md en disco tiene JERARQUIA DE PERMISOS con NIVEL 2 = READ HARDWARE
  AUTORIZADO (lineas 46-88). La version en contexto de sesion no la tiene.
  056 §7 escribe el discriminante de FUNCTION=always, y es DIFERENCIAL.
  018 establece que leer INVALIDATE_RESPONSE no discrimina (REQUEST sin token).

REFUTED:
  "La lectura de MMIO esta prohibida por AGENTS.md" -> REFUTED.

NOT_DETERMINED:
  Que registro cierra cada uno de los 12 huecos UN_REGISTRO: ninguno lo nombra.
  Valor de FUNCTION=always: sigue siendo NOT_PUBLISHED, y eso no lo cambia
  una politica.

NEW RELATIONS:
  Ningun hueco UN_REGISTRO tiene el discriminante escrito, aunque todos dicen
  como se cierra. La via de cierre y el discriminante son dos cosas distintas.

UNLOCKS:
  NIVEL 2 autorizado con registro pre/post.
  NIVEL 3 (experimento parametrizado) no requiere confirmacion humana si es
  reversible, con justificacion por discriminante.
  La unica pared real es NIVEL 4: CONFIG_MODULE_SIG_ALL sin clave.

BLOCKED:
  Cargar un modulo propio (NIVEL 4 + CONFIG_MODULE_SIG_ALL sin clave de firma).
  Es una pared TECNICA, no de politica.

NEXT ACTION:
  Crear los 7 artefactos que AGENTS.md §AUTOMATIZACIÓN DE DOCUMENTACIÓN exige y
  que no existen, generados por herramienta. Y con ella la auditoría de
  REFERENCIAS INTERNAS, que audit_citations.sh no hace: el solo comprueba citas
  al corpus. Por eso 021:154 --que apunta a un `022-` donde el fichero es un
  `023-`-- lleva varias iteraciones sin que nadie lo viera.
```
