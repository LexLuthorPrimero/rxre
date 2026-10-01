# pteflags — censo de productores de flags de PTE en GFX8/Polaris12

Responde la tarea que `AGENTS.md:506` nombra como modelo:

> Localizar todos los producers de PTE flags para GFX8, resolver sus
> transformaciones hasta `amdgpu_gmc_set_pte_pde`, identificar cada bit escrito,
> y clasificar cada bit como PROVEN/NOT_DETERMINED.

No escribe registros, no lee MMIO, no ejecuta código del driver. Es análisis
estático sobre el árbol de referencia, con preprocesador.

## El resultado

```
flag                     bit  estado            productor
AMDGPU_PTE_VALID          0   WRITTEN           amdgpu_ttm_tt_pde_flags (amdgpu_ttm.c:1416)
AMDGPU_PTE_SYSTEM         1   WRITTEN           amdgpu_ttm_tt_pde_flags (amdgpu_ttm.c:1422)
AMDGPU_PTE_SNOOPED        2   WRITTEN           amdgpu_ttm_tt_pde_flags (amdgpu_ttm.c:1425,1430)
AMDGPU_PTE_TMZ            3   WRITTEN           amdgpu_vm.c:1347 / amdgpu_ttm.c:261,885
AMDGPU_PTE_EXECUTABLE     4   WRITTEN           gart_pte_flags (gmc_v8_0.c:961) + get_vm_pte
AMDGPU_PTE_READABLE       5   WRITTEN           amdgpu_ttm_tt_pte_flags (amdgpu_ttm.c:1450)
AMDGPU_PTE_WRITEABLE      6   WRITTEN           amdgpu_ttm_tt_pte_flags (amdgpu_ttm.c:1453)
AMDGPU_PTE_PRT           51   CLEARED_NOT_SET   gmc_v8_0_get_vm_pte lo borra, no lo pone
AMDGPU_PDE_PTE           54   WRITTEN           amdgpu_vm_pt.c:689 (AMDGPU_PDE_PTE_FLAG)
AMDGPU_PTE_LOG           55   OTHER_GEN         solo gmc_v10_0.c / gmc_v11_0.c
AMDGPU_PTE_TF            56   OTHER_GEN         solo gmc_v9_0 / v10_0 / v11_0
AMDGPU_PTE_NOALLOC       58   OTHER_GEN         solo gmc_v10_0.c / gmc_v11_0.c
AMDGPU_PDE_BFS           59   OTHER_GEN         solo init_pdb0, no alcanzable en GFX8
AMDGPU_PTE_IS_PTE        63   OTHER_GEN         solo gmc_v12_0.c
```

Siete bits se escriben, uno se borra sin ponerse, cinco pertenecen a otra
generación. Ninguno queda `UNDETERMINED`.

## El resultado que da valor al resto: GFX8 no tiene MTYPE

GFX9 escribe un tipo de memoria en cada PTE. GFX8 no. Y la razón no es que el
driver decida omitirlo:

```
MTYPE_UC en la TU de gmc_v8_0.c    NO
MTYPE_UC en la TU de gmc_v9_0.c    SI
```

El símbolo **no existe en la unidad de traducción** de GFX8. El contraste es
demostrable porque `gcc -E` sobre `gmc_v9_0.c` sí emite el `enum MTYPE`
(`MTYPE_UC = 0x00000003`, en `vega10_enum.h`) y sobre `gmc_v8_0.c` no emite
ninguno: `gmc_v8_0.c` no incluye ningún `_enum.h`, de 1032 cabeceras que abre.

Un código GFX8 no podría escribir MTYPE aunque quisiera. No es una omisión del
driver; es que el concepto no está en su vocabulario.

## Por qué `-E` y no `-dM`

`-dM` solo emite **macros**. Los identificadores de enumeración, que es donde
vive `MTYPE`, no aparecen nunca. Una consulta que mire solo macros da un falso
**negativo**: "MTYPE no existe" cuando sí existe como enum.

Ese error se cometió durante esta sesión y habría producido la conclusión
opuesta a la correcta, con apariencia de rigor. `-E` emite la unidad entera.

## El preprocesador, y por qué hay que construirlo con cuidado

Correr `gcc -E` sobre un fichero de amdgpu exige 73 `-I` y tres `-include`. La
fuente de esos `-I` es el **`.cmd` que dejó el build real** del árbol, no una
reconstrucción a mano.

Con `-dM` a secas el preprocesador falla con

```
#error Compiler does not support fentry?
```

y produce una salida **parcial** que parece correcta. Un `grep` sobre esa salida
da 0 y parece una ausencia. Es el fallo que `PRE-EXECUTION CONTRACT CHECK`
prohíbe, y esta herramienta lo evita con dos reglas:

1. **`rc` se comprueba siempre.** Si `rc != 0`, la salida no se inspecciona.
2. **El `-I` es obligatorio al escribir el comando.** Emitir solo la ruta
   entrecomillada produce un `gcc` que toma los argumentos como ficheros fuente
   en vez de como rutas de búsqueda, y el fallo aparece mucho después como
   `linux/firmware.h: No existe`.

`-I./include/generated` no está en el `.cmd` y hace falta: `Makefile:589` lo
añade para todo el kernel y el `.cmd` lo hereda de ahí. La herramienta lo añade
**comprobando que el fichero exista**, y lo dice en un comentario.

### Fallos reales que costaron tiempo, y que quedan comentados

| fallo | síntoma |
|---|---|
| `-dM` en vez de `-E` | falso negativo sobre MTYPE: conclusión **invertida** |
| búsqueda por subcadena sin límites de palabra | `MTYPE_UC` casaba dentro de `X86_MEMTYPE_UC`: falso **positivo** |
| `fread` con buffer lleno devuelve 0 | salida truncada a 65535 B, hijo con SIGPIPE, `rc=1` sin causa visible |
| `-I` sin el prefijo | `linux/firmware.h: No existe`, dos niveles más abajo |
| dos funciones de preprocesado divergentes | una se olvidó de los `-include` |
| `-H` emite ` . ` con **un** punto | el separador exigía `..` y nunca encontraba el fin |

Los dos primeros importan más que los otros: un falso negativo y un falso
positivo producen conclusiones opuestas, y ambos con apariencia de rigor.

## Dos construidas, no afirmadas

**La clasificación de PRT se deriva del cuerpo citado**, no se escribe a mano.
La herramienta comprueba si el cuerpo contiene el `clear` y si contiene el
`set`, y clasifica en consecuencia. Comprobado con un mutante: sustituir
`*flags &= ~AMDGPU_PTE_PRT` por `*flags |= AMDGPU_PTE_PRT` cambia la
clasificación de `CLEARED_NOT_SET` a `WRITTEN` y el test falla con `rc=1`.

**`OTHER_GEN` se cerró por enumeración de callers**, no leyendo la rama y
suponiéndola inalcanzable. El caso de `AMDGPU_PDE_BFS` es el que importa:
`amdgpu_gmc.c:1169` lo escribe, pero está dentro de `amdgpu_gmc_init_pdb0()`, y
sus dos únicos llamantes son `gmc_v9_0.c:2140` y `gmc_v12_0.c:1013`.
`gmc_v8_0.c` no lo llama.

## Controles negativos

Cinco. Un control que no detecta su propia mutación se marca `[DEAD]` y cuenta
como fallo: es peor que no tenerlo, porque aparenta cobertura.

```
CN-1  raíz inexistente -> sin salida parcial
CN-2  un enum no es una macro (MTYPE)
CN-3  el conteo de token no cuenta prefijos
CN-4  pf_header_included exige la barra inicial
CN-5  el censo sobre un árbol inexistente falla, no devuelve vacío
```

**CN-1 nació sin controlar nada.** Usaba `PF_ROOT` —la raíz **válida**— en el
caso que pretendía ser el negativo, así que probaba que el camino bueno
funciona y se marcaba `DEAD` porque el negativo no existía. Un control que no
cambia la entrada no controla nada; parece controlar y no controla.

## Capacidad de fallo demostrada

| mutante | resultado |
|---|---|
| `clear` de PRT → `set` | `rc=1`, la clasificación pasa a `WRITTEN` |
| añadir `vega10_enum.h` a `gmc_v8_0.c` | `rc=1`, el contraste MTYPE deja de discriminar y se reporta como incoherente |

La segunda es la importante: la herramienta detecta que su propia prueba
central ha dejado de distinguir los dos casos, en vez de seguir dando un
resultado cómodo.

## Uso

```bash
make test          # censo + 5 controles negativos (default)
make check-noa8    # guardas: no toca hardware
make clean
```

## Lo que NO establece

```
semántica de hardware de cada bit     NOT_DETERMINED
que el silicio interprete la PTE      NOT_DETERMINED
MTYPE en el hardware de GFX8          NOT_DETERMINED — aquí solo se afirma
                                       que el DRIVER no puede escribirlo
```

Que el driver escriba un bit y que el hardware lo interprete son dos hechos
distintos. Este censo afirma el primero. El segundo necesita runtime o
documentación primaria de GFX8, y ninguna de las dos está autorizada aquí.

## Estado

```
19 aserciones, 0 fallos
5 controles negativos, 5 detectados, 0 muertos
informe: 0 líneas incoherentes
3 corridas consecutivas idénticas
GPU INTACTA · RUNTIME NOT_RUN · WRITE_EXECUTION NONE
```