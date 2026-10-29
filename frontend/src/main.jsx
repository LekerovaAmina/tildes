import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { ContentProvider } from './store/content.jsx'
import { ProgressProvider } from './store/progress.jsx'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ContentProvider>
        <ProgressProvider>
          <App />
        </ProgressProvider>
      </ContentProvider>
    </BrowserRouter>
  </React.StrictMode>
)
