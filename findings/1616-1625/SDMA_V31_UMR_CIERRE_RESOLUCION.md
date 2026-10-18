# Informe de cierre estático: resolución de registros SDMA v3.x en UMR para Polaris 12

**Objetivo:** Completar la verificación estática de la ruta de registros SDMA de Polaris 12 en UMR y decidir si puede cerrarse la frontera de procedencia estática.

**Informe de referencia:** `SDMA_V31_UMR_PROCEDENCIA.md` (no se modifica ni sobrescribe).

---

## 1. Flujo de resolución de nombres

La ruta candidata a verificar es:

```
polaris12.oss300.mmSDMA0_CHICKEN_BITS
```

Cada segmento se resuelve estáticamente de la siguiente manera:

| Paso | Segmento | Qué resuelve | Archivo de evidencia | Línea |
|------|----------|--------------|----------------------|-------|
| 1 | `polaris12` | ASIC/familia de GPU | `/usr/share/umr/database/polaris12.asic` | 1 |
| 2 | `oss300` | Bloque IP declarado en polaris12.asic | `/usr/share/umr/database/polaris12.asic` | 8 |
| 3 | `ip/oss_3_0_0.reg` | Archivo de registros del bloque | `/usr/share/umr/database/polaris12.asic` | 8 |
| 4 | `mmSDMA0_CHICKEN_BITS` | Nombre del registro en el regdb | `/usr/share/umr/database/ip/oss_3_0_0.reg` | registro SDMA |
| 5 | `0x3405` | Offset absoluto MMIO del registro | `/usr/share/umr/database/ip/oss_3_0_0.reg` | campo 3 |

**Contenido de `polaris12.asic` (líneas 1–9):**

```
polaris12 null 2 8 2 0
uvd600 null 0 ip/uvd_6_0_0.reg
vce300 null 0 ip/vce_3_0_0.reg
gmc810 null 0 ip/gmc_8_1_0.reg
dce1120 null 0 ip/dce_11_2_0.reg
gfx800 null 0 ip/gfx_8_0_0.reg
smu713 null 0 ip/smu_7_1_3.reg
oss300 null 0 ip/oss_3_0_0.reg
bif510 null 0 ip/bif_5_1_0.reg
```

**Entrada `mmSDMA0_CHICKEN_BITS` en `oss_3_0_0.reg`:**

```
mmSDMA0_CHICKEN_BITS 0 0x3405 9 0 4294967295
	COPY_EFFICIENCY_ENABLE 0 0
	STALL_ON_TRANS_FULL_ENABLE 1 1
	STALL_ON_NO_FREE_DATA_BUFFER_ENABLE 2 2
	COPY_OVERLAP_ENABLE 16 16
	SRBM_POLL_RETRYING 20 20
	CG_STATUS_OUTPUT 23 23
	CE_AFIFO_WATERMARK 26 27
	CE_DFIFO_WATERMARK 28 29
	CE_LFIFO_WATERMARK 30 31
```

El formato de línea de registro es: `<nombre> <inst> <offset> <num_campos> <min> <max>`, seguido por líneas tabuladas `<campo> <lo> <hi>` para cada subcampo.

---

## 2. Archivos y funciones inspeccionadas

### 2.1 Base de datos de UMR (local, solo lectura)

| Archivo | Ruta | Qué contiene | Estado |
|---------|------|--------------|--------|
| `polaris12.asic` | `/usr/share/umr/database/polaris12.asic` | Declaración de 8 bloques IP de polaris12, incluido `oss300` | **Inspeccionado** |
| `oss_3_0_0.reg` | `/usr/share/umr/database/ip/oss_3_0_0.reg` | 660 registros, 301 SDMA (`mmSDMA0_*` + `mmSDMA1_*`) con offsets y subcampos | **Inspeccionado** |
| Directorio `/usr/share/umr/database/ip/` | — | Solo archivos `sdma*_4_*.reg` (v4.0+). No existe `sdma*_3_*.reg`. | **Inspeccionado** |
| Documentación `/usr/share/doc/umr/README` | — | Describe UMR como herramienta de lectura/escritura MMIO; requiere root o setuid | **Inspeccionado** |

### 2.2 Código fuente del parser de UMR

**No disponible localmente.** El sistema tiene instalado el binario `/usr/bin/umr` pero no los archivos fuente `.c` del parser (ni `comp/compiler.c` ni ningún archivo de resolución de nombres). No se puede inspeccionar estáticamente cómo UMR transforma la ruta `polaris12.oss300.mmSDMA0_CHICKEN_BITS` en bloque, archivo, registro y offset en tiempo de ejecución.

---

## 3. Evidencia para cada segmento de la ruta

| Segmento | Evidencia estática | Clasificación |
|----------|-------------------|---------------|
| `polaris12` es un ASIC conocido en el regdb | Archivo `polaris12.asic` existe y comienza con `polaris12 null 2 8 2 0` | **PROVEN** |
| `oss300` es un bloque IP declarado para polaris12 | Línea 8 de `polaris12.asic`: `oss300 null 0 ip/oss_3_0_0.reg` | **PROVEN** |
| `oss_3_0_0.reg` es el archivo de registros del bloque `oss300` | Misma línea 8 de `polaris12.asic` | **PROVEN** |
| `oss_3_0_0.reg` contiene 301 registros SDMA (`mmSDMA0_*` + `mmSDMA1_*`) | Contado directamente del archivo (150 + 151) | **PROVEN** |
| `mmSDMA0_CHICKEN_BITS` existe en `oss_3_0_0.reg` con offset 0x3405 | Línea encontrada mediante grep; offset coincide con kernel `oss_3_0_d.h` | **PROVEN** |
| Subcampos de `mmSDMA0_CHICKEN_BITS` existen (COPY_EFFICIENCY_ENABLE, etc.) | 9 líneas tabuladas bajo el registro en `oss_3_0_0.reg` | **PROVEN** |
| UMR acepta la sintaxis `polaris12.oss300.mmSDMA0_CHICKEN_BITS` | **No verificable** — no hay código fuente del parser localmente | **INFERRED** (no probado) |
| UMR puede listar/resolver registros de `oss300` sin hardware | **No ejecutable** — requiere conexión al dispositivo GPU y privilegios de root | **BLOQUEADO por restricción** |

---

## 4. Sintaxis aceptada y límites de la conclusión

### 4.1 Lo que está estructuralmente respaldado

La cadena de resolución `polaris12 → oss300 → oss_3_0_0.reg → mmSDMA0_CHICKEN_BITS → 0x3405` está **completamente respaldada por evidencia estática** de los archivos de base de datos de UMR. Cada eslabón de la cadena es verificable leyendo los archivos locales.

### 4.2 Lo que NO está respaldado (sin código fuente del parser)

- La sintaxis exacta que el parser de UMR espera para la ruta completa (`polaris12.oss300.mmSDMA0_CHICKEN_BITS` vs. alguna variante con puntos, guiones, corchetes, o prefijo `reg` en lugar de `mm`).
- Si UMR realiza alguna transformación adicional (normalización de offsets, sustitución de prefijo `mm`→`reg`, etc.) antes de acceder al registro.
- Si el bloque `oss300` tiene una dirección base MMIO que se suma al offset del registro, o si el offset en el regdb es ya absoluto.

### 4.3 Condiciones de ejecución (no probadas, no ejecutadas)

- La lectura MMIO real vía UMR requiere conexión al dispositivo GPU y privilegios de root (documentado en `/usr/share/doc/umr/README`: "If you plan to use it as a non-root user you may want to add the setuid bit").
- No se ejecutó `umr` para listar registros ni para leer ningún valor MMIO, cumpliendo la restricción de no acceder al hardware.

---

## 5. Clasificación epistemológica de afirmaciones

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| `polaris12.asic` declara bloque `oss300` cargando `ip/oss_3_0_0.reg` | **PROVEN** | Leído directamente del archivo local (línea 8). |
| `oss_3_0_0.reg` contiene `mmSDMA0_CHICKEN_BITS` con offset 0x3405 | **PROVEN** | Encontrado directamente en el archivo; coincide con kernel `oss_3_0_d.h`. |
| `oss_3_0_0.reg` contiene 301 registros SDMA (150 SDMA0 + 151 SDMA1) | **PROVEN** | Contado directamente del archivo local. |
| La cadena `polaris12 → oss300 → oss_3_0_0.reg → mmSDMA0_CHICKEN_BITS → 0x3405` es estructuralmente válida | **PROVEN** | Cada eslabón verificado en archivos locales de UMR. |
| UMR acepta exactamente `polaris12.oss300.mmSDMA0_CHICKEN_BITS` como ruta de acceso | **INFERRED** | La estructura de la base de datos lo sugiere, pero sin código fuente del parser no es verificable estáticamente. |
| UMR puede listar/resolver registros de `oss300` offline sin hardware | **NO VERIFICABLE** | Requeriría ejecutar `umr`, lo que implica acceso al dispositivo y privilegios de root. |
| `oss300` es el bloque portador de SDMA v3.x para Polaris12 en UMR | **PROVEN** | `polaris12.asic` declara `oss300` y `oss_3_0_0.reg` contiene los 301 registros SDMA v3.x. |

---

## 6. Decisión final

**Decisión: PARTIAL**

Se confirma parcialmente la ruta de resolución:

- **Confirmado:** Asociación del bloque `oss300` con `polaris12` (en `polaris12.asic`). Nombre del registro `mmSDMA0_CHICKEN_BITS` y offset `0x3405` (en `oss_3_0_0.reg`). Subcampos y bitfields del registro.
- **No confirmado (falta evidencia):** El código fuente del parser de UMR no está disponible localmente, por lo que no se puede verificar estáticamente que UMR acepte exactamente la sintaxis `polaris12.oss300.mmSDMA0_CHICKEN_BITS`, ni que realice la resolución completa en tiempo de ejecución sin transformaciones adicionales.

**No se eleva a `CLOSED_STATIC`** porque falta la verificación del parser (código fuente no disponible localmente).
**No se eleva a validación dinámica** porque requeriría root y acceso MMIO, prohibido en esta fase.
**No se declara `BLOCKED`** porque la asociación bloque→archivo→registro→offset está completamente respaldada estáticamente; solo falta la verificación del parser.

**Justificación:** La frontera de procedencia estática está casi cerrada. Las definiciones SDMA v3.x existen en el regdb de UMR (vía `oss300/oss_3_0_0.reg`), cargado para polaris12, y coinciden exactamente con el kernel. La única incertidumbre restante es sintáctica (forma exacta de la ruta que acepta el parser), no de existencia de definiciones.

---

## 7. Una sola siguiente acción prioritaria

**Obtener y inspeccionar estáticamente el código fuente del parser de UMR** (repositorio upstream `hakzsam/umr` en GitLab, archivo relacionado con resolución de nombres/rutas de registros, por ejemplo bajo `src/` o `app/`) para confirmar que UMR acepta la sintaxis `polaris12.oss300.mmSDMA0_CHICKEN_BITS` y cómo transforma dicha ruta en bloque, archivo de registros, nombre y offset. Esto se debe hacer de solo lectura (API web/Git sin clonar), sin ejecutar `umr` contra el hardware, y sin usar sudo/root.

---

## Resumen

- **Se comprobó:** La ruta `polaris12 → oss300 → oss_3_0_0.reg → mmSDMA0_CHICKEN_BITS → 0x3405` está estructuralmente completa y respaldada por los archivos locales de UMR. `oss300` es el bloque portador de SDMA v3.x para Polaris12.
- **Sigue sin demostrarse:** Que el parser de UMR acepte exactamente la sintaxis `polaris12.oss300.mmSDMA0_CHICKEN_BITS` (falta código fuente del parser localmente).
- **Lectura MMIO:** Queda fuera de alcance hasta que exista autorización explícita para esa fase (requiere root).
- **Decisión:** `PARTIAL` — confirmada la asociación bloque/registro/offset; pendiente la verificación del parser.
