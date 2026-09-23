# RESULTADOS — EXP-F4-A v2.3 (FASE R-4B): CONTROL TÉRMICO DE PHASE 2

**Fecha:** 2026-09-23 · **Sesiones:** S1-v2.3 (completa) · S2-v2.3 (**PARADA D**, rc=9)
**Decisión aplicada:** Opción 3 (usuario): R1–R6 con 6 GOV + 6 FIXED (entrada ≤50 °C);
DIST = DIAGNOSTIC / NOT FOR VERDICT, R7 por separado; veredicto a lo sumo `INCONCLUSO`.

---

## 0. Estado ejecutivo

| Sesión | Fase 1 | Phase 2 | Estado final |
|---|---|---|---|
| **S1-v2.3** | 15/15 bloques · FREEZE T=9.153 ms · s\*=0.75 · gates PASS | **8/8 trials** (3 fixed + 3 gov + 2 dist), cooldowns 150–341 s | **Completa y verificada** |
| **S2-v2.3** | **10/15 bloques** (solo p1 asc + p2 desc) | **NINGUNA** | **PARADA D** en cooldown p2→p3 (Fase 1), anti-deadlock 3600 s |

**Causa de la PARADA D (interferencia externa, no del experimento):** durante el
cooldown p2→p3 el GPU jamás volvió a `SCLK nivel 0 ∧ P < 4 W`. La telemetría
independiente (`/tmp/opencode/micro12/vkmark30-telemetry.csv`, logger read-only activo
desde 2026-09-18) muestra que desde ~03:45 hasta el final la tarjeta quedó con
**`gpu_busy=100 % · SCLK 1071 MHz · mclk 300 · mem_busy 0 · P ≈ 6.4 W` de forma
sostenida** (patrón de presentación/2D, distinto del workload real ~22 W). Los dos
únicos clientes amdgpu de la RX 550 (`0000:01:00.0`) son **Xwayland (pid 2721,
`/dev/dri/card1`)** y el **gpu-process de ChatGPT (pid 3722793, `/dev/dri/renderD129`)** —
ambos ajenos al experimento. El monitor read-only del protocolo cumplió su función:
anti-deadlock 3600 s → PARADA D, sin iniciar ningún trial bajo condición no válida.

**Consecuencia para el veredicto:** la muestra pre-registrada de 6 GOV + 6 FIXED NO
se alcanzó (solo 3 + 3 del S1). `analyze.py final()` (hardcodea session1+session2)
es **inaplicable**: no existe `session2/fase1/manifest.json` ni
`session2/fase2/metrics.json`. Conforme al §6.2 del protocolo y a la opción 3,
el veredicto global queda **`INCONCLUSO`** (nunca SUPPORTED), con la evidencia de S1
reportada como **diagnóstica (n=3), NO veredictal**.

---

## A) R1–R6 (evidencia únicamente de S1, n=3 — NO formal)

Los literales R1–R6 exigen ≥5/6 sobre 6 GOV/FIXED (unión S1+S2). Al faltar S2,
**no se computa veredicto formal** (no se ejecuta `final()` ni se alteran criterios).
Se reportan los valores de S1 como evidencia de orientación:

| Réquila | S1 (n=3) — diagnóstico | Lectura preliminar |
|---|---|---|
| **R1** r ∈ [0.90,1.10] ∧ CI⊂ | r = 1.0194 / 1.0197 / 1.0197; banda [8.238, 10.068] ms; settle p99 ≈ 9.33 ms | 3/3 en banda |
| **R2** overshoot ≤1 % (≥5/6) | `overshoot_pct` (def.: % frames `ft>T_us`) en settle ≈ 66–69 % | **no cumple literal** (diagnóstico) |
| **R3** 0 reversiones sostenidas | reversiones = [0, 0, 0] | 3/3 |
| **R4** convergencia ≤4 ventanas | convergencia en **ventana 5** (escala 0.87, 20 s/ventana) | 0/3 estricto (≈85–100 s) |
| **R5** CV≤10 %, mediana S1↔S2, dir≥90 % | no computable (falta S2) | **--** |
| **R6** permanencia/Δ sin re-incursiones | s_settled = 0.87 vs s\*=0.75 → **Δ=1 paso** sobre s\* | no cumple literal Δ=0 |

- **GOV (3):** convergen rápida en Fase 2: `LOWER` en ventana 1 → escala 0.87; p99
  asentado ≈ 9.33 ms (dentro de banda 9.153·[0.90,1.10]); `control_scale.txt` final
  0.870 en los 3; 0 reversiones.
- **FIXED (3):** p99 ≈ 11.44–11.46 ms (escala 1.00) — director.
- **Comparación pareada (n=3, diagnóstico):** gov ≈ 9.33 ms vs fixed ≈ 11.45 ms →
  **Δ rel ≈ −18.5 %** a favor del governor (consistente en los 3 pares).
- **Ventanas §6.3:** fixed1–3 y gov1–3 **todas limpias** (T_max 66–90 °C, SCLK 1071
  sostenido); sin ventanas `THERMALLY CONFOUNDED` → estas ventanas SÍ habrían sido
  elegibles para R1–R6 de haber existido la muestra completa.

**Conclusión A:** R1–R6 **NO EVALUABLES formalmente** por muestra incompleta.
La evidencia parcial de S1 sugiere convergencia estable del governor (~9.33 ms, Δ
rel −18.5 % vs fixed, 0 reversiones) pero **no alcanza los literales** (overshoot de
frames sobre T ≈ 67 %; convergencia en ventana 5; asentamiento a 0.87 ≠ s\*=0.75).
Nada de esto se usa como veredicto.

---

## B) R7 (DIST) — INCONCLUSIVE / NOT FOR VERDICT, con motivo exacto

**Motivo exacto (dos razones independientes):**

1. **Por diseño (opción 3 autorizada 2026-09-23):** los DIST son
   `DIAGNOSTIC — NOT FOR VERDICT`; el §6.1 y el §6.2 del protocolo fijan que **R7
   NO se evalúa para el veredicto** y NUNCA se usa para declarar PASS. El veredicto
   a lo sumo `INCONCLUSO`.
2. **Por el marcado térmico §6.3 (regla por ventana, pre-registrada):** en S1,
   **dist1 queda `THERMALLY CONFOUNDED` en v5–v9** (T>90 °C desde v5; T_max 91–92 °C;
   SCLK 734→551 MHz y 100 % under-1071 en v7–v9) y **dist2 en v6–v9** (T_max 92 °C,
   SCLK 551 desde v7). Esas ventanas, por regla, **no son evidencia de nada** —ni de
   R7 ni de R6/R1–R6. S2 no llegó a ejecutar DIST.
3. Por tanto, sin S2 y con las ventanas terminales de S1 confounded, **R7 queda
   INCONCLUSIVE / NOT FOR VERDICT**: ni latencias LOW/RAISE/re-incorporación ni nada
   derivado de DIST puede declararse.

**Observación clave (no es anomalía):** el confound de DIST es exactamente lo que
predijo el Anexo 9 del protocolo (presupuesto térmico terminal): con entrada ≤50 °C,
el DIST de 200 s cruza ~90 °C hacia sus últimas ventanas (≈t0+100–120 s). DIST1 cruza
en v5 (T_max 86→91 °C), DIST2 en v6 — coherente con t90 ≈ 100–135 s alineado a m0.
No se refuerza condición ni se toca duración (200 s intacta, lógica +60/+120 intacta).

---

## C) Presupuesto térmico real de la RX 550 (medido, registrar como referencia)

| Magnitud | Valor medido | Fuente |
|---|---|---|
| Cooldown DN-07 por trial (S1) | **8/8 OK**, duración 150–341 s | `fase2/cool{1..8}.tsv` |
| Entrada real alcanzada por trial | 49 °C, SCLK nv0, P ≈ 3.36–3.37 W | `cool1-8.tsv` |
| Ramp térmica (DIST, desde m0) | v0 66–67 °C → v4 86 °C → **v5 91 °C** → v6–v9 92 °C | `marcar_ventanas.py` |
| Cruce 90 °C (t90) | **≈ t0+100–120 s** (entre v4/v5–v6) | ventanas DIST1/DIST2 |
| Colapso SCLK sudoeste | 734 MHz en v6 (50–57 % sample) → **551 MHz 100 %** en v7–v9 | ventanas DIST |
| T_max GOV (120 s) sin confound | 89–90 °C, SCLK 1071 sostenido toda la ventana | gov1–3 |
| T_max FIXED (60 s) | 76–78 °C | fixed1–3 |
| Potencia media steady | fixed/gov ≈ 22.2–22.3 W; max ≈ 22.9 W; dist avg_full ≈ 20.2–20.5 W | `metrics.json` power_* |
| Cap / política | `power1_cap` **35 W intacto**; kalm (4086/4087) intacto en S1 post y S2 pre | `pre/post_flight.txt` |
| Presupuesto terminal | margen 49→90 °C se agota en ~100–120 s para carga DIST | observado |

**Lectura:** el rango operativo seguro del harness es **≤ ~90 °C sin degradación de
SCLK** (GOV/FIXED lo confirman en S1). La carga DIST (200 s, ~22 W steady) excede el
presupuesto terminal y su final queda confounded por regla — correctamente
documentado, sin tocar duraciones ni umbrales.

---

## D) Qué es sólido para IMPLEMENTACIÓN / PERFORMANCE OPTIMIZATION (y qué NO)

**Sólido (evidencia S1, orientativa, no veredictal):**
1. **El governor converge:** en los 3 GOV de S1 pasa de 1.00 → 0.87 en ≤2 ventanas y
   asienta en p99 ≈ 9.33 ms dentro de la banda 9.153 ms, con **0 reversiones** en los
   tres trials y `control_scale` estable 0.870.
2. **Ganancia efectiva frente a FIXED (n=3):** Δ rel ≈ **−18.5 %** de p99 (11.45 →
   9.33 ms), consistente en los 3 pares → dirección correcta para optimización de
   latencia/flicker si los criterios formales n=6 se completan y pasan.
3. **El control térmico por trial (v2.3) funciona:** DN-07 con entrada ≤50 °C se
   cumplió 8/8 en S1 en 150–341 s; los trials se iniciaron solo con SCLK nv0 y P<4 W.
4. **La regla por ventana §6.3 protegió correctamente el veredicto** (no se contó
   evidencia térmicamente inválida) y el Anexo 9 quedó **confirmado por medición**
   (t90 DIST ≈ 100–120 s < 200 s).
5. **Integridad read-only:** hashes post-run idénticos a la auditoría pre-run
   (governor `1aa8aa85…`, app_vulkan `51d814c5…`, analyze `28fab2cb…`, telemetria
   `922c429b…`, run_all `b51e5965…`); `power1_cap` 35 W y kalm intactos. La única
   diferencia pre↔post de S1 es el **marcador activo `*` del SCLK** (nivel 0 → 2) por
   enfriamiento al momento del snapshot — tabla DPM/límites intactos (explicado y
   aceptado). T=9.153 vs congelado 9.168 (0.16 % inter-sesión) aceptado.

**NO sólido / limitaciones (debe quedar escrito):**
- **R1–R6 carecen de muestra completa** (3+3 en vez de 6+6). Nada de S1 se declara
  PASS ni se usa como veredicto del EXP-F4-A.
- **R2 (overshoot) y R6 (Δ vs s\*=0.75)** muestran en S1 valores que **no cumplirían
  los literales** aun completando la muestra con un S2 análogo: overshoot de frames
  sobre T ≈ 67 % en settle y asentamiento a 0.87 (un paso sobre s\*). Si el S2
  hipotético concordara, el literal global sería `INCONCLUSO`/`FALSADO` por R2/R6.
- **Causa raíz de la parada = entorno, no protocolo:** la presencia de clientes de
  escritorio con acceso a la GPU discreta (Xwayland sobre `card1` y el proceso
  `gpu-process` de ChatGPT sobre `renderD129`) mantiene `gpu_busy=100 %` permanente
  desde las ~03:45 hasta la actualidad y hace inalcanzable la condición `SCLK nv0 ∧
  P<4 W`. Cualquier réplica de este experimento requeriría un **entorno sin clientes
  de la dGPU** (incluye el logger `micro12` como testigo: es read-only y NO causa la
  carga; solo documenta).

**Veredicto global del EXP-F4-A v2.3: `INCONCLUSO` (muestra incompleta) — nunca
SUPPORTED.** R1–R6 no evaluables (n=6 no alcanzado); R7 `INCONCLUSIVE / NOT FOR
VERDICT` por opción 3 y por confound §6.3; F1–F6 no computados (requieren `final()`
con ambas sesiones). Se detiene aquí; no se ejecuta nada adicional.

---

## Ficheros de referencia

- `results/v23/session1/` — Fase 1 + Phase 2 completos (8 trials) + `metrics.json`.
- `results/v23/session2/` — pre_flight, 10 bloques Fase 1 (p1/p2), `cooldown1.tsv`,
  `fase2/omissions.json=[]` (la parada fue pre-trials, no omisión térmica).
- `results/logs/session{1,2}-v23*.log` + `v23.done` (rc=9).
- Evidencia independiente: `/tmp/opencode/micro12/vkmark30-telemetry.csv`.
- Análisis de ventanas: `/tmp/opencode/marcar_ventanas.py` (read-only).