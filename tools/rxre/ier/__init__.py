"""RXRE · IER — Ingenieria Inversa Evolutiva y Reparativa.

Paquete nuevo: trabajo aparte del nucleo heredado (core/, backends/).
Nada de aqui promociona capacidades ni publica nada por si mismo;
toda promocion a PROMOTED es dictado del propietario.
"""
from . import mission, capability, investigate_f02, cleanup_guard, territory, defect  # noqa: F401
from . import binexpr, cfg, differential, region_analyzer  # noqa: F401
from . import region_analyzer_ail  # noqa: F401  experimental adapter (no angr dependency)
from . import transformer_witness  # noqa: F401  testigo independiente de transformación (M10.8)
from . import witness_cases  # noqa: F401  casos del testigo desde evidencia sellada
from . import independent_verifier  # noqa: F401  verificador independiente del testigo
from . import evidence_contract  # noqa: F401  contrato K=(S,C,T,O) (M10.10)
from . import call_summary_admission  # noqa: F401  admisión de resúmenes interprocedimentales v2 (M11.3)
from . import rxre_angr_adapter  # noqa: F401  adapter RXRE↔angr (M11.4)
__all__ = ["mission", "capability", "investigate_f02", "cleanup_guard", "territory", "defect",
           "binexpr", "cfg", "differential", "region_analyzer", "transformer_witness",
           "witness_cases", "independent_verifier", "call_summary_admission", "rxre_angr_adapter"]
__version__ = "IER-0.6.0"
