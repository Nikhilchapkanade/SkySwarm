import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'

// Global crash handler
window.addEventListener('error', (e) => {
    console.error('Global Crash:', e.error)
})

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled Promise Rejection:', e.reason)
})

// React error boundary
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error }
    }

    componentDidCatch(error, info) {
        console.error('React Render Crash:', error, info)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100vh',
                    background: '#071029',
                    color: '#ff6b6b',
                    fontFamily: 'Inter, sans-serif',
                    gap: 16,
                }}>
                    <h1 style={{ fontSize: 24 }}>⚠️ SkySwarm Crashed</h1>
                    <pre style={{
                        background: 'rgba(255,255,255,0.05)',
                        padding: 16,
                        borderRadius: 8,
                        maxWidth: '80%',
                        overflow: 'auto',
                        fontSize: 12,
                        color: 'rgba(255,255,255,0.6)',
                    }}>
                        {this.state.error?.toString()}
                    </pre>
                    <button
                        onClick={() => window.location.reload()}
                        style={{
                            padding: '10px 24px',
                            background: '#00ffd522',
                            border: '1px solid #00ffd5',
                            borderRadius: 8,
                            color: '#00ffd5',
                            cursor: 'pointer',
                            fontWeight: 600,
                        }}
                    >
                        Reload
                    </button>
                </div>
            )
        }
        return this.props.children
    }
}

const root = ReactDOM.createRoot(document.getElementById('root'))
root.render(
    <ErrorBoundary>
        <App />
    </ErrorBoundary>
)
