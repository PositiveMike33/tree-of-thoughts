#!/bin/bash

# S.O.C. Backup Utility (v1.5)
# Repository: PositiveMike33/tree-of-thoughts

echo "🚀 Initialisation de la sauvegarde de souveraineté..."

# Initialisation Git si nécessaire
if [ ! -d ".git" ]; then
    git init
    git remote add origin https://github.com/PositiveMike33/tree-of-thoughts.git
    git branch -M main
fi

# Stage des changements
git add .

# Commit
echo "💾 Création du commit..."
git commit -m "🚀 S.O.C. v1.5 Deployment - Souveraineté Multicanale & Protocole BOOT-UP"

# Push
echo "⬆️ Envoi vers GitHub (PositiveMike33/tree-of-thoughts)..."
git push -u origin main

echo "✅ Sauvegarde terminée. Votre système est sécurisé sur le Cloud."
