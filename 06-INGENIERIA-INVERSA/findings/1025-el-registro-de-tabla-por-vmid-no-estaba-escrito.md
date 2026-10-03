# 1025 · El registro de tabla de páginas de un VMID no estaba escrito en ninguna parte, y la regla tiene un corte en 8

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC` · `CORPUS=RESEARCH/kernelbuild/linux-7.1.3`
`WORK_CLASS=IMPLEMENTATION` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=4`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## El hueco

`rx550_mmio_access.h` declara 16 mnemonicos de VM en `rx550_mmio_regs[]`, y
`test_regs` verifica **cada uno por separado** contra `gmc_8_1_d.h`: nombre,
índice, `index * 4 == byte_offset`, ancho, orden ascendente.

Eso no demuestra que el contexto 1 esté en el registro correcto. Una tabla con
16 mnemonicos, todos bien escritos uno a uno, puede estar en 16 índices
equivocados a la vez, y ninguna comprobación por entrada lo nota. Lo que
demuestra la corrección es **la relación entre ellos**, y esa relación no estaba
escrita en ningún fichero del componente.

Búsqueda de los consumidores, sobre el árbol, excluyendo los propios ficheros de
la capa y sus tests:

```
$ for s in rx550_pdb0_init rx550_pdb0_map_va rx550_vmid0 rx550_pte_encode \
           rx550_submission rx550_gart_write; do
    printf "%-22s desde el driver: %s\n" $s \
      "$(grep -l "\b$s\b" *.c | grep -vE 'pdb0|vmid|submission|ib_|gart_write' | tr '\n' ' ')"
  done
rx550_pdb0_init        NINGUNO
rx550_pdb0_map_va      NINGUNO
rx550_vmid0            NINGUNO
rx550_pte_encode       NINGUNO
rx550_submission       NINGUNO
rx550_gart_write       NINGUNO
```

## La regla, del corpus y solo del corpus

`gmc_v8_0.c:669-681`, `gmc_v8_0_emit_flush_gpu_tlb()`:

```c
if (vmid < 8)
	reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;
else
	reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;
amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);

/* bits 0-15 are the VM contexts0-15 */
amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid);
```

Y los índices, `gmc_8_1_d.h:636-655`:

```
0x54f  mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR
0x550  mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR
 ...    (contiguos hasta 0x556 = contexto 7)

0x50e  mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR
0x50f  mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR
 ...    (contiguos hasta 0x515 = contexto 15)
```

Tres hechos, y los tres importan:

1. **La regla es posicional**: `base + vmid`, no una tabla.
2. **Tiene un corte en 8**, escrito con un `if` explícito.
3. **Los dos bloques no son contiguos ni contiguos en orden**: el bloque 8..15
   está **por debajo** del 0..7 (0x50e < 0x54f). Es lo contrario de lo que da
   la intuición.

## Qué falla si se implementa la regla sin el corte

Se implementó mal a propósito, en una copia, y se midió:

```
$ # version sin el corte:   if (vmid < 16) return 0x54f + vmid;
  FAIL  C1 vmid  8 -> indice 0x557 (corpus 0x50e)  (0x557 != 0x50e)
  FAIL  C1 vmid  9 -> indice 0x558 (corpus 0x50f)  (0x558 != 0x50f)
  FAIL  C1 vmid 10 -> indice 0x559 (corpus 0x510)  (0x559 != 0x510)
  ...
  FAIL  C1 el bloque 8..15 arranca en 0x50e, NO en 0x557
  32 pass, 12 fail
```

Y el detalle que convierte el fallo en dano: **`0x557` es
`mmVM_CONTEXT0_PAGE_TABLE_START_ADDR`**, y `0x558` es el mismo registro para
el contexto 1.  Programar la base de la tabla del VMID 8 acaba escribiendo en
el registro de INICIO DE LA APERTURA.  Y no falla al hacerlo: el indice cabe
en BAR5, el acceso tiene exito, y el error aparece mucho despues, cuando una
pagina se mapea mal y nadie sabe por que.

Es el mismo modo de fallo que `test_mmio_access` ya documenta con
`mmCP_RB0_RPTR`, donde el indice no es el offset; aqui el modo es peor, porque
el valor equivocado SI es un registro, asi que la escritura es plausible.

## Qué se añadió

Dos funciones puras, en `rx550_mmio_access.{h,c}`, y su test:

```c
uint32_t rx550_mmio_ctx_pt_base_index(unsigned vmid);
int      rx550_mmio_pt_value(uint64_t pd_addr, uint32_t *out);
```

La primera implementa la regla, con el corte. La segunda convierte dirección en
número de página, con el **rechazo** en vez del truncamiento:

```
gmc_8_0.c:675        amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12)
gmc_8_1_sh_mask.h:6879
     VM_CONTEXT0_PAGE_TABLE_BASE_ADDR__PHYSICAL_PAGE_NUMBER_MASK = 0xfffffff
                     __SHIFT = 0x0
```

28 bits, y el campo empieza en el bit 0. Un `>> 12` sobre 40 bits da
exactamente 28, así que el campo cabe entero. Si la dirección tuviera más de 40
bits, cortar sería silencioso.

`vmid >= 16` se rechaza. `mmVM_INVALIDATE_REQUEST` tiene 16 dominios
(`gmc_v8_0.c:637`, bucle `vmid 1..15`), así que no hay un contexto 16. Y
devolver un índice calculable por aritmética sería peor que no devolver nada:
caería dentro de BAR5, el acceso funcionaría, y el fallo no se vería.

## El test, y por qué copia los números del corpus

`tests/test_ctxpt.c`, 44 aserciones, tres bloques:

- **C1** los 16 VMID contra el índice del header, más el corte explícito, más
  que la tabla de mnemonicos y la regla **coincidan** en el contexto 1. Si
  divergen, o la tabla o la regla están hablando de registros distintos.
- **C2** negativos: 16, 17, 1000, `0xffffffff`, y que el rechazo no deje un
  índice dentro de BAR5.
- **C3** el valor: `>> 12`, el tope exacto, el rechazo sin escritura, salida nula.

El test **copia los 16 índices del header en una tabla local**, en vez de leer el
header. Si leyera el header, compararía la regla contra sí misma y no mediría
nada: un cambio en el corpus no produciría ningún fallo.

## Una aserción que parecía discriminar y no

El comentario del test afirmaba que comprobar el rango antes del desplazamiento
importa, porque si se comprobará después `2^40 >> 12 == 2^28` "no lo delataría".

Medido, y es **falso**:

```
$ # version con la comprobacion DETRAS del >> y escribiendo antes de comprobar
  FAIL  C3 y la salida no se toca al rechazar  (0x10000000 != 0xdeadbeef)
  FAIL  C3 y la salida sigue intacta  (0xffffffff != 0xdeadbeef)
  42 pass, 2 fail
```

`pd_addr >> 12 < 2^28` y `pd_addr < 2^40` son la misma condición: no existe
ninguna entrada que distinga los dos órdenes. Lo que sí distingue, y lo que de
verdad importa, es que `*out` no se escriba al rechazar, porque un llamante que
ignore el código de error leería un valor inventado.

El comentario está corregido y dice eso, con la medición al lado. Una aserción
correcta que no discrimina no es un error: es ruido que hace creer que hay una
garantía donde no la hay.

## Estado, y lo que sigue sin tocarse

- 18 suites en la puerta, `con_problema=0`, `make EXIT=0`.
- `rx550_mmio_access.c` sigue siendo `DUAL`: compila en los dos contextos.
- Las dos funciones nuevas están **en el `.ko`**:
  `T rx550_mmio_ctx_pt_base_index`, `T rx550_mmio_pt_value`.
- El módulo sigue sin cargarse. `amdgpu` posee `0000:01:00.0`, y tomar la GPU es
  una decisión con precondiciones propias (§90).
- Estas dos funciones **tampoco tienen consumidores todavía**. Lo que se ha
  cerrado aquí es la regla y su prueba, no el camino de `probe()`.

## Trazabilidad

- Fuente primaria de la regla: `gmc_v8_0.c:672-676`
- Fuente primaria de los índices: `gmc_8_1_d.h:636-655`
- Fuente primaria del ancho del campo: `gmc_8_1_sh_mask.h:6879-6880`
- Test: `tests/test_ctxpt.c`, 44 aserciones, en la puerta de `make run`
- Mutaciones que lo rompen: quitar el corte (12 FAIL), comprobar después del
  desplazamiento (2 FAIL)
- Prefijo de numeración: 1025, reservado antes de escribir