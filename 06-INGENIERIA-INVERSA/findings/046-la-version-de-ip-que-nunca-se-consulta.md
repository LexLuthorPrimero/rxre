# 046 · La versión de IP que nunca se consulta, y por qué `043` preguntó lo que no tenía que preguntar

<!-- CLAUSULA_RETRACTADA_POR=091 -->
> ⚠ **La cláusula del bloqueo técnico de este documento está RETRACTADA.**
> Se leyeron `CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM`, y **no**
> `CONFIG_MODULE_SIG_FORCE`, que está `# CONFIG_MODULE_SIG_FORCE is not set`.
> Medido: `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio **compila**
> con `vermagic` idéntico y **sin firmar**. No hay bloqueo técnico: lo que queda
> es NIVEL 4 → `BLOCKED_BY_AUTHORIZATION`. Ver `206`.

`CLASSIFICATION=TOOL+CONCLUSION` · `TRACK=STATIC` · `GPU INTACTA` · `RUNTIME=NOT_RUN`
`TOOL=tools/hwip.py` · `CIERRA=el BLOCKED de 043` · `GENERALIZADO_POR=047` · `MODIFICATIONS=0` en el corpus
`MODIFICATIONS=0` en el corpus
`CORRIGE_LA_POLITICA` — **este documento trata la lectura de hardware como una pared, y no lo
es.** Leer un registro es `NIVEL 2` en la jerarquía de permisos de `AGENTS.md`: *leer registros,
sysfs, debugfs, iomem, lspci, observar sin modificar* → **AUTORIZADO dentro de investigación**, si
es read-only y reversible, **con registro antes/después**.

La versión de `AGENTS.md` cargada en el contexto de la sesión era más corta y **no tenía esa
sección**. El fichero en disco sí. Y el proyecto se gobierna por el de disco.

Consecuencia: lo que aquí se marca como `BLOCKED` por política es un **experimento autorizado con
un formulario que rellenar**, no una pared. Lo que sí es pared, y es técnica: **cargar un módulo**
(`NIVEL 4`), porque el host tiene `CONFIG_MODULE_SIG_ALL` y `CONFIG_SECURITY_LOCKDOWN_LSM` sin
  > **[091] CORRIGE ESTA CLAUSULA**: no hay bloqueo tecnico. Lo que se leyo fue
  > `CONFIG_MODULE_SIG_ALL` y **no** `CONFIG_MODULE_SIG_FORCE`, que esta
  > `# CONFIG_MODULE_SIG_FORCE is not set`. Medido en este host:
  > `lockdown=[none]`, `SecureBoot disabled`, y un `.ko` propio COMPILA con
  > `vermagic` identico y SIN FIRMAR. Lo que queda es NIVEL 4
  > (`BLOCKED_BY_AUTHORIZATION`), que es otra cosa. Ver 091.
clave de firma. Esa no se quita con autorización.

## CUDA principal

`043` dejó una pregunta abierta como si fuera la única que quedaba:

> "Para saber si esta GPU usa `sdma_v3_0.c` o `sdma_v4_0.c` hay que conocer `SDMA0_HWIP`, y eso
> solo se lee de la tarjeta. La pregunta no es contestable de forma estática."

**La pregunta no hacía falta.** `SDMA0_HWIP` no se consulta para este chip, y eso se demuestra
por alcanzabilidad, leyendo el flujo de control, sin tocar la tarjeta:

```
[OK] el PCI ID 1002:699f del host mapea a CHIP_POLARIS12
       amdgpu_drv.c:2054  {0x1002, 0x699F, PCI_ANY_ID, PCI_ANY_ID, 0, 0, CHIP_POLARIS12},
[OK] el case de CHIP_POLARIS12 esta en la rama que llama a vi_set_ip_blocks
       amdgpu_device.c:2136, llamada en :2145
[OK] solo en el default, y el case del chip rompe antes
       amdgpu_device.c:2149, y el case de :2136 hace break antes
[OK] y tiene un solo llamador, en esa misma rama
       amdgpu_device.c:2150
[OK] el host publica 1002:699f
       01:00.0 [1002:699f] rev c7 (Lexa PRO)
```

`amdgpu_discovery_set_ip_blocks` —**el único sitio del driver que consulta la versión de un IP
block**— tiene un solo llamador, y está en el `default:` de un switch cuyo `case` incluye
`CHIP_POLARIS12` y hace `break` antes. `amdgpu_discovery_set_sdma_ip_blocks` se llama solo desde
ahí (`amdgpu_discovery.c:3452`). **Para `CHIP_POLARIS12` ninguna de las dos se ejecuta.**

Y el dato que confirma que la pregunta era impertinente: los 7 bloques de SDMA que el despacho
por versión selecciona son

```
sdma_v4_0_ip_block   sdma_v4_4_2_ip_block   sdma_v5_0_ip_block   sdma_v5_2_ip_block
sdma_v6_0_ip_block   sdma_v7_0_ip_block      sdma_v7_1_ip_block
```

**Ninguno es `sdma_v3_1_ip_block`.** El camino que decide por versión nunca lleva a la v3, porque
la v3 no está en él: la GPU de la familia VI se resuelve por el `case` del chip. Así que el valor
de `SDMA0_HWIP` no es ambiguo, es **irrelevante**.

**Consecuencia para el proyecto:** el `BLOCKED` de `043` —"¿qué versión de `SDMA0_HWIP` tiene esta
tarjeta?"— queda **cerrado sin runtime**, y con él el `NOT_DETERMINED` sobre qué fichero de SDMA
es el de esta GPU. `sdma_v3_0.c` es el correcto, y ahora por una razón que no depende de leer
nada.

## Lo que sí se lee de la tarjeta, y por qué eso no obliga a abrir runtime

La versión de **cada** IP block se lee de una tabla de IP discovery, y la cadena son **tres
lecturas de MMIO encadenadas**:

```
adev->ip_versions[SDMA0_HWIP][0]  <-  ip->major / minor / revision / variant / subrev
  <-  un descriptor de la tabla IP discovery
    <-  adev->discovery.bin, un buffer en RAM del host
      <-  memcpy desde una región mapeada con memremap()
        <-  adev->discovery.offset
          <-  RREG32(mmDRIVER_SCRATCH_0/1/2)   [la TMR]
            o <-  (RREG32(mmRCC_CONFIG_MEMSIZE) << 20) - DISCOVERY_TMR_OFFSET
```

**Y para esta GPU no hay atajo estático**: ningún `case CHIP_POLARIS12:` del corpus —los 307
ficheros `.c` de `amdgpu/`— escribe `adev->ip_versions[]` con un valor constante. Vega10 y
Arcturus sí lo hacen; Polaris12 no.

Eso no significa que haya que leer nada. Significa algo más útil, y es la distinción que la
herramienta hace explícita:

> **Que un valor se lea de la tarjeta no implica que haya que leerlo. Solo importa si su valor
> selecciona código.**

De los 39 HWIP referenciados, **10 son selectores de despacho** —su valor decide qué fichero se
ejecuta— y el resto no. Y de esos 10, uno solo (`SDMA0_HWIP`) toca una conclusión ya escrita en
un finding, y ese es precisamente el que la prueba de alcanzabilidad declara inalcanzable.

## La función que llena `ip_versions` no se llama como yo creía

Escribí `hwip.py` buscando `amdgpu_discovery_set_ip_versions` y reportó `NO ENCONTRADA`. La
herramienta se negó a suponer, y hacía bien: **esa función no existe**, ni en 7.2.8 ni en 7.1.3.
En 7.2.8 la que recorre la tabla de IP descriptors se llama `amdgpu_discovery_reg_base_init`
(`amdgpu_discovery.c:1498`) y fusiona la inicialización de bases de registro con la de versiones.

La versión siguiente busca la **asignación**, no el nombre. Y encontró otra cosa: la asignación
real ocupa cinco líneas y **la primera no contiene el `=`**, así que exigirlo hacía que no se
encontrara —con un síntoma indistinguible del de "no existe".

**Esa es la hermana de la regla de `043`:** no citar un fichero que no sea de mi ASIC, y **no
citar una función por un nombre que no se ha comprobado**. Las dos se automatizan igual, y las
dos producen el mismo tipo de fallo: un símbolo plausible, inexistente, que no da error.

## Cuatro fallos de la herramienta, y dos que hacen daño

**Un `.+?` no guloso vació la tabla de selectores.** `switch (amdgpu_ip_version(adev, SDMA0_HWIP, 0))`
con un regex no guloso devuelve `amdgpu_ip_version(adev, SDMA0_HWIP, 0` —sin el
cierre—, el segundo regex no casa, y la tabla sale **vacía**. Una tabla vacía no se parece a una llena: se
parece a "no hay despacho por versión", que es lo contrario de lo cierto. **Un fallo que produce
un resultado plausible en vez de un error es el peor de los fallos**, porque no obliga a mirar.
Es la razón por la que el selftest existe: 5 vectores, dos sobre exactamente estos puntos.

**Tomaba el primer `switch (adev->asic_type)`** —hay cinco en `amdgpu_device.c`— y lo tomaba de
otra función. La función se localiza por nombre y el switch se busca dentro: un nombre de función
es un índice, un switch suelto no.

**Una ventana de 70 líneas se comía la función siguiente**, y `SDMA0_HWIP` aparecía
seleccionando `gfx_v12_0_ip_block`. Un recorte fijo no puede saber dónde acaba un bloque en C;
el cierre se cuenta por llaves.

**`lee MMIO: False`, y era el dato más importante de la herramienta.** La función que *parsea* no
lee MMIO — parsea un buffer que ya está en RAM—; la que *llena* ese buffer sí, con `memremap`. Un
solo booleano para los dos hechos producía un `False` que parecía decir "esta versión no se lee
de la tarjeta". **Un detector que confunde el alcance de su afirmación es peor que uno que
calla**, así que ahora son dos campos, y cada uno lleva su función y su línea.

## Lo que sigue `NOT_DETERMINED`

- El spec de GFX8 no está publicado (`033`). Nada de esto lo cambia. Sigue siendo la frontera
  grande, y la del `count` de PTEPDE en particular: que el driver de esta GPU escriba `count`
  es `PROVEN` **sobre el software**, no sobre el hardware.
- El efecto hardware de `INVALIDATE_ALL`, el orden intra-envío, `VALID=0` frente a `PA=0`, y el
  bit 54 (`AMDGPU_PDE_PTE`) en GFX8. Son `NOT_PUBLISHED`, no "aún no buscados".
- La geometría completa de la GART tal y como la implementa el hardware, que `033` también marca.

## UNLOCKS

- **`043` queda cerrado.** No por leer un registro, sino por demostrar que el registro no se lee.
  Y esa forma de cerrar —*alcanzabilidad en vez de medición*— es más fuerte que la que buscaba:
  no da un valor, da que **ningún valor sirve**.
- `hwip.py` cierra el patrón de `043` y `045` para el caso del símbolo: dado un nombre, comprueba
  que exista, y si no, dice que no existe en vez de seguir como si existiera.
- La distinción **"se lee de la tarjeta" / "hay que leerlo"** queda automatizada y es la que
  gobierna la política de runtime de este proyecto. Antes era una intuición; ahora son 39 filas
  con el número de bloques que cada una selecciona, y las que no seleccionan nada no justifican
  abrir nada.
- ~~Quedan 9 selectores de despacho vivos y para cada uno la misma pregunta.~~ **Resuelto por
  `047`:** `tools/unreach.py` aplicó la misma prueba a los 10 y **los 10 son inalcanzables**. La
  conclusión se generaliza: ninguna lectura de MMIO se justifica por *decidir qué código se
  ejecuta*.
- Y `047` mide el límite de esa afirmación: 629 usos más de `amdgpu_ip_version` en 398 funciones
  alcanzables, que afectan al *comportamiento* del código y no a la elección de fichero. Ese
  frente queda abierto y es el siguiente real.

## Falsación

- La prueba se refuta si `amdgpu_discovery_set_ip_blocks` tuviera un segundo llamador, o si
  `CHIP_POLARIS12` no estuviera en la lista de la rama que llama a `vi_set_ip_blocks`, o si esa
  rama no hiciera `break` antes del `default`. Los cinco puntos se comprueban por separado y cada
  uno se imprime con su línea: un fallo en cualquiera devuelve `INCOMPLETA` y no se afirma la
  conclusión. Es lo que pasó tres veces durante el desarrollo de la herramienta.
- Se refuta también si el host no publicase `1002:699f`, que es el punto 5 y el único que depende
  de fuera del corpus.
- El hecho `sdma_v3_1_ip_block ∉ {los 7 selectores}` se refuta si `hwip.py` dejara de encontrar
  alguno de los 7. El selftest cubre el regex que los encuentra, con tres vectores de HWIP.
- El nombre `amdgpu_discovery_reg_base_init` se refuta con un `grep`: una línea. Por eso es
  verificable y por eso se comprobó en los dos corpora.

## Evidencia

```
tools/hwip.py           5 vectores de selftest
                        39 HWIP referenciados, 10 son selectores de despacho
                        SDMA0_HWIP selecciona 7 bloques, ninguno de la v3
                        prueba de alcanzabilidad: 5 de 5 puntos OK
                        ningún case de POLARIS12 hardcodea ip_versions (0 de 307 .c)
                        cadena causal de 3 niveles de MMIO, medida
tools/citegen.py        6 vectores de selftest, añadido en esta iteración
suite del driver        22 + 12 + 195 = 229 checks, 0 fallos
crosscheck              10 vectores CLEAN
rx550pm4val             16/16
audit_citations         245 citas, 0 fallos
corpus                  MODIFICATIONS=0, sha256 12e8d5a973d1ad7c…c3e51941
```

Ningún registro leído de MMIO. `insmod` no ejecutado. `GPU INTACTA`.
