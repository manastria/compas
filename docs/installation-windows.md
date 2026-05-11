# Installation de Compas sur Windows 11

Ce guide couvre l'installation complète de l'environnement nécessaire à l'exécution de **Compas** sur Windows 11 : `pyenv-win` pour gérer les versions Python, `Poetry` pour les dépendances, puis le projet lui-même.

---

## Prérequis

- Windows 11 (x64)
- PowerShell 5.1 ou supérieur (inclus dans Windows 11)
- Droits d'administration sur la machine
- Connexion internet

> **Convention :** toutes les commandes suivantes sont à exécuter dans **PowerShell** (pas dans l'invite de commandes `cmd`). Ouvrir PowerShell via le menu Démarrer ou avec le raccourci `Win + X → Terminal Windows`.

---

## 1. Autoriser l'exécution de scripts PowerShell

Par défaut, Windows bloque l'exécution des scripts PowerShell. Cette restriction doit être levée pour l'utilisateur courant :

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Confirmer avec `O` si une demande de confirmation apparaît.

---

## 2. Installer pyenv-win

[`pyenv-win`](https://github.com/pyenv-win/pyenv-win) est le portage Windows de `pyenv`. Il permet d'installer et de basculer entre plusieurs versions de Python sans toucher à l'installation système.

### Installation via PowerShell

```powershell
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" `
  -OutFile "$env:TEMP\install-pyenv-win.ps1"

& "$env:TEMP\install-pyenv-win.ps1"
```

Le script installe `pyenv-win` dans `%USERPROFILE%\.pyenv` et ajoute automatiquement les entrées nécessaires dans les variables d'environnement utilisateur (`PATH`, `PYENV`, `PYENV_HOME`).

### Prendre en compte les variables d'environnement

**Fermer puis rouvrir PowerShell** pour que les modifications du `PATH` soient effectives.

### Vérifier l'installation

```powershell
pyenv --version
```

La sortie doit afficher quelque chose comme `pyenv 3.1.1`.

---

## 3. Installer la version Python requise par le projet

Le fichier `.python-version` à la racine du dépôt indique la version Python attendue (par exemple `3.12.9`). `pyenv` lit ce fichier automatiquement lorsqu'on se trouve dans le répertoire du projet.

### Mettre à jour la liste des versions disponibles

```powershell
pyenv update
```

### Installer la version déclarée

Se placer dans le répertoire du projet, puis laisser `pyenv` lire `.python-version` :

```powershell
cd C:\chemin\vers\compas
pyenv install
```

`pyenv` détecte la version dans `.python-version` et la télécharge. L'opération peut prendre quelques minutes.

> **Remarque :** si la commande `pyenv install` sans argument n'est pas supportée par la version installée de `pyenv-win`, lire la version cible manuellement et la passer en argument :
> ```powershell
> pyenv install (Get-Content .python-version).Trim()
> ```

### Vérifier l'activation locale

```powershell
python --version
```

Le numéro affiché doit correspondre exactement à celui de `.python-version`.

---

## 4. Installer Poetry

[`Poetry`](https://python-poetry.org/) gère les dépendances et l'environnement virtuel du projet. L'installation se fait via son installateur officiel, indépendamment de la version Python du projet.

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

L'installateur place Poetry dans `%APPDATA%\Python\Scripts` et affiche le chemin exact à la fin de l'installation.

### Ajouter Poetry au PATH

Si `poetry` n'est pas reconnu après l'installation, ajouter son répertoire au `PATH` utilisateur :

```powershell
$poetryBin = "$env:APPDATA\Python\Scripts"
[Environment]::SetEnvironmentVariable(
    "PATH",
    "$env:PATH;$poetryBin",
    "User"
)
```

**Fermer puis rouvrir PowerShell**, puis vérifier :

```powershell
poetry --version
```

### Configurer Poetry pour créer le venv dans le projet

Cette option place l'environnement virtuel dans le sous-dossier `.venv/` du projet, ce qui facilite la détection par les IDE (VS Code, PyCharm) :

```powershell
poetry config virtualenvs.in-project true
```

---

## 5. Installer les dépendances de Compas

Se placer dans le répertoire du projet si ce n'est pas déjà fait :

```powershell
cd C:\chemin\vers\compas
```

Installer les dépendances déclarées dans `pyproject.toml` :

```powershell
poetry install
```

Poetry crée l'environnement virtuel `.venv\`, résout les dépendances et les installe. L'opération ne nécessite pas de droits d'administration.

### Vérifier que Compas est opérationnel

```powershell
poetry run compas --help
```

L'aide de la CLI doit s'afficher sans erreur.

---

## 6. (Optionnel) Activer l'environnement virtuel dans le terminal

Pour éviter de préfixer chaque commande par `poetry run`, activer le venv dans la session PowerShell courante :

```powershell
.\.venv\Scripts\Activate.ps1
```

L'invite de commandes indique alors `(.venv)` en préfixe. Dans ce contexte, `compas` est directement disponible :

```powershell
compas build
compas validate data\
```

Pour désactiver :

```powershell
deactivate
```

---

## Récapitulatif des commandes

```powershell
# 1. Autoriser les scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 2. Installer pyenv-win
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" `
  -OutFile "$env:TEMP\install-pyenv-win.ps1"
& "$env:TEMP\install-pyenv-win.ps1"
# → Fermer et rouvrir PowerShell

# 3. Installer Python (version lue depuis .python-version)
cd C:\chemin\vers\compas
pyenv update
pyenv install

# 4. Installer Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
poetry config virtualenvs.in-project true
# → Fermer et rouvrir PowerShell si nécessaire

# 5. Installer les dépendances
poetry install

# 6. Vérifier
poetry run compas --help
```

---

## Dépannage courant

| Symptôme | Cause probable | Solution |
|----------|---------------|----------|
| `pyenv : Le terme 'pyenv' n'est pas reconnu` | PATH non rechargé | Fermer et rouvrir PowerShell |
| `python` pointe sur la mauvaise version | pyenv non prioritaire dans le PATH | Vérifier que `%USERPROFILE%\.pyenv\pyenv-win\bin` précède les autres entrées Python dans le PATH utilisateur |
| `poetry : Le terme 'poetry' n'est pas reconnu` | `%APPDATA%\Python\Scripts` absent du PATH | Ajouter manuellement (voir section 4) |
| `ModuleNotFoundError` à l'exécution | Venv non activé ou `poetry install` non exécuté | Relancer `poetry install` depuis le répertoire du projet |
| Erreur `SSL` lors du téléchargement | Proxy d'entreprise | Configurer `HTTPS_PROXY` ou demander une exception réseau |
