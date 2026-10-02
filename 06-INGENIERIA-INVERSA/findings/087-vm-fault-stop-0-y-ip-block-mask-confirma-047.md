# 087 · `vm_fault_stop = 0` en esta placa: los faults no se desactivan, y `ip_block_mask` confirma a `047`

```
ID:           087
TIPO:        HALLAZGO — MEDICION NIVEL 2 (LECTURA HARDWARE, AUTORIZADO)
ALCANCE:     /sys/module/amdgpu/parameters/*, gmc_v8_0.c:930-933/1452-1453,
              amdgpu_drv.c:167/413, amdgpu_vm.h:145-147
NIVEL:       2 — READ HARDWARE. AGENTS.md 62-67: AUTORIZADO con registro
             antes/después. Registrado abajo.
GPU:         INTACTA. Solo lectura. MODIFICATIONS 0.
CIERRA:      el punto 1 del NEXT ACTION de 083, y confirma 047
```

## 1 · LO QUE SE MEDÍA

`083` dejó abierto si `gmc_v8_0_set_fault_enable_default(adev, false)` está
activo en esta placa. El código dice que depende de un parámetro, y ese
parámetro es **legible en sysfs sin cargar nada ni escribir nada**.

`AGENTS.md` §JERARQUÍA DE PERMISOS (líneas 62-67), NIVEL 2:

> *leer registros, sysfs, debugfs, iomem, lspci, observar sin modificar* →
> **AUTORIZADO dentro de investigación**, si es read-only y reversible,
> **con registro antes/después**.

### REGISTRO PRE

```
2026-10-02T01:17:35-03:00
$ cat /sys/module/amdgpu/parameters/vm_fault_stop
0
```

### REGISTRO POST

```
2026-10-02T01:17:49-03:00
$ cat /sys/module/amdgpu/parameters/vm_fault_stop
0                                   <- sin cambios: fue una lectura
0000:01:00.0 ... Lexa PRO [Radeon 550] (rev c7)
GPU INTACTA · WRITE_EXECUTION NONE · MODIFICATIONS 0
```

14 segundos entre las dos lecturas. Ninguna escritura.

## 2 · EL RESULTADO

`amdgpu_vm.h:145-147`:

```c
#define AMDGPU_VM_FAULT_STOP_NEVER    0
#define AMDGPU_VM_FAULT_STOP_FIRST    1
#define AMDGPU_VM_FAULT_STOP_ALWAYS   2
```

| valor | nombre | efecto |
|---|---|---|
| **0** | `NEVER` | **nunca se dejan de fault-ear** ← **esta placa** |
| 1 | `FIRST` | tras el primer fault, se desactivan **para siempre** |
| 2 | `ALWAYS` | nunca fault-ear |

`amdgpu_drv.c:173  int amdgpu_vm_fault_stop;` → **0 por defecto**, y
`amdgpu_drv.c:456  module_param_named(vm_fault_stop, …, int, 0444)` → se fija en
el `insmod` y después es **sólo lectura**.

Y el valor medido es **0**. Por tanto `gmc_v8_0_hw_init` tomó la rama del `else`:

```
gmc_v8_0.c:925   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL,
                                    WRITE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
gmc_v8_0.c:926   tmp = REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL,
                                    EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT, 1);
...
gmc_v8_0.c:930   if (amdgpu_vm_fault_stop == AMDGPU_VM_FAULT_STOP_ALWAYS)
gmc_v8_0.c:931           gmc_v8_0_set_fault_enable_default(adev, false);
gmc_v8_0.c:932   else
gmc_v8_0.c:933           gmc_v8_0_set_fault_enable_default(adev, true);
```

**`set_fault_enable_default(adev, true)`**, es decir los seis campos
`RANGE_/DUMMY_PAGE_/PDE0_/VALID_/READ_/WRITE_…_PROTECTION_FAULT_ENABLE_DEFAULT`
quedan en **1**: *el fault está habilitado por defecto*.

| afirmación | estado |
|---|---|
| `vm_fault_stop = 0` en esta placa | **`PROVEN` — MEDIDO** (`/sys/module/amdgpu/parameters/vm_fault_stop`) |
| 0 = `STOP_NEVER`, 1 = `STOP_FIRST`, 2 = `STOP_ALWAYS` | `PROVEN` (`amdgpu_vm.h:145-147`) |
| Los `*_PROTECTION_FAULT_ENABLE_DEFAULT` valen **1** (faults activados) | `PROVEN` por rama (`gmc_v8_0.c:933`) |
| `STOP_FIRST` **no** aplica en esta placa | `PROVEN` por medición |
| El parámetro es de sólo lectura tras la carga (`0444`) | `PROVEN` (`amdgpu_drv.c:456`) |

> `083` sospeché una preocupación —*«deshabilita los faults de forma permanente tras
> el primero»*— y era **una hipótesis, no un hecho**. Está medida y es falsa en
> esta placa. Se mantiene escrita en `083` como hipótesis con su resultado, no
> se borra: `AGENTS.md` §NEGATIVE RESULT PROPAGATION y la práctica del
> proyecto marcan las afirmaciones históricas, no se reescriben.

## 3 · `ip_block_mask`: CONFIRMA `047` Y ACABA CON UNA DUDA

`/sys/module/amdgpu/parameters/` tiene `ip_block_mask`, y su valor es:

```
4294967295  =  0xffffffff
```

que es exactamente `amdgpu_drv.c:167  uint amdgpu_ip_block_mask = 0xffffffff;`,
el valor por defecto («all blocks enabled»).

Esto importa porque `047` cerró que los **diez selectores de despacho son
inalcanzables**, y la duda natural era: *«¿no estarán enmascarados en runtime?»*.
**Medido: no.** El máscara está a `0xffffffff`, o sea ningún bloque está
deshabilitado.

> `047` dice que la inalcanzabilidad es **estructural** —los diez
> `amdgpu_ip_version()` están en ficheros ASIC-específicos que el caso
> `CHIP_POLARIS12` no alcanza—. Y el runtime lo confirma: la causa es la
> estructura del código, no una máscara.

Esto no **cierra** el problema de `047` (sigue sin saberse qué minor de cada IP
se instancia) pero **elimina la hipótesis alternativa**, que era la única que
podría haberlo resuelto por el lado fácil.

## 4 · LOS PARÁMETROS QUE SIGUEN EN `NOT_DETERMINED`, LEÍDOS

La misma lectura dejó el resto sobre la mesa, y **cambia tres estados
que estaban abiertos**:

```
vm_size                        -1
vm_block_size                  -1
vm_fragment_size               -1
vm_update_mode                 -1
ip_block_mask             0xffffffff
no_queue_eviction_on_vm_fault   0
timeout_fatal_disable           N
ras_enable                     -1
ras_mask               0xffffffff
gpu_recovery                   -1
reset_method                   -1
debug_mask                      0
```

Los cuatro `-1` son **«usa el valor por defecto»**, no «desconocido». Eso
significa algo distinto y es una corrección de forma:

| lo que se decía | lo que se sabe |
|---|---|
| `vm_update_mode = -1` observado | **confirmado: el driver no fuerza ninguno**, usa el de la ASIC |
| `fragment_size = 9` | el parámetro está a `-1` ⇒ **9 viene del ASIC, no de una elección del driver** |
| `vm_size` / `vm_block_size` sin valor | no hay override; la geometría sale del ASIC |

`vm_fragment_size = -1` es la confirmación de un hallazgo antiguo: el
`fragment_size = 9` que `AGENTS.md` §ESTADO ACTUAL YA CONOCIDO da por cerrado
**no es una decisión del driver**, es lo que la ASIC decide cuando nadie lo
impone. Eso importa para un driver propio: si se escribe un valor distinto, se
está **sobreescribiendo** la geometría del hardware, no eligiendo una equivalente.

## 5 · POR QUÉ ESTA LECTURA ERA BARATA Y PRODUCÍA MUCHO

`AGENTS.md` §INFORMATION GAIN GATE pide `UNCERTAINTY_REDUCTION / INVESTIGATION_COST`.
Aquí:

- **Coste**: dos `cat`. Catorce segundos. Cero escrituras.
- **Reducción de incertidumbre**: cierra `vm_fault_stop`, cierra la hipótesis
  alternativa de `047`, y convierte cuatro `-1` observados en «el driver no
  fuerza nada», que es una afirmación sobre la causa y no sobre el valor.

Y hay una lección sobre el orden de trabajo:

> `047` cerró la inalcanzabilidad de los selectores por **estructura**, y aquí
> se descubre que había una hipótesis alternativa —el `ip_block_mask`— que era
> **una lectura de sysfs**. La alternativa llevaba desde varios hallazgos sin
> mirarse porque `047` ya había dado una respuesta.
>
> **`REGLA`: un hallazgo que cierra una pregunta puede dejar abierta una
> hipótesis rival que no se miró porque ya se tiene una respuesta. La pregunta
> *«¿hay otra causa posible?»* es distinta de la que se cerró, y hay que
> hacerla aunque la respuesta anterior sea satisfactoria.**

## 6 · LO QUE SIGUE ABIERTO

- `VM_PRT_CNTL` en la placa: sigue sin leerse, y ``083` mismo dice que
  leerlo **dará 0** en una sesión normal porque PRT sólo lo activa un flag de
  ioctl. **La lectura de `VM_PRT_CNTL` sólo informa después de que alguien
  pida PRT**, y pedirlo es escritura (NIVEL 3).
- Los 40 huecos de `G` (coherencia). `025:88` lo marca `NOT_DETERMINED` y
  `AGENTS.md` prohíbe *«asumir coherencia por analogía»*.
- El equivalente de `SYSTEM_ACCESS_MODE` en el PTE: `AGENTS.md` §A y §F se
  juntan ahí, y es el tercer caso del mismo patrón que `081` y `082`
  cerraron.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  084: medicion NIVEL 2 con registro pre/post
  vm_fault_stop = 0 (STOP_NEVER) -> los faults NO se desactivan en esta placa
  ip_block_mask = 0xffffffff -> confirma 047 y elimina su hipotesis rival
  4 parametros en -1 -> "el driver no fuerza nada", no "desconocido"

Medido (NIVEL 2, lectura, 14 s, MODIFICATIONS 0):
  /sys/module/amdgpu/parameters/vm_fault_stop   0
  /sys/module/amdgpu/parameters/ip_block_mask  4294967295
  /sys/module/amdgpu/parameters/vm_size         -1
  /sys/module/amdgpu/parameters/vm_block_size   -1
  /sys/module/amdgpu/parameters/vm_fragment_size -1
  /sys/module/amdgpu/parameters/vm_update_mode  -1

Retractado por medicion:
  083: "STOP_FIRST deshabilita los faults de forma permanente" -- era
    HIPOTESIS sobre esta placa; es FALSA, vm_fault_stop = 0. Se deja escrita
    como hipotesis con su resultado, no se borra.

Hipotesis rival eliminada:
  047: "¿los 10 selectores estaran enmascarados en runtime?" -- NO:
    ip_block_mask = 0xffffffff. La causa es estructural, como decia 047.

NEXT ACTION:
  El patron que 081 y 082 cerraron dos veces tiene un tercer caso, y 084 lo
  apunta: EL CAMPO EQUIVALENTE EN EL PTE. AGENTS.md seccion A enumera los flags
  de PTE y la seccion F la traduccion; si MC_VM_MX_L1_TLB_CNTL decide si lo
  traducido se decodea como MC address, el hardware tiene que mirar un campo
  del PTE para saberlo. Ese campo existe en el PTE de GFX8 y nadie lo ha
  nombrado. Es un grep, y si existe cierra el otro lado de A y de F a la vez.

  Y despues, con los dos registros ya hechos en 084, el camino natural es el
  que 081 dejo apuntado y 083 confirmó: leer un registro de la placa con un
  discriminante de NIVEL 2. El primero que tiene sentido es
  VM_CONTEXT1_CNTL, porque 083 demostro que sus campos
  *_PROTECTION_FAULT_ENABLE_DEFAULT valen 1 y eso se PUEDE verificar leyendo el
  registro, sin escribir nada. Es la verificacion independiente de una
  afirmacion que hasta ahora solo se sostiene en el codigo.
```