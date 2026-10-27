import { decisionsParDate, etatPf, indicateurs, pfParId, rapport, transactions } from "../data";
import { Carte, Courbes, Delta, Donut, Tuile, Vide, chf, couleur, dateCourte, pct } from "../ui";
import { LigneTransaction } from "./Transactions";

function grouper(positions: { valeur_chf: number }[], cle: (p: never) => string) {
  const m = new Map<string, number>();
  positions.forEach((p) => m.set(cle(p as never), (m.get(cle(p as never)) ?? 0) + p.valeur_chf));
  return [...m.entries()].map(([nom, valeur]) => ({ nom, valeur }));
}

export default function PagePortefeuille({ id }: { id: string }) {
  const p = pfParId[id];
  if (!p) return <Vide>Portefeuille introuvable.</Vide>;
  const e = etatPf(id);
  const ind = indicateurs?.portefeuilles[id];
  const tx = transactions.filter((t) => t.portefeuille === id).reverse();
  const parts = [...e.positions.map((x) => ({ ...x })), ...(e.cash_chf > 0.01 ? [{ secteur: "Cash", pays: "Cash", valeur_chf: e.cash_chf }] : [])];
  const predictions = Object.entries(decisionsParDate)
    .map(([d, dec]) => ({ date: d, pred: dec.portefeuilles?.[id]?.prediction }))
    .filter((x) => x.pred?.texte)
    .reverse();
  const verdicts = new Map((rapport?.predictions ?? []).filter((x) => x.portefeuille === id).map((x) => [x.date, x]));

  return (
    <div className="pile">
      <section className="pf-tete" style={{ ["--c" as string]: couleur(p) }}>
        <div className="pf-emoji" aria-hidden="true">{p.emoji}</div>
        <div>
          <h1>{p.nom}</h1>
          <p>{p.description}</p>
          <details>
            <summary>Les règles de la stratégie (figées avant l'étude)</summary>
            <ul>{p.regles.map((r) => <li key={r}>{r}</li>)}</ul>
          </details>
        </div>
      </section>

      <div className="tuiles">
        <Tuile label="Valeur" valeur={chf(e.valeur_totale_chf)} sous={<Delta v={e.gain_total_pct} />} />
        <Tuile label="Gain ou perte" valeur={<Delta v={e.gain_total_chf} unite="chf" fort />} sous={<>Aujourd'hui <Delta v={e.variation_jour_chf} unite="chf" /></>} />
        <Tuile label="Cash restant" valeur={chf(e.cash_chf)} sous={`${pct((e.cash_chf / e.valeur_totale_chf) * 100, 1)} du portefeuille`} />
        <Tuile label="Frais payés" valeur={chf(e.frais_cumules_chf)} sous={`${e.nb_ordres_cumules} ordre(s) exécuté(s)`} />
      </div>

      <Carte titre="Courbe de valeur">
        <Courbes ids={[id]} hauteur={260} modeInitial="chf" />
      </Carte>

      <Carte titre="Positions actuelles">
        {e.positions.length ? (
          <div className="table-defile">
            <table className="table">
              <thead>
                <tr><th>Entreprise</th><th>Secteur</th><th className="droite">Investi</th><th className="droite">Valeur</th><th className="droite">+/−</th><th className="droite">Part</th></tr>
              </thead>
              <tbody>
                {e.positions.map((x) => (
                  <tr key={x.ticker}>
                    <td><strong>{x.nom}</strong><span className="muet petit bloc">{x.ticker} · {x.pays} · {x.prix_cloture.toFixed(2)} {x.devise}</span></td>
                    <td>{x.secteur}</td>
                    <td className="droite nombre">{chf(x.cout_chf)}</td>
                    <td className="droite nombre">{chf(x.valeur_chf)}</td>
                    <td className="droite"><Delta v={x.gain_chf} unite="chf" /><span className="bloc petit"><Delta v={x.gain_pct} /></span></td>
                    <td className="droite nombre">{pct(x.part_pct, 1)}</td>
                  </tr>
                ))}
                <tr className="ligne-cash"><td>Cash</td><td /><td /><td className="droite nombre">{chf(e.cash_chf)}</td><td /><td className="droite nombre">{pct((e.cash_chf / e.valeur_totale_chf) * 100, 1)}</td></tr>
              </tbody>
            </table>
          </div>
        ) : <Vide>Aucune position : tout est en cash ({chf(e.cash_chf)}).</Vide>}
        <p className="muet petit">« Investi » inclut les frais d'achat. Valeurs à la dernière clôture, converties en CHF au taux du jour.</p>
      </Carte>

      <div className="grille-2">
        <Carte titre="Répartition par secteur"><Donut titre="Par secteur" parts={grouper(parts, (x: { secteur: string }) => x.secteur)} /></Carte>
        <Carte titre="Répartition par pays"><Donut titre="Par pays" parts={grouper(parts, (x: { pays: string }) => x.pays)} /></Carte>
      </div>

      {ind && (
        <Carte titre="Indicateurs" action={<a href="#/indicateurs" className="lien-fleche">Explications →</a>}>
          <div className="tuiles">
            <Tuile label="Volatilité quotidienne" valeur={pct(ind.volatilite_pct)} />
            <Tuile label="Pire chute" valeur={<Delta v={ind.pire_chute_pct} />} />
            <Tuile label="Écart avec le Patient" valeur={<Delta v={ind.ecart_patient_pts} unite="pts" />} />
            <Tuile label="Écart avec le Singe" valeur={<Delta v={ind.ecart_singe_pts} unite="pts" />} />
          </div>
        </Carte>
      )}

      <Carte titre="Prédictions vérifiables">
        {predictions.length ? (
          <ul className="liste-simple">
            {predictions.map(({ date, pred }) => {
              const v = verdicts.get(date);
              return (
                <li key={date}>
                  <span className="muet petit">{dateCourte(date)}</span> « {pred!.texte} »
                  {v && v.verdict !== "non vérifiable" && (
                    <span className={`etiquette ${v.verdict === "juste" ? "ok" : v.verdict === "fausse" ? "ko" : ""}`}>
                      {v.verdict === "juste" ? "✓ juste" : v.verdict === "fausse" ? "✗ fausse" : "⏳ en cours"}
                      {v.variation_pct != null && ` (${v.variation_pct > 0 ? "+" : ""}${v.variation_pct.toFixed(1)} %)`}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        ) : <Vide>Pas encore de prédiction.</Vide>}
      </Carte>

      <Carte titre="Transactions">
        {tx.length ? <ul className="liste-tx">{tx.map((t, i) => <LigneTransaction key={i} t={t} sansPf />)}</ul> : <Vide>Aucune transaction.</Vide>}
      </Carte>
    </div>
  );
}
