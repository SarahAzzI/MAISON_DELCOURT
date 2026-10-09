import unittest
import json
import os
import time

from chatbot import (
    CATALOG,
    filter_catalog_by_allergies,
    extract_allergens,
    check_faq_or_cache,
    handle_chat,
)
import db


class TestComplianceAndAllergens(unittest.TestCase):

    def test_catalog_consumer_law_compliance(self):
        """Verifie que chaque coffret possede les mentions obligatoires du Code de la consommation."""
        for item in CATALOG:
            self.assertIn("prix_ttc", item, f"Le coffret {item.get('id')} doit avoir prix_ttc")
            self.assertIn("poids_net_g", item, f"Le coffret {item.get('id')} doit avoir poids_net_g")
            self.assertIn("prix_au_kilo_ttc", item, f"Le coffret {item.get('id')} doit avoir prix_au_kilo_ttc")
            self.assertIn("ingredients", item, f"Le coffret {item.get('id')} doit avoir ingredients")
            self.assertIn("allergenes", item, f"Le coffret {item.get('id')} doit avoir allergenes")
            self.assertIsInstance(item["prix_ttc"], (int, float))
            self.assertIsInstance(item["poids_net_g"], (int, float))
            self.assertTrue(item["prix_au_kilo_ttc"].endswith("€/kg"))

    def test_extract_allergens_synonyms(self):
        """Verifie que les synonymes d'allergenes sont correctement normalises."""
        detected = extract_allergens("noisettes et amandes")
        self.assertIn("fruits à coque", detected)

        detected_gluten = extract_allergens("intolérance au blé et speculoos")
        self.assertIn("gluten", detected_gluten)

        detected_lait = extract_allergens("lactose")
        self.assertIn("lait", detected_lait)

    def test_filter_catalog_fruits_a_coque(self):
        """Verifie que les coffrets contenant des fruits a coque sont strictement elimines."""
        safe, excluded = filter_catalog_by_allergies(CATALOG, "noisettes")
        excluded_ids = [item["id"] for item in excluded]
        safe_ids = [item["id"] for item in safe]

        # C01 (praline noisette), C05 (amande), C06, C07 contiennent des fruits a coque
        self.assertIn("C01", excluded_ids)
        self.assertIn("C05", excluded_ids)
        self.assertIn("C06", excluded_ids)
        self.assertIn("C07", excluded_ids)

        # C02 (Ch'ti Noir) et C04 (Sans Noix) doivent rester dans la selection sure
        self.assertIn("C02", safe_ids)
        self.assertIn("C04", safe_ids)

    def test_filter_catalog_gluten(self):
        """Verifie l'exclusion stricte du gluten."""
        safe, excluded = filter_catalog_by_allergies(CATALOG, "gluten")
        excluded_ids = [item["id"] for item in excluded]
        safe_ids = [item["id"] for item in safe]

        # C03 (gaufre / speculoos), C06, C07 ont du gluten
        self.assertIn("C03", excluded_ids)
        self.assertIn("C06", excluded_ids)
        self.assertIn("C07", excluded_ids)

        # C01, C02, C04, C05 n'ont pas de gluten declare
        self.assertIn("C01", safe_ids)
        self.assertIn("C02", safe_ids)
        self.assertIn("C04", safe_ids)
        self.assertIn("C05", safe_ids)

    def test_zero_match_returns_safe_refusal(self):
        """Verifie qu'une combinaison d'allergenes sans produit sur renvoie un refus immediat."""
        session_id = f"test-safety-{time.time()}"
        db.save_customer(session_id, "ClientTest", "", "lait, fruits à coque, soja", "")

        result = handle_chat(session_id, "Quel chocolat puis-je manger ?")
        reply = result["reply"]

        self.assertIn("Information de sécurité alimentaire", reply)
        self.assertIn("03 20 00 00 00", reply)
        db.delete_session(session_id)

    def test_static_faq_instant_reply(self):
        """Verifie les reponses instantanees sans token pour la FAQ reglementaire et logistique."""
        session_id = f"test-faq-{time.time()}"

        res_horaires = check_faq_or_cache(session_id, "Quels sont vos horaires ?")
        self.assertIsNotNone(res_horaires)
        self.assertIn("9h30 à 19h00", res_horaires)

        res_retractation = check_faq_or_cache(session_id, "Puis-je exercer mon droit de retractation ?")
        self.assertIsNotNone(res_retractation)
        self.assertIn("L. 221-28", res_retractation)

        res_boutique = check_faq_or_cache(session_id, "Avez-vous une boutique à Lille ?")
        self.assertIsNotNone(res_boutique)
        self.assertIn("12 rue Esquermoise", res_boutique)

    def test_purge_old_sessions(self):
        """Verifie que la purge automatique supprime les sessions depassant la duree de conservation."""
        old_session = "old-session-to-purge"
        db.conn.execute("INSERT OR REPLACE INTO customers VALUES (?,?,?,?,?,?)",
                        (old_session, "OldUser", "old@test.fr", "", "", time.time() - 40 * 86400))
        db.conn.commit()

        # Verifie la presence avant purge
        self.assertTrue(bool(db.get_customer(old_session)))

        # Execution de la purge (seuil 30 jours)
        db.purge_old_sessions(max_age_seconds=30 * 86400)

        # Verifie l'effacement apres purge
        self.assertFalse(bool(db.get_customer(old_session)))


if __name__ == "__main__":
    unittest.main()
