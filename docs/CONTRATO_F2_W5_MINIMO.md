# MATRICES F2 / W5 — CONTRATOS DE AUTORIZACIÓN MINIMA
# Estado: READ-ONLY / NO EJECUCIÓN PRIVILEGIADA / NO MODIFICACIÓN
# Evidencia: BLOQUE 0 (inspección real de .rxre/, /proc/iomem, /dev/mem, core/fuego.py)

---

## MATRIZ F2 — SNAPSHOT DE GPU

| Afirmación sin resolver | Evidencia faltante | Procedimiento exacto | Privilegio requerido | Riesgo | Resultado discriminante | Alternativa sin privilegios | Clasificación |
|---|---|---|---|---|---|---|---|
| F2: revertir() restaura registros GPU desde respaldo real | `.rxre/gpu0/original/` es archivo vacío (0 bytes), no directorio ni `.bin`; `revertir()` requiere `original` como archivo fuente (core/fuego.py:108-114) | 1. `sudo python scripts/crear_snapshot_gpu.py` (o manual: leer `/dev/mem` base MMIO -> `.rxre/gpu0/original/register_0.bin` + `metadata.json`) | **Root** (`/dev/mem` es `crw-r----- root kmem`; lectura MMIO requiere acceso a `/dev/mem`) | Bajo si solo lectura MMIO de 4096 bytes; medio si escritura en `.rxre/`; 0 si solo crea archivo pequeño en `.rxre/` | `register_0.bin` > 0 bytes + hash SHA-256 + `revertir("gpu0")` retorna `ok` | Verificar que `.rxre/gpu0/original` existe (ya existe, vacío); documentar que `revertir()` fallaría porque copia archivo vacío; usar `sysfs` (`/sys/class/drm/card1/`) para confirmar GPU sin root (ya hecho) | **REQUIERE ROOT ACOTADO** |

### Matriz F2 — detalle de procedimiento

Comando candidato (NO EJECUTADO — requiere autorización explícita de Lucas):
```bash
sudo python scripts/crear_snapshot_gpu.py
```
Salida esperada: `.rxre/gpu0/original/register_0.bin` (4096 bytes, hash 64 hex), `metadata.json`.
Condición de éxito: archivo `.bin` > 0; `revertir("gpu0")` copia a `restaurado`; hash consistente.
Condición de aborto: fallo de lectura `/dev/mem`; región MMIO no detectada; error de permiso.
Impacto: solo lectura de registros MMIO de GPU (no modifica GPU ni kernel).

### Fórmula de verificación sin root (ya hecha, CONFIRMADA)
- `.rxre/gpu0/` existe (directorio)
- `.rxre/gpu0/original` existe (archivo vacío, no `.bin`)
- `core/fuego.py` `revertir()` requiere `original` como archivo fuente
- `revertir()` no pasa sin archivo válido
→ **F2 PARTIAL confirmado, no inventado como VERIFIED**.

---

## MATRIZ W5 — ACCESO MMIO REAL

| Afirmación sin resolver | Evidencia faltante | Procedimiento exacto | Privilegio requerido | Riesgo | Resultado discriminante | Alternativa sin privilegios | Clasificación |
|---|---|---|---|---|---|---|---|
| W5: lecture MMIO de GPU desde `/dev/mem` | `/proc/iomem` NO muestra región `amdgpu`; `/sys/class/drm/card1/` sí existe (8 entradas); `/dev/mem` es `640 root kmem`; lectura sin root falla (`PermissionError`) | Leer `/dev/mem` en offset de base MMIO detectado por `/proc/iomem` (o `sysfs/drm`) | **Root** (`/dev/mem` 640 `root kmem`); lectura MMIO requiere `kmem` o `root` | Bajo: lectura de 4096 bytes de registro de control; medio: si se interpreta como escritura (no se haría) | `mmap.mmap` sobre `/dev/mem` en offset detectado; lectura de 4 bytes retorna `int`; `verify_integrity` del registro | Leer `/sys/class/drm/card1/` (EDID, modos, device) confirma GPU; `/proc/iomem` confirma ausencia de región `amdgpu` en este hardware (Intel integrado); `lspci` confirma PCIe | **REQUIERE ROOT ACOTADO** (para acceso `/dev/mem`) |

### Matriz W5 — detalle de procedimiento

Comando candidato (NO EJECUTADO — requiere autorización explícita de Lucas):
```bash
python3 << 'PY'
# Solo lectura de 4096 bytes en offset de base MMIO (detectado por /proc/iomem o sysfs)
import mmap, struct, os
with open("/dev/mem", "rb") as f:
    # offset = base de región GPU (requiere detectar primero; hoy /proc/iomem no muestra amdgpu)
    mm = mmap.mmap(f.fileno(), 4096, offset=0)  # ejemplo; base real requiere detección
    val = struct.unpack("<I", mm.read(4))[0]
    mm.close()
print("MMIO leído:", hex(val))
PY
```
Nota: `/proc/iomem` en este hardware no muestra `amdgpu`; GPU es Intel integrado (`lspci` muestra Host bridge, no AMD). Esto explica por qué `amdgpu` no aparece. El acceso a `/dev/mem` aún requeriría root, pero la región específica podría ser distinta.
Condición de éxito: lectura de `/dev/mem` sin `PermissionError`; valor de registro legible.
Condición de aborto: `PermissionError` (sin root); región no detectada; hardware no expone MMIO accesible.
Impacto: solo lectura de registros; no modificación de GPU, kernel, ni `/dev/mem`.

### Fórmula de verificación sin root (ya hecha, CONFIRMADA)
- `ls /sys/class/drm/card1/` → 8 entradas (GPU confirmada, acceso sin root posible)
- `lspci | grep -i vga` → no muestra AMD (Intel integrado)
- `/proc/iomem` → sin `amdgpu` (confirma que no es AMD en este host)
- `/dev/mem` → `PermissionError` sin root (confirma que lectura requiere root)
→ **W5 PARTIAL confirmado con gap exacto**: GPU existe pero acceso MMIO requiere root; además, hardware es Intel, no AMD `amdgpu`.

---

## RECOMENDACIÓN ÚNICA — PRÓXIMO MOVIMIENTO

**Seleccionado: F2 (snapshot) antes que W5 (MMIO)**.

Motivo (evidencia):
1. F2 requiere solo crear un archivo pequeño (`.rxre/gpu0/original/register_0.bin`) en `.rxre/`; no requiere interpretar registros GPU. El riesgo es mínimo (escritura en directorio del proyecto, no en `/dev/mem`).
2. F2 usa `revertir()` que ya existe (`core/fuego.py`); el contrato es claro (copiar `original` → `restaurado`).
3. W5 requiere acceso a `/dev/mem` que es más sensible (registro de hardware); aunque lectura es segura, requiere root y la interpretación de registros Intel (no AMD) es más incierta.
4. Ambos requieren autorización de Lucas. F2 es más simple de autorizar porque su efecto es esencialmente un archivo de datos.

Comando exacto para autorización (NO EJECUTADO):
```bash
# Autorizar F2: crear snapshot de registros GPU (solo lectura /dev/mem, escribir en .rxre/)
sudo python scripts/crear_snapshot_gpu.py
# Si falla por región MMIO no detectada (Intel, no AMD): documentar como PARTIAL definitivo
# Si pasa: actualizar claims.csv F2 → VERIFIED; luego opcionalmente W5
```

Alternativa sin privilegios (ya verificada, confirma PARTIAL):
```bash
# Verificar contrato F2 sin root
ls .rxre/gpu0/  # directorio existe
ls .rxre/gpu0/original  # archivo vacío — confirma que snapshot NO está
python -c "from rxre.core.fuego import revertir; revertir('gpu0')"  # lanza FileNotFoundError (confirmado)
```

---

## CONDICIONES DE CIERRE DE ESTA MISIÓN (sin invento)
- No se ejecutaron comandos privilegiados.
- No se modificaron archivos del proyecto (solo se creó este documento de contrato).
- No se alteraron `.rxre/` (solo inspección; `.rxre/gpu0/original` confirmado vacío).
- No se instalaron herramientas.
- No se crearon commits, ramas ni clones.
- No se alteraron stashes ni remote `legacy`.
- Estado: 52 VERIFIED, 2 PARTIAL (F2, W5), 2 DUPLICATE (F3, F4), 0 HIPOTESIS.
- Siguiente paso: decisión de Lucas sobre `sudo python scripts/crear_snapshot_gpu.py` para F2.
