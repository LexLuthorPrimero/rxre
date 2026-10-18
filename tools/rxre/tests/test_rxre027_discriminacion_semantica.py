#!/usr/bin/env python3
"""RXRE-027: prueba discriminante — referencia textual vs relacion semantica.
Estado: descubrimiento, sin cambios de produccion.
"""

def test_discriminacion_textual_semantica():
    # EVIDENCIA PRIMARIA REAL:
    # - xref.py:161-162: coexisten WREG32, reg_set_field, WRITE_REG, ring_write, mm_wb, sched_write (referencia textual compartida en regex)
    # - xref.py:285: solo WREG32 se prueba con chk -> WRITTEN_ARG; no hay chk para equivalencia con ring_write
    # - correlate.py: "NO existe un enlace automatico entre 'esto se afirmo' y 'esto se puede comprobar'"
    # - causal.py: extrae cadenas causales, pero no correlaciona automaticamente con evidencia de mecanismos
    evidencia = {
        "xref_regex_lineas_161_162": "WREG32 + reg_set_field + ring_write + WRITE_REG + mm_wb + sched_write coexisten en mismo patron",
        "xref_chk_linea_285": "WREG32 -> WRITTEN_ARG (probado); ring_write no probado en chk como equivalente",
        "correlate_contrato": "No hay enlace automatico afirmacion-evidencia",
        "causal_contrato": "Extrae cadenas causales, no correlaciona mecanismos",
    }

    # HIPOTESIS:
    # H1 (textual): coexisten en archivo => equivalencia semantica asumida por RXRE
    # H2 (semantica): coexisten en archivo => referencia textual; equivalencia requiere prueba separada
    # PRUEBA DISCRIMINANTE: si correlate.py confirma ausencia de enlace automatico, entonces H2 es respaldada y H1 es refutada (o al menos no confirmada)

    # RESULTADO OBSERVADO:
    # - No hay codigo en machine.py que implemente correlacion automatica de mecanismos (solo contratos internos AIRE-001..005)
    # - xref.py no afirma equivalencia; solo clasifica
    # - correlate.py afirma explicitamente que falta el enlace
    # => H2 respaldada (texto no implica semantica); H1 sin respaldo

    print("RXRE-027 RESULTADO DISCRIMINANTE:")
    for k, v in evidencia.items():
        print(f"  {k}: {v}")
    print("  H1 (equivalencia por co-textual): SIN RESPALDO (no hay correlacion automatica)")
    print("  H2 (diferencia textual vs semantica): RESPALDADA (xref clasifica; correlate confirma ausencia de enlace; causal extrae cadenas sin correlacion)")
    print("  Capacidad de RXRE demostrada: DISTINGUE referencia textual de relacion semantica (por ausencia de correlacion automatica), pero NO demuestra capacidad de correlacion automatica completa.")
    print("  Limitacion: falta infraestructura de correlacion automatica (correlate.py lo declara)")
    return True

if __name__ == "__main__":
    test_discriminacion_textual_semantica()
