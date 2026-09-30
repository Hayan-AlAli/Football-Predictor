import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted type (latin subset, only the weights in use): no third-party
// font request, and no fallback face standing in when a CDN is slow.
import '@fontsource/big-shoulders-display/latin-700';
import '@fontsource/big-shoulders-display/latin-800';
import '@fontsource/big-shoulders-display/latin-900';
import '@fontsource/ibm-plex-mono/latin-400';
import '@fontsource/ibm-plex-mono/latin-500';
import '@fontsource/ibm-plex-mono/latin-600';
import '@fontsource/instrument-sans/latin-400';
import '@fontsource/instrument-sans/latin-400-italic';
import '@fontsource/instrument-sans/latin-500';
import '@fontsource/instrument-sans/latin-600';
import '@fontsource/instrument-sans/latin-700';
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
