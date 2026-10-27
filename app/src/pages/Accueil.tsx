import { decisionsParDate, dernierEtat, etatPf, etude, joursEtude, ordresParDate, portefeuilles } from "../data";
import { Carte, Courbes, Delta, Pastille, Vide, chf, couleur, dateLongue } from "../ui";

export default function Accueil() {
  const classement = [...portefeuilles].sort((a, b) => etatPf(b.id).valeur_totale_chf - etatPf(a.id).valeur_totale_chf);
  const dateDecision = Object.keys(decisionsParDate).sort().at(-1);
  const decision = dateDecision ? decisionsParDate[dateDecision] : null;
  const ordres = dateDecision ? ordresParDate[dateDecision] : null;
  const jour = dernierEtat?.jour ?? 0;
  const progression = joursEtude.length ? Math.min(100, (jour / joursEtude.length) * 100) : 0;

  return (
    <div className="pile">
      <section className="intro">
        <h1>9 portefeuilles, 200 CHF chacun, un mois</h1>
        <p>
          Chaque matin de bourse à 8h00, Claude décide pour huit stratégies. Un script exécute les ordres au vrai prix
          d'ouverture, avec les frais. Le Singe joue au hasard pour servir de témoin.
        </p>
        <div className="progression" role="progressbar" aria-valuemin={0} aria-valuemax={joursEtude.length} aria-valuenow={jour}
          aria-label={`Jour ${jour} sur ${joursEtude.length}`}>
          <div style={{ width: `${progression}%` }} />
        </div>
        <p className="muet petit">
          {jour ? `Jour ${jour} sur ${joursEtude.length}` : `L'étude commence le ${dateLongue(etude.date_debut)}`} · du{" "}
          {dateLongue(etude.date_debut)} au {dateLongue(etude.date_fin)}
          {dernierEtat && <> · dernière clôture : {dateLongue(dernierEtat.date)}</>}
        </p>
      </section>

      <Carte titre={decision ? `La séance de ce matin · ${dateLongue(decision.date)}` : "La séance de ce matin"}
        action={decision && <a href={`#/journal/${decision.date}`} className="lien-fleche">Lire le journal →</a>}>
        {decision ? (
          <>
            <ul className="trois-lignes">
              {(decision.points_cles?.length ? decision.points_cles : [decision.brief_marche ?? ""]).slice(0, 3).map((l, i) => <li key={i}>{l}</li>)}
            </ul>
            {ordres && (
              <p className="muet petit">
                {ordres.resume.acceptes} ordre(s) accepté(s) · {ordres.resume.rejetes} rejeté(s) par le validateur
              </p>
            )}
          </>
        ) : (
          <Vide>Aucune séance pour l'instant. La première aura lieu le {dateLongue(etude.date_debut)} à 8h00.</Vide>
        )}
      </Carte>

      <Carte titre="Classement">
        <ol className="classement">
          {classement.map((p, i) => {
            const e = etatPf(p.id);
            return (
              <li key={p.id} style={{ ["--c" as string]: couleur(p) }}>
                <a href={`#/p/${p.id}`} className="classement-ligne">
                  <span className="rang">{i + 1}</span>
                  <span className="classement-nom">
                    <span className="classement-emoji" aria-hidden="true">{p.emoji}</span>
                    <span>
                      <strong>{p.nom}</strong>
                      <span className="muet petit bloc">{p.pilote === "script" ? "Témoin : hasard" : p.description.split(":")[0].split(".")[0]}</span>
                    </span>
                  </span>
                  <span className="classement-chiffres">
                    <strong className="nombre">{chf(e.valeur_totale_chf)}</strong>
                    <span className="petit"><Delta v={e.gain_total_chf} unite="chf" /> · <Delta v={e.gain_total_pct} /></span>
                    <span className="petit muet">Aujourd'hui <Delta v={e.variation_jour_pct} /></span>
                  </span>
                </a>
              </li>
            );
          })}
        </ol>
      </Carte>

      <Carte titre="Évolution de tous les portefeuilles">
        {dernierEtat ? <Courbes ids={portefeuilles.map((p) => p.id)} hauteur={340} /> : <Vide>La courbe apparaîtra après la première clôture du soir.</Vide>}
        <p className="muet petit">La ligne pointillée est le Singe (hasard). Survolez la légende pour isoler une courbe.</p>
      </Carte>

      <Carte titre="Les stratégies">
      <div className="grille-2">
        {portefeuilles.map((p) => (
          <a key={p.id} href={`#/p/${p.id}`} className="mini-pf" style={{ ["--c" as string]: couleur(p) }}>
            <Pastille id={p.id} lien={false} />
            <span className="muet petit">{p.description}</span>
          </a>
        ))}
      </div>
      </Carte>
    </div>
  );
}
