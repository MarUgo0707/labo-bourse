"""Le Singe : décisions 100 % aléatoires, sans IA, rejouables (graine fixe + date).

Écrit data/singe/<date>.json. Usage : python scripts/singe.py --date AAAA-MM-JJ [--test]
"""
from __future__ import annotations

import argparse
import random
import sys

from commun import DATA, aujourdhui, dernier_etat, ecrire_json, etude, iso_utc, marche_du_ticker, marche_ouvert, portefeuilles_par_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=aujourdhui())
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    config = etude()
    regles = config["singe"]
    singe = portefeuilles_par_id()["singe"]
    rng = random.Random(f"{regles['graine']}-{args.date}")

    etat = dernier_etat(args.date, config, args.test)["portefeuilles"]["singe"]
    cash = etat["cash_chf"]
    detenus = [p["ticker"] for p in etat["positions"]]
    univers = [t for t in singe["univers"] if marche_ouvert(args.date, marche_du_ticker(t["ticker"]), config)]
    mini = config["montant_min_ordre_chf"]
    ordres = []

    def achat(titre, montant, raison):
        ordres.append({"action": "acheter", "ticker": titre["ticker"], "nom": titre["nom"], "secteur": titre["secteur"],
                       "pays": titre["pays"], "montant_chf": round(montant, 2), "raison": raison,
                       "confiance": "faible", "horizon": "aucun (hasard)"})

    premier_jour = not detenus and etat["nb_ordres_cumules"] == 0
    if premier_jour:
        choix = rng.sample(univers, 3)
        parts = [rng.uniform(0.2, 0.4) for _ in choix]
        total = sum(parts)
        budget = cash * 0.95
        for titre, part in zip(choix, parts):
            achat(titre, budget * part / total, "Tirage au sort du premier jour.")
    else:
        if detenus and rng.random() < regles["proba_vente"]:
            ticker = rng.choice(detenus)
            pos = next(p for p in etat["positions"] if p["ticker"] == ticker)
            if marche_ouvert(args.date, marche_du_ticker(ticker), config):
                ordres.append({"action": "vendre", "ticker": ticker, "nom": pos["nom"], "secteur": pos["secteur"],
                               "pays": pos["pays"], "tout": True, "montant_chf": round(pos["valeur_chf"], 2),
                               "raison": "Tirage au sort : vente de toute la position.",
                               "confiance": "faible", "horizon": "aucun (hasard)"})
                detenus.remove(ticker)
                cash += pos["valeur_chf"]
        if rng.random() < regles["proba_achat"] and len(detenus) < regles["max_positions"]:
            candidats = [t for t in univers if t["ticker"] not in detenus]
            montant = cash * rng.uniform(0.3, 0.6) - 2
            if candidats and montant >= mini:
                achat(rng.choice(candidats), montant, "Tirage au sort : achat d'un titre au hasard.")

    ecrire_json(DATA / "singe" / f"{args.date}.json", {
        "date": args.date,
        "genere_le": iso_utc(),
        "graine": f"{regles['graine']}-{args.date}",
        "mode_test": args.test,
        "ordres": ordres,
    })
    print(f"Singe : {len(ordres)} ordre(s) tiré(s) au sort.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
