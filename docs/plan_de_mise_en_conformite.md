# Plan de Mise en Conformite et Feuille de Route - ChocoBot

Ce document recapitule l'etat d'avancement du projet **ChocoBot**, detaille la mise en conformite reglementaire et technique (RGPD, AI Act, INCO, Droit de la consommation, Sobriete numerique, Supervision) et planifie la feuille de route.

---

## 1. Tableau de bord d'avancement global

| Domaine | Statut Actuel | Ce qui a ete implemente | Ce qui reste a finaliser | Priorite |
| :--- | :---: | :--- | :--- | :---: |
| **Securite Applicative** | **Conforme** | Authentification HTTP Basic sur `/admin` et `/admin/data`, gestion par variables d'environnement. | Maintenance courante | P3 |
| **RGPD (Donnees & Droits)** | **Conforme** | Droit a l'effacement (`DELETE /profile/{id}`), consentement explicite Art. 9, purge automatique des sessions inactives apres 30 jours, minimisation, console pseudonymisee. | Registre Art. 30 et Fiche CNIL | P1 |
| **AI Act (Transparence)** | **Conforme** | Identite transparente ChocoBot (fin de l'usurpation humaine), avertissement permanent IA en bandeau web (Art. 50). | Fiche d'evaluation des risques | P1 |
| **Sante & Allergenes (INCO)** | **Conforme** | **Filtrage deterministe Python pur** dans `chatbot.py` excluant mathematiquement tout coffret incompatible, bandeau d'avertissement permanent atelier dans l'interface, refus direct securise sans appel LLM si 0 produit sur. | Tests unitaires de validation | P1 |
| **Droit de la Consommation** | **Conforme** | Prix exprimes en euros TTC, poids net en grammes, prix a l'unite de mesure (EUR/kg), liste complete des ingredients, mention legale d'exclusion du droit de retractation (Art. L. 221-28 4 degres). | Finalisation de l'affichage front-end | P2 |
| **Sobriete Numerique (Green IT)** | **Conforme** | Cache FAQ statique (0 token, latence < 1 ms), routage dynamique de modele (1b / 3b), fenetre glissante d'historique (4 messages max), max_tokens limite a 350. | Suivi des metriques en production | P3 |
| **Supervision & Incidents** | **Conforme** | Integration Sentry (sans donnees personnelles PII), journalisation structuree `logs/incidents.jsonl`, resolution et post-mortem des 3 incidents majeurs, mode degrade (fallback). | Alertes temps reel | P3 |

---

## 2. Analyse technique des correctifs de conformite

### 2.1. Securite Sanitaire et Allergenes (Reglement INCO UE n deg 1169/2011)
* **Probleme identifie :** Confier la detection des allergenes a un modele de langage probabiliste (LLM) presente un risque d'hallucination inacceptable pouvant causer des chocs anaphylactiques.
* **Solution technique implementee :**
  1. Creation de la fonction deterministe `filter_catalog_by_allergies(catalog, user_allergies, message)` dans `chatbot.py`.
  2. Cartographie exhaustive des synonymes d'allergenes (fruits a coque, arachides, lait, gluten, soja, oeuf, sesame).
  3. Elimination stricte de tout coffret contenant un allergene interdit avant generation du prompt systeme.
  4. Si aucun coffret ne respecte les contraintes, interception immediate sans appel au modele de langage et renvoi d'un message securise invitant a contacter l'atelier lillois.
  5. Affichage d'un bandeau permanent d'information sur les contaminations croisees d'atelier dans `static/index.html`.

### 2.2. Droit de la Consommation et Information Precontractuelle
* **Probleme identifie :** Fiches produits lacunaires, prix sans devise ni taxe, absence de prix au kilo et manque d'informations claires sur la retractation pour les produits frais.
* **Solution technique implementee :**
  1. Restructuration complete de `data/catalog.json` : ajout de `prix_ttc`, `devise`, `poids_net_g`, `prix_au_kilo_ttc`, `ingredients` et `traces_possibles`.
  2. Integration des reponses FAQ normalisees sur les 3 adresses des boutiques de Lille (rue Esquermoise, rue de Bethune, Place Rihour).
  3. Integration de la mention d'exclusion legale du droit de retractation sur les denrees perissables (Art. L. 221-28 4 degres du Code de la consommation).

### 2.3. RGPD et AI Act
* **Solution technique implementee :**
  1. Limitation de la duree de conservation : execution de la purge automatique des donnees inactives (`purge_old_sessions`) a chaque demarrage de l'application FastAPI via le gestionnaire de cycle de vie (`lifespan`).
  2. Droit a l'oubli effectif via bouton et route `DELETE /profile/{session_id}`.
  3. Bandeau d'information visible informant l'utilisateur de la nature artificielle de l'assistant conformement a l'Article 50 de l'AI Act.

---

## 3. Livrables et Documentation Associee

* **Rapport d'Audit Reglementaire :** `docs/Rapport.md`
* **Registre de Traitement & Fiche de Conformite :** `docs/registre_de_traitement_et_fiche_conformite.md`
* **Mesures d'Empreinte et Sobriete :** `RapportEvaluation.md` et `RapportCorrectifsSobriete.md`
* **Supervision et Gestion des Incidents :** `PostMortemIncidents.md` et `incidents.py`
