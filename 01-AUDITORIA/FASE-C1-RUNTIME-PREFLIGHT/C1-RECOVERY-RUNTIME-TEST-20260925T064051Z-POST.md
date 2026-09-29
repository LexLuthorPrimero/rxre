# Recovery Runtime Test — POST_REBOOT — C1-RECOVERY-RUNTIME-TEST-20260925T064051Z

**Timestamp:** `2026-09-25T07:43:17+00:00`
**Pre-reboot JSON SHA256:** `a37762cc257a701434b89cac21667c6b96d3681bdb33ccd1ed87cacc88b3c37a`
**Parent JSON SHA256:** `1b1f8e27cdc53a9a3d1f2353bd819ceb15008dbd96ee99f534cda1db81246e0f`
**Mode:** `READ_ONLY_RECOVERY_TEST`

## Result
```text
PREVIOUS_RECOVERY=UNKNOWN
RECOVERY=FAIL
RECOVERY_TEST_RESULT=FAIL
RECOVERY_PRESENT=PARTIAL
RECOVERY_ACCESSIBLE=NO_LOGIN_PROMPT_OBSERVED
RECOVERY_INDEPENDENT=NOT_DEMONSTRATED
RECOVERY_VERIFIED=NO
RECOVERY_USABLE=NO
TTY_LOGIN=FAIL_NO_INTERACTIVE_TTY
RETURN_TO_GRAPHICAL=PASS
PERMANENT_CHANGES=UNKNOWN
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

## Findings
- The normal reboot completed and the system returned to `graphical.target`; KWin/Xwayland/ChatGPT processes are present.
- The agent shell remains non-TTY (`tty`: no es un tty; stdin `/dev/null`). `getty@tty1.service` is enabled but inactive and no agetty/login process was observed. No TTY switch or login was forced.
- Project, AGENTS.md and restore source are readable from the current session, but accessibility from an independent TTY is not demonstrated.
- `rescue.target`/`emergency.target` remain present and inactive; they were not started.
- `systemctl is-system-running` reports `degraded`; no failed units were repaired.
- Kernel changed from the pre-reboot recorded `7.2.6-201.nobora.fc44.x86_64` to `7.2.4-201.nobara.fc44.x86_64`; this mismatch is recorded, not corrected.

## Accounting
```text
C1_EXECUTED=0
RUNTIME_MATERIALIZED=0
GPU_WRITES=0
STORAGE_WRITES=0
SYSTEMD_CHANGES=0
SYSTEM_CHANGES=0
REBOOT=1
COMMIT=0
```

- Structured post-reboot evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-RECOVERY-RUNTIME-TEST-20260925T064051Z-POST.json`
- JSON SHA256: `b1ed5e3659553d96b1a22cf1f9188fcbb8a001ae0298feed62a860ef8e37d6a3`
- No C1, target start/isolate, TTY switch, GRUB change, client treatment, GPU/storage write, runtime materialization, repair, or commit.
