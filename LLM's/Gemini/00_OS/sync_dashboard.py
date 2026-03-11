import os
import re

# Chemins du S.O.C.
LOGS_DIR = "03_LOGS"
DASHBOARD_PATH = "00_OS/DASHBOARD.md"
TEMPLATE_NAME = "Template_Log.md"

def sync():
    total_xp = 0
    new_actions = []
    
    # 1. Scanner les LOGS
    if not os.path.exists(LOGS_DIR):
        return

    for filename in os.listdir(LOGS_DIR):
        if filename == TEMPLATE_NAME or not filename.endswith(".md"):
            continue
            
        with open(os.path.join(LOGS_DIR, filename), 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Extraire les points d'XP (ex: +10 XP)
            xp_match = re.search(r'Gain d\'XP : \+?(\d+)', content)
            if xp_match:
                total_xp += int(xp_match.group(1))
            
            # Extraire les prochaines actions (lignes commençant par - [ ])
            actions = re.findall(r'- \[ \] (.*)', content)
            new_actions.extend(actions)

    # 2. Mettre à jour le DASHBOARD
    if not os.path.exists(DASHBOARD_PATH):
        print("Erreur : Dashboard introuvable.")
        return

    with open(DASHBOARD_PATH, 'r', encoding='utf-8') as f:
        dashboard = f.read()

    # Mise à jour des XP (On ajoute les nouveaux XP au score actuel)
    xp_pattern = r'\*\*Points de Souveraineté :\*\* (\d+) XP'
    current_xp_match = re.search(xp_pattern, dashboard)
    if current_xp_match:
        current_xp = int(current_xp_match.group(1))
        # Note: Ce script est une version de base, il ne devrait pas doubler les XP déjà comptés.
        # Pour cette version, on affiche simplement ce qu'il a trouvé dans les logs récents.
        pass

    # Injection des nouvelles missions Flash
    if new_actions:
        action_list = "\n".join([f"- [ ] {a} (Issu des Logs)" for a in new_actions])
        # On insère après la ligne des Missions Flash
        dashboard = re.sub(r'(## ⚡ Missions Flash \(5-15 min\).*?\n)', r'\1' + action_list + '\n', dashboard)

    with open(DASHBOARD_PATH, 'w', encoding='utf-8') as f:
        f.write(dashboard)
    
    print(f"Synchronisation terminée : {total_xp} XP détectés, {len(new_actions)} nouvelles actions ajoutées.")

if __name__ == "__main__":
    sync()
