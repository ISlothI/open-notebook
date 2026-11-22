import { useEffect, useState } from "react";
import { fetchHealth } from "./health";

type ServiceState = "checking" | "ready" | "unavailable";

const STATE_TEXT: Record<ServiceState, string> = {
  checking: "Opening your notebook…",
  ready: "Everything is ready.",
  unavailable: "The service is not available right now. Please try again in a moment.",
};

export function App() {
  const [state, setState] = useState<ServiceState>("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((health) => setState(health.status === "ok" ? "ready" : "unavailable"))
      .catch(() => {
        if (!controller.signal.aborted) {
          setState("unavailable");
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <h1>Open Notebook</h1>
      <p role="status">{STATE_TEXT[state]}</p>
    </main>
  );
}
