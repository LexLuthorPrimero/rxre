# Cierre Formal: Compresor/Descompresor BC3/DXT5 para RX 550

**Fecha de cierre**: 2026-09-29
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
- **Throughput**: 82.1 / 82.2 / 78.9 / 82.7 / 85.1 MB/s (C, 5 corridas);
  83.5 / 87.4 / 88.6 / 88.5 / 85.0 MB/s (AVX2, 5 corridas)
- **Speedup C→AVX2**: **no concluyente**. El rango intra-implementación (C entre 78.9 y
  85.1; AVX2 entre 83.5 y 88.6) es del orden de la diferencia entre implementaciones. El
  ensamblador AVX2 reduce min/max, que es una fracción del trabajo; la selección de índices
  permanece en C. **No se afirma aceleración** y el benchmark de speedup no se considera
  concluyente: `NOISE` sin establecer para esta métrica.
- **Conformidad**: Especificación Microsoft D3D9 (AD-11, redondeo +3/+2)
- **Commits clave**: f870e8e (AD-10), ec847d7 (AD-11), 44bc133 (D19a)

### Fase 2: Descompresor (GPU)
- **Estado**: COMPLETA
- **Agreement test**: 0/4096 discrepancias (3 corridas idénticas)
- **GPU**: AMD Radeon RX 550 (PCI 1002:699f, Polaris 12)
- **Driver**: RADV POLARIS12
- **Bugs corregidos**: 3 (índice de color, push constants, dispatch calculation)
- **Control negativo**: Shader roto da 894/4096 discrepancias (test discrimina)
- **Commits clave**: edd434b (agreement test), 7ed1eca (documentación),
  b65636a (agreement test verificado, `DISPATCHES=4`), 5b1996a (AD-15: control negativo
  y corrección de la causal de AD-13.1)

## Decisiones arquitectónicas clave

- **AD-10**: RX550_ALPHA_INSET_STEPS=0 (2.8× más rápido, mismo PSNR)
- **AD-11**: Redondeo +3/+2 según especificación Microsoft D3D9
- **AD-13**: Fase 2 completa con evidencia de ejecución en hardware
- **D19a**: Convención a0=max, a1=min según spec BC3

## Limitaciones abiertas (documentadas, no bloqueantes)

| Limitación | Estado | Impacto |
|---|---|---|
| Sampler hardware (AD-12) | `NOT_DETERMINED` | Requiere Fase 3. Que shader y C concuerden **no** demuestra qué regla sigue el sampler del hardware: el shader no es el sampler |
| `GFX_HWIP` | `NOT_DETERMINED` | Nada de este proyecto consulta la generación gfx ni la infiere |
| Corpus sintético | 64 bloques | AD-10 (`STEPS=0`, 2.8×) se decidió sobre un corpus que no representa texturas reales; el número puede no sobrevivir |
| Rendimiento del shader | sin medir | Un dispatch de 64 bloques no es un benchmark. `NOISE` sin establecer |
| Exhaustividad | no probada | Guarda de regresión sobre hardware real, no prueba sobre todos los bloques posibles |
| Esquema SPIR-V | **VÁLIDO** | `spirv-val --target-env vulkan1.1` rc=0, SPIRV-Tools v2026.1 |

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
