# TTY3 Interactive Login Test — C1-TTY3-INTERACTIVE-LOGIN-TEST-20260925T080020Z

**Mode:** `CONTROLLED_TTY3_INTERACTIVE_LOGIN_TEST`
**Timestamp:** `2026-09-25T08:01:06+00:00`
**PRE JSON SHA256:** `481b40c95ce56afb83212d4ceddfdba8159e1e2c6e7720bd81cad6817f7e8c7d`

```text
GETTY_TTY3_RUNTIME=PASS
TTY3_INTERACTIVE_ACCESS=NOT_AVAILABLE_FROM_AGENT
TTY3_LOGIN_PROMPT=NOT_OBSERVED
TTY3_LOGIN=NOT_TESTED
TTY3_INDEPENDENCE=UNKNOWN
RESTORE=COMPLETED
RECOVERY=FAIL
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

## PRE / ACTION / POST
- PRE: `getty@tty3=disabled/inactive`; active Wayland session on tty2; no tty3 session.
- START: exactly `systemctl start getty@tty3.service`; returned 0; PID 8658; `agetty`; `TTYPath=/dev/tty3`; `ConditionResult=yes`.
- ACCESS: agent has no physical VT/TTY interface (`tty` reports no tty, stdin `/dev/null`). Per instruction, no `chvt`, login, or alternative method was attempted.
- LOGIN: not tested; no prompt, shell, credentials, or logind tty3 session was obtained.
- STOP: exactly `systemctl stop getty@tty3.service`; returned 0; final state restored to inactive/disabled.
- Graphical target, Plasma Login/display-manager, KWin, Xwayland, ChatGPT, Wayland session, active VT tty2 and tty1 state were unchanged.

## Accounting
```text
C1_EXECUTED=0
RUNTIME_MATERIALIZED=0
GPU_WRITES=0
STORAGE_WRITES=0
PERMANENT_SYSTEMD_CHANGES=0
SYSTEMD_CHANGES=2_TEMPORARY_RUNTIME_ACTIONS_RESTORED
SYSTEM_CHANGES=2_TEMPORARY_RUNTIME_ACTIONS_RESTORED
REBOOT=0
COMMIT=0
```

- Structured POST evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY3-INTERACTIVE-LOGIN-TEST-20260925T080020Z-POST.json`
- JSON SHA256: `9ee3e117747132bd2fcb28e8d050a462c9f4bd813487d82ca78b4d7aec2b05a9`
- No C1, runtime materialization, client treatment, GPU/storage write, reboot, chvt, enable, Plasma/display-manager change, or commit.
