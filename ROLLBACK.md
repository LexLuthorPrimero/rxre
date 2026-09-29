# Rollback y recuperación — RX 550

**Estado de esta entrega:** no se aplicaron cambios persistentes al sistema.

## 1. Alcance

La consolidación final sólo modificó el repositorio, documentación y pruebas
con archivos temporales. No se modificaron:

- `/sys` o cualquier nodo de GPU/PM/DPM;
- Mesa, LLVM, libdrm, firmware o VBIOS;
- servicios systemd, Kalm, `system-autopilot` o `irqbalance`;
- GRUB, initramfs, modprobe, udev o parámetros de kernel;
- particiones, Btrfs, SMART o archivos de almacenamiento;
- sesión Wayland, Xwayland, KWin o procesos del host.

## 2. Rollback de una sesión por proceso

Si se exportó una variable para un proceso o terminal:

1. cerrar el proceso que la heredó;
2. cerrar la shell que la exportó;
3. comprobar que no queda en el entorno de la sesión;
4. no convertir una variable por proceso en configuración global.

Las variables conocidas son `DRI_PRIME`, `VK_ICD_FILENAMES`,
`MESA_CUSTOM`, `LD_LIBRARY_PATH`, `LIBGL_DRIVERS_PATH`,
`MESA_VK_DEVICE_SELECT` y `VK_DRIVER_FILES`.

## 3. Rollback de un cambio futuro

Antes de cualquier cambio persistente se debe tener, por separado:

- hash y contenido original del archivo;
- lista exacta de archivos y servicios afectados;
- snapshot de estado RX550/PM/DRM/KWin;
- comando de restauración y verificación de solo lectura;
- TTY, recovery o consola independiente;
- responsable y ventana de autorización.

No usar este documento para justificar un cambio que no fue autorizado. No
restaurar backup histórico sobre la instalación actual: el backup contiene
Nobara 44, kernel 7.2.x, Mesa 26.2.2 y scripts de experimentación que no son
la ruta de producción de Nobara 43.

## 4. Verificación después de rollback

```bash
python3 tools/validate_rx550_final.py
systemctl is-active kalm-gpu.service kalm.service system-autopilot.timer
rpm -q mesa-dri-drivers mesa-vulkan-drivers libdrm llvm-libs linux-firmware
```

La verificación debe ser read-only. Un estado `UNKNOWN`, `NOT_AVAILABLE` o
`UNRESOLVED` no se convierte en éxito por el mero hecho de que el sistema
arranque.

## 5. Recovery no validado

C1 permanece `UNRESOLVED`: no se ejecutó, no se materializó runtime v2 y no se
validó restore. VFIO también permanece `UNRESOLVED` por la topología H81/IOMMU
y porque el host depende de la RX550 para el compositor. No iniciar ninguno de
esos flujos como parte de un rollback rutinario.
