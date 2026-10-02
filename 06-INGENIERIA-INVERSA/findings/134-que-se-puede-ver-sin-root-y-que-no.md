# 134 · Qué se puede observar sin root en esta máquina, y qué no

`CLASSIFICATION=METHODOLOGY` · `TRACK=HOST_OBSERVATION` · `WORK_CLASS=READ_ONLY`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=OBSERVED` · `GPU INTACTA`
`HERRAMIENTA=tools/treescope.py` (heredada) · `CONTINUES=127`
`ACOTA=los discriminantes pendientes de las fronteras D, E y G`

## Cuestión principal

Cinco discriminantes que las fronteras D, E y G tienen abiertos son **NIVEL 2**,
lectura. Nunca se comprobó cuáles son alcanzables sin `root`, y eso convierte
cada uno de ellos en «pendiente» sin saber si pendiente de *qué*.

## Criterio de terminación

Enumerar las vías de observabilidad de runtime y comprobar, para cada una, si
existe y si se puede leer. **Cumplido: seis vías, tres utilizables, y un
descubrimiento que cambia el valor de una de ellas.**

## Respuesta

```
uid                                   1000          sin root

VÍA                                      EXISTE   SE LEE   NOTA
/sys/kernel/tracing                     si       NO       existe, sin permiso
/sys/kernel/debug/tracing               no       --       no existe
available_filter_functions              --       NO       ilegible
/proc/sys/kernel/perf_event_paranoid    si       si       = 2  (solo userspace)
/proc/sys/kernel/kptr_restrict          si       si       = 0  PERO no sirve, ver abajo
/proc/kallsyms                          si       si       63269 simbolos de amdgpu
/proc/modules                           si       si       13 modulos
/sys/module/amdgpu/parameters/          si       si       96 parametros
journalctl -k                           si       si       legible sin root
```

### El límite que no era visible: `kptr_restrict = 0` y las direcciones siguen a cero

```
awk '$1 != "0000000000000000"' /proc/kallsyms   ->   0
```

**Ninguna dirección de `/proc/kallsyms` es utilizable.** `kptr_restrict = 0`
declara que deben ser visibles y no lo son, así que hay un endurecimiento más
que no aparece en el valor de ese parámetro — por ejemplo el espacio de usuario
del contenedor, o un `kallsyms` filtrado. **Declarar el parámetro y no mirar
el fichero es la clase de error que este hallazgo trata de no repetir.**

Consecuencia: `kallsyms` da **presencia de símbolo**, no dirección. Y para lo
que se parecíaBv, para, no sirve.

### Lo que sí aporta: presencia de símbolo, con su control

Un `0` sin denominador no es un resultado, y el control es lo que lo
convierte en uno. Primero probé cinco símbolos con enlace externo y **el
control falló**: hasta `printk` salía ausente. La causa era mi patrón, que no
admitía el sufijo `.cold` ni el prefijo `__pfx_` con que el compilador publica
las variantes frías. Corregido:

```
CONTROL (con enlace externo, deben estar)
  amdgpu_ib_get        PRESENTE
  amdgpu_ring_alloc    PRESENTE
  amdgpu_job_submit    PRESENTE

LO QUE 119 Y 127 RESOLVIERON SOLO POR LECTURA ESTATICA
  sdma_v3_0_ring_emit_ib               PRESENTE
  sdma_v4_0_ring_emit_ib               PRESENTE
  gfx_v8_0_ring_emit_vm_flush          PRESENTE
  amdgpu_ring_generic_pad_ib           PRESENTE
  gfx_v8_0_do_edc_gpr_workarounds      AUSENTE  (static, sin enlace)
```

**`.cold` y `__pfx_` hacen que un símbolo parezca ausente cuando existe**, y
sólo un control positivo lo detecta. Es la versión de símbolos de «un 0 sin
denominador».

### Lo que esto corrobora y lo que deja igual

**Corrobora**, desde el binario, el criterio de `043`/`046`: los dos emisores
de IB —`sdma_v3_0_ring_emit_ib` y `sdma_v4_0_ring_emit_ib`— **están ambos
compilados** en el módulo en ejecución. Lo que decide cuál corre es el
`ip_block` que monta `vi.c`, no qué fichero existe. Eso es exactamente lo que
dicen, y ahora está visto en la tabla de símbolos y no sólo leído en el fuente.

**Deja igual** el gate de `gfx_v8_0.c:1485`, porque
`gfx_v8_0_do_edc_gpr_workarounds` es `static` y no se publica. El gate sigue
siendo `PROVEN` por lectura, y **no** es comprobable por esta vía. Queda
dicho para que nadie lo intente por aquí otra vez.

## Qué se abre y qué se cierra con esto

**Se cierra, como pregunta:**

|abierta | estado |
|---|---|
| ¿`.cold`/prefixos falsean la presencia de símbolos? | `PROVEN` — sí, y sin control positivo no se ve |
| ¿Hay direcciones de kernel utilizables? | `REFUTED` — 0 de 305320 |
| ¿`.cold` de un módulo carga? | `PROVEN` — sí, las variantes frías de amdgpu están |

**Quedan alcanzables sin root:** `journalctl -k`, los 96 parámetros de módulo
de `amdgpu`, `/proc/kallsyms` (presencia), `/proc/modules`, `lspci`,
``.c` de `dmesg` restringido.

**Quedan cerradas sin root:** tracefs y `available_filter_functions`, que son
la vía de los kprobes. Eso **deja sin cambio** el estado de
`116:209-211` —la frecuencia real del invalidate por kprobe—: era `NIVEL 2`
con instrumentación, y la instrumentación no se puede montar.

## El punto que mas importa, y no es tecnico

Tres de las cinco herramientas de esta sesionfallen en lo mismo: un filtro que
acepta demasiado y devuelve un número plausible. `kallsyms` con el patron
`[ .tT]$sym$` devolvía «ausente» para símbolos que existen, y un `0` así es
peor que no medir, porque el `0` parece un hallazgo.

**Y el control cuesta una línea.** `printk` estaba ausente, y eso ya decia
que el problema era mío. No hice falta una hipótesis para encontrarlo: hizo
falta un control, que es lo que `AGENTS.md` §INFORMATION GAIN llama
discriminante.

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`: el árbol de Linux 7.2.8 no se ha
tocado. `GPU INTACTA`.
