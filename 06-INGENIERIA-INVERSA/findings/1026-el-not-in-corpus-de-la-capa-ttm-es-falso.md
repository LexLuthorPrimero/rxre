# 1026 · El `NOT_IN_CORPUS` de la capa TTM del hallazgo 1020 es falso: `amdgpu_ttm.c` está en `working/`

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC`
`CORPUS=RESEARCH/working/linux-7.1.3, RESEARCH/kernelbuild/linux-7.1.3`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=1`
`RUNTIME=NOT_RUN` · `GPU INTACTA`

---

## La afirmación que se comprueba

`1020-la-apertura-del-gart-no-puede-cambiar-en-runtime.md:177-181`, sección 7
«Límites», punto 1:

> **`NOT_IN_CORPUS`, y es un límite real:** `si_meminfo`, `drm_buddy` y la capa
> TTM no están en `working/`. Para **esta** pregunta no importan […] Pero
> cualquier afirmación sobre **resize de VRAM** que traverse TTM sigue sin poder
> derivarse.

Es una de esas afirmaciones que no describen un hecho, sino que **declaran la
ausencia de una capacidad**, y por lo tanto acotan el trabajo. Says
explícitamente que una clase de afirmaciones «sigue sin poder derivarse». Eso es
un `NOT_IN_CORPUS`, y un `NOT_IN_CORPUS` equivocado no cuesta nada hasta que
alguien se apoya en él.

## La medición, contra los dos árboles que hay

```
$ K=RESEARCH/working/linux-7.1.3
$ K=RESEARCH/kernelbuild/linux-7.1.3
```

| fichero | `working/` | `kernelbuild/` | lo que dice 1020 |
|---|---|---|---|
| `drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.c` | **PRESENTE**, 80357 B | PRESENTE | **ausente** ❌ |
| `drivers/gpu/drm/amd/amdgpu/amdgpu_ttm.h` | **PRESENTE** | PRESENTE | **ausente** ❌ |
| `drivers/gpu/drm/drm_buddy.c` | ausente | PRESENTE | ausente ✅ |
| `include/drm/drm_buddy.h` | ausente | PRESENTE | ausente ✅ |
| `drivers/gpu/drm/amd/amdgpu/si_meminfo.c` | ausente | ausente | ausente ✅ |
| `drivers/gpu/drm/ttm/` | ausente | ausente | ausente ✅ |

## Veredicto

- **`si_meminfo`: CORROBORADO.** No está en ninguno de los dos árboles.
- **`drm_buddy`: CORROBORADO** para `working/`, que es lo que dice el texto.
  Matiz que no estaba anotado: sí está en `kernelbuild/`, de modo que
  «no está en el corpus» sería falso; «no está en `working/`» es cierto, y es
  lo que dice.
- **capa TTM: REFUTADO.** `amdgpu_ttm.c` y `amdgpu_ttm.h` están en `working/`,
  con contenido real, desde el 4 de julio. El `NOT_IN_CORPUS` que sostiene es
  falso para la mitad de lo que enumera.

Lo que **sí** falta, y que el texto no distingue, es `drivers/gpu/drm/ttm/` —la
capa TTM genérica, la que usa el DRM de verdad—, que no está en ninguno de los
dos árboles. `amdgpu_ttm.c` es el **lado amdgpu** de TTM, que es otra cosa: habla
de `struct amdgpu_ttm`, de `ttm_to_amdgpu_bo`, de la inicialización del
gestor de VRAM. Es la pieza que responde «cómo reserva amdgpu VRAM», no la que
responde «cómo funciona TTM».

Así que la frase mezcla dos capas con el mismo nombre corto y las trata como una.
El resultado neto —«no puedo derivar nada sobre VRAM que traverse TTM»— sigue
siendo más fuerte de lo que el árbol permite.

## Por qué no lo detecté antes, y por qué lo detecté ahora

Porque `1020` no se puede refutar desde dentro: su propia sección 7 dice que el
fichero que lo sostiene (`amdgpu_gmc.c`) está, y cierra ahí. Nadie abrió el
árbol a comprobar lo que la lista de ausencias afirmaba.

La comprobación salió de otra pregunta. Estaba buscando si el proyecto tenía
decidido qué allocator de VRAM va a usar —la pieza que falta entre «el driver
mapea BAR5» y «el driver tiene tablas de páginas»— y `rx550_vram.h` dice que
`drm_buddy`, `ttm` y `amdgpu_vram_mgr` son «evidencia de QUE hace falta un
allocator». Entonces la pregunta natural es si se pueden leer, y la respuesta
fue que no, según 1020.

Cerrado el hallazgo, el **estado de la afirmación**:

```
si_meminfo     NOT_IN_CORPUS     CORROBORADO
drm_buddy      NOT_IN_CORPUS     CORROBORADO en working/, PRESENTE en kernelbuild
amdgpu_ttm     NOT_IN_CORPUS     REFUTADO
drivers/gpu/drm/ttm/  NOT_IN_CORPUS  CORROBORADO (ausente en los dos arboles)
```

## Lo que este hallazgo no dice

- **No dice que `drm_buddy` sea legible desde `working/`**, porque no lo es.
  Está en `kernelbuild/`, que es otro árbol del mismo 7.1.3.
- **No dice que los dos árboles sean equivalentes.** Finding 024 afirma que
  `working/` y `baseline/` son byte-idénticos (`263c5d83b1f1`). Eso no cubre
  `kernelbuild/`, y lo medido aquí muestra que `kernelbuild/` tiene ficheros que
  `working/` no tiene. **Que el hash coincida para dos árboles no dice nada del
  tercero.**
- **No dice que el `resize` de VRAM esté resuelto.** Sigue sin estar. Lo que
  cambia es que ahora **se puede buscar** en el lado amdgpu de TTM, y no sólo
  declarar que no se puede.
- **No toca el hardware.**

## Un dato lateral que sale de la medición

```
$ git check-ignore -v RESEARCH/working/linux-7.1.3/.../amdgpu_ttm.c
.gitignore:63:RESEARCH/	RESEARCH/working/linux-7.1.3/.../amdgpu_ttm.c
$ git ls-files RESEARCH/working/ | wc -l
0
```

**Ningún fichero del corpus está versionado**: `RESEARCH/` está entero en
`.gitignore:63`. Eso es una decisión razonable por tamaño, pero tiene una
consecuencia que no está escrita en ningún sitio: **el corpus del que sale toda
la evidencia no se puede reproducir desde el repositorio**. Si mañana cambia una
línea de `amdgpu_vm_pt.c`, no hay diff que lo diga, porque el fichero no está
versionado. La procedencia existe mientras la máquina siga como está.

No se corrige aquí: versionar 2 GB de árbol fuente tiene un coste, y la decisión
es del proyecto. Lo que se registra es la consecuencia, que estaba implícita.

## Trazabilidad

- Afirmación comprobada: `06-INGENIERIA-INVERSA/findings/1020-...md:177-181`, §7.1
- Medición: presencia de los seis ficheros en los dos árboles del proyecto
- Corrección aplicada: `1020` §7.1 pasa a `CORROBORADO`/`REFUTADO` por fichero
- `.gitignore:63`: `RESEARCH/` completo
- Prefijo de numeración: 1026, reservado antes de escribir