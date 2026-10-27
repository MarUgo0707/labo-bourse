import { marked } from "marked";
import { datesSeances, decisionsParDate, etatsParDate, journaux, ordresParDate, portefeuilles } from "../data";
import { Carte, Delta, Pastille, Vide, chf, dateLongue } from "../ui";
import { LigneTransaction } from "./Transactions";

function Liste() {
  const dates = [...datesSeances].reverse();
  return (
    <div className="pile">
      <h1>Journal des séances</h1>
      {dates.length ? (
        <ul className="liste-journal">
          {dates.map((d) => {
            const o = ordresParDate[d];
            const e = etatsParDate[d];
            return (
              <li key={d}>
                <a href={`#/journal/${d}`}>
                  <strong>{dateLongue(d)}</strong>
                  <span className="muet petit">
                    {e?.jour ? `Jour ${e.jour} · ` : ""}
                    {o ? `${o.resume.acceptes} ordre(s) accepté(s), ${o.resume.rejetes} rejeté(s)` : decisionsParDate[d] ? "Décisions prises" : "Pas de séance"}
                    {e ? " · clôturée" : " · clôture à venir"}
                  </span>
                </a>
              </li>
            );
          })}
        </ul>
      ) : <Vide>Le journal se remplira dès la première séance.</Vide>}
    </div>
  );
}

export default function Journal({ date }: { date?: string }) {
  if (!date) return <Liste />;
  const dec = decisionsParDate[date];
  const ordres = ordresParDate[date];
  const etat = etatsParDate[date];
  const md = journaux[date];
  const i = datesSeances.indexOf(date);
  const rejetes = ordres?.ordres.filter((o) => o.statut === "rejeté") ?? [];

  return (
    <div className="pile">
      <nav className="precedent-suivant">
        {i > 0 ? <a href={`#/journal/${datesSeances[i - 1]}`}>← Séance précédente</a> : <span />}
        <a href="#/journal">Toutes les séances</a>
        {i < datesSeances.length - 1 ? <a href={`#/journal/${datesSeances[i + 1]}`}>Séance suivante →</a> : <span />}
      </nav>
      <h1>Séance du {dateLongue(date)}</h1>
      {dec?.simulation && <p className="bandeau-test">Séance simulée (test sans IA).</p>}

      {dec && (
        <Carte titre="Brief du marché">
          <p>{dec.brief_marche}</p>
          {dec.sources?.length ? (
            <details><summary>Sources ({dec.sources.length})</summary>
              <ul>{dec.sources.map((s) => <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer noopener">{s.titre}</a></li>)}</ul>
            </details>
          ) : null}
        </Carte>
      )}

      {dec && (
        <Carte titre="Décisions par portefeuille">
          <ul className="decisions">
            {portefeuilles.filter((p) => p.pilote === "ia").map((p) => {
              const d = dec.portefeuilles?.[p.id];
              return (
                <li key={p.id}>
                  <Pastille id={p.id} />
                  <span className={`etiquette ${d?.decision === "agir" ? "ok" : ""}`}>{d?.decision === "agir" ? `${d.ordres.length} ordre(s)` : "Ne fait rien"}</span>
                  <p>{d?.resume ?? "Aucune décision enregistrée."}</p>
                  {d?.prediction?.texte && <p className="muet petit">Prédiction : « {d.prediction.texte} »</p>}
                </li>
              );
            })}
          </ul>
        </Carte>
      )}

      <Carte titre="Ordres rejetés par le validateur">
        {rejetes.length ? (
          <ul className="liste-simple">
            {rejetes.map((o, k) => <li key={k}><Pastille id={o.portefeuille} court /> — {o.action} {o.nom} ({o.ticker}) : <strong>{o.motif}</strong></li>)}
          </ul>
        ) : <Vide>{ordres ? "Aucun ordre rejeté." : "Pas encore validé."}</Vide>}
      </Carte>

      <Carte titre="Résultat le soir même">
        {etat ? (
          <>
            <div className="table-defile">
              <table className="table">
                <thead><tr><th>Portefeuille</th><th className="droite">Valeur</th><th className="droite">Sur la journée</th></tr></thead>
                <tbody>
                  {portefeuilles.map((p) => {
                    const e = etat.portefeuilles[p.id];
                    return (
                      <tr key={p.id}>
                        <td><Pastille id={p.id} /></td>
                        <td className="droite nombre">{chf(e.valeur_totale_chf)}</td>
                        <td className="droite"><Delta v={e.variation_jour_chf} unite="chf" /> <span className="petit"><Delta v={e.variation_jour_pct} /></span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {etat.transactions.length > 0 && <ul className="liste-tx">{etat.transactions.map((t, k) => <LigneTransaction key={k} t={t} />)}</ul>}
          </>
        ) : <Vide>La clôture de 23h00 n'a pas encore eu lieu.</Vide>}
      </Carte>

      <Carte titre="Le carnet de bord complet">
        {md ? <article className="markdown" dangerouslySetInnerHTML={{ __html: marked.parse(md, { async: false }) as string }} /> : <Vide>Pas de journal pour ce jour.</Vide>}
      </Carte>
    </div>
  );
}
