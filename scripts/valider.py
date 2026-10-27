"""Validateur des ordres du matin (sans IA).

Lit data/decisions/<date>.json (Claude) et data/singe/<date>.json (script), vérifie chaque
ordre et écrit data/ordres/<date>.json (acceptés + rejetés avec motif). Un ordre fautif est
rejeté et noté dans le journal, sans bloquer les autres.

Usage : python scripts/valider.py --date AAAA-MM-JJ [--test]
"""
from __future__ import annotations

import argparse
import re
import sys

from commun import (DATA, MOTS_LEVIER, ajouter_texte, arrondi, aujourdhui, calcul_frais, derniere_cloture, dernier_etat,
                    ecrire_json, etude, infos_titre, iso_utc, lire_json, marche_du_ticker, marche_ouvert, portefeuilles,
                    taux_chf, verifier_verrou)

ACTIONS = {"acheter": "achat", "renforcer": "achat", "achat": "achat",
           "vendre": "vente", "alleger": "vente", "alléger": "vente", "vente": "vente"}
FORMAT_TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
CONFIANCES = {"faible", "moyen", "élevé", "eleve"}


class Rejet(Exception):
    pass


def lire_decisions(date: str) -> tuple[dict, str]:
    chemin = DATA / "decisions" / f"{date}.json"
    if not chemin.exists():
        return {}, "absente"
    try:
        dec = lire_json(chemin)
        if not isinstance(dec, dict) or not isinstance(dec.get("portefeuilles"), dict):
            return {}, "invalide"
        return dec, "ok"
    except Exception:
        return {}, "invalide"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=aujourdhui())
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    date, config = args.date, etude()

    erreurs_verrou = verifier_verrou(date, args.test)
    if erreurs_verrou:
        print("VERROU ROMPU :", *erreurs_verrou, sep="\n  ", file=sys.stderr)
        return 1

    decisions, session_ia = lire_decisions(date)
    singe = lire_json(DATA / "singe" / f"{date}.json", {"ordres": []})
    etat = dernier_etat(date, config, args.test)
    secteurs = set(config["secteurs"])
    mini = config["montant_min_ordre_chf"]
    sortie = []

    # Prix estimés = dernière clôture connue avant la séance (aucune information du jour).
    cache_infos: dict[str, dict | None] = {}

    def infos(ticker):
        if ticker not in cache_infos:
            cache_infos[ticker] = infos_titre(ticker, date)
        return cache_infos[ticker]

    for p in portefeuilles():
        pid, c = p["id"], p["contraintes"]
        if p["pilote"] == "script":
            brutes = singe.get("ordres", [])
        else:
            brutes = ((decisions.get("portefeuilles") or {}).get(pid) or {}).get("ordres") or []
        e = etat["portefeuilles"][pid]
        cash = e["cash_chf"]
        valeurs = {pos["ticker"]: pos["valeur_chf"] for pos in e["positions"]}
        total = e["valeur_totale_chf"]

        for rang, o in enumerate(brutes, 1):
            o = dict(o) if isinstance(o, dict) else {"brut": o}
            ticker = str(o.get("ticker", "")).strip().upper()
            ligne = {
                "portefeuille": pid,
                "auteur": "script" if p["pilote"] == "script" else "claude",
                "action": o.get("action"),
                "sens": ACTIONS.get(str(o.get("action", "")).lower()),
                "ticker": ticker,
                "nom": o.get("nom") or ticker,
                "secteur": o.get("secteur") if o.get("secteur") in secteurs else "Autre",
                "pays": o.get("pays") or "?",
                "montant_chf": o.get("montant_chf"),
                "tout": bool(o.get("tout")),
                "raison": o.get("raison", ""),
                "confiance": o.get("confiance", ""),
                "horizon": o.get("horizon", ""),
                "marche": marche_du_ticker(ticker),
            }
            try:
                if rang > config["max_ordres_par_session"]:
                    raise Rejet(f"plus de {config['max_ordres_par_session']} ordres pour ce portefeuille aujourd'hui")
                if ligne["sens"] is None:
                    raise Rejet(f"action inconnue « {o.get('action')} » (acheter, renforcer, vendre ou alléger)")
                if not FORMAT_TICKER.match(ticker):
                    raise Rejet(f"ticker « {ticker} » au format invalide (options, indices, devises et futures interdits)")
                if ligne["marche"] == "INCONNU":
                    raise Rejet("place boursière non couverte par l'étude (SIX, Europe, Londres, États-Unis seulement)")
                if not marche_ouvert(date, ligne["marche"], config):
                    raise Rejet("cette bourse est fermée aujourd'hui")
                if "tickers_autorises" in c and ticker not in c["tickers_autorises"]:
                    raise Rejet(f"hors de la liste autorisée pour ce portefeuille ({', '.join(c['tickers_autorises'])})")
                if "suffixes_autorises" in c and not any(ticker.endswith(s) for s in c["suffixes_autorises"]):
                    raise Rejet(f"seuls les titres {', '.join(c['suffixes_autorises'])} sont autorisés")
                if ligne["sens"] == "achat" and "secteurs_autorises" in c and ligne["secteur"] not in c["secteurs_autorises"]:
                    raise Rejet(f"secteur « {ligne['secteur']} » hors stratégie ({', '.join(c['secteurs_autorises'])})")

                info = infos(ticker)
                if info is None:
                    raise Rejet("ticker introuvable sur Yahoo Finance ou sans cotation récente")
                if ligne["sens"] == "achat":
                    if info["type"] not in c.get("types_autorises", ["EQUITY", "ETF"]):
                        raise Rejet(f"type d'instrument « {info['type']} » non autorisé ici")
                    if MOTS_LEVIER.search(info["nom_yahoo"] or ""):
                        raise Rejet(f"produit à levier ou inversé interdit ({info['nom_yahoo']})")
                d_prix, prix = derniere_cloture(info["barres"], date, strict=True)
                taux = taux_chf(info["devise"], date, strict=True)
                if prix is None or taux is None:
                    raise Rejet("cours ou taux de change de la veille introuvable")
                ligne.update({"devise": info["devise"], "prix_estime": prix, "date_prix_estime": d_prix,
                              "taux_estime": round(taux, 6)})

                if ligne["sens"] == "vente":
                    if ticker not in valeurs:
                        raise Rejet("vente impossible : le portefeuille ne détient pas ce titre (pas de vente à découvert)")
                    montant = valeurs[ticker] if ligne["tout"] else float(ligne["montant_chf"] or 0)
                    if montant <= 0:
                        raise Rejet("montant de vente manquant ou nul")
                    if montant >= valeurs[ticker] * 0.98:
                        ligne["tout"], montant = True, valeurs[ticker]
                    frais = calcul_frais(montant, info["devise"], config)
                    valeurs[ticker] -= montant
                    if valeurs[ticker] <= 0.01:
                        del valeurs[ticker]
                    cash += montant - frais
                    total -= frais
                else:
                    try:
                        montant = float(ligne["montant_chf"])
                    except (TypeError, ValueError):
                        raise Rejet("montant d'achat manquant")
                    if montant < mini:
                        raise Rejet(f"montant inférieur au minimum de {mini} CHF")
                    frais = calcul_frais(montant, info["devise"], config)
                    if montant + frais > cash + 0.01:
                        raise Rejet(f"cash insuffisant : {montant:.2f} + {frais:.2f} CHF de frais > {cash:.2f} CHF disponibles")
                    nouvelles = set(valeurs) | {ticker}
                    if len(nouvelles) > c["max_positions"]:
                        raise Rejet(f"dépasserait {c['max_positions']} positions")
                    part = (valeurs.get(ticker, 0) + montant) / max(total - frais, 1) * 100
                    if part > c["max_pct_position"] + 2:
                        raise Rejet(f"la position pèserait {part:.0f} % du portefeuille (maximum {c['max_pct_position']} %)")
                    cash -= montant + frais
                    total -= frais
                    valeurs[ticker] = valeurs.get(ticker, 0) + montant
                ligne.update({"montant_chf": arrondi(montant), "frais_estimes_chf": frais, "statut": "accepté", "motif": ""})
            except Rejet as r:
                ligne.update({"statut": "rejeté", "motif": str(r)})
            sortie.append(ligne)

    rejetes = [o for o in sortie if o["statut"] == "rejeté"]
    ecrire_json(DATA / "ordres" / f"{date}.json", {
        "date": date,
        "mode_test": args.test,
        "horodatage_validation": iso_utc(),
        "session_ia": session_ia,
        "ordres": sortie,
        "resume": {"acceptes": len(sortie) - len(rejetes), "rejetes": len(rejetes)},
    })

    journal = DATA / "journal" / f"{date}.md"
    texte = ""
    if session_ia != "ok":
        if not journal.exists():
            texte += f"# Séance du {date}\n\n"
        raison = "n'a pas eu lieu ou n'a rien produit" if session_ia == "absente" else "a produit un fichier illisible"
        texte += f"\n> ⚠️ La séance IA {raison}. Aucune décision IA aujourd'hui ; seul le Singe a joué.\n"
    texte += "\n## Contrôle automatique des ordres\n\n"
    texte += f"{len(sortie) - len(rejetes)} ordre(s) accepté(s), {len(rejetes)} rejeté(s).\n"
    for o in rejetes:
        texte += f"\n- ❌ **{o['portefeuille']}** — {o['action']} {o['ticker']} : {o['motif']}."
    ajouter_texte(journal, texte + "\n")
    print(f"Validation : {len(sortie) - len(rejetes)} accepté(s), {len(rejetes)} rejeté(s). Séance IA : {session_ia}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
