# TTY / Getty Read-Only Audit — C1-TTY-GETTY-AUDIT-20260925T074900Z

**Mode:** `READ_ONLY_TTY_GETTY_AUDIT`
**Timestamp:** `2026-09-25T07:49:00+00:00`
**Parent runtime-test POST:** `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-RECOVERY-RUNTIME-TEST-20260925T064051Z-POST.json`
**Parent SHA256:** `b1ed5e3659553d96b1a22cf1f9188fcbb8a001ae0298feed62a860ef8e37d6a3`

## Result
```text
P0=B__CONTAMINATED_REQUIRES_ISOLATION
OWNERSHIP=PARTIAL
PREVIOUS_RECOVERY=FAIL
RECOVERY=FAIL
TTY1=EXISTS_BUT_NOT_ACTIVE_LOGIN
GETTY_TTY1=ENABLED_BUT_INACTIVE
GETTY_REASON=SUPPORTED_DISPLAY_MANAGER_CONFLICT; CONDITION_RESULT_CAUSE=UNKNOWN
SEAT0=EXISTS;CAN_TTY=YES;ACTIVE_SESSION=3_TTY2_WAYLAND
KERNEL_RELEVANCE=UNKNOWN
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

## Findings
- `/dev/tty0`..`/dev/tty6` exist; `/dev/tty1` is a root-owned 4:1 character device. The active VT reported by `/sys/class/tty/tty0/active` is `tty2`.
- `getty.target` is active and the enabled symlink `getty.target.wants/getty@tty1.service` exists, but `getty@tty1.service` is inactive/dead with no journal entries or activation timestamps.
- `plasmalogin.service`/`display-manager.service` explicitly declare `Conflicts=getty@tty1.service` and are active/running. This supports the inactive getty explanation; the exact reason for the persisted `ConditionResult=no` is not independently established.
- `systemd-analyze condition` currently succeeds for `/dev/tty0`, `/dev/tty1` and `/dev/tty2`; current device absence is not supported.
- logind reports `seat0`, `CanTTY=yes`, `CanGraphical=yes`, active session 3 (`VTNr=2`, `TTY=tty2`, `Type=wayland`, `Service=plasmalogin`).
- VT/DRM state shows `vtcon0` bound to a framebuffer, `vtcon1` dummy/unbound, DRM masters for card0/card1, and `amdgpudrmfb`/`i915drmfb`; this is observed relationship, not proven getty causality.
- Kernel differs pre/post (`7.2.6` → `7.2.4`); no direct local evidence links that difference to getty inactivity.

## Provenance
- Structured evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY-GETTY-AUDIT-20260925T074900Z.json`
- JSON SHA256: `cb8a34ae17bbd4a38602df99e6481a111814fc75427824aa6956b52fc71f08e3`
- No reboot, chvt, target transition, getty/GRUB/kernel change, process treatment, GPU/storage write, C1, runtime materialization, or commit.
