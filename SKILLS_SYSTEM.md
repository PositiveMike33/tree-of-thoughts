# Tree of Thoughts Skills System

## Vue d'ensemble

Le système de Skills est une architecture complète pour exposer les compétences Tree of Thoughts (ToT) comme des commandes CLI intégrées à Claude Code avec **optimisation en temps réel** et **suivi de l'évolution utilisateur**.

## Architecture

### Composants Principaux

```
SkillsManagementSystem (Central)
├── UserProfile (Profil utilisateur + évolution)
├── SkillMetrics (Métriques temps réel)
├── SkillConfigs (Configurations dynamiques)
├── OptimizationEngine (Optimisations auto)
└── RealtimeDataHandler (Queue temps réel)
        ↓
SkillWrapper (Wrapper d'exécution)
└── {CodeReviewerCLI, DecisionMakerCLI, ...}
```

### Fichiers Créés

| Fichier | Rôle |
|---------|------|
| `skills_manager.py` | Système central de gestion |
| `skill_wrapper.py` | Wrapper d'exécution + optimisation |
| `cli_handlers.py` | Handlers CLI pour chaque skill |

## Fonctionnalités

### 1. **Exécution de Skills**

Chaque compétence est exposée comme une commande autonome :

- **Code Reviewer** - Analyse de qualité et sécurité du code
- **Decision Maker** - Évaluation d'options décisionnelles
- **Research Analyst** - Recherche avec sources vérifiées
- **Problem Solver** - Exploration de solutions multiples
- **Thesis Validator** - Validation académique de thèses
- **Expert Simulator** - Simulation de raisonnement expert

### 2. **Optimisation en Temps Réel**

Le système analyse continuellement :

```
Exécutions → Queue Temps Réel → Analyse Performance → Recommandations
                                        ↓
                              Auto-Optimisation (sûre)
```

**Types d'optimisations :**
- Ajustement dynamique de `max_steps` et `num_thoughts`
- Adaptation de `confidence_threshold`
- Sélection d'algorithme optimal
- Détection d'anomalies

### 3. **Suivi Utilisateur**

Le profil utilisateur suit :

```python
UserProfile:
├── skill_preferences (Préférences par skill)
├── skill_performance (Historique des performances)
├── algorithm_preferences (Algorithmes préférés)
├── confidence_trends (Tendances de confiance)
├── execution_history (Historique complet)
└── optimization_metrics (Métriques d'optimisation)
```

## Utilisation

### 1. Installation et Intégration

```bash
# Vérifier que les fichiers sont en place
ls -la tree_of_thoughts/vault/skills/skills_manager.py
ls -la tree_of_thoughts/vault/skills/skill_wrapper.py
ls -la tree_of_thoughts/vault/skills/cli_handlers.py
```

### 2. Utilisation Programmatique

```python
from tree_of_thoughts.vault.skills import SkillWrapper, SkillType

# Initialiser le système
wrapper = SkillWrapper(user_id="mon_utilisateur")

# Exécuter une compétence
result = wrapper.execute_skill(
    skill_type=SkillType.CODE_REVIEW,
    prompt="Analysez ce code pour la sécurité",
    context={"file_path": "app.py"},
    apply_optimizations=True  # Active optimisation temps réel
)

# Afficher les résultats
print(result["result"]["output"])
print(f"Confiance: {result['result']['confidence_score']:.1%}")

# Obtenir les recommandations d'optimisation
for rec in result["recommendations"]:
    print(f"💡 {rec['suggestion']}")
```

### 3. Utilisation via CLI

```bash
# Exécuter Code Reviewer
python -m tree_of_thoughts.vault.skills.cli_handlers code_review "Analysez ce code" file_path=app.py

# Obtenir le statut d'une compétence
python -m tree_of_thoughts.vault.skills.cli_handlers status code_review

# Afficher les optimisations suggérées
python -m tree_of_thoughts.vault.skills.cli_handlers optimize code_review

# Gérer la configuration
python -m tree_of_thoughts.vault.skills.cli_handlers config code_review max_steps 7
```

## Optimisations Automatiques

### Recommandations Intelligentes

Le système génère automatiquement des recommandations basées sur :

| Condition | Recommandation | Action |
|-----------|----------------|--------|
| Confiance < 60% | Augmenter profondeur | `max_steps +2` |
| Temps > 80% timeout | Réduire profondeur | `num_thoughts -1` |
| Taux review > 30% | Baisser seuil confiance | `confidence_threshold -0.1` |

### Application d'Optimisations

```python
# Obtenir les recommandations
optimizations = wrapper.get_optimization_status()

# Appliquer une recommandation spécifique
success = wrapper.apply_recommendations(apply_all=False)

# Appliquer toutes les recommandations
success = wrapper.apply_recommendations(apply_all=True)
```

## Métriques et Monitoring

### Accéder aux Métriques

```python
# Métriques d'une compétence spécifique
metrics = wrapper.skills_manager.get_skill_metrics(SkillType.CODE_REVIEW)

print(f"Exécutions: {metrics.total_executions}")
print(f"Confiance moyenne: {metrics.avg_confidence:.1%}")
print(f"Temps d'exécution: {metrics.avg_execution_time:.2f}s")
print(f"Tendance: {metrics.trending_confidence:.1%}")
print(f"Taux de review: {metrics.human_review_rate:.1%}")

# Toutes les métriques
all_metrics = wrapper.get_all_metrics()
```

### Dashboard

```python
# Obtenir le statut de tous les skills
status = wrapper.get_skill_status()

for skill_name, info in status.items():
    print(f"\n{info['name']}:")
    print(f"  Algorithm: {info['algorithm']}")
    if info['metrics']:
        print(f"  Confiance: {info['metrics']['avg_confidence']:.1%}")
        print(f"  Exécutions: {info['metrics']['total_executions']}")
```

## Persistance

### Sauvegarde et Restauration

```python
# Exporter l'état du système
state = wrapper.export_state()
with open("skills_state.json", "w") as f:
    json.dump(state, f)

# Importer un état sauvegardé
with open("skills_state.json", "r") as f:
    state = json.load(f)
wrapper.import_state(state)

# Sauvegarder le profil utilisateur
wrapper.save_state()
```

### Structure de Persistance

```
~/.tot/skills/
├── {user_id}_profile.json
├── metrics/
│   ├── code_review_metrics.json
│   ├── decision_metrics.json
│   └── ...
└── configs/
    └── {skill_type}_config.json
```

## Exemple Complet

```python
from tree_of_thoughts.vault.skills import SkillWrapper, SkillType

def analyze_code_with_optimization():
    """Exemple complet d'utilisation du système."""

    # 1. Initialiser le système
    wrapper = SkillWrapper(user_id="alice")

    # 2. Afficher le statut des skills
    print("=== Statut des Skills ===")
    print(wrapper.cli_list_skills())

    # 3. Exécuter une analyse de code
    print("\n=== Analyse de Code ===")
    code = """
    def process_data(data):
        import pickle
        return pickle.loads(data)  # Sécurité?
    """

    result = wrapper.execute_skill(
        skill_type=SkillType.CODE_REVIEW,
        prompt=f"Analysez ce code:\n{code}",
        context={"severity": "high"},
        apply_optimizations=True
    )

    # 4. Afficher les résultats
    if result["success"]:
        print(result["result"]["output"])
        print(f"\n✓ Confiance: {result['result']['confidence_score']:.1%}")

        # 5. Appliquer les recommandations
        if result["recommendations"]:
            print("\n=== Optimisations Suggérées ===")
            for rec in result["recommendations"]:
                print(f"• {rec['suggestion']}")

    # 6. Afficher les métriques
    print("\n=== Métriques ===")
    metrics = wrapper.skills_manager.get_skill_metrics(SkillType.CODE_REVIEW)
    print(f"Exécutions: {metrics.total_executions}")
    print(f"Confiance moyenne: {metrics.avg_confidence:.1%}")
    print(f"Temps moyen: {metrics.avg_execution_time:.2f}s")

    # 7. Sauvegarder l'état
    wrapper.save_state()
    print("\n✓ État sauvegardé")

if __name__ == "__main__":
    analyze_code_with_optimization()
```

## Configuration Avancée

### Changer d'Algorithme

```python
from tree_of_thoughts.vault.skills import AlgorithmType

# Pour Code Reviewer, passer de BFS à A*
wrapper.switch_algorithm(SkillType.CODE_REVIEW, AlgorithmType.A_STAR)
```

### Ajuster les Paramètres

```python
# Augmenter la profondeur d'exploration
wrapper.update_skill_config(SkillType.CODE_REVIEW, {
    "max_steps": 8,
    "num_thoughts": 7,
    "confidence_threshold": 0.8
})
```

### Créer un Profil Personnalisé

```python
# Préférences utilisateur
wrapper.user_profile.skill_preferences[SkillType.CODE_REVIEW] = {
    "priority": "speed",
    "preferred_algorithm": "bfs",
    "min_confidence": 0.75
}

# Sauvegarder
wrapper.save_state()
```

## Intégration avec Claude Code

Pour intégrer les skills avec Claude Code, voir [CLAUDE_CODE_INTEGRATION.md](CLAUDE_CODE_INTEGRATION.md)

### Commandes Claude Code

Une fois intégrées, les skills seront accessibles via :

```bash
/code-reviewer "Analysez ce code" --file app.py
/decision-maker "Évaluez ces options" --options='["opt1", "opt2"]'
/research-analyst "Recherchez..." --sources='["source1", "source2"]'
/problem-solver "Résolvez..." --constraints='{...}'
/thesis-validator "Validez cette thèse..." --evidence='{...}'
/expert-simulator "Question pour expert..." --expertise="domain"
```

## Dépannage

### Issue: Confiance faible

```python
# Solution: Augmenter la profondeur de recherche
wrapper.update_skill_config(SkillType.YOUR_SKILL, {
    "max_steps": 8,
    "num_thoughts": 7
})
```

### Issue: Exécution lente

```python
# Solution: Réduire la complexité
wrapper.update_skill_config(SkillType.YOUR_SKILL, {
    "num_thoughts": 4,
    "max_steps": 5
})
```

### Issue: Trop de reviews manuels

```python
# Solution: Baisser le seuil de confiance
wrapper.update_skill_config(SkillType.YOUR_SKILL, {
    "confidence_threshold": 0.65
})
```

## Statistiques Système

```python
# Résumé des optimisations
opt_summary = wrapper.skills_manager.get_optimization_summary()
print(f"Total optimisations: {opt_summary['total_optimizations']}")
print(f"Skills optimisés: {opt_summary['skills_optimized']}")
print(f"Historique: {opt_summary['history']}")
```

## Architecture de Flux de Données

```
User Input
    ↓
SkillCLIHandler.execute()
    ↓
SkillWrapper.execute_skill()
    ↓
[Traitement + ToT Search]
    ↓
SkillResult
    ↓
SkillsManagementSystem.record_execution()
    ↓
[Real-time Queue] → process_real_time_data()
    ↓
[Analyze Performance] → Recommendations
    ↓
[Auto-Optimize] (si safe)
    ↓
Save Profile + Metrics
    ↓
Return Result + Optimizations
```

## Points Clés

✅ **Optimisation Continue** - Le système apprend de chaque exécution
✅ **Isolation par Skill** - Chaque skill a sa propre configuration et métriques
✅ **Persistance** - L'évolution utilisateur est sauvegardée localement
✅ **Auto-Optimisation** - Les changements sûrs sont appliqués automatiquement
✅ **Transparence** - Toutes les recommandations sont expliquées
✅ **Contrôle Total** - L'utilisateur peut annu

ler ou modifier tout paramètre

---

**Dernière mise à jour:** 2026-03-04
