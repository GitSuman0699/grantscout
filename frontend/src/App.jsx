import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import ScrollToTop from './components/ScrollToTop';
import HomePage from './pages/HomePage';
import PipelinePage from './pages/PipelinePage';
import RubricPage from './pages/RubricPage';
import ProposalDraftPage from './pages/ProposalDraftPage';
import DraftsPage from './pages/DraftsPage';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import OptimizationPage from './pages/OptimizationPage';
import AgentThoughtStream from './components/AgentThoughtStream';
import { GrantProvider } from './context/GrantContext';

export default function App() {
  return (
    <GrantProvider>
      <BrowserRouter>
        <ScrollToTop />
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
          <Header />
          
          <main style={{ flex: 1, width: '100%' }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/pipeline" element={<PipelinePage />} />
              
              {/* Distinct Dedicated Routes */}
              <Route path="/rubrics/:id" element={<RubricPage />} />
              <Route path="/grants/:id" element={<RubricPage />} />
              <Route path="/drafts/:id" element={<ProposalDraftPage />} />
              
              <Route path="/drafts" element={<DraftsPage />} />
              <Route path="/knowledge" element={<KnowledgeBasePage />} />
              <Route path="/optimization" element={<OptimizationPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Footer */}
          <footer style={{
            borderTop: '2px solid var(--border-dark)',
            backgroundColor: 'var(--ink)',
            color: 'var(--canvas-bg)',
            padding: '2rem'
          }}>
            <div style={{
              maxWidth: '1440px',
              margin: '0 auto',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '1rem',
              fontSize: '0.82rem'
            }}>
              <div>
                <div className="font-heading" style={{ fontSize: '1.4rem' }}>GRANTSCOUT</div>
                <div style={{ color: '#A1A1AA' }}>Built with Strands Agents SDK & Amazon Bedrock for the AWS Agents for Humans Hackathon</div>
              </div>

              <div style={{ fontFamily: 'var(--font-mono)', color: '#A1A1AA' }}>
                © 2026 GrantScout • MIT License
              </div>
            </div>
          </footer>

          {/* Real-Time Multi-Agent Thought & Telemetry Visualizer */}
          <AgentThoughtStream />
        </div>
      </BrowserRouter>
    </GrantProvider>
  );
}
