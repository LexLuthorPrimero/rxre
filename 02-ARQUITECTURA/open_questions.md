# Open Questions — CIERRE 2026-09-19

> **Reconciliación terminológica 2026-09-24:** `W_SMU` significa en estas preguntas
> `W_SMU`/potencia estimada por SMU; no una medición física independiente.
Solo preguntas relevantes que permanecen abiertas (referencias a BUILD_SPEC §45).

> **IDEAS DEL USUARIO (relacionadas, no incorporadas como hechos):** 184 ideas
> originales del usuario están clasificadas y trazadas en `IDEA-REGISTER.md`
> (`02-ARQUITECTURA/`). Este documento sigue siendo el registro de *preguntas
> abiertas con evidencia*; una idea no es pregunta hasta que exista evidencia
> que la separe de la ausencia de respuesta.

- **O-P0-ENV** ¿Qué clientes, agentes y estado de CPU/IRQ/HDD/PM deben aislarse antes de atribuir una corrida a la RX550? El gate READ-ONLY del 2026-09-24 terminó en **B. `CONTAMINATED_REQUIRES_ISOLATION`**: ownership `PARTIAL`, clientes `Xwayland`/`ChatGPT` abiertos, escrituras observadas de autopilot/kalm y `kalm-gpu` con capacidad de cap/DPM. La aislación exacta y su autorización siguen pendientes; no se modifica el sistema desde este registro. Fuente: `01-AUDITORIA/FASE-P0-EXPERIMENTAL-VALIDITY-GATE/P0-EXPERIMENTAL-VALIDITY-GATE-2026-09-24.md`.
- **O-ROOT** ¿Qué causó el régimen histórico E1/E3/E5 (25-31 W / SCLK ~350-390 / MCLK ~1250-1500 /
  74-92 °C / phong 1285 fps)? Descartados por evidencia: cap simple, calor hasta 71 °C, kalm, Mesa CUSTOM,
  otra GPU. Causa [DESCONOCIDA]. No inventar. Discriminador futuro: el propio entorno de la sesión del
  17/09 (kernel/sesión/GUI idénticos) — sin autorización nueva NO se investiga más.
- **O-MCLK** ¿Qué disparó el MCLK alto sostenido (1250-1500) en esa sesión y por qué hoy queda en 625
  (solo picos transitorios)? Hipótesis candidata: presión de memoria de un workload distinto. Prueba
  futura: perfil experimental con forcing MCLK (requiere autorización).
- **O-PHY** ¿Cuál es el W_SMU máximo sostenido de la RX 550 en cargas extremas (>13.6 W medidos)?
  ¿Hay límite térmico efectivo por debajo de los 88-92 °C del régimen histórico no reproducido?
- **O-BOT** ¿Bottleneck exacto del GL jellyfish 640p (CPU submissions vs present vs VRAM/GTT)?
  Espera perf stat/EP-03.
- **O-Mesa** ¿La Mesa CUSTOM (haswell + ACO) aporta algo con workloads reales/juegos? Sin evidencia hoy.
- **O-FPS** El "phong 1285 fps" de E1: ¿era de otra ventana/superficie? EP-08 no halló el runner; el
  script generador no está en el backup. Solo se puede re-medir con una reconstrucción equivalente (EP-07),
  requiere autorización.

Cerradas con evidencia (no listadas aquí): el régimen no es cap-bind, no es kalm, no es Mesa CUSTOM,
no es otra GPU; GL 640p no es SCLK-bound; `W_SMU` observada ≤13.6 W; cap default 35 W.
