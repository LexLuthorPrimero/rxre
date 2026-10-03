# 983 · `awk '…{…; exit}'` + `set -o pipefail` = 141: un guard que se mata a sí mismo al mirar

```text
CLASSIFICATION=ERROR+PATTERN · TRACK=TOOLING
CORPUS=ninguno
HARDWARE_SCOPE=no aplica: es shell, no hardware
WORK_CLASS=READ_ANALYSIS + WRITE_LOCAL
AUTHORIZATION=NONE · RUNTIME=ejecución de shell sobre /sys/kernel/btf, solo lectura
AUTORIA=AGENT-04 (RUNTIME/PROBING/FUZZING/ORACLES)
CONTINUES=982 (donde aparece como el defecto 2b de la reparación)
HALLAZGO=reutilizable: cualquier guion con `set -o pipefail` que haga
        `$(herramienta | awk '…{print; exit}')` tiene este defecto
```

## El defecto

Siete extracciones de `preruntime.sh` usan la forma

```bash
off=$(pahole -C amdgpu_device /sys/kernel/btf/amdgpu 2>/dev/null \
        | awk '/no_hw_access/ {print $(NF-2); exit}')
```

`awk` sale en cuanto casa. `pahole` sigue escribiendo y recibe **SIGPIPE**. Con
`set -o pipefail` —que el harness activa en su línea 25— la sustitución de comando
devuelve **141**, y con `set -e` el script **muere ahí**.

## Medido, y con la causa aislada

```
bash -c 'set -euo pipefail; v=$(pahole … | awk "…{print \$1; exit}"); echo ok'
   -> exit 141, no imprime nada
bash -c 'set -eu;       v=$(pahole … | awk "…{print \$1; exit}"); echo ok'
   -> exit 0, imprime
```

La **única** diferencia entre las dos líneas es `pipefail`. Eso es lo que convierte un
`awk` corriente en un fallo fatal, y por eso no se ve leyendo el código: cada línea está
bien escrita.

## Y quitar el `exit` NO es la solución

`exit` es a la vez **necesario** y **fatal**, y esa tensión es el contenido del hallazgo:

```
$ pahole -C pci_dev /sys/kernel/btf/vmlinux | grep '\<device\>'
10  short unsigned int  device;   offset  62   <- la correcta
88  struct device       dev;      offset 208   <- falso positivo
```

`\<device\>` casa **dos** líneas, porque `struct device` contiene la palabra `device`.
Sin `exit`, la variable saldría con dos líneas y la comparación posterior no podría pasar.

## El fix que conserva las dos propiedades

awk debe **leer hasta EOF** (para que no haya SIGPIPE) e **imprimir solo la primera
coincidencia** (lo que hacía el `exit`):

```awk
{ if (!s) { print $(NF-2); s=1 } }
```

## Por qué esto merece un hallazgo propio

1. **Es invisible al leer.** Cada línea es correcta. El defecto está en la interacción
   entre dos opciones de shell que se activan por separado en la cabecera.
2. **No da error: da el código equivocado.** Sin `pipefail` la línea funciona y devuelve
   bien. Con `pipefail`, muere. El mismo código es correcto o fatal según una bandera que
   está 300 líneas más arriba.
3. **Aparece solo al ejecutar**, y en un bloque que, mientras existian los otros tres
   defectos, **no se podía alcanzar**. Por eso el hallazgo 973 no lo vio: no había forma de
   llegar a ejecutarlo. Lo encontró la reparación.
4. **El patrón es reutilizable.** Cualquier guion con `pipefail` que use
   `$(herramienta | awk '…{print; exit}')` lo tiene. Vale para `pahole`, `readelf`,
   `objdump`, `lsblk`, `lspci`, cualquier cosa.

## La regla que sale

```
Un pipe cuyo consumidor puede salir antes que el productor es un PRODUCTOR CON
ERRORES LATENTES: sin pipefail devuelve bien, con pipefail mata el guion.
```

Y la forma correcta no es `|| true` —que escondería también los fallos reales— sino
consumir todo y filtrar dentro del consumidor.

## Nota sobre por qué no apareció antes

973 audito el harness **estaticamente** y midio las precondiciones por awk **del harness**,
y en ambos casos el `set -e` de esos instrumentos corto antes. El defecto número cuatro
necesitaba que alguien ejecutara el bloque correcto con el `set -o pipefail` correcto. Ese
alguien fue la reparación de 982, y por eso el orden de los dos hallazgos no es
arbitrario: **982 no se podía validar sin descubrir 983**.

```
LIMITACION  Verificado con awk de GNU (mawk presenta diferencias de comportamiento con
            exit temprano en algunos casos). No se ha medido en bash distinto de 5.x.
```