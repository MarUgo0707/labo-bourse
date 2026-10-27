import { useState } from "react";
import { dernierEtat, portefeuilles } from "../data";
import { Carte, Delta, Pastille, Vide, chf } from "../ui";

type Ligne = { ticker: string; nom: string; secteur: string; investi: number; resultat: number; par: { pf: string; investi: number; resultat: number }[] };

export default function Explorer() {
  const [tri, setTri] = useState<"investi" | "resultat" | "pct">("investi");
  if (!dernierEtat) return <div className="pile"><h1>Explorer les mises</h1><Vide>Les mises apparaîtront après la première clôture.</Vide></div>;

  const titres = new Map<string, Ligne>();
  const cellules = new Map<string, { investi: number; resultat: number }>();
  for (const p of portefeuilles) {
    for (const [tk, b] of Object.entries(dernierEtat.portefeuilles[p.id].bilan_titres)) {
      const l = titres.get(tk) ?? { ticker: tk, nom: b.nom, secteur: b.secteur, investi: 0, resultat: 0, par: [] };
      l.investi += b.investi_chf;
      l.resultat += b.resultat_chf;
      l.par.push({ pf: p.id, investi: b.investi_chf, resultat: b.resultat_chf });
      titres.set(tk, l);
      const k = `${b.secteur}|${p.id}`;
      const c = cellules.get(k) ?? { investi: 0, resultat: 0 };
      c.investi += b.investi_chf;
      c.resultat += b.resultat_chf;
      cellules.set(k, c);
    }
  }
  const secteurs = [...new Set([...cellules.keys()].map((k) => k.split("|")[0]))].sort();
  const liste = [...titres.values()].sort((a, b) =>
    tri === "investi" ? b.investi - a.investi : tri === "resultat" ? b.resultat - a.resultat : b.resultat / b.investi - a.resultat / a.investi);
  const maxAbs = Math.max(1, ...[...cellules.values()].map((c) => Math.abs((c.resultat / c.investi) * 100)));

  return (
    <div className="pile">
      <h1>Explorer les mises</h1>
      <p className="muet">Toutes les entreprises et tous les secteurs sur lesquels au moins un portefeuille a misé depuis le début (positions vendues comprises).</p>

      <Carte titre="Carte de chaleur des secteurs">
        <p className="muet petit">Résultat en % de la mise, par secteur et par portefeuille. Vert ▲ = gain, rouge ▼ = perte, gris = proche de zéro.</p>
        <div className="table-defile">
          <table className="chaleur">
            <thead>
              <tr><th>Secteur</th>{portefeuilles.map((p) => <th key={p.id} title={p.nom}><span aria-hidden="true">{p.emoji}</span><span className="sr">{p.nom}</span></th>)}</tr>
            </thead>
            <tbody>
              {secteurs.map((s) => (
                <tr key={s}>
                  <th scope="row">{s}</th>
                  {portefeuilles.map((p) => {
                    const c = cellules.get(`${s}|${p.id}`);
                    if (!c) return <td key={p.id} className="vide-cellule" />;
                    const v = (c.resultat / c.investi) * 100;
                    const intensite = Math.min(1, Math.abs(v) / maxAbs);
                    const fond = Math.abs(v) < 0.05 ? "var(--neutre-fond)" : `color-mix(in oklab, ${v > 0 ? "var(--hausse-fond)" : "var(--baisse-fond)"} ${Math.round(25 + 75 * intensite)}%, var(--surface))`;
                    return (
                      <td key={p.id} style={{ background: fond }} title={`${p.nom} · ${s} : ${chf(c.investi)} misés, résultat ${chf(c.resultat)}`}>
                        <span className="petit">{v > 0.05 ? "▲" : v < -0.05 ? "▼" : "■"} {Math.abs(v).toFixed(1)}</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Carte>

      <Carte titre={`${liste.length} entreprise(s)`} action={
        <label className="petit">Trier par{" "}
          <select value={tri} onChange={(e) => setTri(e.target.value as typeof tri)}>
            <option value="investi">Montant misé</option>
            <option value="resultat">Résultat en CHF</option>
            <option value="pct">Résultat en %</option>
          </select>
        </label>}>
        <ul className="liste-mises">
          {liste.map((l) => (
            <li key={l.ticker}>
              <div className="mise-tete">
                <span><strong>{l.nom}</strong> <span className="muet petit">{l.ticker} · {l.secteur}</span></span>
                <span className="droite"><span className="nombre">{chf(l.investi)}</span> misés · <Delta v={l.resultat} unite="chf" /> <span className="petit">(<Delta v={(l.resultat / l.investi) * 100} />)</span></span>
              </div>
              <div className="mise-par petit">
                {l.par.map((x) => <span key={x.pf}><Pastille id={x.pf} court /> {chf(x.investi)} → <Delta v={x.resultat} unite="chf" /></span>)}
              </div>
            </li>
          ))}
        </ul>
      </Carte>
    </div>
  );
}
