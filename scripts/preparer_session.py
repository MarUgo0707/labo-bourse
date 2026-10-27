"""Préparation de la séance du matin (avant Claude).

- décide s'il y a séance aujourd'hui (période d'étude, bourses ouvertes, séance déjà faite) ;
- vérifie le verrou des règles ;
- écrit data/contexte/<date>.json : indices et devises à la clôture de la veille, séances ratées, etc.

Usage : python scripts/preparer_session.py [--date AAAA-MM-JJ] [--test]
"""
from __future__ import annotations

import argparse
import sys

from commun import (DATA, MARCHES, NOMS_MARCHES, ajouter_texte, cours, dates_disponibles, derniere_cloture, dernier_etat,
                    ecrire_json, etude, iso_utc, jours_etude, maintenant_utc, marche_ouvert, numero_jour, ouverture_utc,
                    plus_jours, portefeuilles, sortie_github, verifier_verrou, aujourdhui)

INDICES = {
    "^SSMI": "SMI (Suisse)",
    "^GSPC": "S&P 500 (États-Unis)",
    "^IXIC": "Nasdaq (États-Unis)",
    "^STOXX50E": "Euro Stoxx 50 (zone euro)",
    "^GDAXI": "DAX (Allemagne)",
    "^VIX": "VIX (indice de la peur)",
    "GC=F": "Or (once, USD)",
    "BTC-USD": "Bitcoin (USD)",
    "USDCHF=X": "Dollar → franc",
    "EURCHF=X": "Euro → franc",
}


def resume_indices(date: str) -> dict:
    resultat = {}
    for ticker, nom in INDICES.items():
        try:
            donnees = cours(ticker, plus_jours(date, -12), plus_jours(date, -1))
        except Exception as e:  # une source qui manque ne doit pas bloquer la séance
            resultat[ticker] = {"nom": nom, "erreur": str(e)}
            continue
        barres = donnees["barres"]
        d1, c1 = derniere_cloture(barres, date, strict=True)
        if c1 is None:
            resultat[ticker] = {"nom": nom, "erreur": "aucune donnée"}
            continue
        d0, c0 = derniere_cloture(barres, d1, strict=True)
        resultat[ticker] = {
            "nom": nom,
            "date": d1,
            "cloture": round(c1, 4),
            "variation_pct": round((c1 / c0 - 1) * 100, 2) if c0 else None,
        }
    return resultat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=aujourdhui())
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    date, test = args.date, args.test
    config = etude()

    def stop(raison: str, code: int = 0) -> int:
        print(raison)
        sortie_github(lancer=False, date=date, raison=raison)
        return code

    erreurs = verifier_verrou(date, test)
    if erreurs:
        for e in erreurs:
            print("VERROU :", e, file=sys.stderr)
        return stop("Verrou des règles rompu : séance refusée.", 1)

    jours = jours_etude(config)
    if not test:
        if date < config["date_debut"] or date > config["date_fin"]:
            return stop(f"{date} est hors de la période d'étude ({config['date_debut']} → {config['date_fin']}).")
        if date not in jours:
            if dt_ouvrable(date):
                ajouter_texte(DATA / "journal" / f"{date}.md",
                              f"# Séance du {date}\n\nToutes les bourses suivies sont fermées aujourd'hui : pas de séance.\n")
            return stop(f"{date} n'est pas un jour de séance (week-end ou toutes les bourses fermées).")
        if (DATA / "decisions" / f"{date}.json").exists():
            return stop("La séance de ce jour a déjà eu lieu : on ne décide jamais deux fois.")

    maintenant = maintenant_utc()
    marches = {}
    for m in MARCHES:
        ouvert = marche_ouvert(date, m, config)
        deja = ouvert and maintenant >= ouverture_utc(date, m, config)
        marches[m] = {
            "nom": NOMS_MARCHES[m],
            "ouvert_aujourdhui": ouvert,
            "ouverture_heure_zurich": config["ouvertures_heure_zurich"][m],
            "deja_ouvert_au_moment_de_la_session": deja,
        }

    seances_ratees = [d for d in jours if d < date and not (DATA / "decisions" / f"{d}.json").exists()]
    clotures_manquantes = [d for d in jours if d < date and not (DATA / "etat" / f"{d}.json").exists()]
    etat = dernier_etat(date, config, test)

    contexte = {
        "date": date,
        "mode_test": test,
        "genere_le": iso_utc(maintenant),
        "jour": numero_jour(date, config),
        "nb_jours": len(jours),
        "dernier_jour": date == config["date_fin"],
        "marches": marches,
        "indices_veille": resume_indices(date),
        "etat_de_reference": etat.get("date") or "état initial (aucune clôture encore)",
        "seances_ratees": seances_ratees,
        "clotures_manquantes": clotures_manquantes,
        "portefeuilles_ia": [p["id"] for p in portefeuilles() if p["pilote"] == "ia"],
    }
    ecrire_json(DATA / "contexte" / f"{date}.json", contexte)
    sortie_github(lancer=True, date=date, raison="séance prévue", modele=config["modele_claude"],
                  max_tours=config["max_tours_claude"], jour=contexte["jour"] or 0, nb_jours=len(jours))
    return 0


def dt_ouvrable(date: str) -> bool:
    import datetime as dt
    return dt.date.fromisoformat(date).weekday() < 5


if __name__ == "__main__":
    sys.exit(main())
