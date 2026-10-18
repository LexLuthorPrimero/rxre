# CONTRATO CAUSAL — INVESTIGACIÓN INVERSA (INSPECCIÓN REAL, SIN PRIVILEGIOS)
# Estado: READ-ONLY / NO PRIVILEGIO / SIN EDITAR PROYECTO (excepto evidencia de contrato)

## Afirmación concreta (PROVEN — evidencia directa de archivo)
El archivo amdgpu.ko (hash 53f55bd2..., 36MB) en el repositorio contiene funciones exportadas reales
observadas con rizin (iI / afl): amdgpu_gfx_enable_kcq, amdgpu_sdma_get_shared_ring,
dpp401_read_state, smu_get_voltage_dependency_table_ppt_v1, generic_reg_get6, dml21_create_copy.
Esto confirma que es un driver AMD (GFX8 / Polaris) y no un archivo vacío o simulado.

## Hipótesis rival (NOT_DETERMINED — requiere evidencia adicional)
Los nombres de funciones podrían ser heredados de una biblioteca base AMD o de un módulo
compartido, no necesariamente exclusivo del RX 550 Polaris 12. No se confirma que estas
funciones operen sobre la GPU física sin ejecutar el módulo.

## Prueba discriminante (ejecutada, reproducible)
Comando: rizin -q -c "iI" amdgpu.ko && rizin -q -c "afl~10" amdgpu.ko
Resultado: 40+ funciones exportadas con paddr/vaddr/size, bintype ELF64, class ELF64,
compiler GCC 15.2.1, arch x86. Distingue archivo real de archivo vacío (0 funciones).

## Procedencia y transformación
Artefacto original: /home/lucas/Escritorio/rxre/amdgpu.ko (archivo físico, creado 2026-10-12 07:30)
Evidencia E2E: audit/evidence/e2e_001.json (hash, tamaño, backend rizin)
Transformación: archivo binario -> funciones observadas -> afirmación estructural -> evidencia guardada.
No hay captura MMIO física (F2 PARTIAL): el snapshot .rxre/gpu0/original es fixture de prueba
(4096 bytes deterministas, meta fixture=true), no registro de GPU.

## Limitación
Sin acceso root /dev/mem no se confirma comportamiento funcional de estas funciones
en ejecución real sobre hardware RX 550. El contrato F2 está corregido (archivo original),
pero la evidencia física de hardware sigue pendiente de autorización.
--- EXTENSIÓN RELACIÓN ESTRUCTURAL (SPEEDRUN 4) ---
Afirmación PROVEN adicional (evidencia rizin directa, sin sudo):
- Función: amdgpu_gfx_enable_kcq (vaddr 0x08b1c860, size 829 bytes)
- Exportaciones con 'gfx': 317 símbolos (rizin iE)
- .rodata real: 0x1fbbc0 bytes (sección de datos, no vacía)
- Disassemblado real en 0x00c2f350 (no 'invalid' para todo; función real)
Hipótesis rival: podría ser módulo compartido o símbolos heredados.
Prueba discriminante: contar símbolos gfx + verificar que función específica tiene código de máquina real (no solo tabla de símbolos). Resultado: PASS (317, código real confirmado).
Limitación: no confirma comportamiento dinámico ni exclusividad RX 550.
