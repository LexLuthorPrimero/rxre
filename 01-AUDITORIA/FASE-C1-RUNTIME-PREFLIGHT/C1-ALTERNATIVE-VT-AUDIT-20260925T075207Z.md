# Alternative VT Read-Only Audit — C1-ALTERNATIVE-VT-AUDIT-20260925T075207Z

**Mode:** `READ_ONLY_ALTERNATIVE_VT_AUDIT`
**Timestamp:** `2026-09-25T07:52:07+00:00`
**Parent:** `C1-RECOVERY-RUNTIME-TEST-20260925T064051Z`
**Parent SHA256:** `b1ed5e3659553d96b1a22cf1f9188fcbb8a001ae0298feed62a860ef8e37d6a3`

## Result
```text
P0=B__CONTAMINATED_REQUIRES_ISOLATION
OWNERSHIP=PARTIAL
PREVIOUS_RECOVERY=FAIL
RECOVERY=FAIL
ACTIVE_VT=tty2
TTY1=EXISTS;GETTY_ENABLED_INACTIVE;PLASMALOGIN_CONFLICT
TTY2=EXISTS;GETTY_DISABLED_INACTIVE;WAYLAND_SESSION
TTY3_TTY6=EXIST;GETTY_DISABLED_INACTIVE;NO_LOGIND_SESSION
CONFLICT_SCOPE=tty1_ONLY_SUPPORTED
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

## Findings
- `tty1..tty6` device nodes exist. Only tty1 has a `getty.target.wants` symlink; tty2..tty6 template instances are loaded but disabled/inactive.
- `plasmalogin.service`/`display-manager.service` explicitly conflict only with `getty@tty1.service` and `kmsconvt@tty1.service`; no explicit Plasma conflict for tty2..tty6 was found.
- `systemd-getty-generator` is documented for serial/kernel consoles; no `console=` parameter or generated serial instance was observed. `autovt@.service` is a symlink to `getty@.service`, not a separate generator instance.
- logind recognizes seat0 and can use TTYs, but its active session is Wayland on tty2; no sessions are associated with tty3..tty6.
- VT/DRM and framebuffer state is present; no technical impossibility for tty3..tty6 was proven, but no login getty is currently available.
- No alternative VT is classified as `RECOVERY=PASS`; enabling/starting a getty would be a future modification and was not performed.

## Provenance
- Structured evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-ALTERNATIVE-VT-AUDIT-20260925T075207Z.json`
- JSON SHA256: `7211ea8ae182450dd165e88d8fd6985d51da6e709d8ca9da4dcf543a5ccb8111`
- No reboot, chvt, getty/display-manager/Plasma/GRUB/kernel change, login, target transition, C1, client treatment, GPU/storage write, or commit.
