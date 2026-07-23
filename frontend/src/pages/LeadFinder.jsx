import { useState, useEffect } from 'react';
import { getFilters, getContacts } from '../api';
import EmailModal from '../components/EmailModal';

function StageBadge({ stage }) {
  const cls = (stage || '').toLowerCase().replace(/\s+/g, '-');
  return <span className={`badge badge-stage ${cls}`}>{stage || 'New'}</span>;
}

export default function LeadFinder() {
  const [filters, setFilters] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [searched, setSearched] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [emailModalContacts, setEmailModalContacts] = useState(null);

  // Wizard selections
  const [role, setRole] = useState('');
  const [opportunityType, setOpportunityType] = useState('');
  const [country, setCountry] = useState('');
  const [sizeBucket, setSizeBucket] = useState('');
  const [isFounder, setIsFounder] = useState('');
  const [priorityMin, setPriorityMin] = useState('');

  useEffect(() => {
    getFilters().then(setFilters).catch(console.error);
  }, []);

  const handleFind = () => {
    setLoading(true);
    setSearched(true);
    const params = {
      limit: 100,
      offset: 0,
      role: role || undefined,
      opportunity_type: opportunityType || undefined,
      country: country || undefined,
      size_bucket: sizeBucket || undefined,
      is_founder: isFounder === '' ? undefined : isFounder,
      priority_min: priorityMin || undefined,
    };
    getContacts(params)
      .then(data => setResults(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const handleReset = () => {
    setRole(''); setOpportunityType(''); setCountry('');
    setSizeBucket(''); setIsFounder(''); setPriorityMin('');
    setResults(null); setSearched(false);
  };

  const hasSelection = role || opportunityType || country || sizeBucket || isFounder || priorityMin;

  return (
    <div>
      {/* Wizard Card */}
      <div className="card" style={{ marginBottom: 'var(--space-xl)', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
          background: 'var(--gradient-primary)', borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0'
        }} />

        <div style={{ textAlign: 'center', marginBottom: 'var(--space-xl)', paddingTop: 'var(--space-md)' }}>
          <h2 style={{
            fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.03em',
            background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>
            Find Your Leads
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: 'var(--space-sm)' }}>
            Select the criteria below to discover matching contacts from 21,990 leads
          </p>
        </div>

        {/* Filter Grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-lg)',
          marginBottom: 'var(--space-xl)'
        }}>
          {/* Role */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
              Role
            </label>
            <select className="filter-select" style={{ width: '100%' }} value={role} onChange={e => setRole(e.target.value)}>
              <option value="">Any Role</option>
              {filters?.roles?.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          {/* Opportunity Type */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
              Opportunity Type
            </label>
            <select className="filter-select" style={{ width: '100%' }} value={opportunityType} onChange={e => setOpportunityType(e.target.value)}>
              <option value="">Any Opportunity</option>
              {filters?.opportunity_types?.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>

          {/* Country */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
              Country
            </label>
            <select className="filter-select" style={{ width: '100%' }} value={country} onChange={e => setCountry(e.target.value)}>
              <option value="">Any Country</option>
              {filters?.countries?.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Company Size */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
              Company Size
            </label>
            <select className="filter-select" style={{ width: '100%' }} value={sizeBucket} onChange={e => setSizeBucket(e.target.value)}>
              <option value="">Any Size</option>
              {filters?.size_buckets?.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {/* Founder */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
              Founder Status
            </label>
            <select className="filter-select" style={{ width: '100%' }} value={isFounder} onChange={e => setIsFounder(e.target.value)}>
              <option value="">Anyone</option>
              <option value="true">Founders Only</option>
              <option value="false">Non-Founders</option>
            </select>
          </div>

          {/* Priority */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
              Minimum Priority
            </label>
            <select className="filter-select" style={{ width: '100%' }} value={priorityMin} onChange={e => setPriorityMin(e.target.value)}>
              <option value="">Any Score</option>
              <option value="70">High (70+)</option>
              <option value="60">Medium+ (60+)</option>
              <option value="50">All Scored (50+)</option>
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-md)' }}>
          <button
            className="filter-btn"
            onClick={handleFind}
            disabled={!hasSelection}
            style={{
              padding: 'var(--space-md) var(--space-2xl)',
              fontSize: '1rem',
              opacity: hasSelection ? 1 : 0.4,
              cursor: hasSelection ? 'pointer' : 'not-allowed',
            }}
          >
            Find Leads
          </button>
          {searched && (
            <button className="filter-btn secondary" onClick={handleReset}
              style={{ padding: 'var(--space-md) var(--space-xl)' }}>
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      {loading && (
        <div className="loading-spinner"><div className="spinner" /></div>
      )}

      {searched && !loading && results && results.total === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-md)' }}>
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}>
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </div>
          <h3 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 'var(--space-sm)' }}>
            No Leads Available
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', maxWidth: 400, margin: '0 auto' }}>
            No contacts match your selected criteria. Try broadening your filters — remove a country or change the role.
          </p>
        </div>
      )}

      {searched && !loading && results && results.total > 0 && (
        <>
          {/* Results Summary */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 'var(--space-md)', padding: '0 var(--space-sm)'
          }}>
            <div>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {results.total.toLocaleString()} leads found
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 'var(--space-sm)' }}>
                (showing top {Math.min(results.data.length, results.total)})
              </span>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap', alignItems: 'center' }}>
              {role && <span className="badge badge-role">{role}</span>}
              {opportunityType && <span className="badge badge-opportunity">{opportunityType}</span>}
              {country && <span className="badge badge-stage">{country}</span>}
              {sizeBucket && <span className="badge badge-founder">{sizeBucket}</span>}
              {selectedIds.size > 0 ? (
                <button className="filter-btn" style={{ marginLeft: 'var(--space-sm)', padding: '6px 16px', fontSize: '0.8rem' }}
                  onClick={() => setEmailModalContacts(results.data.filter(c => selectedIds.has(c.id)))}>
                  Email {selectedIds.size} Selected
                </button>
              ) : (
                <button className="filter-btn" style={{ marginLeft: 'var(--space-sm)', padding: '6px 16px', fontSize: '0.8rem' }}
                  onClick={() => setEmailModalContacts(results.data)}>
                  Email All ({results.data.length})
                </button>
              )}
            </div>
          </div>

          {/* Results Table */}
          <div className="data-table-wrapper">
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 36 }}>
                      <input type="checkbox"
                        checked={results.data.length > 0 && selectedIds.size === results.data.length}
                        onChange={e => {
                          if (e.target.checked) setSelectedIds(new Set(results.data.map(c => c.id)));
                          else setSelectedIds(new Set());
                        }}
                      />
                    </th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Company</th>
                    <th>Country</th>
                    <th>Size</th>
                    <th>Opportunity</th>
                    <th>Priority</th>
                    <th>Stage</th>
                    <th>Email</th>
                    <th>LinkedIn</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {results.data.map(c => (
                    <tr key={c.id} style={{ background: selectedIds.has(c.id) ? 'rgba(99, 102, 241, 0.06)' : undefined }}>
                      <td>
                        <input type="checkbox" checked={selectedIds.has(c.id)}
                          onChange={e => {
                            const next = new Set(selectedIds);
                            if (e.target.checked) next.add(c.id); else next.delete(c.id);
                            setSelectedIds(next);
                          }}
                        />
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{c.first_name} {c.last_name}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {c.title_raw}
                        </div>
                      </td>
                      <td><span className="badge badge-role">{c.role_canonical}</span></td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{c.company_name || '-'}</div>
                      </td>
                      <td>{c.company_country || '-'}</td>
                      <td>
                        {c.company_size_bucket && (
                          <span className="badge badge-founder" style={{ fontSize: '0.65rem' }}>{c.company_size_bucket}</span>
                        )}
                      </td>
                      <td>
                        {c.opportunity_type && (
                          <span className="badge badge-opportunity">{c.opportunity_type}</span>
                        )}
                      </td>
                      <td>
                        {c.priority_score != null ? (
                          <div className="priority-bar">
                            <div className="priority-bar-track">
                              <div
                                className={`priority-bar-fill ${c.priority_score >= 70 ? 'high' : c.priority_score >= 50 ? 'medium' : 'low'}`}
                                style={{ width: `${c.priority_score}%` }}
                              />
                            </div>
                            <span className="priority-score">{c.priority_score}</span>
                          </div>
                        ) : '--'}
                      </td>
                      <td><StageBadge stage={c.stage} /></td>
                      <td>
                        {c.email ? (
                          <a href={`mailto:${c.email}`} style={{ fontSize: '0.78rem' }}>
                            {c.email.length > 25 ? c.email.slice(0, 25) + '...' : c.email}
                          </a>
                        ) : '-'}
                      </td>
                      <td>
                        {c.linkedin_url ? (
                          <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                            style={{ fontSize: '0.78rem', color: 'var(--accent-blue)' }}>
                            Profile
                          </a>
                        ) : '-'}
                      </td>
                      <td>
                        <button className="filter-btn" style={{ padding: '3px 10px', fontSize: '0.72rem' }}
                          onClick={() => setEmailModalContacts([c])}>
                          Email
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Email Modal */}
      {emailModalContacts && (
        <EmailModal
          contacts={emailModalContacts}
          onClose={() => setEmailModalContacts(null)}
          onSent={() => { fetchData(); setSelectedIds(new Set()); }}
        />
      )}
    </div>
  );
}
