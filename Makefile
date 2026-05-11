# Makefile — raccourcis pour les commandes Compas courantes

.PHONY: help install activate build import dashboard validate

help:
	@echo "Commandes disponibles :"
	@echo "  make install    Installer les dépendances"
	@echo "  make activate   Afficher la commande d'activation du venv"
	@echo "  make build      Importer + générer le dashboard"
	@echo "  make import     Importer les fichiers xlsx"
	@echo "  make dashboard  Générer le dashboard HTML"
	@echo "  make validate   Valider les fichiers xlsx"

install:
	poetry install

activate:
	@echo "Exécuter : source .venv/bin/activate"
	@echo "Ou sous zsh/bash : eval \"\$$(poetry env activate)\""

build:
	poetry run compas build --open

import:
	poetry run compas import

dashboard:
	poetry run compas dashboard --open

validate:
	poetry run compas validate data/
