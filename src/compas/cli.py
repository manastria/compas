"""Point d'entrée CLI pour Compas."""

import logging
import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="compas",
    help="Évaluation continue des soft skills — BTS SIO SISR",
    no_args_is_help=True,
)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@app.callback()
def _callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Mode verbeux"),
) -> None:
    _setup_logging(verbose)


@app.command(name="import")
def cmd_import(
    data: str = typer.Option(
        "data", "--data", metavar="DIR",
        help="Dossier contenant les fichiers .xlsx (défaut : data/)",
    ),
    db: str = typer.Option(
        "output/compas.db", "--db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    ),
) -> None:
    """Importer les fichiers xlsx dans la base SQLite."""
    from compas.importer import import_all

    data_dir = Path(data)
    if not data_dir.exists():
        logging.getLogger(__name__).error("Répertoire introuvable : %s", data_dir)
        raise typer.Exit(1)
    if not data_dir.is_dir():
        logging.getLogger(__name__).error("N'est pas un répertoire : %s", data_dir)
        raise typer.Exit(1)

    try:
        import_all(data_dir, Path(db))
    except (ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise typer.Exit(1)


@app.command()
def dashboard(
    db: str = typer.Option(
        "output/compas.db", "--db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    ),
    out: str = typer.Option(
        "output/dashboard.html", "--out", metavar="FILE",
        help="Fichier HTML de sortie (défaut : output/dashboard.html)",
    ),
    alpha: float = typer.Option(
        0.4, "--alpha", metavar="ALPHA",
        help="Coefficient de lissage EMA, entre 0 et 1 (défaut : 0.4)",
    ),
    open_browser: bool = typer.Option(
        False, "--open",
        help="Ouvrir le dashboard dans le navigateur après génération",
    ),
) -> None:
    """Générer le dashboard HTML."""
    from compas.dashboard import generate

    out_path = Path(out)
    try:
        generate(Path(db), out_path, alpha=alpha)
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise typer.Exit(1)

    if open_browser:
        import webbrowser
        webbrowser.open(out_path.resolve().as_uri())


@app.command()
def build(
    data: str = typer.Option(
        "data", "--data", metavar="DIR",
        help="Dossier contenant les fichiers .xlsx (défaut : data/)",
    ),
    db: str = typer.Option(
        "output/compas.db", "--db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    ),
    out: str = typer.Option(
        "output/dashboard.html", "--out", metavar="FILE",
        help="Fichier HTML de sortie (défaut : output/dashboard.html)",
    ),
    alpha: float = typer.Option(
        0.4, "--alpha", metavar="ALPHA",
        help="Coefficient de lissage EMA, entre 0 et 1 (défaut : 0.4)",
    ),
    open_browser: bool = typer.Option(
        False, "--open",
        help="Ouvrir le dashboard dans le navigateur après génération",
    ),
) -> None:
    """Importer puis générer le dashboard."""
    from compas.importer import import_all
    from compas.dashboard import generate

    data_dir = Path(data)
    if not data_dir.exists():
        logging.getLogger(__name__).error("Répertoire introuvable : %s", data_dir)
        raise typer.Exit(1)
    if not data_dir.is_dir():
        logging.getLogger(__name__).error("N'est pas un répertoire : %s", data_dir)
        raise typer.Exit(1)

    try:
        import_all(data_dir, Path(db))
    except (ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise typer.Exit(1)

    out_path = Path(out)
    try:
        generate(Path(db), out_path, alpha=alpha)
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise typer.Exit(1)

    if open_browser:
        import webbrowser
        webbrowser.open(out_path.resolve().as_uri())


@app.command()
def validate(
    paths: list[str] = typer.Argument(
        ..., metavar="FILE_OR_DIR",
        help="Fichier(s) .xlsx ou dossier(s) à valider",
    ),
    strict: bool = typer.Option(
        False, "--strict",
        help="Considérer les avertissements comme des erreurs (code retour 1)",
    ),
) -> None:
    """Vérifier la conformité de fichiers xlsx."""
    from compas.validator import Severity, validate_xlsx

    targets: list[Path] = []
    for path_str in paths:
        p = Path(path_str)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.xlsx")))
        elif p.exists():
            targets.append(p)
        else:
            logging.getLogger(__name__).error("Fichier ou dossier introuvable : %s", p)
            raise typer.Exit(1)

    if not targets:
        logging.getLogger(__name__).warning("Aucun fichier xlsx trouvé.")
        return

    total_errors = 0
    total_warnings = 0

    for xlsx_path in targets:
        issues = validate_xlsx(xlsx_path)
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        total_errors += errors
        total_warnings += warnings

        print(f"\nValidation : {xlsx_path}")
        if not issues:
            print("  OK — aucun problème détecté")
        else:
            for issue in issues:
                print(f"  {issue}")
            parts = []
            if errors:
                parts.append(f"{errors} erreur(s)")
            if warnings:
                parts.append(f"{warnings} avertissement(s)")
            print(f"  → {', '.join(parts)}")

    if len(targets) > 1:
        parts = []
        if total_errors:
            parts.append(f"{total_errors} erreur(s)")
        if total_warnings:
            parts.append(f"{total_warnings} avertissement(s)")
        summary = ", ".join(parts) if parts else "aucun problème"
        print(f"\nRésumé : {len(targets)} fichier(s) — {summary}")

    if total_errors > 0:
        raise typer.Exit(1)
    if strict and total_warnings > 0:
        raise typer.Exit(1)


@app.command()
def explain(
    name: str = typer.Argument(
        ..., metavar="NOM",
        help="Nom ou fragment de nom de l'étudiant (insensible à la casse)",
    ),
    db: str = typer.Option(
        "output/compas.db", "--db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    ),
    out: str = typer.Option(
        "", "--out", metavar="FILE",
        help="Fichier markdown de sortie (défaut : output/explain_<nom>.md)",
    ),
    alpha: float = typer.Option(
        0.4, "--alpha", metavar="ALPHA",
        help="Coefficient de lissage EMA, entre 0 et 1 (défaut : 0.4)",
    ),
) -> None:
    """Générer un rapport markdown d'explication EMA pour un étudiant."""
    from compas.explain import generate_explain

    db_path = Path(db)
    if out:
        out_path = Path(out)
    else:
        slug = name.lower().replace(" ", "_")
        out_path = Path("output") / f"explain_{slug}.md"

    try:
        nom = generate_explain(db_path, name, out_path, alpha=alpha)
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        raise typer.Exit(1)

    logging.getLogger(__name__).info("Rapport généré pour %s : %s", nom, out_path)


def main() -> None:
    """Point d'entrée principal du CLI Compas."""
    app()


if __name__ == "__main__":
    main()
