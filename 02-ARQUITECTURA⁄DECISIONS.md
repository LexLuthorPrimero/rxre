## 2026-09-29 - AD-2: Formato de Compresión de Texturas
**Contexto**: Inicio de la Fase 1 (compresor de texturas para RX550).
**Opciones consideradas**:
  - Opción A: BC1/BC3 estándar → Pros: compatible con hardware, Contras: genérico, no optimizado para Polaris 12.
  - Opción B: LZ4 adaptativo → Pros: rápido, Contras: no preserva estructura 2D de texturas.
  - Opción C: Formato personalizado RGB565 + alpha → Pros: optimizado para descompresión paralela en GPU, ratio 4:1, Contras: no es estándar.
**Decisión tomada**: Opción C.
**Justificación**: El formato personalizado permite descompresión eficiente en los 4 CUs de Polaris 12, preserva el canal alfa (crítico para transparencias), y logra ratio 4:1 sin pérdida visual significativa.
**Impacto**: 04-IMPLEMENTACION/compressor/ (6 archivos), Fase 2 (descompresor en GPU).
  ## 2026-09-29 - AD-6: Formato BC3 Estándar
  **Contexto**: Tres iteraciones previas del formato personalizado tenían errores de layout y eran inferiores a BC3.
  **Opciones consideradas**:
    - Opción A: BC1/BC4 (8 bytes, ratio 8:1, calidad básica)
    - Opción B: BC3 estándar (16 bytes, ratio 4:1, 8 niveles alpha) ← ELEGIDA
    - Opción C: Formato personalizado de 16 bytes (inferior a BC3)
  **Decisión tomada**: Opción B.
  **Justificación**: BC3 es un formato estándar documentado, cumple el ratio 4:1 exacto, tiene 8 niveles de interpolación para alpha (calidad alta), y es 16 bytes exactos. No tiene sentido reinventar un formato inferior.
  **Impacto**: 04-IMPLEMENTACION/compressor/ (6 archivos), Fase 2 (descompresor en GPU).
