# Cierre Formal: Compresor/Descompresor BC3/DXT5 para RX 550

**Fecha de cierre**: $(date +%Y-%m-%d)
**Tag**: v1.0-fase2-completa
**Estado**: COMPLETO con evidencia de hardware

## Resumen ejecutivo

El proyecto implementó un compresor BC3/DXT5 en CPU (Fase 1) y un descompresor como compute shader Vulkan (Fase 2), ambos ejecutándose en hardware real (AMD Radeon RX 550, Polaris 12).

**Resultado principal**: El shader ejecutó en la RX 550 y produjo resultados byte-idénticos al decodificador de referencia (0/4096 discrepancias, 3 corridas reproducibles).

## Evidencia completa

### Fase 1: Compresor (CPU)
- **Estado**: COMPLETA
- **Tests**: 26/26 pasando
- **PSNR**: 28.78/19.59/13.65/10.90 dB (reference/smooth/noise/adversarial)
- **Throughput**: 77.3 MB/s (C), 79.9 MB/s (AVX2), speedup 1.03×
- **Conformidad**: Especificación Microsoft D3D9 (AD-11, redondeo +3/+2)
- **Commits clave**: f870e8e (AD-10), ec847d7 (AD-11), 44bc133 (D19a)

### Fase 2: Descompresor (GPU)
- **Estado**: COMPLETA
- **Agreement test**: 0/4096 discrepancias (3 corridas idénticas)
- **GPU**: AMD Radeon RX 550 (PCI 1002:699f, Polaris 12)
- **Driver**: RADV POLARIS12
- **Bugs corregidos**: 3 (índice de color, push constants, dispatch calculation)
- **Control negativo**: Shader roto da 894/4096 discrepancias (test discrimina)
- **Commits clave**: edd434b (agreement test), 7ed1eca (documentación)

## Decisiones arquitectónicas clave

- **AD-10**: RX550_ALPHA_INSET_STEPS=0 (2.8× más rápido, mismo PSNR)
- **AD-11**: Redondeo +3/+2 según especificación Microsoft D3D9
- **AD-13**: Fase 2 completa con evidencia de ejecución en hardware
- **D19a**: Convención a0=max, a1=min según spec BC3

## Limitaciones abiertas (documentadas, no bloqueantes)

| Limitación | Estado | Impacto |
|---|---|---|
| Sampler hardware (AD-12) | NOT_DETERMINED | Requiere Fase 3 (pipeline gráfico) |
| Esquema SPIR-V | NOT_AVAILABLE | Falta spirv-val |
| Corpus sintético | 64 bloques | AD-10 podría no sobrevivir a texturas reales |
| Throughput GPU | sin medir | Un dispatch no es benchmark |

## Lecciones aprendidas

1. **Validar antes de comparar**: Sin validación previa, ejecuciones afortunadas parecen éxitos
2. **Un test que pasa una vez es PASS; uno reproducible 3 veces es evidencia**
3. **Validadores que modelan código no validan el código**: shader_vs_c no detectó 3 bugs reales
4. **Especificación vs implementación**: bcdec diverge de la spec Microsoft en 82.9% de casos
5. **Control negativo obligatorio**: Un test que no falla cuando debe, no prueba nada

## Próximos pasos (proyectos separados)

**Fase 3**: Integración con pipeline gráfico (resuelve AD-12)
**Fase 4**: Driver exclusivo en assembler GCN/GFX8 (proyecto nuevo)

## Archivos clave

- `CIERRE_PROYECTO.md`: Este documento
- `PROYECTO_STATUS.md`: Estado detallado por fase
- `02-ARQUITECTURA/DECISIONS.md`: Registro completo de decisiones
- `04-IMPLEMENTACION/compressor/`: Compresor BC3 (Fase 1)
- `04-IMPLEMENTACION/decompressor/`: Descompresor en GPU (Fase 2)

---

**Proyecto cerrado formalmente. Código funcional, testeado, y ejecutado en hardware real.**
