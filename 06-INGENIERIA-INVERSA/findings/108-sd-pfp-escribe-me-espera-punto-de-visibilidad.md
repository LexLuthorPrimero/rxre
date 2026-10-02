# 108 · §C/§D: PFP escribe, ME espera — y por eso no hace falta una espera entre PTBA e invalidate

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`AGENTS.md` L412 pide cerrar la cadena hasta **visibility**, y L418 pide separar
tres órdenes: *software emission order / hardware execution order / hardware
completion order*.

Pregunta concreta que quedaba abierta: **`gmc_v8_0_emit_flush_gpu_tlb`
(`gmc_v8_0.c:668-683`) escribe PTBA y luego `VM_INVALIDATE_REQUEST` sin nada entre
ellos. ¿Por qué?**

**Respuesta: porque las dos escrituras las ejecuta el mismo motor, y el orden de
la cola ya las ordena.**

## La secuencia completa, con quién ejecuta qué

```
gfx_v8_0.c:6191   gfx_v8_0_ring_emit_vm_flush(ring, vmid, pd_addr)

 L6196   amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);
             -> gmc_v8_0.c:677   emit_wreg(PTBA, pd_addr >> 12)
             -> gmc_v8_0.c:680   emit_wreg(VM_INVALIDATE_REQUEST, 1 << vmid)

 L6198   /* wait for the invalidate to complete */
 L6199   PACKET3(PACKET3_WAIT_REG_MEM, 5)
 L6200       WAIT_REG_MEM_OPERATION(0)   /* wait */
 L6201       WAIT_REG_MEM_FUNCTION(0)   /* always */
 L6202       WAIT_REG_MEM_ENGINE(0)     /* me */
 L6203       mmVM_INVALIDATE_REQUEST     <- el registro esperado
 L6204       0
 L6205       0     /* ref */
 L6206       0     /* mask */
 L6207       0x20  /* poll interval */

 L6209   /* compute doesn't have PFP */
 L6210   if (usepfp) {
 L6211       /* sync PFP to ME, otherwise we might get invalid PFP reads */
 L6212       PACKET3(PACKET3_PFP_SYNC_ME, 0)
 L6213       0x0
 L6214   }
```

Y el motor de las escrituras:

```
gfx_v8_0.c:6354   switch (ring->funcs->type) {
gfx_v8_0.c:6355   case AMDGPU_RING_TYPE_GFX:
gfx_v8_0.c:6356       cmd = WRITE_DATA_ENGINE_SEL(1) | WR_CONFIRM;
```

Con los dos convenios de codificación, que coinciden:

```
sid.h:388   WRITE_DATA_ENGINE_SEL(x)  (x) << 30   /* 0 - me  1 - pfp  2 - ce */
sid.h:411   WAIT_REG_MEM_ENGINE(x)    (x) << 8    /* 0 - me  1 - pfp */
```

**Los dos codifican `1 = pfp` y `0 = me`, con el mismo convenio.** Por tanto:

| paso | paquete | motor que lo ejecuta |
|---|---|---|
| escribir PTBA | `WRITE_DATA`, `ENGINE_SEL(1)` | **PFP** |
| escribir `VM_INVALIDATE_REQUEST` | `WRITE_DATA`, `ENGINE_SEL(1)` | **PFP** |
| esperar el invalidate | `WAIT_REG_MEM`, `ENGINE(0)` | **ME** |
| sincronizar | `PFP_SYNC_ME` | PFP → ME |

**Las dos escrituras las ejecuta PFP. La espera la ejecuta ME. Son motores
distintos.**

## Por eso no hay nada entre PTBA e invalidate

**Porque las dos escrituras van al mismo motor.** Un motor consume sus paquetes
en orden de cola, y PTBA está antes en la cola. **El orden de la cola ES la
garantía.**

**Si estuvieran en motores distintos, haría falta una espera explícita entre
ellos — y la hay, pero después, no entre ellos.** El `WAIT_REG_MEM` está
después de las dos escrituras, no entre: es el punto donde el ME espera a que
PFP haya hecho su trabajo.

**Y por eso existe `PFP_SYNC_ME`** (L6212), que `095` ya había visto pero sin
saber en qué orden: es la otra mitad del mismo mecanismo. El comentario de
L6211 lo dice sin rodeos — *"otherwise we might get invalid PFP reads"*.

**Consecuencia para un driver propio:** el orden de emisión no es un detalle de
software. **La secuencia PFP-escribe → ME-espera → PFP-se-sincroniza es la que
hace que la invalidación sea visible**, y cambiar el orden de cualquiera de los
tres rompe algo que no tiene y parece codigo redundante y no lo es.

## Y esto contradice la lectura de `017`

`017` concluyó que `FUNCTION=always` con `ref=0, mask=0` **no compara nada**, y
lo usar como prueba de completion no vale. **`107` confirmó los tres ceros.**

**Pero hay dos cosas en ese mismo paquete que `017` no menciona, y que no encajan
con "no compara nada":**

```
L6202   WAIT_REG_MEM_ENGINE(0)   /* me */
L6207   0x20                     /* poll interval */
```

**Si la condición fuera vacía, el motor no importaría y el intervalo de sondeo no
tendría sentido.** Un paquete que no espera nada no necesita decir cada cuánto
sondear, y desde luego no necesita decir **qué motor** lo ejecuta.

**La lectura más defendible, y la marco como hipótesis, no como hecho:**
`always` no significa "pasa siempre", sino **"espera a que esta dirección esté
escrita, sin condición de valor"** — una barrier de visibilidad, no una
comparación. `ref=0` y `mask=0` serían "no compares contra nada", no "no
compares".

**Eso encaja con el nombre del comentario de L6198** — *"wait for the invalidate
to complete"* — y con que exista un `poll interval` distinto de cero.

**Pero es una hipótesis sobre semántica de hardware, y `AGENTS.md` prohíbe
cruzar esa frontera por razonamiento.** Lo que sí es `PROVEN` es que el paquete
lleva motor y sonda, y que `017` no los mencionó al argumentar que la condición
es vacía.

**Lo correcto aquí es weakens el argumento de `017` sin reemplazarlo:** la
condición de valor es vacía; el paquete **no** lo es.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Las escrituras de PTBA e invalidate las ejecuta PFP | `PROVEN` (`gfx_v8_0.c:6356`) |
| El `WAIT_REG_MEM` lo ejecuta ME | `PROVEN` (`gfx_v8_0.c:6202`) |
| Ambos codifican `0=me, 1=pfp` | `PROVEN` (`sid.h:388` y `:411`) |
| No hay espera entre PTBA e invalidate | `PROVEN` |
| El motivo es que son el mismo motor | `PROVEN_DERIVED` |
| La espera va **después** de ambas escrituras | `PROVEN` |
| El paquete lleva motor y poll interval no nulos | `PROVEN` (`L6202`, `L6207`) |
| El punto de visibilidad es el WAIT_REG_MEM del ME | `PROVEN_DERIVED` |
| `always` = barrier de visibilidad, no comparación | **`HYPOTHESIS`** |
| Si el hardware realmente ordena las escrituras de PFP | **`NOT_DETERMINED`** |
| Cuánto tarda la invalidación en ser visible | **`NOT_DETERMINED`** |

**Las dos últimas son `software behaviour ≠ hardware semantics`.** Que la cola
ordene los paquetes de PFP **en el orden en que se escribieron** es algo que el
driver da por hecho y que no he observado. `hardware execution order` sigue
`NOT_PROVEN`, que es exactamente lo que dice el estado de `AGENTS.md`.

**Lo que sí cambia es dónde está el punto de visibilidad.** No está "entre
escribir la tabla y vaciar la TLB": **está en el `WAIT_REG_MEM` que el ME ejecuta
después de que PFP haya escrito el invalidate.** Eso es derivable del código y no
requiere hardware.

## Procedencia

- `STATIC` — `gfx_v8_0.c:6191-6215` y `gfx_v8_0.c:6349-6369`,
  `gmc_v8_0.c:668-683`, `sid.h:386-392` y `sid.h:411-414`, `amdgpu_ring.h:447`.
- Sin `RUNTIME`. Sin escrituras.
- **Corrige la lectura de `017`** (no es mío: **lo informo, no lo edito**).
- Encadenada con `107` (las 7 funciones y el poll), `095` (`PFP_SYNC_ME`),
  `068`/`085` (la secuencia), `103`/`104` (el invalidate), `084` (packet consumption).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, sobre lo que casi hice.**

Tenía la respuesta a medias desde `103`: ya sabía que `emit_flush_gpu_tlb` no
tenía espera entre PTBA e invalidate. Lo traté como "el orden de la cola basta"
y seguí. **No basta por sí solo — basta porque las dos escrituras son del mismo
motor**, y eso no lo había mirado.

La diferencia es de un `grep`: `gfx_v8_0.c:6356`, el `WRITE_DATA_ENGINE_SEL(1)`
del que cuelga toda la explicación. **Un "¿quién ejecuta esto?" casi siempre vale
más que un "¿por qué escriben esto?", y cuesta lo mismo.**