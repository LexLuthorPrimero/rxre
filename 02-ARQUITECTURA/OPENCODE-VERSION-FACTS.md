# OPENCODE-VERSION-FACTS — semántica verificada de OpenCode v2.0.18

**EXTRACTADO de `AGENTS.md` §14.5 el 2026-09-27.** No es instrucción: es
conocimiento verificado, con fecha. Vuelve a él bajo demanda, no en cada
sesión. `AGENTS.md` §14.5 conserva el puntero y la regla de re-verificar.

**Verificado contra el binario instalado y la documentación oficial el
2026-09-27.** Documentado ≠ garantizado: una versión posterior puede
cambiarlo. Re-verifica antes de depender de él.

---

Verified against opencode **v2.0.18** and the official documentation on
2026-09-27 (`https://opencode.ai/docs/{rules,config,agents,permissions,skills}.md`,
HTTP 200). **Re-read them before relying on any of this; these are documented
behaviours, not guarantees, and a later version may differ.**

- **Instructions.** `AGENTS.md` is read from the project, traversing upward;
  `~/.config/opencode/AGENTS.md` is global; `~/.claude/CLAUDE.md` and
  `~/.claude/skills/` are **fallbacks** used when the corresponding
  `opencode`-owned file is absent, and the project's `CLAUDE.md` is a fallback
  used when no `AGENTS.md` exists. The first match wins **in each category**, and
  files from different categories are **combined, not overridden — conflicts
  between them are not resolved.** Editing an `AGENTS.md` does not change the
  instructions already in the current session; a new session is what applies the
  new text.
- **Tool availability is not guaranteed and must not be assumed.** A tool may be
  absent in a given session or version. **Check that a capability exists before
  promising it or building a plan on it**, and never report a capability as
  available because a catalogue lists it.
- **Config.** `opencode.json` / `.jsonc`, merged across locations, later sources
  overriding only conflicting keys. Keys relevant here: `permission` · `agent` ·
  `default_agent` (must be a primary agent; falls back to `build` with a warning) ·
  `model` · `steps` (unset means iterate until the model stops — no cap) ·
  `instructions` · `mcp` · `plugin` · `command` · `subagent_depth` (default 1) ·
  `autoupdate` · `snapshot` · `share`.
- **Permissions.** Actions resolve to `allow` · `ask` · `deny`. Defaults are
  permissive: most are `allow`; `doom_loop` and `external_directory` are `ask`;
  `read` denies `*.env`. **Do not assume a `deny` you did not verify covers the
  tool you are about to use** — confirm against the configuration actually in
  force.
- **Agents.** `build` and `plan` are primary (all tools vs `edit`/`bash` set to
  `ask`); `general`, `explore` and `scout` are subagents. Versioning this file is
  recommended for traceability and sharing, and is not a precondition for a new
  session picking up an edit.
- **The audit is not self-applying.** An instruction here cannot grant, revoke or
  verify a permission. What the engine enforces and what this file asks of you
  are two different things, and only the first one is guaranteed.

---

---

## Contradicción doc↔binario detectada (2026-09-27)

| Ajuste | Schema oficial `config.json` | `docs/config.md` | Binario v2.0.18 |
|---|---|---|---|
| `subagent_depth` | **presente** en `$defs/Config/properties` | sección *Subagent depth* con default 1 | `path=$.subagent_depth kind=unsupported action="omitted unsupported legacy setting"` — **lo descarta** |

**Resolución aplicada:** la clave se eliminó de `opencode.json`. Mantener un
ajuste que el motor ignora en silencio es exactamente la trampa
*configuración presente ≠ configuración efectiva*. **No reconciliado**: queda
registrado como `CONTRADICTION` con `RESOLUTION_STATUS=RESOLVED_BY_REMOVAL`.

## Ausencia de auditoría de denegaciones

Un `deny` ejecutado devuelve `{"error":{"type":"permission.rejected"}}` al
agente, pero **no se registra como evento en `opencode.log`**. Comprobado el
2026-09-27. Consecuencia: el log **no sirve como evidencia de que una
prohibición se respetó**; sólo la salida de la herramienta lo demuestra.
`COMPLIANCE_NOT_OBSERVABLE` desde el log.
