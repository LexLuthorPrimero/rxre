# H12-2 — Registro documental Wayland/xdg-shell/Vulkan WSI

**Estado:** reconciliación documental de r1/r2/r3 completada; **no autoriza una nueva ejecución**.
**Alcance:** únicamente H12-2. No es una campaña H12, no es un benchmark y no modifica código ni configuración del sistema.

## Fuente canónica

El informe completo, con pregunta, estado anterior, fuente, URL, evidencia exacta, interpretación, límites y estado final por hallazgo, está en:

- `01-AUDITORIA/FASE-H12-2-WSI-DOCUMENTATION/H12-2-XDG-SHELL-VULKAN-WSI-EVIDENCE.md`

## Resultado breve

- El XML local es `wayland-protocols` 1.49, `stable/xdg-shell/xdg-shell.xml`, con interfaces v7; el contenido coincide con el tag oficial 1.49.
- H12-1 source-level hace bind de `xdg_wm_base` en versión 1. La versión global del compositor no está serializada en r3.
- `xdg_toplevel.state=4` significa `activated` en esa versión exacta. No prueba keyboard/pointer focus, resize, maximización, fullscreen ni error.
- El serial 12837 fue observado después del primer `vkQueuePresentKHR`, con `640×360` y `states=[4]`. La regla absoluta «configure post-present = conflicto» es demasiado fuerte y queda refutada como regla de protocolo; la causa exacta y la continuación runtime quedan desconocidas.
- En Wayland Vulkan WSI, la implementación de `vkQueuePresentKHR` emite
  `wl_surface.attach`, damage y `commit` para la imagen presentable. El commit
  xdg inicial es previo y separado; después de que WSI/presentation comenzó, la
  aplicación no debe duplicar el commit del buffer presentable.
- `VK_SUBOPTIMAL_KHR` permite decidir si se continúa o se recrea; `VK_ERROR_OUT_OF_DATE_KHR` requiere consultar nuevas capacidades y recrear si se quiere continuar. r3 no alcanzó a probar la compatibilidad posterior.
- H12-2 confirma una capa parcial de capability audit, pero no cierra la causalidad H12 (`GPU completion` vs `VSync/WSI`).

## Artefactos preservados por referencia

Los artefactos originales están fuera del árbol y sus hashes están en el informe:

- r1: `/tmp/opencode/h12-2-smoke-20260924-rx550.jsonl`
- r2: `/tmp/opencode/h12-2-smoke-20260924-rx550-r2.jsonl`
- r3: `/tmp/opencode/h12-2-smoke-20260924-rx550-r3.jsonl`

r3 conserva la clasificación histórica `POST_PRESENT_CONFIGURE_UNCLASSIFIED` y el cleanup `COMPLETED`. El source working tree contiene un borrador posterior de `POST_PRESENT_STATE_ONLY_CONFIGURE`; ese borrador no se considera evidencia runtime de r3. En esta fase no se editó deliberadamente `h12_probe.c`; cualquier cambio de mtime/hash del working tree queda fuera de la provenance de r3.

## Regla de seguridad documental

No ejecutar H12, H12-1, r4 o una campaña nueva hasta que:

1. se apruebe el informe y la taxonomía de `state=4`;
2. se decida explícitamente la política para configures post-present;
3. se registre la versión/hash de protocolo y la provenance del binario;
4. exista autorización separada para cualquier nueva ejecución.

No se usan `wl_surface.frame`, `first pixel`, `vblank`, `display latency`, `Present-ID2`, present timing o `Present-Wait2` como sustitutos de telemetría que no existe.
