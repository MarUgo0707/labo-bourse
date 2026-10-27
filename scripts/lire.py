"""Outil de LECTURE pour la séance Claude (n'écrit rien d'important, ne modifie aucun solde).

Commandes :
  python scripts/lire.py etat               état actuel de chaque portefeuille + règles
  python scripts/lire.py contexte           contexte de la séance (indices de la veille, bourses ouvertes...)
  python scripts/lire.py cours TICKER ...   derniers cours (avant aujourd'hui), devise, type : vérifie qu'un ticker existe
  python scripts/lire.py historique         décisions et prédictions des séances précédentes (résumé)
"""
from __future__ import annotations

import sys

from commun import (DATA, aujourdhui, dates_disponibles, dernier_etat, etude, infos_titre, lire_json, portefeuilles)


def date_session() -> str:
    dates = dates_disponibles("contexte")
    auj = aujourdhui()
    return auj if auj in dates or not dates else max(dates)


def cmd_etat() -> None:
    date = date_session()
    config = etude()
    contexte = lire_json(DATA / "contexte" / f"{date}.json", {})
    etat = dernier_etat(date, config, test=contexte.get("mode_test", False))
    cap = config["capital_initial_chf"]
    print(f"État de référence : {etat.get('date') or 'initial (aucune clôture encore)'} — capital de départ {cap} CHF par portefeuille")
    print(f"Frais : {config['frais']['fixe_par_ordre_chf']} CHF par ordre + {config['frais']['commission_pct']} % "
          f"+ {config['frais']['change_pct']} % de change hors CHF. Slippage {config['slippage_pct']} %.")
    print(f"Maximum {config['max_ordres_par_session']} ordres par portefeuille, minimum {config['montant_min_ordre_chf']} CHF par achat.\n")
    for p in portefeuilles():
        e = etat["portefeuilles"].get(p["id"])
        print(f"=== {p['emoji']} {p['nom']} [{p['id']}] — piloté par : {p['pilote']}")
        print(f"    {p['description']}")
        for r in p["regles"]:
            print(f"    • {r}")
        print(f"    Contraintes vérifiées par machine : {p['contraintes'] if p['id'] != 'singe' else '(script)'}")
        if e is None:
            continue
        perf = (e["valeur_totale_chf"] / cap - 1) * 100
        print(f"    Valeur {e['valeur_totale_chf']:.2f} CHF ({perf:+.2f} %) — cash {e['cash_chf']:.2f} CHF — frais payés {e['frais_cumules_chf']:.2f} CHF")
        if not e["positions"]:
            print("    Aucune position.")
        for pos in e["positions"]:
            print(f"    - {pos['ticker']} {pos['nom']} ({pos['secteur']}, {pos['pays']}) : {pos['quantite']:.4f} titres, "
                  f"coût {pos['cout_chf']:.2f} CHF, valeur {pos['valeur_chf']:.2f} CHF ({pos['gain_pct']:+.2f} %), "
                  f"dernier cours {pos['prix_cloture']} {pos['devise']} le {pos['date_prix']}")
        print()


def cmd_contexte() -> None:
    date = date_session()
    contexte = lire_json(DATA / "contexte" / f"{date}.json")
    if not contexte:
        print("Aucun contexte préparé.")
        return
    print(f"Séance du {contexte['date']} — jour {contexte['jour']} sur {contexte['nb_jours']}"
          f"{' — DERNIER JOUR' if contexte['dernier_jour'] else ''}{' — MODE TEST' if contexte['mode_test'] else ''}")
    print("\nBourses aujourd'hui :")
    for m, info in contexte["marches"].items():
        etat = "ouverte" if info["ouvert_aujourdhui"] else "FERMÉE (ordres impossibles)"
        if info["deja_ouvert_au_moment_de_la_session"]:
            etat += " — DÉJÀ OUVERTE : un ordre sur cette bourse sera annulé (décision trop tardive)"
        print(f"  {m} {info['nom']} : {etat}, ouverture {info['ouverture_heure_zurich']} (heure de Zurich)")
    print("\nIndices et devises à la dernière clôture connue :")
    for t, i in contexte["indices_veille"].items():
        if "erreur" in i:
            print(f"  {i['nom']} ({t}) : donnée indisponible")
        else:
            var = f"{i['variation_pct']:+.2f} %" if i["variation_pct"] is not None else "?"
            print(f"  {i['nom']} ({t}) : {i['cloture']} le {i['date']} ({var})")
    if contexte["seances_ratees"]:
        print(f"\nSéances ratées (à mentionner, jamais à rattraper) : {', '.join(contexte['seances_ratees'])}")
    if contexte["clotures_manquantes"]:
        print(f"Clôtures pas encore calculées : {', '.join(contexte['clotures_manquantes'])}")


def cmd_cours(tickers: list[str]) -> None:
    date = date_session()
    for t in tickers:
        t = t.strip().upper()
        infos = infos_titre(t, date)
        if not infos:
            print(f"{t} : INTROUVABLE sur Yahoo Finance (ticker invalide ou sans cotation récente).")
            continue
        barres = list(infos["barres"].items())[-10:]
        print(f"{t} — {infos['nom_yahoo']} — type {infos['type']} — devise {infos['devise']} — marché {infos['marche']}")
        for d, b in barres:
            print(f"   {d} : clôture {b['cloture']}")
        if len(barres) >= 2:
            premier, dernier = barres[0][1]["cloture"], barres[-1][1]["cloture"]
            print(f"   Variation sur la période affichée : {(dernier / premier - 1) * 100:+.2f} %")


def cmd_historique() -> None:
    date = date_session()
    for d in [x for x in dates_disponibles("decisions") if x < date][-5:]:
        dec = lire_json(DATA / "decisions" / f"{d}.json", {})
        print(f"--- {d}")
        for pid, p in (dec.get("portefeuilles") or {}).items():
            ordres = ", ".join(f"{o.get('action')} {o.get('ticker')} {o.get('montant_chf', '')}" for o in p.get("ordres", []))
            pred = (p.get("prediction") or {}).get("texte", "")
            print(f"  {pid} : {ordres or 'rien'} | prédiction : {pred}")
    ordres = [x for x in dates_disponibles("ordres") if x < date][-1:]
    for d in ordres:
        rejets = [o for o in lire_json(DATA / "ordres" / f"{d}.json", {}).get("ordres", []) if o["statut"] == "rejeté"]
        if rejets:
            print(f"\nOrdres rejetés le {d} :")
            for o in rejets:
                print(f"  {o['portefeuille']} {o['action']} {o['ticker']} : {o['motif']}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, reste = sys.argv[1], sys.argv[2:]
    if cmd == "etat":
        cmd_etat()
    elif cmd == "contexte":
        cmd_contexte()
    elif cmd == "cours" and reste:
        cmd_cours(reste[:15])
    elif cmd == "historique":
        cmd_historique()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
