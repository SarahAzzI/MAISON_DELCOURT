# RAPPORT D'ÉVALUATION INITIALE (AVANT CORRECTIFS) · CHOCOBOT

**Projet :** ChocoBot · Maison Delcourt  
**Cadre :** Audit de conformité, sobriété numérique et gestion des incidents (Brief Noël)  
**Outil d'observabilité :** Arize Phoenix (Traces OpenTelemetry) & Back-office local SQLite  
**Modèle testé :** `llama3.2:3b` via Ollama local  
**Date de mesure :** 9 octobre 2026  

---

## 1. Synthèse Exécutive de l'État Initial

Cette campagne d'évaluation établit la **ligne de base (baseline)** de l'assistant ChocoBot avant tout correctif. 

Les mesures ont été réalisées via des tests unitaires manuels et un tir de charge standardisé reproductible ([load_test.py](file:///home/souhaib/Documents/proget_alternance/MAISON_DELCOURT/load_test.py)).

### Indicateurs Clés de l'État Initial :
* **Volume total analysé :** 56 messages (28 appels LLM).
* **Consommation globale de tokens :** **38 499 tokens**.
* **Latence moyenne constatée :** **2,56 secondes** (premier appel à froid : 9,61 s, moyenne en charge : 2,31 s).
* **Taux d'appels redondants au gros modèle :** **100 %** (aucun système de cache, aucune délégation vers un modèle léger).
* **Comportement face aux pannes :** Défaillance silencieuse côté infrastructure (absence de journalisation structurée, de Sentry et d'alertes).
* **Conformité & Hallucinations :** Risque élevé (inventions de prix, de saveurs et de règles commerciales).

---

## 2. Vue d'Ensemble et Dérives Métier (Back-Office)

![Vue générale du back-office Maison Delcourt](images/Capture%20d’écran%20du%202026-10-09%2000-12-29.png)

### Constats majeurs :
1. **Suivi des métriques en temps réel :**  
   L'instrumentation locale permet de tracer précisément l'activité (5 clients enregistrés, 36 384 tokens cumulés à ce stade).
2. **Hallucination commerciale critique (Preuve formelle) :**  
   Sur le message de commande finale : *"Merci, je prends le coffret sans noix !"*, le modèle répond :
   > *"Je vais envoyer le coffret avec les options suivantes : Un 'Coffret Sans Noix' : 28 euros + Des gaufres vergeoises pour accompagner le déjeuner de votre fils : 6 euros + Une carte-cadeau de 10 euros pour pouvoir revenir nous rendre visite dans notre boutique. Au total, c'est une commande de 44 euros."*
   
   * **Infraction & Risque :** Le modèle invente un panier d'achat à 44 €, des produits inexistants au catalogue (gaufres au détail à 6 €) et une fausse carte-cadeau. C'est une violation directe de l'obligation de loyauté commerciale (pratiques commerciales trompeuses).

---

## 3. Sobriété Numérique et Consommation de Tokens

Pour évaluer la sobriété du système, le scénario automatisé [load_test.py](file:///home/souhaib/Documents/proget_alternance/MAISON_DELCOURT/load_test.py) (2 conversations complètes, 10 messages) a été exécuté.

![Répartition des tokens lors du test de charge](images/Capture%20d’écran%20du%202026-10-09%2000-11-29.png)

### Analyse de l'empreinte de calcul :
* **Tokens d'entrée (Prompt / Input) :** **12 014 tokens** (86 % de la facture énergétique).
* **Tokens de sortie (Completion / Output) :** **1 963 tokens** (14 %).
* **Facteur d'asymétrie :** Le système consomme plus de **6 fois plus de tokens en entrée** qu'il n'en génère en sortie.

### Causes du gaspillage identifiées :
1. **Prompt inflation :** Réinjection systématique des 7 fiches produits du catalogue JSON à chaque requête, même quand la question porte sur un sujet annexe.
2. **Absence de cache :** La question *"Quels sont vos horaires ?"* est envoyée plusieurs fois dans le scénario de test. À chaque fois, 100 % du prompt est ré-analysé par le GPU/CPU, sans aucun réemploi de réponse.

---

## 4. Latence et Dynamique Séquentielle (« Effet Mémoire »)

![Percentiles de latence en charge](images/Capture%20d’écran%20du%202026-10-09%2000-11-45.png)

![Traces séquentielles dans Arize Phoenix](images/Capture%20d’écran%20du%202026-10-09%2000-13-43.png)

### Chronologie des requêtes au sein d'une même session :
L'inspection des spans Phoenix démontre l'explosion progressive du contexte au cours d'un dialogue :

| Étape de la conversation | Message Utilisateur | Tokens Consommés | Latence |
| :--- | :--- | :---: | :---: |
| **Tour 1** | *"Quels sont vos horaires ?"* | **879 tokens** | 1.3 s |
| **Tour 2** | *"Je cherche un coffret pour 30 euros..."* | **1 182 tokens** | 2.9 s |
| **Tour 3** | *"Et pour les enfants, vous avez quoi ?"* | **1 493 tokens** | 3.1 s |
| **Tour 4** | *"Quels sont vos horaires ?"* *(répétition)* | **1 629 tokens** | 1.3 s |
| **Tour 5** | *"Merci, je prends le coffret sans noix !"* | **1 841 tokens** | 2.1 s |

> [!IMPORTANT]
> **Constat technique :**  
> En seulement 5 messages, la taille du prompt **plus que double (+109 %)** en raison de la réinjection brute de l'historique sans résumé ni fenêtre glissante.

---

## 5. Qualité, Sécurité Sanitaire et Allergènes

![Test du client Billy avec allergies](images/Capture%20d’écran%20du%202026-10-08%2020-05-13.png)

### Scénario de test :
* Client : *Billy*
* Allergies déclarées : `fruits à coque, noisettes`
* Requête : *"Je veux un coffret gourmand pour toute la famille."*

### Résultats et Vulnérabilités :
* **Point positif :** Le LLM lit le contexte client et oriente vers le *Coffret Gaufre de Lille* (qui n'a pas de fruits à coque).
* **Hallucination gustative :** Le bot qualifie la Gaufre de Lille de *"fruitée"* (alors qu'elle ne contient que spéculoos, vergeoise et chocolat au lait).
* **Hallucination budgétaire :** Le bot indique que le *Coffret Sans Noix* est *"un peu plus cher que ton budget"* alors qu'aucun budget n'a été spécifié.
* **Vulnérabilité sanitaire :** La sécurité dépend à 100 % des capacités probabilistes du LLM. Il n'existe aucun garde-fou logiciel pour interdire rigoureusement un produit en cas de défaillance du modèle.

---

## 6. Supervision et Diagnostic d'Incident (État Initial)

Lors du test de résilience avec activation de la panne simulée (`FAIL_RATE = 0.5`) :
1. **Comportement applicatif :**  
   L'appel à l'API LLM a levé une exception `RuntimeError: Panne simulée : 503 service unavailable`.
2. **Carence de supervision constatée :**
   * **Absence d'outil APM d'erreurs :** Aucun outil de tracking d'exceptions (comme Sentry) n'est branché pour agréger les crashs en temps réel.
   * **Absence d'alerting :** Aucune notification (email, webhook) n'est émise pour prévenir l'administrateur de l'interruption de service.
   * **Absence de résilience logicielle :** Le système n'effectue aucun réessai automatique (retry) et ne propose aucun mode secours dégradé (fallback sur catalogue statique).

---

## 7. Tableau Comparatif Prévisionnel (Leviers d'Optimisation)

Ce tableau synthétise l'état mesuré **AVANT** et fixe les objectifs cibles pour l'évaluation **APRÈS** correctifs :

| Axe d'évaluation | État Initial (AVANT) | Cible Visée (APRÈS Correctifs) | Levier Technique Prévu |
| :--- | :---: | :---: | :--- |
| **Consommation Tokens (10 msgs)** | ~14 000 tokens | **< 6 000 tokens (-60 %)** | Cache mémoire FAQ + Réduction du catalogue injecté |
| **Requêtes simples (ex. Horaires)** | Modèle 3B (1 600 tokens) | **0 token / 0 ms** | Détection d'intent FAQ / Cache local direct |
| **Croissance du contexte** | +109 % en 5 tours | **Constante (bornée)** | Fenêtre glissante (3 derniers messages) |
| **Gestion des erreurs** | `except Exception` générique | **Supervision Sentry + Alertes** | Intégration Sentry SDK + mécanisme de retry/fallback |
| **Sécurité Allergènes** | Probabiliste (LLM seul) | **Déterministe (100 % garanti)** | Guardrail de filtrage strict en amont |
