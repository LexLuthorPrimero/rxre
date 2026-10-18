# Finding 1617 — RXRE-EXT-003: `rxre verify` health check (CUERPO)

**Fecha:** 2026-10-15
**Categoría:** tooling / CLI / health-check
**Autor:** OpenCode agent (iteración 8-principios)
**Estado:** ✅ completada

## Resumen

Se añade `op: verify` al motor RXRE, operación read-only de health check previo a
cualquier acción. Verifica 4 dimensiones antes de ejecutar:

1. **Database writability** — la BD que RXRE usará para persistir está conectable.
2. **Backend executables en PATH** — umr, rizin y radare2 existen y su versión
   está verificada.
3. **Hardware fingerprint** — la RX 550 (PCI `0000:01:00.0`, vendor `0x1002`,
   device `0x699f` = Polaris12) está presente; la Intel iGPU (`0000:00:02.0`)
   está fuera de la allow-list.
4. **Artefacto válido** (opcional) — existe, es ELF, se detecta su tipo
   (ET_REL/ET_EXEC/ET_DYN) y se calcula el sha256.

## Principio asociado

**CUERPO** (homeostasis): el sistema verifica su propio estado antes de actuar.
Un `verify` previo evita el error F8 (exit 0 con salida incorrecta) porque
detecta condiciones no evaluadas: versión no verificada, ruta no en PATH,
hardware fuera de allow-list, hash corrupto.

## Evidencia

```
echo '{"op":"verify","artefacto":"/bin/ls"}' | ./rxre
```

```json
{
  "status": "ok",
  "op": "verify",
  "checks": {
    "database": {"ok": true, "detail": "conectado"},
    "backends": {
      "umr": {"ok": true, "path": "/usr/bin/umr", "version_verified": true, ...},
      "rizin": {"ok": true, "path": "/usr/bin/rizin", "version_verified": true, ...},
      "radare2": {"ok": true, "path": "/usr/bin/radare2", "version_verified": true, ...}
    },
    "hardware": {
      "allow_list": ["0000:01:00.0"],
      "pci_present": {"0000:01:00.0": {"present": true, "vendor": "0x1002", "device": "0x699f"}},
      "intel_igp_blocked": true
    },
    "artefacto": {"path": "/bin/ls", "exists": true, "is_elf": true, "elf_type": "ET_DYN", "sha256": "..."}
  }
}
```

## Contracto

- **READONLY:** sí (lee PATH, /sys/bus/pci, filesystem — no escribe en nada).
- **WRITES_GPU:** no.
- **TOUCHES_INTEGRATED:** no (no ejecuta backends, solo verifica su existencia).
- **TOUCHES_INTEL_iGPU:** no.

## Cambios

`tools/rxre/api/machine.py`:
- Añadido `_handle_verify()` con 4 checks.
- Registrado en `HANDLERS` y en el listado de `op: ops`.

## Relacionado

- `RXRE-002` (allow-list PCI de la RX 550)
- `findings/1616-rxre-bms-ext-002-rxre-binary-xrefs-callgraph-8-principios.md`
