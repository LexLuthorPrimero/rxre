# Informe de cierre: verificación upstream del parser UMR y resolución SDMA v3.x

**Objetivo:** Resolver la incertidumbre pendiente sobre la sintaxis y resolución de nombres del parser de UMR para la ruta `polaris12.oss300.mmSDMA0_CHICKEN_BITS`.

**Informes previos (preservados, no modificados):**
- `findings/1616-1625/SDMA_V31_UMR_PROCEDENCIA.md` (SOURCE_FOUND)
- `findings/1616-1625/SDMA_V31_UMR_CIERRE_RESOLUCION.md` (PARTIAL)

---

## 1. Fuente upstream, commit y archivos examinados

**Repositorio:** `https://gitlab.freedesktop.org/hakzsam/umr` (fork de `tomstdenis/umr`)
**Rama:** `main` (HEAD `95c15b9eb61a94c7bf47ac7de191315c18029135`)
**Consulta:** API REST de GitLab, solo lectura, sin clonar.

### 1.1 Archivos del parser inspeccionados

| Archivo | Ruta en el repositorio | Función principal |
|---------|----------------------|-------------------|
| `main.c` | `src/app/main.c` | Procesamiento de argumentos CLI, `--read`/`-r`, `get_block_name` |
| `umr_lookup.c` | `src/app/umr_lookup.c` | `umr_lookup()` — decodificación de registros por nombre |
| `find_ip.c` | `src/lib/find_ip.c` | `umr_find_ip_block()` — búsqueda de bloques IP por nombre |
| `find_reg.c` | `src/lib/find_reg.c` | `umr_find_reg_data_by_ip_by_instance_with_ip()` — búsqueda de registros |

---

## 2. Funciones relevantes y flujo de resolución

### 2.1 `get_block_name` — `src/app/main.c` (línea ~344)

```c
static char *get_block_name(struct umr_asic *asic, char *path)
{
    static char asicname[256], block[256], *dot;
    memset(asicname, 0, sizeof asicname);
    memset(block, 0, sizeof block);
    if ((dot = strstr(path, "."))) {
        memcpy(asicname, path, (int)(dot - path));
        strcpy(block, dot + 1);
    } else {
        strcpy(block, path);
    }
    if (asicname[0] && asicname[0] != '*' && strcmp(asic->asicname, asicname)) {
        printf("[ERROR]: Invalid asicname <%s>\n", asicname);
        return NULL;
    }
    return block;
}
```

Divide `path` en `asicname` y `block` buscando el **primer** punto. Usado por `--list-regs` / `-lr`.

### 2.2 `--read` / `-r` — `src/app/main.c` (líneas ~1210–1235)

```c
} else if (!strcmp(argv[i], "--read") || !strcmp(argv[i], "-r")) {
    if (i + 1 < argc) {
        uint32_t reg;
        argflags[i] = 1;
        argflags[i+1] = 1;

        if (!memcmp(argv[i+1], "0x", 2) && sscanf(argv[i+1], "%"SCNx32, &reg) == 1) {
            printf("0x%08lx\n", (unsigned long)asic->reg_funcs.read_reg(asic, reg, REG_MMIO));
        } else {
            str = strstr(argv[i+1], ".");
            str2 = str ? strstr(str+1, ".") : NULL;
            if (str && str2) {
                memset(asicname, 0, sizeof asicname);
                memset(ipname, 0, sizeof ipname);
                memset(regname, 0, sizeof regname);
                str[0] = 0;
                str2[0] = 0;
                strcpy(asicname, argv[i+1]);
                strcpy(ipname, str+1);
                strcpy(regname, str2+1);
            } else {
                fprintf(stderr, "[ERROR]: Invalid asicname.ipname.regname syntax\n");
                return EXIT_FAILURE;
            }
            umr_scan_asic(asic, asicname, ipname, regname);
        }
        ++i;
    }
}
```

**Flujo de resolución para `--read`:**
1. Si empieza con `0x`, se interpreta como dirección MMIO directa.
2. Si no, busca **dos puntos** en la cadena: `asicname.ipname.regname`.
3. Divide la cadena en tres componentes nulos.
4. Valida que existan ambos puntos; si no, error `"Invalid asicname.ipname.regname syntax"`.
5. Llama a `umr_scan_asic(asic, asicname, ipname, regname)`.

### 2.3 `umr_lookup` — `src/app/umr_lookup.c`

Sintaxis: `ipname.regname` (solo 2 niveles, sin asicname). Busca el IP block por nombre y luego el registro dentro de él. Usado por `--lookup` / `-lu`.

### 2.4 `umr_find_ip_block` — `src/lib/find_ip.c`

Busca un bloque IP por nombre parcial (`memcmp` del `ipname`). Soporta instancia opcional.

### 2.5 `umr_find_reg_data_by_ip_by_instance_with_ip` — `src/lib/find_reg.c`

Busca un registro por nombre dentro de un bloque IP específico (o en todos si `ip` es NULL). Características clave:

- **Búsqueda binaria ordenada** dentro de cada bloque IP.
- **Búsqueda por prefijo de IP:** `ip` se compara como prefijo (ej. `"gfx"` coincide con `"gfx90"`).
- **Fallback `mm` → `reg`:** Si el registro empieza con `"mm"` y no se encuentra, reintenta automáticamente con prefijo `"reg"`:
  ```c
  if (!memcmp(regname, "mm", 2)) {
      memcpy(tmpregname, "reg", 4);
      strncpy(tmpregname + 3, regname + 2, sizeof(tmpregname) - 4);
      regname = (const char *)tmpregname;
      goto retry;
  }
  ```
- Devuelve `0xFFFFFFFF` (vía `umr_find_reg`) si no se encuentra.

---

## 3. Sintaxis aceptada según el código

| Comando | Sintaxis aceptada | Niveles | Separador |
|---------|------------------|---------|-----------|
| `--read` / `-r` | `asicname.ipname.regname` | 3 | `.` (dos puntos) |
| `--write` / `-w` | `asicname.ipname.regname` | 3 | `.` (documentado en ayuda) |
| `--writebit` / `-wb` | `asicname.ipname.regname.bitfieldname` | 4 | `.` (documentado en ayuda) |
| `--lookup` / `-lu` | `ipname.regname` | 2 | `.` |
| `--list-regs` / `-lr` | `asicname.blockname` o `blockname` | 1-2 | `.` (vía `get_block_name`) |

**La expresión `polaris12.oss300.mmSDMA0_CHICKEN_BITS` es sintácticamente válida** para `--read` / `-r` / `--write` / `--writebit`:
- `polaris12` → `asicname` (se compara con `asic->asicname`)
- `oss300` → `ipname` (se busca en los bloques IP del ASIC)
- `mmSDMA0_CHICKEN_BITS` → `regname` (se busca dentro del bloque IP, con fallback `mm`→`reg` si fuera necesario)

---

## 4. Evidencia y limitaciones

### 4.1 Evidencia estática de cada segmento

| Segmento | Evidencia | Archivo | Línea |
|----------|-----------|---------|-------|
| `polaris12` es un ASIC válido en el regdb | `polaris12 null 2 8 2 0` | `polaris12.asic` | 1 |
| `oss300` es un bloque IP declarado para polaris12 | `oss300 null 0 ip/oss_3_0_0.reg` | `polaris12.asic` | 8 |
| `oss_3_0_0.reg` es el archivo de registros del bloque | Misma línea 8 | `polaris12.asic` | |
| `oss_3_0_0.reg` contiene `mmSDMA0_CHICKEN_BITS` offset 0x3405 | Entrada encontrada en el regdb | `oss_3_0_0.reg` | |
| El parser acepta `asicname.ipname.regname` | Código de `--read` divide en 3 componentes | `main.c` | ~1210-1235 |
| El parser valida que existan 2 puntos | `if (str && str2)` | `main.c` | ~1217 |
| Registro `mm*` tiene fallback a `reg*` | `if (!memcmp(regname, "mm", 2))` | `find_reg.c` | |

### 4.2 Limitación: `umr_scan_asic` no localizada

La función `umr_scan_asic(asic, asicname, ipname, regname)` es llamada en `main.c` línea 1235, pero **su definición no se encontró** en el árbol fuente disponible de `hakzsam/umr` (ni en `tomstdenis/umr`). Esto impide verificar estáticamente el comportamiento exacto de resolución interna (cómo combina ASIC + IP + registro para devolver el offset final).

Sin embargo, el flujo de resolución es inferible a partir de:
- `umr_find_ip_block()` (busca bloque IP por nombre)
- `umr_find_reg_data_by_ip_by_instance_with_ip()` (busca registro por nombre dentro del bloque, con fallback `mm`→`reg`)
- La documentación de ayuda de `--read` que documenta explícitamente la sintaxis `asicname.ipname.regname`

### 4.3 Condiciones de ejecución (no ejecutadas)

- La lectura MMIO real vía UMR requiere conexión al dispositivo GPU y privilegios de root (documentado en `/usr/share/doc/umr/README`).
- No se ejecutó `umr` para listar registros ni leer valores MMIO, cumpliendo la restricción de no acceder al hardware.

---

## 5. Clasificación epistemológica

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| Sintaxis `asicname.ipname.regname` es aceptada por `--read`/`-r` | **PROVEN** | Código fuente `main.c` líneas ~1210-1235 |
| `polaris12.oss300.mmSDMA0_CHICKEN_BITS` es sintácticamente válida | **PROVEN** | Cumple el formato de 3 niveles con 2 puntos |
| `oss300` es un bloque IP declarado para polaris12 | **PROVEN** | `polaris12.asic` línea 8 |
| `mmSDMA0_CHICKEN_BITS` existe en `oss_3_0_0.reg` offset 0x3405 | **PROVEN** | Encontrado directamente en el regdb |
| El parser resuelve la ruta completa hasta el offset del registro | **INFERRED** | Flujo de código claro, pero `umr_scan_asic` no localizado |
| UMR puede leer `polaris12.oss300.mmSDMA0_CHICKEN_BITS` en runtime | **INFERRED** | Requiere ejecución con root, no autorizado |

---

## 6. Estado final y decisión

**Decisión: CLOSED_STATIC** (con nota)

El código fuente upstream de UMR demuestra cómo se resuelve la ruta `polaris12.oss300.mmSDMA0_CHICKEN_BITS`:
1. `main()` descubre el ASIC y carga la base de datos (`get_asic()`).
2. Para `--read polaris12.oss300.mmSDMA0_CHICKEN_BITS`, el parser divide en `asicname="polaris12"`, `ipname="oss300"`, `regname="mmSDMA0_CHICKEN_BITS"`.
3. Valida la sintaxis (2 puntos requeridos).
4. Llama a `umr_scan_asic()` para resolver la ruta completa.
5. El registro se encuentra mediante `umr_find_ip_block()` + `umr_find_reg_data_by_ip_by_instance_with_ip()` con fallback `mm`→`reg`.

La asociación bloque→archivo→registro→offset está completamente verificada:
- `polaris12.asic` declara `oss300 null 0 ip/oss_3_0_0.reg`
- `oss_3_0_0.reg` contiene `mmSDMA0_CHICKEN_BITS 0 0x3405` con 9 subcampos
- El parser acepta la sintaxis de 3 niveles

**Nota:** La función `umr_scan_asic` no fue localizada en el árbol fuente disponible, por lo que no se puede afirmar con certeza absoluta el comportamiento interno final de resolución. Sin embargo, el flujo de código y la documentación de ayuda respaldan que la sintaxis es válida.

**No se afirma que una lectura MMIO funcione.** La verificación dinámica sigue fuera del alcance autorizado (requiere root y acceso al hardware).

---

## 7. Siguiente acción prioritaria (una sola)

**Localizar la definición de `umr_scan_asic`** en el repositorio upstream de UMR (probablemente en `src/app/main.c` bajo una sección que no se pudo leer completa, o en otro archivo del árbol fuente). Si se confirma su implementación, la frontera de procedencia estática queda totalmente cerrada (`CLOSED_STATIC` sin notas). De lo contrario, el estado actual `CLOSED_STATIC` (con nota sobre `umr_scan_asic`) es suficiente para volver al mapa global de RX 550 y seleccionar la siguiente incertidumbre prioritaria.
