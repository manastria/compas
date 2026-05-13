#!/usr/bin/env bash
set -euo pipefail

# Configuration
SOURCE_BRANCH="dev"
TARGET_BRANCH="master"

# Chemins de développement exclus de la publication
# (.github est conservé pour la CI/CD GitHub Actions)
EXCLUDE_PATHS=(".claude" ".vscode" "scripts" "AGENTS.md" "CLAUDE.md" "PROGRESS.MD")
STOP_BEFORE_COMMIT=false
MSG=""

usage() {
    cat <<EOF
Usage: $0 [options] [message]

Options:
  -x, --exclude PATH        Exclure un fichier ou un répertoire de la publication.
                            Peut être répété.
      --stop-before-commit  Quitter avant le commit pour inspecter le working directory.
  -h, --help                Afficher cette aide.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -x|--exclude)
            if [ "$#" -lt 2 ]; then
                echo "❌ Option $1 : chemin manquant"
                exit 1
            fi
            EXCLUDE_PATHS+=("$2")
            shift 2
            ;;
        --stop-before-commit)
            STOP_BEFORE_COMMIT=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            if [ "$#" -gt 0 ]; then
                MSG="$*"
            fi
            break
            ;;
        -*)
            echo "❌ Option inconnue : $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "$MSG" ]; then
                MSG="$1"
            else
                MSG="$MSG $1"
            fi
            shift
            ;;
    esac
done

# Vérifications préalables
CURRENT=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT" != "$SOURCE_BRANCH" ]; then
    echo "❌ Tu dois être sur la branche $SOURCE_BRANCH (actuellement sur $CURRENT)"
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Working tree pas propre. Commit ou stash d'abord."
    exit 1
fi

# Message de commit
if [ "$STOP_BEFORE_COMMIT" != true ] && [ -z "$MSG" ]; then
    read -rp "📦 Message de publication : " MSG
fi

# Capture le SHA source avant de changer de branche
SOURCE_SHA=$(git rev-parse --short HEAD)

# Synchronise avec GitHub
echo "⬇️  Pull $SOURCE_BRANCH..."
git pull origin "$SOURCE_BRANCH" --rebase

# Publication
echo "🚀 Publication sur $TARGET_BRANCH..."
git checkout "$TARGET_BRANCH"
git pull origin "$TARGET_BRANCH" 2>/dev/null || true
if [ -n "$(git ls-files)" ]; then
    git rm -rf . --quiet
fi
git clean -fd --quiet
git checkout "$SOURCE_BRANCH" -- ":/"

# Suppression des chemins de développement
for path in "${EXCLUDE_PATHS[@]}"; do
    if [ -e "$path" ]; then
        git rm -rf --ignore-unmatch "$path" --quiet
        git clean -fdx --quiet -- "$path"
        echo "🗑️  Exclu : $path"
    fi
done

if [ "$STOP_BEFORE_COMMIT" = true ]; then
    echo "⏸️  Arrêt avant commit. Tu peux maintenant inspecter le working directory."
    echo
    echo "Pour abandonner cette publication et revenir à $SOURCE_BRANCH :"
    echo "  git reset --hard HEAD"
    echo "  git clean -fd"
    echo "  git checkout $SOURCE_BRANCH"
    exit 0
fi

git commit -m "📦 Publish: $MSG

Source: $SOURCE_BRANCH@$SOURCE_SHA"
git push origin "$TARGET_BRANCH"

# Retour
git checkout "$SOURCE_BRANCH"
echo "✅ Publié ($SOURCE_BRANCH@$SOURCE_SHA → $TARGET_BRANCH)"
