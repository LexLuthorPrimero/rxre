"""commands/trace_register.py — Registro de trazas (RXRE).

Reconstrucción mínima. Procedencia y estado de conocimiento:

Documentación del módulo:
  - README.md:19 lo describe como "Registro de trazas".
  - cli.py:32-33 importa ``registrar_trace``, ``TRACE_REGISTRY``
    y ``OperacionNoRegistrada``.
  - test_dispatch004.py:117-127 (``verificar_trace_register``)
    verifica ÚNICAMENTE la importabilidad de los tres nombres.

Búsqueda de reutilización (RXRE-1635):
  - ``git log --all -S 'registrar_trace'`` -> vacío (ningún commit
    añadió/quitó jamás esa cadena).
  - ``git log --all -- '*trace_register*'`` -> vacío (ningún commit
    tocó jamás un fichero trace_register).
  - ``git log --all --diff-filter=D -- '*trace_register*'`` -> vacío
    (nunca existió para ser borrado).
  - ``git grep 'registrar_trace'`` en HEAD y main -> solo cli.py
    (el import). Ausente en todas las ramas, worktrees y el
    filesystem untracked.
  - ``git remote -v``: 0 remotos (RXRE no es público).
  - Conclusión: el módulo NUNCA se commiteó y no existe fuente
    primaria recuperable. No hay implementación reutilizable.

ESTADO DE CONOCIMIENTO (taxonomía RXRE):
  - Existencia del módulo y sus tres nombres: PROVEN (README.md,
    cli.py, test_dispatch004.py).
  - Propósito ("Registro de trazas"): PROVEN (README.md:19).
  - Semántica exacta de ``registrar_trace``/``TRACE_REGISTRY``/
    ``OperacionNoRegistrada``: NOT_DETERMINED. No hay contrato
    tipo README-002 ni implementación original.
  - Esta implementación es un MODEL_CHOICE (patrón registry,
    inferido del nombre "Registro de trazas" y del patrón paralelo
    de api/machine.py). NO es código recuperado.

Consumidor real: NINGUNO. cli.py importa estos símbolos pero no
los usa (imports muertos; ``git grep`` no muestra ningún uso en
cli.py). El único consumidor es el test de importabilidad. Por
tanto los símbolos solo necesitan ser importables; su
comportamiento no afecta a la CLI. Si en el futuro aparece un
consumidor real, la semántica NOT_DETERMINED deberá revalidarse
contra ese consumidor (camino de resolución futura, §65).
"""

# Registro de trazas: nombre -> función de traza.
# (README.md:19 "Registro de trazas".)
TRACE_REGISTRY = {}


class OperacionNoRegistrada(Exception):
    """Operación de traza no presente en ``TRACE_REGISTRY``.

    Modelo paralelo al ``KeyError`` de api/machine.py para
    operaciones no registradas (README-002.md:30), pero como
    excepción de dominio con nombre propio.
    """


def registrar_trace(nombre, funcion):
    """Registra una operación de traza en ``TRACE_REGISTRY``.

    Devuelve ``funcion`` para permitir su uso como decorador::

        @registrar_trace("amdgpu_vm_init")
        def traza_amdgpu_vm_init(...):
            ...

    MODEL_CHOICE: la firma ``(nombre, funcion)`` y el retorno
    decorador son una reconstrucción razonable de "Registro de
    trazas"; la firma real es NOT_DETERMINED (sin fuente primaria).
    Ningún consumidor real la invoca hoy (ver docstring).
    """
    TRACE_REGISTRY[nombre] = funcion
    return funcion
