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


def _cmd_validate(args: argparse.Namespace) -> int:
    from compas.validator import Severity, validate_xlsx

    targets: list[Path] = []
    for path_str in args.paths:
        p = Path(path_str)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.xlsx")))
        elif p.exists():
            targets.append(p)
        else:
            logging.getLogger(__name__).error("Fichier ou dossier introuvable : %s", p)
            return 1

    if not targets:
        logging.getLogger(__name__).warning("Aucun fichier xlsx trouvé.")
        return 0

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
        return 1
    if getattr(args, "strict", False) and total_warnings > 0:
        return 1
    return 0


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

    # ── Sous-commande : validate ────────────────────────────────────────────
    p_val = sub.add_parser("validate", help="Vérifier la conformité de fichiers xlsx")
    p_val.add_argument(
        "paths",
        nargs="+",
        metavar="FILE_OR_DIR",
        help="Fichier(s) .xlsx ou dossier(s) à valider",
    )
    p_val.add_argument(
        "--strict",
        action="store_true",
        help="Considérer les avertissements comme des erreurs (code retour 1)",
    )
    p_val.set_defaults(func=_cmd_validate)

    args = parser.parse_args()
    _setup_logging(args.verbose)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
