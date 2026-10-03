# 924 — `AMDGPU_INFO_READ_MMR_REG` no puede observar la traducción de páginas: la lista permitida no tiene registros de MC ni de VM

Estado: `PROVEN_ABSENT` para la capacidad que se buscaba. Cierra una frontera que estaba
declarada como bloqueada sin probar.
Alcance: la RX 550 de esta placa, Polaris12/GFX8.1, kernel 7.1.3, amdgpu de ese árbol.
AUTORIA=AGENTE-SMU

## La frontera que se cierra

El mecanismo del calentamiento de 6,7 ms de §F — el pago que sigue a las páginas distintas que el
kernel toca, y no al rango de direcciones — estaba bloqueado con la razón «requiere MMIO». Una de las
vías de acceso a MMIO desde userspace sin root era `AMDGPU_INFO_READ_MMR_REG`, que la cabecera
declaraba pero que nunca se había ejecutado. La regla del proyecto es no afirmar que una vía
desbloquea sin ejecutarla, y la regla opuesta — no declarar una capacidad ausente sin haber buscado
el camino completo — pide lo mismo desde el otro lado: no descartar la vía sin haberla recorrido entera.

Caminada está. Y la respuesta cierra la frontera en negativo, con la razón.

## Lo que hace el ioctl

`AMDGPU_INFO_READ_MMR_REG` no es MMIO general. Es una lectura con lista blanca, y la lista blanca
está escrita en el corpus, en `amdgpu/soc15.c`, sección `soc15_allowed_read_registers`:

```
18 registros  SOC15_REG_ENTRY(GC, 0, ...)      bloque del controlador grafico
 1 registro   SOC15_REG_ENTRY(SDMA0, 0, ...)
 1 registro   SOC15_REG_ENTRY(SDMA1, 0, ...)
20 en total
```

`amdgpu_kms.c` recorre esa tabla y, si el offset pedido no está, escribe «unallowed offset» en el
log de depuración y devuelve `-EFAULT`. No hay lista de MC. No hay lista de VM. No hay lista de
GART ni de UVM.

## Por qué esto cierra la frontera de §F

La pregunta abierta de §F es por qué el coste de warms sigue a las **páginas distintas**. Eso es un
asunto de traducción de direcciones virtuales: PTE, PDE, jerarquía de la tabla, RYZEN TLB, y el contador de
la UVMA. Todo eso vive en el bloque de memoria y en el de memoria virtual. La lista permitida no
alcanza ninguno de los dos bloques.

**Consecuencia: esta vía no observa el mecanismo, y no por una limitación de permisos sino por su
diseño.** Un `-EFAULT` aquí significa «este registro no es observable desde userspace por política»,
no «no tienes permiso». Son dos cosas distintas y confundirlas produce la conclusión opuesta a la
verdad: hace parecer que falta un permiso cuando lo que falta es el instrumento.

## El riesgo secundario que sí importaba

El ioctl no es una lectura pura. Envuelve cada lectura en el par:

```
amdgpu_gfx_off_ctrl(adev, false)     /* ... lee ... */    amdgpu_gfx_off_ctrl(adev, true)
```

`amdgpu_gfx_do_off_ctrl` sale inmediatamente si `!(adev->pm.pp_feature & PP_GFXOFF_MASK)`. La
máscara vale `0x8000` en `include/amd_shared.h`. El código que la **limpia** está en `gfx_v9_0.c` y
en `gfx_v10_0.c`. **No hay equivalente en `gfx_v8_0.c`.** De ahí no se deduce el estado en esta placa:
o la máscara sigue puesta, o nunca se puso. `NOT_DETERMINED` por vía estática, y comprobable en
tiempo de ejecución observing si una lectura perturba un trabajo en curso.

Esto queda registrado porque es el tipo de estado que estropea una medición de rendimiento en
silencio: si el par de gfx off no fuera un no-op, cada lectura metería y sacaría el bloque gráfico
de un estado bajo, y cualquier `§H` medido alrededor de una lectura estaría perturbado sin que nada
lo dijera.

## Lo que sí sale de aquí

Los cuatro registros del bloque gráfico que sí son legibles, con sus offsets tomados de
`include/asic_reg/gca/gfx_8_1_d.h` — la ASIC de esta placa, no una genérica:

| Registro | Offset | Para qué sirve |
|---|---|---|
| `mmGB_ADDR_CONFIG` | `0x263e` | base de la apertura GFX y modo de tesela |
| `mmGRBM_STATUS` y `STATUS2` | `0x2004` y `0x2005` | GRBM ocioso o activo |
| `mmCP_CPC_BUSY_STAT` | `0x2085` | el procesador de comandos está ocupado |
| `mmDB_DEBUG2` | `0x260d` | el depurador está ocupado |

`mmGB_ADDR_CONFIG` es el más valioso: de ahí sale la base de MMIO del bloque gráfico, que es un dato
que un driver propio necesita y que hoy no está en ninguna variable de la uapi.

`mmCP_CPC_BUSY_STAT` y `mmGRBM_STATUS` dan una salida que hoy no existe: distinguir «el trabajo se
sigue enviando» de «la GPU está ocupada», que es exactamente el discriminante que separa
envío-limitado de GPU-limitado en §H.

**Lo que falta para construir la herramienta:** la dirección absoluta es
`adev->reg_offset[SOC15_HWIP_GC][0][seg] + offset_del_registro`, y la forma en que esa tabla se
rellena para esta ASIC no está localizada en el corpus. La búsqueda de `SOC15_BASE_GC` en el árbol
entero sale con cero, y el inicializador de `reg_offset` que existe (`aldebaran_reg_init.c`) es de
otra familia de ASIC. Consecuencia práctica: la dirección absoluta necesita root, o el blob de
discovery, o deducirla de `GB_ADDR_CONFIG`… que a su vez está en esa dirección. Es una
dependencia circular, y por eso esta nota **no** afirma que la herramienta esté al alcance.

## Instrumentos

Ninguno nuevo. El trabajo fue estático, del corpus, y no se construyó nada: no había una
observación que recoger, sino una lista que leer.

## Lo que queda abierto

- Si `PP_GFXOFF_MASK` está puesto en esta placa. Comprobable en ejecución; irrelevante mientras no
  haya herramienta que use el ioctl, pero relevante en cuanto la haya.
- La dirección base de MMIO del bloque gráfico para esta ASIC. Bloqueada como arriba.
- El mecanismo del calentamiento de 6,7 ms sigue abierto, y sigue necesitando registros de MC/VM.
  Esta vía no los da. Las vías que quedan son root sobre el nodo de registro, o el hardware
  puesto en un medio que permita observar sin conductor.
