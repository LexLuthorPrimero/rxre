# 1129 — «la IP version no se consulta» era verdad solo para el despacho: dentro del fichero que sí corre hay 19 consultas, y nadie las ha medido

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=sdma_v4_0.c:518,588,627,1025,1303,1740,1771,1869,1891,1906,1949,
                 2102,2110,2332,2633,2722   <- 19 usos de SDMA0_HWIP
         vcn_v4_0.c (3 usos de VCN_HWIP) · mmhub_v1_0.c (1 uso de ISP_HWIP)
ABRE=047-los-diez-selectores-y-el-limite-del-claim.md  (seccion "LO QUE NO DICE")
     046-la-version-de-ip-que-nunca-se-consulta.md
ESTADO=PROVEN-HUECO-DE-MEDICION · analisis estatico · sin root · sin GPU
```

## 0 · LO QUE `046` Y `047` DEMOSTRARON, Y DÓNDE TERMINA SU ALCANCE

`046` demostró, y con reason que este hallazgo no discute, que **el `case` del chip
resuelve por completo qué fichero se ejecuta** y que la versión de SDMA no llega
a leerse **para elegir**. `047` lo generalizó a los diez selectores y escribió su
propio límite:

> *Y no cierra el valor de las IP versions para el **COMPORTAMIENTO** del
> código que sí se ejecuta.*

Y luego hay una tabla, que es la que importa para este hallazgo:

```
  HWIP             estado         funcs   bloques
  SDMA0_HWIP       INALCANZABLE   1        7
  ...
  VCN_HWIP         INALCANZABLE   1        1
```

**La columna `funcs` es la clave.** `SDMA0_HWIP` aparece en **1** función con
**7** usos. Y ese 1 es la función de despacho, que es la que no se ejecuta.

## 1 · LA MEDICIÓN: 19 USOS MÁS, EN EL FICHERO QUE SÍ CORRE

`sdma_v4_0.c` es, según `046`, el fichero que se ejecuta en esta placa. Y
consulta `SDMA0_HWIP` **19 veces**:

```
  sdma_v4_0.c:518    switch (amdgpu_ip_version(adev, SDMA0_HWIP, 0)) {
  sdma_v4_0.c:588    switch (amdgpu_ip_version(adev, SDMA0_HWIP, 0)) {
  sdma_v4_0.c:627    if (amdgpu_ip_version(adev, SDMA0_HWIP, 0) == ...
  sdma_v4_0.c:1025   if (amdgpu_ip_version(adev, SDMA0_HWIP, 0) == ...
  sdma_v4_0.c:1303   switch (...)
  sdma_v4_0.c:1740   switch (...)
  sdma_v4_0.c:1771   if (... == IP_VERSION(4, 0, 0)) && ...
  sdma_v4_0.c:1869   if (...)
  sdma_v4_0.c:1891   if (... >= ...) && (... < ...)
  sdma_v4_0.c:1906   if (...)
  sdma_v4_0.c:1949   if (... == IP_VERSION(4, 2, 2) || ... == IP_VERSION(4, 4, 0))
  sdma_v4_0.c:2102   if (...)
  sdma_v4_0.c:2110   if (... != ...)
  sdma_v4_0.c:2332   switch (...)
  sdma_v4_0.c:2633   if (... >= IP_VERSION(4, 4, 0))
  sdma_v4_0.c:2722   switch (...)
```

**19 contra 7.** Y no es el mismo tipo de uso:

| tipo | dónde | qué decide |
|---|---|---|
| **selector** | la función de despacho, inalcanzable | **qué fichero** se ejecuta |
| **comportamiento** | los 19 de `sdma_v4_0.c`, alcanzable | **qué hace** el fichero elegido |

> **La versión de IP no elige el código, y aun así decide el código.** Eso no es
> una contradicción: son dos preguntas distintas hechas con el mismo dato, y
> `046` mide la primera. Este hallazgo mide que **la segunda tiene 19 puntos de
> decisión en el fichero del page-transfer engine de esta tarjeta.**

## 2 · POR QUÉ ESTO NO ES UN DETALLE, ES LA SEGUNDA MITAD DEL CAMINO

Y aquí es donde se vuelve relevante para este proyecto. El mismo `046` escribe,
en su §"LO QUE ESTA HERRAMIENTA NO DICE":

> *Esto no decide NADA sobre el hardware. Solo sobre que codigo del driver se
> ejecuta. La semantica del MMU, del page walker y del TLB sigue siendo
> NOT_PUBLISHED.*

Y en `047`:

> *Esta es la lista REAL de lo que queda por medir: no 629 usos repartidos por
> el driver entero, sino los que caen en el siliconio de esta placa.*

**`047` acierta la lista real y la midió mal.** MEDIDO los ficheros ASIC-específicos
que ejecuta esta GPU, y sus usos de `amdgpu_ip_version`:

```
  gfx_v8_0.c        0
  gmc_v8_0.c        0
  gfxhub_v1_0.c     0
  sdma_v4_0.c      19      <-- ESTE
  vcn_v4_0.c        3
  mmhub_v1_0.c      1
```

`047` afirma «Ninguno de los ficheros ASIC-especificos consulta
`amdgpu_ip_version()`» y lista cuatro comprobados: `gfx_v8_0.c`, `gmc_v8_0.c`,
`sdma_v3_0.c`, `tonga_ih.c`.

**Los cuatro están en cero. Pero `sdma_v3_0.c` no es el fichero que corre** —lo
dice el propio `046`— y el que corre, `sdma_v4_0.c`, **no estaba en la lista**.

> El cero de `047` es real, pero se midió sobre el fichero equivocado, por
> el mismo motivo que `023` leyó `sdma_v3_0.c`: porque el nombre del fichero se
> parecía más con el ASIC. **Es el mismo error, cuatro documentos después, hecho
> por el camino opuesto.**

## 3 · LA DISTINCIÓN, QUE ES LO QUE FALTA INSTRUMENTAR

Esto es lo que `unreach.py` **no puede** ver, y la razón está en su propio
límite declarado:

> *El grafo de llamadas es TEXTUAL. No preprocesa, asi que una llamada a traves
> de un macro de funcion, o por puntero, no aparece.*

`unreach` responde a *«¿se ejecuta esta función?»*. No responde a *«¿qué valor
toma este parámetro dentro de la función que sí se ejecuta?»*. Y la segunda es
una pregunta de **constante**, no de alcanzabilidad: se mide leyendo los
`case` de un `switch` dentro de un fichero que sí corre.

Lo que haría falta, y es una herramienta distinta, no una ampliación de `unreach`:

```
  para cada IP version consultada dentro de un fichero ALCANZABLE
     ¿qué valores distingue el switch?
     ¿qué comportamiento cambia entre ellos?
     ¿el camino que nos interesa (PM4, IB, page tables, VMID) cae
      dentro de algún switch de esos?
```

La **última** pregunta es la que decide si esto importa para este driver, y es
la que no está medida.

## 4 · LO QUE SÍ SE PUEDE DECIR HOY, Y LO QUE NO

**Se puede enumerar** (`PROVEN`): 19 puntos de decisión de comportamiento en
`sdma_v4_0.c`, 3 en `vcn_v4_0.c`, 1 en `mmhub_v1_0.c`. Con sus líneas.

**No se puede decir** (`NOT_DETERMINED`):

- **qué valor toma `SDMA0_HWIP` en esta tarjeta**. Requiere leer un registro, y
  aunque `046` demostró que no se lee para el despacho, eso no dice que no se
  pueda leer para el comportamiento.
- **cuál de los 19 cambia algo en el camino del page transfer.** Ninguno ha sido
  trazado hasta el emisor de PTE.
- y por tanto **si alguno de los 19 es un bug para esta ASIC**, que es la
  pregunta que de verdad importa.

## 5 · LA PREDICCIÓN QUE HICE, Y QUE AL MIRARLA ES FALSA

La primera versión de este documento afirmaba que dos de los 19 usos eran
candidatos a cerrar sin hardware porque comparan contra valores concretos. Cité
`1949-1950`:

```c
sdma_v4_0.c:1949-1950
  if (amdgpu_ip_version(adev, SDMA0_HWIP, 0) == IP_VERSION(4, 2, 2) ||
      amdgpu_ip_version(adev, SDMA0_HWIP, 0) == IP_VERSION(4, 4, 0))
        amdgpu_sdma_destroy_inst_ctx(adev, true);
  else
        amdgpu_sdma_destroy_inst_ctx(adev, false);
```

**Mirada la función completa, es `sdma_v4_0_sw_fini()` — el camino de parada del
SDMA.** No es el emisor de PTE, no es el page transfer y no tiene nada que ver
con el MMU. La predicción era plausible y era falsa: cité una condición
comparable sin comprobar **en qué función** estaba.

Y el dato bueno es que, al comprobar los diecinueve, sale esto:

```
  linea  funcion                                        ¿toca el camino?
  -----  --------------------------------------------  ---------------------
   518   sdma_v4_0_init_golden_registers                 no
   588   sdma_v4_0_setup_ulv                             no
   627   sdma_v4_0_init_microcode                       no
  1025   sdma_v4_0_ctx_switch_enable                    no
  1303   sdma_v4_0_init_pg                               SI — la cola de paging
  1740   sdma_v4_0_fw_support_paging_queue               SI — la cola de paging
  1771   sdma_v4_0_early_init                            no
  1869   sdma_v4_0_sw_init                               no
  1891   sdma_v4_0_sw_init                               no
  1906   sdma_v4_0_sw_init                               no
  1949   sdma_v4_0_sw_fini                               no
  2102   sdma_v4_0_process_trap_irq                      no
  2110   sdma_v4_0_process_trap_irq                      no
  2332   sdma_v4_0_set_powergating_state                 no
  2633   sdma_v4_0_set_buffer_funcs                      no
  2722   sdma_v4_0_set_ras_funcs                         no
```

**Ninguno de los diecinueve está en el emisor de PTE/PDE.** Dos tocan la cola de
paging, que es el camino de la cola nueva de la GPU, y los trece restantes son
golden registers, microcode, power gating, RAS y traps.

> Eso **debilita la alarma**, y es el resultado honesto: el page transfer de esta
> placa no ramifica sobre `SDMA0_HWIP` en el punto donde se emiten los PTEs. Lo
> que sí ramifica sobre esa versión es la **topología de la cola de paging**, que
> decide cómo se encola, no qué se escribe en la tabla de page tables.
>
> Y por eso el hueco que abrí es **menor** de lo que parecía al escribirlo: no
> son 19 decisiones de las que dependa la corrección de page tables, son 19
> decisiones de las que dependen el arranque, el power gating y el trap handling.
>
> **Un hallazgo que se corrige a sí mismo en el mismo documento no se borra: se
> deja con la corrección visible.** Es la diferencia entre un registro y un
> documento que conserva el error junto con su arreglo.

## 6 · LO QUE ESTE HALLAZGO NO HACE

- **No dice que los 19 usos sean un problema.** Dice que existen y que nadie los
  ha medido. Son 19 decisiones de comportamiento en código que corre, en un
  fichero compartido con toda la familia GFX8 — que es un `ip_block` que también
  sirve a Fiji y Polaris10— y eso **puede estar bien**.
- **No reabre `047`**. Su tabla es correcta **para lo que dice medir**, que es el
  despacho. Lo que este hallazgo añade es que su frase «la lista REAL de lo que
  queda» apuntaba a un cero, y ese cero tenía un hueco en la lista de ficheros
  comprobados.
- **No toca `tools/unreach.py` ni los hallazgos de nadie.** Es de otra sesión y
  el árbol tiene sus ficheros modificados.

## 7 · ESTADO

```
  usos de amdgpu_ip_version en ficheros que esta GPU ejecuta
     sdma_v4_0.c     19   (todos SDMA0_HWIP)
     vcn_v4_0.c       3   (VCN_HWIP)
     mmhub_v1_0.c     1   (ISP_HWIP)
     gfx_v8_0.c       0
     gmc_v8_0.c       0
     gfxhub_v1_0.c    0

  valor de cada IP version en esta tarjeta    NOT_DETERMINED -> leer registro
  si alguno de los 19 afecta al page transfer NOT_DETERMINED -> trazar a mano
  al menos uno verificable sin hardware       SI (1949-1950)  -> sin cerrar

  abre el limite declarado por 047, y no lo reemplaza
  GPU     INTACTA
  sudo    NO usado
```