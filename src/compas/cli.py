"""Point d'entrée CLI pour Compas."""

import argparse
import logging
import sys
from pathlib import Path


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _cmd_import(args: argparse.Namespace) -> int:
    from compas.importer import import_all

    data_dir = Path(args.data)
    if not data_dir.exists():
        logging.getLogger(__name__).error("Répertoire introuvable : %s", data_dir)
        return 1
    if not data_dir.is_dir():
        logging.getLogger(__name__).error("N'est pas un répertoire : %s", data_dir)
        return 1

    try:
        import_all(data_dir, Path(args.db))
    except (ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    return 0


def _cmd_dashboard(args: argparse.Namespace) -> int:
    from compas.dashboard import generate

    out = Path(args.out)
    try:
        generate(Path(args.db), out, alpha=args.alpha)
    except (FileNotFoundError, ValueError, OSError) as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1

    if getattr(args, "open_browser", False):
        import webbrowser
        webbrowser.open(out.resolve().as_uri())

    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    rc = _cmd_import(args)
    if rc != 0:
        return rc
    return _cmd_dashboard(args)


def main() -> None:
    """Point d'entrée principal du CLI Compas."""
    parser = argparse.ArgumentParser(
        prog="compas",
        description="Évaluation continue des soft skills — BTS SIO SISR",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Mode verbeux")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── Sous-commande : import ──────────────────────────────────────────────
    p_import = sub.add_parser("import", help="Importer les fichiers xlsx dans la base SQLite")
    p_import.add_argument(
        "--data", default="data", metavar="DIR",
        help="Dossier contenant les fichiers .xlsx (défaut : data/)",
    )
    p_import.add_argument(
        "--db", default="output/compas.db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    )
    p_import.set_defaults(func=_cmd_import)

    # ── Sous-commande : dashboard ───────────────────────────────────────────
    p_dash = sub.add_parser("dashboard", help="Générer le dashboard HTML")
    p_dash.add_argument(
        "--db", default="output/compas.db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    )
    p_dash.add_argument(
        "--out", default="output/dashboard.html", metavar="FILE",
        help="Fichier HTML de sortie (défaut : output/dashboard.html)",
    )
    p_dash.add_argument(
        "--alpha", type=float, default=0.4, metavar="ALPHA",
        help="Coefficient de lissage EMA, entre 0 et 1 (défaut : 0.4)",
    )
    p_dash.add_argument(
        "--open", dest="open_browser", action="store_true",
        help="Ouvrir le dashboard dans le navigateur après génération",
    )
    p_dash.set_defaults(func=_cmd_dashboard)

    # ── Sous-commande : build (import + dashboard) ──────────────────────────
    p_build = sub.add_parser("build", help="Importer puis générer le dashboard")
    p_build.add_argument(
        "--data", default="data", metavar="DIR",
        help="Dossier contenant les fichiers .xlsx (défaut : data/)",
    )
    p_build.add_argument(
        "--db", default="output/compas.db", metavar="FILE",
        help="Chemin de la base SQLite (défaut : output/compas.db)",
    )
    p_build.add_argument(
        "--out", default="output/dashboard.html", metavar="FILE",
        help="Fichier HTML de sortie (défaut : output/dashboard.html)",
    )
    p_build.add_argument(
        "--alpha", type=float, default=0.4, metavar="ALPHA",
        help="Coefficient de lissage EMA, entre 0 et 1 (défaut : 0.4)",
    )
    p_build.add_argument(
        "--open", dest="open_browser", action="store_true",
        help="Ouvrir le dashboard dans le navigateur après génération",
    )
    p_build.set_defaults(func=_cmd_build)

    args = parser.parse_args()
    _setup_logging(args.verbose)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
