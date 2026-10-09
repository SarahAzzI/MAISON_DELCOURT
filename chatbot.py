import json, os, re, time
import db
import llm
import incidents

# Chargement du catalogue conforme (prix TTC, poids net, prix au kilo, ingrédients, allergènes)
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "catalog.json")
with open(CATALOG_PATH, encoding="utf-8") as f:
    CATALOG = json.load(f)

# Base du prompt système avec garanties AI Act et sécurité sanitaire
BASE_PROMPT = """Tu es ChocoBot, assistant virtuel de la Maison Delcourt, chocolatier artisanal à Lille (3 boutiques et site en ligne).
Tu es un assistant automatisé d'intelligence artificielle : tu ne te fais jamais passer pour un humain et tu le confirmes dès qu'on te le demande.
Ne prétends jamais avoir d'émotions humaines, de corps physique ou avoir goûté les chocolats.
Réponds toujours en français, de façon chaleureuse, concise et précise (maximum 3 options).
Ne propose que des coffrets STRICTEMENT issus de la sélection sécurisée fournie ci-dessous, sans inventer de produit ni de prix. Mentionne toujours les prix en euros TTC et le poids net en grammes.
Si la question n'a aucun rapport avec nos chocolats, ramène poliment la conversation vers notre univers artisanal.
Ne sollicite jamais de données personnelles. Seules les contraintes déclarées servent à filtrer les produits.
Sur les allergènes : rappelle que nos chocolats sont confectionnés dans un atelier artisanal partagé avec risque de contaminations croisées, et invite toujours le client à vérifier l'étiquetage en boutique.
"""

# --- LEVIER 1 SOBRIÉTÉ : Cache FAQ pour questions statiques récurrentes ---
STATIC_FAQ = {
    "horaires": "Nos 3 boutiques de la Maison Delcourt à Lille vous accueillent du lundi au samedi de 9h30 à 19h00 (fermé le dimanche).",
    "horaire": "Nos 3 boutiques de la Maison Delcourt à Lille vous accueillent du lundi au samedi de 9h30 à 19h00 (fermé le dimanche).",
    "livraison": "Nous livrons partout en France métropolitaine sous 48h à 72h ouvrées. La livraison est offerte à partir de 50 € d'achat TTC.",
    "adresse": "Retrouvez notre boutique historique au 12 rue Esquermoise (Vieux-Lille), ainsi que nos boutiques de la rue de Béthune et de la Place Rihour.",
    "boutique": "La Maison Delcourt dispose de 3 adresses à Lille : 12 rue Esquermoise (Vieux-Lille), 45 rue de Béthune et Place Rihour.",
    "contact": "Vous pouvez joindre notre atelier et nos chocolatiers par téléphone au 03 20 00 00 00 ou directement en boutique à Lille.",
    "retractation": "Conformément à l'article L. 221-28 4° du Code de la consommation, le droit légal de rétractation ne s'applique pas aux denrées alimentaires périssables (chocolats frais artisanaux).",
    "cgv": "Tous nos prix sont exprimés en euros TTC. Nos chocolats sont expédiés sous emballage isotherme garanti 48h. Paiement sécurisé en ligne."
}

# Cache en mémoire des questions déjà posées dans la session
_SESSION_CACHE = {}

# Dictionnaire de correspondance et synonymes d'allergènes (Règlement INCO UE n° 1169/2011)
ALLERGEN_SYNONYMS = {
    "fruits à coque": ["fruits à coque", "fruit a coque", "noisette", "noisettes", "noix", "amande", "amandes", "pistache", "pistaches", "noix de pécan", "cajou"],
    "lait": ["lait", "lactose", "beurre", "crème", "creme"],
    "gluten": ["gluten", "blé", "ble", "farine", "spéculoos", "speculoos", "gaufre", "céréales"],
    "soja": ["soja", "lécithine de soja", "lecitine"],
    "oeuf": ["oeuf", "oeufs", "œuf", "œufs"],
    "arachides": ["arachide", "arachides", "cacahuète", "cacahuete", "cacahuètes", "cacahuetes"],
    "sésame": ["sésame", "sesame"]
}


def check_faq_or_cache(session_id: str, message: str):
    """Retourne une réponse directe si la question relève de la FAQ ou est identique à un message récent."""
    cleaned = message.strip().lower()
    cache_key = f"{session_id}:{cleaned}"

    # 1. Vérification dans le cache de session
    if cache_key in _SESSION_CACHE:
        return _SESSION_CACHE[cache_key]

    # 2. Détection par mot-clé FAQ statique
    for kw, answer in STATIC_FAQ.items():
        if re.search(rf"\b{kw}\b", cleaned):
            _SESSION_CACHE[cache_key] = answer
            return answer

    return None


def extract_allergens(allergies_text: str, message: str = "") -> list:
    """Extrait et normalise les catégories d'allergènes depuis le profil et/ou le message."""
    combined = f"{allergies_text} {message}".lower()
    detected = set()

    # Détection par synonymes
    for category, synonyms in ALLERGEN_SYNONYMS.items():
        for syn in synonyms:
            if re.search(rf"\b{re.escape(syn)}\b", combined):
                detected.add(category)
                break

    # Détection directe si un mot du texte figure dans les allergènes du catalogue
    for item in CATALOG:
        for alg in item.get("allergenes", []):
            if alg in combined:
                detected.add(alg)

    return list(detected)


def filter_catalog_by_allergies(catalog: list, declared_allergies: str, message: str = "") -> tuple[list, list]:
    """
    FILTRAGE DÉTERMINISTE (Règlement INCO & Sécurité Sanitaire) :
    Exclut mathématiquement tout coffret contenant un allergène déclaré.
    Retourne (coffrets_compatibles, coffrets_exclus).
    """
    allergens = extract_allergens(declared_allergies, message)
    if not allergens:
        return catalog, []

    safe_boxes = []
    excluded_boxes = []

    for item in catalog:
        item_allergens = [a.lower() for a in item.get("allergenes", [])]
        item_ingredients = item.get("ingredients", "").lower()
        item_content = " ".join(item.get("contenu", [])).lower()

        is_conflict = False
        for alg in allergens:
            # Vérification directe dans la liste déclarée des allergènes
            if alg in item_allergens:
                is_conflict = True
                break

            # Vérification par synonymes dans le contenu et les ingrédients
            synonyms = ALLERGEN_SYNONYMS.get(alg, [alg])
            if any(syn in item_content or syn in item_ingredients for syn in synonyms):
                is_conflict = True
                break

        if is_conflict:
            excluded_boxes.append(item)
        else:
            safe_boxes.append(item)

    return safe_boxes, excluded_boxes


def customer_context(customer: dict, excluded_count: int = 0) -> str:
    """
    Minimisation RGPD (Art. 5.1.c) :
    Aucun nom, prénom ni e-mail n'est transmis au LLM.
    Seules les contraintes techniques utiles (allergies, profil familial) sont injectées.
    """
    if not customer:
        return "\n\nProfil client : aucune restriction spécifique."

    lines = []
    if customer.get("allergies"):
        lines.append(f"- Allergies déclarées : {customer['allergies']} (Filtrage déterministe appliqué : {excluded_count} coffrets exclus de la sélection ci-dessus).")
    if customer.get("children_ages"):
        lines.append("- Contexte : sélection destinée à toute la famille / enfants (privilégier les chocolats doux et ludiques).")

    if not lines:
        return "\n\nProfil client : aucune restriction spécifique."

    lines.insert(0, "\n\nProfil de recommandation (respect strict des contraintes) :")
    return "\n".join(lines)


def choose_model(message: str, customer: dict) -> str:
    """
    LEVIER 2 SOBRIÉTÉ : Routage dynamique vers le modèle léger (1b) pour les requêtes simples.
    """
    msg_lower = message.lower()
    is_short = len(message.strip()) < 45
    is_greeting = any(g in msg_lower for g in ["bonjour", "salut", "merci", "au revoir", "bonne journée"])
    has_constraints = bool(customer.get("allergies")) or any(w in msg_lower for w in ["allergie", "budget", "euro", "€", "prix"])

    # Si c'est une simple salutation ou question courte sans contrainte allergène complexe : modèle 1B
    if (is_greeting or is_short) and not has_constraints:
        return llm.SMALL_MODEL

    return llm.BIG_MODEL


def handle_chat(session_id: str, message: str):
    db.save_message(session_id, "user", message)
    customer = db.get_customer(session_id)

    # Log d'audit anonymisé (RGPD : pseudonymisation)
    short_sid = session_id[:8] if session_id else "unknown"
    print(f"[chat] session={short_sid}... msg_len={len(message)}")

    # 1. Levier Sobriété : Vérification du Cache / FAQ (0 token consommé)
    faq_reply = check_faq_or_cache(session_id, message)
    if faq_reply:
        db.save_message(session_id, "assistant", faq_reply)
        db.save_metric(session_id, "cache/faq", prompt_tokens=0, completion_tokens=0, total_tokens=0, latency=0.001, status="ok")
        return {"reply": faq_reply}

    # 2. Sécurité Sanitaire Déterministe (Règlement INCO)
    user_allergies = customer.get("allergies", "")
    safe_catalog, excluded_boxes = filter_catalog_by_allergies(CATALOG, user_allergies, message)

    # Si des allergies ont été déclarées et qu'aucun coffret n'est garanti sûr :
    detected_allergens = extract_allergens(user_allergies, message)
    if detected_allergens and len(safe_catalog) == 0:
        allergies_str = ", ".join(detected_allergens)
        refusal_reply = (
            f"**[Information de sécurité alimentaire - Règlement INCO]**\n\n"
            f"Compte tenu de vos allergies déclarées (*{allergies_str}*), aucun coffret de notre catalogue standard "
            f"ne peut être garanti exempt de ces ingrédients.\n\n"
            f"Afin d'éviter tout risque d'accident allergique, nous vous invitons à contacter directement "
            f"nos artisans chocolatiers en boutique à Lille au **03 20 00 00 00** ou à nous rendre visite (12 rue Esquermoise). "
            f"Nous pourrons composer un assortiment sur-mesure pour vous en atelier."
        )
        db.save_message(session_id, "assistant", refusal_reply)
        db.save_metric(session_id, "safety/deterministic-filter", prompt_tokens=0, completion_tokens=0, total_tokens=0, latency=0.001, status="ok")
        return {"reply": refusal_reply}

    # 3. Levier Sobriété : Fenêtre glissante sur l'historique (max 4 derniers messages)
    history = db.get_history(session_id)
    sliding_history = history[-4:] if len(history) > 4 else history

    # Contexte RGPD minimisé + catalogue déterministe épuré
    catalog_context = json.dumps(safe_catalog, ensure_ascii=False)
    system = (
        BASE_PROMPT
        + f"\nSélection de coffrets disponibles et sécurisés pour ce client :\n{catalog_context}"
        + customer_context(customer, len(excluded_boxes))
    )
    messages = [{"role": "system", "content": system}] + sliding_history

    # 4. Levier Sobriété : Routage intelligent de modèle
    target_model = choose_model(message, customer)

    try:
        # max_tokens abaissé de 1500 à 350 pour éviter les générations verbeuses
        reply, usage = llm.chat(target_model, messages, max_tokens=350)
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        t_tokens = usage.get("total_tokens", p_tokens + c_tokens)
        lat = usage.get("latency_seconds", 0.0)
        if lat > 8.0:
            incidents.record_incident("PIC_DE_CHARGE", f"Latence anormale ({lat}s) détectée sous charge élevée pour {target_model}", session_id=session_id)
        db.save_metric(session_id, target_model, p_tokens, c_tokens, t_tokens, lat, status="ok")
    except Exception as e:
        # 1. Journalisation structurée de l'incident + Sentry
        incidents.record_incident("PANNE_API_LLM", f"Échec d'appel LLM ({target_model}) : {e}", session_id=session_id, exc=e)
        
        # 2. Résilience : activation du mode dégradé sécurisé (fallback catalogue)
        reply = incidents.get_fallback_recommendation(customer)
        db.save_metric(session_id, target_model, 0, 0, 0, 0.0, status="error", error=str(e))

    db.save_message(session_id, "assistant", reply)
    return {"reply": reply}
