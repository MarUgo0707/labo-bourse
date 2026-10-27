"""Fausse séance Claude, pour tester la chaîne SANS IA (vérification locale ou CI).

Écrit data/decisions/<date>.json et data/journal/<date>.md avec quelques ordres types,
dont des ordres volontairement fautifs pour vérifier que le validateur les rejette.
Usage : python scripts/simuler_decisions.py --date AAAA-MM-JJ
"""
from __future__ import annotations

import argparse
import sys

from commun import DATA, aujourdhui, ecrire_json, portefeuilles


def ordre(action, ticker, nom, secteur, pays, montant, raison):
    return {"action": action, "ticker": ticker, "nom": nom, "secteur": secteur, "pays": pays, "montant_chf": montant,
            "raison": raison, "confiance": "moyen", "horizon": "1 semaine"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=aujourdhui())
    args = parser.parse_args()
    plans = {
        "patient": [ordre("acheter", "VT", "Vanguard Total World", "ETF diversifié", "Monde", 150, "Test : ETF monde."),
                    ordre("acheter", "CHSPI.SW", "iShares Core SPI", "ETF diversifié", "Suisse", 40, "Test : ETF suisse.")],
        "journaliste": [ordre("acheter", "AAPL", "Apple", "Technologie", "États-Unis", 60, "Test."),
                        ordre("vendre", "MSFT", "Microsoft", "Technologie", "États-Unis", 20, "Test : vente à découvert, doit être rejetée.")],
        "risque": [ordre("acheter", "COIN", "Coinbase", "Crypto", "États-Unis", 100, "Test."),
                   ordre("acheter", "TQQQ", "ProShares UltraPro QQQ", "Technologie", "États-Unis", 50, "Test : levier, doit être rejeté.")],
        "ia": [ordre("acheter", "NVDA", "Nvidia", "Semi-conducteurs", "États-Unis", 70, "Test."),
               ordre("acheter", "ASML.AS", "ASML", "Semi-conducteurs", "Pays-Bas", 60, "Test.")],
        "suisse": [ordre("acheter", "NESN.SW", "Nestlé", "Consommation de base", "Suisse", 60, "Test."),
                   ordre("acheter", "AAPL", "Apple", "Technologie", "États-Unis", 30, "Test : hors SIX, doit être rejeté.")],
        "contrarien": [ordre("acheter", "INVALIDEXYZ", "Inconnu", "Technologie", "?", 30, "Test : ticker inexistant.")],
        "momentum": [ordre("acheter", "SAP.DE", "SAP", "Technologie", "Allemagne", 300, "Test : cash insuffisant.")],
        "defensif": [ordre("acheter", "GLD", "SPDR Gold Shares", "Or et métaux précieux", "États-Unis", 60, "Test."),
                     ordre("acheter", "KO", "Coca-Cola", "Consommation de base", "États-Unis", 50, "Test.")],
    }
    dec = {
        "date": args.date,
        "heure_session": "08:00",
        "simulation": True,
        "brief_marche": "Séance simulée pour tester la chaîne (aucune analyse réelle).",
        "points_cles": ["Séance de test sans IA.", "Ordres types, dont certains volontairement fautifs.", "Rien n'est à interpréter."],
        "sources": [],
        "portefeuilles": {
            p["id"]: {"decision": "agir" if plans.get(p["id"]) else "rien", "resume": "Test automatique.",
                      "ordres": plans.get(p["id"], []),
                      "prediction": {"texte": "Test : Apple va monter cette semaine.", "ticker": "AAPL", "direction": "hausse", "horizon_jours": 5}}
            for p in portefeuilles() if p["pilote"] == "ia"
        },
        "incertitudes": ["Données simulées."],
    }
    ecrire_json(DATA / "decisions" / f"{args.date}.json", dec)
    (DATA / "journal" / f"{args.date}.md").write_text(
        f"# Séance du {args.date} (simulation)\n\nCeci est une séance simulée pour tester la chaîne, sans IA.\n",
        encoding="utf-8", newline="\n")
    print("Décisions simulées écrites.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
