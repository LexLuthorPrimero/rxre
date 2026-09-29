# TTY3 Interactive Login Test — PRE — C1-TTY3-INTERACTIVE-LOGIN-TEST-20260925T080020Z

**Mode:** `CONTROLLED_TTY3_INTERACTIVE_LOGIN`
**Timestamp:** `2026-09-25T08:00:20+00:00`
**Parent SHA256:** `e7d1d6e55a004badc1846f5edf9c945b7cb202074986b888e0cd37d323cc740c`

```text
PRE_GETTY_TTY3=disabled/inactive
START_ACTION=systemctl start getty@tty3.service (not yet executed)
CHVT=NOT_ALLOWED
TTY3_PHYSICAL_ACCESS=UNRESOLVED
C1=DEFERRED
GO_C1=NOT_AVAILABLE
```

- PRE includes getty/targets, Plasma Login/display-manager, logind, active VT, Wayland clients, project hashes and accounting.
- No start, stop, enable, chvt, login, reboot, C1 or client treatment occurred during PRE.

- Structured PRE evidence: `/home/lucas/Escritorio/RX550-INVESTIGACION/01-AUDITORIA/FASE-C1-RUNTIME-PREFLIGHT/C1-TTY3-INTERACTIVE-LOGIN-TEST-20260925T080020Z-PRE.json`
- JSON SHA256: `481b40c95ce56afb83212d4ceddfdba8159e1e2c6e7720bd81cad6817f7e8c7d`
