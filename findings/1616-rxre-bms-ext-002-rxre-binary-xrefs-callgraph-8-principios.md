# RXRE-BMS-EXT-002-F: binary.xrefs y binary.callgraph operativos + 8 principios auditados

**Fecha:** 2026-10-16  
**Estado:** VERIFIED  
**Capability:** `binary.xrefs`, `binary.callgraph`  
**Target:** RX 550 / Polaris12 / GFX8  
**Producer:** rizin 0.7.4 / radare2  

## RESUMEN EJECUTIVO

Tres adapters RXRE (`rz_xrefs.py`, `rz_callgraph.py`, `umr_read.py`) y el entry
`machine.py` tenían defectos que bloqueaban el funcionamiento por la CLI y
rompían el loop de los 8 principios. Después de las correcciones:

- `binary.xrefs` por CLI: **empty → ok** (74 xrefs sobre /bin/ls)
- `binary.callgraph` por CLI: **empty → ok** (5 nodes sobre /bin/ls)
- Audit 8 principios: **operacion_cerrada=True, estado=ok, 8/8 cumplen, 0 violaciones**
- Tests: xrefs 30/30, callgraph 21/21, cli009 71/71, autonomy003 11/11

## HALLAZGOS

### Hallazgo 1: `artefacto.encode()` — el path como contenido (RXRE-BMS-EXT-002-C)

**Problema:** `rz_xrefs.py` y `rz_callgraph.py` hacían
`entrada = artefacto.encode() if isinstance(artefacto, str) else artefacto`.
El CLI pasa un **path string** (`/bin/ls`), que `.encode()` convertía a los
bytes de la CADENA, no del contenido del archivo. rizin/r2 analizaba `b'/bin/ls'`
(8 bytes), no el ELF.

```
CLI (before): echo '{"op":"run","capability":"binary.xrefs","artefacto":"/bin/ls"}' | ./rxre
→ status: empty, precheck: null, ejecucion: null, results: 0

CLI (after):  echo '{"op":"run","capability":"binary.xrefs","artefacto":"/bin/ls"}' | ./rxre
→ status: ok, precheck: {input_hash, elf_tipo, ...}, ejecucion: {argv, exit_status, ...}, results: 74
```

**Fix:** Aceptar artefacto como PATH (`str` que existe en disco) o BYTES
(backward compat). Un path válido se pasa DIRECTAMENTE a argv del producer
(como `rz_cfg.py`), con validación `os.path.isfile`, `sha256_de(content)`,
y `ELF signature check`. No se codifica como contenido.

**Patrón correcto:** `rz_cfg.py` → `sha256_de(artefacto)` + `artefacto` como
argumento directo en `argv = [exe, ..., artefacto]`.

### Hallazgo 2: `provenance` como string vs dict (TIERRA, FUEGO)

**Problema:** El `provenance` field era el string `"completa"`, no un dict
estructurado. Los tests `ocho_principios` (RXRE-ECO-001) requieren:
- TIERRA: `provenance.estado == "completa"` + `provenance.input_hash`
- FUEGO: `provenance.transformacion` + `provenance.normalizador`

**Fix:** Cambiado a dict:
```python
"provenance": {
    "estado": "completa",
    "input_hash": input_hash_str,
    "backend": ident_backend,
    "command_or_api": ejec.get("command_or_api", ""),
    "transformacion": "rizin/r2 -c 'aaa; axtj...' -> limieza ANSI -> json.loads -> results",
    "normalizador": "backends.adapters.rz_xrefs.xrefs",
    "tool_version": ident.get("tool_version", ""),
    "repository_commit": ident.get("repository_commit", ""),
    "provenance_estado": "completa",
}
```

### Hallazgo 3: `raw.n_coincidencias` y `value.nodos` faltantes (ALMA, ETER)

**Problema:** Los resultados individuales no tenían los campos que
`ocho_principios` verifica:
- ALMA requiere: `value.nodos > 0` OR `raw.n_coincidencias` truthy
- ETER requiere: `value.nodos > 0` AND `raw.n_coincidencias` truthy

**Fix:** Añadido a cada result:
```python
# En value:
"nodos": xrefs_count  # o nodes para callgraph

# Campo raw nuevo:
"raw": {
    "n_coincidencias": xrefs_count,  # o nodes
    "nodos": xrefs_count,
}
```

### Hallazgo 4: `backend_existe` en `umr_read.py` — orden de validaciones (CUERPO)

**Problema:** `umr_read.register_read` inicializaba
`pre = {"backend_existe": False, ...}` y hacía early-returns en las
validaciones de formato de register_name y BD estática. Estas early-returns
no actualizaban `backend_existe`, por lo que el precheck reportaba
`backend_existe: False` para UMR que EXISTE en `/usr/bin/umr`.

**Fix:** Mover la verificación `b.existe()` DESPUÉS de la PCI validation
(gate de seguridad) pero ANTES de las validaciones de register_name formato,
para que el precheck reporte `backend_existe: True` incluso cuando falla
la validación del formato del registro.

### Hallazgo 5: BODY→MIND loop roto por precheck (RXRE-AUTONOMY-003)

**Problema:** `_verificar_integridad_artefacto` en `machine.py` (otro session)
hace `early return` con `next_actions: []` para artefactos inválidos,
saltando el código BODY→MIND que genera `reflexion_sugerida`. Esto rompe
el loop de retroalimentación: observación → registro → aprendizaje.

**Fix:** El early return ahora incluye:
- `next_actions` con `{"op": "reflect", "args": {"outcome": "failure"}}`
- `reflexion_sugerida` con `outcome: "failure"`

Además, distinción `invalid_input` vs `blocked`:
- Artefacto proporcionado pero inexistente → `invalid_input`
- Artefacto no proporcionado → `blocked`
(Sigue §10 TAXONOMÍA de AGENTS.md)

### Hallazgo 6: `inicio` offset hardcoded en `axtj` (RXRE-BMS-EXT-002-C)

**Problema:** El offset `0x4000` era hardcoded en el comando `axtj @ 0x4000`,
ignorando los parámetros `inicio` y `longitud` declarados en dispatch.

**Fix:** `inicio` controla el offset: `addr = "0x%x" % inicio if inicio is not None else _DEFAULT_XREF_ADDR`.
El default `0x4000` se mantiene (verificado: produce 74 xrefs en /bin/ls).
**Nota:** En rizin 0.7.4, `axtj @ <addr>` lista TODOS los xrefs (quirk);
`axtj` sin `@ addr` devuelve 0.

## VERIFICACIÓN

### Tests ejecutados (todos PASS):

| Suite | Resultado |
|---|---|
| test_xrefs1635.py | 30/30 ✅ |
| test_callgraph1636.py | 21/21 ✅ |
| test_cli009.py | 71/71 ✅ |
| test_autonomy003.py | 11/11 ✅ |
| test_eco_principios002.py | 39/39 ✅ |
| test_eco_ast001.py | 58/58 ✅ |
| test_dispatch004.py | 132/132 ✅ |
| test_umr_hardware002.py | 11/11 ✅ |
| test_backends_bulk.py | 112/113 (1 pre-existing failure) |

### Audit 8 principios (RXRE-ECO-001):

**binary.xrefs vía CLI:**
```
operacion_cerrada: True
estado: ok
cumplen: [CUERPO, MENTE, ALMA, TIERRA, FUEGO, AIRE, AGUA, ETER]
violacion: []
sin_probar: []
```

**binary.callgraph vía CLI:**
```
operacion_cerrada: True
estado: ok
cumplen: [CUERPO, MENTE, ALMA, TIERRA, FUEGO, AIRE, AGUA, ETER]
violacion: []
```

### Evidence artifacts:

- `/tmp/rxre_audit_final.json` — binary.xrefs CLI response (74 results, provenance: completa)
- `/tmp/rxre_cg_audit.json` — binary.callgraph CLI response (5 nodes, provenance: completa)
- `reflexion_2d802a5b0fd417d3` — reflexión registrada y vigilada

## ARCHIVOS MODIFICADOS

| Archivo | Cambio | Principios impactados |
|---|---|---|
| `backends/adapters/rz_xrefs.py` | Rewritten: path/bytes, precheck, provenance dict, raw fields | CUERPO, MENTE, ALMA, TIERRA, FUEGO, AIRE, AGUA, ETER |
| `backends/adapters/rz_callgraph.py` | Same 3 defects fixed (same pattern) | CUERPO, MENTE, ALMA, TIERRA, FUEGO, AIRE, AGUA, ETER |
| `backends/adapters/umr_read.py` | precheck: backend_existe verified before early-returns | CUERPO |
| `api/machine.py` | BODY→MIND: reflect suggestion in early return; invalid_input vs blocked distinction | CUERPO, MIND |

## LIMITACIONES

- `test_backends_bulk` falla en `t_coccinelle_real` (KeyError: n_hits) — **pre-existing**,
  causado por cambios del otro session en `dispatch.py`/`registry.py`. Verificado con
  `git stash`: falla sin mis cambios también.
- `amdgpu.ko` (37MB) con `aaa` supera el timeout del shell (120s) — se verificó con /bin/ls.
- `gpu.register_read` requiere root (`sudo -n`); en esta sesión está bloqueado.
