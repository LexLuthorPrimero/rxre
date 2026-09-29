# RE02-DECISION-REGISTER — decisiones de gobernanza de la línea RE-02

**WORK_CLASS** `DOCUMENTATION`. Registro **versionado y fechado**, separado de
`AGENTS.md` porque §10.2 exige que las decisiones no vivan en línea en un fichero que
envejece, y separado de `RESEARCH/polaris12xl/docs/DECISION-REGISTER.md` porque ese
fichero declara scope propio — *«decisiones arquitectónicas de `polaris12xl`»* — y RE-02
**no es** `polaris12xl`. Prefijo `RG-n` (**R**E-02 **G**overnance) elegido por la misma
lógica de no-colisión que el registro `polaris12xl` declara para `AD-n`.

| Prefijo | Qué registra | Dónde |
|---|---|---|
| `RG-n` | decisiones de gobernanza y alcance de la línea RE-02 | este fichero |
| `AD-n` | decisiones de arquitectura del modelo C de `polaris12xl` | `RESEARCH/polaris12xl/docs/DECISION-REGISTER.md` |
| `D-nn` | defectos encontrados y reparados | `RESEARCH/polaris12xl/docs/04-DEFECT-REGISTRY.md` |
| `D1..D10` | reconciliación documental | `01-AUDITORIA/DECISIONES-D1-D10.md` |

---

## RG-1 — `HUMAN_POLICY`: autorización de alcance de RE-02 y de su instrumentación

| Campo | Valor |
|---|---|
| **DECISION** | **AUTORIZAR RE-02** como línea de investigación del proyecto |
| **DECIDER** | `HUMAN` |
| **DATE** | `2026-09-28` |
| **Forma** | *autorización explícita*, emitida en sesión a raíz del `GATE 0 = SCOPE_NOT_CONFIRMED` emitido por la auditoría adversarial el 2026-09-28 |
| **Origen del gate** | `SCOPE_NOT_CONFIRMED` por **insuficiencia de evidencia de autorización**, nunca por exclusión. Los seis depositarios de alcance (`MASTER-RESEARCH-STATUS.md`, `MASTER-PLAN.md`, `DOCUMENTATION-ROUTER.md`, `DECISIONES-D1-D10.md`, ambos registros de decisión) daron **0** coincidencias de RE-02 |

### SCOPE — lo que queda autorizado, artículo por artículo

| # | Autorizado | Naturaleza |
|---|---|---|
| 1 | RE-02 queda autorizado como **línea de investigación** del proyecto | `GOVERNANCE` |
| 2 | **Análisis estático** de la implementación amdgpu relacionada con PDE/PT | `READ_ONLY_EVIDENCE` |
| 3 | **Construir instrumentación experimental mínima en C** para observar PDE/PT en Polaris12/RX 550 | `STATIC_IMPLEMENTATION` → `RUNTIME_PREFLIGHT` |
| 4 | **Compilar y ejecutar** kernels/driver modificados **únicamente** como parte de experimentos explícitamente definidos | `RUNTIME_EXECUTION`, condicionada |
| 5 | Los primeros cambios C **exclusivamente** instrumentación/observabilidad, **reversibles y aislados** | `SYSTEM_CHANGE`, acotada |

### Lo que esta autorización **NO** es, y queda dicho para que un solo mensaje lo revoque

> - **NO** autoriza cambiar el **comportamiento funcional** del driver. La instrumentación
>   observa; no modifica semántica.
> - **NO** autoriza optimización permanente, ni ahora ni como consecuencia de la
>   instrumentación.
> - **NO** autoriza alterar políticas funcionales de **scheduling, memoria, page tables,
>   CGPG, MEC, power management** ni ningún otro mecanismo del driver con finalidad de
>   optimización. Nótese el alcance: esto alcanza a las *políticas*, no a la *lectura*.
>   Leer `amdgpu_vm_pde_update()` es análisis estático (art. 2); cambiar qué MEC o qué cola
>   se usa sigue prohibido.
> - **NO** es autorización retroactiva. **Las conclusiones anteriores conservan
>   exactamente su estado de evidencia.** En particular, y sin excepción:
>   `MEC2_HARDWARE_CAPABILITY = UNKNOWN` · `MEC2_CAPABLE_HARDWARE = UNKNOWN` ·
>   `CGPG_CAUSALITY = UNKNOWN` · `QUEUE0_CAUSAL_ORIGIN = UNKNOWN` ·
>   `POLARIS12_CAPABILITY = NOT_DETERMINED` · `READABILITY = NOT_PROVEN` ·
>   `MEC2_NOT_USED_BY_AMDGPU_7_1_3 = INVALIDATED` permanece `INVALIDATED`.
> - **NO** habilita D-1 ni D-2 de forma automática: quedan autorizados *como trabajo*,
>   no *como conclusión*. Su resultado, si se investiga, se registra con su propia evidencia.
> - **NO** deroga las prohibiciones vigentes de `AGENTS.md` §13.2 (sin `sudo`, sin módulos,
>   sin escrituras en sysfs, sin `git commit`/`push`) ni los `deny` del motor
>   (`opencode.json`). Los arts. 3–5 operan **dentro** de esos límites: no los amplían.
> - **NO** es una aprobación previa de la viability de la instrumentación. Si el
>   instrumento resulta inviable, la línea se cierra como `BLOCKED`, no se fuerza.

### Requisitos exigidos a cada experimento

Cada experimento definido bajo esta autorización **debe** declarar, **antes** de
ejecutarse:

| Campo | Contenido |
|---|---|
| `QUESTION` | la pregunta falsable |
| `PREDICTION` | lo esperado, escrito **antes** de la observación |
| `CRITERION` | `PASS` / `FAIL` / `UNKNOWN` — y `PASS` exige evidencia de que la condición se cumple |
| `ROLLBACK` | vía de restauración documentada e independiente |
| `EVIDENCE` | artefacto reproducible y su `SHA256` |

`NOISE = NOT_DETERMINED` si no se mide: en ese caso **ningún** tamaño de efecto se
reporta como pequeño, ausente o significativo, sino `UNINTERPRETABLE` (AGENTS.md §9.1).

### Consecuencia inmediata sobre el `GATE 0`

`GATE 0` transiciona de `SCOPE_NOT_CONFIRMED` a **`SCOPE_CONFIRMED`**. El bloqueo era de
**gobernanza**, no de evidencia: el primer discriminante de §28.3
(`OBSERVABILITY_STATUS = REQUIRES_NEW_INSTRUMENTATION`) deja de estar bloqueado por falta
de permiso y queda bloqueado, si acaso, por falta de instrumento — que es una categoría
distinta y debe re-declararse.

### Asimetría que esta decisión no repara, y se registra

La línea `polaris12xl` aplicó `AGENTS.md` §11.1 (`PROMPT_CRITIQUE`) en
`RESEARCH/polaris12xl/docs/00-PROMPT-CRITIQUE.md`. Las rondas RE-02 **no** lo hicieron, y
por eso el `GATE 0` no se había aplicado hasta ahora. `CAUSA` del retardo: la existencia
previa del trabajo operó como autorización de facto. **Un precedente no es una
autorización.** `RG-1` repara el alcance; no repara el proceso, y el proceso queda
registrado como pendiente de `PRECONDITION`.

**Reversión**: un *«no»*, un *«eso no era»* o un *«revoca RG-1»* en la siguiente línea
devuelve la línea a `SCOPE_NOT_CONFIRMED` y `D-1`/`D-2` vuelven a estar bloqueados por
gobernanza. Nada de lo que se escriba bajo esta autorización queda sin vuelta atrás: cada
cambio C instrumental se registra con su hash y su `ROLLBACK`, y §12.4 obliga a preservar
el estado previo.

### Estado del registro

| Decisión | Estado | DATE |
|---|---|---|
| `RG-1` | **ADOPTADA** | 2026-09-28 |

Sin más entradas. Este fichero existe únicamente porque el gate lo exigía: hasta
`2026-09-28`, `RE-02` no tenía registro de decisión y por eso era
`SCOPE_NOT_CONFIRMED` aunque tuviera 6 000 líneas de análisis.
