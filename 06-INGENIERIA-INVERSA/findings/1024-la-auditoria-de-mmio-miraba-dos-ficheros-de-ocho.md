# 1024 · La auditoría de acceso a hardware miraba dos ficheros de ocho, y su comprobación de MMIO no podía fallar en x86-64

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC` · `CORPUS=RESEARCH/kernelbuild/linux-7.1.3`
`WORK_CLASS=REPAIR/CONTROLLED` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## Qué se afirmaba

`test_static.sh` publicaba, en cada corrida y en el informe que el usuario lee:

```
AUDIT · acceso a hardware (debe estar AUSENTE)
  PASS  HW    ninguna llamada de acceso a hardware en el cuerpo
  PASS  HW-L  el .ko no referencia ningún símbolo de acceso a hardware
  PASS  MMIO-M pci_iomap presente en el cuerpo (mapeo de STATE 3)
```

## Qué se midió

**Dos cosas, y las dos dan lo mismo.**

### 1. La HW miraba dos ficheros de ocho

```sh
BODY=$(strip_comments "$SRC"; strip_comments "$DRV/pci_resource.c")
```

`$SRC` es `rx550_target.c`. Son **dos ficheros elegidos a mano**, de los ocho
que hay en `obj-m` después del finding 1023. Los otros seis no los miraba nadie.

Y no era una omisión menor. El fichero que hace MMIO de verdad es
`rx550_mmio_access.c`:

```
398: static uint32_t rx550_slot_read(void *slot)
400: 	return readl((volatile void *)slot);
403: static void rx550_slot_write(void *slot, uint32_t v)
405: 	writel(v, (volatile void *)slot);
```

Es decir: la auditoría decía «ninguna llamada de acceso a hardware», y la única
lectura del hardware del módulo estaba **fuera de su alcance**. Y es alcanzable:
`rx550_target.c:257-259` la llama en `probe()` bajo el parámetro
`rx550_probe_read`.

### 2. La HW-L no podía dispararse en esta arquitectura

La comprobación de nivel de enlace buscaba estos símbolos sin resolver en el
`.ko`:

```
__readl   __writel   __readq   __writeq
```

Medido con un objeto de kernel mínimo que llama a las cuatro, compilado con las
opciones reales de kbuild:

```c
#include <linux/io.h>
unsigned long f(void *p) { return (unsigned long)readl(p) + (unsigned long)readq(p); }
void g(void *p, unsigned long v) { writel((u32)v, p); writeq(v, p); }
```

```
$ nm -u p.o
                 U __fentry__
                 U __x86_return_thunk
```

**Ninguna de las cuatro aparece.** En x86-64 `readl`/`writel`/`readq`/`writeq`
se expanden en línea contra el espacio de MMIO del proceso, no son llamadas.
La lista estaba escrita como si la arquitectura fuera otra.

Un control que no puede fallar no es un control: ocupa sitio en el informe, da
la sensación de que el MMIO está vigilado, y es exactamente el tipo de cosa que
hace que nadie mire el resto del informe.

## La diferencia entre las dos: el objeto, no el símbolo

El invariante real **no** es «no hay `readl` en el módulo». El accessor tiene que
leer; si no, no hay driver. El invariante es:

> **Solo el accessor declarado toca el dispositivo, y ningún objeto más.**

Eso se comprueba sobre el **cuerpo de cada objeto**, no sobre sus símbolos, y
por eso sí puede fallar.

## Lo que hace ahora

**La lista de objetos se extrae del `Makefile`, no se escribe a mano.**

```sh
OBJS_RAW=$(awk '/^rx550_drv-objs[ \t]*:=/{
                   for (i=1; i<=NF; i++) if ($i ~ /\.o$/) { gsub(/\\/,"",$i); print $i } }' "$DRV/Makefile")
```

Escribirla a mano sería el mismo defecto un nivel más arriba: el día que
`obj-m` cambie, la lista no cambiaría y el audit seguiría contando objetos que
ya no están. Se comprueba que **todos** tienen fuente:

```
PASS  COB  8 objetos en obj-m, todos con fuente y ninguno sin auditar
```

**La excepción es explícita y tiene que seguir teniendo motivo.**

```sh
MMIO_EXENTOS="rx550_mmio_access.c"
```

Con la comprobación de que ese fichero **sigue** teniendo MMIO. Si dejara de
tenerlo, la lista estaría admitiendo a un fichero que no necesita excepción y
la comprobación habría perdido su motivo:

```
PASS  COB  el accessor declarado (rx550_mmio_access.c) sigue siendo el que tiene MMIO
```

**Ningún objeto fuera de la excepción puede tocar el dispositivo.**

```
PASS  HW-OBJ ningun objeto fuera del accessor toca el dispositivo (8 objetos)
```

Y los cuatro símbolos que no pueden aparecer en `nm -u` salen de la lista de
`HW-L`, con la medición que lo explica en el propio sitio. Lo que sustituye a
esa lista es `HW-OBJ`, que sí puede fallar.

## La demostración: el check sí falla

Copia del árbol en `/tmp`, con un `writel` inyectado en `rx550_pdb0.c`, que no
es el accessor:

```
  PASS  HW   ninguna llamada de acceso a hardware en el cuerpo     <- la vieja, no lo ve
  PASS  COB  8 objetos en obj-m, todos con fuente y ninguno sin auditar
  FAIL  HW-OBJ 'writel' aparece fuera del accessor, en rx550_pdb0.c
  FAIL  HW-OBJ ningun objeto fuera del accessor toca el dispositivo (8 objetos)
```

Nombra el fichero y el símbolo, y el script sale con código 1. La misma
mutación con la auditoría anterior pasaba limpia: `rx550_pdb0.c` no estaba en su
alcance.

## Dos errores míos, en el mismo bloque, y por qué quedan escritos

**El signo del resultado invertido.** `chk` toma un código de salida donde 0 es
«pasa». La comprobación del accessor hace `hit_acc=1` cuando **ha encontrado**
el MMIO, y pasaba `$hit_acc` tal cual. Con el accessor teniendo `readl` en la
línea 215 del cuerpo limpio, la comprobación salía en FAIL.

Un check con el signo cambiado es peor que un check sin hacer: parece que mide
algo y mide lo contrario, y el informe dice FAIL cuando la realidad es la
correcta.

**`\n` dentro de comillas dobles en bash.** La primera versión armaba el fichero
intermedio con `"$cuerpo_obj$cuerpo"`. Dentro de comillas dobles, `\n` es una
barra y una ene, no un salto de línea: todo quedaba en una sola línea y el `awk`
que separa ficheros no encontraba nada. Se detectó porque el `COB` salía en FAIL
con datos que el `gcc` había limpiado bien.

Es la tercera vez en esta sesión que un Supuesto sobre cómo se comporta una
herramienta resulta falso. Las tres se detectaron porque había un oráculo
independiente —el recuento de aserciones, el hash del fichero, la salida de
`nm`— y no porque alguien lo mirara con atención.

## Estado final

```
17 suites, con_problema=0
resumen estático: 37 PASS, 0 FAIL     (antes 34: +COB x2, +HW-OBJ)
make EXIT=0
```

## Lo que este hallazgo no dice

- **No dice que el MMIO esté bien acotado.** Dice que ahora hay una
  comprobación que puede fallar y que hoy no falla. Que mañana alguien añada
  un `writel` en un cuarto sitio es otra cosa, y ahora se vería.
- **No audita los ficheros que no están en `obj-m`.** Los tres que quedan fuera
  por diseño (`rx550_target.c` es kernel, `vmid1_pgt_backing.c` asigna con
  `calloc`, `ib_bridge.c` depende de `pm4.h`) tienen su propia clasificación,
  registrada en el finding 1023.
- **No carga el módulo.** Sigue sin intentarse: `amdgpu` posee el dispositivo.

## Trazabilidad

- Fichero reparado: `04-IMPLEMENTACION/rx550-driver/tests/test_static.sh`
- Comprobación muerta, medida: `nm -u` de un objeto con `readl`/`writel`
- Cobertura, medida: 8 objetos en `obj-m`, 2 auditados antes, 8 ahora
- Hallazgo relacionado: 1023 (el que puso los ocho objetos en `obj-m`)
- Prefijo de numeración: 1024, reservado antes de escribir