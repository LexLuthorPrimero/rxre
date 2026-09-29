# Decisions — CIERRE 2026-09-19
Registro de decisiones de la investigación (resumen final).

- DN-01..06 (Fase A, 19/09): read-only; thermal policy; ventanas estables (descartar ~0.7s+última);
  robustez VK (sin `MESA_VK_DEVICE_SELECT` numérico; usar ICD). Corridas 04-09 (iGPU Intel) invalidadas.
- DN-07 (Fase B, autorizada): único write permitido = `power1_cap`; protocolo frío con cooldown ≤50 °C,
  caps ASC 25→28→32→35, N=2, sampler 10 Hz con cap por muestra, trap de restauración. Verificado cap=35 W
  al final.
- DN-08: resultado negativo de Fase B se registra y se replantea sin volver a escribir cap hasta
  nueva autorización.
- DN-09 (EP-06, autorizado): soak a cap 25 W con condición de seguridad "display en Intel". Resultado
  negativo (sin pinzado ni a 70-71 °C). Cap restaurado 35 W, verificado.
- DN-10: kalm descartado como causa (auditoría de journal). NO tocar kalm.
- DN-11 (EP-05, autorizado, read-only): réplica línea E5 a 1080p con Mesa CUSTOM por env por proceso,
  sin tocar la Mesa del sistema; A/B CUSTOM vs STOCK con verificación de libs vía /proc maps; verificación
  de condición display. Resultado: CUSTOM no reproduce el régimen E5.
- DN-12 (CIERRE): a partir de aquí NO se ejecutan más experimentos ni se escribe en sysfs. Fase de
  consolidación documental. La Mesa CUSTOM queda como instrumento de investigación, no tuner fijo.
  El régimen histórico 17/09 (E1/E3/E5) es [NO REPRODUCIBLE] y no se convierte en especificación.
- Regla permanente: cualquier write futuro (cap/DPM/SCLK/MCLK) requiere autorización, snapshot+readback
  y restauración garantizada (ver BUILD_SPEC §17-18, §34-35).
- DN-13 (2026-09-21, autorizada): **Regla de documentación de conocimiento e investigación** (aplica desde
  ahora a todo el proyecto):
  1. Todo conocimiento técnico obtenido mediante investigación o experimentación debe quedar documentado,
     incluyendo NO SOLO los resultados y conclusiones, sino también la **metodología** utilizada para
     obtenerlos (qué quisimos saber, cómo lo investigamos, qué evidencia encontramos, cómo la evaluamos y
     por qué decidimos lo que decidimos).
  2. Si NO se conoce con certeza suficiente un aspecto técnico, NO se asume: primero se investiga con
     `websearch`/`webfetch`, priorizando documentación oficial, especificaciones Khronos/Vulkan,
     documentación y código upstream de Mesa/RADV, kernel/amdgpu y otras fuentes primarias; luego se
     registra también esa investigación y su metodología.
  3. El registro por investigación/experimento mínimo incluye: pregunta a resolver; fecha; metodología de
     búsqueda (términos, fuentes, selección/priorización, fuentes oficiales/upstream, contraste de
     afirmaciones contradictorias); fuentes con URLs y qué aportó cada una; hechos VERIFICADOS; hipótesis
     (planteadas, confirmadas, rechazadas, abiertas); metodología experimental (hardware/software, config,
     parámetros, comandos, variables medidas, control de variables, criterios de éxito/fallo/descarte);
     resultados y datos; limitaciones/errores/lo que NO puede concluirse; decisión técnica y alternativas
     descartadas.
  4. Si aparece evidencia que contradice una conclusión anterior, NO se sobrescribe silenciosamente la
     conclusión vieja: se documenta la contradicción, la nueva evidencia y por qué cambió el criterio.
  Fuente de registro de la investigación: `03-EXPERIMENTOS/WORKLOAD-SINTETICO/RESEARCH.md`.
