# Implémentation de la Sécurité des Accès et de la Conformité RGPD

## 1. Contexte & Enjeux
L'audit préalable ([`docs/Rapport.md`](file:///Users/amaury/MAISON_DELCOURT/docs/Rapport.md)) a mis en évidence plusieurs risques critiques :
* Exposition publique des données clients et conversations privées sur `/admin` et `/admin/data`.
* Traitement de données de santé (allergies alimentaires) sans consentement explicite (RGPD Art. 9).
* Absence de droit à l'effacement (RGPD Art. 17).
* Fuite de données personnelles dans les journaux console standard (`stdout`).

Cette implémentation traite l'intégralité de ces points critiques sur la branche **`security/admin-auth-rgpd`**.

---

## 2. Détail des Mesures Mises en Œuvre

### 2.1. Sécurisation du Back-office (`app.py`)
* Implémentation du protocole d'authentification **HTTP Basic Auth** (`fastapi.security.HTTPBasic`).
* Vérification des identifiants avec comparaison sécurisée contre les attaques temporelles (`secrets.compare_digest`).
* Identifiants configurables via variables d'environnement (`ADMIN_USERNAME` et `ADMIN_PASSWORD`), documentés dans `.env.example`.
* Protection stricte des routes :
  * `GET /admin`
  * `GET /admin/data`
* Réponse `401 Unauthorized` avec en-tête `WWW-Authenticate: Basic` si les identifiants sont manquants ou erronés.

### 2.2. Droit à l'Effacement / Droit à l'Oubli (`app.py` & `db.py`)
* **Endpoint API :** `DELETE /profile/{session_id}`.
* **Persistance SQLite :** Fonction `delete_session(session_id)` supprimant les enregistrements dans les tables `customers` et `messages`.
* **Rétention des données :** Fonction `purge_old_sessions(max_age_seconds)` permettant de purger automatiquement les sessions inactives.
* **Interface Utilisateur :** Bouton interactif *« 🗑️ Effacer mes données (Droit à l'oubli) »* réinitialisant immédiatement la session et confirmant l'effacement.

### 2.3. Consentement Explicite & Données Sensibles (RGPD Art. 9)
* **Frontend (`static/index.html`) :** Case à cocher obligatoire (*opt-in*) avant d'enregistrer des allergies alimentaires :
  > *« J'accepte que la Maison Delcourt traite mes données (dont allergies) pour cette recommandation. »*
* **Backend (`app.py`) :** Contrôle strict dans `POST /profile` : si des allergies sont déclarées sans consentement explicite (`consent_data=False`), l'API rejette la requête avec une erreur `400 Bad Request`.

### 2.4. Minimisation des Données & Anonymisation des Logs
* **Minimisation :** Remplacement de la collecte nominative de l'âge des enfants par une option non-intrusive *« Sélection adaptée à toute la famille / enfants »*.
* **Logs Console (`chatbot.py`) :** Remplacement du log non sécurisé `print(f"[chat] {customer} : {message}")` par un log anonymisé :
  ```python
  short_sid = session_id[:8] if session_id else "unknown"
  print(f"[chat] session={short_sid}... msg_len={len(message)}")
  ```

---

## 3. Validation par Tests Automatisés

Un ensemble de tests automatisés vérifie le respect des règles de sécurité :
1. Tentative d'accès non authentifié à `/admin` -> `401 Unauthorized`.
2. Tentative d'accès non authentifié à `/admin/data` -> `401 Unauthorized`.
3. Accès avec identifiants valides -> `200 OK`.
4. Enregistrement d'allergies sans case de consentement -> `400 Bad Request`.
5. Suppression de données via `DELETE /profile/{session_id}` -> données effacées en base.
