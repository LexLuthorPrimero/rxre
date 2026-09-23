# REGISTRO-DE-MOVIMIENTOS.md — Trazabilidad de la reorganización documental

> Cada movimiento de la reorganización se registra aquí con: `origen → destino → hash → fecha → motivo`.
> Los hashes ya están verificados en `REORGANIZACION-MANIFEST.sha256` (pre-movimiento). Tras cada grupo se verifica integridad por hash.

| # | Origen (ruta) | Destino (ruta) | Fecha | Hash verificado | Motivo |
|---|---|---|---|---|---|
| — | *(pendiente de autorización final de movimientos)* | | | | |

## Verificación de integridad

- [ ] Post-movimiento: comparar hashes destino vs `REORGANIZACION-MANIFEST.sha256`.
- [ ] Conflicto de nombres: ninguno detectado (preservación de nombres y estructura interna por carpeta).
- [ ] Operaciones destructivas: CERO (no se borra, no se sobrescribe, no se modifica contenido).