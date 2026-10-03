# benchmark-002 — regresión R-3

## Qué defecto cubre

`parse_calls` trataba **toda** línea `-` de un unified diff de Coccinelle como
sitio de llamada. En un `if/else`, la regla de Coccinelle reemplaza la **rama
completa**, así que dentro del mismo hunk salen como eliminadas líneas de
contexto que no son llamadas:

```diff
 	if (src_id == 224)
-		amdgpu_fence_process(ring);
-	else
-		return 0;
+		amdgpu_fence_process(ring)
+			/*__RC__*/;
+		else
+			return 0;
```

`sí` → `llamadas=3`. `no` → `llamadas=6`.

En el barrido real de `amdgpu_fence_process` sobre
`drivers/gpu/drm/amd/amdgpu/` (linux-7.1.3) el defecto produjo **8 sitios
espurios**: seis `else` y dos `int_handled = false;`. El total.inflateba de 116
a 124.

## Por qué benchmark-001 no lo detectaba

El corpus de benchmark-001 no contenía **ningún** `if/else` con dos ramas de
llamada. El contraste con `grep` cubría recuentos, pero solo se ejecutaba sobre
los corpus congelados, no sobre el árbol real. Los dos huecos juntos dejaron
pasar el defecto durante una ronda completa.

## La fixture

`input/r3_ifelse.c` tiene dos funciones, sin código del kernel:

| función | forma | llamadas reales |
|---|---|---|
| `r3_one_call` | `if (…) { call } else { return 0; }` | 1 |
| `r3_two_calls` | `if (…) { call } else { call }` | 2 |

Total esperado: **3**. El prototipo de `amdgpu_fence_process` no cuenta como
definición, de modo que `ctags` debe reportar `definicion=0`.

`expected/spatch.diff` es la **salida cruda del motor** congelada. Es lo que
permite un control negativo sin depender del historial de git: la regla rota se
aplica a ese diff y **debe** dar 6, la corregida **debe** dar 3.

Si el control negativo dejara de dar 6, el benchmark habría dejado de
discriminar y el resto de la sección R-3 no valdría nada. Por eso se comprueba
explícitamente, no se asume.

## Verificado

| condición | resultado |
|---|---|
| parser defectuoso → suite | `PASS=13 FAIL=1`, `rc=1` |
| parser corregido → suite | `PASS=14 FAIL=0`, `rc=0` |
| regla rota sobre el diff congelado | 6 |
| regla corregida sobre el mismo diff | 3 |
| `grep` textual (1 prototipo + 3 llamadas) | 4 |

## Conteo real esperado

Sobre `drivers/gpu/drm/amd/amdgpu/` de linux-7.1.3:

```
grep textual 'amdgpu_fence_process(' en .c   = 117
menos definiciones                            =   1
llamadas reales                              = 116
```
