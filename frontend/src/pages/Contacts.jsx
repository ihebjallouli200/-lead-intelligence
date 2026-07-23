import { useState, useEffect, useCallback } from 'react';
import { getContacts, getFilters } from '../api';
import EmailModal from '../components/EmailModal';

function StageBadge({ stage }) {
  const cls = (stage || '').toLowerCase().replace(/\s+/g, '-');
  return <span className={`badge badge-stage ${cls}`}>{stage || 'New'}</span>;
}

function PriorityBar({ score }) {
  if (score == null) return <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>--</span>;
  const level = score >= 70 ? 'high' : score >= 50 ? 'medium' : 'low';
  return (
    <div className="priority-bar">
      <div className="priority-bar-track">
        <div className={`priority-bar-fill ${level}`} style={{ width: `${score}%` }} />
      </div>
      <span className="priority-score">{score}</span>
    </div>
  );
}

export default function ContactsPage() {
  const [contacts, setContacts] = useState([]);
  const [filters, setFilters] = useState(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const limit = 50;
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [emailModalContacts, setEmailModalContacts] = useState(null);

  // Filter state
  const [role, setRole] = useState('');
  const [stage, setStage] = useState('');
  const [opportunityType, setOpportunityType] = useState('');
  const [isFounder, setIsFounder] = useState('');
  const [country, setCountry] = useState('');
  const [sizeBucket, setSizeBucket] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [priorityMin, setPriorityMin] = useState('');

  useEffect(() => {
    getFilters().then(setFilters).catch(console.error);
  }, []);

  const fetchData = useCallback(() => {
    setLoading(true);
    const params = {
      limit,
      offset: page * limit,
      role: role || undefined,
      stage: stage || undefined,
      opportunity_type: opportunityType || undefined,
      is_founder: isFounder === '' ? undefined : isFounder,
      country: country || undefined,
      size_bucket: sizeBucket || undefined,
      search: search || undefined,
      priority_min: priorityMin || undefined,
    };
    getContacts(params)
      .then(data => { setContacts(data.data); setTotal(data.total); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, role, stage, opportunityType, isFounder, country, sizeBucket, search, priorityMin]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(0);
    setSearch(searchInput);
  };

  const clearFilters = () => {
    setRole(''); setStage(''); setOpportunityType(''); setIsFounder('');
    setCountry(''); setSizeBucket(''); setSearch(''); setSearchInput('');
    setPriorityMin(''); setPage(0);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      {/* Filter Bar */}
      <div className="filter-bar">
        <form onSubmit={handleSearch} style={{ display: 'contents' }}>
          <input
            className="filter-input"
            placeholder="Search name, email, title, company..."
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
          />
          <button type="submit" className="filter-btn">Search</button>
        </form>

        <select className="filter-select" value={role} onChange={e => { setRole(e.target.value); setPage(0); }}>
          <option value="">All Roles</option>
          {filters?.roles?.map(r => <option key={r} value={r}>{r}</option>)}
        </select>

        <select className="filter-select" value={opportunityType} onChange={e => { setOpportunityType(e.target.value); setPage(0); }}>
          <option value="">All Opportunities</option>
          {filters?.opportunity_types?.map(o => <option key={o} value={o}>{o}</option>)}
        </select>

        <select className="filter-select" value={stage} onChange={e => { setStage(e.target.value); setPage(0); }}>
          <option value="">All Stages</option>
          {filters?.stages?.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select className="filter-select" value={isFounder} onChange={e => { setIsFounder(e.target.value); setPage(0); }}>
          <option value="">Founder?</option>
          <option value="true">Founders Only</option>
          <option value="false">Non-Founders</option>
        </select>

        <select className="filter-select" value={sizeBucket} onChange={e => { setSizeBucket(e.target.value); setPage(0); }}>
          <option value="">All Sizes</option>
          {filters?.size_buckets?.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select className="filter-select" value={country} onChange={e => { setCountry(e.target.value); setPage(0); }}>
          <option value="">All Countries</option>
          {filters?.countries?.slice(0, 30).map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <select className="filter-select" value={priorityMin} onChange={e => { setPriorityMin(e.target.value); setPage(0); }}>
          <option value="">Any Priority</option>
          <option value="70">High (70+)</option>
          <option value="50">Medium+ (50+)</option>
          <option value="30">All Scored</option>
        </select>

        <button className="filter-btn secondary" onClick={clearFilters}>Clear</button>

        {selectedIds.size > 0 && (
          <button className="filter-btn" style={{ padding: '6px 16px', fontSize: '0.8rem' }}
            onClick={() => setEmailModalContacts(contacts.filter(c => selectedIds.has(c.id)))}>
            Email {selectedIds.size} Selected
          </button>
        )}
      </div>

      {/* Results Count */}
      <div style={{ marginBottom: 'var(--space-md)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        {total.toLocaleString()} contacts found
      </div>

      {/* Data Table */}
      <div className="data-table-wrapper">
        {loading ? (
          <div className="loading-spinner"><div className="spinner" /></div>
        ) : contacts.length === 0 ? (
          <div className="empty-state">No contacts match your filters</div>
        ) : (
          <>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 36 }}>
                      <input type="checkbox"
                        checked={contacts.length > 0 && selectedIds.size === contacts.length}
                        onChange={e => {
                          if (e.target.checked) setSelectedIds(new Set(contacts.map(c => c.id)));
                          else setSelectedIds(new Set());
                        }}
                      />
                    </th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Company</th>
                    <th>Country</th>
                    <th>Opportunity</th>
                    <th>Priority</th>
                    <th>Stage</th>
                    <th>Email</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {contacts.map(c => (
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
                        <div style={{ fontWeight: 500 }}>{c.first_name} {c.last_name}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{c.title_raw?.slice(0, 40)}</div>
                      </td>
                      <td><span className="badge badge-role">{c.role_canonical}</span></td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{c.company_name}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{c.company_size_bucket}</div>
                      </td>
                      <td>{c.company_country || '-'}</td>
                      <td>{c.opportunity_type ? <span className="badge badge-opportunity">{c.opportunity_type}</span> : '-'}</td>
                      <td><PriorityBar score={c.priority_score} /></td>
                      <td><StageBadge stage={c.stage} /></td>
                      <td>
                        <div style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {c.email ? (
                            <a href={`mailto:${c.email}`} style={{ fontSize: '0.8rem' }}>{c.email}</a>
                          ) : '-'}
                        </div>
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

            {/* Pagination */}
            <div className="pagination">
              <span className="pagination-info">
                Page {page + 1} of {totalPages} ({total.toLocaleString()} total)
              </span>
              <div className="pagination-controls">
                <button className="page-btn" disabled={page === 0} onClick={() => setPage(0)}>First</button>
                <button className="page-btn" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Prev</button>
                <button className="page-btn" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next</button>
                <button className="page-btn" disabled={page >= totalPages - 1} onClick={() => setPage(totalPages - 1)}>Last</button>
              </div>
            </div>
          </>
        )}
      </div>

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
