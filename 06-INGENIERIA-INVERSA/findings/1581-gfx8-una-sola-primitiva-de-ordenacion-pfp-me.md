# 1581 — GFX8 tiene **una sola** primitiva de ordenación PFP↔ME y la emite **una sola vez**; y existe un observable nativo de "el PFP está parseando paquetes" que **nada en este árbol lee**

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=INVENTARIO + OBSERVABILIDAD
CLASSIFICATION=EVIDENCIA-POR-LECTURA-DE-CÓDIGO+NOT_FOUND CON NOMBRE DE BÚSQUEDA EXPLÍCITO
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno (solo lectura)
MODIFICATIONS=1580 §"Lo que esto abre"  (la linea que abria,  aqui cerrada)
MODIFICATIONS=1225 §invariante del count  (13a comprobacion)
MODIFICATIONS=1546  (gca/ es nativo:  el mismo criterio de discriminacion)
MODIFICATIONS=1578 §4  (el grafo de includes como criterio de cabecera)
ABRE     la linea que 1580 dejo abierta:  primitivas de sincronizacion PFP<->ME
DA       un OBSERVABLE de solo lectura,  de clase READ_ONLY,  nativo de GFX8,
         que este driver no usa  y que un driver propio si puede usar
```

## 1 · La primitiva: una, y es `PACKET3_PFP_SYNC_ME`

```text
  amdgpu/vid.h:200   #define PACKET3_PFP_SYNC_ME   0x42
```

Sin macros de campo. Y se emite **con `count = 0`**: no tiene payload.

```text
  gfx_v8_0.c:6212   amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
  gfx_v8_0.c:6213   amdgpu_ring_write(ring, 0x0);
```

Ese `0x0` de la línea siguiente es el segundo dword y cuenta como el `count`
del invariante de `1225`: payload de 1 dword, count = 0. **Decimotercera
comprobación**, y la primera con payload de un solo dword.

## 2 · Los ocho sitios del árbol son el mismo sitio, ocho veces

```text
  gfx_v6_0.c:2394      if (usepfp)   ->  :2396
  gfx_v7_0.c:3158      if (usepfp)   ->  :3160
  gfx_v8_0.c:6210      if (usepfp)   ->  :6212        <-- NUESTRO
  gfx_v9_0.c:5621      if (ring->funcs->type == AMDGPU_RING_TYPE_GFX)  -> :5623
  gfx_v10_0.c:8764     idem          ->  :8766
  gfx_v11_0.c:6062     idem          ->  :6064
  gfx_v12_0.c:4550     idem          ->  :4552
  gfx_v12_1.c:3446     idem          ->  :3448
```

Los ocho están en la **misma función** —el `vm_flush` de cada generación— y los
ocho llevan el mismo motivo escrito al lado:

```text
  /* compute doesn't have PFP */
  /* sync PFP to ME, otherwise we might get invalid PFP reads */
```

**Y son las únicas 8.** Dos cálculos, no una suposición:

```text
  PACKET3_PFP_SYNC_ME      8 ocurrencias en el arbol
  PACKET3_PFP_SYNC_VC      0
  PACKET3_PFP_SYNC_CNTL    0
```

En `vid.h` hay **un solo opcode cuyo nombre contiene `PFP`**:

```text
  vid.h:200   PACKET3_PFP_SYNC_ME  0x42
```

**En el vocabulario de paquetes de GFX8 no hay ninguna otra primitiva de
sincronización entre PFP y ME.** No una con otro nombre: ninguna. Eso es un hecho
sobre el inventario, y es el tipo de dato que un driver propio necesita: si esa es
la única palanca, el orden entre el PFP y el motor de comandos **no es ajustable**,
solo se puede emitir o no.

### El límite de la búsqueda, dicho explícitamente

Intenté comprobar si las generaciones modernas habían añadido más, buscando
`PACKET3_*SYNC*` y `*PFP*` en los headers `include/asic_reg/gc/`. **No obtuve nada, y
no lo interpreto como ausencia:**

```text
  los headers gc_10_1_0_default.h  y  gc_12_1_0_*.h
      NO contienen NINGUN token PACKET3_*  (medido: el grep devuelve vacio)
  llevan direcciones de registro y mascaras de campo,  no el diccionario de paquetes
```

El diccionario de paquetes de las generaciones nuevas vive en otro sitio —`nvd.h`,
la tabla de descubrimientos— y **no lo he buscado**. Queda `NOT_DETERMINED`, no
`PROVEN_ABSENT`. Es la cuarta vez hoy que un `grep` vacío podía haberme producido una
afirmación falsa y no lo ha hecho: en `1580` un vacío mío sí lo produjo.

## 3 · En nuestra placa, exactamente una vez, y con una condición concreta

```c
  gfx_v8_0.c:6191  static void gfx_v8_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
  gfx_v8_0.c:6192                                                  uint32_t vmid,
  gfx_v8_0.c:6193                                                  uint64_t pd_addr)
  gfx_v8_0.c:6194  {
  gfx_v8_0.c:6194      int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);
  gfx_v8_0.c:6196      amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);
  gfx_v8_0.c:6198      /* wait for the invalidate to complete */
  gfx_v8_0.c:6199      PACKET3(PACKET3_WAIT_REG_MEM, 5)   con FUNCTION(0)=always
  gfx_v8_0.c:6203      mmVM_INVALIDATE_REQUEST ,  0 ,  0 ref ,  0 mask ,  0x20 poll
  gfx_v8_0.c:6209      /* compute doesn't have PFP */
  gfx_v8_0.c:6210      if (usepfp) {
  gfx_v8_0.c:6211          /* sync PFP to ME, otherwise we might get invalid PFP reads */
  gfx_v8_0.c:6212          PACKET3(PACKET3_PFP_SYNC_ME, 0)
  gfx_v8_0.c:6214      }
  gfx_v8_0.c:6215  }
```

La condición es **"el anillo es de tipo GFX"**, es decir: tiene PFP. Los anillos de
cómputo y el KIQ no lo tienen, y por eso no se les emite. Y `usepfp` se calcula en
`:6194`, antes de usarlo en `:6210` — es un solo valor para toda la función.

**La secuencia completa que el driver emite para una invalidación de TLB en el anillo
de gráficos, y que es la unidad que un driver propio tiene que reproducir, es:**

```text
  1  amdgpu_gmc_emit_flush_gpu_tlb(vmid, pd_addr)
  2  PACKET3_WAIT_REG_MEM, count=5,  FUNCTION=always,  poll=0x20      espera por tiempo
  3  PACKET3_PFP_SYNC_ME, count=0                                      ordena PFP tras ME
```

## 4 · Y el payout: hay un observable de "el PFP está vivo" que nadie usa

Encontrado de rebote, buscando qué más menciona PFP en los headers modernos:

```text
  include/asic_reg/gca/gfx_8_0_d.h:563
      #define mmCP_BUSY_STAT                        0x219f
  include/asic_reg/gca/gfx_8_0_sh_mask.h:3555
      #define CP_BUSY_STAT__PFP_PARSING_PACKETS_MASK  0x80
  include/asic_reg/gca/gfx_8_0_sh_mask.h:3556
      #define CP_BUSY_STAT__PFP_PARSING_PACKETS__SHIFT 0x7
```

Tres cosas de valor:

**Una: es NATIVO de GFX8.** Está en `gca/`, no prestado —que es el mismo criterio con
el que `1546`/y en `1578` han discriminado el resto del juego de registros.

**Dos: el bit significa exactamente lo que un driver necesita saber.** "El PFP está
parseando paquetes". Es un **observable de solo lectura**, clase `READ_ONLY`: no
escribe nada, no invalida, no puede estropear el estado. Y es la alternativa
**pregunta-en-lugar-de-ordenar** a `PFP_SYNC_ME`, que es disparar y olvidar.

**Tres: este driver no lo usa.** Medido en `amdgpu/*.c` y `pm/`:

```text
  gfx_v9_0.c:160     SOC15_REG_ENTRY_STR(GC, 0, mmCP_BUSY_STAT)
  gfx_v10_0.c:287    SOC15_REG_ENTRY_STR(GC, 0, mmCP_BUSY_STAT)
  gfx_v11_0.c:142    SOC15_REG_ENTRY_STR(GC, 0, mmCP_BUSY_STAT)
  gfx_v12_0.c:94     SOC15_REG_ENTRY_STR(GC, 0, mmCP_BUSY_STAT)
  gfx_v9_4_3.c:74    SOC15_REG_ENTRY_STR(GC, 0, mmCP_BUSY_STAT)
  gfx_v8_0.c         NINGUNA APARICION
```

**Y una corrección que tuve que hacerme a mitad de esta medición:** al ver esas cinco
líneas iba a escribir *"las generaciones modernas sí leen ese registro y GFX8 no"*.
No es cierto. Lo que hay en `gfx_v9_0.c:160` y compañía es una **tabla de asignación
de offsets** —una lista de `SOC15_REG_ENTRY_STR` que registra direcciones para la
traducción de registros, dozens of lines of the same kind, `mmCP_STALLED_STAT1`,
`mmCP_RB_BASE`, `mmCP_RB0_RPTR`…—. **No es un acceso al registro.** El registro no lo
lee nadie en ninguna generación de este árbol.

Lo correcto es:

```text
  mmCP_BUSY_STAT existe y es NATIVO de GFX8   (0x219F,  bit 7 = PFP parseando)
  en GFX8 no hay ninguna lectura              (0 apariciones en todo amdgpu/ y pm/)
  en GFX9+ tampoco hay lectura;  solo aparece en tablas de OFFSETS
  por tanto:  PENDING.  Ningun codigo de este arbol lo consulta
```

Y queda en `DEFERRED` la pregunta de si el bit es fiable para esperarlo en bucle. **No
lo sé**, y no lo voy a suponer: no hay lectura, no hay prueba y no hay hardware. Lo que
afirmo es que **el observable existe, es de solo lectura, y está libre.**

## 5 · Por qué esto importa para un driver propio, y lo que no resuelve

```text
  lo que si:
    - la secuencia de invalidacion de TLB en el anillo de graficos,  paso a paso,
      con los valores exactos.  Es copiable y verificable
    - hay UNA sola primitiva de ordenacion PFP<->ME.  No hay peralte
    - existe un bit de estado del PFP,  nativo y de solo lectura,  que AMD no usa.
      Es la unica via que veo para SUSTITUIR un shoot-and-forget por un sondeo

  lo que NO:
    - que significa la PTE.  Sigue sin resolverse y no se resuelve con esto
    - si CP_BUSY_STAT es fiable como condicion de salida de un bucle.  DEFERRED
    - si el hardware de GFX8 tiene un bit de "invalidacion completada".  Lo que
      se ve es que el driver NO lo usa  y espera por tiempo,  lo que es
      indicio de que no lo hay  pero no prueba de que no exista
```

## 6 · Procedimiento y alcance

```text
PREGUNTA   que primitivas de sincronizacion PFP<->ME existen en GFX8,  cuando las
           emite el driver,  y si hay un observable de estado del PFP
FUENTES    amdgpu/vid.h,  seccion de opcodes PACKET3
           grep PACKET3_PFP_SYNC_ME en TODO el arbol con contexto de 6 lineas
           conteo explicito de los otros dos nombres  (VC, CNTL)
           los tres sitios de gfx_v8_0.c con contexto
           gca/gfx_8_0_d.h  y  gca/gfx_8_0_sh_mask.h
           grep CP_BUSY_STAT en amdgpu/*.c y pm/,  y lectura del contexto en GFX9
MEDIDO     PACKET3_PFP_SYNC_ME = 0x42,  count=0,  sin payload,  1 solo en GFX8
     8 sitios en el arbol = 8 familias,  todos en vm_flush,  misma condicion
     la condicion en GFX8 es  ring->funcs->type == AMDGPU_RING_TYPE_GFX
     PACKET3_PFP_SYNC_VC = 0 ;  PACKET3_PFP_SYNC_CNTL = 0
     vid.h tiene UN solo opcode con PFP en el nombre
     la secuencia completa de vm_flush en el anillo de graficos,  en 3 pasos
     payload de 1 dword con count=0  ->  invariante de 1225,  13a comprobacion
     mmCP_BUSY_STAT = 0x219F,  NATIVO en gca/,  CP_BUSY_STAT__PFP_PARSING_PACKETS
     bit 7,  mascara 0x80
     0 lecturas en todo el arbol.  Las 5 apariciones en GFX9+ son tablas de
     OFFSETS (SOC15_REG_ENTRY_STR),  no accesos.  CORREGIDO a mitad de medir
DESVIO MIO  uno,  y del mismo patron que los otros tres de hoy
    iba a afirmar "las generaciones modernas si leen ese registro y GFX8 no"  al
     ver cinco coincidencias de token.  Eran tablas de offsets,  no accesos.  Un
     token que coincide no es una operacion que se ejecuta
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
```

## 7 · Lo que sigue

```text
  huecos de riesgo cero de mi lista de siete:  4 · 5 · 7
    y ninguno de los tres tiene para esta placa el valor que tenia este.  El 4
    compara structs de OTRAS GPU;  el 5 son 0 emisiones sin discriminante por uso;
    el 7 es metodologico, sobre RXRE.  Los mido por orden de la lista,  pero sin
    esperar que cambien una decision sobre esta placa

  nuevo,  con valor directo sobre esta placa:
    DEFERRED pero con la via escrita:  sondear CP_BUSY_STAT bit 7  en lugar de
    emitir PFP_SYNC_ME.  Necesita hardware  y  no lo hago sin tu OK

  y sigue en pie lo unico que cierra soft_regs_start:  el valor de
    SMC_RAM[0x20030].  Con la receta del driver (1579),  las dos direcciones
    confirmadas en los tres linajes,  y pendiente de tu OK
```