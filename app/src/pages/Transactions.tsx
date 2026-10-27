import { useMemo, useState } from "react";
import { portefeuilles, transactions, type Transaction } from "../data";
import { Carte, Delta, Pastille, Vide, chf, dateCourte } from "../ui";

export function LigneTransaction({ t, sansPf }: { t: Transaction; sansPf?: boolean }) {
  const achat = t.sens === "achat";
  return (
    <li className={`tx ${t.statut === "annulé" ? "tx-annule" : ""}`}>
      <div className="tx-tete">
        <span className={`tx-sens ${achat ? "achat" : "vente"}`}>{achat ? "Achat" : "Vente"}</span>
        <strong>{t.nom}</strong>
        <span className="muet petit">{t.ticker}</span>
        <span className="tx-montant nombre">{t.statut === "exécuté" ? chf(t.montant_chf) : chf(t.montant_demande_chf)}</span>
      </div>
      <div className="tx-meta petit muet">
        {dateCourte(t.date)} · {!sansPf && <><Pastille id={t.portefeuille} court /> · </>}
        {t.secteur} · {t.pays}
        {t.statut === "exécuté" && <> · frais {chf(t.frais_chf)} · prix {t.prix_execution?.toFixed(2)} {t.devise}</>}
        {t.resultat_realise_chf != null && <> · résultat <Delta v={t.resultat_realise_chf} unite="chf" /></>}
      </div>
      {t.raison && <p className="tx-raison">« {t.raison} »{t.confiance && <span className="muet petit"> — confiance {t.confiance}{t.horizon && `, horizon ${t.horizon}`}</span>}</p>}
      {t.statut === "annulé" && <p className="tx-motif">⊘ Annulé : {t.motif}</p>}
      {t.note && <p className="tx-motif">ℹ︎ {t.note}</p>}
    </li>
  );
}

export default function Transactions() {
  const [pf, setPf] = useState("");
  const [secteur, setSecteur] = useState("");
  const [sens, setSens] = useState("");
  const [date, setDate] = useState("");
  const secteurs = useMemo(() => [...new Set(transactions.map((t) => t.secteur))].sort(), []);
  const dates = useMemo(() => [...new Set(transactions.map((t) => t.date))].sort().reverse(), []);
  const liste = transactions
    .filter((t) => (!pf || t.portefeuille === pf) && (!secteur || t.secteur === secteur) && (!sens || t.sens === sens || t.statut === sens) && (!date || t.date === date))
    .slice()
    .reverse();

  return (
    <div className="pile">
      <h1>Fil des transactions</h1>
      <div className="filtres">
        <label>Portefeuille
          <select value={pf} onChange={(e) => setPf(e.target.value)}>
            <option value="">Tous</option>
            {portefeuilles.map((p) => <option key={p.id} value={p.id}>{p.emoji} {p.nom}</option>)}
          </select>
        </label>
        <label>Secteur
          <select value={secteur} onChange={(e) => setSecteur(e.target.value)}>
            <option value="">Tous</option>
            {secteurs.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label>Type
          <select value={sens} onChange={(e) => setSens(e.target.value)}>
            <option value="">Tous</option>
            <option value="achat">Achats</option>
            <option value="vente">Ventes</option>
            <option value="annulé">Annulés</option>
          </select>
        </label>
        <label>Date
          <select value={date} onChange={(e) => setDate(e.target.value)}>
            <option value="">Toutes</option>
            {dates.map((d) => <option key={d} value={d}>{dateCourte(d)}</option>)}
          </select>
        </label>
      </div>
      <Carte titre={`${liste.length} transaction(s)`}>
        {liste.length ? <ul className="liste-tx">{liste.map((t, i) => <LigneTransaction key={i} t={t} />)}</ul> : <Vide>Aucune transaction ne correspond.</Vide>}
      </Carte>
      <p className="muet petit">Les ordres refusés le matin par le validateur ne sont pas des transactions : ils figurent dans le journal de chaque séance.</p>
    </div>
  );
}
