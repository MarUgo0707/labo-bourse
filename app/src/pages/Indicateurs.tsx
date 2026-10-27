import { indicateurs, portefeuilles } from "../data";
import { Carte, Delta, Pastille, Vide, chf, pct } from "../ui";

const COLONNES: [string, string, (v: NonNullable<typeof indicateurs>["portefeuilles"][string]) => React.ReactNode][] = [
  ["performance_pct", "Performance", (v) => <Delta v={v.performance_pct} />],
  ["volatilite_pct", "Volatilité", (v) => pct(v.volatilite_pct)],
  ["pire_chute_pct", "Pire chute", (v) => <Delta v={v.pire_chute_pct} />],
  ["ratio_rendement_risque", "Rendement / risque", (v) => v.ratio_rendement_risque?.toFixed(2) ?? "—"],
  ["taux_gagnants_pct", "Positions gagnantes", (v) => (v.taux_gagnants_pct == null ? "—" : `${v.taux_gagnants_pct.toFixed(0)} % (${v.nb_titres})`)],
  ["nb_ordres", "Rotation (ordres)", (v) => v.nb_ordres],
  ["poids_frais_pct", "Poids des frais", (v) => <>{pct(v.poids_frais_pct)}<span className="bloc petit muet">{chf(v.frais_chf)}</span></>],
  ["ecart_patient_pts", "Écart / Patient", (v) => <Delta v={v.ecart_patient_pts} unite="pts" />],
  ["ecart_singe_pts", "Écart / Singe", (v) => <Delta v={v.ecart_singe_pts} unite="pts" />],
];

export default function IndicateursPage() {
  if (!indicateurs) return <div className="pile"><h1>Indicateurs d'étude</h1><Vide>Les indicateurs seront calculés après la première clôture.</Vide></div>;
  const tries = [...portefeuilles].sort((a, b) => (indicateurs!.portefeuilles[b.id]?.performance_pct ?? 0) - (indicateurs!.portefeuilles[a.id]?.performance_pct ?? 0));
  return (
    <div className="pile">
      <h1>Indicateurs d'étude</h1>
      <Carte titre="Tableau de bord scientifique">
        <div className="table-defile">
          <table className="table table-indicateurs">
            <thead><tr><th>Portefeuille</th>{COLONNES.map(([k, t]) => <th key={k} className="droite">{t}</th>)}</tr></thead>
            <tbody>
              {tries.map((p) => {
                const v = indicateurs!.portefeuilles[p.id];
                return v ? <tr key={p.id}><th scope="row"><Pastille id={p.id} court /></th>{COLONNES.map(([k, , f]) => <td key={k} className="droite nombre">{f(v)}</td>)}</tr> : null;
              })}
            </tbody>
          </table>
        </div>
      </Carte>
      <Carte titre="Que veut dire chaque indicateur ?">
        <dl className="definitions">
          {COLONNES.map(([k, t]) => (
            <div key={k}><dt>{t}</dt><dd>{indicateurs!.explications[k]}</dd></div>
          ))}
        </dl>
      </Carte>
    </div>
  );
}
