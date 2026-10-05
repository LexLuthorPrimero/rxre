# 1145 — el page walker de GFX8 es una sola instrucción: `WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)`, y el parámetro `vmhub` no se usa porque no hay segundo hub

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gmc_v8_0.c:646-657   gmc_v8_0_flush_gpu_tlb  <- el callback, ENTERO
         gmc_v9_0.c:647-680   gmc_v9_0_flush_gpu_tlb  <- el contraste, misma firma
         gmc_v8_0.c:1093      vmhubs_mask con un solo hub
ABRE=1144-gfx8-no-tiene-mmhub-ni-saw.md
     046-la-version-de-ip-que-nunca-se-consulta.md (su "LO QUE ESTO NO DICE")
ESTADO=PROVEN-IMPLANTACION · lectura de corpus · sin root · sin GPU
```

## 0 · LO QUE DICE LA DOCUMENTACIÓN DEL PROYECTO, Y LO QUE DICE EL CÓDIGO

El proyecto lleva años diciendo que la semántica del MMU, del page walker y
del TLB de GFX8 no está publicada. `047` lo escribe en su §"LO QUE ESTO NO
DICE":

> *La semantica del MMU, del page walker y del TLB sigue siendo NOT_PUBLISHED.*

Y `094` abrió su documento con el comentario de formato del PTE del propio
driver. Todo eso es correcto **sobre el hardware**: no hay guía de Polaris12 en
este corpus.

Pero hay una distinción que esos documentos no hacen, y que separa dos preguntas
que se estaban confundiendo:

```
  ¿qué hace el HARDWARE al invalidar una TLB?     -> NO_PUBLICADO.  Correcto.
  ¿qué INSTRUMENTO usa el DRIVER para pedirlo?      -> ESTA EN EL CODIGO.
```

La segunda se responde leyendo **cinco líneas**, y el resultado cambia lo que
este proyecto puede afirmar sobre su propio flush.

## 1 · LA MEDICIÓN: EL CALLBACK ENTERO

`gmc_v8_0.c:646-657`, completo:

```c
/*
 * gmc_v8_0_flush_gpu_tlb - gart tlb flush callback
 *
 * @adev: amdgpu_device pointer
 * @vmid: vm instance to flush
 * @vmhub: which hub to flush
 * @flush_type: type of flush
 *
 * Flush the TLB for the requested page table (VI).
 */
static void gmc_v8_0_flush_gpu_tlb(struct amdgpu_device *adev, uint32_t vmid,
                                        uint32_t vmhub, uint32_t flush_type)
{
        /* bits 0-15 are the VM contexts0-15 */
        WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);
}
```

**El cuerpo entero es una instrucción.** Cuatro parámetros, y se usan **dos**:
`adev` (para la macro de MMIO) y `vmid`.

`vmhub` no aparece en ninguna sentencia. `flush_type` tampoco.

## 2 · EL CONTRASTE, Y ES LO QUE CONVIERTE EL DATO EN PRUEBA

La **misma firma** en GFX9, `gmc_v9_0.c:655`:

```c
static void gmc_v9_0_flush_gpu_tlb(struct amdgpu_device *adev, uint32_t vmid,
                                   uint32_t vmhub, uint32_t flush_type)
{
        bool use_semaphore = gmc_v9_0_use_invalidate_semaphore(adev, vmhub);
        u32 j, inv_req, tmp, sem, req, ack, inst;
        const unsigned int eng = 17;
        struct amdgpu_vmhub *hub;

        BUG_ON(vmhub >= AMDGPU_MAX_VMHUBS);

        hub = &adev->vmhub[vmhub];
        inv_req = gmc_v9_0_get_invalidate_req(vmid, flush_type);
        sem = hub->vm_inv_eng0_sem + hub->eng_distance * eng;
        req = hub->vm_inv_eng0_req + hub->eng_distance * eng;
        ack = hub->vm_inv_eng0_ack + hub->eng_distance * eng;

        if (vmhub >= AMDGPU_MMHUB0(0))
                inst = 0;
        else
                inst = vmhub;
        ...
}
```

En GFX9 `vmhub` aparece en **cinco** sitios distintos y `flush_type` en otro. En
GFX8, ninguno.

> **El parámetro no usado no es un descuido: es la firma del hook lo que es
> común.** Los dos ficheros implementan el mismo `funcs`, y por eso tienen la
> misma lista de parámetros. GFX9 necesita los dos hubs; **GFX8 recibe el
> parámetro y no lo necesita**, y eso es una **prueba positiva** de que solo hay
> uno.

Y eso cierra por segunda vía lo que `1144` cerró por la vía de las asignaciones:

```
  1144:  0 de 12 asignaciones de mmhub.funcs están en gmc_v8_0.c
  1145:  gmc_v8_0_flush_gpu_tlb no usa el parámetro vmhub, y el gemelo de
         GFX9 lo usa en cinco sitios
```

**Dos medidas independientes, la misma conclusión.** Y la segunda es más fuerte
porque no depende de contar asignaciones: depende de que un parámetro existe en
la firma y no en el código.

## 3 · LA CONSECUENCIA PARA ESTE PROYECTO, Y ES OPERATIVA

### 3.1 · El GART de esta GPU se invalida escribiendo un bit

```
  flush de la TLB del GART en GFX8
     = escribir (1 << vmid) en mmVM_INVALIDATE_REQUEST
```

**Sin condición, sin comprobación, sin bus de invalidación.** El comentario del
propio driver lo dice: *bits 0-15 are the VM contexts0-15*.

Y para un driver propio que implemente el VM, eso significa que **el flush del
GART es la operación más barata posible**: un MMIO de 32 bits. No hay secuencia
de sincronización, no hay semáforo, no hay `inst`.

### 3.2 · La diferencia con GFX9 no es de rendimiento, es de protocolo

| | GFX8 | GFX9 |
|---|---|---|
| invalidación | un MMIO | **semáforo** (`use_invalidate_semaphore`) |
| hubs | 1 | 2 (GFXHUB + MMHUB0) |
| `flush_type` | **ignorado** | selecciona el tipo de request |
| longitud | 1 instrucción | decenas, con busy-wait |

Y hay un `BUG_ON(vmhub >= AMDGPU_MAX_VMHUBS)` en GFX9 que **no tiene equivalente
en GFX8**, porque no hay segundo hub que acotar.

> **Un driver propio de GFX8 no necesita implementar el protocolo de invalidación
> de GFX9.** Si lo hace, está pagando un coste que el hardware de esta ASIC no
> exige. Y si lo omite, tiene que saber que es correcto para esta generación y no
> por descuido.

## 4 · LO QUE ESTO NO DICE, Y ES LO IMPORTANTE

- **No dice qué hace el hardware con ese bit.** Dice que el driver **escribe**
  `1 << vmid` en `mmVM_INVALIDATE_REQUEST`. Que eso invalide la TLB del VMID
  correspondiente es la semántica del registro, que **sigue sin publicarse** y
  sigue siendo de otro nodo.
- **No dice que el flush de un VMID arbitrario sea una sola escritura.** El
  callback recibe un `vmid` y escribe un bit, pero **quién llama** y con qué
  `vmid` no está medido. Si el caller invalida 16 VMID, son 16 escrituras.
- **No toca `flush_type`**, que en GFX8 se ignora. Que exista y no se use es un
  dato, y su valor es `NOT_DETERMINED`: no se ha medido qué valores recibe.
- **No dice que GFX8 no tenga invalidación por VM.** Dice que este callback no
  la distingue.

## 5 · LO QUE ESTE HALLAZGO PERMITE QUE ANTES NO SE PODÍA AFIRMAR

Antes de este documento, el proyecto tenía estas dos afirmaciones, y ninguna se
podían juntar:

```
  A.  la semantica del MMU y del page walker de GFX8 no esta publicada
  B.  existe un callback flush_gpu_tlb en el driver de esta ASIC
```

Y no se podían juntar porque **no se sabía qué hacía**. Ahora sí:

| lo que se sabía | lo que se sabe |
|---|---|
| hay un callback | **hace una escritura de un bit** |
| no sabemos nada del hardware | **sabemos exactamente qué pide el driver** |
| `vmhub` es un parámetro más | **`vmhub` no existe para esta ASIC, y el gemelo lo demuestra** |

> **La diferencia entre «no publicado» y «no medido» es la que separa un
> bloqueo de una tarea.** El hardware sigue sin publicar. El driver ya está
> medido, y el driver es lo que este proyecto reimplementa.
>
> Y esa distinción es la que evita el error que este proyecto ya pagó: leer un
> `NOT_PUBLISHED` como si fuera «no se puede trabajar» y seguir sin tocar el
> único fichero donde la respuesta sí está.

## 6 · LA LECCIÓN, Y ES LA MISMA DE TRES HALLAZGOS

`094`, `1125` y este resuelven la misma pregunta por tres caminos distintos:

```
  094    ¿qué flags escribe gmc_v8_0?          -> leer QUIEN ESCRIBE
  1125   ¿en qué bit va el campo fragment?      -> leer la MACRO
  1145   ¿cómo invalida la TLB esta ASIC?      -> leer el CUERPO del callback
```

**Los tres están en el fichero del ASIC propio, `gmc_v8_0.c`, y los tres se
resolvieron leyendo el fichero entero del ASIC, no la documentación ni el
hardware.**

> Cuando la respuesta está en el fichero que implementa el ASIC, leer el fichero
> entero es más rápido que cualquier análisis del hardware, y además **no
> depende de que exista la guía de hardware**. El bloque que empieza en
> `gmc_v8_0.c:686` y acaba en `:702` resolvió dos hallazgos en dos versiones de
> disco; el callback de `:655` resolvió este.
>
> **Y la lección del coste**: estas tres respuestas costaron un ciclo cada una, y las
> tres estaban en un fichero de 7000 líneas que ya estaba en el árbol desde el
> primer día. Lo que faltaba no era el fichero: era saber que la pregunta tenía
> respuesta ahí.

## 7 · ESTADO

```
  flush del GART en GFX8        1 << vmid -> mmVM_INVALIDATE_REQUEST   PROVEN
  el callback usa vmhub         NO                                     PROVEN
  el gemelo GFX9 lo usa         5 sitios                              PROVEN
  -> hubs de VM en GFX8         1                                      PROVEN (2 vias)
  flush_type en GFX8            IGNORADO                               PROVEN
  invalida por semaforo         NO                                     PROVEN
  que hace el hardware con el bit                                    NOT_PUBLISHED
  quien llama y con que vmid    NO MEDIDO                              -> tarea
  que valores toma flush_type   NO MEDIDO                              -> tarea

  corrobora 1144 por segunda via independiente

  GPU     INTACTA
  sudo    NO usado
  MMIO    NO tocado
  corpus  solo lectura
```