# 171 · La distancia al driver no son 15 eslabones pendientes: es que el primero que falta es MMIO, y todo lo demás depende de él

```
CLASSIFICATION=MEASUREMENT+TOOLING · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.2.8 · HARDWARE_SCOPE=NONE
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_LOCAL=PROPIOS · MODIFICATIONS_CORPUS=0
RUNTIME=NOT_RUN · GPU INTACTA · CERROJOS=0
```

## Qué resuelve

`AGENTS.md` §OBJETIVO FINAL define la cadena que hay que poder construir. Nadie
sabía por dónde estaba, y la respuesta intuitiva —«nos faltan quince eslabones»—
es la lectura equivocada: no es un recuento de lo que falta, es un **problema de
orden**.

Medido con `tools/drvchain.py`, que quita comentarios y cadenas antes de buscar
y distingue cinco grados:

```
eslabón            grado         símbolo con cuerpo
PCI                IMPLEMENTADO  rx550_probe            rx550_drv.c:238
init               NOMBRADO      pci_request_regions    (se llama, no se define)
MMIO               AUSENTE       -
MC / VRAM          AUSENTE       -
GART               AUSENTE       -
GPUVM              PROBADO       rx550_vm_flush         rx550_pm4.c:1000
PTE / PDE          PROBADO       rx550_sdma_vm_set_pte_pde  rx550_pm4.c:337
VMID               NOMBRADO      vmid
TLB / invalidate   NOMBRADO      invalidate
PM4                PROBADO       rx550_pm4_dispatch_direct   rx550_pm4.c:182
                                    rx550_pm4_write_data       rx550_pm4.c:240
                                    rx550_pm4_mem_sync         rx550_pm4.c:153
IB                 AUSENTE       -
CP                 AUSENTE       -
rings              AUSENTE       -
sincronización     AUSENTE       -
interrupciones     AUSENTE       -
shaders            NOMBRADO      dispatch
memoria            AUSENTE       -
reset / recovery   AUSENTE       -
power / clocks     AUSENTE       -

19 eslabones: PROBADO 3, IMPLEMENTADO 1, NOMBRADO 4, AUSENTE 11
con cuerpo de función: 4 de 19   (21%)
```

## 1 · El dato útil no es el recuento: es dónde está el hueco

Todo lo que tiene cuerpo y test —PM4, emisión de IB, GPUVM, PTE/PDE— está
**casi al final** de la cadena. El primer eslabón sin nada de código es **MMIO**,
y todo lo que hay por encima de él depende de él:

```
sin registrar una lectura o una escritura no hay a quién leer o escribir
un registro → sin registro no hay anillo → sin anillo no hay IRQ, ni VM,
ni fence, ni shader
```

Es decir: hay una capa de emisión correcta y probada, y la capa que la hace
funcionar es un mapeo de BAR. **No es un problema de volumen, es de orden**, y
por eso la prioridad de la siguiente iteración la fija `MMIO`, no PM4 ni los
shaders, aunque tengan más apariencia de trabajo interesante.

## 2 · Lo que la herramienta-itself se rompió, y por qué casi cuela

Cinco fallos, todos en la primera hora de la herramienta, y **uno de ellos
produjo un número plausible y falso**:

1. **`19 de 19 AUSENTE`.** `SRC` era `("kernel", "driver")`, relativo a
   `07-DRIVER`, no a la raíz del proyecto. `cargar()` no encontraba **ningún**
   fichero y la cadena entera salía ausente con toda seguridad. Un driver que
   tiene cuatro cuerpos apareció con cero. Ahora hay un guardia que aborta si no
   carga nada, con el motivo escrito:

   ```
   drvchain: no se ha cargado NINGUN fichero desde [...] bajo [...]
              Sin este guardia la cadena entera sale AUSENTE y parece una
              medida del driver cuando es un fallo de la herramienta.
   ```

   Es el peor modo de fallo de un instrumento: parecer una medida y ser un
   error. Y es la forma que más se ha repetido en este proyecto: un número
   plausible sin denominador, y aquí ni siquiera con fuente.

2. **Dos eslabones acreditados por el mismo símbolo.** `rx550_ring_submit`
   estaba en `IB` y en `rings`. No es un IB: es código que se emitiría *dentro*
   de uno. Contarlo dos veces hacía parecer que hay dos eslabones implementados
   donde hay uno. La herramienta ahora detecta y declara los símbolos
   compartidos —aquí ninguno, y dice que la comprobación se ha hecho.

3. **Numeración de línea destruida.** Al rellenar comentarios con espacios se
   destruían los saltos de línea, y cualquier línea citada calculada sobre el
   texto enmascarado era **falsa**. Estaba a punto de citar cuatro posiciones en
   este hallazgo; la comprobación dio `dispatch_direct` en la línea 60 cuando en
   el fichero está en la 182. Ahora `_enmascarar()` conserva los saltos, y hay
   tres vectores que lo comprueban —uno de ellos rompe el enmascarado a propósito
   y falla con `9 vs 4`.

4. **Un número que salía de otro sitio.** Escribí «son 19 líneas de
   `pci_iomap`» sin haberlas medido, y 19 era el número de eslabones. Retirado,
   con la nota de por qué.

5. **Dos vectores que pasaban por el motivo equivocado.** Los de comentario y
   cadena seguían en verde **con el borrado de comentarios roto**, porque el
   anclaje `^[\w]` de `definido()` ya impedía que un comentario pareciera una
   definición: medían otra cosa. El vector que sí carga la pieza es un
   comentario multilínea con una definición en su interior cuyas líneas empiezan
   en la columna 0, y ése sí falla cuando se rompe.

Y una medición que sale de comprobarlo: **quitar cadenas no cambia ningún grado**.
Una cadena de C no puede abarcar líneas, así que su contenido nunca alcanza el
patrón que `definido()` reconoce. Se conservan porque hacen que `codigo` signifique
código, pero el grado depende de los comentarios y no de ellas. Está escrito en
el código para que nadie lo lea como una comprobación que carga peso.

## 3 · Lo que la escala de grados no dice

`PROBADO` significa que un test **toca** la función. Tocar no es ejercitar: una
prueba puede llamar a una función que devuelve 0 siempre y quedarse en verde. Los
tres eslabones `PROBADO` de esta tabla tienen pruebas que **comprueban bytes**, no
sólo que devuelven algo — pero eso lo dice `mutate.py`, no esta tabla, y son dos
mediciones distintas que no deben confundirse.

`NOMBRADO` significa que el símbolo aparece en un comentario. Y aquí hay un
matiz que importa: `init` sale `NOMBRADO` porque el driver **llama** a
`pci_request_regions()` sin definirlo, lo cual es lo correcto — esa función la
pone el núcleo. El grado mide cuerpos propios, y por eso un eslabón puede estar
bien implementado por el núcleo y salir `NOMBRADO` aquí. No es un defecto del
driver; es un límite de la escala, y está dicho para que nadie lo lea como uno.

## Procedencia

```
tools/drvchain.py                13 vectores, 4 con dientes comprobados
07-DRIVER/kernel/rx550_drv.c:238   rx550_probe
07-DRIVER/kernel/rx550_pm4.c:1000  rx550_vm_flush
07-DRIVER/kernel/rx550_pm4.c:337   rx550_sdma_vm_set_pte_pde
07-DRIVER/kernel/rx550_pm4.c:182   rx550_pm4_dispatch_direct
07-DRIVER/kernel/rx550_pm4.c:240   rx550_pm4_write_data
07-DRIVER/kernel/rx550_pm4.c:153   rx550_pm4_mem_sync
07-DRIVER/kernel/rx550_pm4.c:673   rx550_ring_submit
07-DRIVER/tests/test_pm4.c         208 checks, 0 failures
AGENTS.md §OBJETIVO FINAL          los 19 eslabones de la cadena
```

Las cuatro primeras posiciones se verificaron una a una contra el fichero con
`sed -n`, porque la herramienta las daba mal y ese era exactamente el motivo
para no fiarse de ella.

## CORRECCION POSTERIOR

Ninguna sobre lo afirmado. La tabla de arriba es reproducible con
`python3 tools/drvchain.py`, y sus cinco cifras —PROBADO 3, IMPLEMENTADO 1,
NOMBRADO 4, AUSENTE 11, 4 de 19 con cuerpo— se recalculan sobre el árbol en el
momento de leerlas. Un eslabón más y las cifras cambian, y por eso el hallazgo
las da con su fuente y no como veredicto permanente.
