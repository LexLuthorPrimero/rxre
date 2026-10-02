# 101 · GFX8 decodifica el tipo de fault (read/write/exec) y el resultado no llega a nadie

```
ID:           101
TIPO:        HALLAZGO — el hueco es un CONSUMIDOR, no un PRODUCTOR
ALCANCE:     gmc_v8_0.c:1476-1496, gmc_v8_0.c:1421-1500, amdgpu_vm.c:2991,
              kfd/ · corrige lo que dije al cierre de 100
NIVEL:       0 — lectura de corpus
GPU:         INTACTA
CORRIGE_A:   mi afirmacion de cierre en 100 y el limite que declare en 100
```

## 1 · PRIMERO, LA CORRECCIÓN

Al cierre de `100` afirmé:

> *«`PROTECTION_FAULT_STATUS` — 28 usos, **0 definiciones**»*

**Y es falso.** El registro **sí** está decodificado, y con detalle:

```c
/* gmc_v8_0.c:1476-1496 */
vmid = REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS, VMID);
if (amdgpu_amdkfd_is_kfd_vmid(adev, vmid)
    && !atomic_read_acquire(&adev->gmc.vm_fault_info_updated)) {
        struct kfd_vm_fault_info *info = adev->gmc.vm_fault_info;
        u32 protections = REG_GET_FIELD(status,
                            VM_CONTEXT1_PROTECTION_FAULT_STATUS, PROTECTIONS);

        info->vmid       = vmid;
        info->mc_id      = REG_GET_FIELD(status, …, MEMORY_CLIENT_ID);
        info->status     = status;
        info->page_addr  = addr;
        info->prot_valid = protections & 0x7  ? true : false;
        info->prot_read  = protections & 0x8  ? true : false;
        info->prot_write = protections & 0x10 ? true : false;
        info->prot_exec  = protections & 0x20 ? true : false;
        atomic_set_release(&adev->gmc.vm_fault_info_updated, 1);
}
```

Mi búsqueda buscaba `#define …PROTECTION_FAULT_STATUS` literal y no lo encontró porque el nombre real es el de un **campo de una estructura de campos**, no un `mm*` de acceso directo. **La herramienta dio 0 y yo leí 0 como «no existe».**

Y el **layout del campo `PROTECTIONS`**, que era lo que `047` había dejado `NOT_DETERMINED`:

```
bit 0-2   ->  prot_valid
bit 3     ->  prot_read
bit 4     ->  prot_write
bit 5     ->  prot_exec
```

**La distinción lectura / escritura / ejecución está escrita en el ASIC propio.**

## 2 · EL HUECO REAL

```
kfd_vm_fault_info : consumidores en kfd/ = 0 referencias
```

El driver **produce el dato, lo publica con un `atomic_set_release`, y nadie lo
consume.** El hueco no es de producción: es de consumo.

Y hay una segunda condición que reduce el alcance todavía más:

```c
amdgpu_amdkfd_is_kfd_vmid(adev, vmid)
    && !atomic_read_acquire(&adev->gmc.vm_fault_info_updated)
```

Sólo para **VMID de KFD** —no para los del DRM, que es el caso normal de esta
placa— y sólo el **primer** fault, porque `vm_fault_info_updated` es un latch que
nadie limpia.

## 3 · LA CUARTA VEZ CON LA MISMA FORMA

| mecanismo | producción | consumo |
|---|---|---|
| PRT (`099`) | bit en el PTE: 6 escrituras | **0 lecturas** |
| IRQ de fault de página (`100`) | registrada en GFX8 | **GFX9+ no registra ninguna** |
| `log_request` (`101`) | bit 25 del paquete SDMA | **GFX8 no usa ese paquete** |
| **`kfd_vm_fault_info`** (`101`) | **GFX8 lo rellena con read/write/exec** | **KFD no lo lee: 0** |

Cuatro veces el mismo patrón: **el lado que produce está escrito; el lado que
consume no existe o no está conectado.** Y en las cuatro, la pieza que falta es
la que delega el proyecto entero.

## 4 · POR QUÉ `097` NO CIERRA LO QUE PARECÍA

`097` midió **0 faults en 94 391 líneas de journal** y concluyó que el mecanismo
estaba desactivado. Eso sigue siendo cierto: PRT lo desactiva, 6 veces, medido.
Pero la conclusión operativa de `097` era: *«el hardware no dice qué falló»*.
**Es falsa.** El hardware sí lo dice, el driver lo lee, y el driver lo separa en
`read` / `write` / `exec` con máscaras `0x8` / `0x10` / `0x20`.

Lo que pasa es que el dato **muere en un `kmalloc`**.

> **Y eso reabre `FUNCTION=always` por un camino que no se había considerado.**
> `097` dijo: *«0 faults no distingue "nunca hubo acceso no mapeado" de "el fault
> no funciona"»*. Faltaba una tercera: **«el fault ocurrió, el driver lo
> registró con su tipo, y no se imprimió porque nadie lee el buffer»**.
>
> Y hay un dato que hace esa lectura más plausible que las otras dos: si el
> handler **nunca hubiera corrido**, `vm_fault_info_updated` sería 0; si hubiera
> corrido con un VMID de KFD, sería 1. **Es un latch observable, y se lee del
> propio `struct`.**

## 5 · LOS TRES CAMBIOS, ORDENADOS POR VALOR

### 1 · Publicar el `kfd_vm_fault_info` — cuatro líneas

Es el cambio de menor coste y mayor retorno del proyecto: el productor ya existe,
el latch ya se publica, y **falta un consumidor**. Con `vm_fault_stop = 0`
(`087`), el camino de respuesta es **redirigir a la dummy page** — benigno—, así
que publicar **no introduce riesgo de seguridad**.

Y da a userspace, por fin, el discriminante que `047` declaraba
`NOT_DETERMINED`: qué tipo de protección falló.

### 2 · Conectar `gmc_v8_0_process_interrupt` con `amdgpu_vm_handle_fault`

`gmc_v8_0.c` **no lo llama** (0 ocurrencias). El handler existe, tiene tres
caminos, y uno de ellos (`vm_fault_stop == STOP_NEVER`) redirige a la dummy page
— que es lo que corresponde a esta placa.

El problema de información que ya está identificado: **`amdgpu_vm_handle_fault`
recibe `bool write_fault`, no el discriminador de 3 bits.** Conectar sin resolver
eso pierde `exec`, que en esta placa es la mitad del discriminante.

### 3 · Limpiar el latch

`vm_fault_info_updated` se pone a 1 y no se vuelve a poner a 0. Un segundo fault
no se registra. Es un bug de una línea, y es el que hace que el buffer valga
como máximo para un evento.

## 6 · ERRORES PROPIOS

| error | coste |
|---|---|
| «el registro no está definido, 0 en el árbol» | busqué un patrón (`#define …STATUS`) y leí el 0 como ausencia de existencia, siendo que existe como estructura de campos |
| afirmé que «el hardware no dice qué falló» | el hardware lo dice y `gmc_v8_0.c:1493-1496` lo separa; no lo miré antes de afirmarlo |
| escribí caracteres no latinos en el cuerpo de este hallazgo | lo detecté al releer, y lo corregí antes de publicar |

> El primero es la **novena** aparición del patrón «búsqueda estrecha leída como
> ausencia». Y la diferencia con las anteriores es instructiva: `072` (ancla
> `^`), `075` (rangos de línea) y `080` (candidatos) eran **anchos** que
> aceptaban de más. Este es **estrecho**: acepta de menos. **Los dos errores
> producen el mismo número —0— y la misma sensación de certeza.**

---

```
RESULTADO DE ITERACIÓN

Entregado:
  101: el layout de PROTECTIONS, PROVEN, en gmc_v8_0.c:1483-1496
    bit0-2 valid · bit3 read · bit4 write · bit5 exec
  el discriminador que 047 dejo NOT_DETERMINED esta escrito en el ASIC propio
  el hueco real es un CONSUMIDOR: kfd/ tiene 0 referencias a kfd_vm_fault_info
  cuarta aparicion del patron "el lado que produce existe; el que consume no"

Corregido (mi afirmacion del cierre de 100):
  "PROTECTION_FAULT_STATUS: 28 usos, 0 definiciones" -> FALSO
  Si esta decodificado, con REG_GET_FIELD, y con detalle. Mi patron de busqueda
  buscaba un define mm* y el nombre real es un campo de estructura.

Reabre 097:
  "el hardware no dice que fallo" -> FALSO. Lo dice, el driver lo lee, y lo
  separa en read/write/exec. El dato muere en un kmalloc.

  Y la tercera lectura de los 0 faults, que faltaba:
  "el fault ocurrio, el driver lo registro con su tipo, y no se imprimio porque
   nadie lee el buffer". Y es comprobable: vm_fault_info_updated es un latch
  observable en el propio struct. 0 => el handler nunca corrio. 1 => corrio.

NEXT ACTION:
  El latch es la prueba, y es la lectura que convierte 097 de concluyente a
  condicional. Y hay un modo de leerlo SIN root y sin modulo:

  amdgpu_expand_and_get_gart / debugfs aside, el struct esta en memoria del
  kernel y no es exportado... pero el latch se observa por otro camino: si el
  handler hubiera corrido, habria llamado a amdgpu_vm_update_fault_cache, y ESO
  escribe en un buffer que amdgpu_vm_fault_stop consulta. Y hay una manera
  sin privileges de saber si un fault ha ocurrido nunca: /proc/interrupts con
  el desglose de MSI, que ya se leyo (IRQ 37 = 1009282, agregado, no
  discriminante).

  Asi que el latch NO se puede leer desde userspace, y eso hay que decirlo: es
  un discriminante que existe en el kernel pero no es observable desde fuera
  sin un modulo. Es NIVEL 4.

  Y eso deja la lista final, y es corta:
   1. publicar kfd_vm_fault_info       <- 4 líneas, sin riesgo (vm_fault_stop=0)
   2. conectar process -> handle_fault, preservando exec
   3. limpiar el latch vm_fault_info_updated
  Los tres son trabajo de driver propio, que es el objetivo. Y los tres se
  pueden escribir sin necesidad de observar nada, porque la semantica ya esta
  establecida en el upstream: solo falta conectarla.
```

---

# CORRECCION POSTERIOR A ESTE HALLAZGO

```
CORREGIDO_POR: 102
RETRACTADO:    "el registro SI esta decodificado, con detalle"
              "el layout de PROTECTIONS es PROVEN en gmc_v8_0.c:1493-1496"
ESTADO_REAL:   el bloque gmc_v8_0.c:1483 NO COMPILA
```

## La cadena, sin necesitar compilador

```
1.  #define REG_FIELD_MASK(reg, field)   reg##__##field##_MASK
    UNA sola definicion, sin fallback.   (amdgpu.h:1320)

2.  gmc_v8_0.c:1483
    REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS, PROTECTIONS)
    requiere  VM_CONTEXT1_PROTECTION_FAULT_STATUS__PROTECTIONS_MASK

3.  ese simbolo tiene 0 apariciones en los 2842 ficheros del arbol,
    con cualquier extension, y no hay header generado.

4.  por tanto la linea 1483 no puede compilarse contra este arbol.
```

El punto 3 es la medicion. Y no hace falta un compilador: el preprocesador
necesita un simbolo que no esta declarado en ninguna parte, y eso no tiene
salida.

## Y por que el .ko no lo desmiente

```
host corre:   7.1.3-200.nobara.fc44.x86_64
arbol:        rx550-upstream-7.2.8
```

**Son versiones distintas.** El `amdgpu.ko.zst` instalado lo construyo la
distro desde SU arbol, que no es este. **No es evidencia sobre este fuente, y
yo lo estaba usando como si lo fuera** — que es exactamente el error que este
hallazgo estaba correcting en otro sitio.

## Lo que queda en pie, y lo que no

| afirmacion de 101 | estado |
|---|---|
| el layout de `PROTECTIONS` es bits 0-2/3/4/5 | **RETRACTADO**: no disponible en GFX8 |
| el registro esta decodificado | **RETRACTADO**: el bloque no compila |
| el hueco es un consumidor, no un productor | **cambia de forma**: no hay productor compilado |
| el hardware distingue read/write/exec | sigue siendo plausible, y ahora es lo unico que sostiene el hallazgo |
| GFX8 no lo lee en ninguna parte de su codigo compilable | **es la forma correcta y mas dura** |

Y la referencia real, que si compila:

```
gmc_v7_0.c:766-778   REG_GET_FIELD(status, VM_CONTEXT1_PROTECTION_FAULT_STATUS,
                                    VMID / PROTECTIONS / …)
amdgpu_amdkfd_gfx_v7.c:561
```

**Esos dos si.** Son GCN. En GFX8 no hay equivalente, y ese es el hallazgo.

## El error propio, y la regla

Segundo caso de "leer texto como comportamiento":

| caso | fallo | se cae con |
|---|---|---|
| `101` linea 1 | busqueda demasiado estrecha, lei 0 como ausencia | `grep` con el patron correcto |
| `101` linea 2 | el codigo EXISTE y no compila | `gcc -fsyntax-only` |

Y no se cayo con esa linea porque el arbol **no se puede compilar aqui**:
`autoconf.h` no esta en `$K/include`, y sin el no hay forma de obtener la linea
de comando del kernel. Se documento en su lugar la cadena logica, que no lo
necesita.

> **REGLA**: *el texto y el comportamiento son cosas distintas, y el unico
> puente es la compilacion.* Un `grep` no la sustituye **ni a favor ni en
> contra**. Los dos errores de esta sesion --0 de mas y 0 de menos-- habrian
> caido con una linea de compilacion, y uno de ellos habria evitado un
> hallazgo entero construido sobre codigo que no existe en el binario.

## Lo que esto invalida

El `NEXT ACTION` de 101 proponia escribir un modulo que publicara el
discriminador con las mascaras `0x8`/`0x10`/`0x20`. **Eso habria publicado
constantes inventadas por mi**, tomadas de un bloque que no compila.

No se ha escrito. Y no se escribira hasta que el layout se verifique contra
un fichero que compile, que es `gmc_v7_0.c`, y con la reserva explicita de que
**es GCN, no GFX8**, y que copiarla a GFX8 es una decision del driver propio y
no una lectura.
