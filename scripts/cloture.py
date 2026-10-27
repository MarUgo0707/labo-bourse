"""Clôture du soir (pur Python, sans IA).

Pour chaque jour de séance sans état calculé (jusqu'à la date donnée) :
  1. exécute les ordres acceptés au prix d'ouverture réel du jour + slippage + frais ;
  2. valorise chaque portefeuille au prix de clôture, convertit en CHF au taux du jour ;
  3. écrit data/marche/<date>.json et data/etat/<date>.json.

Usage : python scripts/cloture.py [--date AAAA-MM-JJ] [--test]
"""
from __future__ import annotations

import argparse
import copy
import sys

from commun import (DATA, arrondi, aujourdhui, calcul_frais, cours, derniere_cloture, dernier_etat, ecrire_json, etude,
                    iso_utc, jours_etude, lire_iso, lire_json, marche_du_ticker, numero_jour, ouverture_utc, plus_jours,
                    portefeuilles, taux_chf)


def barre_du_jour(ticker: str, date: str) -> tuple[dict, str]:
    donnees = cours(ticker, plus_jours(date, -10), date)
    return donnees["barres"], donnees["devise"]


def executer(date: str, etat_prec: dict, config: dict, test: bool) -> dict:
    ordres_jour = lire_json(DATA / "ordres" / f"{date}.json", {"ordres": [], "horodatage_validation": None})
    valide_le = ordres_jour.get("horodatage_validation")
    slip = config["slippage_pct"] / 100
    etat = copy.deepcopy(etat_prec["portefeuilles"])
    for pid in etat:  # positions indexées par ticker pendant le calcul
        etat[pid]["positions"] = {p["ticker"]: p for p in etat[pid]["positions"]}
    transactions, prix_marche = [], {}

    def prix(ticker):
        if ticker not in prix_marche:
            barres, devise = barre_du_jour(ticker, date)
            b = barres.get(date)
            d_cl, cl = derniere_cloture(barres, date)
            prix_marche[ticker] = {"devise": devise, "ouverture": b["ouverture"] if b else None,
                                   "cloture": cl, "date_cloture": d_cl, "a_cote_ce_jour": b is not None}
        return prix_marche[ticker]

    acceptes = [o for o in ordres_jour["ordres"] if o["statut"] == "accepté"]
    # Les ventes d'abord (elles libèrent du cash), puis les achats, dans l'ordre donné.
    acceptes.sort(key=lambda o: 0 if o["sens"] == "vente" else 1)

    for o in acceptes:
        e = etat[o["portefeuille"]]
        t = {k: o.get(k) for k in ("portefeuille", "auteur", "action", "sens", "ticker", "nom", "secteur", "pays",
                                   "marche", "raison", "confiance", "horizon")}
        t.update({"date": date, "montant_demande_chf": o["montant_chf"]})
        transactions.append(t)
        p = prix(o["ticker"])
        if not test and valide_le and lire_iso(valide_le) > ouverture_utc(date, o["marche"], config):
            t.update(statut="annulé", motif="décision validée après l'ouverture de cette bourse (règle anti-triche)")
            continue
        if not p["a_cote_ce_jour"] or not p["ouverture"]:
            t.update(statut="annulé", motif="le titre n'a pas coté ce jour-là")
            continue
        taux = taux_chf(p["devise"], date)
        if taux is None:
            t.update(statut="annulé", motif="taux de change du jour introuvable")
            continue
        bilan = e["bilan_titres"].setdefault(o["ticker"], {
            "nom": o["nom"], "secteur": o["secteur"], "pays": o["pays"], "investi_chf": 0.0, "recupere_chf": 0.0,
            "frais_chf": 0.0, "valeur_actuelle_chf": 0.0, "resultat_chf": 0.0, "nb_ordres": 0})

        if o["sens"] == "achat":
            px = p["ouverture"] * (1 + slip)
            montant = float(o["montant_chf"])
            frais = calcul_frais(montant, p["devise"], config)
            if montant + frais > e["cash_chf"]:
                f = config["frais"]
                pct = (f["commission_pct"] + (f["change_pct"] if p["devise"] != "CHF" else 0)) / 100
                montant = (e["cash_chf"] - f["fixe_par_ordre_chf"]) / (1 + pct) - 0.01
                if montant < 1:
                    t.update(statut="annulé", motif="cash insuffisant au moment de l'exécution")
                    continue
                frais = calcul_frais(montant, p["devise"], config)
                t["note"] = "montant réduit au cash disponible"
            quantite = montant / (px * taux)
            e["cash_chf"] -= montant + frais
            pos = e["positions"].setdefault(o["ticker"], {
                "ticker": o["ticker"], "nom": o["nom"], "secteur": o["secteur"], "pays": o["pays"],
                "marche": o["marche"], "devise": p["devise"], "quantite": 0.0, "cout_chf": 0.0,
                "date_achat": date})
            pos["quantite"] += quantite
            pos["cout_chf"] += montant + frais
            bilan["investi_chf"] += montant + frais
            t.update(montant_chf=arrondi(montant), quantite=round(quantite, 6), cash_chf=arrondi(-(montant + frais)))
        else:
            pos = e["positions"].get(o["ticker"])
            if not pos:
                t.update(statut="annulé", motif="position déjà vendue")
                continue
            px = p["ouverture"] * (1 - slip)
            valeur_dispo = pos["quantite"] * px * taux
            quantite = pos["quantite"] if o.get("tout") or o["montant_chf"] >= valeur_dispo * 0.98 \
                else float(o["montant_chf"]) / (px * taux)
            brut = quantite * px * taux
            frais = calcul_frais(brut, p["devise"], config)
            net = brut - frais
            if net <= 0:
                t.update(statut="annulé", motif="montant trop faible : les frais dépasseraient la vente")
                continue
            cout_vendu = pos["cout_chf"] * quantite / pos["quantite"]
            pos["quantite"] -= quantite
            pos["cout_chf"] -= cout_vendu
            if pos["quantite"] <= 1e-9:
                del e["positions"][o["ticker"]]
            e["cash_chf"] += net
            bilan["recupere_chf"] += net
            t.update(montant_chf=arrondi(brut), quantite=round(quantite, 6), cash_chf=arrondi(net),
                     resultat_realise_chf=arrondi(net - cout_vendu))
        e["frais_cumules_chf"] += frais
        e["nb_ordres_cumules"] += 1
        bilan["frais_chf"] += frais
        bilan["nb_ordres"] += 1
        t.update(statut="exécuté", motif="", prix_execution=round(px, 6), prix_ouverture=p["ouverture"],
                 devise=p["devise"], taux_chf=round(taux, 6), frais_chf=arrondi(frais))

    # Valorisation au prix de clôture.
    taux_jour = {}
    for pid, e in etat.items():
        positions = []
        for tk, pos in e["positions"].items():
            p = prix(tk)
            taux = taux_chf(pos["devise"], date) or pos.get("taux_chf")
            taux_jour[pos["devise"]] = taux
            cl = p["cloture"] if p["cloture"] else pos.get("prix_cloture")
            valeur = pos["quantite"] * cl * taux
            pos.update(prix_cloture=round(cl, 6), date_prix=p["date_cloture"] or pos.get("date_prix"),
                       taux_chf=round(taux, 6), valeur_chf=arrondi(valeur),
                       gain_chf=arrondi(valeur - pos["cout_chf"]),
                       gain_pct=arrondi((valeur / pos["cout_chf"] - 1) * 100) if pos["cout_chf"] else 0.0,
                       quantite=round(pos["quantite"], 8), cout_chf=arrondi(pos["cout_chf"], 4))
            positions.append(pos)
        valeur_pos = sum(p["valeur_chf"] for p in positions)
        total = e["cash_chf"] + valeur_pos
        for pos in positions:
            pos["part_pct"] = arrondi(pos["valeur_chf"] / total * 100) if total else 0.0
        prec_total = etat_prec["portefeuilles"][pid]["valeur_totale_chf"]
        cap = config["capital_initial_chf"]
        for tk, b in e["bilan_titres"].items():
            b["valeur_actuelle_chf"] = next((p["valeur_chf"] for p in positions if p["ticker"] == tk), 0.0)
            b["resultat_chf"] = b["recupere_chf"] + b["valeur_actuelle_chf"] - b["investi_chf"]
            for k in ("investi_chf", "recupere_chf", "frais_chf", "valeur_actuelle_chf", "resultat_chf"):
                b[k] = arrondi(b[k], 4)
        e.update(
            cash_chf=arrondi(e["cash_chf"], 4),
            positions=sorted(positions, key=lambda p: -p["valeur_chf"]),
            valeur_positions_chf=arrondi(valeur_pos),
            valeur_totale_chf=arrondi(total, 4),
            variation_jour_chf=arrondi(total - prec_total),
            variation_jour_pct=arrondi((total / prec_total - 1) * 100) if prec_total else 0.0,
            gain_total_chf=arrondi(total - cap),
            gain_total_pct=arrondi((total / cap - 1) * 100),
            frais_cumules_chf=arrondi(e["frais_cumules_chf"], 4),
        )

    for devise in ("USD", "EUR", "GBP"):
        taux_jour.setdefault(devise, taux_chf(devise, date))
    ecrire_json(DATA / "marche" / f"{date}.json", {
        "date": date, "genere_le": iso_utc(), "mode_test": test,
        "taux_change_chf": {k: round(v, 6) for k, v in sorted(taux_jour.items()) if v},
        "prix": dict(sorted(prix_marche.items())),
    })
    return {
        "date": date,
        "jour": numero_jour(date, config),
        "genere_le": iso_utc(),
        "mode_test": test,
        "session_ia": lire_json(DATA / "ordres" / f"{date}.json", {}).get("session_ia", "absente"),
        "taux_change_chf": {k: round(v, 6) for k, v in sorted(taux_jour.items()) if v},
        "portefeuilles": etat,
        "transactions": transactions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=aujourdhui())
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    config = etude()

    if args.test:
        a_traiter = [args.date]
    else:
        a_traiter = [d for d in jours_etude(config) if d <= args.date and not (DATA / "etat" / f"{d}.json").exists()]
    if not a_traiter:
        print("Rien à clôturer.")
        return 0
    for date in a_traiter:
        print(f"Clôture du {date}…")
        etat = executer(date, dernier_etat(date, config, args.test), config, args.test)
        ecrire_json(DATA / "etat" / f"{date}.json", etat)
        ex = sum(1 for t in etat["transactions"] if t["statut"] == "exécuté")
        print(f"  {ex} ordre(s) exécuté(s), {len(etat['transactions']) - ex} annulé(s).")
        for pid, e in etat["portefeuilles"].items():
            print(f"  {pid:12s} {e['valeur_totale_chf']:8.2f} CHF ({e['gain_total_pct']:+.2f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
