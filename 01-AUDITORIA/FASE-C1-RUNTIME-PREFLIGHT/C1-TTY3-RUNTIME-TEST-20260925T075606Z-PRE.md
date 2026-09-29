# TTY3 Runtime Test — PRE — C1-TTY3-RUNTIME-TEST-20260925T075606Z

**Mode:** `RUNTIME_CONTROLLED_TTY3`
**Timestamp:** `2026-09-25T07:56:06+00:00`
**Parent audit SHA256:** `7211ea8ae182450dd165e88d8fd6985d51da6e709d8ca9da4dcf543a5ccb8111`

## PRE
```text
GETTY_TTY3_EXPECTED=disabled/inactive
START_ACTION=systemctl start getty@tty3.service (not yet executed)
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

- PRE captures getty@tty3, getty@tty1, targets, Plasma Login, display-manager, logind, VT, Wayland clients, GPU holders, project hashes and accounting.
- No start, stop, enable, chvt, reboot, target transition, C1 or client treatment occurred in PRE.

- Structured PRE evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY3-RUNTIME-TEST-20260925T075606Z-PRE.json`
- JSON SHA256: `50526ccebc426132159b02dd35effe6b80c224d85cd25a7fbcdb5af38b8a60bf`
