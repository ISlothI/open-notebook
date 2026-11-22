import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, type Credentials } from "../api/client";
import { Logo } from "../brand/Logo";
import { messages } from "../messages";
import { errorText } from "../ui/toast";

const text = messages.auth;

export function AuthScreen() {
  const [registering, setRegistering] = useState(false);
  const queries = useQueryClient();
  const submission = useMutation({
    mutationFn: (credentials: Credentials) =>
      registering ? api.register(credentials) : api.signIn(credentials),
    onSuccess: (user) => queries.setQueryData(["me"], user),
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    submission.mutate({
      email: String(form.get("email")),
      password: String(form.get("password")),
    });
  };

  return (
    <main className="auth">
      <section className="auth-brand" aria-hidden="true">
        <Logo size={120} />
        <p className="auth-tagline">{messages.tagline}</p>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <div className="wordmark">
            <Logo />
            <span>{messages.appName}</span>
          </div>
          <h1>{registering ? text.registerTitle : text.signInTitle}</h1>
          <p className="muted">{registering ? text.registerLead : text.signInLead}</p>
          <form onSubmit={submit} className="stack">
            <label className="field">
              {text.email}
              <input name="email" type="email" autoComplete="username" required />
            </label>
            <label className="field">
              {text.password}
              <input
                name="password"
                type="password"
                autoComplete={registering ? "new-password" : "current-password"}
                minLength={registering ? 10 : undefined}
                required
              />
              {registering && <span className="hint">{text.passwordHint}</span>}
            </label>
            {submission.isError && (
              <p className="form-error" role="alert">
                {errorText(submission.error)}
              </p>
            )}
            <button type="submit" className="button primary" disabled={submission.isPending}>
              {registering ? text.register : text.signIn}
            </button>
          </form>
          <button
            type="button"
            className="link-button"
            onClick={() => {
              submission.reset();
              setRegistering(!registering);
            }}
          >
            {registering ? text.toSignIn : text.toRegister}
          </button>
        </div>
      </section>
    </main>
  );
}
