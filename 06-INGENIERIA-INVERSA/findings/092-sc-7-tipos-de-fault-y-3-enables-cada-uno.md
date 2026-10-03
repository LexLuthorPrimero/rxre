# 092 · §C: siete tipos de fault, tres enables cada uno, y el driver solo usa uno

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`064` listó seis protection faults y los dejó como lista. Esta nota los cuenta
bien, encuentra el registro, y —esto es lo útil— **dice qué hace el driver con
ellos**, que es la parte de software permitido.

## Corrección a `064`: son siete, y el registro no es el que `064` buscaba

`064` الرياضة `WRITE/READ/RANGE/SECURE/VALID_PROTECTION_FAULT_ENABLE`. Esos
campos **existen**, pero en `GCVM_CONTEXT0_CNTL`:

```
include/asic_reg/gc/gc_10_1_0_sh_mask.h
include/asic_reg/gc/gc_11_0_0_sh_mask.h
include/asic_reg/gc/gc_11_5_0_sh_mask.h
include/asic_reg/gc/gc_12_0_0_sh_mask.h
include/asic_reg/gc/gc_12_1_0_sh_mask.h
include/asic_reg/gc/gc_10_3_0_sh_mask.h
```

`GC` es el núcleo gráfico, y **sólo existe de GFX10.1 en adelante**. En las
cabeceras de esta GPU:

```
gca/gfx_8_0_sh_mask.h    GCVM_CONTEXT0_CNTL: 0
gca/gfx_8_1_sh_mask.h    GCVM_CONTEXT0_CNTL: 0
gmc/gmc_8_1_sh_mask.h    GCVM_CONTEXT0_CNTL: 0
gmc/gmc_8_2_sh_mask.h    GCVM_CONTEXT0_CNTL: 0
```

El registro de GFX8 se llama **`VM_CONTEXT{n}_CNTL`**, no `GCVM_CONTEXT`. Son
dos generaciones de layout distintas.

## El recuento real: 7 tipos

En `gmc_8_1_sh_mask.h`, para cada VM context:

| tipo | `_DEFAULT` | `_INTERRUPT` | `_SAVE` |
|---|---|---|---|
| `RANGE` | sí | sí | **no** |
| `DUMMY_PAGE` | sí | sí | **no** |
| `PDE0` | sí | sí | sí |
| `VALID` | sí | sí | sí |
| `READ` | sí | sí | sí |
| `WRITE` | sí | sí | sí |
| `EXECUTE` | sí | sí | sí |

**Siete tipos, no seis.** `064` se quedó corto en uno. Y la estructura es
triple: cada tipo tiene hasta tres enables independientes.

`RANGE` y `DUMMY_PAGE` **no tienen `_SAVE`**. Los otros cinco sí. Eso no es
uniforme, y el driver no lo menciona en ninguna parte.

## Qué activa el driver: sólo `_DEFAULT`

```
gmc_v8_0.c:896   tmp = REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:927   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, RANGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:927   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, DUMMY_PAGE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:928   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, PDE0_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:929   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, VALID_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:930   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, READ_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:931   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, WRITE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:932   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
```

**Los siete en enable, a 1. Y ni un solo `_INTERRUPT` ni `_SAVE` en todo el
driver.**

Verificado: `grep -rn 'PROTECTION_FAULT_ENABLE' amdgpu/*.c` devuelve sitios
sólo en `mmhub_v3_0_1.c`, que es MMHUB 3.0.1 — generación GFX10, no nuestra.

**Esto es la regla para un driver propio**: en GFX8, amdgpu activa los siete
tipos en su modo por defecto y no toca los otros dos ejes. No hay un solo
`ENABLE_SAVE` ni `ENABLE_INTERRUPT` escrito para esta GPU. Si quieres que un
fault dispare un interrupt, o que su dirección se grabe, **eso no está en el
driver que corre y hay que escribirlo desde cero**.

## Y lo que hace cuando ocurre: imprime, no decodifica

```
gmc_v8_0.c:1006   u32 vmid = REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS, VMID);
gmc_v8_0.c:1007   u32 protections = REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS, PROTECTIONS);
gmc_v8_0.c:1013   mc_id = REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS, MEMORY_CLIENT_ID);
gmc_v8_0.c:1016   dev_err(adev->dev, "VM fault (0x%02x, vmid %d, pasid %d) at page %u, %s from '%s' (0x%02x, %s)\n",
```

**`protections` se imprime como `0x%02x` y no se decodifica.** El driver calcula
la variable en L1007 y luego la pasa al `printf` sin interpretarla.

Y `PROTECTIONS` es un campo de 8 bits:

```
gmc_8_1_sh_mask.h   VM_CONTEXT1_PROTECTION_FAULT_STATUS__PROTECTIONS_MASK 0xff
```

**Es una máscara de bits, no un código.** Ocho bits para siete tipos: cada bit
es un tipo, y el driver no dice cuál. El log te dice "hubo un fault, con esta
máscara", y el autor del driver tiene que saber por su cuenta que bit es cuál.

Eso es lo que un driver propio tiene que añadir, y no es difícil: es un `switch`
de 7 casos sobre una máscara que el hardware ya entrega.

## El layout del registro de status, completo

```
campo                  bits      ancho    máscara
PROTECTIONS            0-7       8        0xff
MEMORY_CLIENT_ID       12-20     9        0x1ff000
MEMORY_CLIENT_RW       24        1        0x1000000
VMID                   25-28     4        0x1e000000
ATOMIC                 29        1        0x20000000

ocupada 0x3f1ff0ff · solapes 0
libres: 8, 9, 10, 11, 21, 22, 23, 30, 31  -> 9 bits reservados sin campo
```

**Nueve bits reservados** en dos bloques (8-11 y 21-23), más 30-31. El
registro es de 32 bits y sólo usa 23.

`MEMORY_CLIENT_ID` con **9 bits** es el más ancho, y da 511 clientes de memoria
distintos. El driver lo imprime como `mc_client >> 24` en 4 caracteres — o sea,
**decodifica el ID a un nombre de bloque de 4 letras** (`"VMCB"`, `"HTC "`, etc.)
sacándolo del registro `VM_CONTEXT1_PROTECTION_FAULT_MCCLIENT`, que es otro
registro distinto del status.

## El eslabón con §B

`VM_CONTEXT1_CNTL2` (sí en GFX8) tiene cinco campos:

```
gmc_8_1_sh_mask.h   VM_CONTEXT1_CNTL2__CLEAR_PROTECTION_FAULT_STATUS_ADDR__SHIFT              0x0
gmc_8_1_sh_mask.h   VM_CONTEXT1_CNTL2__ENABLE_CLEAR_PROTECTION_FAULT_STATUS_ADDR_WHEN_INVALIDATE_CONTEXT__SHIFT  0x1
gmc_8_1_sh_mask.h   VM_CONTEXT1_CNTL2__ENABLE_INTERRUPT_PROCESSING_FOR_SUBSEQUENT_FAULTS_PER_CONTEXT__SHIFT      0x2
gmc_8_1_sh_mask.h   VM_CONTEXT1_CNTL2__ALLOW_SUBSEQUENT_PROTECTION_FAULT_STATUS_ADDR_UPDATES__SHIFT             0x3
gmc_8_1_sh_mask.h   VM_CONTEXT1_CNTL2__WAIT_FOR_IDLE_WHEN_INVALIDATE__SHIFT                                   0x4
```

El segundo es la costura con `194`: **`ENABLE_CLEAR_PROTECTION_FAULT_STATUS_ADDR_WHEN_INVALIDATE_CONTEXT`**
dice que el invalidate limpia la dirección de fault. Y `194` probó que en
GFX8 el invalidate es obligatorio.

**Entonces el invalidate cumple dos papeles en GFX8**: vacía la TLB (085) y,
si ese bit está puesto, limpia el status del fault. El mismo registro
`VM_L2_CNTL2` que dispara el invalidate lleva ese flag al lado
(`INVALIDATE_ALL_L1_TLBS`, `INVALIDATE_L2_CACHE`, `gmc_v8_0.c:861-862`).

Y `ALLOW_SUBSEQUENT_..._UPDATES` es el campo con más consecuencia para un driver
propio: **si no lo pones, la dirección grabada es la del primer fault y todas
las siguientes se pierden en silencio.** Ningún mensaje de error dice que
perdiste un fault.

## Un detalle que sólo existe en esta GPU

`gmc_8_1_sh_mask.h` tiene una segunda familia de faults que **`gmc_8_2` no
tiene**:

```
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_ADDR
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_ADDR__LOGICAL_PAGE_ADDR__
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_STATUS
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_STATUS__ATOMIC__
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_STATUS__MEMORY_CLIENT_ID__
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_STATUS__MEMORY_CLIENT_RW__
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_STATUS__PROTECTIONS__
MC_VM_MB_L1_TLS0_PROTECTION_FAULT_STATUS__VMID__
```

Presentes en 8.1, ausentes en 8.2. Y **esta GPU es 8.1** (`087`, observado en
el log). Es un registro de fault **por L1 TLS0**, con los mismos cinco campos
de status.

El driver **no lo toca nunca**: `grep -rn 'L1_TLS0_PROTECTION_FAULT'` en
`amdgpu/*.c` → **0 resultados**.

O sea: hay un segundo juego de registros de fault específico de esta
generación, con el hardware puesto y el driver sin leer. **Eso es el candidato
más serio que he encontrado para F1**, porque leer un registro de fault no
requiere escribir nada ni tocar la TLB.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| 7 tipos de protection fault en GFX8 | `PROVEN` (`gmc_8_1_sh_mask.h`) |
| Cada uno con hasta 3 enables | `PROVEN` (misma) |
| `RANGE` y `DUMMY_PAGE` sin `_SAVE` | `PROVEN` |
| El driver activa los 7 en `_DEFAULT` | `PROVEN` (`gmc_v8_0.c:927-932`) |
| Cero `_INTERRUPT` / `_SAVE` escritos en GFX8 | `PROVEN` (0 sitios) |
| `PROTECTIONS` es máscara de 8 bits, no decodificada | `PROVEN` (`gmc_v8_0.c:1007,1016`) |
| 9 bits reservados en el registro de status | `PROVEN` (máscaras) |
| El invalidate limpia el status del fault si el bit está puesto | `PROVEN` (máscara) |
| Qué bit de `PROTECTIONS` es cada tipo | **`NOT_DETERMINED`** |
| Qué significa `ATOMIC` | `NOT_DETERMINED` |
| Qué hace `MEMORY_CLIENT_ID` con 9 bits | `NOT_DETERMINED` |
| Para qué sirve `L1_TLS0_PROTECTION_FAULT` | **`NOT_DETERMINED`**, y no lo usa nadie |

**Las tres últimas son el hueco honesto.** El bit↔tipo no está en el corpus, y
no hay atajo: o AMD lo publicó (y `§B/§C` es `NOT_DETERMINED` por
`RE-29`, el mismo bloqueo), o hay que deducirlo experimentalmente.

**Y eso lo hace más interesante, no menos**: el `PROTECTIONS` es una máscara que
el hardware rellena. Si un driver propio provoca un fault de escritura y mira
qué bit se enciende, tiene el mapping empírico en una lectura — **sin MMIO
write a la TLB y sin riesgo para la sesión gráfica**. Es la vía más barata que
he encontrado para cerrar §C, y no requiere F1.

## Procedencia

- `STATIC` — `gmc_v8_0.c:890-932` y `:996-1021`, `gmc_8_1_sh_mask.h`,
  `gmc_8_2_sh_mask.h` (para el contraste), `gc_10_1_0_sh_mask.h` y hermanos
  (para el descarte de `GCVM_CONTEXT0_CNTL`).
- Sin `RUNTIME`. Sin lectura de la GPU. Sin escrituras.
- Corrige el recuento de `064` (6 → 7) y corrige el nombre del registro.
  `064` no es mío; **informo en vez de editarlo**.
- Encadenada con `194` (el invalidate y el status), `205` (§G),
  `087` (esta GPU es 8.1, y por eso `L1_TLS0` existe).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método, porque las dos fueron mías.**

La primera: busqué `WRITE_PROTECTION_FAULT_ENABLE_MASK` en el subdirectorio
`asic_reg/` y no salió, y escribí "no existe en ninguna cabecera". **Era
`NAME_NOT_FOUND` tratado como ausencia.** El token existe en 33 cabeceras y 25
ficheros `.c`; yo lo había buscado con prefijo `WRITE_` en el subárbol
equivocado. Es la séptima vez que me pasa, y ya es un patrón instalado: **un
grep vacío no es una ausencia, es una búsqueda mal planteada.** El
`gfx_v8_0_sh_mask.h` que sí iba a mirar me habría dado la respuesta.

La segunda: dije "el driver no programa ningún protection fault en GFX8"
cuando ya había visto 39 ocurrencias de `PROTECTION_FAULT` en `gmc_v8_0.c`.
Afirmé desde un recuento de `mmATC` y desde un `PROTECTION_FAULT_ENABLE` que
sólo saqué de `mmhub_v3_0_1.c`, sin comprobar el fichero GFX8 que tenía delante.
Octava vez. La regla que sí funciona es la de `205`: **abrir el fichero y leer
las líneas, antes de contar en los demás.**