# 001 — Localización exacta de `amdgpu.ko`

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Ámbito**: IA-1 Ingeniero Inverso, `06-INGENIERIA-INVERSA/`
**Autorización**: lectura de `/lib/modules`, escritura en el ámbito propio. Sin sysfs, sin carga
de módulos, sin `sudo`, sin `SYSTEM_CHANGE`.

---

## 1. Kernel en ejecución

```
7.1.3-200.nobara.fc44.x86_64
```

Comando: `uname -r`

## 2. Ruta exacta

```
/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

**El fichero lleva sufijo `.zst` y está comprimido.** El comando indicado en la orden
(`find /lib/modules/$(uname -r) -name "amdgpu.ko"`) **no devuelve nada**: sin comodín no casa
con `amdgpu.ko.zst`. El comando que sí funciona:

```bash
find /lib/modules/$(uname -r) -name "amdgpu.ko*"
```

Coexiste además un módulo de otra versión en `/lib/modules/6.18.2-200.nobara.fc43.x86_64/`.
**No es el de esta máquina**: el kernel en ejecución es `7.1.3`. Cualquier análisis sobre el
6.18.2 no describe este host.

## 3. SHA256 — el identificador que deben usar IA-2 e IA-3

| Artefacto | SHA256 | Tamaño |
|---|---|---|
| `amdgpu.ko.zst` (en disco, comprimido) | `6ec8f7e7a258c520c9c8b9f4269f73d2052bcd1bdb8d178c640b9c25aa06a663` | 5 954 300 B comprimidos |
| `amdgpu-analysis/amdgpu.ko` (ELF, descomprimido) | `a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024` | **37 494 368 B** |

**El segundo es el que se analiza.** Citar el primero no basta: la compresión no es biyectiva
respecto al contenido del ELF y el hash del `.zst` no identifica el objeto de análisis.

Identificadores adicionales del mismo objeto, para que no haya ambigüedad:

| Campo | Valor |
|---|---|
| `srcversion` | `D68004925455E20A24C2B87` |
| `vermagic` | `7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload` |
| ELF BuildID | `4d5342509f84dd84f0d5d515b03eb6c7659fb492` |

Comandos:

```bash
sha256sum /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
zstd -d -c /lib/modules/$(uname -r)/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst \
  > 06-INGENIERIA-INVERSA/amdgpu-analysis/amdgpu.ko
sha256sum 06-INGENIERIA-INVERSA/amdgpu-analysis/amdgpu.ko
```

## 4. Perfil del objeto

```
ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), BuildID[sha1]=4d53...,
not stripped
```

`relocatable` y `not stripped` juntos: el objeto conserva nombres de símbolo locales y su
estructura, y no tiene direcciones absolutas porque el kernel lo reubica al cargarlo.

## 5. Referencia: la fuente C de este mismo módulo está en el repo

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu.h
```

`struct amdgpu_device` ocupa las líneas 858-1201. **Esto es la vía principal para los rounds
siguientes**: los nombres de los offsets se leen en C, no se desensamblan. Ver
`002-module-sections.md` §6 y `003-exported-symbols.md` §5.

## 6. Nota sobre la copia de trabajo

El ELF descomprimido (35,8 MiB) queda en `amdgpu-analysis/amdgpu.ko` como artefacto de trabajo,
**no commiteado**: 35,8 MiB de objeto binario no aportan nada a un repositorio de fuentes y
harían el historial inmanejable. Los 4 documentos y los `.txt` derivados sí se versionan. Si IA-2
necesita el binario, lo regenera con el comando de §3 en un minuto.

## Procedencia

Todos los valores se obtuvieron ejecutando los comandos indicados sobre
`/lib/modules/7.1.3-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst` el
2026-09-29. Ningún valor transcrito de documentación ni de memoria.
