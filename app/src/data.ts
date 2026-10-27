// Toutes les données sont lues dans ../data et ../config au moment du build :
// le site est reconstruit après chaque séance et chaque clôture.
import etudeJson from "../../config/etude.json";
import pfJson from "../../config/portefeuilles.json";

export type Portefeuille = {
  id: string;
  nom: string;
  emoji: string;
  couleur: { clair: string; sombre: string };
  pilote: "ia" | "script";
  description: string;
  regles: string[];
  contraintes: Record<string, unknown>;
};

export type Position = {
  ticker: string; nom: string; secteur: string; pays: string; marche: string; devise: string;
  quantite: number; cout_chf: number; prix_cloture: number; date_prix: string; taux_chf: number;
  valeur_chf: number; gain_chf: number; gain_pct: number; part_pct: number; date_achat: string;
};

export type BilanTitre = {
  nom: string; secteur: string; pays: string; investi_chf: number; recupere_chf: number; frais_chf: number;
  valeur_actuelle_chf: number; resultat_chf: number; nb_ordres: number;
};

export type EtatPf = {
  cash_chf: number; valeur_positions_chf: number; valeur_totale_chf: number; frais_cumules_chf: number;
  nb_ordres_cumules: number; positions: Position[]; bilan_titres: Record<string, BilanTitre>;
  variation_jour_chf: number; variation_jour_pct: number; gain_total_chf: number; gain_total_pct: number;
};

export type Transaction = {
  date: string; portefeuille: string; auteur: string; action: string; sens: "achat" | "vente";
  ticker: string; nom: string; secteur: string; pays: string; marche: string;
  raison: string; confiance: string; horizon: string; statut: "exécuté" | "annulé"; motif: string;
  montant_demande_chf: number; montant_chf?: number; quantite?: number; prix_execution?: number;
  prix_ouverture?: number; devise?: string; taux_chf?: number; frais_chf?: number; resultat_realise_chf?: number;
  note?: string;
};

export type Etat = {
  date: string; jour: number | null; mode_test: boolean; session_ia: string; genere_le: string;
  taux_change_chf: Record<string, number>; portefeuilles: Record<string, EtatPf>; transactions: Transaction[];
};

export type OrdreValide = {
  portefeuille: string; auteur: string; action: string; sens: string | null; ticker: string; nom: string;
  secteur: string; pays: string; montant_chf: number; raison: string; confiance: string; horizon: string;
  statut: "accepté" | "rejeté"; motif: string;
};

export type Ordres = {
  date: string; mode_test: boolean; horodatage_validation: string; session_ia: string;
  ordres: OrdreValide[]; resume: { acceptes: number; rejetes: number };
};

export type Prediction = { texte: string; ticker?: string; direction?: string; horizon_jours?: number };

export type Decisions = {
  date: string; heure_session?: string; brief_marche?: string; points_cles?: string[];
  sources?: { titre: string; url: string }[]; simulation?: boolean; incertitudes?: string[];
  portefeuilles: Record<string, { decision: string; resume: string; ordres: Record<string, unknown>[]; prediction?: Prediction }>;
};

export type Contexte = {
  date: string; mode_test: boolean; jour: number | null; nb_jours: number; genere_le: string;
  seances_ratees: string[]; clotures_manquantes: string[];
};

export type Indicateurs = {
  date: string | null; explications: Record<string, string>;
  portefeuilles: Record<string, {
    valeur_chf: number; performance_pct: number; volatilite_pct: number; pire_chute_pct: number;
    ratio_rendement_risque: number | null; taux_gagnants_pct: number | null; nb_titres: number; nb_ordres: number;
    nb_annules: number; frais_chf: number; poids_frais_pct: number; performance_sans_frais_pct: number;
    ecart_patient_pts: number; ecart_singe_pts: number;
  }>;
};

export type Rapport = {
  genere_le: string; provisoire: boolean;
  periode: { debut: string; fin: string; nb_jours: number; seances_cloturees: number };
  classement: ({ id: string } & Indicateurs["portefeuilles"][string])[];
  secteurs: { secteur: string; investi_chf: number; resultat_chf: number; resultat_pct: number; nb_titres: number }[];
  titres: { ticker: string; nom: string; secteur: string; investi_chf: number; resultat_chf: number; resultat_pct: number;
    par: { portefeuille: string; investi_chf: number; resultat_chf: number }[] }[];
  meilleurs_paris: Pari[]; pires_paris: Pari[];
  predictions: { date: string; portefeuille: string; texte: string; ticker?: string; direction?: string;
    verdict: string; variation_pct?: number; date_fin?: string }[];
  lecons: string[];
};
type Pari = { portefeuille: string; ticker: string; nom: string; investi_chf: number; resultat_chf: number; resultat_pct: number };

export const etude = etudeJson as typeof etudeJson;
export const portefeuilles = pfJson.portefeuilles as unknown as Portefeuille[];
export const pfParId = Object.fromEntries(portefeuilles.map((p) => [p.id, p]));
export const CAPITAL = etude.capital_initial_chf;

function parDate<T>(mods: Record<string, unknown>): Record<string, T> {
  const out: Record<string, T> = {};
  for (const [chemin, contenu] of Object.entries(mods)) {
    const m = chemin.match(/(\d{4}-\d{2}-\d{2})\.(json|md)$/);
    if (m) out[m[1]] = contenu as T;
  }
  return out;
}

const g = import.meta.glob;
export const etatsParDate = parDate<Etat>(g("../../data/etat/*.json", { eager: true, import: "default" }));
export const decisionsParDate = parDate<Decisions>(g("../../data/decisions/*.json", { eager: true, import: "default" }));
export const ordresParDate = parDate<Ordres>(g("../../data/ordres/*.json", { eager: true, import: "default" }));
export const contexteParDate = parDate<Contexte>(g("../../data/contexte/*.json", { eager: true, import: "default" }));
export const journaux = parDate<string>(g("../../data/journal/*.md", { eager: true, query: "?raw", import: "default" }));

const uniques = g(["../../data/indicateurs.json", "../../data/rapport-final.json"], { eager: true, import: "default" });
export const indicateurs = (Object.entries(uniques).find(([k]) => k.endsWith("indicateurs.json"))?.[1] ?? null) as Indicateurs | null;
export const rapport = (Object.entries(uniques).find(([k]) => k.endsWith("rapport-final.json"))?.[1] ?? null) as Rapport | null;

export const etats: Etat[] = Object.keys(etatsParDate).sort().map((d) => etatsParDate[d]);
export const dernierEtat: Etat | null = etats.at(-1) ?? null;
export const transactions: Transaction[] = etats.flatMap((e) => e.transactions);
export const datesSeances = Array.from(
  new Set([...Object.keys(decisionsParDate), ...Object.keys(journaux), ...Object.keys(etatsParDate), ...Object.keys(ordresParDate)]),
).sort();
export const contientTest =
  etats.some((e) => e.mode_test) || Object.values(ordresParDate).some((o) => o.mode_test) ||
  Object.values(decisionsParDate).some((d) => d.simulation);

// Calendrier de l'étude (identique à scripts/commun.py : jours ouvrables où au moins une bourse est ouverte).
export const joursEtude: string[] = (() => {
  const jours: string[] = [];
  const feries = etude.jours_feries as Record<string, string[]>;
  const d = new Date(etude.date_debut + "T12:00:00Z");
  const fin = new Date(etude.date_fin + "T12:00:00Z");
  while (d <= fin) {
    const iso = d.toISOString().slice(0, 10);
    const ouvrable = d.getUTCDay() !== 0 && d.getUTCDay() !== 6;
    if (ouvrable && Object.keys(feries).some((m) => !feries[m].includes(iso))) jours.push(iso);
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return jours;
})();

export function etatPf(id: string, etat: Etat | null = dernierEtat): EtatPf {
  return etat?.portefeuilles[id] ?? {
    cash_chf: CAPITAL, valeur_positions_chf: 0, valeur_totale_chf: CAPITAL, frais_cumules_chf: 0, nb_ordres_cumules: 0,
    positions: [], bilan_titres: {}, variation_jour_chf: 0, variation_jour_pct: 0, gain_total_chf: 0, gain_total_pct: 0,
  };
}

/** Lignes pour les graphiques : un point de départ à 200 CHF puis une valeur par clôture. */
export function serie(ids: string[], mode: "chf" | "pct") {
  const conv = (v: number) => (mode === "chf" ? v : (v / CAPITAL - 1) * 100);
  const depart: Record<string, number | string> = { date: "Départ" };
  ids.forEach((id) => (depart[id] = conv(CAPITAL)));
  return [depart, ...etats.map((e) => {
    const ligne: Record<string, number | string> = { date: e.date };
    ids.forEach((id) => (ligne[id] = conv(e.portefeuilles[id]?.valeur_totale_chf ?? CAPITAL)));
    return ligne;
  })];
}
