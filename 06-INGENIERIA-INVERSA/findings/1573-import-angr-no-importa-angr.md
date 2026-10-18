# 1573 · `import angr` no importa angr: el directorio clonado es un namespace package

```
CLASSIFICATION=FACT · TRACK=RUNTIME
HARDWARE_SCOPE=NINGUNO · WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0
GPU INTACTA · NO se ha tocado 0000:00:02.0
CIERRA=la identidad de los cuatro backends clonados (angr y rz-ghidra)
ABRE=si compilar/instalar angr y rz-ghidra es necesario para cerrar binary.decompile
```

## Qué demuestra

Dentro del árbol del proyecto, `import angr` **funciona**:

```python
>>> import angr
>>> angr.__file__
None
>>> angr.__path__
['/home/lucas/Escritorio/RX550-INVESTIGACION/tools/rxre/github/angr']
>>> angr.Project
AttributeError: module 'angr' has no attribute 'Project'
```

`__path__` apunta al **directorio clonado**, no al paquete. Python lo trata como
*namespace package* porque el directorio se llama `angr`. Fuera del árbol:

```
ModuleNotFoundError: No module named 'angr'
```

> un import que funciona no es un paquete importado

## Por qué decide el estado de la capacidad

El registro de backends exige identidad **verificable en runtime**, no declarada.
Con `__file__ is None` no hay forma de confirmar qué se importó. Un backend que
no se puede identificar no puede entrar en provenance: se registraría un
`tool_version` que nadie puede confirmar.

Por eso `angr` y `rz-ghidra` están en `NOT_DETERMINED`, no en `UNAVAILABLE`:

```
no se comprobó que angr no sirva; se comprobó que no se puede VERIFICAR aquí
```

Declararlos `AVAILABLE` por haber clonado el repo sería `NOT_FOUND` convertido
en `PROVEN_ABSENT` — la clase de defecto que §5 prohíbe.

## Consecuencia para el contrato

`Backend.path()` busca el **binario** en `PATH`, no el módulo. La identidad se
verifica ejecutando el ejecutable, porque en Python un import no es prueba de
nada cuando el nombre del directorio colisiona con el del paquete.

## Reproducir

```bash
cd ~/Escritorio/RX550-INVESTIGACION && python3 -c "import angr; print(angr.__file__, list(angr.__path__))"
cd /tmp && python3 -c "import angr"      # ModuleNotFoundError
```

## Provenance

```text
artefacto   tools/rxre/github/angr  commit be995f52ee38a055d0f96d04f3e4d02192a3d743
producer    interpreter python3 del sistema
transform   import angr -> inspeccion de __file__ / __path__ / atributos
registro    tools/rxre/backends/registry.py -> NO_VERIFICABLES
limitacion  no se instalo angr; NO se compilo rz-ghidra (§20)
```