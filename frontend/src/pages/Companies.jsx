import { useState, useEffect, useCallback } from 'react';
import { getCompanies, getFilters } from '../api';

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([]);
  const [filters, setFilters] = useState(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const limit = 50;

  // Filter state
  const [industry, setIndustry] = useState('');
  const [country, setCountry] = useState('');
  const [sizeBucket, setSizeBucket] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');

  useEffect(() => {
    getFilters().then(setFilters).catch(console.error);
  }, []);

  const fetchData = useCallback(() => {
    setLoading(true);
    const params = {
      limit,
      offset: page * limit,
      industry: industry || undefined,
      country: country || undefined,
      size_bucket: sizeBucket || undefined,
      search: search || undefined,
    };
    getCompanies(params)
      .then(data => { setCompanies(data.data); setTotal(data.total); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [page, industry, country, sizeBucket, search]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(0);
    setSearch(searchInput);
  };

  const clearFilters = () => {
    setIndustry(''); setCountry(''); setSizeBucket('');
    setSearch(''); setSearchInput(''); setPage(0);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      {/* Filter Bar */}
      <div className="filter-bar">
        <form onSubmit={handleSearch} style={{ display: 'contents' }}>
          <input
            className="filter-input"
            placeholder="Search company name, keywords, technologies..."
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
          />
          <button type="submit" className="filter-btn">Search</button>
        </form>

        <select className="filter-select" value={industry} onChange={e => { setIndustry(e.target.value); setPage(0); }}>
          <option value="">All Industries</option>
          {filters?.industries?.slice(0, 30).map(i => <option key={i} value={i}>{i}</option>)}
        </select>

        <select className="filter-select" value={country} onChange={e => { setCountry(e.target.value); setPage(0); }}>
          <option value="">All Countries</option>
          {filters?.countries?.slice(0, 30).map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <select className="filter-select" value={sizeBucket} onChange={e => { setSizeBucket(e.target.value); setPage(0); }}>
          <option value="">All Sizes</option>
          {filters?.size_buckets?.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <button className="filter-btn secondary" onClick={clearFilters}>Clear</button>
      </div>

      {/* Results Count */}
      <div style={{ marginBottom: 'var(--space-md)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        {total.toLocaleString()} companies found
      </div>

      {/* Data Table */}
      <div className="data-table-wrapper">
        {loading ? (
          <div className="loading-spinner"><div className="spinner" /></div>
        ) : companies.length === 0 ? (
          <div className="empty-state">No companies match your filters</div>
        ) : (
          <>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Industry</th>
                    <th>Country</th>
                    <th>City</th>
                    <th>Employees</th>
                    <th>Size</th>
                    <th>Website</th>

                  </tr>
                </thead>
                <tbody>
                  {companies.map(c => (
                    <tr key={c.id}>
                      <td style={{ fontWeight: 600 }}>{c.name}</td>
                      <td>
                        <span style={{ fontSize: '0.8rem' }}>{c.industry_raw || '-'}</span>
                        {c.industry_category && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', marginTop: 2 }}>
                            {c.industry_category}
                          </div>
                        )}
                      </td>
                      <td>{c.country || '-'}</td>
                      <td>{c.city || '-'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                        {c.employees_count?.toLocaleString() || '-'}
                      </td>
                      <td>
                        {c.size_bucket && (
                          <span className="badge badge-role">{c.size_bucket}</span>
                        )}
                      </td>
                      <td>
                        {c.domain ? (
                          <a href={c.domain.startsWith('http') ? c.domain : `https://${c.domain}`}
                             target="_blank" rel="noopener noreferrer"
                             style={{ fontSize: '0.8rem' }}>
                            {c.domain.replace(/^https?:\/\//, '').slice(0, 30)}
                          </a>
                        ) : '-'}
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
    </div>
  );
}
