# 099 · §C OBSERVADO: el PRT se disparó de verdad en esta máquina y enmascaró el fault de PDE0

```
CLASSIFICATION=DOCUMENTATION · TRACK=RUNTIME (READ_ONLY)
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

`082` y `083` estimaron que **PRT puede activarse en GFX8 y que nadie lo
atiende**. Eso era una posibilidad de lectura.

En esta máquina **se activó**, y la respuesta del driver está en el log de
arranque. No es mío: es de las 00:26:43, y mi trabajo empezó sobre las 01:2x.

```
oct 02 00:26:43 kalm kernel: amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!
```

El arranque de la GPU es a las 00:10:26, así que ocurrió **16 minutos y 17
segundos después del arranque**.

## Qué hace cuando se dispara

```
gmc_v8_0.c:770   if (enable && !adev->gmc.prt_warning) {
gmc_v8_0.c:771       dev_warn(adev->dev, "Disabling VM faults because of PRT request!\n");
gmc_v8_0.c:772       adev->gmc.prt_warning = true;
```

Y a continuación escribe **siete campos** de `VM_PRT_CNTL`, todos a `enable`:

```
gmc_v8_0.c:776   CB_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS      = 1
gmc_v8_0.c:778   CB_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS     = 1
gmc_v8_0.c:780   TC_DISABLE_READ_FAULT_ON_UNMAPPED_ACCESS      = 1
gmc_v8_0.c:782   TC_DISABLE_WRITE_FAULT_ON_UNMAPPED_ACCESS     = 1
gmc_v8_0.c:784   L2_CACHE_STORE_INVALID_ENTRIES                = 1
gmc_v8_0.c:786   L1_TLB_STORE_INVALID_ENTRIES                 = 1
gmc_v8_0.c:788   MASK_PDE0_FAULT                               = 1
```

**Siete "disable".** El driver no atiende la página: **desactiva el aviso**.

`CB` y `TC` son los dos cachés de datos (la misma división CE/TC de `095`), así
que un acceso a memoria no mapeada **no falla en ninguno de los dos**, en lectura
ni en escritura. Sin excepción, sin aviso por acceso.

## Y esto conecta directamente con `092`

`092` catalogó siete tipos de protection fault, y el séptimo en la lista de
`gmc_v8_0.c:927-932` es:

```
gmc_v8_0.c:928   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PDE0_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
```

Y el camino de PRT escribe:

```
gmc_v8_0.c:788   MASK_PDE0_FAULT = enable;
```

**El camino de PRT enmascara exactamente el tipo de fault que `092` Enabling
habilitó.** Es el mismo campo, dice lo contrario, y lo dice después.

**Secuencia completa en esta máquina:**

```
00:10:30  gmc_v8_0.c:927-932   el driver habilita los 7 tipos de fault, PDE0 incluido
00:26:43  alguien mapea con AMDGPU_VM_PAGE_PRT
00:26:43  gmc_v8_0_set_prt(adev, true)
00:26:43  MASK_PDE0_FAULT = 1, y los otros 6 disable también
00:26:43  dev_warn, UNA vez
```

**Para un driver propio esto es el hallazgo más accionable de la tanda**: si
implementas PRT como lo hace amdgpu, no estás implementando una forma de
atender páginas faltantes. Estás **desactivando siete mecanismos de error**,
incluido el aviso de PDE0. Un driver que quiera realmente atender la página
tiene que hacerlo por otro camino, porque el registro que AMD eligió para
PRT es precisamente el de silenciar faults.

## Es un contador de referencias, no un estado

```
amdgpu_vm.c:1437   enable = !!atomic_read(&adev->vm_manager.num_prt_users)
amdgpu_vm.c:1452   if (atomic_inc_return(&num_prt_users) == 1)  -> habilita PRT
amdgpu_vm.c:1463   if (atomic_dec_return(&num_prt_users) == 0)  -> deshabilita PRT
amdgpu_vm.c:1475   amdgpu_vm_prt_put(cb->adev)   (al señalarse el fence)
```

**PRT está activo mientras haya ≥1 usuario, y se desactiva cuando el último
suelta al señalarse su fence.** No es un estado permanente: es un préstamo.

Y los cuatro sitios que toman referencia están **todos** condicionados:

```
amdgpu_vm.c:1809   if (mapping->flags & AMDGPU_VM_PAGE_PRT)   -> prt_get
amdgpu_vm.c:2117   if (before->flags    & AMDGPU_VM_PAGE_PRT) -> prt_get
amdgpu_vm.c:2132   if (after->flags     & AMDGPU_VM_PAGE_PRT) -> prt_get
amdgpu_vm.c:1546   amdgpu_vm_prt_fini()                         -> prt_get
```

**PRT sólo se activa si un proceso mapea memoria con `AMDGPU_VM_PAGE_PRT`.** Es
una petición explícita de userspace, no algo que el hardware imponga.

## Y el aviso sale UNA sola vez, en toda la vida del proceso

```
gmc_v8_0.c:770   if (enable && !adev->gmc.prt_warning)
```

**`prt_warning` es un flag permanente, nunca se limpia.** El `dev_warn` sólo
imprime la primera vez. Verificado: el log de este arranque tiene **una** línea
PRT, y es la de las 00:26:43.

**Un segundo evento de PRT no produce ningún mensaje.** Si el estado cambió a
partir de ese momento, no hay rastro en el log. Eso es exactamente el tipo de
cambio de estado silencioso que hace un resultado experimental no reproducible.

## El problema: no hay forma de saber si PRT está activo ahora

Busqué en todo lo observable:

| dónde | qué |
|---|---|
| `debugfs` de la GPU | `amdgpu_vm_info`, `amdgpu_fence_info`, `amdgpu_evict_gtt`, `amdgpu_gtt_mm` — ninguno expone PRT |
| `sysfs` | nada con `prt` |
| `journalctl` | sólo el aviso, una vez, y nunca se limpia |
| `/proc` | nada |

**`num_prt_users` y `prt_warning` viven sólo en memoria del driver, y no hay
ningún observable que los exponga.** No es `NOT_OBSERVED` por falta de mirada:
es que la ruta de exposición no existe en este kernel.

**Y esto es un confoundidor declarado y no controlable para cualquier
experimento de faults.** Si PRT está activo, los faults que un experimento
intenta provocar **no se producen**, y el resultado sería "no hay fault" sin
que eso signifique que el hardware no los genera.

**Es el confoundidor que más pesa de los que he encontrado**, porque no se puede
neutralizar desde fuera: ni con parámetros de módulo, ni con debugfs, ni con
sysfs.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| PRT se disparó en esta máquina | `OBSERVED` (log, 00:26:43) |
| Ocurrió 16 min después del arranque | `OBSERVED` |
| PRT desactiva 7 mecanismos, incluido `MASK_PDE0_FAULT` | `PROVEN` (`gmc_v8_0.c:776-790`) |
| PRT contradice el enable de `PDE0_..._FAULT_DEFAULT` | `PROVEN_DERIVED` |
| PRT es un contador de referencias | `PROVEN` (`amdgpu_vm.c:1437-1464`) |
| Sólo se activa con `AMDGPU_VM_PAGE_PRT` | `PROVEN` (4 sitios) |
| El aviso se imprime una sola vez | `PROVEN` (`gmc_v8_0.c:770`) |
| **Si PRT está activo ahora mismo** | **`NOT_DETERMINED`, sin observable** |
| Qué proceso lo disparó | `NOT_DETERMINED` |
| Por qué accedió a memoria no mapeada | `NOT_DETERMINED` |
| Si PRT estaba activo durante las mediciones de `097`/`098` | **`NOT_DETERMINED`** |

**La última fila es la incómoda.** `097` y `098` se hicieron con el sistema en
este estado, y no puedo afirmar que PRT no estuviera enmascarando faults durante
esos experimentos.

**Pero no afecta a sus conclusiones**, y hay que dizer por qué: `097` y `098`
miden el mecanismo de **fence** (`DATA_SEL`, deltas de secuencia, retraso del
host), que va por otra vía —escritura DMA a la página de fence y lectura de
memoria del sistema—, **no por faults de VM**. PRT no toca ese camino. Los dos
hallazgos siguen válidos.

**Aun así lo declaro**, porque `AGENTS.md` exige confounder en toda medición y
porque no saber si un confoundidor estaba activo es información, no un detalle.

## Procedencia

- `RUNTIME` — `journalctl -k -b`, sólo lectura. Sin MMIO write, sin TLB, sin
  módulos, sin parámetros.
- `STATIC` — `gmc_v8_0.c:761-800` y `:1738` y `:927-932`, `amdgpu_vm.c:1426-1499`
  y `:1809` y `:2117` y `:2132`, y `AM_DRV.c` para la búsqueda de observables.
- Encadenada con `092` (los 7 tipos de fault y `PDE0`), `083`/`082` (PRT
  activable y sin atender), `095` (CE y TC, los dos cachés que PRT silencia),
  `098` (la página de fence y su layout).
- Corrige el estado de `082`/`083`: PRT no es una posibilidad de lectura, ya
  ocurrió en esta máquina.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, y es sobre cómo cierro los trabajos.**

Iba a cerrar `098` con un control de "no hay faults nuevos en el log", y ese
control me devolvió **1 coincidencia** — que era un hecho real,viejo y
relevante que no buscaba. Lo habitual habría sido filtrarlo como "ya estaba" y
publicar.

**Un control que devuelve 1 hay que abrirlo.** Si un filtro de coincidencias
devuelve algo, ese algo es un dato hasta que se demuestre lo contrario, y yo no
tenía ninguna razón para suponer que el PRT estaba resuelto. Resultó ser el
hallazgo más accionable de los tres últimos.

**Y una observación sobre el repo, que no es mía:** `scopeguard.py --findings`
devuelve ahora `NUMERO LIBRE = None`. Hay 159 ficheros en `findings/` y el
número más alto en uso es 098. La herramienta no encuentra hueco y dice `None`.
Es la señal de que la asignación de números por dos sesiones independientes ha
llegado al límite de lo que esa heurística puede resolver, y `num_collision.py`
sigue reportando 550 referencias ambiguas. Lo informo; no lo toco.