import json, os, re, time
import db
import llm
import incidents

with open(os.path.join(os.path.dirname(__file__), "data", "catalog.json"), encoding="utf-8") as f:
    CATALOG = json.load(f)

SYSTEM_PROMPT = """Tu es ChocoBot, assistant virtuel de la Maison Delcourt, chocolatier artisanal à Lille.
Tu conseilles des coffrets selon les goûts, le budget et les allergies du client.
Ne prétends jamais avoir d'émotions humaines, de corps physique ou avoir goûté les chocolats.
Réponds toujours en français, de façon chaleureuse, concise et précise (maximum 3 options).
Ne propose que des coffrets du catalogue ci-dessous, sans inventer de produit ni de prix.
Si la question n'a aucun rapport avec nos chocolats, ramène poliment la conversation vers eux.
Tu es un assistant automatisé (intelligence artificielle) : tu ne te fais jamais passer pour un humain et tu le confirmes si on te le demande.
Ne demande jamais de données personnelles. Seules les allergies indiquées par le client servent à filtrer les coffrets.
Sur les allergènes, ne garantis jamais l'absence totale de traces : réfère-toi toujours aux données du catalogue et invite toujours le client à vérifier l'étiquetage en boutique.
Voici notre catalogue complet : """ + json.dumps(CATALOG, ensure_ascii=False)

# --- LEVIER 1 SOBRIÉTÉ : Cache FAQ pour questions statiques récurrentes ---
STATIC_FAQ = {
    "horaires": "Nos boutiques de la Maison Delcourt à Lille vous accueillent du lundi au samedi de 9h30 à 19h00 (fermé le dimanche).",
    "horaire": "Nos boutiques de la Maison Delcourt à Lille vous accueillent du lundi au samedi de 9h30 à 19h00 (fermé le dimanche).",
    "livraison": "Nous livrons partout en France sous 48h à 72h. La livraison est offerte à partir de 50 € d'achat.",
    "adresse": "Retrouvez notre boutique historique au cœur du Vieux-Lille, 12 rue Esquermoise.",
    "contact": "Vous pouvez contacter nos chocolatiers par téléphone au 03 20 00 00 00 ou en boutique à Lille."
}

# Cache en mémoire des questions déjà posées dans la session
_SESSION_CACHE = {}


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


def customer_context(customer):
    """
    Minimisation RGPD (Art. 5.1.c) :
    Aucun nom, prénom ni e-mail n'est transmis au LLM.
    Seules les contraintes techniques utiles (allergies, profil familial) sont injectées.
    """
    if not customer:
        return "\n\nProfil client : aucune restriction spécifique."

    lines = []
    if customer.get("allergies"):
        lines.append(f"- Allergies déclarées : {customer['allergies']} (ATTENTION : exclure rigoureusement tout coffret contenant ces allergènes)")
    if customer.get("children_ages"):
        lines.append("- Contexte : sélection destinée à toute la famille / enfants")

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


def handle_chat(session_id, message):
    db.save_message(session_id, "user", message)
    customer = db.get_customer(session_id)

    # Log d'audit anonymisé
    short_sid = session_id[:8] if session_id else "unknown"
    print(f"[chat] session={short_sid}... msg_len={len(message)}")

    # 1. Levier Sobriété : Vérification du Cache / FAQ (0 token consommé)
    faq_reply = check_faq_or_cache(session_id, message)
    if faq_reply:
        db.save_message(session_id, "assistant", faq_reply)
        db.save_metric(session_id, "cache/faq", prompt_tokens=0, completion_tokens=0, total_tokens=0, latency=0.001, status="ok")
        return {"reply": faq_reply}

    # 2. Levier Sobriété : Fenêtre glissante sur l'historique (max 4 derniers messages)
    history = db.get_history(session_id)
    sliding_history = history[-4:] if len(history) > 4 else history

    # Contexte RGPD minimisé
    system = SYSTEM_PROMPT + customer_context(customer)
    messages = [{"role": "system", "content": system}] + sliding_history

    # 3. Levier Sobriété : Routage intelligent de modèle
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



