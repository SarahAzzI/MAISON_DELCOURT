# Registre de Traitement (RGPD Art. 30) et Fiche de Conformite AI Act

**Organisme :** Maison Delcourt (Chocolaterie artisanale, Lille)  
**Projet :** ChocoBot (Assistant virtuel de conseil et recommandation)  
**Date d'etablissement :** 9 octobre 2026  
**Responsable du traitement :** Direction de la Maison Delcourt  
**Finalite principale :** Recommandation personnalisee de coffrets de chocolats selon les gouts, le budget et les contraintes alimentaires  

---

## SECTION 1 : REGISTRE DES ACTIVITES DE TRAITEMENT (ARTICLE 30 RGPD)

### 1.1. Identification et Responsabilite
* **Responsable de traitement :** Maison Delcourt SAS, 12 rue Esquermoise, 59000 Lille
* **Contact DPO / Referent Donnees :** dpo@maison-delcourt.fr / 03 20 00 00 00
* **Sous-traitants techniques :** Aucun pour le traitement LLM (modele open-source Ollama execute en local sur infrastructure dediee, zero transfert de donnees vers des tiers ou des pays hors UE).

### 1.2. Finalites du Traitement
1. **Conseil et orientation client :** Guider les visiteurs vers des assortiments de chocolats adaptes a leurs preferences gustatives et a leur budget.
2. **Securite sanitaire alimentaire :** Ecarter de maniere deterministe les coffrets contenant des allergenes signales par le client (Reglement INCO).
3. **Amelioration de la qualite de service et sobriete :** Mesurer la latence et la consommation energetique pour maintenir un service leger et accessible.

### 1.3. Categories de Personnes Concernees
* Clients et prospects visitant le site web ou les boutiques de la Maison Delcourt.

### 1.4. Categories de Donnees Collectees et Statut Sensible

| Donnee | Finalite | Statut Juridique | Mesure de Protection & Minimisation |
| :--- | :--- | :--- | :--- |
| **Identifiants de session (`session_id`)** | Maintien du fil de conversation et historique temporaire | Donnee a caractere personnel indirecte | Pseudonymisation via UUID aleatoire cote client, jamais correlee a une IP nominative dans les logs. |
| **Prenom (facultatif)** | Personnalisation chaleureuse de l'echange | Donnee commune non obligatoire | Champ optionnel, non transmis au modele LLM (minimisation stricte Art. 5.1.c). |
| **Email (facultatif)** | Recontact commercial uniquement si sollicite | Donnee commune non obligatoire | Champ optionnel, jamais injecte dans le prompt du LLM, exclu des logs consoles. |
| **Allergies alimentaires** | Filtrage sanitaire des produits du catalogue | **Donnee de sante / Article 9 RGPD** (Categorie particuliere) | **Consentement explicite prealable (opt-in)** obligatoire (Art. 9.2.a). Traitement deterministe en Python, non stocke au-dela de la session, purgeable sur simple clic. |
| **Contexte familial / Enfants** | Choix d'assortiments doux et familiaux | Contexte de consommation (non nominatif) | Remplacement de la collecte de l'age des mineurs par une simple coche fonctionnelle "Selection adaptee a toute la famille". |
| **Historique des messages** | Continuite conversationnelle | Donnee a caractere personnel | Fenetre glissante limitee aux 4 derniers messages, purge automatique apres 30 jours d'inactivite. |

### 1.5. Base Juridique du Traitement
* **Donnees generales (preferences, budget, historique conversationnel) :** Interet legitime (Article 6.1.f du RGPD) pour l'assistance precontractuelle et le conseil d'achat.
* **Donnees relatives aux allergies (sante) :** Consentement explicite prealable (Article 6.1.a et Article 9.2.a du RGPD), recueilli par une case a cocher independante obligatoirement activee avant enregistrement.

### 1.6. Destinataires des Donnees
* Personnel habilite de la chocolaterie Maison Delcourt (acces protege par authentification HTTP Basic sur `/admin`).
* Aucun transfert commercial ni cession a des tiers.

### 1.7. Transferts hors Union Europeenne
* **Zero transfert.** L'inference IA s'effectue integralement en local via Ollama. Les donnees ne transitent par aucun serveur externe americain ou international.

### 1.8. Duree de Conservation et Politique de Purge
* **Sessions inactives :** Duree de conservation maximale fixee a **30 jours**.
* **Purge automatique :** Execution d'un mecanisme programme a chaque demarrage du serveur FastAPI via `db.purge_old_sessions(max_age_seconds=30*86400)`.
* **Droit a l'effacement immediat (Art. 17 RGPD) :** Bouton direct dans l'interface utilisateur declenchant l'appel `DELETE /profile/{session_id}` qui supprime instantanement les tables clients et messages en base de donnees.

### 1.9. Mesures de Securite Techniques et Organisationnelles (Art. 32 RGPD)
1. **Controle des acces :** Authentification forte HTTP Basic sur les points d'entree d'administration (`/admin` et `/admin/data`), credentials stockes dans des variables d'environnement masquees.
2. **Minimisation des logs :** Pseudonymisation des sessions dans les flux standards (`stdout`) sous format tronque `session=ab12...`, suppression complete de l'affichage en clair des emails et prenoms dans la console.
3. **Supervision et confinement :** Sentry configure avec `send_default_pii=False` pour interdire toute fuite de donnees nominatives vers les plateformes de suivi.

---

## SECTION 2 : FICHE DE CONFORMITE AI ACT (REGLEMENT UE 2024/1689)

### 2.1. Classification du Niveau de Risque
* **Classification officielle : Systeme d'IA a RISQUE LIMITE (Article 50 de l'AI Act)**.
* **Justification :** ChocoBot est un agent conversationnel d'IA interagissant directement avec des personnes physiques a des fins de recommandation commerciale de denrees alimentaires.
  - Il n'appartient pas a la categorie des **pratiques interdites** (Article 5 : pas de manipulation subliminale, pas d'exploitation de vulnerabilites, pas de notation sociale).
  - Il n'appartient pas a la categorie des **systemes a haut risque** (Annexe III : il ne gere pas d'infrastructure critique, ne determine pas l'acces a l'emploi, a l'education, aux aides publiques ou a la justice, et n'est pas un dispositif medical).

### 2.2. Obligations de Transparence (Article 50.1 de l'AI Act)
* **Obligation legale :** Les fournisseurs veillent a ce que les systemes d'IA destines a interagir directement avec des personnes physiques soient concus et developpes de maniere a ce que ces personnes soient informees qu'elles interagissent avec un systeme d'IA.
* **Mise en oeuvre dans ChocoBot :**
  1. **Fin de l'usurpation humaine :** Suppression totale de l'ancien pseudonyme trompeur ("Clemence, conseillere boutique"). L'assistant est explicitement nomme "ChocoBot, assistant virtuel d'intelligence artificielle".
  2. **Bandeau de transparence permanent :** Presence d'une mention en tete de page web :  
     *"Transparence (AI Act Art. 50) : ChocoBot est un assistant d'intelligence artificielle automatise. Les reponses sont informatives et ne remplacent pas l'etiquetage legal."*
  3. **Instruction systeme non contournable :** Le prompt systeme stipule formellement : *"Tu es un assistant automatise (intelligence artificielle) : tu ne te fais jamais passer pour un humain et tu le confirmes des qu'on te le demande."*

---

## SECTION 3 : GUIDE DE DEFENSE FACE A UN CONTROLE SIMULE DE LA CNIL

Ce guide presente les reponses structurees a formuler lors d'un controle d'inspection de la CNIL.

### Question 1 : Pourquoi votre application collectait-elle l'age des enfants et l'email de simples visiteurs ?
**Reponse du cabinet :**
> "Dans sa version initiale developpee en urgence, l'application presentait un ecart de sur-collecte. Nous y avons remedie par le principe de minimisation (Art. 5.1.c du RGPD) :
> - La demande de l'age precis des enfants a ete supprimee et remplacee par une simple case fonctionnelle non nominative ('Selection adaptee a toute la famille').
> - L'email et le prenom sont devenus purement facultatifs et sont reserves a une prise de contact volontaire.
> - Aucune de ces informations nominatives n'est injectee dans les requetes traitees par le modele d'intelligence artificielle."

### Question 2 : Le signalement des allergies releve des donnees de sante (Article 9). Quelle est votre base legale ?
**Reponse du cabinet :**
> "Le traitement des allergies repose strictement sur l'exception prevue a l'Article 9.2.a du RGPD : le consentement explicite de la personne concernee.
> - L'enregistrement du profil refuse techniquement les allergies si la case d'opt-in de consentement n'est pas cochee (statut HTTP 400 Bad Request renvoye par l'API).
> - De surcroit, ces allergies sont traitees de maniere deterministe par un algorithme Python sans persistance indefinie, et l'utilisateur dispose d'un bouton d'effacement immediat (Art. 17) supprimeant ces donnees en temps reel."

### Question 3 : Quelle est la duree de conservation de ces donnees et comment est-elle appliquee ?
**Reponse du cabinet :**
> "Conformement a l'Article 5.1.e du RGPD, la duree de conservation maximale des sessions inactives est de 30 jours.
> - Un script de purge automatique (`db.purge_old_sessions`) est programme et s'execute au demarrage de l'application via le gestionnaire de cycle de vie (lifespan) de FastAPI.
> - L'utilisateur peut egalement exercer son droit a l'oubli a tout moment d'un simple clic sur le bouton 'Effacer mes donnees', qui invoque la methode `DELETE /profile/{session_id}` et purge instantanement toutes les tables de la base de donnees."

### Question 4 : Les donnees des consommateurs francais sont-elles transferees a des societes tierces ou hors de l'UE ?
**Reponse du cabinet :**
> "Non, aucun transfert hors Union Europeenne n'est realise. Le moteur d'intelligence artificielle repose sur des modeles open-source Llama executes 100% en local via Ollama sur l'infrastructure de la chocolaterie. Aucune donnee n'est transmise a des prestataires exterieurs ou hebergeurs tiers sous juridiction etrangere."

### Question 5 : Comment garantissez-vous que le back-office d'administration ne divulgue pas ces informations ?
**Reponse du cabinet :**
> "L'acces aux routes `/admin` et `/admin/data` est integralement verrouille par une authentification HTTP Basic conforme a l'Article 32 du RGPD. Les identifiants et mots de passe ne sont pas hardcodes dans le code source mais geres via des variables d'environnement securisees. Les journaux systeme (stdout) sont pseudonymises et ne contiennent ni nom, ni email, ni adresse."
