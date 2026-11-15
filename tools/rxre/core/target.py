#!/usr/bin/env python3
"""RXRE-007 FASE 1. Identidad del target y reparto de capacidades por target.

QUE ES Y QUE NO ES
-----------------
Este modulo IDENTIFICA la pieza de hardware contra la que se esta trabajando.
No interpreta ningun valor. Un target correcto con una lectura mal
interpretada sigue siendo un error; y un target mal identificado con una
lectura correcta tambien. Por eso aqui no hay ningun valor de registro, ni
offset, ni asercion semantica: eso es trabajo del decompilador y del
productor, no del que dice QUE hardware es.

Lo que si hace, y es su trabajo completo:

  1. `get_current_target()` — quien es el target, LEIDO del sistema, con la
     procedencia de cada dato anotada.
  2. `get_capabilities_for_target()` — que preguntas son validas para ese
     target, y una EXCLUSION CONSERVADORA para los que no estan mapeados.
  3. `get_target_provenance()` — por que se eligio este target.

LA EXCLUSION CONSERVADORA
------------------------
Un target sin mapear devuelve `[]`, no "todas". Es la decision de diseño
que mas importa aquí: ante la duda, se responde menos. Si se devolvieran
todas las capacidades para un target desconocido, un fallo de identificacion
pasaria desapercibido y cada lectura seria irrelevante sin que nada lo
dijera. Con `[]` el sistema dice "no se que hacer aqui", que es verdad.

PROCEDENCIA, Y POR QUE NO SE USA UN PROCESO EXTERNO
---------------------------------------------------
La identidad se lee de `/sys/bus/pci/devices/<BDF>/{vendor,device,revision}`.
MEDIDO 2026-10-14 en esta maquina:

    /sys/bus/pci/devices/0000:01:00.0/vendor    -> 0x1002
    /sys/bus/pci/devices/0000:01:00.0/device    -> 0x699f
    /sys/bus/pci/devices/0000:01:00.0/revision  -> 0xc7
    /sys/bus/pci/devices/0000:01:00.0/driver    -> .../pci/drivers/amdgpu

sysfs y no `lspci`: no hay proceso que pueda faltar, no hay texto que
parsear, y el kernel mantiene la ruta viva mientras el device este
enchufado. `lspci` es una segunda fuente, y se usa SOLO como contraste en
`_get_target_from_pci()` cuando se le pasa un BDF explicito.

El nombre del ASIC (`Polaris12`) y la generacion (`gfx_8_0`) NO salen de
sysfs: sysfs no los publica. Salen del mapa `_MAPA_PCI`, y su PROCEDENCIA
lo dice. Un nombre de ASIC escrito sin decir de donde salio es una
afirmacion que parece un hecho; aqui se declara de donde viene.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.capabilities import CAPACIDADES

#: Directorio de PCI en sysfs.
_SYSFS_PCI = "/sys/bus/pci/devices"

#: El UNICO PCI que este proyecto autoriza. Viene de la regla del
#: propietario: la grafica integrada del procesador (0000:00:02.0) no se
#: toca. El modulo no "elige": aplica la lista y dice.
ALLOWED_PCI = ("0000:01:00.0",)


@dataclass(frozen=True)
class TargetIdentity:
    """Identidad de una pieza de hardware.

    frozen=True a proposito: una identidad que se puede mutar en medio de
    una sesion es una identidad que ya no identifica nada. Los seis campos
    son de lectura; para cambiar de target se construye otro.
    """
    vendor: str
    device: str
    revision: str
    asic: str
    gfx_generation: str
    provenance: Tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:  # pragma: no cover - solo legibilidad
        return ("TargetIdentity(vendor=%s device=%s rev=%s asic=%s gfx=%s)"
                % (self.vendor, self.device, self.revision, self.asic,
                   self.gfx_generation))


#: Mapa PCI -> (asic, generacion). MEDIDO: `1002:699f` es la Lexa PRO /
#: Radeon 550 de este host (`lspci -nn -d 1002:699f`), y la base de datos de
#: UMR de esta maquina nombra a ese ASIC `polaris12` con IPs `gfx_8_0` /
#: `bif_5_1` / `smu_7_1_3`, o sea generacion gfx 8.0.
#:
#: Procedencia: `lspci` para el id, `/usr/share/umr/database/polaris12.asic`
#: para el nombre del ASIC y la generacion. Ninguno de los dos valores sale
#: de este modulo por deduccion.
_MAPA_PCI: Dict[str, Tuple[str, str]] = {
    "1002:699f": ("Polaris12", "gfx_8_0"),
}

#: Rutas de donde se toma cada parte de la identidad. Se exportan para que
#: la procedencia sea un DATO y no un texto pegado en un log.
_PROCEDENCIA_PCI = "sysfs:/sys/bus/pci/devices/{bdf}/{campo}"
_PROCEDENCIA_ASIC = ("mapa declarado en core.target._MAPA_PCI, derivado de "
                     "lspci -nn -d 1002:699f y del nombre del ASIC en "
                     "/usr/share/umr/database/polaris12.asic")


def _map_pci_id_to_asic_gfx(pci_id: str) -> Optional[Tuple[str, str]]:
    """id PCI 'vendor:device' -> (asic, generacion) o None si no se conoce.

    Acepta `0x1002:0x699f`, `1002:699f` y `1002:699F`. La normalizacion es
    deliberada: quien llama puede que venga de sysfs (con 0x) o de `lspci`
    (sin 0x, en minusculas), y que esas dos formas den resultados
    distintos seria un fallo de normalizacion disfrazado de target
    desconocido.
    """
    if not isinstance(pci_id, str) or ":" not in pci_id:
        return None
    vendor, _, device = pci_id.partition(":")
    vendor = vendor.lower().removeprefix("0x").strip()
    device = device.lower().removeprefix("0x").strip()
    if not vendor or not device:
        return None
    return _MAPA_PCI.get("%s:%s" % (vendor, device))


def _get_target_from_pci(bdf: str) -> Optional[TargetIdentity]:
    """Lee la identidad de un BDF concreto desde sysfs. None si no se puede.

    No lanza excepcion si el device no existe: la ausencia de un target es
    una RESPUESTA ("no se"), no un fallo del programa. Un `FileNotFoundError`
    obligaria a que cada consumidor tratara el caso normal como error.
    """
    base = os.path.join(_SYSFS_PCI, bdf)
    try:
        with open(os.path.join(base, "vendor")) as fh:
            vendor = fh.read().strip().lower().removeprefix("0x")
        with open(os.path.join(base, "device")) as fh:
            device = fh.read().strip().lower().removeprefix("0x")
        with open(os.path.join(base, "revision")) as fh:
            revision = fh.read().strip().lower().removeprefix("0x")
    except OSError:
        return None

    par = _map_pci_id_to_asic_gfx("%s:%s" % (vendor, device))
    if par is None:
        return None
    asic, gfx = par

    prov: List[str] = [
        "PCI %s: vendor=%s device=%s rev=%s" % (bdf, vendor, device, revision),
        "vendor/device/revision leidos de " + _PROCEDENCIA_PCI.format(
            bdf=bdf, campo="{vendor,device,revision}"),
        "asic=%s gfx=%s desde %s" % (asic, gfx, _PROCEDENCIA_ASIC),
    ]
    driver = os.path.join(base, "driver")
    if os.path.exists(driver):
        try:
            prov.append("driver en uso: %s" % os.path.basename(
                os.path.realpath(driver)))
        except OSError:
            pass
    return TargetIdentity(vendor=vendor, device=device, revision=revision,
                          asic=asic, gfx_generation=gfx,
                          provenance=tuple(prov))


def _initialize_capability_mapping() -> Dict[str, List[dict]]:
    """Mapa generacion -> capacidades validas para esa generacion.

    Se construye UNA vez y se cachea. Se construye desde `CAPACIDADES` leido
    en el momento, no desde una copia: una capacidad nueva en
    `core.capabilities` entra en el mapa sin tocar este fichero. Un mapa
    escrito a mano se desincroniza del catalogo sin que nada lo note, y un
    mapa desincronizado devuelve capacidades que ya no existen.
    """
    global _MAPA_CAPACIDADES
    mapa: Dict[str, List[dict]] = {}
    for cap in CAPACIDADES:
        mapa.setdefault(cap.get("gfx_generation", ""), []).append(cap)
    _MAPA_CAPACIDADES = mapa
    return mapa


#: Cache del mapa. Lo inicializa `_initialize_capability_mapping()`.
_MAPA_CAPACIDADES: Optional[Dict[str, List[dict]]] = None


def get_current_target(bdf: Optional[str] = None) -> Optional[TargetIdentity]:
    """Target actual, LEIDO del sistema. None si no hay ninguno autorizado.

    Sin `bdf`, recorre `ALLOWED_PCI` en orden y devuelve el primero que
    exista y está mapeado. El orden es el de la allow-list, que es una
    decision del propietario, no un resultado de esta funcion.
    """
    if bdf is not None:
        return _get_target_from_pci(bdf)
    for candidato in ALLOWED_PCI:
        t = _get_target_from_pci(candidato)
        if t is not None:
            return t
    return None


def get_capabilities_for_target(target) -> List[dict]:
    """Capacidades validas para `target`. `[]` si su generacion no est&aacute; mapeada.

    LA EXCLUSION ES EL PUNTO. Una generacion sin mapa devuelve lista vacia.
    No devuelve "todas", y no lanza error: no saber que hacer en un target
    desconocido ES una respuesta valida, y es la unica segura. Devolver
    todas haria que un fallo de identificacion pasara desapercibido, con
    lectura correcta sobre el hardware equivocado.
    """
    if target is None:
        return []
    if _MAPA_CAPACIDADES is None:
        _initialize_capability_mapping()
    gen = getattr(target, "gfx_generation", "") or ""
    caps = (_MAPA_CAPACIDADES or {}).get(gen)
    return list(caps) if caps else []


def get_target_provenance(target) -> Tuple[str, ...]:
    """Por que se eligio este target. Tuple de cadenas no vacias.

    Nunca devuelve `None` ni una tupla vacia para un target existente: una
    identidad sin procedencia es una afirmacion sin respaldo, que es
    exactamente lo que el resto de RXRE no acepta. Para un target que no
    existe, devuelve una sola cadena que lo dice, en vez de una tupla vacia
    que se podria leer como "no hay nada que explicar".
    """
    if target is None:
        return ("sin target: ninguno de los PCI autorizados %s esta presente "
                "o es reconocible en esta maquina" % (ALLOWED_PCI,),)
    prov = tuple(getattr(target, "provenance", ()) or ())
    return prov if prov else ("identidad construida sin procedencia declarada",)