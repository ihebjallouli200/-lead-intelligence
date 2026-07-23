import { useState, useEffect } from 'react';
import { matchCVLeads, getFilters } from '../api';
import EmailModal from '../components/EmailModal';

function StageBadge({ stage }) {
  const cls = (stage || '').toLowerCase().replace(/\s+/g, '-');
  return <span className={`badge badge-stage ${cls}`}>{stage || 'New'}</span>;
}

function MatchScoreBar({ score }) {
  const level = score >= 75 ? 'high' : score >= 50 ? 'medium' : 'low';
  return (
    <div className="priority-bar">
      <div className="priority-bar-track">
        <div className={`priority-bar-fill ${level}`} style={{ width: `${score}%` }} />
      </div>
      <span className="priority-score" style={{ color: score >= 75 ? 'var(--accent-emerald)' : 'var(--accent-indigo-light)' }}>
        {score}%
      </span>
    </div>
  );
}

export default function CVMatcher() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [filters, setFilters] = useState(null);

  // Optional filters
  const [country, setCountry] = useState('');
  const [sizeBucket, setSizeBucket] = useState('');

  // Bulk selection & Email Modal state
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [emailModalContacts, setEmailModalContacts] = useState(null);

  useEffect(() => {
    getFilters().then(setFilters).catch(console.error);
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUploadAndMatch = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setSelectedIds(new Set());

    try {
      const data = await matchCVLeads(file, {
        country: country || undefined,
        size_bucket: sizeBucket || undefined,
        limit: 100,
      });
      setResults(data);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div>
      {/* Upload Zone Card */}
      <div className="card" style={{ marginBottom: 'var(--space-xl)', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '3px',
          background: 'var(--gradient-primary)', borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0'
        }} />

        <div style={{ textAlign: 'center', marginBottom: 'var(--space-lg)', paddingTop: 'var(--space-sm)' }}>
          <h2 style={{
            fontSize: '1.6rem', fontWeight: 800, letterSpacing: '-0.03em',
            background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>
            Match CV with Opportunities
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: 'var(--space-xs)' }}>
            Upload your resume (PDF or TXT) to instantly extract your skills and rank matching leads from 21,990 contacts.
          </p>
        </div>

        {/* Drop Target */}
        <div
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          style={{
            border: '2px dashed var(--border-medium)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-xl)',
            textAlign: 'center',
            background: 'rgba(255,255,255,0.015)',
            cursor: 'pointer',
            transition: 'all 0.2s smooth',
            marginBottom: 'var(--space-lg)',
          }}
          onClick={() => document.getElementById('cv-file-input').click()}
        >
          <input
            id="cv-file-input"
            type="file"
            accept=".pdf,.txt,.md"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <div style={{ fontSize: '2.5rem', marginBottom: 'var(--space-sm)' }}>📄</div>
          {file ? (
            <div>
              <div style={{ fontWeight: 600, color: 'var(--accent-indigo-light)', fontSize: '1.05rem' }}>
                {file.name}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                {(file.size / 1024).toFixed(1)} KB — Click or drag to replace file
              </div>
            </div>
          ) : (
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '1rem' }}>
                Click to upload or drag & drop your CV file here
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
                Supports PDF, TXT, MD
              </div>
            </div>
          )}
        </div>

        {/* Optional Filter Controls */}
        <div style={{ display: 'flex', gap: 'var(--space-md)', justifyContent: 'center', flexWrap: 'wrap', marginBottom: 'var(--space-lg)' }}>
          <select className="filter-select" value={country} onChange={e => setCountry(e.target.value)}>
            <option value="">All Countries</option>
            {filters?.countries?.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select className="filter-select" value={sizeBucket} onChange={e => setSizeBucket(e.target.value)}>
            <option value="">All Company Sizes</option>
            {filters?.size_buckets?.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button
            className="filter-btn"
            onClick={handleUploadAndMatch}
            disabled={!file || loading}
            style={{
              padding: 'var(--space-sm) var(--space-2xl)',
              fontSize: '0.95rem',
              opacity: file && !loading ? 1 : 0.4,
            }}
          >
            {loading ? 'Analyzing CV & Matching Leads...' : 'Analyze & Match Leads'}
          </button>
        </div>

        {error && (
          <div style={{
            padding: 'var(--space-md)', background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.2)', borderRadius: 'var(--radius-md)',
            color: 'var(--accent-rose)', fontSize: '0.85rem', textAlign: 'center'
          }}>
            {error}
          </div>
        )}
      </div>

      {/* Loading Spinner */}
      {loading && (
        <div className="loading-spinner"><div className="spinner" /></div>
      )}

      {/* Results View */}
      {!loading && results && (
        <div>
          {/* Extracted CV Skills Summary */}
          {results.cv_profile && (
            <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
              <div className="card-header" style={{ marginBottom: 'var(--space-md)' }}>
                <span className="card-title">Extracted Skill Profile</span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {results.cv_profile.total_skills_count} skills detected in {results.cv_profile.filename}
                </span>
              </div>

              {/* Skills Tags */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)', marginBottom: 'var(--space-md)' }}>
                {results.cv_profile.extracted_skills?.map(skill => (
                  <span className="badge badge-role" key={skill} style={{ fontSize: '0.78rem', padding: '4px 10px' }}>
                    {skill}
                  </span>
                ))}
                {results.cv_profile.extracted_skills?.length === 0 && (
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No specific tech skills detected in taxonomy. Try uploading a more detailed resume.
                  </span>
                )}
              </div>

              {/* Matched Domains */}
              {results.cv_profile.matched_opportunities?.length > 0 && (
                <div style={{ marginTop: 'var(--space-sm)' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                    Top Matching Opportunity Domains
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)' }}>
                    {results.cv_profile.matched_opportunities.map(opp => (
                      <span className="badge badge-opportunity" key={opp} style={{ fontSize: '0.75rem' }}>
                        {opp}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Results Summary & Actions */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 'var(--space-md)', padding: '0 var(--space-sm)'
          }}>
            <div>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {results.total.toLocaleString()} Matching Leads Found
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 'var(--space-sm)' }}>
                (ranked by skill & domain relevance)
              </span>
            </div>
            <div>
              {selectedIds.size > 0 ? (
                <button className="filter-btn" style={{ padding: '6px 16px', fontSize: '0.8rem' }}
                  onClick={() => setEmailModalContacts(results.data.filter(c => selectedIds.has(c.id)))}>
                  Email {selectedIds.size} Selected
                </button>
              ) : (
                <button className="filter-btn" style={{ padding: '6px 16px', fontSize: '0.8rem' }}
                  onClick={() => setEmailModalContacts(results.data)}>
                  Email All Matched ({results.data.length})
                </button>
              )}
            </div>
          </div>

          {/* Matches Table */}
          <div className="data-table-wrapper">
            {results.data.length === 0 ? (
              <div className="empty-state">No contacts matched your CV skills with the current filters.</div>
            ) : (
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
                      <th>Match Score</th>
                      <th>Decision Maker</th>
                      <th>Company</th>
                      <th>Country</th>
                      <th>Matching Tech Stack</th>
                      <th>Opportunity</th>
                      <th>Stage</th>
                      <th>Email</th>
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
                        <td><MatchScoreBar score={c.match_score} /></td>
                        <td>
                          <div style={{ fontWeight: 600 }}>{c.first_name} {c.last_name}</div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{c.title_raw}</div>
                        </td>
                        <td>
                          <div style={{ fontWeight: 500 }}>{c.company_name}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{c.company_size_bucket}</div>
                        </td>
                        <td>{c.company_country || '-'}</td>
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxWidth: 220 }}>
                            {c.matched_skills?.map(skill => (
                              <span key={skill} className="badge badge-stage" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                                {skill}
                              </span>
                            ))}
                            {c.matched_skills?.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Industry match</span>}
                          </div>
                        </td>
                        <td>
                          {c.opportunity_type && (
                            <span className="badge badge-opportunity">{c.opportunity_type}</span>
                          )}
                        </td>
                        <td><StageBadge stage={c.stage} /></td>
                        <td>
                          {c.email ? (
                            <a href={`mailto:${c.email}`} style={{ fontSize: '0.78rem' }}>
                              {c.email.length > 22 ? c.email.slice(0, 22) + '...' : c.email}
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
            )}
          </div>
        </div>
      )}

      {/* Email Modal */}
      {emailModalContacts && (
        <EmailModal
          contacts={emailModalContacts}
          onClose={() => setEmailModalContacts(null)}
          onSent={() => setSelectedIds(new Set())}
        />
      )}
    </div>
  );
}
