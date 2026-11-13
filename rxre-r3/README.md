# RXRE R3 — Expediente sellado: reconstrucción verificable de `filenvercmp` y `wc`

Snapshot íntegro del trabajo R3 (2026-11-12): reconstrucciones desde disasm, corpus sellados, matrices oráculo, claims expandidos. Todo verificable con el siguiente procedimiento.

## Contenido del paquete

| Ruta | Qué es |
|---|---|
| `EXPEDIENTE_R3.md` | Informe vivo del proceso R3 (§1-21) |
| `reconstruction/filenvercmp.c` | Reconstrucción escrita § manual desde desensamblado |
| `records/DIAGNOSTICO_791.md`, `disas*.txt` | Evidencia instrucción-por-instrucción del bug que rompió las 791 divergencias |
| `case*_seed*.txt` | Corpora sellados de entrada |
| `matrix_*.txt` | Oráculos correspondientes (outputs nativos) |
| `wc/SEAL_WC.txt` | Sello de la cadena wc (hitos 1-8) |
| `wc/wc_recon.c` | Reconstrucción observacional de wc |
| `release/rxre-cleanroom/` | Snapshot del paquete público final |
| `evidence/*.asm` | Desensamblado de apoyo para filenvercmp |
| `re.config`, `SEAL_WC.txt` / `SEAL.txt` | Sellos criptográficos |

## Verificación

### `filenvercmp` (4 pasos)
```sh
# 1) digest manifest
sha256sum -c records/recon_final.sha256   # verifica la reconstrucción
# 2) corpus target
gcc -std=c11 -O2 -Wall -o /tmp/verify2 reconstruction/filenvercmp.c harness/verify_recon.c
/tmp/verify2 oracle/cases_seed20261112.txt oracle/matrix_native.txt
# esperado: total=34145 mismatches=0
```

### `wc` (hito 1-L)
```sh
gcc -std=c11 -O2 -Wall -o /tmp/verify_wc wc/wc_recon.c wc/verify_wc.c
LC_ALL=C /tmp/verify_wc wc/cases_seed20261114.txt wc/matrix_native_wc.txt
# esperado: total=4899 mismatches=0
```

### `wc` flags / UTF-8 / -L
```sh
/tmp/verify_wc wc/cases_wcL_seed20261117.txt wc/matrix_native_wcL.txt C
/tmp/verify_wc wc/cases_highutf8_seed20261120.txt wc/matrix_highutf8.txt utf8
```

Notas de uso:
- El modo LC_ALL debe coincidir con el utilizado al sellar matrices (C → todos los corpus LC_ALL=C sellados; utf8 → corpuses largos altos en bytes).
- Los binarios propios son fuente; reproducí el toolchain con `gcc`.
- Los ELF no están en el paquete; son reconstruibles y no forman parte del entregable público.

## Estado real

- Primera generación sellada: 0 divergencias (34.145 × 2)
- Segunda generación sellada: 0 divergencias (4.914/4.914)
- Segunda verificación de filenvercmp contra dos compiladores: 0 divergencias
- wc LC_ALL=C y UTF-8: 0 divergencias
- Auditoría byte a byte en LC_ALL=C (todas las 256 clases): 0 divergencias
- **EXENTO** — verificación por terceros: NOT_EXECUTED; PUERTA cond. 3 PENDING_EXTERNAL_REVIEWER

## Integridad

Sellos disponibles para verificación externa. Contacto abierto para verificadores terceros.
