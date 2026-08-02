import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { AffectProvider } from "./affect";
import { queryClient } from "./lib/queryClient";
import "./styles/tokens.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AffectProvider>
        <App />
      </AffectProvider>
    </QueryClientProvider>
  </StrictMode>,
);
