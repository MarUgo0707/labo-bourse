"""Garde-fichiers : après la séance Claude, annule toute modification hors de
data/decisions/<date>.json et data/journal/<date>.md.

Le workflow fait un commit local juste avant Claude : tout écart par rapport à ce commit
est donc l'œuvre de la séance. Usage : python scripts/garde.py --date AAAA-MM-JJ
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from commun import DATA, RACINE, ajouter_texte, aujourdhui

# Cache régénéré par les scripts : on le remet en place sans le signaler.
SILENCIEUX = {"data/referentiel/tickers.json"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RACINE, capture_output=True, text=True, check=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=aujourdhui())
    args = parser.parse_args()
    autorises = {f"data/decisions/{args.date}.json", f"data/journal/{args.date}.md"}

    annules = []
    for ligne in git("status", "--porcelain", "-uall").splitlines():
        statut, chemin = ligne[:2], ligne[3:].strip().strip('"')
        if " -> " in chemin:
            chemin = chemin.split(" -> ")[1]
        if chemin in autorises:
            continue
        if statut == "??":
            (RACINE / chemin).unlink(missing_ok=True)
        else:
            git("checkout", "HEAD", "--", chemin)
        if chemin not in SILENCIEUX:
            annules.append(chemin)

    if annules:
        print("Modifications non autorisées annulées :", *annules, sep="\n  ")
        ajouter_texte(DATA / "journal" / f"{args.date}.md",
                      "\n## ⚠️ Garde-fichiers\n\nLa séance a tenté de modifier des fichiers interdits. "
                      "Ces changements ont été annulés automatiquement :\n\n"
                      + "".join(f"- `{c}`\n" for c in annules))
    else:
        print("Aucune modification hors des fichiers autorisés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
