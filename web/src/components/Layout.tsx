import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/ideas", label: "Ideas" },
  { to: "/validity", label: "Validity" },
  { to: "/judgments", label: "Judgments" },
  { to: "/disagreement", label: "Similarity vs novelty" },
  { to: "/annotate", label: "Annotate" },
  { to: "/experiments", label: "Experiments" },
  { to: "/method", label: "Method" },
];

type Theme = "system" | "light" | "dark";

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("explorer-theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("explorer-theme", theme);
    } catch {
      /* storage unavailable: the preference lasts for this page view */
    }
  }, [theme]);
  const next: Record<Theme, Theme> = {
    system: "light",
    light: "dark",
    dark: "system",
  };
  return (
    <button
      className="btn ghost"
      type="button"
      onClick={() => setTheme(next[theme])}
      aria-label={`Theme: ${theme}. Switch to ${next[theme]}`}
    >
      Theme: {theme}
    </button>
  );
}

export function Logo() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <circle cx="3.5" cy="4" r="2" />
      <circle cx="12.5" cy="4.5" r="2" />
      <circle cx="8" cy="12" r="2.2" />
      <path d="M5.3 5l1.6 5M10.8 5.8L9 10.2M5.5 4.1h5" />
    </svg>
  );
}

export function Layout() {
  const location = useLocation();
  useEffect(() => {
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [location.pathname]);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-row">
            <NavLink
              to="/ideas"
              className="brand"
              aria-label="Explorer, LLM idea novelty"
            >
              <span className="brand-mark">
                <Logo />
              </span>
              <span>
                <span className="brand-name">Explorer</span>
                <br />
                <span className="brand-sub">
                  LLM idea novelty
                </span>
              </span>
            </NavLink>
            <span className="deployment">
              Are AI-generated ideas new, or recombinations?
            </span>
            <ThemeToggle />
          </div>
          <nav className="tabs" aria-label="Sections">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" className="main" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  );
}
