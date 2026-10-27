import { useEffect, useMemo, useState, type ReactNode } from "react";
import { CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CAPITAL, pfParId, serie, type Portefeuille } from "./data";

// ------------------------------------------------------------ formats

const nf = (min: number, max: number) => new Intl.NumberFormat("fr-CH", { minimumFractionDigits: min, maximumFractionDigits: max });
const n2 = nf(2, 2);
const n1 = nf(1, 1);

export const chf = (v: number | null | undefined) => (v == null ? "—" : `${n2.format(v)} CHF`);
export const pct = (v: number | null | undefined, d = 2) => (v == null ? "—" : `${(d === 1 ? n1 : n2).format(v)} %`);
export const signe = (v: number) => (v > 0.0049 ? "+" : v < -0.0049 ? "−" : "");
export const dateLongue = (iso: string) =>
  /^\d{4}-\d{2}-\d{2}$/.test(iso)
    ? new Date(iso + "T12:00:00Z").toLocaleDateString("fr-CH", { weekday: "long", day: "numeric", month: "long", year: "numeric" })
    : iso;
export const dateCourte = (iso: string) =>
  /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(iso + "T12:00:00Z").toLocaleDateString("fr-CH", { day: "numeric", month: "short" }) : iso;

/** Variation avec flèche ▲▼ (jamais la couleur seule). */
export function Delta({ v, unite = "pct", fort }: { v: number | null | undefined; unite?: "pct" | "chf" | "pts"; fort?: boolean }) {
  if (v == null) return <span className="muet">—</span>;
  const cls = v > 0.0049 ? "hausse" : v < -0.0049 ? "baisse" : "neutre";
  const fleche = cls === "hausse" ? "▲" : cls === "baisse" ? "▼" : "■";
  const abs = Math.abs(v);
  const texte = unite === "chf" ? `${n2.format(abs)} CHF` : unite === "pts" ? `${n2.format(abs)} pts` : `${n2.format(abs)} %`;
  return (
    <span className={`delta ${cls}${fort ? " fort" : ""}`}>
      <span aria-hidden="true">{fleche}</span> {signe(v)}{texte}
    </span>
  );
}

// ------------------------------------------------------------ thème

export type Theme = "auto" | "clair" | "sombre";

function lireTheme(): Theme {
  try {
    const t = localStorage.getItem("theme");
    return t === "clair" || t === "sombre" ? t : "auto";
  } catch {
    return "auto";
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(lireTheme);
  const media = typeof window !== "undefined" ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  const [systemeSombre, setSystemeSombre] = useState(media?.matches ?? false);
  useEffect(() => {
    if (!media) return;
    const f = (e: MediaQueryListEvent) => setSystemeSombre(e.matches);
    media.addEventListener("change", f);
    return () => media.removeEventListener("change", f);
  }, [media]);
  useEffect(() => {
    const racine = document.documentElement;
    if (theme === "auto") racine.removeAttribute("data-theme");
    else racine.setAttribute("data-theme", theme === "sombre" ? "dark" : "light");
    try {
      localStorage.setItem("theme", theme);
    } catch {
      /* stockage indisponible : le thème reste valable pour la visite */
    }
  }, [theme]);
  const sombre = theme === "sombre" || (theme === "auto" && systemeSombre);
  return { theme, setTheme, sombre };
}

let sombreCourant = false;
export const definirSombre = (s: boolean) => (sombreCourant = s);
export const couleur = (p: Portefeuille | string) => {
  const pf = typeof p === "string" ? pfParId[p] : p;
  return pf ? (sombreCourant ? pf.couleur.sombre : pf.couleur.clair) : "#888";
};

// ------------------------------------------------------------ petits composants

export function Pastille({ id, lien = true, court }: { id: string; lien?: boolean; court?: boolean }) {
  const p = pfParId[id];
  if (!p) return <span>{id}</span>;
  const contenu = (
    <>
      <span className="pastille-point" style={{ background: couleur(p) }} aria-hidden="true" />
      <span aria-hidden="true">{p.emoji}</span> {court ? p.nom.replace(/^Le /, "") : p.nom}
    </>
  );
  return lien ? <a className="pastille" href={`#/p/${id}`}>{contenu}</a> : <span className="pastille">{contenu}</span>;
}

export function Carte({ titre, children, action, className }: { titre?: ReactNode; children: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <section className={`carte ${className ?? ""}`}>
      {(titre || action) && (
        <header className="carte-tete">
          {titre && <h2>{titre}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function Tuile({ label, valeur, sous }: { label: string; valeur: ReactNode; sous?: ReactNode }) {
  return (
    <div className="tuile">
      <div className="tuile-label">{label}</div>
      <div className="tuile-valeur">{valeur}</div>
      {sous && <div className="tuile-sous">{sous}</div>}
    </div>
  );
}

export function Vide({ children }: { children: ReactNode }) {
  return <p className="vide">{children}</p>;
}

export function Bascule<T extends string>({ options, valeur, onChange, label }: { options: [T, string][]; valeur: T; onChange: (v: T) => void; label: string }) {
  return (
    <div className="bascule" role="group" aria-label={label}>
      {options.map(([v, t]) => (
        <button key={v} type="button" aria-pressed={valeur === v} onClick={() => onChange(v)}>{t}</button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------ graphiques

function InfoBulle({ active, payload, label, mode }: { active?: boolean; payload?: { dataKey: string; value: number }[]; label?: string; mode: "chf" | "pct" }) {
  if (!active || !payload?.length) return null;
  const tries = [...payload].sort((a, b) => b.value - a.value);
  return (
    <div className="infobulle">
      <div className="infobulle-titre">{label === "Départ" ? "Départ" : dateLongue(label ?? "")}</div>
      {tries.map((p) => (
        <div key={p.dataKey} className="infobulle-ligne">
          <span><span className="pastille-point" style={{ background: couleur(p.dataKey) }} /> {pfParId[p.dataKey]?.emoji} {pfParId[p.dataKey]?.nom}</span>
          <strong>{mode === "chf" ? chf(p.value) : `${signe(p.value)}${n2.format(Math.abs(p.value))} %`}</strong>
        </div>
      ))}
    </div>
  );
}

export function Courbes({ ids, hauteur = 300, modeInitial = "pct" }: { ids: string[]; hauteur?: number; modeInitial?: "chf" | "pct" }) {
  const [mode, setMode] = useState<"chf" | "pct">(modeInitial);
  const [focus, setFocus] = useState<string | null>(null);
  const donnees = useMemo(() => serie(ids, mode), [ids, mode]);
  const reference = mode === "chf" ? CAPITAL : 0;
  return (
    <div className="courbes">
      <div className="courbes-barre">
        <Bascule label="Unité du graphique" options={[["pct", "En %"], ["chf", "En CHF"]]} valeur={mode} onChange={setMode} />
      </div>
      <div style={{ height: hauteur }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={donnees} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--grille)" vertical={false} />
            <XAxis dataKey="date" tickFormatter={dateCourte} tick={{ fill: "var(--texte-2)", fontSize: 12 }} stroke="var(--axe)" minTickGap={24} />
            <YAxis
              width={56}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => (mode === "chf" ? n1.format(v) : `${n1.format(v)} %`)}
              tick={{ fill: "var(--texte-2)", fontSize: 12 }}
              stroke="var(--axe)"
            />
            <ReferenceLine y={reference} stroke="var(--texte-3)" strokeDasharray="4 4" />
            <Tooltip content={<InfoBulle mode={mode} />} cursor={{ stroke: "var(--texte-3)", strokeWidth: 1 }} />
            {ids.map((id) => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                stroke={couleur(id)}
                strokeWidth={focus === id ? 3 : 2}
                strokeOpacity={focus && focus !== id ? 0.2 : 1}
                strokeDasharray={pfParId[id]?.pilote === "script" ? "6 4" : undefined}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {ids.length > 1 && (
        <ul className="legende" aria-label="Légende">
          {ids.map((id) => (
            <li key={id}>
              <button type="button" onMouseEnter={() => setFocus(id)} onMouseLeave={() => setFocus(null)}
                onFocus={() => setFocus(id)} onBlur={() => setFocus(null)} onClick={() => (location.hash = `#/p/${id}`)}>
                <span className={`legende-trait${pfParId[id]?.pilote === "script" ? " pointille" : ""}`} style={{ borderColor: couleur(id) }} />
                {pfParId[id]?.emoji} {pfParId[id]?.nom}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Palette catégorielle (validée) pour les parts : secteur ou pays.
const PARTS_CLAIR = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const PARTS_SOMBRE = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];

export function Donut({ parts, titre }: { parts: { nom: string; valeur: number }[]; titre: string }) {
  const total = parts.reduce((s, p) => s + p.valeur, 0);
  if (!total) return <Vide>Pas encore de données.</Vide>;
  // Au-delà de 7 parts, le reste est regroupé dans « Autres ».
  const tries = [...parts].sort((a, b) => b.valeur - a.valeur);
  const visibles = tries.length > 8 ? [...tries.slice(0, 7), { nom: "Autres", valeur: tries.slice(7).reduce((s, p) => s + p.valeur, 0) }] : tries;
  const pal = sombreCourant ? PARTS_SOMBRE : PARTS_CLAIR;
  return (
    <figure className="donut">
      <div className="donut-graphe" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={visibles} dataKey="valeur" nameKey="nom" innerRadius="62%" outerRadius="95%" paddingAngle={1.5}
              stroke="var(--surface)" strokeWidth={2} isAnimationActive={false}>
              {visibles.map((p, i) => <Cell key={p.nom} fill={p.nom === "Autres" ? "var(--texte-3)" : pal[i % pal.length]} />)}
            </Pie>
            <Tooltip formatter={(v: number, n: string) => [`${chf(v)} · ${n1.format((v / total) * 100)} %`, n]}
              contentStyle={{ background: "var(--surface)", border: "1px solid var(--bord)", borderRadius: 8, color: "var(--texte)" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <figcaption>
        <div className="donut-titre">{titre}</div>
        <ul className="donut-legende">
          {visibles.map((p, i) => (
            <li key={p.nom}>
              <span className="pastille-point carre" style={{ background: p.nom === "Autres" ? "var(--texte-3)" : pal[i % pal.length] }} />
              <span className="donut-nom">{p.nom}</span>
              <span className="nombre">{n1.format((p.valeur / total) * 100)} %</span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}

