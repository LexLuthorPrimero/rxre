# TTY3 Controlled Runtime Test — C1-TTY3-RUNTIME-TEST-20260925T075606Z

**Mode:** `CONTROLLED_TTY3_RUNTIME_TEST`
**Timestamp:** `2026-09-25T07:57:27+00:00`
**PRE JSON SHA256:** `50526ccebc426132159b02dd35effe6b80c224d85cd25a7fbcdb5af38b8a60bf`

## Result
```text
GETTY_TTY3_RUNTIME=PASS
GETTY_TTY3=ACTIVE_DURING_TEST
GETTY_PID=7958
TTY3_INTERACTIVE_LOGIN=NOT_TESTED
TTY3_LOGIN=NOT_TESTED
TTY3_INDEPENDENCE=UNKNOWN
RESTORE=COMPLETED
FINAL_ACTIVE=inactive
FINAL_ENABLED=disabled
RECOVERY=FAIL
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

## PRE / ACTION / POST
- PRE: `getty@tty3=disabled/inactive`; Wayland session on tty2; no tty3 login.
- ACTION: exactly `systemctl start getty@tty3.service`; no `enable`, `chvt`, login, target transition or reboot.
- START: returned 0; `getty@tty3=active/running`, PID 7958, `agetty`, `TTYPath=/dev/tty3`, `ConditionResult=yes`.
- LOGIN: not tested because no safe interactive TTY access was available without `chvt`; no logind tty3 session appeared.
- STOP: exactly `systemctl stop getty@tty3.service`; returned 0; journal records start and successful stop.
- POST: `getty@tty3=inactive/disabled`; graphical.target, Plasma Login/display-manager, KWin, Xwayland, ChatGPT, Wayland session and active VT tty2 remained.
- No unexpected impact observed. Runtime start/stop were temporary and restored; no permanent systemd/configuration change observed.

## Accounting
```text
C1_EXECUTED=0
RUNTIME_MATERIALIZED=0
GPU_WRITES=0
STORAGE_WRITES=0
SYSTEMD_CHANGES=2_TEMPORARY_RUNTIME_ACTIONS_RESTORED
SYSTEM_CHANGES=2_TEMPORARY_RUNTIME_ACTIONS_RESTORED
COMMIT=0
```

- Structured POST evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY3-RUNTIME-TEST-20260925T075606Z-POST.json`
- JSON SHA256: `e7d1d6e55a004badc1846f5edf9c945b7cb202074986b888e0cd37d323cc740c`
- No C1, GPU/client treatment, GPU/storage write, reboot, chvt, enable, display-manager/Plasma change, or commit.
