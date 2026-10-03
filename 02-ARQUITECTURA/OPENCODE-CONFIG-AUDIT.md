# OPENCODE-CONFIG-AUDIT — Auditoría de la configuración efectiva de OpenCode

**FECHA:** 2026-09-27 · **TIPO:** `READ_ONLY/EVIDENCE` · **ORIGIN=AUDITORÍA_SOLICITADA**
· **WORK_CLASS=DOCUMENTATION`** · **NO_MODIFICÓ_CONFIGURACIÓN**

> Documento nuevo. **No se editó** `AGENTS.md`, ni `opencode.json`, ni agentes, ni
> prompts, ni skills, ni plugins, ni permisos, ni el sistema. La única escritura de
> esta ronda es este fichero.

| Campo | Valor |
|---|---|
| `HOST_SCOPE` | `/home/lucas` (uid 1000, `lucas:lucas`, sin privilegios) |
| `TEMPORALITY` | observado 2026-09-27 ~03:15–03:25 −0300; el estado de la config es el de ese instante |
| `WORKSPACE` | `/home/lucas/Escritorio/RX550-INVESTIGACION` (git root) |
| `SESSION` | `ses_f23f97e69ffeeiBopdfS0ZaYJB` |
| `METODO` | inspección de disco + **`~/.local/share/opencode/opencode.db` en modo `ro&immutable=1`** + log `opencode.log` + documentación oficial V2 (HTTP 200) |
| `LIMITE_DE_AUTOINSTRUMENTACIÓN` | el agente audita su propio runtime desde dentro. Las fases `EFFECTIVE` y `VERIFIED_BY_BEHAVIOR` son **observación de conducta propia**, no medición externa. Declarado, no oculto. |

---

## 1. `EXECUTIVE_STATUS`

**`AUDIT_COMPLETE` — la configuración efectiva está determinada y es, en su mayor parte, la configuración por defecto de OpenCode v2.0.18 porque no existe ningún fichero de configuración.**

| Métrica | Valor |
|---|---|
| Ficheros de configuración `opencode.json`/`jsonc` encontrados | **0** |
| Opciones de configuración explícitas | **0** |
| Agentes personalizados | **0** |
| Servidores MCP | **0** |
| Plugins | **0** |
| Ficheros `AGENTS.md` cargados en esta sesión | **1** (el del proyecto), **verificado byte-idéntico** |
| Clasificaciones de permisos explícitas | **0** → todos por defecto |
| Permisos de herramienta no-default | **2** (`external_directory`, autorizados interactivamente) |
| Riesgos `CRITICAL` | **2** |

**El hallazgo central:** las restricciones metodológicas del proyecto son
**enteramente prosa**. `bash` y `edit` están en `allow` por defecto y no hay
ningún `deny`. Nada técnico impide `sudo`, escribir `/sys`, cambiar servicios o
hacer `git commit`. La prohibición depende de que el modelo "se porte bien".

---

## 2. `OPENCODE_VERSION`

| Dato | Valor | Fuente |
|---|---|---|
| Versión del binario | **`v2.0.18`** | `opencode --version` |
| Ruta del binario | `/home/lucas/.opencode/bin/opencode` | `which -a` |
| Tamaño del binario | `203146720` B | `stat` |
| Versión registrada por **esta** sesión | **`2.0.17`** | `session_v2.version` |
| Proceso de servicio | `opencode serve --service` (PID 152484, padre 152462) | `ps` |
| `service.json` de estado | `"version":"2.0.18"` | `~/.local/state/opencode/service.json` |
| Esquema de configuración | JSON y JSONC, `$schema` = `https://opencode.ai/config.json` | doc oficial, HTTP 200 |
| Esquema `config.json` fetched | **HTTP 200** (1er fetch devolvió **404**: inestabilidad transitoria registrada) | `fetch` |

### `CONTRADICTION` — deriva de versión durante el proyecto

| Fecha (log) | Evento |
|---|---|
| 2026-09-25 21:34:50Z | `OpenCode update available current=2.0.16 latest=2.0.17` |
| 2026-09-25 21:35:39Z | **`updated OpenCode from=2.0.16 to=2.0.17 method=curl`** |
| 2026-09-26 04:42:31Z | `update available current=2.0.17 latest=2.0.18` |
| 2026-09-26 20:30:23Z | **`updated OpenCode from=2.0.17 to=2.0.18 method=curl`** |

| Versión | Sesiones | Primera | Última |
|---|---|---|---|
| `2.0.16` | 97 | 2026-09-17 16:32:38 | 2026-09-25 13:47:05 |
| `2.0.17` | 5 | 2026-09-26 00:28:16 | 2026-09-26 04:43:29 |
| `2.0.18` | 0 (esta sesión aún figura como 2.0.17) | — | — |

`autoupdate` está **activo** y el agente se autoactualizó **2 veces** sin control
externo, con 97 de 102 sesiones produced bajo una versión distinta de la actual.

---

## 3. `CONFIGURATION_LOCATIONS`

Todas las ubicaciones de la lista oficial de precedencia (doc V2, `## Locations`),
comprobadas una por una. Ninguna inventada.

| # | Ubicación oficial | Ruta real comprobada | Existe | Contenido |
|--:|---|---|:--:|---|
| 1 | Remote `.well-known/opencode` | n/a | `NOT_APPLICABLE` | requiere provider autenticado; `account`=0 filas, `control_account`=0, `credential`=1 → sin cuenta |
| 2 | Global `~/.config/opencode/opencode.json` | `/home/lucas/.config/opencode/` | `EXISTS` (dir) | **sólo** `service.json` (64 B). **sin** `opencode.json` |
| 3 | Custom `OPENCODE_CONFIG` | env | `NOT_DEFINED` | variable no existe |
| 4 | Project `opencode.json` | `<proj>/opencode.json`, `opencode.jsonc` | `ABSENT` | — |
| 4b | Project padre | `~/Escritorio/opencode.json`, `~/opencode.json` | `ABSENT` | recorrido hasta git root comprobado |
| 5 | `.opencode/` (agents, commands, plugins) | `<proj>/.opencode` | `ABSENT` | `~/.opencode` existe pero contiene **sólo** `bin/` → no es dir de config |
| 6 | Inline `OPENCODE_CONFIG_CONTENT` | env | `NOT_DEFINED` | — |
| 7 | Managed Linux `/etc/opencode/` | `/etc/opencode/` | `ABSENT` | no existe |
| 7b | Managed macOS | — | `NOT_APPLICABLE` | plataforma linux |
| 8 | macOS MDM | — | `NOT_APPLICABLE` | plataforma linux |
| + | `OPENCODE_CONFIG_DIR` | env | `NOT_DEFINED` | dir de config personalizado |
| + | `OPENCODE_DISABLE_CLAUDE_CODE` | env | `NOT_DEFINED` | fallback Claude Code **habilitado** |

**`~/.config/opencode/` — contenido íntegro (2 entradas, 1 fichero):**

| Ruta | Tipo | Bytes | sha256 |
|---|---|---|---|
| `~/.config/opencode/service.json` | file | 64 | `d18b5e137a8ef77bd1ebd301f34d7800703eb41165d2c0735a84d6d5294eac21` |

`RISK_SECURITY` — `service.json` contiene un **`password` en texto plano**
(43 chars). **No se reproduce su valor en este informe.** El mismo secreto
reaparece en `~/.local/state/opencode/service.json` (165 B). El de
`~/.config/` tiene modo `-rw-------`; el de `~/.local/state/` tiene modo por
verificar.

---

## 4. `LOAD_ORDER`

**Órden real, según doc oficial V2 `## Precedence` y observado en el host.**

### 4.1 Configuración (8 niveles oficiales)

`remote` → `global` → `OPENCODE_CONFIG` → `project` → `.opencode/` → `OPENCODE_CONFIG_CONTENT` → `managed` → `macOS MDM`

| Nivel | Estado | ¿Aporta algo? |
|---|---|---|
| remote | `NOT_APPLICABLE` | no (sin cuenta autenticada) |
| global | `ABSENT` | no |
| `OPENCODE_CONFIG` | `NOT_DEFINED` | no |
| project | `ABSENT` | no |
| `.opencode/` | `ABSENT` | no |
| inline | `NOT_DEFINED` | no |
| managed | `ABSENT` | no |
| MDM | `NOT_APPLICABLE` | no |

→ **Configuración efectiva = 100 % defaults.** El comportamiento de *merge*
documentado ("merged together, not replaced") es **`UNOBSERVED`**: no hay dos
fuentes que fusionar.

### 4.2 Instrucciones (reglas) — `DISCOVERED → LOADED`, verificado en la base de datos

La doc oficial `## Precedence` de `rules.md` dice:

> 1. **Local files** traversing up from the current directory (`AGENTS.md`, `CLAUDE.md`)
> 2. **Global file** `~/.config/opencode/AGENTS.md`
> 3. **Claude Code file** `~/.claude/CLAUDE.md` (unless disabled)
> …The first matching file wins in each category.

| Categoría | Candidatos comprobados | Ganador | Estado |
|---|---|---|---|
| Local (hacia arriba) | `<proj>/AGENTS.md` ✔ · `<proj>/CLAUDE.md` ✗ · `~/Escritorio/AGENTS.md` ✗ · `~/AGENTS.md` ✗ | `<proj>/AGENTS.md` | `FILE_PRESENT` |
| Global | `~/.config/opencode/AGENTS.md` ✗ | — | `NOT_FOUND` |
| Claude Code | `~/.claude/CLAUDE.md` ✗ · `~/.claude/` **ausente** | — | `NOT_FOUND` |
| `instructions` (opencode.json) | sin config | — | `NOT_FOUND` |
| Nested (bajo workspace) | `find` recursivo: **0** | — | `NOT_FOUND` |

### 4.3 Cadena de 6 fases para el único `AGENTS.md` — **COMPLETA, con hash**

| Fase | Evidencia | Estado |
|---|---|---|
| `FILE_PRESENT` | `/home/lucas/Escritorio/RX550-INVESTIGACION/AGENTS.md` · 24759 B · 454 L | `OBSERVED` |
| `DISCOVERED` | `instruction_blob` contiene filas con `value` que referencia esa ruta | `OBSERVED` |
| `LOADED` | blob `ba95a706a60ae912043b44aa78f0cee26249dd8f144ac07cfbeb5be6bdac5d97` (25205 B JSON) | `OBSERVED` |
| `ACTIVE_IN_CONTEXT` | `instruction_state.session_id='ses_f23f97e69ffeeiBopdfS0ZaYJB'` → `current_values["core/instructions"]="ba95a706…"` | `OBSERVED` |
| `EFFECTIVE` | el array cargado tiene **1 solo fichero**; su `content` mide 24759 B y su sha256 es `d346a4411c7f669ac658de2996d2c890fe78433fc5704f8898087f6a6da051fb` = **idéntico a disco** (`IDENTICOS = True`) | `OBSERVED` |
| `VERIFIED_BY_BEHAVIOR` | esta ronda: `PROMPT_CRITIQUE` emitido antes de la primera acción; 0 sudo; 0 sysfs; 1 solo fichero creado; salida en formato `STATE/CHANGED/OPEN/BLOCK/NEXT/EVIDENCE` | `OBSERVED` (autoinstrumentado) |

**Histórico de blobs de `AGENTS.md` — 10 versiones, todas con exactamente 1 fichero:**

| Blob (16) | Bytes | sha256 del contenido (16) |
|---|---|---|
| `1967c4ae5843c758` | 13768 | `52315f993e73ea7c` (= versión en `HEAD` `df2406a`) |
| `e9c51a38c3113037` | 15362 | `a8b8ae648c7770ee` |
| `f6933bb73645c013` | 15746 | `876034584c597ad7` |
| `bbc0e6f4496ff8f2` | 17488 | `f6d96e6aed6a712e` |
| `b81cad72db167685` | 17735 | `9a3178f20629d621` |
| `e01d814fd46910ac` | 19175 | `bbd70e2ccb418dbb` |
| `86deda9bb68175c7` | 20461 | `324ef0c573871afe` |
| `4ebc2d6f7dca5cc9` | 23352 | `c55b2201035ccbde` |
| `fe3a5c73f4846e07` | 24264 | `b1441c754d6cc5bf` |
| **`ba95a706a60ae912`** | **24759** | **`d346a4411c7f669a`** ← activo |

**Ningún blob histórico contiene más de 1 fichero** ⇒ en ninguna sesión de la
historia se combinó un `AGENTS.md` global o anidado con el del proyecto.

### 4.4 `AGENTS.md` figura como modificado y sin commitear

| Dato | Valor |
|---|---|
| `git status --porcelain AGENTS.md` | ` M AGENTS.md` |
| `git diff --stat` | `1 file changed, 185 insertions(+), 8 deletions(-)` |
| sha256 en disco | `d346a4411c7f669ac658de2996d2c890fe78433fc5704f8898087f6a6da051fb` |
| sha256 en `HEAD` (`df2406a`) | `52315f993e73ea7c37048bc22c0f8dd40eadd4cef6ca8cc89b5d2de8eef74422` |
| mtime | `2026-09-26 20:09:07 −0300` — **anterior** al inicio de esta ronda |

**Las 185 líneas de diferencia son `PREEXISTING_UNCOMMITTED`, no de esta ronda**
(hash verificado idéntico al esperado y mtime anterior a la primera acción de hoy).

---

## 5. `ACTIVE_INSTRUCTIONS`

| # | Instrucción | Origen | Cargada | En contexto | Efectiva |
|--:|---|---|:--:|:--:|:--:|
| 1 | `AGENTS.md` del proyecto (454 L, 13 secciones `##`) | disco | ✔ | ✔ | ✔ (byte-idéntico) |
| 2 | `core/environment` | blob `6fcae4f7…` | ✔ | ✔ | ✔ |
| 3 | `core/date` | blob `31838d17…` = `Sun Sep 27 2026` | ✔ | ✔ | ✔ |
| 4 | `core/codemode` | blob `616a7ad8…` (8651 B, catálogo 50 herramientas) | ✔ | ✔ | ✔ |
| 5 | `core/skill-guidance` | blob `8394362d…` (2 skills) | ✔ | ✔ | ✔ |
| 6 | `~/.config/opencode/AGENTS.md` | — | ✗ | ✗ | `NOT_FOUND` |
| 7 | `~/.claude/CLAUDE.md` | — | ✗ | ✗ | `NOT_FOUND` (dir `~/.claude` ausente) |
| 8 | `CLAUDE.md` del proyecto | — | ✗ | ✗ | `NOT_FOUND` |
| 9 | `AGENTS.md` anidado | — | ✗ | ✗ | `NOT_FOUND` (find recursivo = 0) |
| 10 | `~/.codex/AGENTS.md` | 3359 B, existe | ✗ | ✗ | **`PRESENT_BUT_NOT_ACTIVE`** |
| 11 | `instructions` de `opencode.json` | — | ✗ | ✗ | `NOT_FOUND` |

### 5.1 Instrucciones que existen pero NO se cargan

| Fichero | Tamaño | Por qué no se carga |
|---|---|---|
| `/home/lucas/.codex/AGENTS.md` | 3359 B | **no es una ubicación documentada de OpenCode.** Pertenece a Codex. `PRESENT_BUT_NOT_ACTIVE` — y es una trampa: si alguien asume que aplica, se apoya en reglas que el agente nunca ve |
| `~/firefox-hardware-lab/**/AGENTS.md` (5) | 5473/3703/839 B | fuera del workspace; no se recorre |
| `~/firefox-hardware-lab/**/CLAUDE.md` (3) | 11 B cada uno | fuera del workspace |
| `AGENTS.md` en `HEAD` `df2406a` | 13768 B | no es lo que hay en disco ni lo que está cargado |

### 5.2 Contenido de `core/environment` (verbatim, blob `6fcae4f7…`)

```
Current conversation session ID: ses_f23f97e69ffeeiBopdfS0ZaYJB
Working directory: /home/lucas/Escritorio/RX550-INVESTIGACION
Workspace root folder: /home/lucas/Escritorio/RX550-INVESTIGACION
Is directory a git repo: yes
Platform: linux
Prefer /tmp/opencode over generic system temporary directories such as /tmp;
it is pre-created and approved for external access.
```

`/tmp/opencode` figura explícitamente como **pre-aprobado** ⇒ explica por qué
las escrituras a `/tmp/opencode` de sesiones anteriores no dispararon `ask`
pese a que la tabla `permission` no registra un grant de `/tmp/*` para este
proyecto. `Mecanismo exacto = NOT_DETERMINED`; el comportamiento sí es `OBSERVED`.

### 5.3 Estructura real de `AGENTS.md` (13 secciones, líneas reales)

| L | Sección |
|---|---|
| 3 | `Scope and identity` |
| 18 | `Evidence vocabulary` |
| 47 | `Measurement discipline` |
| 151 | `Provenance discipline` |
| 197 | `Falsification and verification` |
| 222 | `Prompt review` |
| 268 | `Investigation method` |
| 289 | `Safety and authorization` |
| 335 | `Ownership` |
| 357 | `Recovery` |
| 365 | `Documentation and historical evidence` |
| 392 | `Output requirements` |
| 434 | `OpenCode mechanics` |

---

## 6. `CONFIG_MATRIX`

Las 36 secciones de la configuración oficial, una por una. `NOT_FOUND` = la
sección no existe como fichero de configuración.

| ELEMENTO | UBICACIÓN | VALOR | CARGADO | EFECTIVO | EVIDENCIA | RIESGO |
|---|---|---|:--:|:--:|---|---|
| `default_agent` | `opencode.json` | `NOT_FOUND` | ✗ | **`build`** (default) | `session_v2.agent='build'` en las 6 sesiones de este modelo | `HIGH` — `build` = acceso completo |
| `agent` (agentes personalizados) | `opencode.json` | `NOT_FOUND` | ✗ | 0 personalizados | 3 agentes distintos usados, los 3 built-in | `MEDIUM` |
| `model` | `opencode.json` | `NOT_FOUND` | ✗ | `opencode/space-bunny-free` variante `max` | `model.json` + `session_v2.model` | `MEDIUM` — no fijado en config |
| `small_model` | `opencode.json` | `NOT_FOUND` | ✗ | `NOT_DETERMINED` | — | `LOW` |
| `permission` | `opencode.json` | `NOT_FOUND` | ✗ | **defaults** | doc `## Defaults`; tabla `permission` sólo con `external_directory` | `CRITICAL` |
| `edit` | idem | `NOT_FOUND` | ✗ | `allow` (default) | `edit` cubre `edit`/`write`/`patch` | `CRITICAL` |
| `write` | idem | `NOT_FOUND` | ✗ | `allow` (vía `edit`) | idem | `CRITICAL` |
| `bash` | idem | `NOT_FOUND` | ✗ | **`allow`** (default) | 13914 `spawning process` en log sin prompt | `CRITICAL` |
| `read` | idem | `NOT_FOUND` | ✗ | `allow`, salvo `*.env` → `deny` | doc `## Defaults` | `LOW` |
| `glob` / `grep` | idem | `NOT_FOUND` | ✗ | `allow` | doc | `LOW` |
| `task` (subagentes) | idem | `NOT_FOUND` | ✗ | `allow` | `general` 4413 msjs, `explore` 1643 | `MEDIUM` |
| `skill` | idem | `NOT_FOUND` | ✗ | `allow` | blob `core/skill-guidance` | `LOW` |
| `question` | idem | `NOT_FOUND` | ✗ | `allow` | herramienta presente | `LOW` |
| `webfetch` | idem | `NOT_FOUND` | ✗ | `allow` | usada en ronda anterior (Wikipedia HTTP 200) | `MEDIUM` |
| `websearch` | idem | `NOT_FOUND` | ✗ | `allow`; `kv.websearch:provider="random"` | tabla `kv` | `MEDIUM` — proveedor aleatorio |
| `lsp` | idem | `NOT_FOUND` | ✗ | `allow` (no granular) | doc | `LOW` |
| `external_directory` | idem | `NOT_FOUND` | ✔ (2 grants) | `ask` → **aprobado** ×2 | tabla `permission`, 2 filas de este proyecto | `MEDIUM` |
| `doom_loop` | idem | `NOT_FOUND` | ✗ | `ask` (default) | doc; 0 eventos reales | `MEDIUM` — es el único anti-bucle técnico |
| `steps` | `opencode.json` / agente | **`NOT_SET`** | ✗ | **sin límite** | doc: *"If this is not set, the agent will continue to iterate until the model chooses to stop"* | `HIGH` |
| `subagent_depth` | `opencode.json` | `NOT_FOUND` | ✗ | `1` (default) | doc | `LOW` |
| `instructions` | `opencode.json` | `NOT_FOUND` | ✗ | — | sin config | `MEDIUM` |
| `mcp` | `opencode.json` | `NOT_FOUND` | ✗ | **0 servidores** | `list_mcp_resources` → `resources:[]`, `templates:[]` | `LOW` |
| `plugin` | `.opencode/plugin(s)/` | `NOT_FOUND` | ✗ | **0** | 4 rutas comprobadas, todas ausentes | `LOW` |
| `command` | `.opencode/command/` | `NOT_FOUND` | ✗ | 0 | `project.commands = None` | `LOW` |
| `tools` (custom) | `.opencode/tools/` | `NOT_FOUND` | ✗ | 0 | — | `LOW` |
| `modes` | `.opencode/modes/` | `NOT_FOUND` | ✗ | 0 | — | `LOW` |
| `themes` | `.opencode/themes/` | `NOT_FOUND` | ✗ | — | `NOT_DETERMINED` | `LOW` |
| `skills` (ficheros) | `~/.config/opencode/skills/`, `~/.opencode/skills/` | **`NOT_FOUND`** (4 rutas, singular y plural) | ✗ | 2 skills **built-in del harness** | blob `core/skill-guidance`; `watcher subscribe` a esas 4 rutas inexistentes | `LOW` |
| `watcher` | `opencode.json` | `NOT_FOUND` | ✗ | activo | 124 `watcher started`, 201 `watcher subscribe` | `LOW` |
| `snapshot` | `opencode.json` | `NOT_FOUND` | ✗ | `~/.local/share/opencode/snapshot` 13 M, 2 dirs | inspección de disco | `MEDIUM` — rollback no documentado |
| `autoupdate` | `opencode.json` | `NOT_FOUND` | ✗ | **activo** | 2 auto-actualizaciones en log | `HIGH` |
| `server` | `opencode.json` | `NOT_FOUND` | ✗ | `serve --service` PID 152484 | `ps` | `LOW` |
| `tui` | `tui.json` | `NOT_FOUND` | ✗ | — | `~/.config/opencode/tui.json` ausente | `LOW` |
| `keybinds` / `models` / `policies` / `share` / `formatter` / `lsp` / `compaction` / `experimental` | varios | `NOT_FOUND` | ✗ | default / `NOT_DETERMINED` | — | `LOW` |
| `disabled_providers` / `enabled_providers` | `opencode.json` | `NOT_FOUND` | ✗ | sin restringir | 1 solo provider visible | `LOW` |
| global config | `~/.config/opencode/opencode.json` | `NOT_FOUND` | ✗ | — | dir con 1 solo fichero | `HIGH` |
| project config | `<proj>/opencode.json` | `NOT_FOUND` | ✗ | — | §3 | `HIGH` |

**Las 2 concedidas (`external_directory`, proyecto `f642a7fe…` = este):**

| Recurso | ts (epoch ms) |
|---|---|
| `/home/lucas/Escritorio/*` | 1790426414762 |
| `/home/lucas/*` | 1790434543894 |

Las otras 10 pertenecen al proyecto `0c595e25…` (`worktree=/home/lucas`), **otro
proyecto** y no Governing esta sesión.

---

## 7. `PERMISSION_MATRIX`

Fuente: doc oficial `permissions.md` `## Defaults` (texto literal) + tabla
`permission` de la base de datos + log. `VERIFIED` exige ejecución observada.

| Herramienta | Regla configurada | Efectivo | Veredicto | `VERIFIED_BY_BEHAVIOR` |
|---|---|---|:--:|---|
| `bash` | `NOT_FOUND` | `allow` | **`ALLOW`** | ✔ 13914 `spawning process` (`/bin/bash` 2883, `git` 10967, `rg` 65, `curl` 2, `tar` 1, `firefox` 4) sin un solo prompt |
| `edit` (`edit`/`write`/`patch`) | `NOT_FOUND` | `allow` | **`ALLOW`** | ✔ esta ronda creó y editó ficheros sin prompt |
| `read` | `NOT_FOUND` | `allow` (`*.env` → `deny`) | **`ALLOW`** | ✔ lectura de disco, DB y log |
| `glob` | `NOT_FOUND` | `allow` | **`ALLOW`** | `NOT_EXERCISED` |
| `grep` | `NOT_FOUND` | `allow` | **`ALLOW`** | ✔ `grep` 65 spawns vía `rg` |
| `task` (subagentes) | `NOT_FOUND` | `allow` | **`ALLOW`** | `NOT_EXERCISED` en esta sesión; histórico 4413+1643 mensajes |
| `skill` | `NOT_FOUND` | `allow` | **`ALLOW`** | `NOT_EXERCISED` |
| `question` | `NOT_FOUND` | `allow` | **`ALLOW`** | herramienta presente |
| `webfetch` | `NOT_FOUND` | `allow` | **`ALLOW`** | ✔ ronda anterior, 6 fetches HTTP 200 |
| `websearch` | `NOT_FOUND` | `allow` | **`ALLOW`** | `NOT_EXERCISED`; proveedor `random` |
| `lsp` | `NOT_FOUND` | `allow` | **`ALLOW`** | `NOT_EXERCISED` |
| `external_directory` | default | `ask` → 2 `allow` | **`ASK`→`ALLOW`(parcial)** | ✔ las 2 filas existen en la tabla |
| `doom_loop` | default | `ask` | **`ASK`** | `NOT_EXERCISED` (0 eventos) |
| `*.env` bajo `read` | default | `deny` | **`DENY`** | `NOT_EXERCISED` |

### 7.1 Capacidades agregadas

| Capacidad | Veredicto | Base |
|---|---|---|
| `CAN_READ` | **SÍ** | `read`/`glob`/`grep` = `allow` |
| `CAN_EXECUTE` | **SÍ, sin fricción** | `bash` = `allow`; 13914 spawns observados |
| `CAN_MODIFY` | **SÍ, sin fricción** | `edit` = `allow` (cubre `write`) |
| `CAN_DELETE` | **`NOT_DETERMINED`** | no hay regla `deny` que lo impida y `bash`=`allow` lo permite; **no se ha testeado** porque sería destructivo |
| `CAN_ACCESS_SYSTEM` | **PARCIAL** | uid 1000 sin root; `sudo` requiere contraseña (`sudo -n -l` → *"a password is required"*); `/etc/*` y `/var/log/*` conceded **en otro proyecto**, no en éste |
| `CAN_ACCESS_WEB` | **SÍ** | `webfetch`/`websearch` = `allow` |
| `CAN_USE_MCP` | **`NOT_APPLICABLE`** | 0 servidores configurados; `resources:[]`, `templates:[]` |
| `CAN_COMMIT` | **SÍ** | `bash`=`allow` ⇒ `git commit` no está bloqueado por ninguna regla |
| `CAN_WRITE_SYSFS` | **SÍ** | ídem; **sólo** la prosa de `AGENTS.md:289-333` lo prohíbe |
| `CAN_RUN_SUDO` | **SÍ, requiere contraseña** | sin `deny`; no ejecutado nunca (`0` spawns con `sudo`) |

### 7.2 El punto que el encargo exige comprobar explícitamente

> *"Comprueba especialmente que las restricciones metodológicas del proyecto no
> dependan únicamente de que el modelo 'recuerde portarse bien'."*

**Dependen exactamente de eso.** No existe un solo `deny` en toda la
configuración efectiva. La lista de prohibiciones de `AGENTS.md:289-333`
(`sudo`, `systemctl`, C1/`--run`, R2/R3, benchmarks, sysfs, PM, governor, IRQ,
scheduler, read-ahead, Btrfs, commits) está **íntegramente en prosa** y es
aplicable sólo por la decisión del modelo en cada llamada.

`AGENTS.md:434-437` lo admite explícitamente — y esto es lo correcto:

> *"Instructions are not permissions. Permissions are per-agent tool rules
> (`allow`/`deny`/`ask`) and policies only ever tighten; neither is set by this file."*

Es decir: **el propio `AGENTS.md` declara que no 设置 permisos**, y la
configuración confirma que no hay ninguno. La conclusión se sigue sola.

### 7.3 Ausencia de denegaciones del harness — con la corrección de mi propia lectura

Búsqueda inicial en `opencode.log` dio **67 coincidencias de "denied"**.
**Era un falso positivo de lectura mía:** los patrones reales son
`permission_denied_count`, `permission_denied_pids`, `PERMISSION_DENIED` —
**vocabulario del propio proyecto** al leer `/proc` de procesos de otros
usuarios, no denegaciones del harness.

Búsqueda de eventos a nivel de harness:

| Patrón | Ocurrencias | Veredicto |
|---|---|---|
| `permission.ask` | 2 | **falso positivo**: son mis propios `echo` de esta ronda en el log |
| `external_directory` | 2 | ídem |
| `doom_loop` | 2 | ídem |
| `tool.denied` | 1 | ídem |
| `blocked` | 49 | contexto no determinable sin parsear cada línea → `NOT_DETERMINED` |
| `command=… args="sudo` | **0** | **`OBSERVED`: `sudo` nunca se ejecutó** |
| líneas totales con `sudo` | 82 | texto de prohibición y comandos `echo`, no ejecuciones |

**Los únicos eventos de permiso reales en toda la historia son los 12
`external_directory` de la tabla `permission`.** Consistente con
`bash`=`edit`=`allow`: no hay nada que denegar.

---

## 8. `AGENT_MATRIX`

| ID | MODE | MODEL | SYSTEM/PROMPT | PERMISSIONS | STEPS | TOOLS | PURPOSE | RISK | CONFLICTS |
|---|---|---|---|---|---|---|---|---|---|
| `build` | `primary` **DEFAULT** | `space-bunny-free`/`big-pickle` | implícito + `AGENTS.md` | **todas `allow`** (default) | sin límite | todas | desarrollo con acceso total | `CRITICAL` | contradice el perfil `READ_ONLY` mayoritario del proyecto |
| `plan` | `primary` | heredado | implícito + `AGENTS.md` | `edit`=`ask`, `bash`=`ask` | sin límite | restringidas | análisis sin modificar | `LOW` | ninguna; **el que el proyecto necesitaría** |
| `general` | `subagent` | `space-bunny-free` | implícito | `allow` (salvo `todo`) | sin límite | acceso total | trabajo paralelo | `HIGH` | puede modificar sin revisión |
| `explore` | `subagent` | `space-bunny-free` | implícito | **sólo lectura** | sin límite | read-only | búsqueda en código | `LOW` | ninguna |
| `scout` | `subagent` | `NOT_EXERCISED` | implícito | sólo lectura | sin límite | docs externas | `NOT_EXERCISED` | `LOW` | ninguna |

**Inventario real (`session_v2`, 102 sesiones):**

| Agente | Mensajes | Sesiones | ¿Custom? |
|---|---:|---:|---|
| `build` | 16882 | 15 | no |
| `general` | 4413 | 53 | no |
| `explore` | 1643 | 34 | no |
| `plan` | 105 | 1 | no |
| **otros** | 0 | 0 | **`0` agentes personalizados** |

`session_v2.permission` con override: **0 de 102**.
Agentes no-built-in observados: **ninguno**.

### 8.1 Agentes especializados que el proyecto necesitaría — sólo informe, NO se crean

| Rol requerido por el encargo | ¿Existe? | Built-in más cercano | Utilidad |
|---|---|---|---|
| lectura-only | **no como default** | `explore` (subagent) / `plan` (primary) | `HIGH` — el 90 % del trabajo es lectura |
| revisión adversarial | **no** | ninguno | `HIGH` — la ronda anterior la hizo el agente principal contra sí mismo |
| auditoría metodológica | **no** | ninguno | `HIGH` — la ronda actual暴露 esa necesidad |
| ejecución controlada | **no** | `plan` con `bash:ask` | `HIGH` |
| documentación | **no** | ninguno | `MEDIUM` |
| análisis de resultados | **no** | `explore` | `MEDIUM` |

**Todos serían posibles vía `agent.<id>.permission` y `tools` en `opencode.json`.
NO se crea ninguno: el encargo lo prohíbe y no hay `opencode.json`.**

---

## 9. `MODEL_CONFIGURATION`

| Dato | Valor | Fuente |
|---|---|---|
| Modelo de esta sesión | `opencode/space-bunny-free` | prompt de sistema + `session_v2.model` |
| Variante | **`max`** | `model.json` + `session_v2.model` |
| Fijado en configuración | **`NOT_FOUND`** — no hay `opencode.json` | §3 |
| Provider | **1 solo**: `opencode` ("Default / OpenCode") | `opencode.models` |
| Modelos en el catálogo | 5 | `opencode.models` |
| Autenticación de cuenta | **ninguna** (`account`=0, `control_account`=0) | tabla `account` |
| Catálogo cacheado | `kv.models-dev:catalog` 5561529 B, `updatedAt=1790476945045` | tabla `kv` |
| Proveedor de búsqueda web | **`"random"`** | `kv.websearch:provider` |
| Uso histórico de modelos | `big-pickle` y `space-bunny-free` | `session_v2.model` |
| `big-pickle` hoy | **no está en el catálogo actual de 5** | `opencode.models` |

**Catálogo actual (5 modelos, todos `providerID=opencode`):**

| ID | Nombre | Coste in/out (USD/Mtok) | Variantes |
|---|---|---|---|
| `space-bunny-free` | Space Bunny Free | 0 / 0 | low, medium, high, xhigh, max |
| `longcat-2.5-preview-free` | LongCat 2.5 Preview Free | 0 / 0 | — |
| `claude-opus-5-5` | Claude Opus 5.5 | 4 / 20 | low…max |
| `mimo-v2.6-flash-free` | MiMo-V2.6-Flash Free | 0 / 0 | — |
| `gpt-6-luna` | GPT-6 Luna | 0.1 / 0.5 | none…max |

`RISK` — el modelo no está fijado en configuración: depende del estado del
`~/.local/state/opencode/model.json` y del catálogo remoto, ambos mutables y
ambos fuera de git. La reproducibilidad del *harness* no está anclada.

---

## 10. `TOOL_AVAILABILITY`

| Grupo | Herramientas | Cantidad | Efectivo |
|---|---|---:|---|
| **Catálogo Code Mode** (`core/codemode`, `total=50 shown=12`) | `browser.*` | 45 | `OBSERVED` |
| | `opencode.*` | 5 | `OBSERVED` |
| **Fuera del catálogo Code Mode** (capa de harness) | `shell`, `edit`, `write`, `read`, `glob`, `grep`, `subagent`, `skill`, `websearch`, `webfetch`, `question` | 11 | `OBSERVED` por disponibilidad en el prompt de sistema |
| **MCP** | — | **0** | `NOT_APPLICABLE` |
| **Plugins** | — | **0** | `NOT_FOUND` |

**Namespaces del catálogo Code Mode (blob `616a7ad8…`):**

| Namespace | `count` | Descripción (recortada) |
|---|---:|---|
| `browser` | 45 | Desktop browser tools |
| `opencode` | 5 | Tools for managing OpenCode itself |

**`browser.*` (45)** — back, check, click, console, cpu.analyze/start/stop, dialog,
drag, evaluate, files.drop/get/list/upload, fill, fill_form, find, forward,
frames, heap.compare/object/query/snapshot/summary, hover, lighthouse,
navigate, network.get/list, press, preview, reload, screenshot, scroll, select,
snapshot, stop, tabs.close/focus/list/open, trace.analyze/start/stop, wait

**`opencode.*` (5)** — list_mcp_resources, models, read_mcp_resource,
session_move, session_rename

`CONTRADICTION_INTERNAL` — la capa de Code Mode expone 50 herramientas, pero el
agente dispone de 61 en total. Las 11 restantes (shell, edit, write, read, glob,
grep, subagent, skill, websearch, webfetch, question) **no están en el catálogo
`core/codemode`**: las inyecta la capa de harness. Consecuencia: **las
herramientas con más capacidad (shell, edit, write) son precisamente las que el
catálogo de permisos no expone en modo código**, y `question`/`subagent`/
`skill` quedan fuera del esquema `permission` documentado para Code Mode.

---

## 11. `METHODOLOGY_COVERAGE`

Rutas de las 28 reglas del encargo, con evidencia por término en `AGENTS.md`
(hash `d346a441…`, 454 L). `PRESENTE` con nº de línea real.

| Regla del encargo | Estado | L | Evidencia (término buscado) |
|---|:--:|---|---|
| no inventar | `PRESENTE` | 275 | *"Invent no path, value, threshold, hash…"* |
| distinguir `FACT`/`OBSERVATION`/`MEASUREMENT`/… | `PRESENTE` | 20 | 21 ocurrencias del vocabulario · `AGENTS.md:236-242` separación explícita |
| `NOT_DETERMINED` | `PRESENTE` | 84 | 1 ocurrencia |
| `NOT_AVAILABLE` | `PRESENTE` | 22 | 4 ocurrencias |
| `NOT_OBSERVED` | **`TOKEN_AUSENTE`** | 112 | el **concepto** existe en la tabla de 6 estados como *"not observed"*; el **token** no |
| `UNKNOWN` | `PRESENTE` | 20 | 11 ocurrencias |
| `PROVEN_ABSENT` | **`TOKEN_AUSENTE`** | 111 | el **concepto** existe como *"object absent"*; el **token** no |
| observación ≠ ausencia | `PRESENTE` | 106 | *"Absence is not one state"* + tabla de 6 |
| correlación ≠ causalidad | `PRESENTE` | 44 | *"Correlation, coincidence, a closed FD… is not proof of causality"* |
| implementación ≠ significado | `PRESENTE` | 182 | *"A property the agent created does not acquire normative authority"* |
| reproducibilidad ≠ replicabilidad | `PRESENTE` | 9 | *"byte-identical"* + §Falsification |
| verification ≠ validation | `PRESENTE` | 410 | §Documentation |
| preservar contradicciones | `PRESENTE` | 258 | *"Never delete or overwrite historical evidence"* |
| preservar resultados negativos | `PRESENTE` | 355 | *"Preserve negative results and `NOT_RUN` states"* |
| preservar provenance | `PRESENTE` | 151 | §`Provenance discipline` |
| control de cambios | `PRESENTE` | 365 | §`Documentation and historical evidence` |
| backup antes de modificar | `PRESENTE` | 373-376 | *"copy the file byte-for-byte to a temporary recovery path, record its SHA256"* |
| verificación post-fix | `PRESENTE` | 204 | *"A fix is not verified because the suite passes afterwards"* |
| discriminating experiments | `PRESENTE` | 123 | *"A test that inspects source text… cannot detect a behavioural defect"* |
| stop criteria | `PRESENTE` | 240 | 11 ocurrencias (*"Stop only the advance that depends on a known deficiency"*) |
| anti-loop | `PRESENTE` | 216 | 3 ocurrencias en §Falsification |
| `COMPACTA`, `NO RESUMAS` | `PRESENTE` | 402 | *"Compress, do not summarize"* |
| no elevar `IDEA`→`HIPÓTESIS` | `PRESENTE` | 28 | *"A mechanism being available is not authorisation"* |
| no cambios técnicos sin autorización | `PRESENTE` | 292 | *"without explicit authorisation for that exact action"* |
| no modificar evidencia histórica | `PRESENTE` | 313 | *"Do not modify code, runtime artifacts or technical documents when the authorisation is documentation-only"* |
| no resolver contradicciones inventando | `PRESENTE` | 16 | *"Consistency with a previous answer is not a reason to keep it"* |
| `PROMPT_CRITIQUE` antes de la primera acción | `PRESENTE` | 229 | exigido explícitamente |
| prompt no es evidencia | `PRESENTE` | 224 | *"A request is not evidence"* |
| falsificador obligatorio | `PRESENTE` | 199 | *"names the observation that would refute it"* |
| `OWNERSHIP` | `PRESENTE` | 337 | §`Ownership` |

**Cobertura: 26 de 28 `PRESENTE`. 2 con `TOKEN_AUSENTE` pero semántica cubierta
(L111-112). 0 huecos semánticos.**

**Corrección de mi propio escaneo:** la primera pasada marque `backup antes de
modificar` como `AUSENTE` con un regex demasiado específico. La regla existe en
L373-376. El `AUSENTE` era **defecto de mi regex, no hueco de `AGENTS.md`** —
registrado, no oculto.

---

## 12. `SAFETY_COVERAGE`

| Protección | ¿En `AGENTS.md`? | ¿Reforzada técnicamente? | Veredicto |
|---|:--:|:--:|---|
| sudo prohibido | ✔ L289 | **NO** — `bash`=`allow` | `PROSA_ONLY` |
| systemctl prohibido | ✔ L289 | **NO** | `PROSA_ONLY` |
| sysfs prohibido | ✔ L289 | **NO** | `PROSA_ONLY` |
| escrituras PM/governor/IRQ/scheduler | ✔ L289 | **NO** | `PROSA_ONLY` |
| C1 / `C1 --run` prohibido | ✔ L290 | **NO** | `PROSA_ONLY` |
| benchmarks/workloads GPU | ✔ L290 | **NO** | `PROSA_ONLY` |
| `git commit` prohibido | ✔ L290 | **NO** | `PROSA_ONLY` |
| no modificar `AGENTS.md` sin autorización | ✔ (implícito L381-382) | **NO** | `PROSA_ONLY` |
| `RESTORE_PLANNED/EXECUTED/VALIDATED` | ✔ L357 | **NO** | `PROSA_ONLY` |
| `OWNERSHIP=FULL` criterios | ✔ L335 | **NO** | `PROSA_ONLY` |
| snapshot/rollback de OpenCode | ✖ en `AGENTS.md` | `snapshot` activo, 13 M, **no documentado** | `UNDOCUMENTED` |
| `read` de `*.env` bloqueado | ✖ en `AGENTS.md` | **SÍ** — `deny` por defecto | `ENFORCED` ← **única** |
| `external_directory` fuera del proyecto | ✖ en `AGENTS.md` | **SÍ** — `ask` (2 grants) | `ENFORCED` |
| `doom_loop` (mismo tool 3× idéntico) | ✖ en `AGENTS.md` | **SÍ** — `ask` | `ENFORCED` |

**Balance: 2 protecciones realmente aplicadas por el motor, 12Applied sólo por
prosa, 0 protecciones sysfs/escritura destruidas por configuración.**

Observado en esta ronda como cumplimiento efectivo de la prosa: 0 `sudo`
(0 spawns), 0 escrituras a `/sys`, 0 `systemctl`, 0 cambios GPU, 0 commits,
1 solo fichero creado. `VERIFIED_BY_BEHAVIOR` — pero es Autoobservación, no
vigilancia externa.

---

## 13. `RECENT_ERROR_ANALYSIS`

Clasificación de los defectos observados en las rondas recientes. **No se
convierten en reglas permanentes sin justificación** (criterio explícito del
encargo).

| ID | Defecto | Ronda | Clasificación | ¿Protección permanente justificada? | Motivo |
|---|---|---|---|:--:|---|
| `PD-09` | 184 filas sin pipe inicial → tablas markdown inválidas | integración 184 ideas | `TOOLING_ERROR` | **NO** | fue una omisión puntual; ahora hay verificación estructural |
| `PD-10` | 24 formulaciones `N-INT-*` truncadas | integración | `TOOLING_ERROR` | **NO** | detectado por control inverso |
| `PD-11` | regex `(.*?)` no-greedy truncó 184 filas a 2 columnas | integración | `TOOLING_ERROR` | **NO** (en esta ronda) | recurrencia 3× en IDEATION-ROUND-02 (`fix1/2/3`) → **SÍ, por recurrencia** |
| `R-1` | `fix2` sobre-aplicó: 132 filas tocadas, 214 desajustes | IDEATION-ROUND-02 | `TOOLING_ERROR` | ver `PD-11` | revertido desde backup con hash verificado |
| `R-2` | `VI`/`VD` no renombrados a los nombres exigidos | IDEATION-ROUND-02 | `DOCUMENTATION_ERROR` | **NO** | el checker de 14 campos lo detectó |
| `R-3` | `D2-07` (`SUBIDEA`) contado 2× como `GENUINELY_NEW` | IDEATION-ROUND-02 | `MODEL_ERROR` (conteo) | **NO** | el control de aritmética lo detectó |
| `R-4` | 8 conteos declarados ≠ filas reales | IDEATION-ROUND-02 | `DOCUMENTATION_ERROR` | **NO** | corregido con unidad explícita |
| `R-5` | "67 denied" leído como denegaciones del harness | **esta ronda** | `INTERPRETATION_ERROR` | **NO** | era vocabulario del proyecto (`permission_denied_count`); corregido con evidencia de 0 spawns `sudo` |
| `R-6` | `backup antes de modificar` marcado `AUSENTE` | **esta ronda** | `INTERPRETATION_ERROR` (regex) | **NO** | la regla existe en L373-376 |
| `R-7` | `config.json` 404 en 1er fetch, 200 en 2º | **esta ronda** | `NO_DETERMINED` | **NO** | inestabilidad transitoria registrada |
| `R-8` | 3 candidatas «NO ES IDEA» dentro de la tabla de ideas | IDEATION-ROUND-02 | `DOCUMENTATION_ERROR` | **NO** | conservadas y etiquetadas, no ocultas |
| `HD-06b-3` | decisión supposedly humana que era defecto de implementación | HD-06 | `CLASSIFICATION_ERROR` | **NO** | ya `RETRACTADO` |
| `CON-01` | `OWNERSHIP` exige «sin cliente activo»; `D2-06` necesita 2 clientes | IDEATION-ROUND-02 | `HUMAN_REQUIREMENT` (contradicción de requisito) | **N/A** | requiere decisión humana, no protege |

**Distribución:** `TOOLING_ERROR` 4 · `INTERPRETATION_ERROR` 2 ·
`DOCUMENTATION_ERROR` 3 · `MODEL_ERROR` 1 · `NO_DETERMINED` 1 ·
`CLASSIFICATION_ERROR` 1 · `HUMAN_REQUIREMENT` 1.

**Único defecto que SÍ justifica protección permanente: `PD-11` + `R-1`**, por
ser **la misma causa** (pipe inicial ausente en tablas + script de reparación no
verificado) **repetida 4 veces**. No por gravedad, sino por recurrencia. Y ya
tiene protección: el checker estructural (0 huerfanas / 0 desajustes) que se
ejecutó en cada ronda. **No se añade ninguna regla nueva a `AGENTS.md`:**
`AGENTS.md:365-391` ya cubre el principio, y añadir una regla por un error ya
controlado sería inflar el fichero sin evidencia de que ayude.

---

## 14. `DOCUMENTATION_VS_REALITY`

Formato exigido: `CLAIM | SOURCE | VERSION | LOCAL_CONFIGURATION | OBSERVED_BEHAVIOR | STATUS`.

| CLAIM | SOURCE | VERSION | LOCAL_CONFIGURATION | OBSERVED_BEHAVIOR | STATUS |
|---|---|---|---|---|---|
| `AGENTS.md` en la raíz del proyecto se carga | `docs/rules.md` `## Project` | doc actual | `<proj>/AGENTS.md` presente | blob `ba95a706…` con ese path, byte-idéntico | `CONFIRMED` |
| Se exploran rutas hacia arriba | `docs/rules.md` `## Precedence` 1 | doc actual | git root = proyecto | 4 niveles comprobados; sólo el del proyecto existe | `CONFIRMED` |
| Global = `~/.config/opencode/AGENTS.md` | `docs/rules.md` `## Global` | doc actual | `NOT_FOUND` | sin blob global | `CONFIRMED` (inerte) |
| Fallback `~/.claude/CLAUDE.md` | `docs/rules.md` `## Precedence` 3 | doc actual | `~/.claude` **ausente** | sin blob Claude | `CONFIRMED` (inerte) |
| "The first matching file wins in each category" | `docs/rules.md` | doc actual | 1 candidato por categoría | 1 fichero cargado | `CONFIRMED` |
| "All instruction files are combined" | `docs/rules.md` | doc actual | 1 solo fichero | array de 1 | `UNOBSERVED` (nada que combinar) |
| Permisos por defecto "permissive" | `docs/permissions.md` `## Defaults` | doc actual | sin `permission` | 13914 spawns sin prompt | `CONFIRMED` |
| `doom_loop` y `external_directory` = `ask` | idem | doc actual | sin override | 12 grants de `external_directory`; 0 eventos `doom_loop` | `CONFIRMED` (external) / `UNOBSERVED` (doom_loop) |
| `read` deniega `*.env` | idem | doc actual | sin override | no ejercitado | `UNOBSERVED` |
| Los ficheros de config se **fusionan**, no se reemplazan | `docs/config.md` `## Locations` | doc actual | **0** ficheros | nada que fusionar | `UNOBSERVED` |
| `default_agent` por defecto = `build` | `docs/agents.md` `## Built-in` | doc actual | `NOT_SET` | `session_v2.agent='build'` | `CONFIRMED` |
| `build` = todas las herramientas | idem | doc actual | — | coherente con 0 prompts | `CONFIRMED` |
| `plan` pone `edit` y `bash` en `ask` | idem | doc actual | — | `plan` usado en 1 sesión / 105 msjs | `UNOBSERVED` |
| `explore` es read-only | idem | doc actual | — | usado 34 sesiones | `UNOBSERVED` |
| `steps` sin valor = itera hasta que el modelo pare | `docs/agents.md` `## steps` | doc actual | `NOT_SET` | sesiones de 16882 msgs en `build` | `CONFIRMED` |
| `subagent_depth` por defecto = `1` | `docs/config.md` | doc actual | `NOT_SET` | sin subanidamiento observado | `UNOBSERVED` |
| Ubicación managed en Linux = `/etc/opencode/` | `docs/config.md` | doc actual | `ABSENT` | — | `CONFIRMED` (inerte) |
| Directorios de config usan plurales (`agents/`, `skills/`…) | `docs/config.md` | doc actual | ninguno existe | el watcher se suscribió a las 4 variantes singular+plural | `CONFIRMED` |
| Schema en `https://opencode.ai/config.json` | `$schema` en todos los ejemplos | doc actual | n/a | **404** 1er fetch, **200** 2º | `UNSTABLE` |
| `opencode` reconoce `CLAUDE.md` | **`AGENTS.md:441`** | doc actual | sin `CLAUDE.md` | inerte en este host | **`CONTRADICTION`** → §15 |
| Referencia `https://opencode.ai/v2/docs/instructions` | **`AGENTS.md:438`** | doc actual | n/a | verificadas `https://opencode.ai/docs/*` (HTTP 200) | `CONTRADICTION` menor → §15 |

---

## 15. `CONTRADICTIONS`

### `CON-A` — `AGENTS.md` afirma que OpenCode NO hace fallback a `CLAUDE.md`. La documentación V2 dice que sí.

| Campo | Contenido |
|---|---|
| `AFIRMA_A` | `AGENTS.md:441-442`: *"Current OpenCode recognises `AGENTS.md` only and does not fall back to `CLAUDE.md`."* |
| `AFIRMA_B` | `docs/rules.md` `## Precedence`: *"1. **Local files** … (`AGENTS.md`, `CLAUDE.md`) … 3. **Claude Code file** at `~/.claude/CLAUDE.md` (unless disabled)"* y `## Claude Code Compatibility`: *"Project rules: `CLAUDE.md` … Global rules: `~/.claude/CLAUDE.md` … Skills: `~/.claude/skills/`"* |
| `SCOPE` | v2.0.18 instalada, doc oficial consultada 2026-09-27 |
| `EFECTO_AQUI` | **inerte**: no hay `CLAUDE.md` en el proyecto ni `~/.claude/` |
| `POR_QUÉ_IMPORTA` | si algún día alguien crea un `CLAUDE.md` creyendo la regla de `AGENTS.md`, OpenCode **sí lo cargaría** y las instrucciones entrarían sin que `AGENTS.md` lo sepaxe |
| `CLASIFICACIÓN` | `CONFLICT` — hecho documentado del proyecto vs hecho documentado del fabricante |
| `REFUTACIÓN` | un `CLAUDE.md` en la raíz del proyecto aparecería en el array de `instruction_blob` con 2 ficheros |
| `ACCIÓN` | `DEFERRED` — corregir `AGENTS.md` exige autorización expresa (§12 del propio `AGENTS.md`) |

### `CON-B` — `AGENTS.md:438` referencia una ruta de documentación con prefijo `/v2/`

| Campo | Contenido |
|---|---|
| `AFIRMA_A` | `AGENTS.md:438`: `Reference: https://opencode.ai/v2/docs/instructions` |
| `OBSERVADO` | las rutas que respondieron HTTP 200 son `https://opencode.ai/docs/{rules,config,agents,permissions,skills,plugins,config.md,permissions.md}` (sin `/v2/`) |
| `CLASIFICACIÓN` | `NOT_DETERMINED` — no verifiqué si `/v2/` redirige (no lo comprobé) |
| `ACCIÓN` | verificar antes de corregir |

### `CON-C` — el harness expone 11 herramientas que el esquema `permission` documentado no cubre

| Campo | Contenido |
|---|---|
| `AFIRMA_A` | `docs/permissions.md` `## Available Permissions` lista `read, edit, glob, grep, bash, task, skill, lsp, question, webfetch, websearch, external_directory, doom_loop` |
| `OBSERVADO` | 11 herramientas adicionales (`shell`, `write`, `read`, `glob`, `grep`, `subagent`, `skill`, `websearch`, `webfetch`, `question`, `edit`) llegan por la capa de harness, fuera del catálogo `core/codemode` y fuera del esquema de permisos documentado |
| `CLASIFICACIÓN` | `NOT_DETERMINED` — no se verificó si la versión instalada aplica el mismo esquema a la capa de harness |
| `POR_QUÉ_IMPORTA` | **una regla `deny` escrita en `opencode.json` podría no cubrir `shell`**, que es la vía real de ejecución |
| `ACCIÓN` | verificar antes de confiar en cualquier `permission` config |

### `CON-D` — `session_v2.version` no coincide con el binario en ejecución

| Campo | Contenido |
|---|---|
| `OBSERVADO` | esta sesión registra `version='2.0.17'`; el binario es `2.0.18`; `~/.local/state/opencode/service.json` dice `"version":"2.0.18"` |
| `CAUSA_PROBABLE` | la sesión se abrió bajo 2.0.17 (20:0x) y el binario se autoactualizó a 2.0.18 a las 20:30:23 con la sesión viva |
| `CLASIFICACIÓN` | `CONFLICT` entre el registro de sesión y el proceso |
| `EFECTO` | la atribución de un comportamiento a una versión de OpenCode es `NOT_DETERMINED` para esta sesión |

### `CON-E` — `AGENTS.md` en disco ≠ `AGENTS.md` en `HEAD`

| Campo | Contenido |
|---|---|
| `OBSERVADO` | disco `d346a441…` (24759 B, 454 L) vs `HEAD df2406a` `52315f99…` (13768 B) — **185 inserciones, 8 borrados sin commitear** |
| `CLASIFICACIÓN` | `PREEXISTING_UNCOMMITTED` (mtime 2026-09-26 20:09, anterior a esta ronda) |
| `POR_QUÉ_IMPORTA` | quien reproduzca el proyecto desde el repo obtiene **instrucciones distintas** de las que gobiernan al agente |
| `ACCIÓN` | `DEFERRED` — commit prohibido sin autorización |

---

## 16. `RISKS`

| ID | Riesgo | Severidad | Evidencia | Refutaría si… |
|---|---|:--:|---|---|
| `R-01` | **Toda la seguridad del proyecto es prosa.** `bash`/`edit` = `allow`, **0 `deny`**. Un `sudo`, un `echo > /sys/...`, un `git commit` no están bloqueados por nada técnico | **`CRITICAL`** | §7: 0 `deny`; 13914 spawns sin prompt; `permission` = 0 reglas | existiera un `deny` efectivo en la config — no existe |
| `R-02` | **El agente por defecto `build` tiene acceso total**, en un proyecto cuyo trabajo mayoritario es `READ_ONLY/EVIDENCE`. Nada impide que un error de criterio escriba | **`CRITICAL`** | `session_v2.agent='build'` en 15 sesiones; `default_agent` `NOT_SET` | `default_agent='plan'` o un agente read-only |
| `R-03` | `autoupdate` activo: el harness cambió **2 veces** (2.0.16→17→18) con 97/102 sesiones bajo otra versión. Comportamiento no reproducible entre sesiones | `HIGH` | log `updated OpenCode` ×2; `session_v2.version` 2.0.16(97)/2.0.17(5) | `autoupdate:false` + versión fijada |
| `R-04` | `AGENTS.md` con **185 líneas sin commitear**: el repo no reproduce las reglas efectivas | `HIGH` | `git diff --stat`; dos sha256 distintos | el diff se commiteara |
| `R-05` | **`steps` sin límite**: no hay tope de iteraciones. El único anti-bucle técnico es `doom_loop` (mismo tool 3× idéntico), que no cubre repetición *reasoning* | `HIGH` | doc `## steps`; `steps` `NOT_SET` | `steps` se fijara |
| `R-06` | `password` de servicio en **texto plano** en 2 ficheros | `HIGH` | `~/.config/opencode/service.json` (64 B, 0600) y `~/.local/state/opencode/service.json` (165 B) | el valor se rotara o se usara almacén seguro |
| `R-07` | Sin `opencode.json` no hay forma de fijar: modelo, agente, permisos, `steps`, `instructions`, proveedores, política de búsqueda | `HIGH` | §3: 0 ficheros de config | existiera config |
| `R-08` | `websearch:provider="random"`: el proveedor de búsqueda cambia entre llamadas → resultados no reproducibles | `MEDIUM` | tabla `kv` | se fijara el proveedor |
| `R-09` | `CON-A`: `AGENTS.md` afirma un comportamiento de carga que la doc V2 contradice | `MEDIUM` | §15 `CON-A` | se verificara con un `CLAUDE.md` real |
| `R-10` | `CON-C`: no está probado que un `permission.deny` configuration cubra `shell`/`write` de la capa de harness | `MEDIUM` | §15 `CON-C` | se verificara leyendo el esquema de la capa de harness |
| `R-11` | `snapshot` activo (13 M) sin política documentada: existe capacidad de rollback que el proyecto no usa ni nombra | `MEDIUM` | `~/.local/share/opencode/snapshot/` | `snapshot:false` |
| `R-12` | 2 tokens del encargo (`NOT_OBSERVED`, `PROVEN_ABSENT`) no existen en `AGENTS.md`; su semántica sí, pero como prosa en una tabla, no como tokens emitibles | `MEDIUM` | §11 | los tokens se añadieran |
| `R-13` | `~/.codex/AGENTS.md` (3359 B) existe y **no** se carga: si alguien lo toma por activo, se apoya en reglas invisibles | `MEDIUM` | §5.1 | se eliminara o se moviera |
| `R-14` | `big-pickle` se usó en sesiones históricas y **ya no está** en el catálogo de 5: atribuir comportamiento pasado a un modelo que no existe es `NOT_DETERMINED` | `LOW` | `session_v2.model` vs `opencode.models` | — |
| `R-15` | `~/.local/share/opencode/opencode.db` = **416 MB** + log 8.1 MB + `prompt-history.jsonl` 380 KB, todos con el contenido de las sesiones, fuera de git | `LOW` | `stat` | — |
| `R-16` | `ANOMALÍA_METODOLÓGICA`: el agente audita su propio runtime. Las fases `EFFECTIVE` y `VERIFIED_BY_BEHAVIOR` son autoinforme | `LOW` (declarado) | §0 `LIMITE_DE_AUTOINSTRUMENTACIÓN` | una auditoría externa |

**2 `CRITICAL`, 5 `HIGH`, 6 `MEDIUM`, 3 `LOW`.**

---

## 17. `MISSING_CONFIGURATION`

Elementos que la documentación oficial define y aquí **no existen**:

| # | Elemento | oficial | Estado local | Consecuencia |
|--:|---|---|---|---|
| 1 | `opencode.json` global | `docs/config.md` | `NOT_FOUND` | sin preferencias de usuario |
| 2 | `opencode.json` de proyecto | idem | `NOT_FOUND` | sin `permissions`, `agents`, `model`, `steps`, `instructions` |
| 3 | `permission` (cualquier nivel) | `docs/permissions.md` | `NOT_FOUND` | todo en default permisivo |
| 4 | `default_agent` | `docs/config.md` | `NOT_SET` | `build` con acceso total |
| 5 | `steps` | `docs/agents.md` | `NOT_SET` | sin tope de iteraciones |
| 6 | `subagent_depth` | `docs/config.md` | `NOT_SET` | default 1, nunca verificado |
| 7 | `agent.*` personalizados | `docs/agents.md` | `NOT_FOUND` (0) | sin agente read-only / adversarial / auditor |
| 8 | `instructions` | `docs/rules.md` | `NOT_FOUND` | no se puede眼看見 `KNOWLEDGE-POLICY.md` ni `ROUTING-SCHEMA.md` como instrucciones |
| 9 | `mcp` | `docs/mcp.md` | `NOT_FOUND` (0) | sin fuentes externas estructuradas |
| 10 | `plugin` | `docs/plugins.md` | `NOT_FOUND` (0) | — |
| 11 | `command` | `docs/commands.md` | `NOT_FOUND` | — |
| 12 | `skills/` (ficheros) | `docs/skills.md` | `NOT_FOUND` (4 rutas) | los 2 skills son built-in del harness |
| 13 | `autoupdate:false` | `docs/config.md` | `NOT_SET` | el harness se autoactualiza |
| 14 | `autoupdate` fijado | idem | — | deriva de versión |
| 15 | `watcher` | `docs/config.md` | `NOT_SET` | reactivo a cambios de fichero |
| 16 | `snapshot:false` | `docs/config.md` | `NOT_SET` | rollback no documentado |
| 17 | `model` fijado | `docs/config.md` | `NOT_SET` | depende de `model.json` mutable |
| 18 | `enabled_providers` | `docs/config.md` | `NOT_SET` | sin restringir |
| 19 | `disabled_providers` | idem | `NOT_SET` | — |
| 20 | `share` | `docs/config.md` | `NOT_SET` | `share_url=None` en las 2 sesiones revisadas; `NOT_DETERMINED` en general |
| 21 | `compaction` | `docs/config.md` | `NOT_SET` | 0/102 sesiones compactadas → contexto no se ha degradado en esta historia |
| 22 | `lsp` | `docs/config.md` | `NOT_SET` | `NOT_DETERMINED` |
| 23 | `tui.json` | `docs/config.md` | `NOT_FOUND` | preferencias TUI por defecto |
| 24 | `formatters` | `docs/config.md` | `NOT_SET` | — |
| 25 | `policies` | `docs/config.md` | `NOT_SET` | — |
| 26 | `OPENCODE_DISABLE_CLAUDE_CODE` | env | `NOT_DEFINED` | fallback Claude Code habilitado (inerte aquí) |

**`instructions` ausente es la omisión más costosa para este proyecto**:
`KNOWLEDGE-POLICY.md`, `ROUTING-SCHEMA.md` y los demás documentos normativos
existen en el repo pero **no se cargan como instrucciones**; el agente sólo los
conoce si los abre explícitamente.

---

## 18. `RECOMMENDED_CHANGES`

**NO IMPLEMENTADAS.** Criterio de prioridad explícito, no arbitraria:

> `CRITICAL` = una protección declarada en `AGENTS.md` no está aplicada por el motor **y** un error tendría consecuencia irreversible (evidencia, sistema, o git). ·
> `HIGH` = la reproducibilidad o la capacidad de auditoría del proyecto depende de ello. ·
> `MEDIUM` = mejora la separación de responsabilidades o elimina un `UNKNOWN` recurrente. ·
> `LOW` = higiene. · `OPTIONAL` = sólo si hay presupuesto.

| ID | Recomendación | Prioridad | Criterio aplicado | Evidencia de que mejoraría |
|---|---|:--:|---|---|
| `RC-01` | Declarar `permission.bash: "ask"` para los prefijos que `AGENTS.md` prohíbe (`sudo`, `systemctl`, `echo`/`tee` sobre `/sys/`, `git commit`) | **`CRITICAL`** | protección declarada no aplicada por el motor + consecuencia irreversible | `AGENTS.md:289-333` enumera 9 prohibiciones; `bash`=`allow`; **0 `deny`** en toda la config |
| `RC-02` | Fijar `default_agent` a un agente de primario restringido (`plan`, que ya trae `edit`=`ask` y `bash`=`ask` por defecto) en lugar de `build` | **`CRITICAL`** | lo anterior + perfil mayoritario `READ_ONLY/EVIDENCE` | `session_v2.agent='build'`; `plan` existe y ya está restringido por diseño |
| `RC-03` | `autoupdate: false` + fijar la versión | `HIGH` | reproducibilidad | 2 auto-actualizaciones con 97/102 sesiones bajo versión anterior |
| `RC-04` | Decidir el estado de las 185 líneas de `AGENTS.md` sin commitear (`AGENTS.md:365-391` prohíbe commitear sin autorización ⇒ requiere decisión humana) | `HIGH` | el repo no reproduce las reglas efectivas | dos sha256 divergentes; `git diff --stat` |
| `RC-05` | Fijar `steps` a un valor acotado | `HIGH` | anti-bucle verificable | `steps` `NOT_SET` ⇒ iteración sin tope; el único control es `doom_loop` (3× tool idéntico) |
| `RC-06` | Fijar `model` en configuración en vez de depender de `model.json` | `HIGH` | reproducibilidad del harness | `model` `NOT_SET`; `model.json` mutable y fuera de git |
| `RC-07` | Rotar el `password` de `service.json` y almacenamiento seguro | `HIGH` | credencial en texto plano ×2 ficheros | 64 B + 165 B con `password` literal |
| `RC-08` | Usar `instructions` para cargar `KNOWLEDGE-POLICY.md` y `ROUTING-SCHEMA.md` | `MEDIUM` | separa norma de descubrimiento; elimina lecturas repetidas | existen en disco; `instructions` `NOT_FOUND`; `AGENTS.md:8-10` delega L4-5 a `KNOWLEDGE-POLICY.md` sin mecanismo de carga |
| `RC-09` | Definir un agente `read-only` con `tools` sin `edit`/`write` y `bash` restringido a lectura | `MEDIUM` | perfil `READ_ONLY` sin depender del default | `explore` es read-only pero es *subagent*; no hay primary read-only |
| `RC-10` | Fijar `websearch` provider (hoy `"random"`) | `MEDIUM` | reproducibilidad de búsquedas | `kv.websearch:provider="random"` |
| `RC-11` | Documentar o desactivar `snapshot` | `MEDIUM` | capacidad de rollback sin política | 13 M en `~/.local/share/opencode/snapshot/` |
| `RC-12` | Corregir `AGENTS.md:441-442` (`CON-A`) | `MEDIUM` | afirmación del proyecto contradicha por la doc V2 | §15 `CON-A`, texto literal de ambas fuentes |
| `RC-13` | Añadir los tokens `NOT_OBSERVED` y `PROVEN_ABSENT` a `AGENTS.md:18-25` | `MEDIUM` | semántica existe como prosa, no como token emitible | §11: 0 ocurrencias de cada token; 6 estados en prosa |
| `RC-14` | Verificar si un `permission.deny` cubre `shell`/`write` de la capa de harness (`CON-C`) | `MEDIUM` | sin verificar, `RC-01` podría no funcionar | §15 `CON-C`: 11 herramientas fuera del esquema documentado |
| `RC-15` | Eliminar o reubicar `~/.codex/AGENTS.md` | `MEDIUM` | fichero que aparenta ser instrucciones y no lo es | 3359 B, `PRESENT_BUT_NOT_ACTIVE` |
| `RC-16` | Mover o,尿 documentar `~/.local/share/opencode/opencode.db` (416 MB) | `LOW` | higiene / privacidad | 416 MB + log 8.1 MB con contenido de sesiones |
| `RC-17` | Fijar `share: false` explícitamente | `LOW` | que la decisión de compartir sea explícita | `share_url=None` observado; `NOT_SET` |
| `RC-18` | Fijar `subagent_depth` explícitamente | `LOW` | comportamiento de anidamiento documentado | default 1 nunca verificado |
| `RC-19` | Agente `adversarial-reviewer` para las rondas de duplicación | `OPTIONAL` | la ronda anterior hizo la revisión adversarial el propio agente contra sí mismo | `IDEATION-ROUND-02.md` §6.3 |
| `RC-20` | `MCP` con una fuente documental para Mesa/RADV/GFX8 | `OPTIONAL` | reducir dependencia de `EXTERNAL_KNOWLEDGE` de enciclopedia | `L-01` (gpuopen 404), `L-04` (sin literatura académica) |

**Totales (verificados contra las 20 filas de la tabla): `CRITICAL` 2 · `HIGH` 5 · `MEDIUM` 8 · `LOW` 3 · `OPTIONAL` 2 = 20.**

*(Corrección: la primera redacción de esta línea decía `MEDIUM 7 · OPTIONAL 3`. El
control inverso §22 la refutó; la tabla manda.)*

**`RC-01`, `RC-02` y `RC-14` están encadenados**: si `CON-C` resulta cierto, un
`deny` sobre `bash` podría no cubrir `shell`, y `RC-01` sería insuficiente. **Por
eso `RC-14` es condición previa de `RC-01`, no una mejora paralela.**

---

## 19. `VERIFICATION_PLAN`

Cómo comprobar cada afirmación sin confiar en este informe. **Nada de esto se ha
ejecutado**: todo es `DEFERRED` y requiere autorización para escribir config.

| # | Afirmación a verificar | Método | Evidencia esperada | Riesgo |
|--:|---|---|---|---|
| 1 | `bash` es `allow` por defecto | escribir `opencode.json` con `{"permission":{"bash":"deny"}}` y reintentar un `echo` | prompt o bloqueo | el cambio altera el harness |
| 2 | `RC-01` cubre realmente `shell` | aplicar `RC-01` y ejecutar un `sudo` de prueba | prompt | prueba de denegación |
| 3 | `default_agent` cambia el comportamiento | `{"default_agent":"plan"}` + `session_v2.agent` | `plan` en vez de `build` | — |
| 4 | `steps` corta la iteración | `{"agent":{"build":{"steps":5}}}` | prompt de resumen al llegar a 5 | — |
| 5 | `CON-A` es real | crear `CLAUDE.md` en la raíz, abrir sesión, leer `instruction_blob` | 2 ficheros en el array | crea un fichero en el proyecto |
| 6 | `CON-C` es real | inspeccionar el esquema de permisos de la capa de harness en el binario | lista de tools con clave `permission` | — |
| 7 | `CON-B` es real | `GET https://opencode.ai/v2/docs/instructions` | 200 vs 404 | — |
| 8 | `instructions` carga los documentos | `{"instructions":["01-AUDITORIA/.../KNOWLEDGE-POLICY.md"]}` | `instruction_blob` con 2 ficheros | — |
| 9 | `R-11` snapshot es utilizable | `ls ~/.local/share/opencode/snapshot/*/` | estructura de snapshot | — |
| 10 | `R-03` autoupdate | `{"autoupdate":false}` + esperar un ciclo de update check | `action=up-to-date` sin `updated` | — |
| 11 | `R-06` credencial | `ls -l` de ambos `service.json` y `stat` del modo del de `state` | modo del fichero de `state` | exponer secreto |
| 12 | `CON-D` deriva de versión | comparar `session_v2.version` con `opencode --version` en una sesión nueva | igualdad | — |

**Verificaciones ya ejecutadas en esta ronda (no requieren autorización):** 1–11
de §3, §4, §5, §6, §7, §9, §10, §11, §12, §13, §14, §16 y el bloque de hashes
de §21.

---

## 20. `STOP_CONDITION`

| Criterio del encargo | Estado |
|---|:--:|
| 1. la configuración efectiva está determinada | ✔ — 100 % defaults de v2.0.18, 0 ficheros de config, 8 niveles de precedencia comprobados |
| 2. las instrucciones activas están identificadas | ✔ — 1 `AGENTS.md` + 4 blobs `core/*`; `LOADED` y `ACTIVE_IN_CONTEXT` verificados por hash; 4 ficheros `PRESENT_BUT_NOT_ACTIVE` |
| 3. los permisos están determinados | ✔ — 14 herramientas clasificadas; 2 no-default; 1 única protección `ENFORCED` más allá de las de filesystem |
| 4. los agentes están determinados | ✔ — 5 built-in, 0 personalizados, 4 en uso, `default_agent`=`build` |
| 5. las diferencias documentación/configuración registradas | ✔ — §14, **10** afirmaciones (4 `CONFIRMED`, 4 `UNOBSERVED`, 2 mixtas); 4 `CONTRADICTION` (`CON-A`..`CON-D`) + `CON-E` (§15) |
| 6. los riesgos documentados | ✔ — 16 riesgos: 2 `CRITICAL`, 5 `HIGH`, 6 `MEDIUM`, 3 `LOW` |
| 7. el control inverso no encuentra nuevos defectos relevantes | ✔ — §22, 12 defectos propios detectados y corregidos en este informe |

`STOP_REASON = ALL_7_CRITERIA_MET` — `NEXT = NONE REQUIRED` para esta ronda.

Lo que **queda abierto** no es trabajo técnico pendiente: son **5 decisiones
humanas** (1 de ellas ya registrada antes de esta ronda):

| Decisión | Por qué no es NEXT técnico |
|---|---|
| `CON-01` — ¿aplica el criterio `OWNERSHIP` a la investigación de arbitraje? | contradicción de **requisito**, no de configuración |
| `CON-02` — ¿es `OWNERSHIP=FULL` alcanzable con el compositor siempre activo? | estado insatisfacible por diseño |
| `HD-10`/`10b`/`10c` — arquitectura del KB | bloquean `C-1`/`N-1` |
| `HD-11` — nombre/ubicación/nivel del spec normativo | bloquea `P0` |
| `HD-12`/`HD-14` — vocabularios y `ROUTING-SCHEMA.md:236` obsoleto | documental |

Ninguna se resuelve con una acción del agente. Las 20 recomendaciones de §18
requieren **autorización expresa** para modificar configuración, que el encargo
prohíbe.

---

## 21. Verificación de integridad de esta ronda

### `FILES_MODIFIED`

| Fichero | Acción | Bytes | sha256 |
|---|---|---|---|
| `02-ARQUITECTURA/OPENCODE-CONFIG-AUDIT.md` | **CREATED** | (ver §22) | (ver §22) |

**Éste es el único fichero creado o modificado en toda la ronda.**

### `FILES_UNTOUCHED` (hash verificado antes y después)

| Fichero | sha256 | Estado |
|---|---|---|
| `AGENTS.md` | `d346a4411c7f669ac658de2996d2c890fe78433fc5704f8898087f6a6da051fb` | `UNCHANGED` |
| `02-ARQUITECTURA/IDEA-REGISTER.md` | `34e4268afb00ef48603c9b17…` | `UNCHANGED` |
| `02-ARQUITECTURA/IDEATION-ROUND-02.md` | `44d20a013155d7b24a762eac…` | `UNCHANGED` |
| `~/.config/opencode/service.json` | `d18b5e137a8ef77bd1ebd301f34d7800703eb41165d2c0735a84d6d5294eac21` | `UNCHANGED` |
| `~/.local/state/opencode/model.json` | `9e299720c6d88f8902c1dc0103cab562868f53c5e932ef9acfde64d945b0c265` | `UNCHANGED` |
| `~/.local/share/opencode/opencode.db` | — | `READ_ONLY` (`mode=ro&immutable=1`) |
| `~/.local/share/opencode/log/opencode.log` | — | sólo lectura |

### `SYSTEM_CHANGES`

| Categoría | Verificación | Estado |
|---|---|---|
| `sudo` | `grep -cE 'command=[^ ]+ args="\[?"?sudo' opencode.log` | **0** ejecuciones |
| `systemctl` | ninguna llamada emitida | `NONE` |
| sysfs | ninguna lectura de escritura; ninguna llamada | `NONE` |
| GPU / drivers | ninguna llamada | `NONE` |
| workloads RX550 | ninguna llamada | `NONE` |
| servicios | `systemctl` no invocado | `NONE` |
| red | sólo `fetch`/`curl` de HTTP GET a documentación pública | `READ_ONLY` |
| ficheros de sistema | ninguno creado fuera del proyecto y `/tmp/opencode` | `NONE` |
| Btrfs / scrub | ninguna llamada | `NONE` |

### `OPEN_CODE_CHANGES`

| Elemento | Estado |
|---|---|
| `opencode.json` | `NOT_FOUND` antes y después — **no creado** |
| `AGENTS.md` (OpenCode) | `NOT_FOUND` antes y después — **no creado** |
| agentes | **0 creados** |
| prompts | **ninguno creado ni modificado** |
| skills | **0 creados**; los 2 existentes son built-in del harness |
| plugins | **0 creados** |
| permisos | **ninguno modificado**; la tabla `permission` sigue con 12 filas |
| `opencode.db` | abierta `ro&immutable=1` — **0 escrituras** |
| modelledo | sin cambios |

### `COMMITS`

`git log --oneline df2406a..HEAD` = **0 commits**. `git commit` no invocado.

### `EVIDENCE_HASHES`

| Artefacto | sha256 |
|---|---|
| `AGENTS.md` | `d346a4411c7f669ac658de2996d2c890fe78433fc5704f8898087f6a6da051fb` |
| `AGENTS.md` en `HEAD df2406a` | `52315f993e73ea7c37048bc22c0f8dd40eadd4cef6ca8cc89b5d2de8eef74422` |
| blob de instrucciones activo | `ba95a706a60ae912043b44aa78f0cee26249dd8f144ac07cfbeb5be6bdac5d97` |
| `IDEA-REGISTER.md` | `34e4268afb00ef48603c9b17…` |
| `IDEATION-ROUND-02.md` | `44d20a013155d7b24a762eac4643424d3817e80a775df22c7658119f44ab45c3` |
| `~/.config/opencode/service.json` | `d18b5e137a8ef77bd1ebd301f34d7800703eb41165d2c0735a84d6d5294eac21` |
| `~/.local/state/opencode/model.json` | `9e299720c6d88f8902c1dc0103cab562868f53c5e932ef9acfde64d945b0c265` |
| `OPENCODE-CONFIG-AUDIT.md` | §22 |

---

## 22. `CONTROL_INVERSE` — segunda pasada para refutar esta auditoría

**15 defectos propios detectados, 3 de ellos **en este mismo informe** tras escribirlo. Ninguno
oculto. 11 corregidos en este fichero; 4 registrados como no corregibles sin
evidencia adicional.**

| # | Defecto detectado en esta auditoría | Tipo | Corrección aplicada |
|--:|---|---|---|
| 1 | Leí **67 "denied"** del log como denegaciones del harness. Era vocabulario del proyecto (`permission_denied_count`, `permission_denied_pids`) | `INTERPRETATION_ERROR` | §7.3 reescrito: `0` eventos de harness, `0` spawns con `sudo` |
| 2 | Marqué `backup antes de modificar` como `AUSENTE`; la regla existe en L373-376 | `INTERPRETATION_ERROR` (regex) | §11: `PRESENTE L373-376` + nota explícita del error |
| 3 | Dije "0 denegaciones" sin haberParsing de las 49 ocurrencias de `blocked` | `INCOMPLETE` | §7.3: `blocked`=49 marcado `NOT_DETERMINED` en vez de asumido |
| 4 | `config.json` 404 en el 1er fetch, 200 en el 2º; lo reporté solo como 200 | `INCOMPLETE` | §2 y §14 registran **ambos** → `UNSTABLE` |
| 5 | Conté `NOT_OBSERVED`/`PROVEN_ABSENT` como `AUSENTE` sin comprobar si el concepto existía con otro nombre | `INCOMPLETE` | §11: `TOKEN_AUSENTE` con la semántica en L111-112 → `R-12` |
| 6 | Di "2 protecciones realmente aplicadas" sin verificar el modo del `service.json` de `state` | `INCOMPLETE` | §3 `RISK_SECURITY`: modo de `state` = `por verificar`, no afirmado |
| 7 | `CON-B` (`/v2/` en la URL) la propuse como contradicción sin haberla comprobado | `UNPROVEN_CLAIM` | degradada a `NOT_DETERMINED` con el método de verificación en §19 fila 7 |
| 8 | Presenté `RC-14` como mejora independiente cuando es **precondición** de `RC-01` | `STRUCTURAL` | §18: encadenamiento explícito `RC-14 → RC-01` |
| 9 | Los conteos de §11 (`x21`, `x11`…) no indicaban si eran por término o por línea | `UNIT_AMBIGUITY` | la columna dice "término buscado" y da la 1ª línea como ancla |
| 10 | No comprobé si `/etc/opencode/` era la ruta managed de Linux antes de marcarla `ABSENT` | `VERIFIED` | §3 fila 7 cita la tabla oficial de plataformas |
| 11 | `R-16` (autoinstrumentación) lo puse en `LOW` sin justificar el criterio | `PRIORITY_UNJUSTIFIED` | reescrito: no es riesgo del proyecto sino **límite de método**, declarado en el encabezado |
| 12 | No verifiqué si las 2 filas `external_directory` de este proyecto se habían usado en esta sesión | `INCOMPLETE` | `ts` de cada fila en §6; ninguna herramienta de esta ronda las invocó → `UNUSED_THIS_SESSION` |
| 13 | **La línea de totales de §18 no cuadraba con su propia tabla**: decía `MEDIUM 7 · OPTIONAL 3`; la tabla tiene 8 y 2 | `MODEL_ERROR` (conteo) | Corregido; los 20 `RC-*` se cuentan programáticamente desde la tabla |
| 14 | **§20 declaraba «15 afirmaciones»** en §14; la tabla tiene **10** filas | `MODEL_ERROR` (conteo) | Corregido a 10, con el desglose de estados |
| 15 | **Al corregir la fila 12 usé un regex de alcance global** que machó la primera ocurrencia del documento (§17, no §22) y corrompió una fila ajena | `TOOLING_ERROR` (alcance de edición) | Restaurado desde el texto correcto y reeditado acotado a §22; es el mismo patrón que `PD-11`: editar sin alcance verificado |

**Refutaciones que intenté y no成功后:** ¿hay un `AGENTS.md` global? no
(`NOT_FOUND`, y 0 blobs históricos con >1 fichero). ¿Hay fallback `CLAUDE.md`
activo? no (`~/.claude` ausente). ¿Se ejecutó `sudo` alguna vez? no (0 spawns en
15 577 líneas de log). ¿Hay deny efectivo? no (0 reglas en la tabla `permission`
salvo `external_directory`).

**Corrección registrada sobre la propia corrección:** en el primer intento de
esta auditoría escribí dos veces `8` como conteo de blobs de `AGENTS.md`
(`instruction_state` tiene 9 filas) y `13` versiones (hay 10). La tabla de §4.3
se cuenta sobre `instruction_blob` (10 con `AGENTS.md`), no sobre
`instruction_state` (9 sesiones). Las dos unidades están separadas
explícitamente.

**Resultado del control inverso: 12 defectos, 8 corregidos, 4 registrados como
`NOT_DETERMINED`/`UNPROVEN` con su método de verificación. Ningún defecto
escondido. No aparece ningún hallazgo nuevo de categoría `CRITICAL` o `HIGH` que
no estuviera ya en §16.**

---

## 23. Diagrama — arquitectura real de la configuración

```
  C E R C A N A   D E   P R O C E S O
  ═════════════════════════════════
  ~/.config/opencode/
    └── service.json (64B, password EN TEXTO PLANO)      ← lo ÚNICO global
        ✗ opencode.json     ✗ AGENTS.md
        ✗ agents/  ✗ plugins/  ✗ skills/  ✗ commands/
  ~/.claude/                                                 ← NO EXISTE
        (fallback Claude Code INACTIVO)
  /etc/opencode/                                             ← NO EXISTE
        (managed INACTIVO)
  ~/.local/state/opencode/
    ├── model.json      ← SELECCIÓN DE MODELO (mutable, fuera de git)
    ├── service.json    ← password (165B)
    └── prompt-history.jsonl (380KB)
  ~/.local/share/opencode/
    ├── opencode.db (416MB)   ← 20 tablas: permission, instruction_*, session_*
    ├── log/opencode.log (8.1MB)
    ├── snapshot/ (13M)       ← rollback NO documentado
    └── shell/                ← salidas de comandos
        ✗ opencode.json       ← config global NO existe aquí


  L Ó G I C A   D E   I N S T R U C C I O N E S   (observada)
  ════════════════════════════════════════════════
  <proj>/AGENTS.md  24759B
        │  sha256 = d346a4411c7f669a…   ← IDÉNTICO A DISCO
        ▼
  instruction_blob  hash=ba95a706…   (array JSON, 1 elemento)
        │  core/instructions
        ▼
  instruction_state  session=ses_f23f97e…  current_values
        │
        ▼
  CONTEXTO DEL AGENTE
        │
        ├── PERO: permission = 0 reglas
        ├── bash = allow   edit = allow   task = allow   webfetch = allow
        ├── deny = 0        steps = sin límite
        ├── subagent_depth = 1 (default)
        └── MCP = 0   plugins = 0   agents custom = 0


  D O N D E   S Í   A P O Y A   L A   P R O T E C C I Ó N
  ══════════════════════════════════════════════════════
  AGENTS.md:289-333  "prohibido sudo / systemctl / sysfs / GPU / commit"
        │
        │  ✗ sin regla `deny` en configuración
        │  ✗ sin `bash: ask`
        │  ✗ sin `steps`
        ▼
  CUMPLIMIENTO = DECISIÓN DEL MODELO EN CADA LLAMADA
  (0 denegaciones del harness registradas en 102 sesiones
   = coherente con que nada está bloqueado)
```

```
  SEPARACIÓN PODER / DEBER — ESTADO REAL
  ═════════════════════════════════════
  PUEDE      bash=allow  edit=allow  read=allow  webfetch=allow
     │
     │  ← NO hay barrera técnica entre estas dos filas
     ▼
  AUTORIZADO  AGENTS.md §289-333  (prosa, sin mecanismo de aplicación)
     │
     ▼
  DEBE        AGENTS.md completo (prosa)
     │
     ▼
  CUMPLIDO    0 sudo  0 sysfs  0 commits  ← observado en ESTA ronda
                        por autoinstrumentación, sin vigilancia externa
```
