# 129 · §A/§G: dos knobs distintos, y la granularidad del fragmento sale de la profundidad del árbol

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`128` dejó dos preguntas juntas. Esta nota las separa y cierra la que es software:

> **¿`PDE_CACHE_EFFECTIVE_SIZE` y `L2_CACHE_BIGK_FRAGMENT_SIZE` son el mismo
> parámetro con dos nombres, o dos granularidades distintas?**

**Son dos knobs distintos.** Y el segundo tiene una regla que nadie había mirado.

## 1 · No son un alias: `PDE_CACHE_EFFECTIVE_SIZE` no lo escribe nadie

```
grep -rn 'PDE_CACHE_EFFECTIVE_SIZE'  sobre los 2787 ficheros de amd/**/*.c   ->  0
```

**Cero. En ningún chip, en ninguna generación.** El campo existe en el header
(`VM_L2_CNTL2`, bits 28-30) y ningún fichero del driver lo programa jamás.

Y el otro:

```
grep -rn 'L2_CACHE_BIGK_FRAGMENT_SIZE'  ->  49 escrituras en 25 ficheros
gmc_v8_0.c:869        REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, field)
gfxhub_v12_0.c:245    REG_SET_FIELD(tmp, GCVM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, 9)
gfxhub_v12_0.c:249    REG_SET_FIELD(tmp, GCVM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, 6)
mmhub_v1_0.c:185/189  ... , 9)  y  ... , 6)
```

**Y ningún fichero escribe los dos.** La prueba de alias habría sido exactamente
eso.

**Consecuencia:** la caché de PDEs tiene **un tamaño efectivo propio, en valor de
reset, que nadie modifica**. No es un segundo nombre del fragment size.
`PROVEN` por ausencia en los 2787 ficheros, que es `PROVEN_ABSENT` y no
`NOT_FOUND`.

## 2 · El 9 y el 6 no son por VMHub: son una capacidad de hardware

Lo iba a leer como "un hub gráfico y otro de medios". Es otra cosa:

```
gfxhub_v12_0.c:242   if (adev->gmc.translate_further) {
gfxhub_v12_0.c:243       tmp = REG_SET_FIELD(tmp, GCVM_L2_CNTL3, BANK_SELECT, 12);
gfxhub_v12_0.c:244-245   tmp = REG_SET_FIELD(tmp, GCVM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, 9);
gfxhub_v12_0.c:246   } else {
gfxhub_v12_0.c:247       tmp = REG_SET_FIELD(tmp, GCVM_L2_CNTL3, BANK_SELECT, 9);
gfxhub_v12_0.c:248-249   tmp = REG_SET_FIELD(tmp, GCVM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, 6);
gfxhub_v12_0.c:250   }
```

**El fragment size es 9 con `translate_further`, y 6 sin él.** En todos los hubs,
grafico y multimedia, con la misma condición.

Y el flag dice exactamente qué es `translate_further`:

```
gmc_v9_0.c:1936   adev->gmc.translate_further = adev->vm_manager.num_level > 1;
gmc_v9_0.c:1945   adev->gmc.translate_further = adev->vm_manager.num_level > 1;
gmc_v9_0.c:1957   adev->gmc.translate_further = adev->vm_manager.num_level > 1;
```

> **`translate_further` = el árbol de page tables tiene más de un nivel.**

## 3 · Y en GFX8 no se elige: se lee

```
gmc_v8_0.c:865   field = adev->vm_manager.fragment_size;
gmc_v8_0.c:866   tmp  = RREG32(mmVM_L2_CNTL3);
gmc_v8_0.c:869   tmp  = REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, field);
```

**GFX8 no consulta `translate_further`. Toma el valor del registro de hardware y
lo escribe en el registro de control.** Y donde se lee de hardware, la decisión la
toma el silicio, no el driver.

**Los `gfxhub_*` de GFX9+ sí eligen, con literales.**

## 4 · Las dos reglas coinciden en esta GPU, y eso es la corroboración

| | regla | valor en esta máquina |
|---|---|---|
| GFX9+ | `num_level > 1` ⇒ 9 | `num_level = 2` ⇒ **9** |
| GFX8 | se lee del registro | observado **9** |

**El log de arranque dice las dos cosas: `"2 levels, block size is 10-bit, fragment
size is 9"`.**

**Antes los tenía como dos hechos independientes del log. No lo son: son la misma
capacidad de hardware expresada dos veces, y las dos reglas dan el mismo número.**

**Eso no prueba que la regla de GFX9+ valiera en GFX8** —no hay código que la
aplique aquí— **pero sí que el 9 observado es el que la regla predice.** Es
`CORROBORATED`, no `PROVEN`.

## Lo que esto cierra de §A y §G

`127` dejó abierta la geometría de la traducción, y dijo que la explicación del
invalidate obligatorio podía ser granularidad de fragmento o caché de PDEs
obsoletas. **Ahora hay un dato que discrimina:**

```
128   fragment size 9  ->  512 páginas de 4 KiB  ->  2 MiB por entrada
128   PDE_CACHE_EFFECTIVE_SIZE  ->  nunca programado, valor de reset desconocido
```

**Los dos mecanismos siguen siendo candidatos y no los separo.** Lo que sí queda
cerrado es que **la granularidad de la caché de fragmentos es conocida y es
grande**, y que **la caché de PDEs es una variable independiente que el driver no
controla**.

**Y para un driver propio eso son dos campos distintos que leer y dos decisiones
distintas que tomar.** Si mi invalidate por dominio tiene que ser correcto, tengo
que asumir lo que el reset pone en `PDE_CACHE_EFFECTIVE_SIZE`, porque no tengo
manera de averiguarlo por software.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `PDE_CACHE_EFFECTIVE_SIZE` no lo escribe nadie | `PROVEN_ABSENT` (0 de 2787) |
| `L2_CACHE_BIGK_FRAGMENT_SIZE` sí, 49 veces | `OBSERVED` |
| Ningún fichero escribe ambos | `PROVEN` |
| Son knobs distintos, no un alias | `PROVEN_DERIVED` |
| El 9/6 es `translate_further`, no VMHub | `PROVEN` (`gfxhub_v12_0.c:242`) |
| `translate_further = num_level > 1` | `PROVEN` (3 sitios, `gmc_v9_0.c`) |
| GFX8 lee el valor, GFX9+ lo elige | `PROVEN` (dos estilos de código) |
| `num_level = 2` en esta GPU | `OBSERVED` (log de arranque) |
| La regla de GFX9+ predice el 9 observado | `CORROBORATED` |
| La granularidad de la traducción es 2 MiB | `PROVEN_DERIVED` |
| El valor de reset de `PDE_CACHE_EFFECTIVE_SIZE` | **`NOT_DETERMINED`** |
| Qué caché pesa más en el flush obligatorio | **`NOT_DETERMINED`** |

**Las dos últimas son las que siguen abiertas, y las dos son hardware.** La
segunda no se separa por software: ambos mecanismos explican el flush obligatorio
de `amdgpu_vm.c:1157` y ambos son compatibles con todo lo medido.

**Y la penúltima no es hardWARE con placa: es un `RREG32` de `0x501`, el mismo
observable que `128` dejó escrito para tres filas.** Sigue siendo el más rentable.

## Procedencia

- `STATIC` -- `gfxhub_v12_0.c:238-252`, `gmc_v8_0.c:865-870`, `gmc_v8_0.c:829`,
  `gmc_v9_0.c:1936`, `gmc_v9_0.c:1945`, `gmc_v9_0.c:1957`,
  `amdgpu_vm.c:1126`, `include/asic_reg/gmc/gmc_8_1_sh_mask.h`.
- Búsquedas con `grep -rn` sobre los 2787 ficheros del corpus, con nombre de
  fichero en la salida, y `comm` para el cruce de los dos símbolos.
- `OBSERVED` -- `"2 levels, block size is 10-bit, fragment size is 9"`, del log de
  arranque, de sesión anterior.
- Sin MMIO write, sin lectura de MMIO, sin TLB, sin módulos, sin debugfs.
- Encadenada con `127` (la caché L2 de fragmentos), `128` (los dos mecanismos de
  invalidate y los cinco campos sin escribir), `124`/`126` (la coherencia),
  `085` (el flush obligatorio), `103`/`104`/`106`.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`. No se editó ningún header.

## Nota de método

**Empecé por una pregunta de nomenclatura —"¿son el mismo campo?"— y acabó siendo
una pregunta de hardware.**

**Y el momento en que cambió fue leer el `if`, no el campo.** Un campo con dos
nombresruiting se habría delatado con una búsqueda de símbolos. Lo que cambió el
significado fue ver que el discriminante es `translate_further`, y que
`translate_further` es `num_level > 1`.

**El mismo campo, el mismo `9`, dos reglas distintas y un solo valor — y el valor
 sale de una capacidad que el log también imprime.** Eso no estaba en el plan y
 sale de leer la rama que no correspondía a esta GPU, que es la twelfth.

*La rama del `else` de un chip que no es el mío, leída para entender el `if`,
aporta más que el `if` mismo.* Y en `126` pasó igual: leí `AMDGPU_IB_POOL_DELAYED`
—que no usa esta GPU— y por eso entendí qué significaba `IMMEDIATE`.