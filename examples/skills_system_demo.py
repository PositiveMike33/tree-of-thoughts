#!/usr/bin/env python3
"""
Tree of Thoughts Skills System Demo

Démonstration complète du système de skills avec optimisation en temps réel.
"""

import json
from tree_of_thoughts.vault.skills import (
    SkillWrapper,
    SkillType,
    AlgorithmType,
    get_cli_handler,
)


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f" {title:^68}")
    print("=" * 70 + "\n")


def demo_basic_execution():
    """Démo 1: Exécution basique de skills."""
    print_header("DÉMO 1: Exécution Basique de Skills")

    wrapper = SkillWrapper(user_id="demo_user")

    # Exécuter Code Reviewer
    print("1. Exécution: Code Reviewer")
    print("-" * 70)

    result = wrapper.execute_skill(
        skill_type=SkillType.CODE_REVIEW,
        prompt="Analysez ce code Python pour les bugs et la sécurité",
        context={"language": "python", "size": "small"},
    )

    if result["success"]:
        skill_result = result["result"]
        print(f"✓ Exécution réussie")
        print(f"  • Confiance: {skill_result['confidence_level']} ({skill_result['confidence_score']:.1%})")
        print(f"  • Temps: {skill_result['execution_time']:.2f}s")
        print(f"  • Nodes explorés: {skill_result['audit_trail'].get('nodes_explored', 'N/A')}")
    else:
        print(f"✗ Erreur: {result.get('error')}")


def demo_skill_status():
    """Démo 2: Afficher le statut des skills."""
    print_header("DÉMO 2: Statut des Skills")

    wrapper = SkillWrapper(user_id="demo_user")

    print(wrapper.cli_list_skills())


def demo_optimization():
    """Démo 3: Optimisation en temps réel."""
    print_header("DÉMO 3: Optimisation en Temps Réel")

    wrapper = SkillWrapper(user_id="demo_user")

    print("Exécution multiple pour générer des données d'optimisation...")
    print("-" * 70)

    # Simuler plusieurs exécutions
    for i in range(3):
        print(f"\nExécution {i+1}/3...")
        result = wrapper.execute_skill(
            skill_type=SkillType.DECISION,
            prompt=f"Choisir entre option A, B, C (itération {i+1})",
            context={"iteration": i+1},
        )

    # Afficher les optimisations
    print("\n" + "-" * 70)
    print("Recommendations d'optimisation:")
    print("-" * 70)

    opt_status = wrapper.get_optimization_status()
    if opt_status["pending_recommendations"]:
        for rec in opt_status["pending_recommendations"]:
            print(f"\n• Type: {rec['type']}")
            print(f"  Suggestion: {rec['suggestion']}")
            if "action" in rec:
                action = rec["action"]
                print(f"  Action: {action['parameter']} → {action['new_value']}")
    else:
        print("✓ Aucune optimisation nécessaire")


def demo_algorithm_switching():
    """Démo 4: Changer d'algorithme."""
    print_header("DÉMO 4: Changement d'Algorithme")

    wrapper = SkillWrapper(user_id="demo_user")

    skills_to_test = [
        (SkillType.CODE_REVIEW, [AlgorithmType.BFS, AlgorithmType.A_STAR]),
        (SkillType.DECISION, [AlgorithmType.BEST]),
        (SkillType.RESEARCH, [AlgorithmType.A_STAR]),
    ]

    for skill_type, algorithms in skills_to_test:
        print(f"\nSkill: {skill_type.value}")
        print("-" * 70)

        for algo in algorithms:
            # Changer d'algorithme
            result = wrapper.switch_algorithm(skill_type, algo)

            if result["success"]:
                print(f"  ✓ Switched to {algo.value}")
            else:
                print(f"  ✗ Error: {result['message']}")

    # Afficher la config finale
    print("\n" + "-" * 70)
    print("Configuration finale:")
    print("-" * 70)

    for skill_type in SkillType:
        config = wrapper.skills_manager.get_skill_config(skill_type)
        if config:
            print(f"\n{skill_type.value}:")
            print(f"  • Algorithm: {config.algorithm.value}")
            print(f"  • Max steps: {config.max_steps}")
            print(f"  • Confidence threshold: {config.confidence_threshold}")


def demo_metrics_and_reporting():
    """Démo 5: Métriques et rapports."""
    print_header("DÉMO 5: Métriques et Rapports")

    wrapper = SkillWrapper(user_id="demo_user")

    # Exécuter quelques skills
    print("Exécution de plusieurs skills pour générer des métriques...")
    print("-" * 70)

    test_cases = [
        (SkillType.CODE_REVIEW, "Analysez ce code"),
        (SkillType.DECISION, "Évaluez ces options"),
        (SkillType.CODE_REVIEW, "Vérifiez la sécurité"),
    ]

    for skill_type, prompt in test_cases:
        result = wrapper.execute_skill(skill_type, prompt)
        if result["success"]:
            print(f"✓ {skill_type.value}: {result['result']['confidence_level']}")

    # Afficher les métriques
    print("\n" + "-" * 70)
    print("Métriques des Skills:")
    print("-" * 70)

    all_metrics = wrapper.get_all_metrics()
    for skill_type, metrics in all_metrics.items():
        if metrics.total_executions > 0:
            print(f"\n{skill_type.value}:")
            print(f"  • Exécutions: {metrics.total_executions}")
            print(f"  • Confiance moyenne: {metrics.avg_confidence:.1%}")
            print(f"  • Temps moyen: {metrics.avg_execution_time:.2f}s")
            print(f"  • Tendance: {metrics.trending_confidence:.1%}")
            print(f"  • Taux de review: {metrics.human_review_rate:.1%}")


def demo_persistence():
    """Démo 6: Persistance et import/export."""
    print_header("DÉMO 6: Persistance et Import/Export")

    wrapper = SkillWrapper(user_id="demo_user_persistence")

    # Exécuter quelques skills
    print("1. Exécution de skills...")
    print("-" * 70)

    for i in range(2):
        wrapper.execute_skill(SkillType.CODE_REVIEW, f"Analyse {i+1}")

    # Exporter l'état
    print("\n2. Export de l'état du système...")
    print("-" * 70)

    state = wrapper.export_state()
    print(f"✓ État exporté avec:")
    print(f"  • {len(state['skill_configs'])} configurations de skills")
    print(f"  • {len(state['skill_metrics'])} métriques")
    print(f"  • {len(state['optimization_history'])} optimisations")

    # Sauvegarder
    print("\n3. Sauvegarde locale...")
    print("-" * 70)

    wrapper.save_state()
    print("✓ État sauvegardé dans ~/.tot/skills/")

    # Importer dans une nouvelle instance
    print("\n4. Import dans une nouvelle instance...")
    print("-" * 70)

    wrapper2 = SkillWrapper(user_id="demo_user_persistence")
    success, msg = wrapper2.import_state(state)

    if success:
        print(f"✓ {msg}")
        metrics = wrapper2.skills_manager.get_skill_metrics(SkillType.CODE_REVIEW)
        if metrics:
            print(f"  • Code Reviewer executions: {metrics.total_executions}")
    else:
        print(f"✗ {msg}")


def demo_cli_handlers():
    """Démo 7: Utilisation des CLI handlers."""
    print_header("DÉMO 7: CLI Handlers")

    print("Utilisation des handlers CLI spécialisés...")
    print("-" * 70)

    # Code Reviewer CLI
    code_handler = get_cli_handler(SkillType.CODE_REVIEW)
    print("\n1. CodeReviewerCLI:")
    result = code_handler.execute(
        prompt="Vérifiez la qualité",
        algorithm="bfs",
    )
    print(result)

    # Decision Maker CLI
    decision_handler = get_cli_handler(SkillType.DECISION)
    print("\n2. DecisionMakerCLI:")
    result = decision_handler.execute(
        prompt="Quelle option choisir?",
    )
    print(result)

    # Afficher le statut
    print("\n3. Statut du Code Reviewer:")
    print(code_handler.status())


def demo_advanced_workflow():
    """Démo 8: Workflow avancé."""
    print_header("DÉMO 8: Workflow Avancé Complet")

    wrapper = SkillWrapper(user_id="demo_advanced")

    print("1. Configuration personnalisée...")
    print("-" * 70)

    # Configurer un skill personnalisé
    success, msg = wrapper.update_skill_config(SkillType.CODE_REVIEW, {
        "max_steps": 8,
        "num_thoughts": 7,
        "confidence_threshold": 0.80,
    })

    if success:
        print("✓ Configuration mise à jour:")
        config = wrapper.skills_manager.get_skill_config(SkillType.CODE_REVIEW)
        print(f"  • max_steps: {config.max_steps}")
        print(f"  • num_thoughts: {config.num_thoughts}")
        print(f"  • confidence_threshold: {config.confidence_threshold}")

    print("\n2. Exécution avec config personnalisée...")
    print("-" * 70)

    result = wrapper.execute_skill(
        skill_type=SkillType.CODE_REVIEW,
        prompt="Analysez ce code complexe",
    )

    if result["success"]:
        sr = result["result"]
        print(f"✓ Exécution réussie")
        print(f"  • Confiance: {sr['confidence_score']:.1%}")
        print(f"  • Temps: {sr['execution_time']:.2f}s")

    print("\n3. Optimisations appliquées...")
    print("-" * 70)

    opt_summary = wrapper.skills_manager.get_optimization_summary()
    print(f"Total d'optimisations: {opt_summary['total_optimizations']}")
    print(f"Skills optimisés: {opt_summary['skills_optimized']}")

    print("\n4. Résumé final...")
    print("-" * 70)

    print(wrapper.cli_optimize())


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " Tree of Thoughts Skills System - Complete Demo ".center(68) + "║")
    print("║" + " Avec optimisation en temps réel ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    demos = [
        ("Exécution Basique", demo_basic_execution),
        ("Statut des Skills", demo_skill_status),
        ("Optimisation", demo_optimization),
        ("Changement d'Algorithme", demo_algorithm_switching),
        ("Métriques", demo_metrics_and_reporting),
        ("Persistance", demo_persistence),
        ("CLI Handlers", demo_cli_handlers),
        ("Workflow Avancé", demo_advanced_workflow),
    ]

    for title, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n✗ Erreur dans {title}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(" Demo Complétée! ".center(70))
    print("=" * 70)
    print("\nProchaines étapes:")
    print("  1. Lire SKILLS_SYSTEM.md pour la documentation complète")
    print("  2. Lire CLAUDE_CODE_SKILLS_INTEGRATION.md pour l'intégration")
    print("  3. Intégrer avec Claude Code pour les commandes /skill")
    print("  4. Configurer les hooks de session Claude Code")
    print()


if __name__ == "__main__":
    main()
