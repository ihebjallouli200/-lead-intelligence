import { useState } from 'react';
import './index.css';
import Dashboard from './pages/Dashboard';
import LeadFinder from './pages/LeadFinder';
import CVMatcher from './pages/CVMatcher';
import ContactsPage from './pages/Contacts';
import CompaniesPage from './pages/Companies';

const PAGES = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'matcher', label: 'Match CV' },
  { id: 'finder', label: 'Find Leads' },
  { id: 'contacts', label: 'Contacts' },
  { id: 'companies', label: 'Companies' },
];

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>Lead Intelligence</h1>
        <nav className="header-nav">
          {PAGES.map(p => (
            <button
              key={p.id}
              className={`nav-btn ${activePage === p.id ? 'active' : ''}`}
              onClick={() => setActivePage(p.id)}
            >
              {p.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="app-main">
        {activePage === 'dashboard' && <Dashboard />}
        {activePage === 'matcher' && <CVMatcher />}
        {activePage === 'finder' && <LeadFinder />}
        {activePage === 'contacts' && <ContactsPage />}
        {activePage === 'companies' && <CompaniesPage />}
      </main>
    </div>
  );
}
