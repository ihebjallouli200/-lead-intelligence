import { useState, useEffect } from 'react';
import { getEmailStatus, getEmailTemplates, sendEmail, sendBulkEmail } from '../api';

/**
 * EmailModal — compose and send emails to one or multiple leads.
 *
 * Props:
 *   contacts: array of contact objects to email
 *   onClose: () => void
 *   onSent: (results) => void — called after successful send
 */
export default function EmailModal({ contacts, onClose, onSent }) {
  const [status, setStatus] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('default');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [useCustom, setUseCustom] = useState(false);
  const [sending, setSending] = useState(false);
  const [results, setResults] = useState(null);
  const [dryRun, setDryRun] = useState(false);
  const [skipContacted, setSkipContacted] = useState(true);

  const isBulk = contacts.length > 1;
  const validEmails = contacts.filter(c => c.email && c.email_valid);

  // Load email status and templates
  useEffect(() => {
    getEmailStatus().then(setStatus).catch(console.error);
    getEmailTemplates().then(t => {
      setTemplates(t);
      if (t.length > 0) {
        setSelectedTemplate(t[0].id);
        setSubject(t[0].subject);
        setBody(t[0].body);
      }
    }).catch(console.error);
  }, []);

  // Update preview when template changes
  useEffect(() => {
    if (!useCustom) {
      const tmpl = templates.find(t => t.id === selectedTemplate);
      if (tmpl) {
        setSubject(tmpl.subject);
        setBody(tmpl.body);
      }
    }
  }, [selectedTemplate, templates, useCustom]);

  // Preview: fill variables for first contact
  const previewContact = contacts[0] || {};
  const previewVars = {
    first_name: previewContact.first_name || 'there',
    last_name: previewContact.last_name || '',
    company: previewContact.company_name || 'your company',
    role: previewContact.role_canonical || 'professional',
    opportunity_type: previewContact.opportunity_type || '',
    size_bucket: previewContact.company_size_bucket || '',
    country: previewContact.company_country || '',
  };

  const renderPreview = (text) => {
    return text.replace(/\{\{(\w+)\}\}/g, (_, key) => previewVars[key] || `[${key}]`);
  };

  const handleSend = async () => {
    setSending(true);
    try {
      let result;
      if (isBulk) {
        result = await sendBulkEmail({
          contactIds: contacts.map(c => c.id),
          template: useCustom ? undefined : selectedTemplate,
          customSubject: useCustom ? subject : undefined,
          customBody: useCustom ? body : undefined,
          dryRun,
          skipContacted,
        });
      } else {
        result = await sendEmail({
          contactId: contacts[0].id,
          template: useCustom ? undefined : selectedTemplate,
          customSubject: useCustom ? subject : undefined,
          customBody: useCustom ? body : undefined,
          dryRun,
        });
      }
      setResults(result);
      if (onSent) onSent(result);
    } catch (e) {
      setResults({ success: false, error: e.message });
    }
    setSending(false);
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(6px)',
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-medium)',
        borderRadius: 'var(--radius-xl)', padding: 'var(--space-xl)',
        width: '100%', maxWidth: 700, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: 'var(--shadow-lg)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-lg)' }}>
          <div>
            <h2 style={{
              fontSize: '1.3rem', fontWeight: 700,
              background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>
              {isBulk ? `Send Email to ${contacts.length} Leads` : `Email ${contacts[0]?.first_name} ${contacts[0]?.last_name}`}
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 4 }}>
              {validEmails.length} valid email{validEmails.length !== 1 ? 's' : ''}
              {contacts.length - validEmails.length > 0 && ` (${contacts.length - validEmails.length} will be skipped)`}
            </p>
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.5rem', cursor: 'pointer',
          }}>x</button>
        </div>

        {/* Gmail status */}
        {status && !status.configured && (
          <div style={{
            padding: 'var(--space-md)', background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.2)', borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--space-lg)', fontSize: '0.85rem', color: 'var(--accent-rose)',
          }}>
            Gmail not configured. Edit <code>.env</code> with your GMAIL_ADDRESS and GMAIL_APP_PASSWORD, then restart the backend.
          </div>
        )}

        {/* Results */}
        {results ? (
          <div>
            <div style={{
              padding: 'var(--space-lg)', borderRadius: 'var(--radius-md)',
              background: results.sent > 0 || results.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
              border: `1px solid ${results.sent > 0 || results.success ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)'}`,
              marginBottom: 'var(--space-lg)',
            }}>
              {isBulk ? (
                <>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                    {results.dry_run ? 'Dry Run Complete' : 'Emails Sent'}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-sm)' }}>
                    <div><span style={{ color: 'var(--accent-emerald)', fontWeight: 700 }}>{results.sent}</span> sent</div>
                    <div><span style={{ color: 'var(--text-muted)', fontWeight: 700 }}>{results.skipped}</span> skipped</div>
                    <div><span style={{ color: 'var(--accent-rose)', fontWeight: 700 }}>{results.failed}</span> failed</div>
                  </div>
                </>
              ) : (
                <div style={{ fontSize: '1rem', fontWeight: 600 }}>
                  {results.success
                    ? (results.dry_run ? 'Dry run successful — no email sent' : `Email sent to ${results.email}`)
                    : `Error: ${results.error}`}
                </div>
              )}
            </div>
            <div style={{ textAlign: 'center' }}>
              <button className="filter-btn" onClick={onClose}>Close</button>
            </div>
          </div>
        ) : (
          <>
            {/* Template selector */}
            <div style={{ marginBottom: 'var(--space-lg)' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
                Email Template
              </label>
              <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
                <select className="filter-select" style={{ flex: 1 }} value={selectedTemplate}
                  onChange={e => { setSelectedTemplate(e.target.value); setUseCustom(false); }}>
                  {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={useCustom} onChange={e => setUseCustom(e.target.checked)} />
                  Custom
                </label>
              </div>
            </div>

            {/* Subject */}
            <div style={{ marginBottom: 'var(--space-md)' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
                Subject
              </label>
              <input className="filter-input" style={{ width: '100%' }}
                value={useCustom ? subject : renderPreview(subject)}
                onChange={e => { setSubject(e.target.value); setUseCustom(true); }}
                readOnly={!useCustom}
              />
            </div>

            {/* Body */}
            <div style={{ marginBottom: 'var(--space-lg)' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 'var(--space-sm)' }}>
                Body {!useCustom && '(preview — variables filled for first contact)'}
              </label>
              <textarea
                style={{
                  width: '100%', minHeight: 180, padding: 'var(--space-md)',
                  background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)', color: 'var(--text-primary)',
                  fontFamily: 'var(--font-sans)', fontSize: '0.85rem', lineHeight: 1.6, resize: 'vertical',
                }}
                value={useCustom ? body : renderPreview(body)}
                onChange={e => { setBody(e.target.value); setUseCustom(true); }}
                readOnly={!useCustom}
              />
            </div>

            {/* Options */}
            <div style={{ display: 'flex', gap: 'var(--space-lg)', marginBottom: 'var(--space-lg)', fontSize: '0.85rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
                Dry run (test without sending)
              </label>
              {isBulk && (
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={skipContacted} onChange={e => setSkipContacted(e.target.checked)} />
                  Skip already contacted
                </label>
              )}
            </div>

            {/* Send button */}
            <div style={{ display: 'flex', gap: 'var(--space-md)', justifyContent: 'flex-end' }}>
              <button className="filter-btn secondary" onClick={onClose}>Cancel</button>
              <button className="filter-btn" onClick={handleSend} disabled={sending || (status && !status.configured)}>
                {sending ? 'Sending...' : dryRun ? 'Test (Dry Run)' : isBulk ? `Send to ${validEmails.length} Leads` : 'Send Email'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
