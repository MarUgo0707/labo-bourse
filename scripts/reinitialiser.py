"""Remise à zéro des données de test.

Supprime tout fichier de données daté AVANT le début de l'étude ou marqué « mode_test »,
ainsi que les rapports et indicateurs (régénérés à la prochaine clôture).
Usage : python scripts/reinitialiser.py [--tout]   (--tout : efface aussi les données de l'étude, à éviter !)
"""
from __future__ import annotations

import argparse
import re
import sys

from commun import DATA, etude, lire_json

DOSSIERS = ("decisions", "marche", "etat", "journal", "ordres", "contexte", "singe")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tout", action="store_true")
    args = parser.parse_args()
    debut = etude()["date_debut"]
    supprimes = []
    for dossier in DOSSIERS:
        for f in (DATA / dossier).glob("*.*"):
            m = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
            if not m:
                continue
            test = f.suffix == ".json" and isinstance(lire_json(f, {}), dict) and lire_json(f, {}).get("mode_test")
            if args.tout or m.group(1) < debut or test:
                f.unlink()
                supprimes.append(str(f.relative_to(DATA)))
    for nom in ("indicateurs.json", "rapport-final.json", "rapport-final.md", "referentiel/tickers.json") + (("verrou.json",) if args.tout else ()):
        if (DATA / nom).exists():
            (DATA / nom).unlink()
            supprimes.append(nom)
    print(f"{len(supprimes)} fichier(s) supprimé(s).", *supprimes, sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
