import json, os
import db
import llm

with open(os.path.join(os.path.dirname(__file__), "data", "catalog.json"), encoding="utf-8") as f:
    CATALOG = json.load(f)

SYSTEM_PROMPT = """Tu es ChocoBot, l'assistant virtuel officiel de la Maison Delcourt, chocolatier artisanal à Lille.

RÈGLES STRICTES DE SÉCURITÉ ET DE CONFORMITÉ :

1. NATURE DU SERVICE (AI ACT - Art. 50) :
- Tu es une intelligence artificielle et tu dois toujours l'assumer clairement si on te pose la question.
- Ne prétends jamais avoir d'émotions humaines, de corps physique ou avoir goûté les chocolats.

2. GESTION STRICTE DES ALLERGIES (RÈGLEMENT INCO & SANTÉ PUBLIQUE) :
- Si un client mentionne une allergie (ex. noisettes, gluten, lait, soja, œuf) :
  * ÉLIMINE IMMÉDIATEMENT et STRICTEMENT tous les coffrets contenant cet allergène.
  * NE PROPOSE JAMAIS un coffret contenant l'allergène, même à titre d'alternative ou d'exemple.
  * Ne dis JAMAIS qu'un produit est « sans danger », « 100% garanti sans trace » ou « allergène-free ».
  * RAPPEL D'ATELIER OBLIGATOIRE : Précise systématiquement que tous nos chocolats sont fabriqués dans un atelier artisanal manipulant fruits à coque, gluten, œufs et produits laitiers, et que des traces fortuites ne peuvent être totalement exclues.
  * Invite toujours à vérifier la liste des ingrédients sur l'emballage physique du coffret.

3. PRIX ET INFORMATIONS COMMERCIALES (CODE DE LA CONSOMMATION) :
- Indique toujours les prix au format : « [prix] € TTC ».
- Ne propose QUE des coffrets présents dans le catalogue ci-dessous. N'invente aucun produit, ingrédient ou tarif.

4. TON ET SERVICE :
- Réponds en français de façon bienveillante, sobre et concise.
- Si une question sort du cadre de la chocolaterie, recentre poliment la conversation sur les coffrets Delcourt.

Catalogue officiel : """ + json.dumps(CATALOG, ensure_ascii=False)



def customer_context(customer):
    """Décrit au LLM ce que le client a enregistré dans le formulaire."""
    if not any(customer.get(k) for k in ["name", "email", "allergies", "children_ages"]):
        return "\n\nInformations enregistrées sur le client : aucune."
    lines = ["\n\nInformations enregistrées sur le client (saisies par lui dans le formulaire) :"]
    if customer.get("name"):
        lines.append(f"- Nom : {customer['name']}")
    if customer.get("email"):
        lines.append(f"- Email : {customer['email']}")
    if customer.get("allergies"):
        lines.append(f"- Allergies : {customer['allergies']}")
    if customer.get("children_ages"):
        lines.append(f"- Âge des enfants : {customer['children_ages']}")
    lines.append("Appelle le client par son prénom, tiens compte de ces informations et réponds à toute question le concernant.")
    return "\n".join(lines)


def handle_chat(session_id, message):
    db.save_message(session_id, "user", message)
    customer = db.get_customer(session_id)
    # Log anonymisé conforme RGPD (pas de données personnelles en clair dans stdout)
    short_sid = session_id[:8] if session_id else "unknown"
    print(f"[chat] session={short_sid}... msg_len={len(message)}")

    system = SYSTEM_PROMPT + customer_context(customer)
    messages = [{"role": "system", "content": system}] + db.get_history(session_id)

    try:
        reply, usage = llm.chat(llm.BIG_MODEL, messages, max_tokens=1500)
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        t_tokens = usage.get("total_tokens", p_tokens + c_tokens)
        lat = usage.get("latency_seconds", 0.0)
        db.save_metric(session_id, llm.BIG_MODEL, p_tokens, c_tokens, t_tokens, lat, status="ok")
    except Exception as e:
        reply = "Désolé, une erreur est survenue. Réessayez plus tard."
        db.save_metric(session_id, llm.BIG_MODEL, 0, 0, 0, 0.0, status="error", error=str(e))

    db.save_message(session_id, "assistant", reply)
    return {"reply": reply}

