import { useState } from "react";
import { etatPf, indicateurs, portefeuilles } from "../data";
import { Carte, Courbes, Delta, Pastille, Vide, chf, couleur, pct } from "../ui";

export default function Comparateur() {
  const [choix, setChoix] = useState<string[]>(["patient", "journaliste", "singe"]);
  const basculer = (id: string) =>
    setChoix((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 3 ? [...c.slice(1), id] : [...c, id]));
  const ids = portefeuilles.map((p) => p.id).filter((id) => choix.includes(id));

  const lignes: [string, (id: string) => React.ReactNode][] = [
    ["Valeur", (id) => chf(etatPf(id).valeur_totale_chf)],
    ["Performance", (id) => <Delta v={etatPf(id).gain_total_pct} />],
    ["Volatilité quotidienne", (id) => pct(indicateurs?.portefeuilles[id]?.volatilite_pct)],
    ["Pire chute", (id) => <Delta v={indicateurs?.portefeuilles[id]?.pire_chute_pct} />],
    ["Rendement / risque", (id) => indicateurs?.portefeuilles[id]?.ratio_rendement_risque?.toFixed(2) ?? "—"],
    ["Frais payés", (id) => chf(etatPf(id).frais_cumules_chf)],
    ["Ordres exécutés", (id) => etatPf(id).nb_ordres_cumules],
    ["Cash", (id) => chf(etatPf(id).cash_chf)],
  ];

  return (
    <div className="pile">
      <h1>Comparateur</h1>
      <Carte titre="Choisir 2 ou 3 portefeuilles">
        <div className="choix-pf">
          {portefeuilles.map((p) => (
            <button key={p.id} type="button" aria-pressed={choix.includes(p.id)} onClick={() => basculer(p.id)} style={{ ["--c" as string]: couleur(p) }}>
              {p.emoji} {p.nom}
            </button>
          ))}
        </div>
      </Carte>
      {ids.length < 2 ? <Vide>Choisissez au moins deux portefeuilles.</Vide> : (
        <>
          <Carte titre="Courbes"><Courbes ids={ids} hauteur={300} /></Carte>
          <Carte titre="Risques et frais">
            <div className="table-defile">
              <table className="table">
                <thead><tr><th />{ids.map((id) => <th key={id} className="droite"><Pastille id={id} court /></th>)}</tr></thead>
                <tbody>
                  {lignes.map(([nom, f]) => (
                    <tr key={nom}><th scope="row">{nom}</th>{ids.map((id) => <td key={id} className="droite nombre">{f(id)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Carte>
        </>
      )}
    </div>
  );
}
