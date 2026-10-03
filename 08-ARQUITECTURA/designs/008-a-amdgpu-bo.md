# 008-A — `struct amdgpu_bo`: definición y relación con GEM/TTM

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 14
**Tipo**: `READ_ONLY/EVIDENCE` — análisis estático. Sin hardware, sin compilación, sin ejecución.
**Árbol**: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `007`, Q-5, cerrojo ajeno.

---

## Scope

Responder una sola pregunta: **¿dónde se define realmente `struct amdgpu_bo` y cuál es su
relación demostrable con GEM/TTM en la ruta Polaris12?**

## Question

La búsqueda previa (`007` §5) la dejó como `NOT_DETERMINED` porque un `grep` sobre `amdgpu.h` no
devolvió nada. Eso fue un `OBSERVATION` mal_leída, no una ausencia.

## Evidence — la corrección

```
$ grep -n "struct amdgpu_bo {" amdgpu.h
(vacío)
$ grep -rn "struct amdgpu_bo {" *.h ../include/amdgpu/*.h
amdgpu_object.h:103:struct amdgpu_bo {
```

**El tipo existe. Mi `grep` buscó en el fichero equivocado.** `amdgpu.h` es el agregador que
incluye `amdgpu_object.h`; la definición no está en el primero.

Esto es exactamente el caso que la regla metodológica del encargo advertía: *«un grep vacío no es
una conclusión sobre upstream sin determinar primero si ese objeto pertenece a la ruta
analizada»*. Pertenece, pero a otra cabecera.

### Definición

```
amdgpu_object.h:103   struct amdgpu_bo {
amdgpu_object.h:104       u32                    preferred_domains;
amdgpu_object.h:105       u32                    allowed_domains;
amdgpu_object.h:106       struct ttm_place       placements[AMDGPU_BO_MAX_PLACEMENTS];
amdgpu_object.h:107       struct ttm_placement   placement;
amdgpu_object.h:108       struct ttm_buffer_object tbo;      <-- HEREDA DE TTM
amdgpu_object.h:109       struct ttm_bo_kmap_obj kmap;
amdgpu_object.h:110       u64                    flags;
amdgpu_object.h:112       struct amdgpu_vm_bo_base *vm_bo;
amdgpu_object.h:114       struct amdgpu_bo       *parent;
amdgpu_object.h:116   #ifdef CONFIG_MMU_NOTIFIER
amdgpu_object.h:117       struct mmu_interval_notifier notifier;
```

### Relación con TTM — demostrada, no inferida

```
amdgpu_object.h:108   struct ttm_buffer_object tbo;   primer miembro con nombre
```

El primer miembro de `struct amdgpu_bo` es `struct ttm_buffer_object tbo`, y el comentario de la
línea 104 dice `/* Protected by tbo.reserved */`. Eso es la relación de **composición**: un BO de
AMDGPU **es** un TTM BO con campos AMDGPU añadidos al principio. `to_amdgpu_bo()` es el
`container_of` que traduce una dirección de TTM a una de AMDGPU.

### Relación con GEM

```
amdgpu_gem.c:166   int amdgpu_gem_object_create(struct amdgpu_device *adev, unsigned long size, ...)
amdgpu_gem.c:191       r = amdgpu_bo_create_user(adev, &bp, &ubo);
amdgpu_gem.c:1285  r = amdgpu_gem_object_create(adev, args->size, 0, domain, flags);   (desde userspace)
```

## Trace

```
userspace (ioctl)
│
│  amdgpu_gem.c:1285   amdgpu_gem_object_create() desde el ioctl
▼
amdgpu_gem_object_create()                    [amdgpu_gem.c:166]
│
│  amdgpu_gem.c:191   amdgpu_bo_create_user()
▼
amdgpu_bo_create_user()
│
│  (crea el ttm_buffer_object embebido en amdgpu_bo)
▼
struct amdgpu_bo {                           [amdgpu_object.h:103]
  struct ttm_buffer_object tbo;              [amdgpu_object.h:108]  <-- la base es TTM
}
```

## Classification

| Elemento | Estado | Evidencia |
|---|---|---|
| `struct amdgpu_bo` existe | `PROVEN` | `amdgpu_object.h:103` |
| Está en otra cabecera, no en `amdgpu.h` | `PROVEN` | `grep -rn` sobre `*.h` |
| Es composición sobre `ttm_buffer_object` | `PROVEN` | `amdgpu_object.h:108` + comentario `:104` |
| La creación pasa por `amdgpu_bo_create_user()` | `PROVEN` | `amdgpu_gem.c:191` |
| La ruta Polaris12 usa TTM BO | `PROVEN` (por `vi.c:2109-2122` + `amdgpu_device.c:1987`, familia VI) | ver `007` §3 |
| El **ciclo de vida** completo del BO en la familia VI | `NOT_DETERMINED` | no seguido más allá de la creación |
| Si un driver propio **necesita** TTM | **`OPTIONAL`**, no `REQUIRED` | la composición demuestra cómo AMDGPU lo hace, no qué exige el hardware |

**Corrección que hay que hacer en `007`**: la línea «`struct amdgpu_bo`: `NOT_DETERMINED` (mi
grep falló)» pasa a `PROVEN`. El texto de `007` ya no es incorrecto — dice «mi grep falló» — pero la
tabla de gaps lo listaba como abierto sin resolver. Queda cerrado aquí.

## Unknowns

| # | Desconocimiento | Por qué sigue abierto |
|---|---|---|
| U-1 | Ciclo de vida del BO: eviction, pinning, `parent` | requiere seguir `amdgpu_bo.c`; fuera del alcance declarado |
| U-2 | Si `vm_bo` es obligatorio para compute | no seguido |
| U-3 | Interacción con `CONFIG_MMU_NOTIFIER` | `#ifdef`, no analizado |

## Closure criterion — cumplido

Pregunta cerrada: definición localizada, relación con TTM demostrada por el miembro, relación con
GEM demostrada por la cadena de creación, y la evidencia negativa del `grep` original explicada.

## Tooling used

`grep -n` / `grep -rn` sobre el árbol del driver. `sed -n` para extraer el cuerpo de la definición.
Sin AST: el hallazgo fue de localización, no de relaciones de tipos, y la lectura directa bastó.

---

```
STATUS: PROVEN

EVIDENCE:
amdgpu_object.h:103   struct amdgpu_bo {
amdgpu_object.h:108       struct ttm_buffer_object tbo;   /* composicion con TTM */
amdgpu_object.h:104   /* Protected by tbo.reserved */
amdgpu_gem.c:166      amdgpu_gem_object_create()
amdgpu_gem.c:191          amdgpu_bo_create_user()
amdgpu_gem.c:1285     amdgpu_gem_object_create()  (desde ioctl de userspace)

DISCRIMINANT:
cerrado — el tipo existe; el grep inicial busco en la cabecera equivocada
(amdgpu.h en vez de amdgpu_object.h). Ausencia de resultado != ausencia de tipo.

ARTIFACT:
08-ARQUITECTURA/designs/008-a-amdgpu-bo.md

RUNTIME:
NOT_RUN

MODIFICATIONS:
NONE (fichero nuevo, sin commit)

COMMIT:
NONE
```
