# 503 · `src_data[0]` como discriminante: la afirmación de `060` sobrevive, pero su cita no

`CLASSIFICATION=EVIDENCE` · `TRACK=STATIC` · `WORK_CLASS=READ_ONLY`
`WRITE_EXECUTION=NONE` · `MODIFICATIONS=0` · `RUNTIME=NOT_RUN` · `GPU INTACTA`
`HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0` (por clase+vendor)

## Cuestión principal

`060` afirma que `src_data[0]` es un **discriminante de subtipo de evento**, y lo
apoya en `dce_v8_0.c:3083-3115`. `292` acaba de medir que **`dce_v8_0.c` no lo
ejecuta esta GPU**.

La pregunta no es si la cita es exacta — lo es — sino si **la afirmación**
sobrevive por otra vía. Una cita muerta puede sostener una afirmación verdadera,
y una cita viva puede sostener una falsa. Son dos cosas y hay que separarlas.

## Criterio de terminación

Determinar si el discriminante por `src_data[0]` existe en código **en ruta de
ejecución** de esta GPU. **Cumplido.**

## 1 · La cita de `060` es exacta

```
dce_v8_0.c:3083   static int dce_v8_0_crtc_irq(struct amdgpu_device *adev,
dce_v8_0.c:3091           switch (entry->src_data[0]) {
```

Correcta. No es un error de transcripción. **El problema no es la cita: es que el
fichero no se ejecuta.**

## 2 · La cadena de alcanzabilidad, cerrada entera

```
dce_v8_0_crtc_irq                       (3083)   el decodificador que cita 060
  <- dce_v8_0_crtc_irq_funcs.process    (3532)
  <- adev->crtc_irq.funcs                (3551, dentro de dce_v8_0_set_irq_funcs)
  <- dce_v8_0_set_irq_funcs(adev)        (2685, dentro de dce_v8_0_early_init)
  <- dce_v8_0_ip_block.early_init        (3236)
  <- amdgpu_device_ip_block_add(...)     ← NO EXISTE en todo amdgpu/
```

**No hay más entradas.** Ese decodificador **no se ejecuta nunca en esta placa.**

## 3 · Y en el camino conectado tampoco hay discriminante de display

Solo tres ficheros registran `crtc_irq.funcs` en todo `amdgpu/`:
`dce_v6_0.c`, `dce_v8_0.c`, `dce_v10_0.c`. **Ninguno es de esta GPU.** Y
`src_data[0]` **no aparece** en `amdgpu_dm.c` ni en `amdgpu_dm_irq.c`, que es
donde vive el DC de Polaris12 (`dm_ip_block`).

## 4 · Dónde aparece `src_data[0]`, y cuál de esos ficheros corre aquí

```
dce_v8_0.c   5      NO EN RUTA      dce_v6_0.c   5      NO EN RUTA
dce_v10_0.c  5      NO EN RUTA      vce_v3_0.c   3      ** EN RUTA **
vce_v4_0.c   3      no              gmc_v8_0.c   2      ** EN RUTA **
```

## 5 · Los dos que corren, y NO dicen lo mismo

**`gmc_v8_0.c` — lo imprime, no lo usa como discriminante:**

```c
gmc_v8_0.c:1435   dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n",
                          entry->src_id, entry->src_data[0]);
gmc_v8_0.c:1465   dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n",
                          entry->src_id, entry->src_data[0]);
```

Es el **payload de un fault**, volcado a un log. No hay `switch`. Es exactamente
lo que `059` había dicho al descartarlo, y lo que `060` respondió que era la
pregunta incorrecta.

**`vce_v3_0.c` — sí es un discriminante de subtipo:**

```c
vce_v3_0.c:753   switch (entry->src_data[0]) {
                case 0:
                case 1:
                case 2:
                        amdgpu_fence_process(&adev->vce.ring[entry->src_data[0]]);
                        break;
                default:
                        DRM_ERROR("Unhandled interrupt: %d %d\n", ...);
```

Y **`vce_v3_0.c` es el código que corre en esta GPU**: el bloque es
`vce_v3_4_ip_block` y el código es `vce_v3_0`. Uno de los cuatro aliasing que
`292` corroboró.

## Veredicto sobre `060`: la afirmación sobrevive, la cita no

| mitad de la afirmación | estado |
|---|---|
| `src_data[0]` es el payload de un evento | **CONFIRMADA, con cita viva**: `gmc_v8_0.c:1435` — el GMC de esta GPU lo imprime como payload del fault |
| `src_data[0]` es un discriminante de subtipo | **CONFIRMADA, con cita viva y distinta**: `vce_v3_0.c:753` — `switch` por subtipo en el VCE de esta GPU |
| «el decodificador de display está en `dce_v8_0.c`» | **REFUTADA para esta GPU**: ese fichero no se ejecuta |

Y hay una coherencia interna que reinforces el resultado: `060` dice que el
decodificador **no** está en el GMC. Y el GMC, en efecto, **no** lo usa como
discriminante — solo lo imprime. Las dos mitades de `060` son correctas, pero por
ficheros distintos, y uno de los dos que nombra está muerto.

**Lo que hay que corregir en `060` no es su conclusión: es la procedencia.** La
cadena causal funciona; el eslabón que señalaba el fichero no se ejecuta aquí.

## Confounders

- **No he construido ni ejecutado nada.** Es `PROVEN` sobre el texto.
- **`src_data[0]` en `vce_v3_0.c` es del VCE, no del display.** La granularidad
  de subtipo queda demostrada para video, no para display en esta placa. Para
  display **no hay** código vivo que la demuestre: `NOT_DETERMINED`, no
  `PROVEN_ABSENT`, porque no he revisado el camino de DC de forma exhaustiva.
- No he revisado si algún módulo fuera de `amdgpu/` registra `crtc_irq`.
- He buscado `src_data[0]`; no he buscado `src_data` con otro índice. Un
  `src_data[1]` podría discriminarse en el camino de display.
- **`060` sigue siendo un documento de otra sesión.** No he editado nada suyo:
  registro la corrección, no la aplico.

## Clasificación

| afirmación | estado |
|---|---|
| `060` cita `dce_v8_0.c:3083-3115` correctamente | `PROVEN` |
| `dce_v8_0_crtc_irq` no es alcanzable en esta GPU | `PROVEN` — cadena cerrada |
| solo 3 ficheros registran `crtc_irq.funcs`, ninguno de esta GPU | `PROVEN` |
| `src_data[0]` no aparece en `amdgpu_dm.c` | `PROVEN` |
| `src_data[0]` es payload de un fault en el GMC vivo | `PROVEN` — `gmc_v8_0.c:1435` |
| `src_data[0]` es discriminante de subtipo en código vivo | `PROVEN` — `vce_v3_0.c:753` |
| `vce_v3_0.c` es el código de esta GPU | `PROVEN` — bloque `vce_v3_4`, código `v3_0` |
| «el decodificador de display está en `dce_v8_0.c`» | `REFUTED` para esta GPU |
| hay discriminante de subtipo para **display** vivo | `NOT_DETERMINED` |
| `src_data[1]` u otro índice discrimina en DC | `NOT_OBSERVED` |

## Desfalsificación

- **(a)** la cita de `060` es exacta → refutable con `dce_v8_0.c:3083`. **Verificado.**
- **(b)** el decodificador no se ejecuta → refutable siguiendo la cadena hasta
  `amdgpu_device_ip_block_add`. **Verificado: no existe.**
- **(c)** hay discriminante vivo → refutable con `grep src_data\[0\]` y la
  comprobación de ruta. **Verificado: `vce_v3_0.c`.**
- **(d)** el GMC no discrimina → refutable con `gmc_v8_0.c:1432-1466`. **Verificado:**
  dos `dev_err`, ningún `switch`.
- **(e)** que el DC de esta GPU discrimine por subtipo → **no comprobado.**

## UNLOCKS

- **Un claim puede tener la conclusión correcta y la procedencia muerta**, y eso
  no lo detecta ningún linter de citas: `dce_v8_0.c:3083` resuelve perfectamente.
  La cita es válida y el fichero es inerte. **Resoluble ≠ en ruta de ejecución.**
  Son dos preguntas, y hasta ahora el proyecto solo hacía la primera.
- **`292` Finds SSH el mecanismo, y este hallazgo lo confirma en un caso**: la
  cuarta pregunta de `cite_registry` —*¿lo ejecuta esta GPU?*— no es
  redundante con *¿resuelve la cita?*. Acaba de encontrar un error que la
  comprobación de resolubilidad no podía ver.
- **`059` y `060` tenían razón a medias los dos.** `059` dijo que `src_data[0]`
  era un puntero de ring: falso como generalidad, cierto para el consumidor que
  él miró. `060` dijo que era un discriminante: cierto, pero no en el fichero
  que\Eventuala.
- **Siguiente paso, y sale de aquí**: existe una comprobación que ninguna
  herramienta tiene —*¿esta función es alcanzable desde un `ip_block` que esta
  GPU añade?*— y el caso de `dce_v8_0.c` demuestra que encuentra defectos reales.
  Convertir la **cadena de alcanzabilidad** en un verificador de función, y no
  solo de fichero, es la capacidad que falta.

## Evidencia

```
sed -n 3083,3092p dce_v8_0.c      switch (entry->src_data[0])   <- la cita de 060
grep -n dce_v8_0_crtc_irq dce_v8_0.c   3083 def / 3532 funcs / 3551 asigna
grep -rn "crtc_irq.funcs" amdgpu/      solo dce_v6_0, dce_v8_0, dce_v10_0
grep -c "src_data\[0\]" gmc_v8_0.c     2   -> dos dev_err, ningun switch
sed -n 753,757p vce_v3_0.c       switch por subtipo -> amdgpu_fence_process
vi.c:2124  amdgpu_device_ip_block_add(adev, &vce_v3_4_ip_block)  -> v3_0 corre
```

`WRITE_EXECUTION=NONE`. `MODIFICATIONS=0`. `GPU INTACTA`.