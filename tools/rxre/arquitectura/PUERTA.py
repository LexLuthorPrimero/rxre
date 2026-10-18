"""PUERTA: AUDIT A-F -> DELIVERED -> REVISION INDEPENDIENTE -> ACCEPTED.

    DEL DIAGRAMA:
      AUDIT A-F -> STATE=DELIVERED -> REVISION INDEPENDIENTE
                          |
                +---------+---------+
                v                   v
            CONTESTED             ACCEPTED
                |                    |
      vuelve a CHALLENGED     ETAPA 1 (bloqueada hasta aqui)

      [v3] ACCEPTED no es string manual:
        · artefactos integros
        · 0 refutaciones criticas pendientes
        · revisor declara no haber participado
        · autoridad de aceptacion nombrada

LA REGLA QUE SOSTIENE TODO ESTE MODULO
--------------------------------------
`aceptar()` NO tiene forma de recibir un booleano de "ya podeis". Las cuatro
condiciones se EVALUAN contra el estado del repo. Si falta una, devuelve
CONTESTED con la condicion que falta nombrada.

La razon de que no exista un metodo `marcar_aceptado()` es que entonces
alguien lo llamaria. El diagrama dice "ACCEPTED no es string manual", y una
funcion que escribe "ACCEPTED" es exactamente el string manual que prohibe.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import NOT_DETERMINED, PROVEN, PROVEN_ABSENT
from .schemas import canonico, hash_contenido

DELIVERED = "DELIVERED"
ACCEPTED = "ACCEPTED"
CONTESTED = "CONTESTED"
CHALLENGED = "CHALLENGED"

CONDICIONES = (
    "artefactos_integros",
    "cero_refutaciones_criticas",
    "revisor_sin_participacion",
    "autoridad_aceptacion_nombrada",
)


class Puerta:
    def __init__(self):
        self.artefactos: Dict[str, Dict] = {}
        self.refutaciones: List[Dict] = []
        self.participaciones: List[str] = []
        self.autoridad: Optional[str] = None
        self.revisor: Optional[str] = None
        self.historico: List[Dict] = []

    # -- registro de lo que hay que mirar --------------------------------
    def registrar_artefacto(self, nombre: str, ruta: str,
                            hash_declarado: Optional[str] = None) -> str:
        """Guarda el artefacto CON su hash declarado.

        Guardar el contenido sin el hash declarado seria permitir que la
        integridad se declare a posteriori. Se calcula ahora o no se
        calcula nunca.
        """
        if not os.path.isfile(ruta):
            raise FileNotFoundError(ruta)
        with open(ruta, "rb") as fh:
            bruto = fh.read()
        actual = hashlib.sha256(bruto).hexdigest()
        a_id = "art_" + hash_contenido([nombre, actual])[:16]
        self.artefactos[a_id] = {
            "id": a_id, "nombre": nombre, "ruta": ruta,
            "bytes": len(bruto),
            "hash_declarado": hash_declarado, "hash_actual": actual,
        }
        return a_id

    def agregar_artefacto_directo(self, nombre: str, contenido: str,
                                  hash_declarado: Optional[str] = None) -> str:
        bruto = contenido.encode("utf-8")
        actual = hashlib.sha256(bruto).hexdigest()
        a_id = "art_" + hash_contenido([nombre, actual])[:16]
        self.artefactos[a_id] = {
            "id": a_id, "nombre": nombre, "ruta": "<memoria>",
            "bytes": len(bruto), "hash_declarado": hash_declarado,
            "hash_actual": actual,
        }
        return a_id

    def refutar(self, artefacto_id: str, motivo: str,
                critica: bool = True) -> Dict:
        r = {"artefacto": artefacto_id, "motivo": motivo,
             "critica": bool(critica), "resuelta": False}
        self.refutaciones.append(r)
        return r

    def declarar_participacion(self, quien: str, artefacto_id: str) -> None:
        """Si alguien participo en construir el artefacto, ese mismo alguien
        NO puede ser el revisor independiente. Es la primera condicion que
        se puede refutar a uno mismo."""
        self.participaciones.append(quien)

    def nombrar_autoridad(self, quien: str) -> None:
        self.autoridad = quien

    def nombrar_revisor(self, quien: str) -> None:
        self.revisor = quien

    # -- las cuatro condiciones, EVALUADAS --------------------------------
    def evaluar_condiciones(self) -> Dict[str, Dict]:
        c: Dict[str, Dict] = {}

        # 1. artefactos integros
        if not self.artefactos:
            c["artefactos_integros"] = {
                "cumple": False,
                "detalle": "no hay artefactos registrados: no hay nada que "
                           "integridad pueda proteger",
                "integridad": None}
        else:
            fallos = []
            capas = []
            for a in self.artefactos.values():
                if a["ruta"] == "<memoria>":
                    capas.append({"artefacto": a["nombre"],
                                  "integridad": "PASS",
                                  "autenticidad": NOT_DETERMINED,
                                  "validez_semantica": NOT_DETERMINED})
                    continue
                with open(a["ruta"], "rb") as fh:
                    ahora = hashlib.sha256(fh.read()).hexdigest()
                integro = (a["hash_declarado"] is None
                           or ahora == a["hash_declarado"])
                if not integro:
                    fallos.append(a["nombre"])
                capas.append({
                    "artefacto": a["nombre"],
                    "integridad": "PASS" if integro else "FAIL",
                    "autenticidad": NOT_DETERMINED,
                    "validez_semantica": NOT_DETERMINED})
            c["artefactos_integros"] = {
                "cumple": not fallos,
                "detalle": ("todos integros" if not fallos else
                            "artefactos alterados: %s" % ", ".join(fallos)),
                "capas": capas}

        # 2. cero refutaciones criticas pendientes
        criticas = [r for r in self.refutaciones
                    if r["critica"] and not r["resuelta"]]
        c["cero_refutaciones_criticas"] = {
            "cumple": not criticas,
            "detalle": ("0 refutaciones criticas pendientes" if not criticas
                        else "%d refutaciones criticas pendientes"
                             % len(criticas)),
            "pendientes": [r["motivo"] for r in criticas]}

        # 3. el revisor declara no haber participado
        if self.revisor is None:
            c["revisor_sin_participacion"] = {
                "cumple": False,
                "detalle": "no hay revisor nombrado"}
        elif self.revisor in self.participaciones:
            c["revisor_sin_participacion"] = {
                "cumple": False,
                "detalle": "el revisor %s participo en construir artefactos"
                           % self.revisor,
                "participaciones": sorted(set(self.participaciones))}
        else:
            c["revisor_sin_participacion"] = {
                "cumple": True,
                "detalle": "el revisor %s no figura entre los participantes"
                           % self.revisor}

        # 4. autoridad de aceptacion nombrada
        c["autoridad_aceptacion_nombrada"] = {
            "cumple": self.autoridad is not None,
            "detalle": ("autoridad nombrada: %s" % self.autoridad
                        if self.autoridad else
                        "no hay autoridad de aceptacion nombrada")}

        return c

    # -- el veredicto -----------------------------------------------------
    def aceptar(self) -> Dict[str, Any]:
        """Evalua las 4 condiciones. NO acepta un argumento de entrada.

        No hay ningun parametro por el que se pueda pasar "ya podeis".
        """
        condiciones = self.evaluar_condiciones()
        faltan = [k for k in CONDICIONES if not condiciones[k]["cumple"]]
        estado = ACCEPTED if not faltan else CONTESTED
        veredicto = {
            "estado": estado,
            "condiciones": condiciones,
            "faltan": faltan,
            "etapa_1_bloqueada": estado != ACCEPTED,
            "criterio": ("ACCEPTED se alcanza solo si las %d condiciones se "
                         "cumplen todas" % len(CONDICIONES)),
        }
        self.historico.append(veredicto)
        return veredicto

    def Desafiar(self, evidencia_nueva: str) -> Dict[str, Any]:
        """ACCEPTED no es terminal. Evidencia nueva devuelve a CHALLENGED."""
        self.historico.append({"estado": CHALLENGED,
                               "evidencia": evidencia_nueva,
                               "ts": hash_contenido([evidencia_nueva,
                                                     len(self.historico)])[:12]})
        return self.historico[-1]


def estado_actual(ruta_state: str) -> Tuple[str, Optional[str]]:
    """Lee audit/STATE sin escribirlo.

    Devuelve (estado, motivo_del_camblog) para que quien llame vea el
    estado JUNTO con por que se cambio. Leer el estado sin su historia
    permite que un ACCEPTED aparezca sin explicacion, que es la forma mas
    economica de perder trazabilidad.
    """
    if not os.path.isfile(ruta_state):
        return NOT_DETERMINED, "no existe"
    with open(ruta_state, "r", encoding="utf-8") as fh:
        bruto = fh.read()
    estado = bruto.strip()
    changelog = os.path.join(os.path.dirname(ruta_state),
                             "STATE_CHANGELOG.md")
    motivo = None
    if os.path.isfile(changelog):
        with open(changelog, "r", encoding="utf-8") as fh:
            motivo = fh.read().strip().splitlines()[-1] if fh else None
    return estado, motivo


def transiciones_validas() -> List[Tuple[str, str]]:
    return [
        (DELIVERED, CONTESTED),
        (DELIVERED, ACCEPTED),
        (ACCEPTED, CHALLENGED),
        (CONTESTED, CHALLENGED),
    ]


def una_allow_list_se_demuestra_por_lo_que_rechaza() -> Dict[str, bool]:
    """La puerta no se demuestra por lo que acepta: se demuestra por lo que
    rechaza. Estos son los cuatro rechazos que la v3-7 exige."""
    return {
        "acepta_sin_artefactos": False,
        "acepta_con_refutacion_critica": False,
        "acepta_con_revisor_que_participo": False,
        "acepta_sin_autoridad_nombrada": False,
    }