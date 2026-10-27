import { pfParId, rapport } from "../data";
import { Carte, Delta, Pastille, Vide, chf, dateLongue } from "../ui";

export default function RapportPage() {
  if (!rapport) return <div className="pile"><h1>Rapport final</h1><Vide>Le rapport sera généré après la première clôture, puis finalisé après la dernière séance.</Vide></div>;
  const r = rapport;
  const tranchees = r.predictions.filter((p) => p.verdict === "juste" || p.verdict === "fausse");
  const justes = tranchees.filter((p) => p.verdict === "juste").length;
  return (
    <div className="pile rapport">
      <div className="rapport-tete">
        <h1>Rapport {r.provisoire ? "provisoire" : "final"}</h1>
        <button type="button" className="bouton" onClick={() => window.print()}>Imprimer / PDF</button>
      </div>
      <p className="muet">
        Du {dateLongue(r.periode.debut)} au {dateLongue(r.periode.fin)} · {r.periode.seances_cloturees} séance(s) clôturée(s) sur {r.periode.nb_jours}
        {r.provisoire && " · ce rapport se met à jour chaque soir jusqu'à la fin de l'étude"}.
      </p>

      <aside className="encadre-honnete">
        <strong>À lire avant tout.</strong> Un mois est un échantillon très court. Sur une période aussi brève, le hasard
        pèse souvent plus lourd que la qualité d'une stratégie : un bon classement ici ne prouve pas qu'une stratégie est
        bonne, et un mauvais ne prouve pas qu'elle est mauvaise. Le Singe sert justement à mesurer ce que le hasard seul
        peut produire. Argent fictif, exécution simulée.
      </aside>

      <Carte titre="Classement">
        <div className="table-defile">
          <table className="table">
            <thead><tr><th>#</th><th>Portefeuille</th><th className="droite">Valeur</th><th className="droite">Performance</th><th className="droite">Sans les frais</th><th className="droite">Frais</th><th className="droite">Ordres</th></tr></thead>
            <tbody>
              {r.classement.map((c, i) => (
                <tr key={c.id}>
                  <td>{i + 1}</td><td><Pastille id={c.id} /></td>
                  <td className="droite nombre">{chf(c.valeur_chf)}</td>
                  <td className="droite"><Delta v={c.performance_pct} /></td>
                  <td className="droite"><Delta v={c.performance_sans_frais_pct} /></td>
                  <td className="droite nombre">{chf(c.frais_chf)}</td>
                  <td className="droite nombre">{c.nb_ordres}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Carte>

      <Carte titre="Leçons retenues">
        <ul className="liste-simple">{r.lecons.map((l) => <li key={l}>{l}</li>)}</ul>
      </Carte>

      <div className="grille-2">
        <Carte titre="Par secteur">
          {r.secteurs.length ? (
            <ul className="liste-simple">
              {r.secteurs.map((s) => <li key={s.secteur} className="ligne-espacee"><span>{s.secteur} <span className="muet petit">({s.nb_titres})</span></span><span><Delta v={s.resultat_chf} unite="chf" /> · <Delta v={s.resultat_pct} /></span></li>)}
            </ul>
          ) : <Vide>Pas encore de mise.</Vide>}
        </Carte>
        <Carte titre="Par action (top 10)">
          {r.titres.length ? (
            <ul className="liste-simple">
              {r.titres.slice(0, 10).map((t) => <li key={t.ticker} className="ligne-espacee"><span>{t.nom} <span className="muet petit">{t.ticker}</span></span><Delta v={t.resultat_chf} unite="chf" /></li>)}
            </ul>
          ) : <Vide>Pas encore de mise.</Vide>}
        </Carte>
      </div>

      <div className="grille-2">
        <Carte titre="Meilleurs paris">
          <ul className="liste-simple">{r.meilleurs_paris.map((p) => <li key={p.portefeuille + p.ticker} className="ligne-espacee"><span><Pastille id={p.portefeuille} court /> · {p.nom}</span><Delta v={p.resultat_pct} /></li>)}</ul>
        </Carte>
        <Carte titre="Pires paris">
          <ul className="liste-simple">{r.pires_paris.map((p) => <li key={p.portefeuille + p.ticker} className="ligne-espacee"><span><Pastille id={p.portefeuille} court /> · {p.nom}</span><Delta v={p.resultat_pct} /></li>)}</ul>
        </Carte>
      </div>

      <Carte titre="Impact des frais">
        <p>
          Avec 200 CHF, chaque ordre coûte cher : la colonne « Sans les frais » du classement montre la performance qu'aurait
          eue chaque stratégie sans frais. En moyenne, les frais ont représenté{" "}
          <strong>{(r.classement.reduce((s, c) => s + c.poids_frais_pct, 0) / Math.max(1, r.classement.length)).toFixed(2)} %</strong> du capital.
        </p>
      </Carte>

      <Carte titre={`Prédictions vérifiables · ${justes} juste(s) sur ${tranchees.length}`}>
        <p className="muet petit">Deviner « hausse » ou « baisse » au hasard donne environ 50 % de réussite.</p>
        {r.predictions.length ? (
          <ul className="liste-simple">
            {r.predictions.map((p, i) => (
              <li key={i}>
                <span className="muet petit">{p.date}</span> {pfParId[p.portefeuille]?.emoji} « {p.texte} »{" "}
                <span className={`etiquette ${p.verdict === "juste" ? "ok" : p.verdict === "fausse" ? "ko" : ""}`}>
                  {p.verdict === "juste" ? "✓ juste" : p.verdict === "fausse" ? "✗ fausse" : p.verdict === "en cours" ? "⏳ en cours" : "non vérifiable"}
                </span>
              </li>
            ))}
          </ul>
        ) : <Vide>Aucune prédiction pour l'instant.</Vide>}
      </Carte>
    </div>
  );
}
