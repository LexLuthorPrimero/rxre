"""Los siete planos: TODOS lanzan `NotImplementedError`.

Un stub que devuelve `None` deja al llamador con la sensacion de que la
operacion se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE
TODAVIA. La diferencia es la que evita que un pipeline construya conclusiones
encima de planos vacios.

Este test no es burocracia: fija que los siete planos NO puedan usarse por
error. Si alguien implementa uno de verdad y olvida quitarlo de aqui, el
test falla y se entera.
"""
from __future__ import annotations

import inspect

import pytest

from rxre import planes


def test_all_planes_raise():
    """Los 7 planos levantan NotImplementedError al construir."""
    assert len(planes.PLANES) == 7, (
        "el diagrama define 7 planos; si hay mas o menos, el diagrama y el "
        "codigo han divergido y hay que decidir cual manda")
    for nombre, clase in planes.PLANES.items():
        with pytest.raises(NotImplementedError):
            clase()


@pytest.mark.parametrize("nombre", sorted(planes.PLANES))
def test_plano_declares_not_verified(nombre):
    """Cada plano declara `VERIFICADO = False` de forma explicita."""
    clase = planes.PLANES[nombre]
    assert clase.VERIFICADO is False
    assert clase.COMPONENTE == nombre


@pytest.mark.parametrize("nombre", sorted(planes.PLANES))
def test_plano_has_todo_and_adversarial_test(nombre):
    """Cada docstring tiene TODO, evidencia desbloqueante y test adversarial.

    Se comprueba el CONTENIDO, no que el docstring exista. Un docstring que
    dice "TODO: implementar" sin decir que evidencia lo desbloquea es una
    nota, no un contrato.
    """
    doc = inspect.getdoc(planes.PLANES[nombre]) or ""
    assert "TODO" in doc, "%s sin TODO" % nombre
    assert "Evidencia que lo desbloquearia" in doc, \
        "%s no dice que evidencia lo desbloquearia" % nombre
    assert "Test adversarial pendiente" in doc, \
        "%s no declara el test adversarial que lo tumbaria" % nombre


def test_stub_raises_with_pointer_to_the_docstring():
    """El mensaje de la excepcion apunta al TODO, no dice 'no implementado'.

    La diferencia es util en un traceback: quien lo lea tiene que saber donde
    esta la explicacion de POR QUE falta, no solo que falta.
    """
    with pytest.raises(NotImplementedError, match="audit A-F"):
        planes.Mente()