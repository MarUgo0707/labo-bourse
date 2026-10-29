"""Outils partagés par tous les scripts de Labo Bourse (aucune IA ici)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import time
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
CONFIG = RACINE / "config"
ZURICH = ZoneInfo("Europe/Zurich")
warnings.filterwarnings("ignore")

# Les sorties en UTF-8 même sous Windows (emoji, accents).
for flux in (sys.stdout, sys.stderr):
    try:
        flux.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------- fichiers

def lire_json(chemin: Path, defaut=None):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return defaut


def ecrire_json(chemin: Path, objet) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline="\n") as f:
        json.dump(objet, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ajouter_texte(chemin: Path, texte: str) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    existant = chemin.read_text(encoding="utf-8") if chemin.exists() else ""
    if existant and not existant.endswith("\n"):
        existant += "\n"
    chemin.write_text(existant + texte, encoding="utf-8", newline="\n")


def etude() -> dict:
    return lire_json(CONFIG / "etude.json")


def portefeuilles() -> list[dict]:
    return lire_json(CONFIG / "portefeuilles.json")["portefeuilles"]


def portefeuilles_par_id() -> dict[str, dict]:
    return {p["id"]: p for p in portefeuilles()}


def sortie_github(**valeurs) -> None:
    """Écrit des sorties de step GitHub Actions (et les affiche)."""
    chemin = os.environ.get("GITHUB_OUTPUT")
    for cle, val in valeurs.items():
        val = str(val).lower() if isinstance(val, bool) else str(val)
        print(f"{cle}={val}")
        if chemin:
            with open(chemin, "a", encoding="utf-8") as f:
                f.write(f"{cle}={val}\n")


# ---------------------------------------------------------------- dates

def aujourdhui() -> str:
    return dt.datetime.now(ZURICH).date().isoformat()


def derniere_date_cloturable() -> str:
    """Dernier jour dont la bourse américaine a fermé (16h00 à New York, + 30 min de marge).

    Le cron GitHub peut partir avec plusieurs heures de retard, après minuit : on ne doit pas
    alors clôturer le nouveau jour (pas encore ouvert) à la place de la veille.
    """
    return (dt.datetime.now(ZoneInfo("America/New_York")) - dt.timedelta(hours=16, minutes=30)).date().isoformat()


def maintenant_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso_utc(moment: dt.datetime | None = None) -> str:
    return (moment or maintenant_utc()).isoformat().replace("+00:00", "Z")


def lire_iso(texte: str) -> dt.datetime:
    return dt.datetime.fromisoformat(texte.replace("Z", "+00:00"))


def jour(date: str) -> dt.date:
    return dt.date.fromisoformat(date)


def plus_jours(date: str, n: int) -> str:
    return (jour(date) + dt.timedelta(days=n)).isoformat()


MARCHES = ("CH", "EU", "UK", "US")
NOMS_MARCHES = {"CH": "Bourse suisse (SIX)", "EU": "Bourses européennes", "UK": "Bourse de Londres", "US": "Bourses américaines"}
SUFFIXES_EU = {".DE", ".F", ".PA", ".AS", ".MI", ".MC", ".BR", ".VI", ".HE", ".ST", ".CO", ".OL", ".LS", ".IR"}


def marche_du_ticker(ticker: str) -> str:
    if "." not in ticker:
        return "US"
    suffixe = "." + ticker.rsplit(".", 1)[1].upper()
    if suffixe == ".SW":
        return "CH"
    if suffixe == ".L":
        return "UK"
    if suffixe in SUFFIXES_EU:
        return "EU"
    return "INCONNU"


def marche_ouvert(date: str, marche: str, config: dict | None = None) -> bool:
    config = config or etude()
    if jour(date).weekday() >= 5:
        return False
    return date not in config["jours_feries"].get(marche, [])


def ouverture_utc(date: str, marche: str, config: dict | None = None) -> dt.datetime:
    """Heure d'ouverture dans le fuseau de la bourse : suit les changements d'heure de chaque pays."""
    config = config or etude()
    fuseau, heure = config["ouvertures_heure_locale"][marche]
    h, m = (int(x) for x in heure.split(":"))
    local = dt.datetime.combine(jour(date), dt.time(h, m), tzinfo=ZoneInfo(fuseau))
    return local.astimezone(dt.timezone.utc)


def ouverture_heure_zurich(date: str, marche: str, config: dict | None = None) -> str:
    return ouverture_utc(date, marche, config).astimezone(ZURICH).strftime("%H:%M")


def jours_etude(config: dict | None = None) -> list[str]:
    """Jours de séance : jours ouvrables où au moins une bourse est ouverte."""
    config = config or etude()
    d, fin, jours = jour(config["date_debut"]), jour(config["date_fin"]), []
    while d <= fin:
        iso = d.isoformat()
        if any(marche_ouvert(iso, m, config) for m in MARCHES):
            jours.append(iso)
        d += dt.timedelta(days=1)
    return jours


def numero_jour(date: str, config: dict | None = None) -> int | None:
    jours = jours_etude(config)
    return jours.index(date) + 1 if date in jours else None


# ---------------------------------------------------------------- réseau

def avec_retries(fonction, essais: int = 4, pause: float = 4.0, nom: str = "appel réseau"):
    derniere = None
    for i in range(essais):
        try:
            return fonction()
        except Exception as e:  # noqa: BLE001 - on veut tout rattraper ici
            derniere = e
            print(f"  ! {nom} : essai {i + 1}/{essais} raté ({e})", file=sys.stderr)
            time.sleep(pause * (i + 1))
    raise RuntimeError(f"{nom} impossible après {essais} essais : {derniere}")


DEVISES_CENTIMES = {"GBp": ("GBP", 100), "GBX": ("GBP", 100), "ZAc": ("ZAR", 100), "ILA": ("ILS", 100)}

_cache_titres: dict[str, dict] = {}


def _nombre(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or x <= 0 else x


def cours(ticker: str, debut: str, fin_incluse: str) -> dict:
    """Cours journaliers bruts (non ajustés) d'un titre entre deux dates incluses.

    Renvoie {"devise", "type", "nom", "barres": {date: {"ouverture", "cloture"}}}.
    Les prix en centimes (pence...) sont convertis dans l'unité principale.
    """
    cle = f"{ticker}|{debut}|{fin_incluse}"
    if cle in _cache_titres:
        return _cache_titres[cle]
    import yfinance as yf

    def telecharger():
        t = yf.Ticker(ticker)
        try:
            df = t.history(start=debut, end=plus_jours(fin_incluse, 1), auto_adjust=False, actions=False, raise_errors=True)
        except Exception as e:
            # Un ticker inexistant ou sans données sur la période n'est pas une panne réseau : pas de relance.
            if any(m in str(e).lower() for m in ("delisted", "no data", "not found", "no timezone", "no price")):
                return None, {}
            raise
        meta = {}
        try:
            meta = t.history_metadata or {}
        except Exception:
            pass
        return df, meta

    df, meta = avec_retries(telecharger, essais=3, pause=3, nom=f"cours {ticker}")
    devise = (meta or {}).get("currency") or ""
    diviseur = 1
    if devise in DEVISES_CENTIMES:
        devise, diviseur = DEVISES_CENTIMES[devise]
    barres = {}
    if df is not None and len(df):
        for idx, ligne in df.iterrows():
            o, c = _nombre(ligne.get("Open")), _nombre(ligne.get("Close"))
            if c is None:
                continue
            barres[idx.date().isoformat()] = {
                "ouverture": round(o / diviseur, 6) if o else None,
                "cloture": round(c / diviseur, 6),
            }
    resultat = {
        "devise": devise.upper() if devise else "",
        "type": (meta or {}).get("instrumentType", ""),
        "nom": (meta or {}).get("longName") or (meta or {}).get("shortName") or "",
        "barres": dict(sorted(barres.items())),
    }
    _cache_titres[cle] = resultat
    return resultat


def derniere_cloture(barres: dict, avant_ou_egal: str, strict: bool = False):
    """(date, clôture) de la dernière barre <= date (ou < date si strict)."""
    dates = [d for d in barres if (d < avant_ou_egal if strict else d <= avant_ou_egal)]
    if not dates:
        return None, None
    d = max(dates)
    return d, barres[d]["cloture"]


_cache_taux: dict[tuple[str, str], float] = {}


def taux_chf(devise: str, date: str, strict: bool = False) -> float | None:
    """Combien de CHF vaut 1 unité de la devise, à la clôture du jour (ou du dernier jour connu)."""
    devise = devise.upper()
    if devise == "CHF":
        return 1.0
    cle = (devise, date + ("<" if strict else ""))
    if cle not in _cache_taux:
        donnees = cours(f"{devise}CHF=X", plus_jours(date, -10), date)
        _, valeur = derniere_cloture(donnees["barres"], date, strict=strict)
        if valeur is None:
            return None
        _cache_taux[cle] = valeur
    return _cache_taux[cle]


# ---------------------------------------------------------------- référentiel des titres

FICHIER_REFERENTIEL = DATA / "referentiel" / "tickers.json"
MOTS_LEVIER = re.compile(r"\b(2x|3x|-1x|-2x|-3x|leveraged|levier|ultra|inverse|short|bear|bull 2|daily 2|daily 3)\b", re.I)


def infos_titre(ticker: str, avant: str) -> dict | None:
    """Infos d'un titre et ses 15 derniers jours de cours strictement avant `avant`.

    Met à jour le référentiel partagé. Renvoie None si le titre est introuvable.
    """
    donnees = cours(ticker, plus_jours(avant, -25), plus_jours(avant, -1))
    if not donnees["barres"] or not donnees["devise"]:
        return None
    ref = lire_json(FICHIER_REFERENTIEL, {})
    ref[ticker] = {
        "devise": donnees["devise"],
        "type": donnees["type"],
        "nom_yahoo": donnees["nom"],
        "marche": marche_du_ticker(ticker),
    }
    ecrire_json(FICHIER_REFERENTIEL, dict(sorted(ref.items())))
    return {**ref[ticker], "barres": donnees["barres"]}


def devise_titre(ticker: str, date: str) -> str | None:
    ref = lire_json(FICHIER_REFERENTIEL, {})
    if ticker in ref:
        return ref[ticker]["devise"]
    infos = infos_titre(ticker, plus_jours(date, 1))
    return infos["devise"] if infos else None


# ---------------------------------------------------------------- états

def calcul_frais(montant_chf: float, devise: str, config: dict) -> float:
    f = config["frais"]
    frais = f["fixe_par_ordre_chf"] + montant_chf * f["commission_pct"] / 100
    if devise.upper() != "CHF":
        frais += montant_chf * f["change_pct"] / 100
    return round(frais, 2)


def etat_initial(config: dict | None = None) -> dict:
    config = config or etude()
    cap = config["capital_initial_chf"]
    return {
        "date": None,
        "portefeuilles": {
            p["id"]: {
                "cash_chf": cap,
                "valeur_positions_chf": 0.0,
                "valeur_totale_chf": cap,
                "frais_cumules_chf": 0.0,
                "nb_ordres_cumules": 0,
                "positions": [],
                "bilan_titres": {},
            }
            for p in portefeuilles()
        },
    }


def dates_disponibles(dossier: str, suffixe: str = ".json") -> list[str]:
    dates = []
    for f in (DATA / dossier).glob(f"*{suffixe}"):
        nom = f.name[: -len(suffixe)]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", nom):
            dates.append(nom)
    return sorted(dates)


def dernier_etat(avant: str, config: dict | None = None, test: bool = False) -> dict:
    """Dernier état calculé strictement avant la date. Hors mode test, ignore tout ce qui précède l'étude."""
    config = config or etude()
    candidates = [d for d in dates_disponibles("etat") if d < avant]
    if not test:
        candidates = [d for d in candidates if d >= config["date_debut"]]
    if not candidates:
        return etat_initial(config)
    return lire_json(DATA / "etat" / f"{candidates[-1]}.json")


# ---------------------------------------------------------------- verrou

def empreinte_regles(config: dict | None = None) -> str:
    config = config or etude()
    figees = {k: config[k] for k in ("date_debut", "date_fin", "capital_initial_chf", "slippage_pct", "frais",
                                    "max_ordres_par_session", "montant_min_ordre_chf", "singe")}
    contenu = json.dumps({"etude": figees, "portefeuilles": portefeuilles()}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()


def verifier_verrou(date: str, test: bool = False) -> list[str]:
    """Pré-enregistrement : après le début, les règles ne doivent plus bouger."""
    import subprocess

    config = etude()
    if test or date < config["date_debut"]:
        return []
    erreurs = []
    chemin = DATA / "verrou.json"
    verrou = lire_json(chemin)
    empreinte = empreinte_regles(config)
    if verrou is None:
        ecrire_json(chemin, {"cree_le": iso_utc(), "date": date, "empreinte_sha256": empreinte,
                             "explication": "Empreinte des règles figées (portefeuilles + frais) au premier jour de l'étude."})
    elif verrou["empreinte_sha256"] != empreinte:
        erreurs.append("Les règles figées (portefeuilles.json ou frais) ont été modifiées après le début de l'étude.")
    try:
        debut_utc = dt.datetime.combine(jour(config["date_debut"]), dt.time(0, 0), tzinfo=ZURICH).astimezone(dt.timezone.utc)
        sortie = subprocess.run(["git", "log", "--format=%cI", "--", "config/portefeuilles.json"],
                                cwd=RACINE, capture_output=True, text=True, check=True).stdout.split()
        if any(lire_iso(s) >= debut_utc for s in sortie):
            erreurs.append("Un commit a modifié config/portefeuilles.json après la date de début.")
    except Exception as e:  # git absent : on s'appuie sur l'empreinte seule
        print(f"  (vérification git du verrou impossible : {e})", file=sys.stderr)
    return erreurs


def arrondi(x: float, n: int = 2) -> float:
    return round(float(x), n)
