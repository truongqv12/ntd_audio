import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  fallback?: (reset: () => void, error: Error) => ReactNode;
};

type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("ui_error_boundary_caught", error, info.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (this.props.fallback) return this.props.fallback(this.reset, error);
    return (
      <div className="error-boundary-fallback" role="alert">
        <h2>Something went wrong.</h2>
        <p className="muted-copy">{error.message}</p>
        <button type="button" onClick={this.reset}>
          Try again
        </button>
      </div>
    );
  }
}
