import { contexteParDate, decisionsParDate, etatsParDate, joursEtude, ordresParDate } from "../data";
import { Carte, Pastille, Tuile, Vide, dateLongue } from "../ui";

export default function Sante() {
  const aujourdhui = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Zurich" });
  const passes = joursEtude.filter((d) => d <= aujourdhui);
  const reussies = Object.keys(ordresParDate).filter((d) => ordresParDate[d].session_ia === "ok").sort();
  const ratees = passes.filter((d) => !decisionsParDate[d] || ordresParDate[d]?.session_ia !== "ok");
  const sansCloture = passes.filter((d) => !etatsParDate[d] && d < aujourdhui);
  const rejets = Object.values(ordresParDate).flatMap((o) => o.ordres.filter((x) => x.statut === "rejeté").map((x) => ({ ...x, date: o.date })));
  const derniereCloture = Object.keys(etatsParDate).sort().at(-1);
  const dernierContexte = Object.keys(contexteParDate).sort().at(-1);

  return (
    <div className="pile">
      <h1>Santé du système</h1>
      <div className="tuiles">
        <Tuile label="Dernière séance réussie" valeur={reussies.at(-1) ? dateLongue(reussies.at(-1)!) : "aucune"} />
        <Tuile label="Dernière clôture" valeur={derniereCloture ? dateLongue(derniereCloture) : "aucune"} />
        <Tuile label="Séances ratées" valeur={`${ratees.length} sur ${passes.length}`} />
        <Tuile label="Ordres rejetés" valeur={rejets.length} />
      </div>
      {dernierContexte && <p className="muet petit">Dernière préparation de séance : {contexteParDate[dernierContexte].genere_le.replace("T", " à ").replace("Z", " UTC")}.</p>}

      <Carte titre="Séances ratées">
        {ratees.length ? <ul className="liste-simple">{ratees.map((d) => <li key={d}><a href={`#/journal/${d}`}>{dateLongue(d)}</a> — {ordresParDate[d] ? `séance IA : ${ordresParDate[d].session_ia}` : "aucune séance enregistrée"}</li>)}</ul> : <Vide>Aucune séance ratée. ✓</Vide>}
        <p className="muet petit">Une séance ratée n'est jamais rattrapée : décider après coup avec des informations connues plus tard serait de la triche.</p>
      </Carte>
      <Carte titre="Clôtures manquantes">
        {sansCloture.length ? <ul className="liste-simple">{sansCloture.map((d) => <li key={d}>{dateLongue(d)}</li>)}</ul> : <Vide>Aucune clôture manquante. ✓</Vide>}
        <p className="muet petit">Une clôture manquante est rattrapée automatiquement le soir suivant (les prix d'exécution sont des faits, pas des décisions).</p>
      </Carte>
      <Carte titre="Ordres rejetés">
        {rejets.length ? <ul className="liste-simple">{rejets.reverse().map((o, i) => <li key={i}><span className="muet petit">{o.date}</span> <Pastille id={o.portefeuille} court /> {o.action} {o.ticker} : {o.motif}</li>)}</ul> : <Vide>Aucun ordre rejeté.</Vide>}
      </Carte>
    </div>
  );
}
