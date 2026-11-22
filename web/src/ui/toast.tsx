import { createContext, type ReactNode, useCallback, useContext, useRef, useState } from "react";
import { ApiError, UnreachableError } from "../api/client";
import { messages } from "../messages";

const VISIBLE_MS = 5_000;
const ToastContext = createContext<(text: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [text, setText] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const show = useCallback((next: string) => {
    clearTimeout(timer.current);
    setText(next);
    timer.current = setTimeout(() => setText(""), VISIBLE_MS);
  }, []);

  return (
    <ToastContext value={show}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {text && <div className="toast">{text}</div>}
      </div>
    </ToastContext>
  );
}

export const useToast = () => useContext(ToastContext);

export function errorText(error: unknown): string {
  return error instanceof ApiError || error instanceof UnreachableError
    ? error.message
    : messages.errors.unexpected;
}
