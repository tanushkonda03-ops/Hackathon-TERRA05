import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[TERRA05 ERROR BOUNDARY]', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="w-screen h-screen flex flex-col items-center justify-center bg-[#F5F7FA] text-[#1A202C] p-6 font-sans">
          <div className="max-w-md w-full bg-white border border-[#DDE3EA] rounded-xl shadow-lg p-6 space-y-4">
            <div className="flex items-center space-x-2.5 text-rose-600 border-b border-[#DDE3EA] pb-3">
              <AlertTriangle className="w-5 h-5" />
              <h2 className="font-bold text-base tracking-wide">
                TERRA05 APPLICATION MODULE RECOVERY
              </h2>
            </div>
            
            <p className="text-xs text-[#64748B] leading-relaxed">
              A module encountered a rendering exception. The system has prevented a blank screen.
            </p>

            {this.state.error && (
              <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded text-[11px] font-mono text-rose-700 max-h-36 overflow-auto">
                {this.state.error.toString()}
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={this.handleReload}
                className="px-4 py-2 bg-[#0284C7] hover:bg-[#0369A1] text-white rounded-lg text-xs font-bold uppercase tracking-wider flex items-center space-x-1.5 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reload Dashboard</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
