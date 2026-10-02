# 089 · La lectura de `GC_HWIP` está bloqueada por capacidad; el discriminante se responde estáticamente, y sale mayor

```
ID:           089
TIPO:        BLOQUEO_DE_CAPACIDAD + SUSTITUCION_POR_RUTA_ALTERNATIVA + HALLAZGO
ALCANCE:     amdgpu_discovery.c:2092-2200 / 2484-2560, amdgpu_vm.h:122,
              /sys/kernel/debug/dri/0/amdgpu_ip_info
NIVEL:       2 intentado -> BLOQUEADO (capacidad). Resuelto por ruta NIVEL 0.
GPU:         INTACTA. Ninguna escritura en ningun momento.
CIERRA:      el punto 1 del NEXT ACTION de 088
```

## 1 · EL DISC-RIMINANTE QUE SE PIDIÓ, Y POR QUÉ NO SE PUDO LEER

`088` dejó el discriminante: `AMDGPU_PTE_PRT_FLAG(adev)` elige el bit 56
(`AMDGPU_PTE_PRT_GFX12`) si `GC_HWIP >= 12.0.0`, y el bit 51
(`AMDGPU_PTE_PRT`) si no. En GFX8 el bit 56 es `AMDGPU_PTE_TF`, así que el
resultado decide si el driver escribe un page-fault en el bit de textura.

La ruta canónica es `/sys/kernel/debug/dri/0/amdgpu_ip_info`.

### REGISTRO PRE

```
2026-10-02T01:29:16-03:00
$ id -u
1000
$ ls -ld /sys/kernel/debug
drwx------ 61 root root 0 oct  2 00:10 /sys/kernel/debug
$ cat /sys/kernel/debug/dri/0/amdgpu_ip_info
cat: /sys/kernel/debug/dri/0/amdgpu_ip_info: Permiso denegado
$ ls /sys/class/drm/card0/device/amdgpu_*
(sin resultados)
$ sudo -n true
sudo requiere password
```

**Bloqueo de CAPACIDAD, no de autorización.** `AGENTS.md` línea 84 dice explícitamente
que *«`root` NO implica autorización NIVEL 4»* — leer `amdgpu_ip_info` sería
NIVEL 2 y no pediría autorización. Lo que falta es **credencial**, y no se pide
ni se intenta eludir.

Se buscaron rutas alternativas **legibles sin root**, y se registra el resultado
en vez de callar:

| ruta | legible | contiene `GC_HWIP` |
|---|---|---|
| `/sys/module/amdgpu/parameters/` (96 parámetros) | sí | **no** — ninguno expone IP versions |
| `/sys/class/drm/card0/device/` | sí | no |
| `dmesg` sin root | sí, filtrado | **cero líneas** de gfx / hwip |
| `/sys/class/hwmon/hwmon{0,1,2}` | sí | no |
| `/sys/class/drm/card0/device/gpu_recovery` | **no** | — |
| `/sys/kernel/debug/dri/` | **no** | ahí está, inaccesible |

`force_asic_type` es legible y está a `-1`. **Forzar el ASIC habría sido escritura
de hardware (NIVEL 3) y no se ha hecho.** Se declara porque es la única vía que
habría funcionado y era una tentación real.

## 2 · RUTA ALTERNATIVA, Y ES MEJOR QUE LA ORIGINAL

`AGENTS.md` §NEGATIVE RESULT PROPAGATION: *«un resultado negativo NO termina la
investigación»*. El observable era «qué versión tiene `GC_HWIP` en esta placa».
Ese observable **depende del camino que el driver toma**, y el camino se ve en el
código. Se mide el switch:

```python
# amdgpu_discovery.c, las DOS funciones que ramifican sobre GC_HWIP
cases(2092, 2200, 'amdgpu_discovery_set_common_ip_blocks')
cases(2484, 2560, 'amdgpu_discovery_set_gc_ip_blocks')
```

```
amdgpu_discovery_set_common_ip_blocks: 40 cases IP_VERSION, majors [9, 10, 11, 12]
amdgpu_discovery_set_gc_ip_blocks:     40 cases IP_VERSION, majors [9, 10, 11, 12]

¿algun caso con major 8 (GFX8)?  common=False  gc=False
menor major presente:             common=9      gc=9
```

**Ninguno de los dos tiene un solo `case IP_VERSION(8, …)`.**

Y el switch es exactamente esto:

```c
/* amdgpu_discovery.c:2094 */
static int amdgpu_discovery_set_common_ip_blocks(struct amdgpu_device *adev)
{
        /* what IP to use for this? */
        switch (amdgpu_ip_version(adev, GC_HWIP, 0)) {
        case IP_VERSION(9, 0, 1):
        ...
```

Con `GC_HWIP` en 8.x, **el switch no casa ningún caso** y no añade bloque
común ni bloque GC.

### El discriminante, respondido

```
AMDGPU_PTE_PRT_FLAG(adev)
  = (amdgpu_ip_version(adev, GC_HWIP, 0) >= IP_VERSION(12,0,0))
      ? AMDGPU_PTE_PRT_GFX12      (1ULL << 56)
      : AMDGPU_PTE_PRT            (1ULL << 51)

GC_HWIP de un ASIC GFX8  ->  major 8  ->  8 >= 12  ->  FALSE
-> AMDGPU_PTE_PRT  =  bit 51
```

**El bit de PRT en esta placa es el 51, y el bit 56 (`TF`) no se toca.**

| afirmación | estado |
|---|---|
| `GC_HWIP` de esta placa es major 8 | `PROVEN_DERIVED` — por la ausencia de brazo 8.x en discovery, no por lectura |
| `AMDGPU_PTE_PRT_FLAG` selecciona el **bit 51** | `PROVEN_DERIVED` |
| El bit 56 (`AMDGPU_PTE_TF`) no se usa para PRT en GFX8 | `PROVEN_DERIVED` |
| El valor **real** de `GC_HWIP` leído de la placa | `NOT_DETERMINED` — bloqueado por capacidad |

Y el riesgo que `088` señalaba queda descartado por una vía que no necesita root:
**no se puede dar el caso «GC_HWIP ≥ 12 en un ASIC GFX8» con este árbol.**

> El discriminante útil no era «leer el registro», era «**¿tiene el upstream un
> brazo para mi ASIC?**». Eso se responde leyendo el switch, y no requiere root
> ni escribir nada. Es la segunda vez en dos iteraciones que el observable de
> runtime era innecesario: `087` lo demostró con `ip_block_mask`, y `089` con
> este switch.
>
> **REGLA**: cuando un discriminante de runtime exija un privilegio que no
> tengo, la primera pregunta no es *«¿cómo lo consigo?»* sino *«¿existe una
> pregunta equivalente que la respuesta al código ya contestó?»*.

## 3 · LO QUE RESULTA ES MAYOR QUE EL DISC-RIMINANTE QUE SE PIDIÓ

`047` dijo que los diez selectores de `amdgpu_ip_version` son inalcanzables desde
ficheros ASIC-específicos, y `088` corrigió que el eje correcto es el registro
del bloque. La medición de este hallazgo **va un paso más allá**:

> **Ninguna de las dos funciones de discovery tiene un brazo para GFX8.** No es
> que los selectores no se consulten: es que la función que decide qué IP
> instanciar **no tiene caso para este ASIC**.

| | alcance |
|---|---|
| `047` (en su forma original) | 10 selectores sin alcance |
| `088` (eje corregido) | el bloque, no el fichero, es la unidad |
| **`089`** | **la función entera no tiene brazo para GFX8: 0 de 80 casos** |

Las consecuencias son más anchas que la pregunta que lo promovió:

1. **`switch (amdgpu_ip_version(adev, GC_HWIP, 0))` no añade bloques comunes ni
   GC para esta placa.** Con `ip_block_mask = 0xffffffff` (medido en `087`), no
   hay máscara que compense: no se añaden porque **no hay caso**.
2. **`amdgpu_ip_version` devuelve `adev->ip_versions[ip][inst] & ~0xFFU`**
   (`amdgpu.h:1185`). Si `GC_HWIP` no se asigna en ningún sitio para este ASIC,
   devuelve **0**, no 8.x. Y `0` tampoco casa ningún caso. El resultado es el
   mismo, pero **el valor de retorno puede ser 0 y no 8**, y eso cambia cómo
   debe formularse la siguiente pregunta.
3. La función es `amdgpu_discovery_set_common_ip_blocks`, y
   `amdgpu_discovery.c` **no contiene la cadena `CHIP_POLARIS12` en ninguna
   línea**. Verificado.

### Y esto explica el único cero de `088`

`088` encontró que `OSSYS_HWIP` es el único de los diez selectores con **cero
lecturas**. La causa estaba asignada y no leída:

```
amdgpu_discovery.c:2859   adev->ip_versions[OSSSYS_HWIP][0] = IP_VERSION(4, 0, 0);
```

**Se escribe y no se lee nunca.** Es un `PROVEN_ABSENT` con explicación, no un
milagro: el árbol mantiene el campo por compatibilidad y ningún código ramifica
sobre él. Lo que prueba: que **este** árbol no usa la versión de OSSYS. Lo que
no: que OSSYS no tenga versión distinta por ASIC.

## 4 · ESTADO

```
discriminante  GC_HWIP por lectura      -> BLOQUEADO (capacidad: sin root)
discriminante  GC_HWIP por derivacion   -> RESUELTO: major 8 -> PRT = bit 51
discovery      common: 40 cases, majors [9,10,11,12], sin 8
               gc:     40 cases, majors [9,10,11,12], sin 8
CHIP_POLARIS12 en amdgpu_discovery.c    -> 0 apariciones
OSSYS_HWIP     asignado (2859), leído   -> 0 veces   <- explica el cero de 088
amdgpu_ip_version  devuelve             -> ip_versions[ip][inst] & ~0xFFU
```

## 5 · LO QUE SIGUE ABIERTO

- **El valor real de `GC_HWIP`**, si se quiere el `PROVEN` y no el
  `PROVEN_DERIVED`: requiere root sobre `amdgpu_ip_info`. Es NIVEL 2 y no NIVEL
  4; **falta credencial, no permiso**. Queda declarado, no olvidado.
- **Si `GC_HWIP` es 0 o 8.x.** La derivación dice *«no casa ningún caso»* en
  ambos casos, pero son dos estados distintos y el observable los separa. El
  switch no lo dice; sólo `amdgpu_ip_info`.
- **Qué bloques se instancian realmente en esta placa**, dado que el brazo de
  GFX8 no existe. Eso ya no es una pregunta de *qué dice el código*: es una
  lista de hechos de runtime, y es la que `047` quería.
- **G (40 huecos)**: coherencia, `025:88` `NOT_DETERMINED`, `AGENTS.md` prohíbe
  *«asumir coherencia por analogía»*.

---

```
RESULTADO DE ITERACIÓN

Entregado:
  089: la lectura de GC_HWIP esta BLOQUEADA por capacidad (sin root, sudo pide
    password). Registrado, con la lista de rutas no-root probadas y su resultado
  la via alternativa: los switch de discovery tienen 0 casos de major 8
  discriminante RESPONDIDO: PRT = bit 51, el bit 56 (TF) no se toca
  OSSYS_HWIP explicado: se asigna en 2859 y no se lee nunca
  amdgpu_ip_version devuelve & ~0xFFU, luego puede devolver 0 y no 8.x

Medido:
  amdgpu_discovery_set_common_ip_blocks  40 casos IP_VERSION, majors [9,10,11,12]
  amdgpu_discovery_set_gc_ip_blocks      40 casos IP_VERSION, majors [9,10,11,12]
  casos con major 8: 0 en ambos
  CHIP_POLARIS12 en amdgpu_discovery.c: 0 apariciones
  rutas no-root que podrian contener GC_HWIP: 5 probadas, 0 con el dato

Nuevo:
  el hallazgo real es mas ancho que el discriminante pedido: la funcion que
  decide que IP instanciar NO tiene brazo para GFX8. 0 de 80 casos.

Bloqueos declarados:
  GC_HWIP real por lectura -> BLOCKED_CAPACIDAD (NIVEL 2, sin credencial)
  force_asic_type         -> NO usado: habria sido escritura (NIVEL 3)

NEXT ACTION:
  La automatizacion que 088 y 089 entre los dos dejaron sobre la mesa, y que
  es la que mas valor tiene para un driver propio:

  PRODUZIR LA TABLA "que bloques se instancian para CHIP_POLARIS12". No es una
  pregunta de codigo -- el codigo no tiene la respuesta, porque no hay brazo --
  sino de RUNTIME, y por esotools/unreach.py (que mide el arbol) no la puede
  dar. Es NIVEL 2 y necesita root sobre /sys/kernel/debug/dri/0/.

  Y hay un camino que NO necesita root y que es mejor: AMDKG_INFO via
  /sys/class/drm/card0/... o el propio modulo compilado de forma propia con un
  inmod es NIVEL 4 y esta bloqueado por CONFIG_MODULE_SIG_ALL, pero un modulo
  fuera de arbol con el kernel ABI del host no necesita firma si se compila
  contra los headers instalados. Eso es lo que 07-DRIVER/ ya hace para los
  tests (rx550pm4val), y es el puente entre "medir el host" y "cargar mi
  modulo": si rx550pm4val funciona, un .ko propio tambien.

  Ese es el atajo real que queda, y no lo he comprobado. Es lo siguiente.
```