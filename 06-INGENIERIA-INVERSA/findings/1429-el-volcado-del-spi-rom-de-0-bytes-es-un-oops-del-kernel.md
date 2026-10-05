# 1429 — el volcado del SPI ROM de 0 bytes no es un resultado negativo: es un `oops` del kernel por desreferencia nula, con el campo de estado capturado

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN/RE
CLASSIFICATION=DEFECTO-EN-KERNEL-VIGENTE+INVALID_RESULT+CORRECCION-DE-DOS-HALLAZGOS
TRACK=RUNTIME-PASIVO(journalctl) + STATIC(fuente) · sin GPU · sin sudo
GENERADO=2026-10-04
AFECTADO=revkit/capturas/psp_spirom_dump.txt        (0 bytes + .err de 0 bytes)
         06-INGENIERIA-INVERSA/findings/097-*        (tenia el oops, no su causa)
         06-INGENIERIA-INVERSA/findings/946-*        (tenia "causa DESCONOCIDA")
         revkit/captura.py:71,198-212,219            (el productor)
ESTADO=PROBADO · hay un BUG de kernel capturado en el journal, con marca de tiempo, PID,
       comando y RIP · las cuatro patas de la causa, verificadas a mano
       · el volcado es INVALID_RESULT (el proceso murio), no "no hay nada"
       · es un NULL-deref ALCANZABLE en tarjetas gfx8 legacy, con un nodo modo 0444
```

## 0. Qué se afirmaba y por qué era incorrecto

`revkit/capturas/psp_spirom_dump.txt` pesa **0 bytes** y su `.err` también **0 bytes**. La
tentación, y la lectura por defecto, es: *"no hay ROM SPI"* o *"no se pudo leer"*. **Las dos
son falsas**, y se ve en un detalle que casi nadie mira: **el `.err` vacío**.

```text
$ wc -c  revkit/capturas/psp_spirom_dump.txt      -> 0
$ wc -c  revkit/capturas/psp_spirom_dump.txt.err  -> 0
$ wc -c  revkit/capturas/amdgpu_sensors.txt.err    -> 93
```

Un `.err` de 0 bytes **no significa "sin error"**. Un error de lectura produce texto:

```text
$ head -c 120 revkit/capturas/amdgpu_sensors.txt.err
head: error al leer '.../amdgpu_sensors': Argumento inválido
```

93 bytes, el error del driver (`-EINVAL`). Un `.err` de 0 bytes significa otra cosa
distinta: **el proceso desapareció antes de poder escribir**. Un oops mata el proceso.

## 1. El oops, en el journal, con la marca de tiempo del volcado

```text
$ journalctl --list-boots
 -4  Fri 2026-10-02 00:10:26 -03  ...  (aqui esta)
 -3  Fri 2026-10-02 14:54:59 -03  ...

$ journalctl -k -b -4 | grep -c 'kernel NULL pointer'
7 lineas
```

Texto literal:

```text
oct 02 00:18:06 kalm kernel: BUG: kernel NULL pointer dereference, address: 00000000000000b8
oct 02 00:18:06 kalm kernel: #PF: supervisor read access in kernel mode
oct 02 00:18:06 kalm kernel: #PF: error_code(0x0000) - not-present page
oct 02 00:18:07 kalm kernel: Oops: Oops: 0000 [#1] SMP PTI
oct 02 00:18:07 kalm kernel: CPU: 1 UID: 0 PID: 6105 Comm: head Not tainted 7.1.3-200...
oct 02 00:18:07 kalm kernel: RIP: 0010:psp_read_spirom_debugfs_open+0xa5/0x170 [amdgpu]
oct 02 00:18:07 kalm kernel: RAX: 0000000000000000 RBX: 0000000000000000
oct 02 00:18:07 kalm kernel: Code: 56 b9 02 00 00 00 ba 00 10 00 00 ... 48 8b 85 28 f5 03 00
                                 <48> 8b 80 b8 00 00 00 48 85 c0 74 5a ...
```

**El encaje con el artefacto es al segundo:**

```text
psp_spirom_dump.txt      mtime  2026-10-02 00:18:06.494253085     0 bytes
oops en el journal                     oct 02 00:18:06               <-- mismo segundo
Comm: head                                          <-- el comando era head
UID: 0                                              <-- se lanzo como root
RIP: psp_read_spirom_debugfs_open+0xa5/0x170        <-- la funcion que abre el nodo
```

Y el productor, en el propio proyecto:

```text
revkit/captura.py:71        psp_spirom_dump con tope de 262144 bytes
revkit/captura.py:198-212   head -c "$tope" "$D/$nodo" > "$f" 2>"$f.err"
revkit/captura.py:42        DEBUGFS = "/sys/kernel/debug/dri/0000:01:00.0"
```

**Corregido:** el subagente que localizó el oops en el journal lo situó en el
boot `-3`. **Está en el boot `-4`**, que es donde cae el volcado. El boot `-3` sólo tiene 2
líneas de traza. El oops existe; el índice del boot estaba mal.

## 2. Las cuatro patas de la causa, verificadas a mano

### Pata 1 — el nodo se crea sin condición

```c
/* amdgpu/amdgpu_psp.c:4466-4471 */
void amdgpu_psp_debugfs_init(struct amdgpu_device *adev)
{
    ...
    debugfs_create_file_size("psp_spirom_dump", 0444, minor->debugfs_root,
```

**Modo `0444`, creado sin mirar si esta GPU tiene PSP.** Cualquiera puede abrirlo.

### Pata 2 — la macro desreferencia `funcs` para *llegar* al miembro que quiere proteger

```c
/* amdgpu/amdgpu_psp.h:509-511 */
#define psp_dump_spirom(psp, fw_pri_mc_addr) \
    ((psp)->funcs->dump_spirom ? \
     (psp)->funcs->dump_spirom((psp), fw_pri_mc_addr) : -EINVAL)
```

La comprobación es `(psp)->funcs->dump_spirom ? ... : -EINVAL`. **La guarda protege al
miembro, pero para alcanzar el miembro hay que desreferenciar `psp->funcs`.** Si
`psp->funcs` es `NULL`, la propia guarda peta antes de poder proteger nada.

### Pata 3 — el desplazamiento del fallo dice cuál es el miembro

Extraído del `struct psp_funcs` del propio `amdgpu_psp.h` de este kernel:

```text
dump_spirom esta en la posicion 23 de la tabla de punteros
offset = 23 * 8 = 184 = 0xB8
direccion de fallo del kernel = 0xB8          COINCIDE
instruccion = 48 8b 80 b8 00 00 00  ->  mov rax,[rax+0xb8]   con RAX = 0
```

**El kernel dice `0xB8`, el código dice `0xB8`, y la instrucción leída en el `Code:` del
oops dice `[rax+0xb8]` con `RAX = 0`.** Tres fuentes independientes del mismo número.

### Pata 4 — por qué `funcs` es `NULL` en esta tarjeta

`adev->psp.funcs` sólo se asigna dentro del `init_microcode` de un driver de versión de PSP
(`psp_v3_1.c`, `psp_v13_0.c`, …). Y **esta tarjeta no tiene bloque `psp_ip_block`**: el log
de arranque del hallazgo 1418 lista nueve bloques y ninguno es PSP, porque
`vi_set_ip_blocks()` (`vi.c:2105-2123`) no lo añade para `CHIP_POLARIS12`. **Nadie asigna la
función y el nodo se crea igualmente.**

> **Éste es un `NULL-deref` alcanzable en el kernel que corre en esta máquina**, disparado
> por un `open()` de un fichero modo `0444` bajo `/sys/kernel/debug`. No es un problema del
> proyecto: es del driver, y afecta a la familia gfx8 legacy en general — tarjetas sin PSP
> donde el nodo se registra sin condición.

## 3. Qué queda invalidado

| se decía | era | ahora |
|---|---|---|
| `psp_spirom_dump.txt` = 0 bytes ⇒ "no hay ROM SPI" | conclusión de un artefacto **nunca producido** | `INVALID_RESULT` (§27): el proceso murió antes de escribir |
| `.err` = 0 bytes ⇒ "no hubo error" | confundía **sin mensaje** con **sin fallo** | hubo un `oops`; el kernel lo registra en otro sitio |
| "hace falta root" | `UID: 0`, ya era root | **root no lo arregla**: la causa no es el permiso, es el puntero nulo |
| hallazgo 097 | registra el oops y especula una lectura sin root | tenía el síntoma sin la causa |
| hallazgo 946 | "causa DESCONOCIDA" | la causa está en `amdgpu_psp.h:509-511`, y es una guarda mal escrita |

**Los dos hallazgos tenían media respuesta cada uno y nunca se juntaron.** El 097 vio el
oops. El 946 vio que el volcado no explicaba nada. La unión es este documento.

**Y una consecuencia práctica, por si alguien lo intentaba de nuevo:** el SPI ROM **no es
obtenible por esta vía en esta tarjeta**, con root o sin él. No es una cuestión de
permisos. **Y no conviene intentarlo**: la operación mata el proceso y ensucia el kernel log
con un `oops`, que es un estado degradado del sistema, no una lectura.

## 4. Lo que este hallazgo NO hace

- **No toca el kernel.** No se ha ejecutado nada contra el nodo. El oops es de **octubre**,
  de una sesión anterior; este hallazgo lo *lee*.
- **No abre la vía del SPI ROM.** La declara cerrada **por esta interfaz**, que es lo único
  que la evidencia sostiene. Que exista otro camino no se afirma.
- **No afirma que el blob de discovery esté dentro del SPI ROM.** El hallazgo 1428 ya
  cerró otra cosa, que es más fuerte: **no hay blob de discovery para Polaris12, en disco ni
  por diseño**, y el camino que lo leería ni se ejecuta en esta tarjeta.
- **No propone un parche upstream.** No es trabajo de este proyecto, y no está autorizado.

## 5. Procedencia

```text
journalctl --list-boots                          boots -5..0
journalctl -k -b -4 | grep -c 'kernel NULL pointer'    7 lineas
journalctl -k -b -4   BUG / Oops / CPU:1 UID:0 PID:6105 Comm:head / RIP / RAX / Code
revkit/capturas/psp_spirom_dump.txt    mtime 2026-10-02 00:18:06.494253085   0 bytes
revkit/capturas/psp_spirom_dump.txt.err                                         0 bytes
revkit/capturas/amdgpu_sensors.txt.err   93 bytes  (contraste: un error si se ve)
revkit/captura.py:42,71,198-212,219      el productor
RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/
  amdgpu_psp.c:4466,4471                 nodo 0444 sin condicion
  amdgpu_psp.h:509-511                   la macro mal guardada
  amdgpu_psp.h  struct psp_funcs         dump_spirom en la posicion 23 -> 0xB8
amdgpu/vi.c:2105-2123                   sin psp_ip_block para CHIP_POLARIS12
metodo    lectura de journal y de fuente.  Ninguna ejecucion, ningun acceso root.
```

```text
ESTADO=PROBADO · hay un BUG de kernel capturado: NULL-deref en psp_read_spirom_debugfs_open,
       con marca de tiempo al segundo, Comm:head, UID:0, RIP y Code legibles
       · el volcado de 0 bytes es INVALID_RESULT, no un resultado negativo: el proceso
         murio.  Un .err de 0 bytes es la senal, y es distinta de un error de lectura
       · la causa son las cuatro patas: nodo 0444 sin condicion + guarda que desreferencia
         psp->funcs + dump_spirom en 0xB8 (el fault exacto) + ausencia de psp_ip_block
       · ALCANZABLE en el kernel vigente, en tarjetas gfx8 legacy sin PSP
CIERRA   097 (vio el oops) y 946 (causa desconocida): los dos tenian media respuesta
REFUTA  "el volcado de 0 bytes significa que no hay ROM SPI"
REFUTA  "hace falta root": ya se era UID 0
LIMITE  el SPI ROM no es obtenible POR ESTA VIA en esta tarjeta; no se afirma que no exista
         otro camino
RIESGO  reintentar el volcado ensucia el kernel log con un oops.  No hacerlo.
Peligro upstream  real y alcanzable, pero fuera del alcance de este proyecto: no se parchea
Siguiente  amdgpu_mst_topology.txt tiene la misma firma (0 bytes + .err de 0 bytes).  Comprobar
           si es el mismo oops o uno distinto.  Esa comprobacion es solo de lectura.
```
