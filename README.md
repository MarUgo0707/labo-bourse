# 🧪 Labo Bourse

Une étude d'investissement **simulée** (argent 100 % fictif) sur un mois : du **28 octobre au 27 novembre 2026**.
Neuf portefeuilles virtuels de **200 CHF** suivent chacun une stratégie différente. Chaque jour de bourse à
**8h00 (heure de Zurich)**, une séance automatique de Claude décide pour huit d'entre eux ; le neuvième, le Singe,
joue au hasard pour servir de témoin. Un tableau de bord public montre tout.

Aucune connexion à un vrai courtier, jamais. Rien ici n'est un conseil d'investissement.

## Comment ça marche, chaque jour

| Heure (Zurich) | Quoi | Qui |
|---|---|---|
| 08:00 | Préparation : calendrier, verrou des règles, indices et devises de la veille | script Python |
| 08:00 – 08:30 | Séance : brief du marché, décisions par portefeuille, journal | **Claude** (écrit seulement `data/decisions/` et `data/journal/`) |
| juste après | Garde-fichiers (annule toute écriture interdite), tirage du Singe, validation des ordres | scripts Python |
| 23:00 | Clôture : exécution au **prix d'ouverture réel** + slippage + frais, valorisation à la clôture, conversion en CHF, indicateurs, rapport | script Python, **sans IA** |
| après chaque étape | Publication du tableau de bord | GitHub Pages |

Tout est commité dans git : l'historique sert de piste d'audit.

### Anti-triche

- Claude **ne touche jamais aux soldes** : il décide, un script exécute.
- Les ordres sont exécutés au prix d'**ouverture** du jour, décidés **avant** l'ouverture. Un ordre validé après
  l'ouverture de sa bourse est annulé.
- Une séance ratée n'est **jamais rattrapée**. Une clôture ratée, si (les prix d'exécution sont des faits).
- Les stratégies sont **pré-enregistrées** dans `config/portefeuilles.json`. Dès le premier jour, une empreinte
  (`data/verrou.json`) fige les règles et les frais : toute modification ultérieure bloque les séances.
- Le validateur rejette (sans bloquer le reste) : cash négatif, ticker inconnu, hors univers du portefeuille,
  levier, produit inversé, vente à découvert, trop d'ordres, position trop grosse, bourse fermée.

## Les portefeuilles

🏛️ Le Patient (référence passive) · 📰 Le Journaliste · 🔥 Le Risque-tout · 🤖 Le Thématique IA · 🇨🇭 Le Suisse ·
🔄 Le Contrarien · 📈 Le Momentum · 🛡️ Le Défensif · 🎲 Le Singe (hasard, sans IA)

Les règles détaillées sont dans `config/portefeuilles.json`.

## Frais (à ajuster AVANT le début de l'étude)

Dans `config/etude.json`, bloc `frais` :

```json
"frais": { "fixe_par_ordre_chf": 1.0, "commission_pct": 0.0, "change_pct": 0.5 }
```

- `fixe_par_ordre_chf` : frais fixes payés à chaque achat ou vente.
- `commission_pct` : commission en % du montant (0 par défaut).
- `change_pct` : frais de change en % pour tout titre qui n'est pas en CHF.
- `slippage_pct` (à côté) : écart défavorable appliqué au prix d'exécution (0,1 %).

Les valeurs par défaut sont volontairement prudentes, dans l'esprit d'un néo-courtier suisse bon marché. Avec
200 CHF, 1 CHF par ordre représente déjà 0,5 % du capital : les frais sont affichés partout. **Après le 28 octobre,
ces valeurs sont verrouillées.**

## Le modèle Claude

`config/etude.json` → `"modele_claude": "sonnet"` (pour ménager le quota Pro) et `"max_tours_claude": 60`.
Ces deux réglages ne sont pas verrouillés.

## Réglages GitHub (une seule fois)

1. **Pages** : *Settings → Pages → Build and deployment → Source : « GitHub Actions »*.
2. **Jeton Claude** : dans un terminal, `claude setup-token` (il ouvre le navigateur et affiche un jeton), puis
   *Settings → Secrets and variables → Actions → New repository secret*, nom `CLAUDE_CODE_OAUTH_TOKEN`,
   valeur : le jeton. Ne le colle jamais ailleurs.
3. **Actions** : *Settings → Actions → General → Workflow permissions : « Read and write permissions »*.

## Lancer à la main

Onglet **Actions** du dépôt :

- **Séance du matin (Claude)** → *Run workflow* (cocher `mode_test` pour un essai hors calendrier).
- **Clôture du soir (sans IA)** → *Run workflow* (idem).
- **Vérification de la chaîne** → rejoue tout avec des décisions simulées, sans IA et sans rien commiter.
- **Publier le tableau de bord** → reconstruit le site.

Après un essai en `mode_test`, effacer ses données : `python scripts/reinitialiser.py`, puis commiter.

## En local (facultatif)

```bash
pip install -r scripts/requirements.txt
python scripts/preparer_session.py --date 2026-10-26 --test
python scripts/simuler_decisions.py --date 2026-10-26      # fausse séance, sans IA
python scripts/singe.py --date 2026-10-26 --test
python scripts/valider.py --date 2026-10-26 --test
python scripts/cloture.py --date 2026-10-26 --test
python scripts/rapport.py --test
python scripts/reinitialiser.py                            # remise à zéro

cd app && npm install && npm run dev                       # tableau de bord
```

## Organisation

```
config/       etude.json (dates, frais, modèle) · portefeuilles.json (stratégies figées)
prompts/      session.md : instructions de la séance quotidienne de Claude
scripts/      Python : préparation, lecture, garde, Singe, validation, clôture, rapport
data/         contexte/ decisions/ singe/ ordres/ marche/ etat/ journal/ + indicateurs et rapport
app/          tableau de bord Vite + React + TypeScript (lit data/ au moment du build)
.github/      workflows : séance du matin, clôture du soir, publication, vérification
```

## Limites honnêtes

- Un mois est un **échantillon court** : le hasard pèse lourd. Le Singe est là pour le mesurer.
- Prix de Yahoo Finance (gratuit, parfois en retard ou incomplet). Prix bruts, non ajustés : un fractionnement
  d'action pendant l'étude fausserait la position concernée.
- Les dividendes ne sont pas comptés.
- Les crons de GitHub peuvent démarrer avec quelques minutes de retard.
