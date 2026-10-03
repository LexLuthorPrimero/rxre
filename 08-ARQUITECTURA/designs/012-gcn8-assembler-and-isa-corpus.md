# 012 — Bloque D: ensamblador GCN8 y corpus ISA GFX8

> Iteración 1 de la misión de preparación del camino ejecutable.
> Fecha 2026-09-29 · host Nobara 44 · kernel `7.1.3-200.nobara.fc44.x86_64`
> Clasificación: `READ_ONLY/EVIDENCE` + `STATIC_IMPLEMENTATION` (nada construido)

---

## 1. Resultado

```
AS_PATH_EXISTS              = PROVEN          llvm-mc 22.1.8, target amdgcn
AS_DETERMINISTIC            = PROVEN          dos ensamblados, sha256 idéntico
AS_TARGET_ENFORCED          = REFUTED         el triple NO limita la ISA
ISA_SPEC_GFX8_DOCUMENT      = NOT_AVAILABLE   (sin cambio)
ISA_REGISTERS_GFX8_IN_CORPUS= PROVEN          3 cabeceras, 1448 defines
GATE_ALTERNATIVE_AVAILABLE  = PROVEN          corpus como filtro por opcode
```

La ruta de ensamblado **existe y es reproducible**. Lo que **no** existe es la
garantía de que lo ensamblado sea GFX8. Esa garantía hay que construirla con otra
herramienta, y hay una candidata mejor que el propio triple.

---

## 2. Qué se comprobó y cómo

Todo se verificó **ejecutando y leyendo el código de retorno**, no infiriendo del
nombre. Esta es la disciplina del proyecto: un nombre no es una medición.

### 2.1 `clang` NO tiene target AMDGPU

```
$ clang -target gfx803 -c t.s -o /dev/null
clang -cc1as: error: unknown target triple 'gfx803'        rc=1
$ clang -target gfx900   ... unknown target triple          rc=1
$ clang -target gfx1103  ... unknown target triple          rc=1
$ clang --version
clang version 22.1.8 (Fedora 22.1.8-4.fc44)
```

El clang instalado no puede ensamblar GCN por la vía del driver.

### 2.2 `llvm-mc` SÍ tiene target amdgcn

```
$ llvm-mc --version | grep -A2 "Registered Targets"
  amdgcn      - AMD GCN GPUs

$ llvm-mc -triple=amdgcn-amdg-amdhsa-gfx803 t.s -filetype=obj   rc=0
$ llvm-mc -triple=amdgcn-amdg-amdhsa-gfx900 t.s -filetype=obj   rc=0
$ llvm-mc -triple=amdgcn-amdg-amdhsa-gfx1103 t.s -filetype=obj  rc=0
```

El objeto resultante es real: `.text` de 4 bytes, símbolo `probe_end` definido en
offset 0, sección `PROGBITS AX`.

### 2.3 Determinismo

```
$ llvm-mc ... gfx803 -filetype=obj -o d1.o ; llvm-mc ... -o d2.o ; cmp d1.o d2.o
  IDENTICOS   sha256 413249811cfd7d2f…
```

Dos ensamblados del mismo fuente son byte a byte idénticos. La ruta es
reproducible en el sentido fuerte.

### 2.4 Los bytes son los esperados y se pueden desensamblar

Fuente mínimo, una instrucción:

```asm
	.text
	.globl probe_end
probe_end:
	s_endpgm
```

```
$ llvm-mc --show-encoding -triple=amdgcn-amdg-amdhsa-gfx803
"amdgcn-amdg-amdhsa-gfx803-gfx000"
[0x00,0x00,0x81,0xbf]
```

Extraído del `.text` del objeto: `00 00 81 bf`, dword little-endian `0xBF810000`.
**Fuente → ensamblado → objeto → extracción de bytes → desensamblado** es un ciclo
cerrado y verificable.

---

## 3. El hallazgo negativo que importa

El triple **no** restringe el conjunto de instrucciones. En la misma instalación:

```
s_endpgm                        gfx803 = 000081bf   gfx900 = 000081bf   gfx1103 = 000081bf
v_mov_b32_e64 v0, s0            los tres idénticos
s_waitcnt vmcnt(0)              los tres idénticos

v_cmp_gt_f32_e64 vcc,   v0, v1  gfx803 = 6a 00 08 d0 …   gfx900 = igual   gfx1103 = igual
v_cmp_gt_f32_e64 s[0:1], v0, v1  gfx803 = 00 00 08 d0 …   gfx900 = igual   gfx1103 = igual
```

La última fila es la decisive. `vcc` es la grafía de GFX8; `s[0:1]` la de GFX11.
**El ensamblador acepta las dos en las tres CPU**, y produce bytes distintos para
cada una sin que el target rechace ninguna.

```
ensamblador existe
        ≠
ensamblador limita la ISA al target
        PROVEN           la primera
        REFUTADO         la segunda
```

Consecuencia operativa: `llvm-mc -triple=…-gfx803` **no** es un filtro de
compatibilidad GFX8. Es un ensamblador GCN que acepta sintaxis antigua. Un
programa podría ensamblarse sin error y usar una instrucción que Polaris12 no
tiene.

**Esto es un `LIMITATION`, no un `BLOCKER`.** El camino sigue siendo utilizable;
lo que falta es el filtro, y hay uno mejor disponible.

---

## 4. El filtro alternativo: el corpus GFX8

El repositorio contiene el enum de registros de GFX8, generado desde
`asic_reg`/ACD:

```
RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gca/
  gfx_8_0_enum.h       376 576 B   1448 defines
  gfx_8_0_sh_mask.h  1 136 970 B
  gfx_8_0_d.h          244 444 B
  (y también gfx_6_0, gfx_7_0, gfx_7_2, gfx_8_1)

sha256(gfx_8_0_enum.h) = fa6b8ff974fccdd54aa0e1b6a6430508…
```

Cobertura para la ruta de un kernel compute mínimo:

```
VOP1                5 defines
VOP2                5
VOP3               11
S_ENDPGM            2
S_LOAD_DWORD        5
S_STORE_DWORD       3
FLAT               45
```

Ejemplo de anclaje, desde el propio corpus:

```c
/* gfx_8_0_enum.h */
#define SQ_S_ENDPGM   0x1
#define SQ_S_SLEEP    0xe
```

El opcode de `SQ_S_ENDPGM` es `0x1` en el campo SGPR de GFX8. Es el mismo hecho
que la codificación `0xBF810000` de la instrucción completa, visto desde el otro
lado: el campo opcode corroborado por el registro de GFX8, el resto de la
codificación corroborado por el round-trip con LLVM.

### 4.1 Matriz de las dos puertas

| puerta | qué garantiza | estado |
|---|---|---|
| triple `gfx803` de `llvm-mc` | nada sobre ISA | `REFUTADO` |
| `gfx_8_0_enum.h` del corpus | opcode y campos de registro de GFX8 | `PROVEN` |
| documento ISA GFX8 | semántica de instrucción y de campo | `NOT_AVAILABLE` |

Las dos primeras se complementan: LLVM da la codificación de la instrucción
completa, el corpus da el campo de opcode registrado para GFX8. Juntas permiten
un filtro **mejor** que el triple, porque está atado a la definición real de
GFX8 y no a la tabla de CPUs de LLVM.

### 4.2 Corrección de un veredicto anterior

Rondas previas cerraron:

```
ISA GFX8 publicada = NOT_AVAILABLE
```

**Ese veredicto sigue siendo correcto** para el documento ISA: el árbol del
kernel no lo trae, y `03-EXPERIMENTOS/` tampoco. Lo que cambió es que la
afirmación podría leerse como "no hay nada de GFX8 en el corpus", y eso **era
falso**: hay 1,76 MB de definiciones de registro GFX8. La distinción correcta es:

```
documento ISA GFX8 (semántica)          NOT_AVAILABLE
definiciones de registro GFX8 (códigos)  PROVEN, en el corpus
```

Ambas cosas se necesitan y son de naturalezas distintas.

---

## 5. Estado de las ramas de la misión

| rama | resultado de esta iteración |
|---|---|
| A · Fence | no tocado; `P-8` sigue cerrado, no se re-audita |
| B · Memory/GTT | no tocado; ya hay `FASE-G-MEMORY-VRAM-GTT-DESIGN.md` (conceptual, no ejecutado) |
| C · GPUVM | no tocado |
| **D · GCN8** | **este documento** |
| E · PM4 | no tocado; `PACKET3_*` viene del driver, no de `gfx_8_0_enum.h` |
| F..L | no tocados |

---

## 6. Lo que falta para cerrar D

```
FALTA 1  un programa GCN8 mínimo con efecto observable en la GPU
         (no solo una instrucción que termina el shader)
         → requiere: elegir la instrucción, y runtime para verificarla

FALTA 2  el filtro por opcode aplicado de forma reproducible
         → MECANISMO CONCRETO, no bloqueado:
            extraer los opcodes de gfx_8_0_enum.h
            y confrontarlos con los que emite llvm-mc --show-encoding

FALTA 3  confirmar que Polaris12 corresponde al target gfx803
         → NO_DETERMINED localmente. La tabla de targets de LLVM es una
           fuente EXTERNAL, y el corpus no liga CHIP_POLARIS12 a un
           nombre de target de LLVM. Es el mismo tipo de hueco que
           POLARIS12→GFX8.
```

`FALTA 2` es trabajo estático y se puede hacer sin runtime. `FALTA 1` y `FALTA 3`
no.

---

## 7. Divergencia con otra sesión: `CONTRADICTION`

Otra línea de trabajo (`04-IMPLEMENTACION/rx550-driver/target_match.h`) sostiene:

> `/usr/share/hwdata/pci.ids` lista bajo el único device ID 0x699F al menos cinco
> tableros distintos (1028:1720, 1458:22f3, 148c:2380, 17aa:5069, 1da2:e367).
> El device ID NO identifica la tarjeta.

**Refutado contra el fichero.**

```
$ grep -c 699F /usr/share/hwdata/pci.ids
0
```

`0x699F` **no aparece en ninguna posición** del único `pci.ids` del sistema
(`/usr/share/hwdata/pci.ids`, 1 653 928 B, sha256 `171941ee30cde6a62…`). No hay
entrada de device bajo la que colgar subentradas. Además, dos de los cinco
subdevice citados (`22f3`, `5069`) tampoco existen en el fichero.

La sección AMD del fichero sí contiene los otros IDs de Polaris12:

```
6980  Polaris12
6981  Lexa XT [Radeon PRO WX 3200]
6985  Lexa XT [Radeon PRO WX 3100]
6986  Polaris12
6987  Lexa [Radeon 540X/550X/630 / RX 640 / E9171 MCM]
```

Ambas evidencias se preservan. No se modifica el fichero de la otra sesión.

### 7.1 Lo que sí es correcto de la otra sesión, y se incorpora

Las afirmaciones sobre la **API PCI** son correctas y se verificaron contra el
corpus 7.1.3 completo, no contra el `kernel-devel` podado:

```c
/* drivers/pci/pci.h:459-469 */
static inline const struct pci_device_id *
pci_match_one_device(const struct pci_device_id *id, const struct pci_dev *dev)
{
	if ((id->vendor  == PCI_ANY_ID || id->vendor  == dev->vendor) &&
	    (id->device  == PCI_ANY_ID || id->device  == dev->device) &&
	    (id->subvendor == PCI_ANY_ID || id->subvendor == dev->subsystem_vendor) &&
	    (id->subdevice == PCI_ANY_ID || id->subdevice == dev->subsystem_device) &&
	    !((id->class ^ dev->class) & id->class_mask))
		return id;
	return NULL;
}
```

Tres consecuencias, todas `PROVEN`:

1. El core **sí** compara subvendor y subdevice. Ponerlos en la `id_table` no es
   inerte, mecánicamente.
2. `class_mask == 0` no impone clase.
3. **La revisión no participa en el match.** `struct pci_device_id`
   (`include/linux/mod_devicetable.h:44-50`) no tiene campo de revisión. Si la
   revisión importa, hay que comprobarla en `probe()`.

Y el punto de llamada, que confirma que `probe` sólo se invoca si hubo match:

```c
/* drivers/pci/pci-driver.c:453-455 */
id = pci_match_device(drv, pci_dev);
if (id)
	error = pci_call_probe(drv, pci_dev, id);
```

Esto **corrige una limitación registrada en el componente 3**. Ahí se dejó escrito
que la semántica del core no era verificable. Ahora sí lo es, y el resultado es
favorable al diseño que ya se había elegido:

```
$ grep -n driver_data drivers/pci/pci-driver.c drivers/base/dd.c
  (todas las coincidencias son de pci_device_id.driver_data, NO de dev->driver_data)
```

El core **no toca** `dev->driver_data`. No lo pone a NULL antes de `probe()` y no
lo limpia al desenlazar. El invariante `BEFORE_PROBE drvdata = NULL` **no** es
una garantía del core: es responsabilidad del driver. La decisión de diseño de no
depender de él queda ahora respaldada por evidencia y no sólo por prudencia.
