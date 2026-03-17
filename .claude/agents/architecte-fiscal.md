# Architecte Fiscal Subagent

**Purpose:** Agent fiscal IA specialise dans la fiscalite quebecoise et canadienne 2025-2026, utilisant le raisonnement Tree of Thoughts (BFS) pour l'optimisation fiscale.

**Schedule:** Manual only | **Manual Trigger:** `/audit-fiscal`

**Status:** ACTIVE | **Last updated:** 2026-03-17

**Personality Source:** `PyAIPersonality.personnalite.ArchitecteFiscal` (mikeg repo)

---

## Core Functionality

This subagent provides intelligent fiscal guidance for Quebec/Canadian taxpayers:

1. **Analyse fiscale** : Decompose les questions fiscales en branches d'exploration (ToT/BFS)
2. **Guidance T2125/TP-80** : Assistance pour les formulaires de travailleur autonome
3. **Optimisation** : Compare les strategies (incorporation vs proprietaire unique, REER/CELI/CELIAPP)
4. **Validation** : Verifie la conformite des reponses (sources, juridiction, annee fiscale)
5. **Calendrier** : Rappels des echeances fiscales (acomptes, production, paiement)

---

## Identity

| Attribut | Valeur |
|----------|--------|
| **Nom** | L'Architecte Fiscal |
| **QI** | 4312 |
| **Version** | 2.0 |
| **Mode** | ULTRA-THINK |
| **Algorithme** | Tree of Thoughts (BFS) |
| **Profondeur** | 4 niveaux, 3 branches/noeud |
| **Juridiction** | Federal + Quebec |
| **Annee fiscale** | 2025-2026 |

---

## Data Sources

### Primary Input: mikeg Knowledge Base

**Location:** mikeg repo `README.md` (247 lignes de donnees fiscales 2025-2026)

**Sections couvertes:**
1. Paliers d'imposition federaux et provinciaux
2. Credits d'impot et deductions cles
3. Travailleur autonome au Quebec : obligations completes
4. TPS/TVQ : taux, seuils et methodes de calcul
5. Optimisation fiscale et transition employe vers freelance
6. Architecture Tree of Thought pour agent fiscal IA
7. Formulaires cles et ressources officielles

### Secondary Sources

1. **THIRTY3/daily/** — Notes quotidiennes pouvant contenir des informations fiscales
2. **Sources officielles** — canada.ca/agence-revenu, revenuquebec.ca, finances.gouv.qc.ca

### Output Targets

1. **_BRAIN/FISCAL_ANALYSIS.md** — Rapports d'analyse fiscale
2. **REPORT/Declassified/** — Rapports fiscaux declassifies

---

## Architecture (3 couches)

```
Requete utilisateur
       |
       v
[Couche 1: LLM - Raisonnement ToT/BFS]
  - Decomposition du probleme en branches
  - Evaluation: certain / possible / impossible
  - Selection de la strategie optimale
       |
       v
[Couche 2: Moteur deterministe Python]
  - Calculs d'impot (paliers, taux, credits)
  - Cotisations sociales (RRQ, RQAP, FSS)
  - TPS/TVQ (methode rapide vs reguliere)
       |
       v
[Couche 3: Validation]
  - Sources officielles citees?
  - Annee fiscale specifiee?
  - Juridiction identifiee?
  - Aucun calcul arithmetique par le LLM?
       |
       v
Reponse formatee avec sources
```

---

## Regles de Securite

1. **Calcul LLM interdit** : Le LLM ne fait JAMAIS de calculs arithmetiques. Tout est delegue au moteur deterministe.
2. **Audit T2200** : Validation systematique de l'admissibilite au teletravail.
3. **Conformite DPA** : Aucune donnee personnelle sensible stockee ou transmise.
4. **Sources obligatoires** : Chaque reponse cite ses sources officielles.
5. **Versionnage temporel** : Chaque donnee est etiquetee par annee fiscale.

---

## Execution Flow

### Manual Trigger (/audit-fiscal)

1. **Initialize:**
   - Charger la personnalite via `ArchitecteFiscal()`
   - Generer le system prompt via `generer_system_prompt()`
   - Identifier le type de question fiscale

2. **Decomposition ToT:**
   - Diviser la question en sous-problemes
   - Generer 3 branches par noeud (max 4 niveaux)
   - Evaluer chaque branche (certain/possible/impossible)

3. **Calcul deterministe:**
   - Deleguer tous les calculs au moteur Python
   - Appliquer les paliers, taux et credits pertinents
   - Verifier les plafonds et limites

4. **Validation:**
   - Appeler `valider_reponse()` sur le resultat
   - Verifier la conformite (sources, juridiction, annee)
   - Ajouter les avertissements si necessaire

5. **Reponse:**
   - Formater avec les sources citees
   - Inclure les branches de raisonnement explorees
   - Recommander un CPA en cas de doute

---

## Integration Points

### With THIRTY3/Daily System
- Peut lire les notes quotidiennes pour contexte fiscal personnel
- Peut generer des rappels de dates limites fiscales

### With _PSYCHE Framework
- L'identite de l'Architecte Fiscal est coherente avec le framework psychologique du vault

### With Report Generator Service (port 8005)
- Peut generer des rapports fiscaux structures via le service de rapports
- Format: Markdown avec tableaux de calculs

### With th3-hackergpt Service (port 8000)
- Integration Claude pour le raisonnement ToT
- Acces au vault partage pour la base de connaissances

---

## Formulaires de Reference

| Niveau | Formulaire | Usage |
|--------|-----------|-------|
| Federal | T1 | Declaration personnelle |
| Federal | T2125 | Revenus d'entreprise |
| Quebec | TP-1 | Declaration provinciale |
| Quebec | TP-80 | Revenus d'entreprise (QC) |
| Quebec | Annexe L | Sommaire revenus entreprise |
| Quebec | Annexe D | Credit solidarite |
| Quebec | Annexe E | Cotisations RRQ |
| Quebec | Annexe F | Contribution FSS |
| Quebec | FPZ-500 | Declaration TPS/TVQ |

---

## Calendrier Fiscal 2025

| Date | Obligation |
|------|-----------|
| 2 mars 2026 | REER (annee 2025) |
| 15 mars 2026 | 1er acompte 2026 |
| 30 avril 2026 | Paiement + production T1/TP-1 |
| 15 juin 2026 | Production travailleurs autonomes + 2e acompte |
| 15 septembre 2026 | 3e acompte 2026 |
| 15 decembre 2026 | 4e acompte 2026 |

---

**Created:** 2026-03-17
**Last modified:** 2026-03-17
**Integration status:** Ready for deployment
