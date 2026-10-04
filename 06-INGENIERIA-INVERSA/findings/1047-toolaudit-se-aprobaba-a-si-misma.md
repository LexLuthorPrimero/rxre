# 1047 — `toalaudit.py` se aprobaba a sí misma sin ejecutar nada, y deduplicaba por una clave que no identifica un fichero

```
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-MAIN-TOOLAUDIT
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · REPARADO Y VERIFICADO
AFECTADO=08-ARQUITECTURA/tools/toalaudit.py
ORIGEN=el nodo ALIAS-VALIDEZ-MEDICION detecto el segundo; el primero lo encontre yo
ESTADO=PROBADO (dos defectos) · REPARADO · selftest 18/18 PASS por primera vez
```

## Defecto 1 — la puerta se aprobaba a sí misma sin hacer nada

`toalaudit.py` **no tenía punto de entrada**. Medido: 757 líneas, **0 ocurrencias de
`__main__`**, **0 de `sys.exit`**. La última línea no vacía del fichero era un `chk(...)`
dentro de la función `main()`.

Consecuencia medida, no inferida:

```
$ python3 08-ARQUITECTURA/tools/toalaudit.py --self
rc=0    stdout=0 B    stderr=0 B
```

Y la cadena que lo convierte en defecto y no en rareza está en el **propio fichero**, en
`corre_self_test()`:

```
:452   r = subprocess.run([sys.executable, p, flag], capture_output=True, ...)
:454   if r.returncode == 0:
:455       return "PASA"
```

Es decir: **`toolaudit` se lanzaba a sí mismo como script, su `main()` no llegaba a
ejecutarse, salía con rc=0, y `corre_self_test` leía ese rc=0 como `PASA`.**

> La puerta que juzga a las demás herramientas era aprobada sin hacer un solo check.

Es el mismo defecto que el hallazgo 998 documentó para `oracle.sh` —una puerta que pasa
por no hacer nada— con dos diferencias que lo empeoran: aquí la puerta **es** el juez, y
además el `chk` inalcanzable estaba **después** del `return 0` de `main()`, así que el
fichero *parecía* contener una aserción que jamás corrió.

**Reparado:** `if __name__ == "__main__": sys.exit(main())`, y el `chk` movido dentro de
`selftest()`. El self-test **no se había ejecutado nunca**; ahora imprime 34 líneas y
`18/18 PASS`.

## Defecto 2 — la clave de deduplicación no identifica un fichero

`inventariar()` deduplicaba con `clave = os.path.realpath(p)`, bajo el comentario
`# el mismo fichero, dos veces`. Para el mismo fichero, medido:

```
realpath via RAIZ  -> /.../RX550-INVESTIGACION/08-ARQUITECTURA/tools/toalaudit.py
realpath via ALIAS -> /.../RX550-INVESTIGACION-WORKSPACES/01-COORDINACION/08-.../toalaudit.py
iguales como CADENA: False
(st_dev, st_ino) RAIZ : (2067, 7372948)
(st_dev, st_ino) ALIAS: (2067, 7372948)
iguales como INODO   : True
```

El árbol tiene **6 `mount --bind`** de la raíz del proyecto sobre
`RX550-INVESTIGACION-WORKSPACES/<alias>` (`/proc/self/mountinfo` lo dice literalmente), y
`realpath` **no** los resuelve: no son symlinks. O sea que el código no hacía lo que su
comentario afirmaba.

Peor: **el self-test que supuestamente lo cubría usaba la misma clave equivocada**
(`len({os.path.realpath(i["path"]) for i in inv})`). Un test que comparte el defecto del
código no puede detectarlo: pasa siempre. Era un test tautológico.

**Reparado:** clave `(st_dev, st_ino)`, y el check del self-test cambiado a la misma
propiedad con la clave correcta.

## El control negativo, y por qué el PRIMERO no valía

Mi primer control *"demostró"* que las dos claves daban 629 — es decir, que el defecto
no existía. **Ese control estaba mal**, y lo vi porque su resultado era absurdo: estaba
midiendo `realpath` sobre la lista **ya deduplicada**, donde trivialmente no puede haber
duplicados. La deduplicación ya había ocurrido; yo la medía después.

El control correcto ejecuta el pipeline **con cada clave**:

| raíces que recorre | `realpath` (vieja) | `(dev,ino)` (nueva) |
|---|---|---|
| las que usa por defecto | 164 | 164 |
| raíz del proyecto | 629 | 629 |
| **raíz + alias** | **1258** | **629** |

La clave vieja **duplica exactamente** (1258 = 2 × 629). La nueva no.

**Y de aquí sale la calificación honesta, que es la parte que no da gusto:**

```
ARBOLES = [ RAIZ/08-ARQUITECTURA/tools , RAIZ/tools ]
```

`toolaudit` **no recorre la raíz del proyecto**. Sus raíces son dos subdirectorios de
`tools/`, y un `mount --bind` de la raíz del proyecto **no** crea alias dentro de ellos.
Por tanto:

> **El defecto es LATENTE, no ACTIVO.** Los recuentos publicados por `toalaudit` —164
> herramientas; 629 si se le pidiera la raíz— **no están multiplicados**. No se corrige
> ningún número porque ningún número estaba mal por esto.

Se corrige porque (a) el comentario mentía, (b) el self-test era tautológico, y (c) en
cuanto alguien amplíe `ARBOLES` —que es exactamente lo que hacía el nodo
`ALIAS-VALIDEZ-MEDICION` al medir el factor— la herramienta empieza a contar el mismo
fichero dos veces sin avisar.

## Lo que este defecto NO era

No era contaminación de los recuentos publicados. La hipótesis con la que empecé —*«todo
el proyecto puede estar contado siete veces»*— la refutó el propio nodo de alias, y con
el nodo de alias, y con
razon: `os.walk` desde la raiz principal alcanza **0** aliases. La hipotesis era mia,
era falsa, y queda escrita aqui para que la lea quien encuentre este hallazgo
dentro de seis meses.
vaya a leer quien encuentre este hallazgo dentro de seis meses.

## Lo que el nodo de alias dejó abierto y este hallazgo no cierra

`realpath` no identifica un fichero en este árbol. Eso no vale solo para `toalaudit`:
cualquier herramienta que deduplique por `realpath` **parece** protegida y no lo está. La
puerta que lo compruebe de forma permanente tiene que comparar **`(st_dev, st_ino)`**, que
es lo único que sobrevive a un `mount --bind`.