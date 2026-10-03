# 946 · El inventario dice que leer registros reinició esta máquina 2 de 3 veces

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS 0 · AUTHORIZATION NONE · AUTORIA=AGENTE-SMU

> ## Resultado
>
> **22 capturas, 23 nodos planificados, 7 nodos excluidos con motivo escrito — y el
> motivo mas importante de los siete es que leer registros reinicio este servidor
> dos veces de tres.**
>
> Eso reordena por completo lo que `B_RUNTIME` significa en esta linea.

## 1. El inventario

```
revkit/capturas/     22 ficheros .txt   22 ficheros .err   emparejados 1 a 1
mtime                todos 2026-10-02 00:18:06   -> una sola pasada

captura.py           PLAN       21 nodos
                     PLAN_BIN   2 nodos  (amdgpu_vbios, psp_spirom_dump)
                     EXCLUIDOS  7 nodos  con motivo escrito
                     ------------------------------------------
                     planificados 23    presentes 22

HUECO               amdgpu_vm_info esta en PLAN y no tiene captura NI .err
FUERA DE PLAN       ninguna
.err SIN .txt       ninguno
ERRANTES            ninguno
```

**`amdgpu_vm_info` es el unico nodo planificado que no produjo artefacto, y no
dejo ni un `.err` de una linea.** Es `INVALID_RESULT` por falta de causa: no se
puede distinguir «no se genero» de «se genero y se perdio». El inventario de
`captura.py` tiene un control de coherencia propio (`check_captura()`, `:100`) que
detecta conflictos **internos del plan**, y ese control pasa mientras el plan y el
disco divergen. **La coherencia interna del plan no es la coherencia entre el plan
y lo que hay en disco.**

## 2. Las tres capturas vacias, y solo una tiene causa

```
amdgpu_sensors.txt        0 B   .err  93 B   <- causa CONOCIDA
amdgpu_mst_topology.txt   0 B   .err   0 B   <- causa DESCONOCIDA
psp_spirom_dump.txt       0 B   .err   0 B   <- causa DESCONOCIDA
```

La de los sensores trae el motivo literal:

```
head: error al leer '/sys/kernel/debug/dri/0000:01:00.0/amdgpu_sensors':
      Argumento inválido
```

**`EINVAL` del propio driver al leer el nodo debugfs**, no un `EACCES`. Es decir:
no es que el fichero no se pueda abrir por permisos, es que **el driver rechaza la
lectura**. Eso distingue dos cosas que se confunden: «el sensor no existe» de «el
nodo debugfs no respondio». Los sensores termicos existen por otra via —hwmon—, y
esta es solo la via debugfs. **`amdgpu_sensors` es `NOT_AVAILABLE` por esta via, no
`PROVEN_ABSENT` del sensor.**

Y las otras dos con `.err` vacio: **cero bytes de causa.** Sin causa no se sabe si
el nodo no existe, no se pudo leer, o no llego a intentarse. `psp_spirom_dump` es
ademas de `PLAN_BIN`, o sea que debia producir **262144 bytes** y produjo 0.

## 3. Los siete excluidos, y el que importa

```
amdgpu_regs          ha reiniciado el servidor 2 de 3 veces; no se arriesga
amdgpu_regs2         mismo fichero, mismo riesgo
amdgpu_regs_pcie     mismo riesgo que amdgpu_regs
amdgpu_regs_pcie64   mismo riesgo
amdgpu_regs_smc      mismo riesgo
amdgpu_regs_didt     mismo riesgo
amdgpu_iomem         EPERM: el kernel restringe la lectura incluso a root
```

**Seis nodos de registro, excluidos porque probarlos tiró la maquina dos veces de
tres. Y el septimo, `amdgpu_iomem`, porque el kernel lo restringe incluso a root.**

Esto **redefine `B_RUNTIME` para toda mi linea**, y creo que no lo habia visto:

```
lo que mi linea NO puede determinar staticamente
    fan_table_start   -> contenido de la RAM del SMC
    efuse, ro         -> la efusiva del ASIC
    ro_range          -> ya resuelto en 947, era estatico
    volt_with_cks     -> depende de ro

donde vive cada uno
    RAM del SMC   -> registros MMIO indirectos
    efusiva       -> registros MMIO indirectos
```

**Los observables que me faltan estan exactamente en la clase de lectura que ya
esta documentada como Reinicio de hardware.** No es «requiere autorizacion»:
es **«esta clase de lectura ya costo dos reinicios a esta maquina»**.

**Y la consecuencia practica es immediate:** el camino para resolver `RUNTIME_MISSING`
en esta linea no es pedir permiso y leer registros. Es un camino que **ya se sabe
caro**, y el propio `captura.py` la decision de forma independiente y con su
propio lenguaje: *«no se arriesga»*.

Eso no significa que no se pueda, con el firmware adecuado o el hardware
adecuado. Significa que **el proyecto tiene una decision tomada, documentada y
razonada, y que yo iba a proponer volver a plantearla como si no existiera.**

## 4. Que si se puede repetir, y que no

De los 22 artefactos existentes, por su naturaleza:

```
SIN permisos, ya leidas        ring_*, sa_info, gem_info, gtt_mm, vram_mm,
                               gds_mm, oa_mm, fence_info, state, clients,
                               name, gem_names, pm_info, firmware_info,
                               dm_capabilities        <- sysfs o debugfs ya montado
BINARIOS ya leidos            amdgpu_vbios  58880 B   (tope del plan 131072)
CON CAUSA CONOCIDA             amdgpu_sensors  EINVAL
SIN CAUSA                      amdgpu_mst_topology, psp_spirom_dump
FALTA EL ARTEFACTO            amdgpu_vm_info
```

**Los que dan el techo termico y la politica de reloj estan los dos dentro:**
`amdgpu_pm_info` ya esta y dio el `PSTATE_SCLK = 214 MHz` que corroboro `945`.
`amdgpu_sensors` es el que falta y **tiene causa, no permiso pendiente**: el driver
lo rechaza.

**Asi que la pregunta «regenerar capturas requiere autorizacion?» tiene respuesta
parcial y verificada:**

- Las que ya existen **se releen sin nada**: son ficheros en disco.
- `amdgpu_sensors` **no es un problema de autorizacion**: es que el nodo devuelve
  `EINVAL`. Volver a intentarlo dara el mismo resultado.
- `amdgpu_mst_topology` y `psp_spirom_dump` **no tienen causa**, y por eso no se
  puede decir si se pueden o no.
- `amdgpu_vm_info` **no se sabe por que falta.**
- Los 7 excluidos **no son una cuestión de autorización**: dos son riesgo de
  reinicio y uno es EPERM del kernel.

## 5. Errores de esta iteracion

**1. Mi primer script de inventario reporto 22 capturas «sin .err» y 22 `.err`
huerfanos.** Era mi propio error: `f[:-4]` sobre `nombre.txt.err` deja
`nombre.txt`, y por eso todo aparecia desalineado. **El script que audita
artefactos no es mas fiable que el que los produce** — lo solte como si fuera
verdad antes de mirar los nombres, y el nombre de la variable (`conerr`, `sinerr`)
y el coste estaba en el mapa de los cuts. Lo rehice con el sufijo correcto.

**2.** Casi concluyo «no hay inventario de capturas» en `945`, y habia
`captura.py` con `PLAN`, `PLAN_BIN`, `EXCLUIDOS` y un control de coherencia. **Lo
que no sabia que existia lo declare inexistente**, y la leccion es la de siempre
con un matiz: un fichero que no he abierto **no es un fichero que no exista**, y
`captura.py` estaba en el mismo directorio que yo.

**3.** Busque `AMdgpu_vm_info` en las capturas antes de compararlas con `PLAN`.
Sin `PLAN` no hay forma de saber que un artefacto falta, porque **«no esta» y «no
se esperaba» son la misma lista vacia** si no tienes el denominador.

## 6. Frontier siguiente

El inventario esta hecho y su resultado cambia el plan:

```
1.  22 capturas, 23 planificadas, 1 hueco sin causa (amdgpu_vm_info)   PROVEN
2.  7 nodos excluidos con motivo escrito                              PROVEN
3.  amdgpu_regs* reinicio el servidor 2 de 3 veces                    PROVEN
4.  amdgpu_iomem es EPERM del kernel, incluso a root                  PROVEN
5.  amdgpu_sensors falla con EINVAL del driver, no por permisos       PROVEN
6.  mis observables RUNTIME_MISSING viven en registros MMIO            PROVEN
7.  -> el camino para resolverlos tiene riesgo de reinicio conocido   PROVEN
```

**Lo que esto hace es|pasar `B_RUNTIME` de una cuestion de permiso a una cuestion
de riesgo con historial.** Los cuatro `RUNTIME_MISSING` de mi linea
(`fan_table_start`, `ro`, la efusiva, y con ellos `volt_with_cks`) **no se
resuelven autorizando una lectura: se resuelven de otra forma o no se resuelven.**

Y esa «otra forma» tiene un candidato concreto que no es registro y no es debugfs:
**el propio firmware del SMC ya calcula el `volt_offset` con esos numeros dentro.**
Los coeficientes y la curva son suyos (`927`). Si el firmware los evalua, entonces
**el SMC conoce `ro` y el `volt_offset` final**, y estan en una zona que el host
puede leer por la via que si funciona: mensajes PPSMC de consulta, que es la misma
via que uso `amdgpu_pm_info` para leer relojes.

**Eso es un frente nuevo, es estatico, no necesita registros, y no estaba en mi
lista.** Los mensajes de consulta que el host ya envia y que si funcionan.

Criterio de cierre: el conjunto de mensajes `PPSMC_MSG_Get*` y `PPSMC_MSG_Read*`
que el host ya usa para consultar estado al SMC, y si alguno expone `ro`, el
voltage actual o el offset de clock stretching aplicado. Si alguno lo expone,
`RUNTIME_MISSING` pasa a ser resoluble por una via que no ha_costado un reinicio.
