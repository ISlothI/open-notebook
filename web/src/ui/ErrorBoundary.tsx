import { Component, type ReactNode } from "react";
import { messages } from "../messages";

/** Keeps a programming error in one view from leaving the user with a blank window. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  override render() {
    if (!this.state.failed) {
      return this.props.children;
    }
    return (
      <div className="centered" role="alert">
        <p>{messages.errors.boundary}</p>
        <button type="button" className="button" onClick={() => location.reload()}>
          {messages.retry}
        </button>
      </div>
    );
  }
}
