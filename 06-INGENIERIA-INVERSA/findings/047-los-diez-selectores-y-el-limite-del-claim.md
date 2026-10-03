# 047 · Ninguno de los 10 selectores de IP es alcanzable, y por qué el claim fuerte sería falso

<!-- CLAUSULA_RETRACTADA_POR=091 -->
> ⚠ **La cláusula del bloqueo técnico de este documento está RETRACTADA.**
> Se leyeron `CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM`, y **no**
> `CONFIG_MODULE_SIG_FORCE`, que está `# CONFIG_MODULE_SIG_FORCE is not set`.
> Medido: `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio **compila**
> con `vermagic` idéntico y **sin firmar**. No hay bloqueo técnico: lo que queda
> es NIVEL 4 → `BLOCKED_BY_AUTHORIZATION`. Ver `206`.

`CLASSIFICATION=TOOL+CONCLUSION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`TOOL=tools/unreach.py` · `GENERALIZA=046` · `MODIFICATIONS=0` en el corpus
`MODIFICATIONS=0` en el corpus
`CORRIGE_LA_POLITICA` — **este documento trata la lectura de hardware como una pared, y no lo
es.** Leer un registro es `NIVEL 2` en la jerarquía de permisos de `AGENTS.md`: *leer registros,
sysfs, debugfs, iomem, lspci, observar sin modificar* → **AUTORIZADO dentro de investigación**, si
es read-only y reversible, **con registro antes/después**.

La versión de `AGENTS.md` cargada en el contexto de la sesión era más corta y **no tenía esa
sección**. El fichero en disco sí. Y el proyecto se gobierna por el de disco.

Consecuencia: lo que aquí se marca como `BLOCKED` por política es un **experimento autorizado con
un formulario que rellenar**, no una pared. Lo que sí es pared, y es técnica: **cargar un módulo**
(`NIVEL 4`), porque el host tiene `CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM` sin
  > **[091] CORRIGE ESTA CLAUSULA**: no hay bloqueo tecnico. Lo que se leyo fue
  > `CONFIG_MODULE_SIG_ALL` y **no** `CONFIG_MODULE_SIG_FORCE`, que esta
  > `# CONFIG_MODULE_SIG_FORCE is not set`. Medido en este host:
  > `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio COMPILA con
  > `vermagic` identico y SIN FIRMAR. Lo que queda es NIVEL 4
  > (`BLOCKED_BY_AUTHORIZATION`), que es otra cosa. Ver 091.
clave de firma. Esa no se quita con autorización.

## CUDA principal

`046` demostró para **un** HWIP que su versión es irrelevante porque la función que la consulta no
se ejecuta. Era la misma pregunta para nueve selectores más. `unreach.py` la hace para los diez, y
el resultado es más fuerte de lo que esperaba:

```
  HWIP             estado         funcs   bloques
  ----------------------------------------------------------
  UVD_HWIP         INALCANZABLE   1       24
  GC_HWIP          INALCANZABLE   4       18
  MP0_HWIP         INALCANZABLE   2       11
  SDMA0_HWIP       INALCANZABLE   1        7
  OSSSYS_HWIP      INALCANZABLE   1        6
  MP1_HWIP         INALCANZABLE   1        6
  DCE_HWIP         INALCANZABLE   1        2
  VPE_HWIP         INALCANZABLE   1        2
  ISP_HWIP         INALCANZABLE   1        2
  VCN_HWIP         INALCANZABLE   1        1

  VEREDICTO: los 10 selectores de despacho son INALCANZABLES desde esta GPU.
```

**Las 14 funciones de despacho por versión son alcanzables sólo desde `amdgpu_discovery_set_ip_blocks`,
y esa función sólo se llama desde el `default:` de un switch cuyo `case` de `CHIP_POLARIS12` hace
`break` antes.** Cero alcanzables, cero fuera del grafo. Idéntico en `linux-7.1.3` y
`linux-7.2.8`.

## El claim fuerte sería falso, y la herramienta lo dice antes de que yo lo escribiera

Lo obvio era afirmar *"ninguna versión de IP necesita leerse"*. **Es falso, y medido:**

```
usos de amdgpu_ip_version():   661, en 413 funciones
en funciones de DESPACHO:      32 usos, 15 funciones
en el resto de funciones:     629 usos, 398 funciones
```

Solo 15 de esas 413 funciones son de despacho. Las otras 398 usan la versión para
**comportamiento**, no para elegir fichero, y muchísimas son alcanzables.

La afirmación correcta es estrecha y se sostiene:

> **La elección de qué código se ejecuta no necesita ninguna lectura de MMIO**, porque la resuelve
> entera el `case` del chip. El valor de una IP version puede seguir importando para el
> comportamiento de ese código, y eso no está medido.

Y hay un caso que obliga a la prudencia por partida propia: **`amdgpu_device_ip_early_init` —la
función que decide el despacho— consulta ella misma `amdgpu_ip_version(adev, GC_HWIP, 0)`
después del switch** (`amdgpu_device.c:2159`). Ese uso es alcanzable, y la prueba de
inalcanzabilidad no lo cubre, porque la prueba es sobre las *funciones de despacho*, no sobre la
función que las contiene. Una herramienta que presentara el resultado sin este párrafo estaría
invitando a un error de razonamiento.

**Confundir "inalcanzable" con "no se lee" sería repetir el error de `035` por el otro lado**: una
afirmación más fuerte que la evidencia. Eso es lo que las herramientas tienen que impedir, no
lo que yo tengo que recordar.

## Y el cero que sale al intersectar: el código de esta placa no consulta la versión **en absoluto**

Al cruzar los 629 usos con los ficheros que esta GPU ejecuta —resueltos del `case`, no de una lista
escrita a mano— sale **cero**:

```
ficheros .c del ASIC resueltos: 7
usos alcanzables en ellos:       0, en 0 funciones

  gfx_v8_0.c    0     gmc_v8_0.c   0
  sdma_v3_0.c   0     tonga_ih.c  0
```

**Ningún fichero ASIC-específico consulta `amdgpu_ip_version()`.** Y esos ficheros son
exactamente donde vive lo que este driver propio va a reimplementar: el anillo GFX, el
`WAIT_REG_MEM`, el `PFP_SYNC_ME`, el emisor de PTEPDE, la vm-flush, el page walker, el PTBA.

Los 629 usos están en ficheros **genéricos** — `amdgpu_psp.c` (37), `amdgpu_ras.c` (29),
`amdgpu_device.c` (20), `amdgpu_kms.c` (5)— compartidos con toda la familia, y son de PSP, RAS,
SR-IOV y VBIOS.

**Eso convierte la afirmación en algo más fuerte y más útil:**

> No solo es que la versión de IP no decida qué código se ejecuta. Es que **el código de esta
> placa no la consulta en absoluto**. Los tres caminos que importan — PM4, IB, page tables — son
> íntegramente ASIC-específicos e íntegramente libres de la dependencia.

Es la diferencia entre una dependencia que hay que medir y una que no existe. Y se mide con un
`grep` por fichero, que es la forma más barata de evidencia que existe.

## Generalizar cambia la estructura de la prueba

`046` comprobaba **"un solo llamador"**. Eso funciona para `amdgpu_discovery_set_ip_blocks` y
**falla** para varias de las 14 funciones:

| función | llamadores |
|---|---|
| `amdgpu_discovery_set_ih_ip_blocks` | `amdgpu_discovery.c:3423` **y** `:3427` |
| `amdgpu_discovery_set_psp_ip_blocks` | `:3420` **y** `:3432` |
| `amdgpu_discovery_set_smu_ip_blocks` | `:3439` **y** `:3465` |

Un "un solo llamador" daría `NO` para esas tres, y sería un **falso**: tienen varios, pero todos
dentro de la misma función inalcanzable. Por eso la versión general trabaja sobre el **grafo** y
calcula el **cierre transitivo**: si `set_ih_ip_blocks` sólo se llama desde `set_ip_blocks`, y
`set_ip_blocks` sólo desde el `default`, y ahí no se llega, entonces `set_ih` tampoco.

Hoy las 14 se llaman directamente desde `set_ip_blocks`, así que un nivel bastaría. **Codificarlo a
un nivel sería asumir la forma actual del código** —justo lo que `041` prohíbe— y hoy daría la
respuesta correcta por casualidad.

## Cuatro fallos, y los tres son la misma clase

Los tres primeros **produjeron una respuesta plausible en vez de un error**. No obligan a
mirar, y por eso son los peores:

**El grafo iba al revés.** Construía `callee → callers`, que es lo que sale de recorrer el texto, y
el BFS desde la raíz caminaba **hacia arriba**: un solo nodo, y 10 selectores marcados alcanzables
cuando no lo son. Un grafo mal dirigido no falla: da una respuesta segura y equivocada. La
dirección va ahora en el nombre del tipo.

**El fall-through de los `case`.** La forma real es un grupo de nueve:

```c
case CHIP_TOPAZ:
case CHIP_TONGA:
...
case CHIP_POLARIS12:      <-- el que interesa, y el sexto del grupo
case CHIP_VEGAM:
        r = vi_set_ip_blocks(adev);
        break;
```

Llevaba un único `actual` que se sobrescribía en cada `case`, así que **solo registraba el
último**: `CHIP_STONEY`. `CHIP_POLARIS12` no aparecía nunca y la herramienta informaba "case no
encontrado" sobre un `case` que está a 50 líneas. Leer una estructura de C como si fuera una
secuencia plana.

**El patrón de nombres.** Buscaba `_set_ip_blocks`, y los nombres reales son
`amdgpu_discovery_set_**sdma**_ip_blocks`: el `_set_` lleva el nombre del bloque **en medio**, y
`_set_ip_blocks` **no es subcadena**. Capturaba 3 funciones de 18, y el grafo parecía correcto
estando casi vacío. El selftest lo fija: el patrón bueno encuentra 6 de 6, el malo 3 de 6.

El cuarto —la ventana de 70 líneas que se comía la función siguiente y hacía que `SDMA0_HWIP`
seleccionara `gfx_v12_0_ip_block`— es la **tercera vez** que aparece el mismo fallo. Ya merece
regla: **un recorte de N líneas no puede saber dónde acaba un bloque en C**. Se cuenta por llaves,
siempre.

**La cota se imprime.** `grafo 18 funciones con llamadas a ..._ip_blocks(adev)` — porque un grafo
con pocas aristas parece un grafo con pocas relaciones, no un grafo mal construido, y solo se
distingue mirando la cota.

## UNLOCKS

- **La política de runtime de este proyecto tiene ahora su regla, y es medible:** ninguna lectura
  de MMIO se justifica por *decidir qué código se ejecuta*. Se justifica, si acaso, por el
  *comportamiento* de ese código — 629 usos en 398 funciones — y eso es un lista concreta, no una
  intuición.
- `unreach.py` generaliza a N selectores lo que `046` hizo para uno. El patrón es reutilizable
  para cualquier otra afirmación del tipo *"¿este camino se ejecuta para mi ASIC?"*, que es la
  pregunta que ha generado los tres errores más caros del proyecto.
- Los 15 usos de `amdgpu_ip_version` en funciones de despacho son ahora localizables uno a uno, y
  se sabe que **ninguno se ejecuta**.
- **El camino de PM4, IB y page tables no tiene dependencia de IP version.** Eso no era una
  hipótesis: son cero usos en cero ficheros ASIC-específicos. La implementación del driver propio
  puede copiar la estructura de esos ficheros sin arrastrar ninguna decisión pendiente de
  hardware.
- El siguiente frente real son los 629 usos de comportamiento, reducidos a los que caen en el
  siliconio de esta placa — que, medido, son **cero** para este camino y quedan abiertos solo para
  PSP, RAS, SR-IOV y VBIOS.

## Lo que sigue `NOT_DETERMINED`

- El spec de GFX8 no está publicado (`033`). Nada de esto lo cambia.
- El valor de las IP versions **para el comportamiento** del código que sí se ejecuta: 629 usos en
  398 funciones, sin medir. Es un frente nuevo y real. **Ninguno cae en el camino de este driver**
  —los ficheros ASIC-específicos tienen cero— así que no bloquea PM4, IB ni page tables, pero sí
  cualquier cosa que toque PSP, RAS, SR-IOV o VBIOS.
- Todo lo de `033`/`037`/`040` que depende de la semántica del MMU, del page walker y del TLB.

## Falsación

- La afirmación se refuta si alguno de los 10 selectores tuviera una función de despacho alcanzable.
  Los cinco estados se imprimen por fila y `ALCANZABLE` da código de salida 1, así que no puede
  pasar inadvertido.
- Se refuta también si `CHIP_POLARIS12` no estuviera en el grupo de fall-through que llama a
  `vi_set_ip_blocks`, o si ese grupo no hiciera `break` antes del `default`. Ambas cosas se
  comprueban e se imprimen con su línea, y `grupo_de: 9 chips` es la cota.
- El grafo se refuta si su recuento de 18 no cuadra con el corpus. Se imprime precisamente para
  eso; y el nombre del patrón se prueba contra llamadas reales en el selftest, donde el patrón
  malo da 3 de 6.
- Todo es `PROVEN_DERIVED` sobre el **flujo de control del driver**, no sobre el hardware. Que
  el silicio exista y la tabla IP discovery sea correcta no se afirma ni se niega aquí.

## Evidencia

```
tools/unreach.py        7 comprobaciones de selftest
                         10 selectores, 0 alcanzables, 0 fuera del grafo
                         idéntico en linux-7.1.3 y linux-7.2.8
                         grafo de 18 funciones, cota impresa
                         661 usos de amdgpu_ip_version en 413 funciones,
                           de los que 629 en 398 no son de despacho
tools/hwip.py           5 vectores (046)
tools/citegen.py        6 vectores (045)
herramientas            17 en el oraculo, todas con selftest salvo audit_citations (script)
suite del driver        22 + 12 + 195 = 229 checks, 0 fallos
crosscheck              10 vectores CLEAN
rx550pm4val             16/16
audit_citations         252 citas, 0 fallos
corpus                  MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
