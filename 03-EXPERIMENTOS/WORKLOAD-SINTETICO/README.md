# Workload sintético GPU (prototipo mínimo, #[HIPÓTESIS]/DISEÑO PENDIENTE)

Rama §J del MASTER-PLAN. Prototipo mínimo de un workload Vulkan **compute** para
la RX 550 (Polaris12/RADV). Pendiente de validación (NO ejecutado aún por
instrucción; NO es candidato M2 hasta pasar los gates de §J).

## Propósito de este prototipo

Evaluar (hipótesis de diseño, §J) qué patrón de carga compute puede generar
potencia sostenida y reproducible en Polaris12. NO busca "hacer consumir 35 W"
sino producir carga técnicamente representativa y parametrizable para medir
potencia/rendimiento con la telemetría del laboratorio.

## Qué hace

- Enumeración de devices Vulkan; selección **estricta** de RX 550
  (vendor=0x1002, device=0x699F); `--any-gpu` solo para desarrollo.
- Buffer SSBO de tamaño configurable (presión de VRAM/bandwidth).
- Shader compute con presión ALU/FLOP (fma/mad), acarreo de memoria (lecturas
  estridadas sobre el SSBO) y parámetros por push constant:
  `iterations` (carga ALU dentro de la invocación), `stride` (salto de memoria),
  `seed` (variabilidad determinista) y tamaño de dispatche (workgroups).
- Bucle de `--duration` segundos (por defecto 30) en cola compute.
- Salida reproducible por stdout con la config usada.

## Compilar

```bash
make
```

## Ejecución (pendiente de autorización/validación)

```bash
./main --duration 30 --workgroups 4096 --iterations 512 --stride 16 --seed 42 --vram 268435456
```

Ambiente recomendado (igual que M1/exploratorios):

```bash
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json \
MESA_VK_DEVICE_SELECT=1002:699f \
./main ...
```

La verificación de device 0x699F se hace adentro del programa (no solo por env).

## Diseño B — workload GRÁFICO (`main-graphics`)

Implementación del Diseño B (ver `DESIGN-GRAPHICS.md`): fullscreen triangle bufferless + fragment
pesado (≈4 sampleos bilineal incoherentes sobre 4×4096² RGBA8 + ~24 FMA) con overdraw (4 capas) y
blending aditivo ONE/ONE, offscreen. El contenido de las texturas se genera en HOST con la familia de
hash `hash32` y se sube con `vkCmdCopyBufferToImage` (enmienda Anexo A; sin storage images en GFX8).

```bash
make main-graphics        # el binario `main` de E-01/E-02 NO se recompila
./main-graphics [--width 1920] [--height 1080] [--layers 4] [--textures 4]
               [--tex-size 4096] [--fma-iters 4] [--seed HEX] [--seed-extra HEX]
               [--warmup 5] [--duration 20] [--any-gpu]
               [--skip-gen] [--skip-frag]    # solo depuración de faults VM
```

### Campos del runner para correlación temporal

- `start_wall_ns` / `end_wall_ns`: reloj `CLOCK_REALTIME` (ns) del inicio y fin de la ventana MEDIDA
  (tras warmup). La telemetría (`telemetria.sh`) graba cada fila con `ts` = `date +%s%N` (mismo reloj):
  correlación directa `[start_wall_ns, end_wall_ns]` ↔ filas `ts` de `telemetria.csv`.
- Otros campos de la fase medida: `frames` (warmup/measure), `fps`, `frametime_ns` (min/avg/max/p50),
  `vram` (heap/bytes de imágenes), `sample_counts_cb`.
- Criterio de validez ampliado (R-11/E-03): además de `exit 0` y fences OK, la corrida DEBE tener 0
  líneas `GPU fault|VM fault` en `journalctl` en su rango temporal.
- Códigos de aborto: 2 device lost, 3 fence timeout/hang, 4 OOM, 5 presupuesto VRAM.

## Gates §J pendientes de validar

1. Compilación limpia (verificable con `make`).
2. Selección inequívoca RX 550 `0x699f` (implementado).
3. Sin modificación de configuración permanente del sistema (no toca sysfs).
4. Sin forzar SCLK/MCLK/DPM (env temporal únicamente).
5. Sin tocar Kalm (no interactúa con kalm).
6. Sin crashes/reset/hang/OOM (por validar con telemetría + journal).
7. Temperatura estable (por validar).
8. Consumo reproducible (por validar).
9. ≥27 W sostenidos con cap=35 W (objetivo, NO garantizado).
10. Repetibilidad para A/B (por validar).