"""Typer CLI: discovery and analysis only, never automated outreach."""

from contextlib import contextmanager
from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from prospector.config import Settings
from prospector.database.repository import Repository
from prospector.database.session import create_database_engine, create_session_factory, initialize_database, session_scope
from prospector.discovery.base import DiscoveryError
from prospector.discovery.categories import CATEGORIES
from prospector.enrichment.manual import apply_enrichment
from prospector.models import ScanStatus
from prospector.pipeline import scan_pipeline
from prospector.reports.terminal import detail, export_json, ranking
from prospector.scoring.weights import ScoringConfig
from prospector.service import run_scan


app = typer.Typer(no_args_is_help=True, help="ProspectorBot: análise de oportunidades, sem contato automatizado.")


@contextmanager
def database(settings: Settings):
    engine = create_database_engine(settings)
    try:
        initialize_database(engine)
        yield create_session_factory(engine)
    finally:
        engine.dispose()


def fail(message: str):
    typer.echo(f"Erro: {message}", err=True)
    raise typer.Exit(code=1)


def load_settings() -> Settings:
    try:
        return Settings.from_env()
    except (ValidationError, ValueError):
        fail("Configuração inválida; confira as variáveis PROSPECTOR_* em .env.example.")


def selected_scan(repo: Repository, scan_id: UUID | None):
    if scan_id is not None:
        scan = repo.get_scan(scan_id)
        if scan is None:
            fail("Scan não encontrado.")
        return scan
    scans = [scan for scan in repo.list_scans() if scan.status == ScanStatus.COMPLETED]
    if not scans:
        fail("Nenhum scan concluído. Execute 'prospector scan' primeiro.")
    return scans[0]


@app.command()
def scan(
    query: Annotated[str, typer.Option(help="Nicho ou categoria Geoapify.")],
    location: Annotated[str, typer.Option(help="Cidade/estado ou região.")],
    limit: Annotated[int, typer.Option(min=1, max=50)] = 30,
    output: Annotated[Path | None, typer.Option(help="Exportar relatório JSON.")] = None,
):
    """Encontrar negócios, analisar websites e armazenar o ranking."""
    if not query.strip() or not location.strip():
        fail("Nicho e localização não podem estar vazios.")
    settings = load_settings()
    if settings.geoapify_api_key is None:
        fail("Configure GEOAPIFY_API_KEY no ambiente. Veja README.md.")
    try:
        scoring = ScoringConfig.load(settings.scoring_config)
        with database(settings) as factory:
            with scan_pipeline(settings) as (provider, analyzer):
                typer.echo("Buscando negócios na Geoapify e analisando websites públicos...")
                result = run_scan(query, location, limit, provider, analyzer, factory, scoring,
                                  progress=lambda done, total: typer.echo(f"Avaliados: {done}/{total}"),
                                  enrich=apply_enrichment)
            with session_scope(factory) as session:
                repo = Repository(session)
                typer.echo(ranking(repo, result))
                if output:
                    export_json(repo, result, output)
                    typer.echo(f"Relatório salvo: {output}")
    except (DiscoveryError, RuntimeError) as exc:
        fail(str(exc))
    except (OSError, ValidationError, SQLAlchemyError):
        fail("Falha de configuração, arquivo ou banco; confira caminhos e permissões.")


@app.command()
def leads(
    scan_id: Annotated[UUID | None, typer.Option("--scan", help="Scan específico; padrão: último concluído.")] = None,
    output: Annotated[Path | None, typer.Option(help="Exportar relatório JSON.")] = None,
):
    """Exibir o ranking armazenado, sem consultar a internet."""
    try:
        with database(load_settings()) as factory, session_scope(factory) as session:
            repo = Repository(session)
            result = selected_scan(repo, scan_id)
            typer.echo(ranking(repo, result))
            if output:
                export_json(repo, result, output)
                typer.echo(f"Relatório salvo: {output}")
    except (OSError, SQLAlchemyError):
        fail("Falha ao acessar o banco ou gravar o relatório.")


@app.command()
def show(
    lead: Annotated[int, typer.Argument(min=1, help="Posição no ranking do comando leads.")],
    scan_id: Annotated[UUID | None, typer.Option("--scan")] = None,
):
    """Exibir evidências e oportunidades de uma posição no ranking."""
    try:
        with database(load_settings()) as factory, session_scope(factory) as session:
            repo = Repository(session)
            result = selected_scan(repo, scan_id)
            scores = repo.list_scores(result.id)
            if lead > len(scores):
                fail("Posição não encontrada neste ranking.")
            typer.echo(detail(repo, result.id, scores[lead - 1]))
    except (OSError, SQLAlchemyError):
        fail("Falha ao acessar o banco.")


@app.command()
def categories():
    """Listar os nichos traduzidos pelo primeiro provedor."""
    for name, category in sorted(CATEGORIES.items()):
        typer.echo(f"{name}: {category}")
    typer.echo("Barbearias usa a categoria de cabeleireiros; pode incluir salões de beleza.")


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Interface; mantenha local, a API não tem autenticação.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(min=1, max=65535)] = 8000,
    reload: Annotated[bool, typer.Option(help="Recarregar ao editar o código.")] = False,
):
    """Iniciar a API HTTP usada pelo frontend web."""
    import uvicorn

    uvicorn.run("prospector.api.app:create_app", factory=True, host=host, port=port, reload=reload)


def main():
    app()


if __name__ == "__main__":
    main()
