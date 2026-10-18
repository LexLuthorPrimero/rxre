"""CLI de RXRE. Typer.

Superficie:

    rxre init
    rxre claim add / show / transition
    rxre evidence add / verify
    rxre status

`rxre status` es el comando que importa: es el que dice, sin ambiguedad, que
siete planos no existen. Si el status dijera "7 planos OK", el esqueleto
estaria mintiendo sobre si mismo.

    el estado de un comando de diagnostico tiene que ser verdad aunque incomode
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, db as _db, state as _state
from .planes import PLANES

app = typer.Typer(add_completion=False,
                  help="Esqueleto de RXRE. TIERRA funcional, 7 planos stub.")
claim_app = typer.Typer(help="Claims epistemicos.")
evidence_app = typer.Typer(help="Evidencia (append-only).")
app.add_typer(claim_app, name="claim")
app.add_typer(evidence_app, name="evidence")

consola = Console()

# El estado de la puerta global. No se deduce de nada: es lo que el diagrama
# declara, y lo que el audit A-F tiene que mover.
AUDIT_ESTADO = "ESPERANDO ARTEFACTOS"
ETAPA_1 = "BLOQUEADA"


@app.command()
def init() -> None:
    """Crea `.rxre/rxre.db`. Idempotente."""
    ruta = _db.init()
    consola.print(f"[green]Base creada:[/green] {ruta}")
    consola.print("[dim]TIERRA activa. 7 planos en stub.[/dim]")


@app.command()
def status() -> None:
    """El estado real del sistema, sin adornos."""
    # El detalle de TIERRA se resuelve ANTES de construir la tabla. La API
    # interna de `rich` para reescribir una celda despues (`row.cells`) no es
    # publica; montar la tabla con el texto ya resuelto es lo unico que no
    # depende de como rich decida representar sus filas.
    try:
        conn = _db.connect()
        c, e = _db.counts(conn)
        conn.close()
        tierra = f"grafo de evidencia ({c} claims, {e} evidence)"
    except Exception:                                        # noqa: BLE001
        tierra = "grafo de evidencia (base no inicializada: `rxre init`)"

    t = Table(title=f"RXRE v{__version__}", title_style="bold")
    t.add_column("Plano", style="bold")
    t.add_column("Estado")
    t.add_column("Detalle")

    t.add_row("TIERRA", "[green]● activa[/green]", tierra)
    for nombre in PLANES:
        t.add_row(nombre, "[yellow]○ stub[/yellow]", "NotImplementedError")

    consola.print()
    consola.print(t)
    consola.print()
    consola.print(f"  Audit A-F:  [yellow]{AUDIT_ESTADO}[/yellow]")
    consola.print(f"  Etapa 1:    [red]{ETAPA_1}[/red]")
    consola.print()


# --- claims ----------------------------------------------------------------
@claim_app.command("add")
def claim_add(
    statement: str = typer.Argument(..., help="La afirmacion."),
    object_hash: str = typer.Option(..., "--object-hash"),
    scope: str = typer.Option(..., "--scope"),
    state: str = typer.Option("NOT_DETERMINED", "--state"),
) -> None:
    """Crea un claim."""
    conn = _db.connect()
    try:
        cid = _db.create_claim(conn, statement, object_hash, scope, state)
    finally:
        conn.close()
    consola.print(f"[green]{cid}[/green]")


@claim_app.command("show")
def claim_show(claim_id: str = typer.Argument(...)) -> None:
    """Muestra un claim y su evidencia."""
    conn = _db.connect()
    try:
        claim = _db.get_claim(conn, claim_id)
        if claim is None:
            typer.secho(f"claim inexistente: {claim_id}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        ev = _db.list_evidence(conn, claim_id)
    finally:
        conn.close()

    t = Table(show_header=False)
    t.add_column("campo", style="bold")
    t.add_column("valor")
    for k in ("id", "statement", "object_hash", "scope", "epistemic_state",
              "version", "created_at", "updated_at"):
        t.add_row(k, str(claim[k]))
    consola.print(t)
    consola.print(f"\n[bold]evidencia ({len(ev)})[/bold]")
    for e in ev:
        marca = "~" if e["supersedes_ref"] else "+"
        consola.print(f"  {marca} [cyan]{e['id']}[/cyan] "
                      f"{e['type']} {e['tool_version']}")
        if e["supersedes_ref"]:
            consola.print(f"      [dim]supersede {e['supersedes_ref']}[/dim]")


@claim_app.command("transition")
def claim_transition(
    claim_id: str = typer.Argument(...),
    new_state: str = typer.Argument(...),
    reason: str = typer.Option("", "--reason"),
) -> None:
    """Cambia el estado de un claim. Valida la transicion."""
    try:
        res = _state.transition(claim_id, new_state, reason)
    except _state.InvalidTransitionError as exc:
        typer.secho(f"transicion invalida: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except _state.MissingContradictionError as exc:
        typer.secho(f"INVALIDATED requiere contradiccion: {exc}",
                    fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except _db.StaleVersionError as exc:
        typer.secho(f"carrera perdida: {exc}", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    consola.print(f"[green]{res['id']}[/green]  "
                  f"{res['epistemic_state']}  [dim]v{res['version']}[/dim]")


# --- evidence --------------------------------------------------------------
@evidence_app.command("add")
def evidence_add(
    claim_id: str = typer.Argument(...),
    type: str = typer.Option("source", "--type"),
    source_hash: str = typer.Option(..., "--source-hash"),
    tool: str = typer.Option("", "--tool",
                             help="Nombre del producer, p.ej. ghidra."),
    tool_version: str = typer.Option("", "--version",
                                     help="Version del producer, p.ej. 11.0."),
    command: str = typer.Option(..., "--command"),
    output_hash: str = typer.Option(..., "--output-hash"),
    provenance: str = typer.Option(..., "--provenance"),
    supersedes: Optional[str] = typer.Option(None, "--supersedes"),
) -> None:
    """Anade evidencia. Append-only: nunca modifica una fila anterior.

    `--tool ghidra --version 11.0` se guardan juntos en la columna
    `tool_version` como 'ghidra 11.0'. El SQL declara una sola columna y el
    CLI expone las dos mitades porque son cosas que el usuario dice por
    separado; separarlas en el esquema obligaria a duplicar el campo y a
    decidir despues cual de los dos manda.
    """
    if not tool and not tool_version:
        typer.secho("hace falta --tool y/o --version", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    version_completa = " ".join(p for p in (tool.strip(), tool_version.strip())
                                if p)

    conn = _db.connect()
    try:
        eid = _db.add_evidence(
            conn, claim_id, type, source_hash, version_completa, command,
            output_hash, provenance, supersedes)
    finally:
        conn.close()
    consola.print(f"[green]{eid}[/green]")


@evidence_app.command("verify")
def evidence_verify(evidence_id: str = typer.Argument(...)) -> None:
    """Relee la evidencia y verifica su `row_hash`."""
    conn = _db.connect()
    try:
        fila = _db.get_evidence(conn, evidence_id, verify=True)
    except _db.IntegrityError as exc:
        typer.secho(f"INTEGRIDAD FALLIDA: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2)
    except KeyError:
        typer.secho(f"evidencia inexistente: {evidence_id}",
                    fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()
    t = Table(show_header=False)
    t.add_column("campo", style="bold")
    t.add_column("valor")
    for k in ("id", "claim_ref", "type", "source_hash", "tool_version",
              "command", "output_hash", "supersedes_ref", "created_at",
              "row_hash"):
        t.add_row(k, str(fila[k]))
    consola.print(t)
    consola.print("\n[green]row_hash verificado[/green]")


@app.command()
def main() -> None:      # pragma: no cover
    app()


if __name__ == "__main__":      # pragma: no cover
    app()