# Informe de procedencia UMR para SDMA v3.1 / Polaris 12

**Objetivo:** Determinar si existen definiciones de registros SDMA v3.1 trazables y autorizadas (kernel o UMR upstream) para Polaris 12 (1002:699f, rev 0xc7), y si es posible reconstruir un regdb SDMA v3.x independiente a partir de ellas, sin reusar v4.0 por suposición.

**Estado del objetivo:** RESUELTO estáticamente. Las definiciones SDMA v3.x YA EXISTEN en el regdb instalado de UMR, embebidas en el archivo `oss_3_0_0.reg` dentro del bloque IP `oss300`, el cual **sí está cargado para polaris12**. Coinciden exactamente (301/301 registros, 859/859 subcampos) con las definiciones autoritativas del kernel en `oss_3_0_d.h` + `oss_3_0_sh_mask.h`. No es necesario crear `sdma0_3_1_0.reg`.

---

## 1. Pregunta y alcance

**Pregunta:** ¿Existe una definición de registros SDMA v3.1 (o v3.x) autorizada y trazable para Polaris 12 que permita dotar a UMR de un regdb SDMA v3.x, sin suponer compatibilidad con v4.0?

**Alcance:**
- Solo fuentes locales existentes y repositorio upstream de UMR de solo lectura (GitLab API / web, sin clonar).
- No se creó `sdma0_3_1_0.reg` ni ninguna regdb nueva (pendiente de decisión).
- No se usó sudo/root, no se leyó ni escribió MMIO/VRAM/`/dev/dri`, no se modificaron archivos del sistema, kernel, driver, firmware, regdb ni permisos.
- La validación dinámica (lectura MMIO real vía UMR) queda pendiente porque requiere root, que está fuera del alcance de esta fase.

---

## 2. Fuentes consultadas y límites de cobertura

### 2.1 Kernel local (fuente autorizada principal)

| Archivo | Ruta | Contenido relevante |
|---|---|---|
| `oss_3_0_d.h` | `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/oss/oss_3_0_d.h` | 301 definiciones `#define mmSDMA0_*` / `mmSDMA1_*` con offsets absolutos MMIO (0x3400–0x37ff para SDMA0; 0x3600–0x37c7 para SDMA1). Líneas 291–594. |
| `oss_3_0_sh_mask.h` | `.../oss/oss_3_0_sh_mask.h` | 859 definiciones de campo (`SDMA0_REG__CAMPO_MASK` / `__SHIFT`) para 301 registros SDMA. |
| `sdma_v3_0.c` | `.../amdgpu/sdma_v3_0.c` | `sdma_v3_1_ip_block` (major=3, minor=1, rev=0, funcs=`sdma_v3_0_ip_funcs`) en líneas 1693–1700. Incluye `oss/oss_3_0_d.h`. Consume `mmSDMA0_*` + `SDMA1_REGISTER_OFFSET=0x200`. |
| `vid.h` / `cikd.h` | `.../amdgpu/vid.h` (líneas 26–27), `.../amdgpu/cikd.h` (líneas 491–492) | `SDMA0_REGISTER_OFFSET 0x0`, `SDMA1_REGISTER_OFFSET 0x200`. |
| `vi.c` | `.../amdgpu/vi.c` | Selecciona el bloque SDMA v3.1 para VI/Polaris12. |

### 2.2 UMR instalado localmente (regdb)

| Archivo | Ruta | Contenido relevante |
|---|---|---|
| `oss_3_0_0.reg` | `/usr/share/umr/database/ip/oss_3_0_0.reg` | 660 registros totales; **301 registros SDMA** (`mmSDMA0_*` = 150, `mmSDMA1_*` = 151) con offsets absolutos 0x3400–0x37ff y subcampos (lo hi). |
| `polaris12.asic` | `/usr/share/umr/database/polaris12.asic` | Declara 8 bloques IP, incluido `oss300 null 0 ip/oss_3_0_0.reg`. Ningún bloque `sdma*`. |
| Directorio `/usr/share/umr/database/ip/` | — | Solo archivos `sdma*_4_*.reg` (v4.0+). No existe `sdma*_3_*.reg`. |

### 2.3 UMR upstream (GitLab, solo lectura, sin clonar)

Proyecto identificado vía API de búsqueda: `Samuel Pitoiset / umr` (ID 27167), `https://gitlab.freedesktop.org/hakzsam/umr`. Rama por defecto `main`, HEAD `95c15b9`.

Se consultó el árbol de `database/ip` y el historial de commits (API `repository/commits?path=...`) para las etiquetas `UMR_RELEASE_1_00` … `1.0.11` y ramas (`main`, `add_steamdeck`, `fix_waves_scan`, `small-fixups`, `switch-buffer-fields`).

**Resultado upstream:** No existe, ni existe en el historial, ningún archivo `sdma*_3_*.reg` (probado sistemáticamente: `sdma0_3_0_0.reg`, `sdma0_3_1_0.reg`, `sdma1_3_0_0.reg`, `sdma1_3_1_0.reg`, `sdma_3_0_0.reg`, `sdma_3_1_0.reg`, `sdma0_3_0.reg`, `sdma0_3_1.reg`, `sdma3_0_0.reg`, `sdma3_1_0.reg` — todos devuelven historial vacío `[]`). Los únicos archivos SDMA del upstream son v4.x (`sdma0_4_0_0.reg`, `sdma0_4_1_0.reg`, `sdma0_4_2_0.reg`, `sdma0_4_2_2.reg`, `sdma1_4_0_0.reg`, `sdma1_4_2_0.reg`, `sdma1_4_2_2.reg`, `sdma2_4_2_2.reg`…`sdma7_4_2_2.reg`, `sdma_4_4_0.reg`) más `lsdma_6_0_0.reg` (añadido en 1.0.5/1.0.6/1.0.7).

El archivo `polaris12.asic` del upstream nunca ha incluido un bloque SDMA (historial: commits `abb597b8` y `cf4fd33`, el "Big database refactor" de 2021-03-08). Pre-refactor, `polaris12.c` declaraba los mismos 8 bloques (uvd6, vce3, gmc81, dce112, gfx80, smu713, oss30, bif51) sin SDMA separado.

**Límite de cobertura:** No se puede validar dinámicamente (lectura MMIO) porque requiere root. No se clonó el repositorio upstream (prohibido). La verificación upstream se limitó a API de árbol, commits por ruta y etiquetas publicadas.

---

## 3. Archivos y definiciones candidatas

### 3.1 Candidato principal (encontrado): `oss_3_0_0.reg` — bloque `oss300`

Este archivo **YA EXISTE** en el regdb instalado de UMR y **YA ESTÁ CARGADO para polaris12** (línea `oss300 null 0 ip/oss_3_0_0.reg` en `polaris12.asic`). Contiene los 301 registros SDMA v3.x con offsets absolutos MMIO.

**Ruta de acceso UMR (estática):** `polaris12.oss300.mmSDMA0_<REGISTRO>` / `polaris12.oss300.mmSDMA1_<REGISTRO>`.

### 3.2 Candidatos descartados

| Candidato | Motivo de descarte |
|---|---|
| `sdma0_3_1_0.reg` / `sdma1_3_1_0.reg` | Nunca existieron en UMR upstream (historial vacío). No hay que crearlos todavía (instrucción explícita). |
| `sdma0_4_0_0.reg` (v4.0) | Es v4.0, no v3.1. Los offsets están normalizados a 0x0–0x1ff y difieren de v3.x en registros de control (POWER_CNTL 0x1a vs 0x3402, etc.). Reusarlo por suposición queda rechazado (decisión previa). |
| Bloque `sdma0`/`sdma1` en `polaris12.asic` | No existe; `polaris12.asic` tiene 8 bloques, ninguno `sdma*`. El acceso correcto es vía `oss300`. |

---

## 4. Commits, etiquetas y procedencia

**UMR upstream (`hakzsam/umr`, GitLab):**
- HEAD `main`: `95c15b9eb61a94c7bf47ac7de191315c18029135`
- Etiquetas consultadas: `UMR_RELEASE_1_00`, `1_01`, `1_02`, `1_03`, `1.0.4`, `1.0.5`, `1.0.6`, `1.0.7`, `1.0.8`, `1.0.9`, `1.0.10`, `1.0.11`
- Commits SDMA relevantes: `62010f3f` ("Improved searching of register database"), `cf4fd33a` ("Big database refactor", 2021-03-08), `af96781d` ("fix waves scan for GFX10.3"), `d95273c9` ("add Steam Deck to the pci database")
- Commits que añadieron `lsdma_6_0_0.reg`: "import of new lsdma IP block" (1.0.5–1.0.7)

**Procedencia de las definiciones SDMA v3.x:**
- El kernel define `mmSDMA0_*`/`mmSDMA1_*` en `oss_3_0_d.h` (parte de los headers VI/OSS). El driver `sdma_v3_0.c` (incluyendo `sdma_v3_1_ip_block`) los consume directamente.
- El regdb de UMR (`oss_3_0_0.reg`) fue generado a partir de estos mismos headers del kernel (el compilador `comp/compiler.c` de UMR parsea los headers SOC15/pre-SOC15 del árbol DRM-next).
- `polaris12.asic` (tanto en UMR instalado como en upstream) declara `oss300` cargando `oss_3_0_0.reg`.

---

## 5. Tabla de comparación de registros (evidencia)

Comparación automática directa de archivos locales (kernel `oss_3_0_d.h` vs UMR `oss_3_0_0.reg`), sin suposición de normalización:

| Métrica | Kernel `oss_3_0_d.h` | UMR `oss_3_0_0.reg` | Resultado |
|---|---|---|---|
| Registros `mmSDMA0_*` definidos | 150 | 150 | Coinciden |
| Registros `mmSDMA1_*` definidos | 151 | 151 | Coinciden |
| Total registros SDMA | 301 | 301 | **301/301 nombres comunes** |
| Registros solo en kernel | — | — | 0 |
| Registros solo en UMR | — | — | 0 |
| Offsets idénticos (absolutos) | 301 | 301 | **0 discrepancias** |
| Ejemplos de offsets | `mmSDMA0_CNTL 0x3404`, `mmSDMA0_CHICKEN_BITS 0x3405`, `mmSDMA0_ACTIVE_FCN_ID 0x3424`, `mmSDMA1_CNTL 0x3604` | Idénticos | Verificado |
| Subcampos kernel (MASK+SHIFT) | 859 (en `oss_3_0_sh_mask.h`) | — | — |
| Subcampos UMR (lo hi) | — | 1222 | — |
| Subcampos idénticos (ambos) | — | — | **859/859 idénticos** |
| Subcampos distinto offset | — | — | 0 |
| Subcampos solo en kernel | — | — | 0 |
| Subcampos solo en UMR (RESERVED extra) | — | — | 363 (no conflictos; son campos de relleno) |
| `polaris12.asic` carga `oss300` | Sí | `oss300 null 0 ip/oss_3_0_0.reg` | **Confirmado** |

**Bitfield de ejemplo (`mmSDMA0_CHICKEN_BITS`, offset 0x3405):**

| Campo | Kernel (MASK → bits) | UMR (lo hi) | ¿Coincide? |
|---|---|---|---|
| COPY_EFFICIENCY_ENABLE | 0x1 → bit 0 | 0 0 | Sí |
| STALL_ON_TRANS_FULL_ENABLE | 0x2 → bit 1 | 1 1 | Sí |
| STALL_ON_NO_FREE_DATA_BUFFER_ENABLE | 0x4 → bit 2 | 2 2 | Sí |
| COPY_OVERLAP_ENABLE | 0x10000 → bit 16 | 16 16 | Sí |
| SRBM_POLL_RETRYING | 0x100000 → bit 20 | 20 20 | Sí |
| CG_STATUS_OUTPUT | 0x800000 → bit 23 | 23 23 | Sí |
| CE_AFIFO_WATERMARK | 0xc000000 → bits 26-27 | 26 27 | Sí |
| CE_DFIFO_WATERMARK | 0x30000000 → bits 28-29 | 28 29 | Sí |
| CE_LFIFO_WATERMARK | 0xc0000000 → bits 30-31 | 30 31 | Sí |

**Conclusión de la comparación:** Las definiciones SDMA v3.x en `oss_3_0_0.reg` de UMR son **idénticas** (nombre, offset absoluto, máscara/shift de cada campo) a las definiciones autoritativas del kernel en `oss_3_0_d.h` + `oss_3_0_sh_mask.h`. No hay discrepancias.

---

## 6. Diferencias, incertidumbres y riesgos de compatibilidad

### 6.1 Ninguna diferencia de registro encontrada

La comparación estática muestra coincidencia total (301/301 registros, 859/859 subcampos). No hay registros faltantes, duplicados, offsets conflictivos ni máscaras diferentes entre kernel y UMR.

### 6.2 Los 363 subcampos "solo en UMR"

Son campos `RESERVED` que el regdb de UMR enumera explícitamente pero que el kernel no tiene definidos como MASK/SHIFT en `oss_3_0_sh_mask.h`. No representan un conflicto de compatibilidad: son bits no nombrados por el kernel. Riesgo bajo.

### 6.3 Riesgo: ruta de acceso UMR sin probar dinámicamente

Estáticamente, la ruta `polaris12.oss300.mmSDMA0_CHICKEN_BITS` es resoluble (bloque `oss300` cargado en `polaris12.asic`, registro presente en `oss_3_0_0.reg`). Pero **no se ha probado la lectura MMIO real** porque requiere `sudo`/`root`, prohibido en esta fase. Esta es la única incertidumbre restante.

### 6.4 Riesgo: base de direcciones del bloque oss300

El regdb guarda offsets absolutos (0x3400+). Para VI/Polaris12, el bloque OSS/SDMA está mapeado en MMIO en ese rango (el kernel lee `mmSDMA0_CNTL` = 0x3404 directamente en el espacio MMIO del dispositivo). Esto está corroborado por el driver `sdma_v3_0.c` que usa `mmSDMA0_*` sin offset adicional para SDMA0 (`SDMA0_REGISTER_OFFSET = 0x0`).

---

## 7. Clasificación epistemológica de afirmaciones

| Afirmación | Clasificación | Base |
|---|---|---|
| `oss_3_0_d.h` del kernel define 301 registros SDMA (`mmSDMA0_*` + `mmSDMA1_*`) | **PROVEN** | Extraído y contado directamente del archivo local. |
| `oss_3_0_0.reg` de UMR contiene 301 registros SDMA con los mismos nombres | **PROVEN** | Extraído y contado directamente del regdb instalado. |
| Todos los 301 offsets coinciden exactamente kernel vs UMR | **PROVEN** | Comparación automática join sobre archivos locales; 0 discrepancias. |
| Todos los 859 subcampos del kernel están en UMR con mismo rango de bits | **PROVEN** | Comparación automática MASK/SHIFT vs lo hi; 0 distintos. |
| `polaris12.asic` declara `oss300 null 0 ip/oss_3_0_0.reg` | **PROVEN** | Leído directamente del archivo local. |
| No existe `sdma*_3_*.reg` en UMR upstream (ninguna etiqueta/rama) | **PROVEN** | API de commits por ruta devolvió `[]` para 10 nombres probados; árbol de todas las etiquetas revisado. |
| El regdb de UMR ya tiene SDMA v3.x (vía `oss300/oss_3_0_0.reg`) | **PROVEN** | Consecuencia directa de los puntos anteriores. |
| UMR puede leer `polaris12.oss300.mmSDMA0_*` en runtime | **INFERRED** (no probado) | Evidencia estática sólida, pero lectura MMIO real requiere root (no autorizado). |
| Offsets absolutos 0x3400/0x3600 son correctos para Polaris12 | **CORROBORATED** | Kernel `oss_3_0_d.h` + `sdma_v3_0.c` + `SDMA0_REGISTER_OFFSET=0x0` + `SDMA1_REGISTER_OFFSET=0x200`, todo coherente. |
| No se necesita crear `sdma0_3_1_0.reg` | **PROVEN** | Las definiciones ya existen en `oss_3_0_0.reg`. |

---

## 8. Decisión final y justificación

**Decisión: A. SOURCE_FOUND**

Existe una definición SDMA v3.x trazable y con alcance suficientemente documentado: las 301 definiciones de registros y 859 subcampos SDMA v3.x ya están presentes en el regdb instalado de UMR, dentro del archivo `oss_3_0_0.reg`, bajo el bloque IP `oss300`, el cual **sí está cargado para polaris12** (`polaris12.asic` línea `oss300 null 0 ip/oss_3_0_0.reg`). Coinciden exactamente con las definiciones autoritativas del kernel (`oss_3_0_d.h` + `oss_3_0_sh_mask.h`): 301/301 nombres, 0 discrepancias de offset, 859/859 subcampos idénticos.

**Justificación:**
- El bloqueo previo ("no hay SDMA v3.x regdb") se debió a buscar un archivo separado `sdma*_3_*.reg`, que no existe ni ha existido en UMR. Las definiciones SDMA v3.x están embebidas en el bloque OSS, no en un archivo SDMA dedicado.
- No es necesario (ni se debe, por instrucción) crear `sdma0_3_1_0.reg`.
- No hay que reusar v4.0 por suposición: v3.x ya tiene su propia definición verificable.
- La única limitación es la validación dinámica (lectura MMIO), que requiere root y queda para una fase futura autorizada.

**No se selecciona B (PARTIAL_SOURCE) porque la cobertura es completa (301/301 registros). No se selecciona C ni D porque se encontró la definición autorizada.**

---

## 9. Comandos ejecutados, errores y códigos de salida

Todas las operaciones fueron de solo lectura. No se usó `sudo`. No se modificó ningún archivo.

### 9.1 Exploración upstream UMR (GitLab API, solo lectura)

```bash
curl -s "https://gitlab.freedesktop.org/api/v4/projects?search=umr&per_page=5"     # → identificó hakzsam/umr (ID 27167)
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/tree?path=database/ip&ref=main&per_page=200"   # → árbol principal (solo sdma*_4_*.reg)
# Para cada tag UMR_RELEASE_1_00..1.0.11:
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/tree?path=database/ip&ref=<tag>&per_page=100" | grep -i sdma   # → solo sdma*_4_*.reg (y lsdma_6_0_0.reg en 1.0.5–1.0.8)
# Historial por ruta (probó 10 nombres de sdma*_3_*.reg):
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/commits?path=database/ip/sdma0_3_1_0.reg&per_page=1"   # → [] (nunca existió)
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/commits?path=database/ip/sdma1_3_1_0.reg&per_page=1"   # → [] (nunca existió)
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/commits?path=database/ip/sdma0_3_0_0.reg&per_page=1"   # → [] (nunca existió)
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/commits?path=database/ip/sdma0_4_0_0.reg&per_page=1"   # → existe (2 commits)
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/commits?path=database/ip/lsdma_6_0_0.reg&per_page=1"   # → existe (import en 1.0.5)
curl -s "https://gitlab.freedesktop.org/api/v4/projects/27167/repository/files/database%2Fpolaris12.asic/raw?ref=<commit>"   # → 8 bloques, sin SDMA; oss300 presente
```
Códigos de salida: todos 0 (curl exitoso, respuestas JSON válidas). Ninguna operación de escritura ni clonación.

### 9.2 Comparación estática kernel vs UMR (archivos locales)

Script temporal `/tmp/opencode/compare_sdma_fields.py` (fuera del repositorio, no incorporado al proyecto):

```bash
python3 /tmp/opencode/compare_sdma_fields.py   # → salida mostrada en sección 5; código de salida 0
```

Extracciones previas (shell, sólo lectura):
```bash
grep '#define mmSDMA0_\|#define mmSDMA1_' <oss_3_0_d.h> | awk '{print $2,$3}' | sort > /tmp/k_sdma_all.txt      # 301 líneas
grep '^mmSDMA0_\|^mmSDMA1_' /usr/share/umr/database/ip/oss_3_0_0.reg | awk '{print $1,$3}' | sort > /tmp/u_sdma_all.txt   # 301 líneas
join -j1 /tmp/k_sdma_all.txt /tmp/u_sdma_all.txt   # → 301 comunes, 0 solo en cada lado, 0 offsets distintos
```

### 9.3 Errores

Ningún error de ejecución. Las únicas respuestas "vacías" del upstream fueron `[]` (historial inexistente para sdma*_3_*.reg), lo cual es un resultado válido de "no existe en este repositorio", no un error de red.

---

## 10. Siguiente acción prioritaria (una sola)

**Validar estáticamente que UMR resuelve la ruta `polaris12.oss300.mmSDMA0_CHICKEN_BITS` (y un registro SDMA1) sin necesidad de root ni MMIO**, por ejemplo inspeccionando el código de resolución de rutas de UMR o intentando un listado de registros del bloque `oss300` en modo offline/seguro si la herramienta lo permite sin hardware. Si se confirma la resolución estática de la ruta, documentar que `oss300` es el bloque portador de SDMA v3.x para Polaris12 y cerrar la tarea de procedencia; la lectura MMIO real quedará para una fase futura con autorización de root.

---

## Resumen final

- **Se comprobó:** Las definiciones SDMA v3.x de Polaris12 (301 registros + 859 subcampos) ya existen en el regdb instalado de UMR, en `oss_3_0_0.reg` bajo el bloque `oss300`, cargado para polaris12. Coinciden exactamente con el kernel (`oss_3_0_d.h` + `oss_3_0_sh_mask.h`). No existe `sdma*_3_*.reg` en UMR upstream ni en su historial.
- **Sigue sin demostrarse:** La lectura MMIO real de estos registros vía UMR (`polaris12.oss300.mmSDMA0_*`), porque requiere root.
- **BLOCKED → cambia a RESUELTO (estáticamente):** La pregunta de procedencia está respondida: las definiciones están en el regdb existente, trazables al kernel. La única restricción pendiente es la validación dinámica por falta de privilegios, fuera del alcance de esta fase.
- **Siguiente acción:** Verificar estáticamente la resolución de la ruta UMR `polaris12.oss300.mmSDMA0_*` sin root/MMIO.
