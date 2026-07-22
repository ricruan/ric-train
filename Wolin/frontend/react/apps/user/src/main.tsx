import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@interview/shared/styles/tokens.css';
import '@interview/shared/styles/base.css';
import './styles/app.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
