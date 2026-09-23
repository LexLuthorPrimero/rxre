# Evidence — CIERRE 2026-09-19
Referencias a datos y reportes. Los históricos detallados viven en el backup
`~/Escritorio/RX550_Modo_Torneo_Backup_2026-09-19_0836/` y en `rejected_ideas.md`/`research_log.md`.

## Episodios y archivos de resultado
| Experimento | Dir | Resultado |
|---|---|---|
| FASE A (discriminación) | `experiments/fase-a-discriminacion-20260919-114241/` | `RESULTADOS-FASE-A.md`, `INVALIDACION-corridas-04-09.md`; 3 GL válidas + 3 VK phong + 3 VK default |
| FASE B (cap probe) | `experiments/fase-b-cap-probe-20260919-122038/` | `RESULTADOS-FASE-B.md`, 28 runs cap 25/28/32/35 W desde frío |
| EP-08 (auditoría telemetría) | `experiments/fase-b-cap-probe-20260919-122038/EP08-auditoria-telemetria-E1E3.md` | E1/E3 muestrearon la RX 550 real; runner no está en backup |
| EP-06 (soak + réplica E1) | `experiments/ep06-soak-cap-20260919-205645/` | `RESULTADOS-EP06.md`, soak 1/2 CSV, réplica E1 caliente |
| EP-05 (A/B Mesa CUSTOM vs STOCK) | `experiments/ep05-mesa-custom-20260919-212249/` | `RESULTADOS-EP05.md`, `CONDICIONES.txt`, 12+4 runs con telemetry.csv + libs-cargadas.txt |

## Números reproducibles clave (ver knowledge.md y BUILD_SPEC §15)
- Draw: 9.4-13.6 W; cap nunca liga hoy; max 13.6 W @2560×1440 texturizado (EP-06).
- Clocks en carga: SCLK 1071, MCLK 625 (picos 1500 transitorios); MCLK idle 300.
- FPS base: GL jelly 640p 1228-1250; VK phong 640p 396-413; VK shading 640p 403-413; jelly 1080p 202-204;
  desktop 1080p 199-202; shading 1080p 73.
- EP-05 A/B (1080p): CUSTOM==STOCK (ΔFPS≤1%, ΔP≤0.3 W); Mesa verificada por /proc maps (CUSTOM =
  /opt/mesa-26.2.2-rx550-haswell/lib64/libgallium-26.2.2.so + libvulkan_radeon; STOCK = /usr/lib64).
- kalm: 17/09 (día de E1/E3/E5) 0 eventos [Kalm] en journal; 18-19/09 decenas de miles (kalm real activo)
  con régimen libre. kalm descartada como explicación del régimen histórico.

## Datos históricos NO reproducidos (registro, no hecho)
- E1/E3/E5 (17/09): ver backup `experiments/mesa-e1-20260917-170430/`, `mesa-e3-20260917-213646/e5/`.
  25 W pin/SCLK ~350-390/MCLK ~1250-1500/74-92 °C; phong 1285 fps; desktop 443 fps @1080@35 W.
  Toda la sesión del 17/09 no se ha reproducido hoy (Fase B, EP-06, EP-05). => [NO REPRODUCIBLE].