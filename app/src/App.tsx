import { useEffect, useState } from "react";
import { contientTest, dernierEtat, joursEtude } from "./data";
import { definirSombre, useTheme, type Theme } from "./ui";
import Accueil from "./pages/Accueil";
import PagePortefeuille from "./pages/Portefeuille";
import Transactions from "./pages/Transactions";
import Journal from "./pages/Journal";
import Explorer from "./pages/Explorer";
import Comparateur from "./pages/Comparateur";
import IndicateursPage from "./pages/Indicateurs";
import RapportPage from "./pages/Rapport";
import Sante from "./pages/Sante";

const NAV: [string, string][] = [
  ["", "Accueil"],
  ["transactions", "Transactions"],
  ["journal", "Journal"],
  ["explorer", "Explorer les mises"],
  ["comparer", "Comparateur"],
  ["indicateurs", "Indicateurs"],
  ["rapport", "Rapport"],
  ["sante", "Santé"],
];

function useRoute() {
  const lire = () => location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const [route, setRoute] = useState(lire);
  useEffect(() => {
    const f = () => {
      setRoute(lire());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return route;
}

const THEMES: Record<Theme, [Theme, string, string]> = {
  auto: ["clair", "◐", "Thème automatique (cliquer pour passer en clair)"],
  clair: ["sombre", "☀", "Thème clair (cliquer pour passer en sombre)"],
  sombre: ["auto", "☾", "Thème sombre (cliquer pour revenir en automatique)"],
};

export default function App() {
  const route = useRoute();
  const { theme, setTheme, sombre } = useTheme();
  definirSombre(sombre);
  const [page, arg] = route;
  const jour = dernierEtat?.jour ?? (dernierEtat ? null : 0);

  let contenu;
  switch (page) {
    case "p": contenu = <PagePortefeuille id={arg} />; break;
    case "transactions": contenu = <Transactions />; break;
    case "journal": contenu = <Journal date={arg} />; break;
    case "explorer": contenu = <Explorer />; break;
    case "comparer": contenu = <Comparateur />; break;
    case "indicateurs": contenu = <IndicateursPage />; break;
    case "rapport": contenu = <RapportPage />; break;
    case "sante": contenu = <Sante />; break;
    default: contenu = <Accueil />;
  }
  const actif = page === "p" ? "" : page ?? "";

  return (
    <div className="appli" key={String(sombre)}>
      <header className="entete">
        <div className="entete-ligne">
          <a href="#/" className="marque">
            <span aria-hidden="true">🧪</span> Labo Bourse
          </a>
          <span className="jour-pilule" title="Jour de l'étude">
            {jour ? `Jour ${jour} sur ${joursEtude.length}` : `Étude du ${joursEtude[0]?.slice(8)}.${joursEtude[0]?.slice(5, 7)} au ${joursEtude.at(-1)?.slice(8)}.${joursEtude.at(-1)?.slice(5, 7)}`}
          </span>
          <button type="button" className="theme-bouton" onClick={() => setTheme(THEMES[theme][0])} aria-label={THEMES[theme][2]} title={THEMES[theme][2]}>
            {THEMES[theme][1]}
          </button>
        </div>
        <nav className="nav" aria-label="Navigation principale">
          {NAV.map(([h, t]) => (
            <a key={h} href={`#/${h}`} aria-current={actif === h ? "page" : undefined}>{t}</a>
          ))}
        </nav>
      </header>
      {contientTest && (
        <div className="bandeau-test" role="status">
          🧪 Données de <strong>test</strong> affichées : elles seront effacées avant le début de l'étude.
        </div>
      )}
      <main className="contenu">{contenu}</main>
      <footer className="pied">
        Argent 100 % fictif · étude simulée · cours Yahoo Finance · décisions par Claude, exécution et calculs par script.
        <br />Rien ici n'est un conseil d'investissement.
      </footer>
    </div>
  );
}
