# Esqueleto de RXRE. TIERRA funcional, 7 planos en stub.

## Qué hay

| Módulo | Estado | Qué hace |
|---|---|---|
| `rxre/db.py` | **funcional** | TIERRA: claims, evidencia append-only por trigger, `row_hash` verificado al leer, `supersedes_ref`, optimistic locking |
| `rxre/state.py` | **funcional** | 6 estados, tabla de transiciones, `INVALIDATED` exige contradicción |
| `rxre/hash.py` | **funcional** | 3 capas separadas: integridad / autenticidad / validez semántica |
| `rxre/cli.py` | **funcional** | `rxre init`, `claim`, `evidence`, `status` |
| `rxre/planes/alma.py` | stub | `NotImplementedError` |
| `rxre/planes/eter.py` | stub | `NotImplementedError` |
| `rxre/planes/aire.py` | stub | `NotImplementedError` |
| `rxre/planes/mente.py` | stub | `NotImplementedError` |
| `rxre/planes/cuerpo.py` | stub | `NotImplementedError` |
| `rxre/planes/fuego.py` | stub | `NotImplementedError` |
| `rxre/planes/agua.py` | stub | `NotImplementedError` |

**Lo que falta:** los siete planos no están implementados, y ninguno puede
estarlo sin evidencia del audit A-F. Cada stub declara en su docstring qué
evidencia concreta lo desbloquearía y qué test adversarial lo tumbaría.

**Lo que no se afirma:** que esto sea RXRE. Es un esqueleto con TIERRA
funcional sobre una arquitectura que sigue marcada como HIPÓTESIS.

## El audit A-F es la puerta de entrada. Sin ACCEPTED, Etapa 1 está bloqueada.

## Correr

```bash
pip install -e .          # o: pip install -e ".[dev]"
pytest                    # 17 tests

rxre init                 # crea .rxre/rxre.db
rxre claim add "el binario expone 3 funciones" --object-hash abc --scope binary.functions
rxre claim show <id>
rxre claim transition <id> PROVEN --reason "dos producers coinciden"
rxre evidence add <id> --source-hash s --tool ghidra --version 11.0 \
  --command "analyzeHeadless" --output-hash o --provenance "{}"
rxre evidence verify <evidence_id>
rxre status
```

`rxre status` es el comando de diagnóstico: dice que TIERRA está activa y
que los siete planos son stub. Si dijera otra cosa, estaría mintiendo.