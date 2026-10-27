"""Indicateurs d'étude et rapport final (pur Python, sans IA).

Écrit data/indicateurs.json, data/rapport-final.json et data/rapport-final.md.
Tant que la dernière séance n'est pas clôturée, le rapport est marqué « provisoire ».

Usage : python scripts/rapport.py [--test] [--sans-predictions]
"""
from __future__ import annotations

import argparse
import statistics
import sys

from commun import (DATA, arrondi, cours, dates_disponibles, derniere_cloture, ecrire_json, etude, iso_utc, jours_etude,
                    lire_json, plus_jours, portefeuilles)

EXPLICATIONS = {
    "performance_pct": "Combien le portefeuille a gagné ou perdu depuis le début, en pourcentage des 200 CHF.",
    "volatilite_pct": "De combien la valeur bouge en moyenne d'un jour à l'autre : plus c'est haut, plus c'est agité.",
    "pire_chute_pct": "La plus grosse baisse entre un sommet et le creux qui a suivi (max drawdown).",
    "ratio_rendement_risque": "Le gain moyen par jour divisé par l'agitation : plus c'est haut, mieux le risque a été payé.",
    "taux_gagnants_pct": "Parmi les titres achetés, la part qui rapporte de l'argent (frais compris).",
    "nb_ordres": "Nombre d'ordres exécutés : mesure à quel point la stratégie bouge (rotation).",
    "poids_frais_pct": "Les frais payés, en pourcentage du capital de départ.",
    "ecart_patient_pts": "Différence de performance avec le Patient (la référence passive), en points de pourcentage.",
    "ecart_singe_pts": "Différence de performance avec le Singe (le hasard), en points de pourcentage.",
}


def charger_etats(test: bool, config: dict) -> list[dict]:
    dates = dates_disponibles("etat")
    if not test:
        dates = [d for d in dates if config["date_debut"] <= d <= config["date_fin"]]
    return [lire_json(DATA / "etat" / f"{d}.json") for d in dates]


def indicateurs(etats: list[dict], config: dict) -> dict:
    cap = config["capital_initial_chf"]
    resultat = {}
    for p in portefeuilles():
        pid = p["id"]
        serie = [cap] + [e["portefeuilles"][pid]["valeur_totale_chf"] for e in etats]
        rend = [serie[i] / serie[i - 1] - 1 for i in range(1, len(serie))]
        pic, pire = serie[0], 0.0
        for v in serie:
            pic = max(pic, v)
            pire = min(pire, v / pic - 1)
        vol = statistics.pstdev(rend) if len(rend) >= 2 else 0.0
        moy = statistics.fmean(rend) if rend else 0.0
        dernier = etats[-1]["portefeuilles"][pid] if etats else None
        bilan = dernier["bilan_titres"] if dernier else {}
        gagnants = sum(1 for b in bilan.values() if b["resultat_chf"] > 0)
        frais = dernier["frais_cumules_chf"] if dernier else 0.0
        transactions = [t for e in etats for t in e["transactions"] if t["portefeuille"] == pid]
        resultat[pid] = {
            "valeur_chf": arrondi(serie[-1]),
            "performance_pct": arrondi((serie[-1] / cap - 1) * 100),
            "volatilite_pct": arrondi(vol * 100, 3),
            "pire_chute_pct": arrondi(pire * 100),
            "ratio_rendement_risque": arrondi(moy / vol, 3) if vol > 0 else None,
            "taux_gagnants_pct": arrondi(gagnants / len(bilan) * 100, 1) if bilan else None,
            "nb_titres": len(bilan),
            "nb_ordres": sum(1 for t in transactions if t["statut"] == "exécuté"),
            "nb_annules": sum(1 for t in transactions if t["statut"] == "annulé"),
            "frais_chf": arrondi(frais),
            "poids_frais_pct": arrondi(frais / cap * 100),
            "performance_sans_frais_pct": arrondi((serie[-1] + frais) / cap * 100 - 100),
        }
    for pid, r in resultat.items():
        r["ecart_patient_pts"] = arrondi(r["performance_pct"] - resultat["patient"]["performance_pct"])
        r["ecart_singe_pts"] = arrondi(r["performance_pct"] - resultat["singe"]["performance_pct"])
    return resultat


def evaluer_predictions(etats: list[dict], config: dict, test: bool) -> list[dict]:
    jours = [e["date"] for e in etats]
    if not jours:
        return []
    fin_dispo = jours[-1]
    sortie = []
    for d in dates_disponibles("decisions"):
        if not test and not (config["date_debut"] <= d <= config["date_fin"]):
            continue
        dec = lire_json(DATA / "decisions" / f"{d}.json", {}) or {}
        for pid, p in (dec.get("portefeuilles") or {}).items():
            pred = (p or {}).get("prediction") or {}
            if not pred.get("texte"):
                continue
            ligne = {"date": d, "portefeuille": pid, "texte": pred["texte"], "ticker": pred.get("ticker"),
                     "direction": pred.get("direction"), "horizon_jours": pred.get("horizon_jours"), "verdict": "non vérifiable"}
            ticker, direction = (pred.get("ticker") or "").upper(), pred.get("direction")
            if ticker and direction in ("hausse", "baisse"):
                horizon = max(1, int(pred.get("horizon_jours") or 5))
                calendrier = jours_etude(config) if not test else jours
                idx = calendrier.index(d) if d in calendrier else 0
                cible = calendrier[min(idx + horizon - 1, len(calendrier) - 1)]
                try:
                    barres = cours(ticker, plus_jours(d, -10), max(cible, fin_dispo))["barres"]
                except Exception:
                    barres = {}
                _, depart = derniere_cloture(barres, d, strict=True)
                fin = min(cible, fin_dispo)
                _, arrivee = derniere_cloture(barres, fin)
                if depart and arrivee:
                    var = (arrivee / depart - 1) * 100
                    juste = var > 0 if direction == "hausse" else var < 0
                    ligne.update(variation_pct=arrondi(var), date_fin=fin,
                                 verdict=("juste" if juste else "fausse") if cible <= fin_dispo else "en cours")
            sortie.append(ligne)
    return sortie


def agreger(etats: list[dict]) -> tuple[list, list]:
    """Résultat par secteur et par titre (tous portefeuilles confondus)."""
    if not etats:
        return [], []
    titres, secteurs = {}, {}
    for pid, e in etats[-1]["portefeuilles"].items():
        for tk, b in e["bilan_titres"].items():
            t = titres.setdefault(tk, {"ticker": tk, "nom": b["nom"], "secteur": b["secteur"], "investi_chf": 0, "resultat_chf": 0, "par": []})
            t["investi_chf"] += b["investi_chf"]
            t["resultat_chf"] += b["resultat_chf"]
            t["par"].append({"portefeuille": pid, "investi_chf": b["investi_chf"], "resultat_chf": b["resultat_chf"]})
            s = secteurs.setdefault(b["secteur"], {"secteur": b["secteur"], "investi_chf": 0, "resultat_chf": 0, "nb_titres": 0})
            s["investi_chf"] += b["investi_chf"]
            s["resultat_chf"] += b["resultat_chf"]
            s["nb_titres"] += 1
    for x in list(titres.values()) + list(secteurs.values()):
        x["investi_chf"], x["resultat_chf"] = arrondi(x["investi_chf"]), arrondi(x["resultat_chf"])
        x["resultat_pct"] = arrondi(x["resultat_chf"] / x["investi_chf"] * 100) if x["investi_chf"] else 0.0
    return (sorted(secteurs.values(), key=lambda s: -s["resultat_pct"]),
            sorted(titres.values(), key=lambda t: -t["resultat_chf"]))


def paris(etats: list[dict]) -> list[dict]:
    if not etats:
        return []
    liste = []
    for pid, e in etats[-1]["portefeuilles"].items():
        for tk, b in e["bilan_titres"].items():
            if b["investi_chf"] > 0:
                liste.append({"portefeuille": pid, "ticker": tk, "nom": b["nom"], "investi_chf": b["investi_chf"],
                              "resultat_chf": b["resultat_chf"], "resultat_pct": arrondi(b["resultat_chf"] / b["investi_chf"] * 100)})
    return sorted(liste, key=lambda x: -x["resultat_pct"])


def lecons(ind: dict, secteurs: list, preds: list, noms: dict) -> list[str]:
    ia = {k: v for k, v in ind.items() if k not in ("singe",)}
    classement = sorted(ind.items(), key=lambda kv: -kv[1]["performance_pct"])
    l = []
    meilleur, pire = classement[0], classement[-1]
    l.append(f"Meilleure stratégie : {noms[meilleur[0]]} ({meilleur[1]['performance_pct']:+.2f} %). "
             f"Moins bonne : {noms[pire[0]]} ({pire[1]['performance_pct']:+.2f} %).")
    actives = [k for k in ia if k != "patient"]
    battent_singe = [k for k in actives if ind[k]["ecart_singe_pts"] > 0]
    battent_patient = [k for k in actives if ind[k]["ecart_patient_pts"] > 0]
    l.append(f"{len(battent_singe)} stratégie(s) IA active(s) sur {len(actives)} ont fait mieux que le Singe (le hasard), "
             f"et {len(battent_patient)} sur {len(actives)} mieux que le Patient (ne rien faire).")
    plus_actif = max(ind.items(), key=lambda kv: kv[1]["nb_ordres"])
    moy_frais = statistics.fmean(v["poids_frais_pct"] for v in ind.values())
    l.append(f"Les frais ont coûté en moyenne {moy_frais:.2f} % du capital. La stratégie la plus active, "
             f"{noms[plus_actif[0]]} ({plus_actif[1]['nb_ordres']} ordres), y a laissé {plus_actif[1]['poids_frais_pct']:.2f} %.")
    if secteurs:
        l.append(f"Secteur le plus rentable : {secteurs[0]['secteur']} ({secteurs[0]['resultat_pct']:+.1f} %). "
                 f"Le moins rentable : {secteurs[-1]['secteur']} ({secteurs[-1]['resultat_pct']:+.1f} %).")
    tranchees = [p for p in preds if p["verdict"] in ("juste", "fausse")]
    if tranchees:
        justes = sum(1 for p in tranchees if p["verdict"] == "juste")
        l.append(f"Prédictions vérifiables : {justes} justes sur {len(tranchees)} ({justes / len(tranchees) * 100:.0f} %). "
                 "Pour comparaison, deviner « hausse » ou « baisse » au hasard donne environ 50 %.")
    return l


def ecrire_markdown(r: dict, noms: dict) -> str:
    md = [f"# Rapport {'provisoire' if r['provisoire'] else 'final'} — Labo Bourse",
          "", f"Période : {r['periode']['debut']} → {r['periode']['fin']} · {r['periode']['seances_cloturees']} séance(s) clôturée(s) sur {r['periode']['nb_jours']}.",
          "", "> **À lire avant tout.** Un mois est un échantillon très court. Sur une période aussi brève, le hasard pèse "
          "souvent plus lourd que la qualité d'une stratégie : un bon classement ici ne prouve pas qu'une stratégie est bonne, "
          "et un mauvais ne prouve pas qu'elle est mauvaise. Les résultats sont simulés (argent fictif).", "",
          "## Classement", "", "| # | Portefeuille | Valeur | Performance | Frais | Ordres |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(r["classement"], 1):
        md.append(f"| {i} | {noms[c['id']]} | {c['valeur_chf']:.2f} CHF | {c['performance_pct']:+.2f} % | {c['frais_chf']:.2f} CHF | {c['nb_ordres']} |")
    md += ["", "## Leçons retenues", ""] + [f"- {x}" for x in r["lecons"]]
    md += ["", "## Par secteur", ""] + [f"- {s['secteur']} : {s['resultat_chf']:+.2f} CHF ({s['resultat_pct']:+.1f} %)" for s in r["secteurs"]]
    md += ["", "## Meilleurs paris", ""] + [f"- {noms[p['portefeuille']]} · {p['nom']} ({p['ticker']}) : {p['resultat_pct']:+.1f} %" for p in r["meilleurs_paris"]]
    md += ["", "## Pires paris", ""] + [f"- {noms[p['portefeuille']]} · {p['nom']} ({p['ticker']}) : {p['resultat_pct']:+.1f} %" for p in r["pires_paris"]]
    md += ["", "## Prédictions vérifiables", ""]
    for p in r["predictions"]:
        md.append(f"- {p['date']} · {noms.get(p['portefeuille'], p['portefeuille'])} : « {p['texte']} » → **{p['verdict']}**")
    return "\n".join(md) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--sans-predictions", action="store_true")
    args = parser.parse_args()
    config = etude()
    etats = charger_etats(args.test, config)
    noms = {p["id"]: f"{p['emoji']} {p['nom']}" for p in portefeuilles()}
    ind = indicateurs(etats, config)
    ecrire_json(DATA / "indicateurs.json", {"genere_le": iso_utc(), "explications": EXPLICATIONS,
                                            "date": etats[-1]["date"] if etats else None, "portefeuilles": ind})

    preds = [] if args.sans_predictions else evaluer_predictions(etats, config, args.test)
    secteurs, titres = agreger(etats)
    tous_paris = paris(etats)
    jours = jours_etude(config)
    rapport = {
        "genere_le": iso_utc(),
        "provisoire": not etats or etats[-1]["date"] < config["date_fin"],
        "periode": {"debut": config["date_debut"], "fin": config["date_fin"], "nb_jours": len(jours),
                    "seances_cloturees": len(etats)},
        "classement": [{"id": k, **v} for k, v in sorted(ind.items(), key=lambda kv: -kv[1]["performance_pct"])],
        "secteurs": secteurs,
        "titres": titres,
        "meilleurs_paris": tous_paris[:5],
        "pires_paris": list(reversed(tous_paris[-5:])) if len(tous_paris) > 5 else list(reversed(tous_paris)),
        "predictions": preds,
        "lecons": lecons(ind, secteurs, preds, noms),
    }
    ecrire_json(DATA / "rapport-final.json", rapport)
    (DATA / "rapport-final.md").write_text(ecrire_markdown(rapport, noms), encoding="utf-8", newline="\n")
    print(f"Indicateurs et rapport {'provisoire' if rapport['provisoire'] else 'FINAL'} écrits ({len(etats)} séance(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
