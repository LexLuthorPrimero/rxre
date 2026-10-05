# 1521 — `TARGET_MISMATCH` en dos ejes: la GPU integrada no está en el bus PCI, y el kernel que corre es 7.2.9 mientras el driver es 7.1.3

```
AUTOR=AGENTE-INSTR
FECHA=2026-10-05 05:07 -03
TIPO=FACT + TARGET_MISMATCH
ESTADO=PROVEN (las dos discrepancias) / NOT_DETERMINED (por que desaparecio la iGPU)
ALCANCE=esta maquina, en el arranque actual.  SOLO LECTURA.
MEDIDO=comparacion del fingerprint real contra el TARGET CONTRACT de AGENTS.md
HARDWARE_FINGERPRINT_REAL=i7-4790 8h, ECS H81H3-M4, 11.6 GiB, chassis 3,
  sin VM, kernel 7.2.9-200.nobara.fc44.x86_64, arranque 2026-10-05 04:01:21
ENCADENA=1510 (la integrada desaparecio, NOT_DETERMINED) -- aqui se mide POR QUE
  no, y se encuentra un segundo eje de mismatch
```

## Qué se midió, y por qué

`1510` registró que la GPU integrada había desaparecido de `/sys` y que el
por qué era `NOT_DETERMINED` porque `dmesg` está restringido. Quedó una
incógnita abierta sobre **la premisa del proyecto entero**.

AGENTS.md define la frontera dura sobre `0000:00:02.0` y afirma que *«la consola
es de la Intel»*. Si ese dispositivo no existe, la prohibición sigue siendo
correcta pero **carece de objeto**, y todo lo que el proyecto haya medido de la
integrada pertenece a un arranque anterior.

Eso merecía una medición, no una nota al pie.

## Resultado 1 — la integrada NO está en el bus PCI. No es que `i915` falle.

```
$ lspci -nn | head
00:00.0 Host bridge       Intel 4th Gen Core Processor DRAM Controller [8086:0c00]
00:01.0 PCI bridge        Intel Xeon E3-1200 v3/4th Gen Core PCIe x16 [8086:0c01]
00:14.0 USB controller    Intel 8 Series/C220 xHCI [8086:8c31]
...
01:00.0 VGA compatible    AMD Lexa PRO [1002:699f] (rev c7)
01:00.1 Audio device      AMD Baffin HDMI/DP [1002:aae0]
03:00.0 Ethernet          Realtek RTL8111/8168 [10ec:8168]

$ journalctl -b | grep -ci i915
0
```

**No hay `00:02.0`.** No hay entradas VGA Intel, ni `i915` en el kernel log, ni
el nodo en sysfs, ni el módulo cargado.

Y esto **no es un módulo que no carga**: un `i915` que fallara dejaría rastro en
el journal y aparecería el dispositivo en el bus con el driver sin claims. Aquí
**el dispositivo no está en el bus**. Eso es una cosa distinta.

**Y no es una VM:**

```
$ systemd-detect-virt        ->  none
product_name                ->  H81H3-M4
sys_vendor                  ->  ECS
chassis_type                ->  3   (desktop)
/sys/firmware/acpi/tables/  ->  APIC BGRT data DBGP DMAR ...
MemTotal                    ->  12165904 kB
```

Placa, CPU y RAM **coinciden con el TARGET CONTRACT**:

| eje | target | real | |
|---|---|---|---|
| CPU | Intel Core i7-4790 / Haswell | `i7-4790 CPU @ 3.60GHz`, 8 núcleos | ✓ |
| placa | ECS H81H3-M4 | `H81H3-M4`, vendor ECS | ✓ |
| RAM | 12 GiB DDR3 | 12165904 kB = 11.6 GiB | ✓ |
| GPU | AMD Radeon RX 550 | Lexa PRO `[1002:699f]` | ✓ |
| VRAM | ~2 GiB | `mem_info_vram_total` = 2147483648 | ✓ |
| **GPU integrada** | **Intel HD 4600 en `0000:00:02.0`** | **ausente del bus PCI** | **✗** |

En una ECS H81H3-M4 con un i7-4790, la iGPU **está** en `00:02.0`. Su ausencia
no es «un driver que no carga»: es que el bus no la enumera.

**La hipótesis más probable, y NO se afirma porque no es medible desde aquí:**
el ajuste de firmware que desactiva la iGPU en la BIOS/UEFI (en las ECS suele
aparecer como *Intel Graphics* / *Internal Graphics* / *DVMT Pre-Allocated*).
No se ha medido la configuración del firmware, así que es `HYPOTHESIS`, no
`CONCLUSION`. **No se ha tocado el firmware ni la BIOS para comprobarlo.**

## Resultado 2 — segundo `TARGET_MISMATCH`, independiente del primero, y con consecuencia operativa

```
$ uname -r
7.2.9-200.nobara.fc44.x86_64

$ modinfo 04-IMPLEMENTACION/rx550-driver/rx550_drv.ko | grep vermagic
vermagic:  7.1.3-200.nobara.fc44.x86_64 SMP preempt mod_unload

$ modinfo -n amdgpu
/lib/modules/7.2.9-200.nobara.fc44.x86_64/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst
```

**El `.ko` del proyecto está compilado para 7.1.3 y el kernel que corre es 7.2.9.**

Y el árbol tiene los tres:

```
/lib/modules/6.18.2-200.nobara.fc43.x86_64
/lib/modules/7.1.3-200.nobara.fc44.x86_64
/lib/modules/7.2.9-200.nobara.fc44.x86_64
```

**Consecuencia concreta y verificable:** `insmod rx550_drv.ko` **fallaría** con
`Invalid module format` por `vermagic`. No es una predicción: es lo que hace el
kernel cuando el `vermagic` no coincide, y el valor está escrito en el propio
`.ko` y en `uname -r`.

Y el corpus fuente es `RESEARCH/working/linux-7.1.3`, con
`rx550-upstream-7.2.8` al lado como otra versión. **El proyecto tiene las dos y
el hardware está corriendo la tercera.**

Esto es la parte que importa del hallazgo: **`1510` y todo lo anterior se
midieron sobre 7.2.9 ejecutándose, y el proyecto está construido sobre 7.1.3.**
Cualquier lectura de registro, cualquier `vermagic`, cualquier decisión sobre
`struct` del driver es de **7.2.9**, no del target.

## Procedencia

- `CROSS-CHECK` — cada eje por **vía independiente**: `lspci -nn`,
  `journalctl -b`, `/proc/cpuinfo`, `/sys/class/dmi/id/*`,
  `systemd-detect-virt`, `/proc/meminfo`, `uname -r`, `modinfo`,
  `modinfo -n amdgpu`, `/sys/class/drm/*/device/mem_info_vram_total`.
- **La ausencia de `00:02.0` se comprobó por tres vías**: `lspci` no lo lista,
  `journalctl` no tiene ni una línea con `i915`, y `/sys/class/drm` no lo tiene.
- `journalctl` **sí** es legible aunque `dmesg` no lo sea — y eso es lo que
  permitió convertir el `NOT_DETERMINED` de `1510` en una medición.
- **El arranque actual empezó a las 2026-10-05 04:01:21**, con
  `uptime 1h 3m` al empezar a medir. **La máquina reinició**, y las mediciones de
  `1481`–`1501` son del arranque anterior.
- **Sin MMIO, sin TLB, sin insmod, sin tocar firmware. `GPU INTACTA`.** Ninguna
  operación de esta sesión ha escrito en hardware, en `/sys`, ni en la BIOS.

## Lo que NO se afirma

- **No se afirma por qué no está la integrada.** Es `NOT_DETERMINED`. La
  hipótesis de firmware es plausible y no medida; leer el ajuste de la BIOS exige
  reiniciar, y eso no se hace sin autorización explícita.
- **No se afirma que el target esté mal.** Puede que la iGPU se haya apagado en
  la BIOS deliberadamente, o que se haya estropeado, o que este arranque sea de
  otro equipo con la misma placa. **No se ha medido cuál**, y el DMI coincide en
  todos los ejes que se han mirado.
- **No se ha modificado nada** para producir este hallazgo. Ni un parámetro, ni
  un fichero de configuración, ni el árbol.
- **No se ha recompilado** el driver contra 7.2.9, ni se ha comprobado si
  compila. Eso es una acción distinta y no está hecha.

## Consecuencia para el proyecto, y es la parte accionable

AGENTS.md §4 dice, literalmente:

```
Si el fingerprint real no coincide con el target:
    TARGET_MISMATCH
    No ejecutar silenciosamente una ruta genérica.
```

**Se cumple en dos ejes, y la respuesta no es ignorar el hallazgo.** Las tres
cuestiones que quedan abiertas y que son distintas entre sí:

1. **¿Cuál es el target?** El corpus es 7.1.3 y el hardware corre 7.2.9. Sin
   decidir esto, `vermagic` no se puede fijar y el driver no se puede probar.
2. **¿Debe el proyecto migrar a 7.2.9?** Hay árbol de 7.2.9 en
   `/lib/modules/` y `rx550-upstream-7.2.8` en el árbol. Es una decisión de
   proyecto, no una corrección.
3. **¿Dónde está la iGPU?** La frontera dura de AGENTS.md la define sobre un
   dispositivo que no aparece en el bus. Si la iGPU no vuelve, la prohibición
   sigue vigente **y vacía**, y el `PUERTA_FRONTERA` de `rxre.py` no tiene sujeto
   que proteger hoy.

## Y un documento del proyecto acaba de quedar desmentido

`HARDWARE-FINGERPRINT.md`, generado el **2026-10-02** y con
`GENERADO=2026-10-02` en su cabecera, declara en su tabla de coincidencias:

```
| iGPU | Intel HD 4600 | `8086:0412` en `0000:00:02.0`, driver `i915` | coincide |
| OS  | Nobara/Fedora-based | `7.1.3-200.nobara.fc44.x86_64`         | coincide |
```

Los dos son **falsos hoy**. Y el documento es correcto: era verdad del arranque
que había cuando se generó, y la máquina **reinició el 2026-10-05 a las
04:01:21**.

Eso no es un defecto del documento. **Es un defecto del formato:** un
fingerprint sin fecha de arranque en el cuerpo se lee como una propiedad de la
máquina, y no lo es. `GENERADO=2026-10-02` está en la cabecera, a siete líneas
de donde se lee la tabla.

Y hay un detalle que lo hace más grave: la tabla marca **«coincide»** en una
columna que se llama, literalmente, *coincide*. Un lector que busca
discrepancias **no mira esa columna**, porque su nombre dice que ya se miró.

**No se ha modificado `HARDWARE-FINGERPRINT.md`.** Este hallazgo lo desmentido,
no lo corrige: corregirlo sería escribir un estado que no he medido con cuidado,
y AGENTS.md §80 manda lo contrario ante una contradicción — registrar ambas
versiones, no elegir.

La corrección que sí corresponde es de **formato**, no de contenido: el
fingerprint necesita el **arranque al que pertenece** en la misma línea que cada
medida, para que deje de leerse como una propiedad de la máquina. Eso no se ha
hecho y es una acción propuesta.

**Lo que NO se ha hecho, deliberadamente:** no he reiniciado, no he entrado en
la BIOS, no he tocado `/etc/modprobe.d`, no he cargado ningún módulo, y no he
cambiado laBIOS. Todo eso es reversible sólo en parte, y ninguna de esas
operaciones es necesaria para **saber** — que es lo que este hallazgo establece.

## Dos notas de método

**La primera: un `NOT_DETERMINED` es una pregunta, no un final.**

`1510` cerró con *«por qué desapareció la integrada es `NOT_DETERMINED`, y no se
especula»*. Fue correcto, y dejó una puerta abierta. Esta iteración la empujó:
en vez de buscar el motivo a ciegas, se buscó **por qué se busca**, es decir, qué
afirmación del proyecto dependía de ello. Y la respuesta fue «toda la frontera
dura», lo que convirtió una nota en un `TARGET_MISMATCH` de dos ejes.

*Un `NOT_DETERMINED` que no tiene pregunta detrás no se investiga nunca.*

**La segunda: el segundo eje apareció por accidente, y por eso no se perdió.**

Iba a verificar la iGPU y, al leer `lspci` de paso, vi que el bridge rotulaba
«Xeon E3-1200 v3». Fui a mirar `/proc/cpuinfo` esperando un(target mismatch de
CPU) y era el i7-4790 correcto. **Seguí leyendo y `uname -r` me dio 7.2.9.**

Si hubiera parado en «el hardware es el correcto», el `vermagic` del `.ko` se
habría seguido sin ver sin ver, y es la única discrepancia de este hallazgo que
tiene una consecuencia operativa inmediata.

*Cuando dos mediciones encajan, la tentación es cerrar. La tercera es la que
duele.*
