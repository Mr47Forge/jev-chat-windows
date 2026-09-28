import { Component } from 'react'

export class AppErrorBoundary extends Component {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error, info) {
    console.error('Relationship Atlas could not render.', error, info)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="app-error" id="main-content">
        <div>
          <span>Relationship Atlas</span>
          <h1>This page could not finish loading.</h1>
          <p>Your saved pairing remains on this device. Reload the app to try again.</p>
          <button className="primary-button" type="button" onClick={() => window.location.reload()}>Reload app</button>
        </div>
      </main>
    )
  }
}
