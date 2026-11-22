import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "@fontsource-variable/newsreader/wght.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/editor.css";
import { App } from "./App";
import { ApiError } from "./api/client";
import { ErrorBoundary } from "./ui/ErrorBoundary";
import { ToastProvider } from "./ui/toast";

const MAX_RETRIES = 2;

const queries = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failures, error) => !(error instanceof ApiError) && failures < MAX_RETRIES,
    },
  },
});

const container = document.getElementById("root");
if (!container) {
  throw new Error("The root element is missing from index.html");
}

createRoot(container).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queries}>
        <ToastProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
