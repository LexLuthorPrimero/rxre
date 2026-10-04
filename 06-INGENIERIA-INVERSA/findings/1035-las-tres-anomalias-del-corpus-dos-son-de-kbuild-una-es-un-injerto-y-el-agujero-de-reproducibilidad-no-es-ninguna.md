# 1035 · Las tres anomalías del corpus: dos son de kbuild, una es un injerto, y el agujero de reproducibilidad no es ninguna de las tres

`CLASSIFICATION=CONTRADICTION_RESOLVED` · `TRACK=STATIC + TARBALL`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `TARBALL=RESEARCH/evidence/linux-7.1.3.tar.xz`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1` (este fichero)
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## Qué es esto

Tres cosas del árbol del corpus que no están en el tarball oficial y no tenían
explicación registrada. Se closes las tres por medición, contra el tarball, y se
contesta la pregunta que las hace interesantes: **si el manifiesto de hashes cubre
o no esos ficheros**.

El resultado principal es una **discrepancia de alcance**, y no es la que se
esperaba: las tres anomalías están fuera del manifiesto *y eso es correcto según el
alcance que el manifiesto declara*, mientras que **el manifiesto se deja fuera
4 de los 6 ficheros que el corpus de verdad modifica**, dos de los cuales son los
más citados del proyecto.

---

## 0 · La medición de base: corpus contra tarball, fichero a fichero

No se|CAN repeat `tar -tJf`: se descomprimió el tarball entero y se calculó el
sha256 de sus 93 609 ficheros regulares, y se calculó el sha256 de los 103 618 del
corpus. Script: `/tmp/opencode/corpus_full_diff.py`. Resultado:
`/tmp/opencode/corpus_full_diff.json`.

```
tarball  sha256 = be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc
         158 335 040 B · 99 849 miembros · 6 141 directorios · 93 609 ficheros regulares

corpus   103 618 ficheros regulares · 87 symlinks · 0 no-regulares

sólo en el corpus (EXTRA)  : 10 009 ficheros · 17 607 438 B
sólo en el oficial (FALTA) :      0 ficheros
rutas comunes              : 93 609
CONTENIDO DISTINTO         :      6 ficheros
TAMAÑO DISTINTO            :      6 ficheros  (los mismos 6)
```

**`FALTA = 0`.** El corpus es un **superconjunto estricto** del tarball: no le
falta ni un fichero de los 93 609. Eso descarta de raíz la hipótesis «el corpus
está recortado».

### Los 6 ficheros que el corpus modifica de verdad

| fichero | oficial | corpus | Δ bytes | Δ líneas |
|---|---:|---:|---:|---:|
| `drivers/gpu/drm/amd/amdgpu/amdgpu_debugfs.c` | 56 735 | 67 381 | **+10 646** | +264 / −0 |
| `drivers/gpu/drm/amd/amdgpu/amdgpu_debugfs.h` | 1 838 | 3 352 | **+1 514** | +33 / −0 |
| `drivers/gpu/drm/amd/amdgpu/amdgpu_vm.c` | 87 124 | 87 642 | +518 | |
| `drivers/gpu/drm/amd/amdgpu/amdgpu_vm_pt.c` | 26 857 | 27 774 | +917 | |
| `drivers/gpu/drm/Kconfig` | 11 484 | 11 530 | +46 | +2 / −0 |
| `drivers/gpu/drm/Makefile` | 7 687 | 7 733 | +46 | +1 / −0 |

Las cuatro primeras son instrumentación declarada del proyecto. Las dos últimas son
**las costuras del injerto**, y son exactamente las dos líneas que el enunciado de
este nodo llama «líneas de splice». Verificado por `difflib` contra el contenido
extraído del tarball:

```
drivers/gpu/drm/Kconfig     @@ -364,2 +364,4 @@
                                tristate
                           +
                           +source "drivers/gpu/drm/polaris12xl/Kconfig"

drivers/gpu/drm/Makefile    @@ -257,2 +257,3 @@
                                $(call if_changed_dep,hdrtest)
                           +obj-$(CONFIG_DRM_POLARIS12XL) += polaris12xl/
```

`Kconfig:367` y `Makefile:259` son, en el corpus, la última línea de cada fichero.
Las dos costuras son **anómalas** —el `source` va después del `endif`/`endmenu` del
menú DRM, y el `obj-` va después de las reglas `hdrtest`—, como afirma el hallazgo
1033 §R6. **Corroborado.**

### Los 10 009 ficheros añadidos, por clase

| clase | n | qué es |
|---|---:|---|
| `include/config/*` | 9 700 | salida de `make config`: un stub por `CONFIG_*` |
| kbuild host tools + generados | 210 | `scripts/`, `tools/objtool/`, `scripts/kconfig/`, `scripts/mod/`, `include/generated/*`, `kernel/*.s`, `arch/x86/{include/generated,tools,kernel}` |
| **`drivers/gpu/drm/polaris12xl/**`** | **79** | el injerto (anomalía 1) |
| `drivers/gpu/drm/amd/amdgpu/*.{o,o.cmd}` | 6 | `.o` + `.cmd` de los 3 TU instrumentados |
| raíz del árbol | 14 | 8 de las anomalías 2 y 3, más `.config`, `.config.old`, `.module-common.o`, `..module-common.o.cmd`, `.modules-only.symvers.cmd`, `modules-only.symvers` |

`9 700 + 210 + 79 + 6 + 14 = 10 009`. Cuadra exacto, no aproximado.

**El recuento de 46 ficheros del enunciado de este nodo era incorrecto: son 79.**
Descompuestos: **36 ficheros de fuente** (`Kconfig`, `Makefile`,
`SOURCE-MANIFEST.sha256`, `kernel/p12xl_main.c`, 15 `core/*.c`, 17
`include/polaris12xl/*.h`) y **43 artefactos de build** (`.o`, `.ko`, `.cmd`,
`.mod*`, `modules.order`). 79 = 36 + 43.

---

## 1 · Anomalía 1 — `drivers/gpu/drm/polaris12xl/`

### Qué es

Un **módulo kernel out-of-tree de este proyecto**, injertado en el árbol del corpus
para poder compilarse con kbuild. No es una idiosyncraticía del corpus: es un
`obj-m` más.

### De dónde viene

**La ruta `git log` no existe, y no por descuido.** Measured:

```
$ git log --diff-filter=A --format='%h %ad %s' --date=short \
    -- 'RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/polaris12xl'
(vacío)

$ git check-ignore -v RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/polaris12xl/Makefile
.gitignore:63:RESEARCH/       RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/polaris12xl/Makefile
```

`.gitignore:63` es `RESEARCH/`, línea completa. **Todo el corpus está fuera del
repositorio, así que la atribución por commit y autor es imposible por
construcción, no por negligencia.** La misma vacuidad devuelve `git log` para las
anomalías 2 y 3. Esto no es un dato sobre estas tres anomalías: es un dato sobre
**todo** `RESEARCH/`, y es la limitación de reproducibilidad de la que ya se sabe.

La procedencia real sí es recuperable, por contenido:

| | |
|---|---|
| `.ko` compilado | `polaris12xl.ko`, 723 136 B, mtime **2026-10-03 11:16:51** |
| `.config` del corpus | mtime **2026-10-03 11:14:38**, `CONFIG_DRM_POLARIS12XL=m` |
| fuentes `.c`/`.h` | mtime **2026-09-27 04:19 → 2026-09-28 01:18** |

El árbol se configuró a las 11:14:38 y el módulo se compiló a las 11:16:51, dos
minutos después. Los `.cmd` de `core/` llevan la misma marca que los `.o`.

### La cadena de custodia está intacta — con un manifiesto propio

El injerto **sí tiene registro de integridad, y no es el de amdgpu**:

```
drivers/gpu/drm/polaris12xl/SOURCE-MANIFEST.sha256   35 entradas, 3 603 B
```

Las rutas van relativas a `drivers/gpu/drm/`, no al subárbol. Verificado:

```
SOURCE-MANIFEST contra la copia de kernelbuild : ok=35  mismatch=0  missing=0
```

**35/35.** Las 43 piezas de build (`.o`, `.ko`, `.cmd`) quedan fuera, que es lo
correcto: no son fuente.

Las 35 fuentes son las mismas que hay en el árbol de preparación
`RESEARCH/polaris12xl/`, y la comparación byte a byte da:

```
34 de 36 ficheros idénticos a RESEARCH/polaris12xl/
Makefile  →  idéntico a RESEARCH/polaris12xl/Makefile.kbuild
            (sha256 53f5eb85b92e660b7c3265a616d27a91a38eec3c34f9f6274404523952e0fd62)
SOURCE-MANIFEST.sha256  →  sin contraparte en el árbol de preparación
            (se genera al instalar, no al preparar)
```

El `Makefile` de 8 927 B del árbol de preparación es el `makefile` de las dos
compilaciones (tests userspace + módulo); el de 2 078 B que hay dentro del corpus es
su fragmento kbuild, `Makefile.kbuild`. Los dos existen y son coherentes. **Nada
está huérfano.**

### `polaris12xl` NO es un nombre de ASIC

La premisa del enunciado («un nombre de ASIC que no es de la generación GFX8») es
**REFUTADA**, y el propio proyecto ya lo tenía escrito. `p12xl_asic.h:44-52`:

> *PCI identity, as a VALUE, not as a binding — These constants exist so the model
> can be \*described\*. They are NOT a pci_device_id table and there is no code path
> that registers them with the bus.*

Y la identidad del RX 550 **sí está compilada**, como valor:

```
core/p12xl_asic.c:25   .vendor = 0x1002
core/p12xl_asic.c:26   .device = 0x699f          <-- 0x699F, Polaris12
core/p12xl_part.c:23   #define P12XL_THIS_DEVICE  0x699Fu
```

`Kconfig` lo dice sin ambigüedad: *"Experimental Polaris12 learning driver (DO NOT
INSTALL)"*. **`polaris12xl` es el nombre del módulo, no del chip.** El ASIC es
`0x699F` / `CHIP_POLARIS12`, tal y como lo nombra `amdgpu_drv.c:2041`. El proyecto
no ha inventado un ASIC: ha bautizado un módulo.

### Inercia: corroborada con medida, no con comentario

`01-AUDITORIA/PATCH-RECOVERY/PATCH-SOURCES.md:191` afirma que el módulo es «inerte
por construcción: sin `pci_driver`, sin `drm_driver`, no puede enlazar ni tocar el
dispositivo», y lo usa para marcarlo **NO** usable. Recuento sobre las fuentes del
módulo (excluyendo `build/`, `tools/`, `ideas/`, `docs/`, `evidence/`):

| símbolo | apariciones |
|---|---:|
| `MODULE_DEVICE_TABLE` | **0** |
| `PCI_DEVICE_TABLE` | **0** |
| `pci_register_driver` | **0** |
| `drm_dev_register` | **0** |
| `pci_enable_device` | **0** |
| `pci_iomap` | **0** |
| `pci_request_region` | **0** |
| `ioremap` | **0** |
| `p12xl_pci_id_rx550` | 4 (1 decl, 1 def, 1 comentario, 1 test) — **0 llamadas desde `core/`** |

**Cero caminos de registro.** La inercia es estructural, no una promesa. La
afirmación del proyecto se sostiene. Y el que la.identity esté compilada no la
contradice: una constante no enlaza nada. El propio `tools/safety-audit.sh`
registró esto como **defecto D-21** y corrigió la comprobación de «no aparece
`0x699F`» a «no hay `pci_device_id` y el accessor no tiene llamadores».

**Un error de recuento, en cambio:** `PATCH-SOURCES.md:191` dice «**10 ficheros en
`core/`**». `core/` tiene **15** `.c`
(`p12xl_asic`, `evidence`, `hang`, `ih`, `ip`, `iv`, `know`, `mem`, `obs`, `part`,
`pm`, `power`, `reset`, `ring`, `sched`). REFUTED. No cambia la conclusión de la
tabla —que es **NO**—, pero es un número falso en una tabla de decisión.

### Qué lo cita

**14 ficheros, 39 ocurrencias.** Alcance de búsqueda: **3 802 ficheros /
14 983 685 232 B** leídos (árbol del proyecto excluyendo `RESEARCH/`,
`rx550-upstream-7.2.8/`, `.git/`, `__pycache__`, `.opencode`; los 21 ficheros de
>40 MB se leyeron por trozos, sin exclusión).

De las 14, **13 sólo mencionan el módulo o citan `RESEARCH/polaris12xl/…`** — el
árbol de preparación, que es donde vive el documento. Ninguna de esas 13 trata la
presencia dentro del corpus.

**Una sola** trata la presencia dentro del corpus como hecho, y lo hace
correctamente: `findings/1033 §R6`, que dice que el corpus *no es* un árbol
upstream limpio y que toda frase del proyecto sobre «el corpus» tiene que excluir
`drivers/gpu/drm/polaris12xl/`. Es exactamente la regla correcta.

### Veredicto 1

**EXPLICADA.** Injerto deliberado de un módulo propio, con dos costuras de una
línea, con manifiesto de integridad propio que verifica 35/35, con árbol de
preparación byte-idéntico, con nombre de módulo y no de ASIC, y con inercia
estructural verificada. **Ninguna afirmación del proyecto queda invalidada.** La
única corrección es el «10 ficheros en `core/`» de `PATCH-SOURCES.md:191`, que son
15. `PROVEN_ABSENT` de que nada fuera de esa tabla dependa del recuento.

---

## 2 · Anomalía 2 — `.checked-atomic-*.h`

### Qué es, y dónde

Tres ficheros **de 0 bytes** en la **raíz** del árbol del corpus — no en un
`drivers/` ni en un `include/`, que es donde los situaba el enunciado:

```
RESEARCH/kernelbuild/linux-7.1.3/.checked-atomic-arch-fallback.h    0 B  2026-09-27 03:54:50
RESEARCH/kernelbuild/linux-7.1.3/.checked-atomic-instrumented.h     0 B  2026-09-27 03:54:50
RESEARCH/kernelbuild/linux-7.1.3/.checked-atomic-long.h             0 B  2026-09-27 03:54:50
```

Más sus tres `.cmd` hermanos (`.465`, `.460`, `.420` B), que son el *build log* de
kbuild.

### De dónde viene: el `Kbuild` del tarball oficial

No es del proyecto. El productor es el **`Kbuild` de nivel superior del kernel
oficial**, y la receta exacta está dentro del propio `.cmd`:

```
savedcmd_.checked-atomic-instrumented.h := if ! command -v sha1sum >/dev/null; then
  echo "warning: cannot check the header due to sha1sum missing"; exit 0; fi;
  if [ "$(sed -n '$s:// ::p' include/linux/atomic/atomic-instrumented.h)" !=
       "$(sed '$d' include/linux/atomic/atomic-instrumented.h | sha1sum | sed 's/ .*//')" ];
  then echo "error: ... has been modified." >&2; exit 1; fi; touch $@
```

Y en el `Kbuild` del corpus, que **es el del oficial** (`Kbuild` no está entre los
6 ficheros modificados):

```
quiet_cmd_check_sha1 = CHKSHA1 $<
atomic-checks += $(addprefix $(obj)/.checked-, \
      atomic-arch-fallback.h \
      atomic-instrumented.h \
      atomic-long.h)
```

**Son las sondas de upstream que verifican que nadie editó a mano las cabeceras
atómicas.** El fichero de 0 bytes es el **exito**: la sonda corrió, comparó el
`sha1` con el pie de la propia cabecera y hizo `touch`.

### La sonda pasó — verificado

Las tres cabeceras vigiladas son **byte-idénticas** al tarball oficial:

| | oficial | corpus | idéntico |
|---|---|---|---|
| `include/linux/atomic/atomic-instrumented.h` | `6fd766b72f7a6335…` | `6fd766b72f7a6335…` | **sí** |
| `include/linux/atomic/atomic-long.h` | `5df7f4b60e3a5f10…` | `5df7f4b60e3a5f10…` | **sí** |
| `include/linux/atomic/atomic-arch-fallback.h` | `df526d6b93b043fb…` | `df526d6b93b043fb…` | **sí** |

### Ausencia en el oficial

`PROVEN_ABSENT` sobre el listado completo de los 99 849 miembros del tarball:
**0 entradas** contienen `.checked-atomic`. Es lo correcto: son productos de build,
no fuentes.

### Qué lo cita

**0 ficheros, 0 ocurrencias**, sobre los 3 802 ficheros / 14 983 685 232 B del
alcance declarado. **PROVEN_ABSENT.**

### Veredicto 2

**EXPLICADA Y CORRECTA.** Producto del `Kbuild` oficial; su presencia es prueba de
que la sonda pasó, y la sonda pasó porque las tres cabeceras están intactas. No hay
nada que arreglar y nada que registrar como desviación del corpus. Es ruido de
compilación, no una anomalía del contenido del corpus.

---

## 3 · Anomalía 3 — `.tmp_missing-syscalls`

### Qué es, y dónde

**0 bytes**, en la **raíz** del árbol del corpus, junto a su `.cmd` de 4 988 B y 57
líneas. mtime 2026-09-27 03:54:59, nueve segundos después de las sondas atómicas.

### De dónde viene: el mismo `Kbuild` oficial

```
Kbuild:50   missing-syscalls-file := .tmp_missing-syscalls$(missing_syscalls_instance)

$(missing-syscalls-file): scripts/checksyscalls.sh $(rq-offsets-file) FORCE
        $(call if_changed_dep,syscalls)

      cmd_syscalls = DEPFILE=$(depfile) $(CONFIG_SHELL) $< $(CC) $(c_flags) \
                        $(missing_syscalls_flags); touch $@
```

Y el `.cmd` contiene la invocación real, con el `gcc -Wp,-MMD` de
`scripts/checksyscalls.sh` y los `-I./include/generated` de este árbol.

**Es la comprobación de upstream de que las llamadas al sistema usadas por el
kernel estén declaradas.** El nombre lo dice, y el nombre acierta: es un temporal
de kbuild. El `.tmp` y el `FORCE` son de la propia regla.

### Ausencia en el oficial

`PROVEN_ABSENT` sobre los 99 849 miembros: **0 entradas**. Producto de build.

### Qué lo cita

**0 ficheros, 0 ocurrencias**, mismo alcance. **PROVEN_ABSENT.**

### Veredicto 3

**EXPLICADA Y CORRECTA.** Producto del `Kbuild` oficial, nombre fiel, sin citas,
sin desviación de contenido. Ruido de compilación.

---

## 4 · La pregunta de fondo: ¿cubre el manifiesto?

### Lo que hay

| registro | entradas | bytes | alcance declarado |
|---|---:|---:|---|
| `corpus-amdgpu-sha256-linux-7.1.3.txt` | **61** | 9 116 | «sha256 de cada fichero del corpus linux-7.1.3 **al que el componente de driver CITA**» |
| `corpus-amdgpu-instrumented-linux-7.1.3.txt` | **61** | 6 986 | el mismo, + `instrumented: yes\|no` + delta en bytes; generado 2026-10-04 01:43:20 |
| `drivers/gpu/drm/polaris12xl/SOURCE-MANIFEST.sha256` | **35** | 3 603 | el injerto, rutas relativas a `drivers/gpu/drm/` |
| `.corpus_guard_state.json` | **2 787** | 428 812 | **sólo `RESEARCH/working/linux-7.1.3`** — otro árbol, no `kernelbuild` |

### Las tres anomalías contra esos registros

| anomalía | ficheros | cubiertos |
|---|---:|---:|
| 1 · `polaris12xl/` | 79 | 0 por el manifiesto de amdgpu; **35 por su propio `SOURCE-MANIFEST`** (los 43 artefactos de build, fuera, correctamente) |
| 2 · `.checked-atomic-*.h` (+ `.cmd`) | 6 | **0** |
| 3 · `.tmp_missing-syscalls` (+ `.cmd`) | 2 | **0** |

`.corpus_guard_state.json` no menciona ninguna de las tres: 0 ocurrencias de
`polaris12xl`, 0 de `checked-atomic`, 0 de `tmp_missing-syscalls`.

### ¿Es eso un agujero?

**Para las anomalías 2 y 3, no.** Su producto es el `Kbuild` del oficial, y el
propio `Kbuild` está en el tarball verificado por hash. Reproducirlas es
`make` sobre un árbol que ya se sabe íntegro.

**Para la anomalía 1, no**, porque el injerto trae su propio manifiesto y este
verifica 35/35. La cadena «tarball oficial + `SOURCE-MANIFEST.sha256` + las 2
costuras de una línea» reconstruye el subárbol por completo.

**El alcance de 61 está declarado y la herramienta lo respeta.** El manifiesto lo
dice en su cabecera, y `04-IMPLEMENTACION/rx550-driver/tools/corpus_manifest_check.py`
lo dice en su docstring (L14-16 «que CITA el componente de driver»; L51-54 «no decide
si un fichero está instrumentado»; L56-60 «a `working/` y `baseline/` les faltan 21
de las 61»). No es un truncamiento silencioso.

### El agujero real es otro, y es mayor

El corpus modifica **6** ficheros. El manifiesto cubre **2**:

| fichero | Δ bytes | ¿en el manifiesto? |
|---|---:|---|
| `amdgpu_vm.c` | +518 | **sí** (`instrumented: yes`) |
| `amdgpu_vm_pt.c` | +917 | **sí** (`instrumented: yes`) |
| `amdgpu_debugfs.c` | **+10 646** | **NO** |
| `amdgpu_debugfs.h` | +1 514 | **NO** |
| `drivers/gpu/drm/Kconfig` | +46 | **NO** |
| `drivers/gpu/drm/Makefile` | +46 | **NO** |

**El mayor delta de todo el corpus —10 646 B, +264 líneas— no tiene sha256 en
ningún sitio del repositorio.** Y no es una modificación cualquiera: el diff
apertura es

```
+#include <linux/ktime.h>
+/*
+ * RE-02-E1 (RG-1): observational PDE emission ring.
```

Es instrumentación del propio proyecto, la más importante de las dos parejas que
tocan `amdgpu_debugfs`. Y `amdgpu_debugfs` es, por conteo, **la cadena más citada
del proyecto**: **1 343 ocurrencias en 30 ficheros**, incluido
`04-IMPLEMENTACION/rx550-mem/rx550_sub.h`, `docs/EVIDENCE-MATRIX.md`,
`docs/CURRENT-STATE.md`, `08-ARQUITECTURA/designs/010-stage2-p8-teardown-completion.md`
(7) y `06-INGENIERIA-INVERSA/findings/1000-…` (2).

Alcance de esa búsqueda: los mismos 3 802 ficheros / 14 983 685 232 B.

### Lo que eso invalida

**No invalida ninguna afirmación sobre el hardware.** Ni el ASIC, ni GFX8, ni los
mapas de registros, ni PM4, ni VM/GART, ni el RX 550. La semántica del proyecto no
se apoya en ninguno de los tres artefactos anómalos, y las dos cabeceras atómicas y
el temporal de syscalls no participan en ninguna cadena semántica.

**Degrada una afirmación concreta de reproducibilidad.** La receta «el corpus se
regenera del tarball oficial **y hay hashes para verificar cada modificación**» es
`PARTIAL`, no `PROVEN`: **2 de las 6 modificaciones tienen hash; 4 no.** En
concreto, quien重建 el corpus en otra máquina con el manifiesto como lista de
comprobación **no tiene forma de verificar `amdgpu_debugfs.c`**, que es la
modificación de mayor tamaño y una de las dos que alimentan el anillo de PDE.

**Confirma** el hallazgo 1033 §R6 y le añade el enumerado completo que faltaba:
6 ficheros modificados, 10 009 añadidos, 0 ausentes.

**No invalida** el «NO» de `PATCH-SOURCES.md:191` sobre usar `polaris12xl`, ni su
afirmación de inercia.

---

## 5 · Lo que queda abierto

1. **La atribución por commit es imposible para todo `RESEARCH/`**, no sólo para
   estas tres anomalías. `.gitignore:63` es `RESEARCH/` entero. Cualquier
   afirmación del tipo «el fichero X lo puso el commit Y» sobre el corpus es
   `NOT_DETERMINED` y no puede dejar de serlo mientras el corpus esté ignorado.
   Lo único recuperable es `mtime` + contenido, que es lo que se ha usado aquí.
2. **`.config` (290 253 B, mtime 2026-10-03 11:14:38) y `.config.old` (290 183 B)
   no están en el oficial ni en ningún manifiesto.** No afectan a la identidad de
   las fuentes, que es el propósito declarado del manifiesto, pero sí condicionan
   los 9 700 `include/config/*` y los 210 artefactos de kbuild: sin ellos el
   *estado de build* del corpus no es reproducible. `.config` contiene
   `CONFIG_DRM_POLARIS12XL=m`, `CONFIG_DRM_AMDGPU=m`, `CONFIG_DEBUG_FS=y`.
3. **`amdgpu` no está compilado en el corpus.** `CONFIG_DRM_AMDGPU=m`, pero el
   único `.ko` del árbol es `polaris12xl.ko` y en `amd/amdgpu/` sólo hay 3 `.o`
   (`amdgpu_debugfs.o`, `amdgpu_vm.o`, `amdgpu_vm_pt.o`). Se compilaron los TU
   instrumentados, no el módulo. Corrobora 1033 §R6 («no hay `amdgpu.ko`») y
   significa que **el corpus no demuestra que el código instrumentado enlace**.
   `amdgpu_debugfs.h` no tiene `.o`, lo cual es lo esperado por ser cabecera.
4. **Decisión del nodo principal, no de este:** si `corpus-amdgpu-sha256-linux-7.1.3.txt`
   debe crecer de 61 a 65 entradas para cubrir las 4 modificaciones que le faltan.
   Este hallazgo no modifica el manifiesto: sólo mide su alcance y muestra que 2 de
   6 deltas no tienen hash.

---

## Trazabilidad

- **Corpus**: `RESEARCH/kernelbuild/linux-7.1.3` — 103 618 ficheros regulares,
  87 symlinks
- **Tarball**: `RESEARCH/evidence/linux-7.1.3.tar.xz` —
  `be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc`,
  158 335 040 B, 99 849 miembros
- **Script de la medición**: `/tmp/opencode/corpus_full_diff.py`;
  datos: `/tmp/opencode/corpus_full_diff.json`
- **Anomalía 1**: `drivers/gpu/drm/polaris12xl/` (79 ficheros);
  `SOURCE-MANIFEST.sha256` 35/35; `RESEARCH/polaris12xl/` 34/36 idénticos;
  `Makefile` = `Makefile.kbuild`; `.ko` 723 136 B @ 2026-10-03 11:16:51;
  `p12xl_asic.h:44-52`; `core/p12xl_asic.c:25-26`; `Kconfig` completo;
  `PATCH-SOURCES.md:191`
- **Anomalía 2**: `.checked-atomic-{arch-fallback,instrumented,long}.h` (0 B) y sus
  `.cmd`; productor `Kbuild` (`atomic-checks`, `cmd_check_sha1`);
  las 3 cabeceras atómicas idénticas al oficial
- **Anomalía 3**: `.tmp_missing-syscalls` (0 B) y su `.cmd`;
  productor `Kbuild:50` + `cmd_syscalls` + `scripts/checksyscalls.sh`
- **Costuras**: `drivers/gpu/drm/Kconfig:367`, `drivers/gpu/drm/Makefile:259`
  (oficiales `dc7fa973…` y `20228b76…`; corpus `b7abe26d…` y `c0b1af16…`)
- **Modificados**: `amdgpu_debugfs.c` (`6f…`/`…`) +10 646; `amdgpu_debugfs.h`
  +1 514; `amdgpu_vm.c` +518; `amdgpu_vm_pt.c` +917
- **Manifiestos**: `corpus-amdgpu-sha256-linux-7.1.3.txt` (61),
  `corpus-amdgpu-instrumented-linux-7.1.3.txt` (61),
  `.corpus_guard_state.json` (2 787, sólo `working/`),
  `04-IMPLEMENTACION/rx550-driver/tools/corpus_manifest_check.py` (L14-16, L51-60)
- **Alcance de la búsqueda de citas**: 3 802 ficheros / 14 983 685 232 B;
  excluidos `RESEARCH/`, `rx550-upstream-7.2.8/`, `.git/`, `__pycache__`,
  `.opencode`; los 21 ficheros de >40 MB leídos por trozos
- **Hallazgos relacionados**: `1033` §R6 (confirmado y completado),
  `1011`, `403`, `551`, `968`
- **Sin escribir**: `04-IMPLEMENTACION/` — `corpus_manifest_check.py` sólo se leyó
- **Prefijo de numeración**: 1035, reservado antes de escribir
  (`tools/nextnum.py --reservar 1035` → `RESERVADO`)