import { Suspense, lazy } from "react";
import { Route, HashRouter, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RouteLoadingFallback } from "./components/RouteLoadingFallback";

// Route-level code splitting: recharts (the largest dependency) only
// loads when the Overview or Variance tab is actually visited, instead of
// blocking the first paint for every tab.
const Overview = lazy(() => import("./pages/Overview").then((m) => ({ default: m.Overview })));
const Variance = lazy(() => import("./pages/Variance").then((m) => ({ default: m.Variance })));
const Close = lazy(() => import("./pages/Close").then((m) => ({ default: m.Close })));
const Outputs = lazy(() => import("./pages/Outputs").then((m) => ({ default: m.Outputs })));

// HashRouter, not BrowserRouter: this is a static, single-command deploy
// (any static host — Vercel, Netlify, GitHub Pages) with no server-side
// routing configured, so a direct link to /variance must work without a
// rewrite rule. Hash-based routes (/#/variance) always resolve to
// index.html first, everywhere, with zero host configuration.
function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route
            index
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <Overview />
              </Suspense>
            }
          />
          <Route
            path="variance"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <Variance />
              </Suspense>
            }
          />
          <Route
            path="close"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <Close />
              </Suspense>
            }
          />
          <Route
            path="outputs"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <Outputs />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </HashRouter>
  );
}

export default App;
