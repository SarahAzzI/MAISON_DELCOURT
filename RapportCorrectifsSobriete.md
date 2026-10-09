# RAPPORT TECHNIQUE DE CORRECTIFS · SOBRIÉTÉ NUMÉRIQUE & CONFORMITÉ RGPD

**Projet :** ChocoBot · Maison Delcourt  
**Auteur du patch :** Souhaib Massrour  
**Date :** 9 octobre 2026  
**Fichier cible principal :** `chatbot.py`  
**Outil de validation :** Arize Phoenix (Traces OpenTelemetry en direct)  

---

## 1. Contexte et Objectifs des Correctifs

Suite à l'évaluation initiale réalisée avec **Arize Phoenix** et **CodeCarbon**, deux axes d'amélioration prioritaires ont été traités :
1. **Conformité RGPD (Minimisation des données - Art. 5.1.c)** : Éliminer la transmission de données personnelles identifiantes (nom, email) au modèle de langage.
2. **Sobriété Numérique & Éco-conception (Green IT)** : Implémenter les 3 leviers d'optimisation préconisés par le brief :
   * **Levier 1 :** Mise en place d'un cache mémoire et d'un traitement déterministe pour les questions fréquentes (FAQ).
   * **Levier 2 :** Routage intelligent vers le modèle léger (`llama3.2:1b`) pour les interactions simples.
   * **Levier 3 :** Plafonnement du contexte conversationnel via une fenêtre glissante (*sliding window*).

---

## 2. Détail des Modifications et Preuves Visuelles

### A. Minimisation RGPD : Nettoyage du Contexte Client (`chatbot.py`)
* **Problème initial :** La fonction `customer_context()` injectait le nom civil et l'adresse email du client directement dans le `SYSTEM_PROMPT` envoyé au modèle de langage.
* **Correctif appliqué :**
  * Suppression totale de l'injection du nom et de l'email dans le prompt.
  * Suppression de l'instruction d'interpellation par le prénom.
  * Conservation stricte des seules contraintes techniques indispensables au conseil : les **allergies déclarées** et le **contexte familial**.
* **Impact juridique :** Respect du principe de minimisation (RGPD Art. 5.1.c) et garantie formelle qu'aucune PII ne transite dans le contexte du LLM.

---

### B. Levier 1 Sobriété : Cache Mémoire et Réponse Directe FAQ

* **Problème initial :** Les questions récurrentes portant sur les horaires ou la livraison (ex. *"Quels sont vos horaires ?"*) appelaient systématiquement le modèle de 3 milliards de paramètres, brûlant entre 800 et 1 600 tokens de prompt et 2 à 3 secondes d'inférence GPU/CPU à chaque occurrence.
* **Correctif appliqué :**
  * Création d'un dictionnaire statique `STATIC_FAQ` pour les questions fréquentes d'information générale (horaires, livraison, adresse, contact).
  * Création d'un cache mémoire par session `_SESSION_CACHE` mémorisant les questions identiques au cours d'un échange.
  * Interception en amont dans `handle_chat()` avant tout appel d'inférence.

![Validation du cache dans Arize Phoenix avec 0 token](images/Capture%20d’écran%20du%202026-10-09%2001-36-56.png)

> [!NOTE]
> **Preuve dans Arize Phoenix (Capture ci-dessus) :**  
> Lors de la requête sur les horaires à 01:24:30, la trace Phoenix confirme un temps de réponse instantané de **33 ms** et une consommation de **0 token** (ligne `total tokens = 0`). Le modèle n'est plus sollicité inutilement.

---

### C. Levier 2 Sobriété : Routage Dynamique de Modèles (1B vs 3B) et Maîtrise des Tokens

* **Problème initial :** 100 % des requêtes étaient dirigées vers `BIG_MODEL` (`llama3.2:3b`), y compris les simples salutations (*"Bonjour"*, *"Merci"*). Par ailleurs, `max_tokens` était fixé à 1 500, autorisant des générations verbeuses et coûteuses.
* **Correctif appliqué :**
  * Implémentation de la fonction `choose_model()` :
    * Les salutations et messages courts (< 45 caractères) sans contrainte allergène complexe sont routés vers `SMALL_MODEL` (`llama3.2:1b`).
    * Les requêtes de conseil complexes (budget, allergies, occasions) restent traitées par `BIG_MODEL` (`llama3.2:3b`).
  * Réduction du plafond de complétion `max_tokens` de **1 500 à 350 tokens**.

![Maîtrise de la volumétrie des tokens après correctifs](images/Capture%20d’écran%20du%202026-10-09%2001-37-23.png)

> [!TIP]
> **Observation de la consommation (Capture ci-dessus) :**  
> Sur une requête complète, le prompt est maintenu à **794 tokens** et la complétion est strictement bornée à **242 tokens** (fin des réponses à rallonge de 1 500 tokens).

---

### D. Levier 3 Sobriété : Fenêtre Glissante sur l'Historique (*Sliding Window*) et Latence

* **Problème initial :** L'intégralité des messages de la session était réinjectée à chaque tour de parole, provoquant une inflation continue du prompt (+109 % de tokens en 5 messages lors du test initial).
* **Correctif appliqué :**
  * Limitation de l'historique injecté aux **4 derniers messages** (`history[-4:]`), soit les 2 derniers tours de conversation complets.

![Profil de latence après optimisation](images/Capture%20d’écran%20du%202026-10-09%2001-37-12.png)

> [!IMPORTANT]
> **Bilan sur la latence (Capture ci-dessus) :**  
> Les requêtes en cache tombent à **0,01 s**, tandis que les requêtes de conseil traitées par le LLM restent stables sans subir la dégradation de temps causée par l'accumulation infinie de l'historique.

---

## 3. Matrice d'Impact Avant / Après (Synthèse Chiffrée)

| Métrique / Comportement | Avant Correctifs | Après Correctifs (Mesuré en direct) | Gain Réel |
| :--- | :---: | :---: | :---: |
| **Question récurrente (ex. Horaires)** | ~1 600 tokens / 2,5 s | **0 token / 33 ms** | **-100 % de tokens (instantané)** |
| **Question simple (ex. Bonjour)** | Modèle 3B | **Modèle 1B (`llama3.2:1b`)** | **Empreinte mémoire divisée par 3** |
| **Plafond max_tokens de sortie** | 1 500 tokens | **350 tokens** (242 mesurés) | **-76 % de charge maximale** |
| **Croissance du contexte** | +109 % en 5 tours | **Plafonné à ~800-1 000 tokens** | **Stabilisation stricte** |
| **Données nominatives dans le prompt** | Nom et email injectés | **Aucune PII transmise** | **Conformité RGPD garantie** |

---

## 4. Fichiers Modifiés & Traçabilité

* `chatbot.py` : Fonctions `customer_context()`, `check_faq_or_cache()`, `choose_model()`, `handle_chat()`.
