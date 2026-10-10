import "@fontsource/geist-sans/400.css";
import "@fontsource/geist-sans/500.css";
import "@fontsource/geist-sans/600.css";
import "@fontsource/geist-mono/400.css";
import "@fontsource/geist-mono/500.css";
import "./styles.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Annotate } from "./pages/Annotate";
import { Disagreement } from "./pages/Disagreement";
import { Experiments } from "./pages/Experiments";
import { Ideas } from "./pages/Ideas";
import { Item } from "./pages/Item";
import { Judgments } from "./pages/Judgments";
import { Method } from "./pages/Method";
import { NotFound } from "./pages/NotFound";
import { Validity } from "./pages/Validity";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root element");

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/ideas" replace />} />
          <Route path="ideas" element={<Ideas />} />
          <Route path="items/:id" element={<Item />} />
          <Route path="validity" element={<Validity />} />
          <Route path="judgments" element={<Judgments />} />
          <Route path="disagreement" element={<Disagreement />} />
          <Route path="annotate" element={<Annotate />} />
          <Route path="experiments" element={<Experiments />} />
          <Route path="experiments/:exp" element={<Experiments />} />
          <Route path="method" element={<Method />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
