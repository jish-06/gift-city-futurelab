import { FormEvent, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, BadgeCheck, Building2, Check, CheckCircle2,
  ChevronRight, CircleDollarSign, ClipboardList, Clock3, Database, FileCheck2,
  FileText, GitCompareArrows, Globe2, KeyRound, Landmark, LayoutDashboard,
  Link2, LogOut, Play, Plus, RefreshCw, ShieldAlert, ShieldCheck, Wallet,
  Workflow, X, Zap,
} from 'lucide-react';
import { api, clearToken, getToken, post, saveToken } from './api';

type AuthUser = { email: string; role: 'maker' | 'checker'; name: string };
type LoginResponse = { access_token: string; user: AuthUser; expires_in: number };
type Rec = {
  id: string; type: string; severity: string; status: string; title: string; description: string;
  currency: string; exposure_amount: string; hedge_amount: string; mismatch_amount: string;
  maturity_difference_days: number | null; assumptions: string[]; evidence: any[]; snapshot_hash: string;
};
type Dashboard = {
  company: any; exposures: any[]; open_hedges: number; open_invoices: number;
  pending_recommendations: number; recent_recommendations: Rec[]; events: any[];
};

const nav = [
  ['Overview', LayoutDashboard], ['Transactions', FileText], ['Hedge alignment', GitCompareArrows],
  ['Recommendations', ShieldAlert], ['Approvals', FileCheck2], ['Pipeline', Workflow],
  ['Shadow balances', Database], ['Netting', Building2], ['Liquidity', Wallet],
  ['Working capital', CircleDollarSign], ['Scenario lab', Activity],
  ['Accounting drafts', ClipboardList], ['Connections', Link2], ['Audit trail', Database],
] as const;
const fmt = (v: string | number, currency = '') => `${currency ? currency + ' ' : ''}${Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export default function App() {
  const [authReady, setAuthReady] = useState(false);
  const [auth, setAuth] = useState<AuthUser | null>(null);

  useEffect(() => {
    const onUnauthorized = () => { setAuth(null); setAuthReady(true); };
    window.addEventListener('fxnexus:unauthorized', onUnauthorized);
    if (!getToken()) {
      setAuthReady(true);
    } else {
      api<AuthUser>('/api/auth/me').then(setAuth).catch(() => { clearToken(); setAuth(null); }).finally(() => setAuthReady(true));
    }
    return () => window.removeEventListener('fxnexus:unauthorized', onUnauthorized);
  }, []);

  async function handleLogin(email: string, password: string) {
    const result = await api<LoginResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
    saveToken(result.access_token);
    setAuth(result.user);
  }

  async function handleLogout() {
    try { await post('/api/auth/logout'); } catch { /* local token is still cleared */ }
    clearToken();
    setAuth(null);
  }

  if (!authReady) return <div className="auth-loading"><div className="brandmark"><Globe2 size={24} /></div><b>Opening secure demo workspace…</b></div>;
  if (!auth) return <LoginPage onLogin={handleLogin} />;
  return <Workspace auth={auth} onLogout={handleLogout} />;
}

function LoginPage({ onLogin }: { onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('maker@fxnexus.local');
  const [password, setPassword] = useState('Maker-Demo-2026!');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try { await onLogin(email.trim(), password); } catch (err: any) { setError(err.message || 'Sign-in failed'); }
    finally { setBusy(false); }
  }
  return <div className="login-shell">
    <div className="login-art">
      <div className="login-brand"><div className="brandmark"><Globe2 size={23} /></div><div><b>FXNexus</b><small>TREASURY INTELLIGENCE</small></div></div>
      <div className="login-copy"><span className="eyebrow light">EVENT-DRIVEN FX OPERATIONS</span><h1>Know your exposure.<br /><em>Act with evidence.</em></h1><p>A connected decision-support layer for cross-border cash flows, hedge alignment and treasury workflows.</p>
        <div className="login-feature"><span><Activity size={17} /></span><div><b>From business event to treasury action</b><small>Invoice · payment · cash · hedge · approval</small></div></div>
        <div className="login-feature"><span><ShieldCheck size={17} /></span><div><b>Human-controlled by design</b><small>Evidence, maker-checker review and simulation only</small></div></div>
      </div>
      <div className="login-art-foot">FXNEXUS · LOCAL DEMONSTRATION ENVIRONMENT</div>
    </div>
    <div className="login-panel-wrap"><form className="login-panel" onSubmit={submit}>
      <div className="login-panel-heading"><span className="eyebrow">WELCOME BACK</span><h2>Sign in to FXNexus</h2><p>Use one of the local demo roles to open the treasury workspace.</p></div>
      {error && <div className="login-error"><AlertTriangle size={16} />{error}</div>}
      <label>Email address<input type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required /></label>
      <label>Password<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
      <button className="primary login-submit" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} /></button>
      <div className="demo-access"><div className="demo-access-head"><KeyRound size={15} /><b>Demo access</b><span>LOCAL ONLY</span></div>
        <button type="button" onClick={() => { setEmail('maker@fxnexus.local'); setPassword('Maker-Demo-2026!'); }}><b>Maker</b><small>maker@fxnexus.local</small></button>
        <button type="button" onClick={() => { setEmail('checker@fxnexus.local'); setPassword('Checker-Demo-2026!'); }}><b>Checker</b><small>checker@fxnexus.local</small></button>
      </div>
      <p className="login-note">Demo credentials are configured in <code>backend/.env</code>. Change them before sharing this project. Demo sessions expire automatically.</p>
    </form></div>
  </div>;
}

function Workspace({ auth, onLogout }: { auth: AuthUser; onLogout: () => void }) {
  const [page, setPage] = useState('Overview');
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [hedges, setHedges] = useState<any[]>([]);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [netting, setNetting] = useState<any[]>([]);
  const [shadow, setShadow] = useState<any>({ cash_snapshots: [], settlement_ledger: [], warning: '' });
  const [integrations, setIntegrations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Rec | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [d, i, h, r, a, au, p, n, sh, conn] = await Promise.all([
        api<Dashboard>('/api/dashboard'), api<any[]>('/api/invoices'), api<any[]>('/api/hedges'),
        api<Rec[]>('/api/recommendations'), api<any[]>('/api/approvals/pending'), api<any[]>('/api/audit'),
        api<any[]>('/api/pipeline'), post('/api/netting/calculate'), api<any>('/api/shadow-balances'),
        api<any>('/api/integrations/status'),
      ]);
      setDash(d); setInvoices(i); setHedges(h); setRecs(r); setApprovals(a); setAudit(au);
      setPipeline(p); setNetting(n); setShadow(sh); setIntegrations(conn); setError('');
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { refresh(); }, []);
  useEffect(() => { if (notice) { const t = setTimeout(() => setNotice(''), 5000); return () => clearTimeout(t); } }, [notice]);

  const exposureData = useMemo(() => dash?.exposures.map(x => ({
    currency: x.currency, direction: x.direction, amount: Number(x.amount),
  })) || [], [dash]);

  async function action(fn: () => Promise<any>, msg: string) {
    try { const result = await fn(); setNotice(msg); await refresh(); return result; }
    catch (err: any) { setError(err.message); throw err; }
  }

  const canMake = auth.role === 'maker';
  const canCheck = auth.role === 'checker';
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brandmark"><Globe2 size={22} /></div><div><b>FXNexus</b><small>TREASURY INTELLIGENCE</small></div></div>
      <div className="workspace"><span className="dot" /> DEMO WORKSPACE <ChevronRight size={14} /></div>
      <nav>{nav.map(([label, Icon]) => <button key={label} className={`navitem ${page === label ? 'active' : ''}`} onClick={() => { setPage(label); setSelected(null); }}><Icon size={17} /><span>{label}</span>{label === 'Recommendations' && dash?.pending_recommendations ? <em>{dash.pending_recommendations}</em> : null}</button>)}</nav>
      <div className="sidebar-bottom"><div className="secure"><ShieldAlert size={16} /><div><b>Decision support mode</b><small>No live trades enabled</small></div></div>
        <div className="user"><div className="avatar">{auth.role === 'maker' ? 'MK' : 'CK'}</div><div><b>{auth.name}</b><small>{auth.role} · Demo role</small></div><span className="online" /></div>
      </div>
    </aside>
    <main className="main">
      <header className="topbar"><div><div className="eyebrow">TREASURY WORKSPACE / {page.toUpperCase()}</div><h1>{page}</h1></div>
        <div className="top-actions"><span className="live"><i /> SIMULATION ENVIRONMENT</span><button className="iconbtn" onClick={refresh} title="Refresh data"><RefreshCw size={17} /></button><div className="signed-in"><div className="avatar">{auth.role === 'maker' ? 'MK' : 'CK'}</div><div><b>{auth.name}</b><small>{auth.role} role</small></div></div><button className="logout-btn" onClick={onLogout} title="Sign out"><LogOut size={16} /><span>Sign out</span></button></div>
      </header>
      {notice && <div className="toast success"><CheckCircle2 size={16} />{notice}<button onClick={() => setNotice('')}><X size={15} /></button></div>}
      {error && <div className="toast error"><AlertTriangle size={16} />{error}<button onClick={() => setError('')}><X size={15} /></button></div>}
      {loading && !dash ? <div className="loading">Loading FXNexus workspace…</div> : <div className="page-content">
        {page === 'Overview' && dash && <Overview dash={dash} exposureData={exposureData} recs={recs} setPage={setPage} setSelected={setSelected} />}
        {page === 'Transactions' && <Transactions invoices={invoices} onPayment={(body: any) => action(() => post('/api/payments', body), 'Payment event processed; exposure and hedge alignment recalculated.')} onDueDate={(body: any) => action(() => post('/api/events', body), 'Expected cash-flow date changed; hedge maturity alignment recalculated.')} />}
        {page === 'Hedge alignment' && <HedgeAlignment hedges={hedges} invoices={invoices} recs={recs} onReconcile={() => action(() => post('/api/reconcile'), 'Hedge reconciliation completed.')} />}
        {page === 'Recommendations' && <Recommendations recs={recs} setSelected={setSelected} canCreate={canMake} onProposal={async (rec: Rec) => {
          const isRoll = rec.type === 'MATURITY_MISMATCH';
          const body = {
            action_type: isRoll ? 'PREPARE_ROLL_ADJUSTMENT_FOR_REVIEW' : 'PREPARE_HEDGE_ADJUSTMENT_FOR_REVIEW',
            description: isRoll ? `Prepare a roll/adjustment review for the maturity mismatch on ${rec.currency}.` : `Review potential mismatch of ${rec.mismatch_amount} ${rec.currency}`,
            proposed_amount: rec.mismatch_amount, currency: rec.currency,
            rationale: isRoll ? 'Payment/shipment timing may have moved. Compare revised expected cash-flow date with contract maturity; obtain a bank quote and authorised approval before any rollover.' : 'Underlying exposure changed; verify eligibility, maturity and contract terms before any bank instruction.',
          };
          const proposal = await post(`/api/recommendations/${rec.id}/proposals`, body);
          await post(`/api/proposals/${proposal.proposal_id}/request-approval`);
          setNotice('Proposal submitted to checker approval queue. No trade or rollover was executed.'); await refresh();
        }} />}
        {page === 'Approvals' && <Approvals approvals={approvals} canApprove={canCheck} onDecision={(a: any, decision: string, confirmations: any) => action(() => post(`/api/approvals/${a.id}/decision`, { decision, comment: decision === 'APPROVE' ? 'Verified source records and hedge status.' : 'Reviewed by demo checker.', expected_snapshot_hash: a.snapshot_hash, confirmations }), decision === 'APPROVE' ? 'Approved internally — no external trade executed.' : 'Decision recorded.')} onSimulate={(a: any) => action(() => post(`/api/proposals/${a.proposal_id}/simulate`), 'Demo action simulated. No bank or broker order placed.')} />}
        {page === 'Pipeline' && <Pipeline rows={pipeline} onAdd={(body: any) => action(() => post('/api/pipeline', body), 'Pipeline scenario added.')} onUpdate={(body: any) => action(() => post('/api/events', body), 'CRM deal update event processed; probability-weighted exposure refreshed.')} />}
        {page === 'Shadow balances' && <ShadowBalances data={shadow} onResolve={(body: any) => action(() => post('/api/events', body), 'Settlement treatment updated from the review event.')} />}
        {page === 'Netting' && <Netting rows={netting} />}
        {page === 'Liquidity' && <Liquidity cashSnapshots={shadow.cash_snapshots} />}
        {page === 'Working capital' && <WorkingCapital />}
        {page === 'Scenario lab' && <ScenarioLab />}
        {page === 'Accounting drafts' && <Accounting hedges={hedges} onCreate={async (id: string, framework: string) => { const result = await api<any>(`/api/accounting/draft?hedge_id=${encodeURIComponent(id)}&framework=${encodeURIComponent(framework)}`, { method: 'POST' }); const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${result.download_url}`, { headers: { Authorization: `Bearer ${getToken()}` } }); if (!response.ok) throw new Error('Memo was created, but PDF download failed: ' + await response.text()); const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `FXNexus_${framework.replaceAll(' ', '_')}_Hedge_Accounting_Draft.pdf`; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url); setNotice('Accounting draft generated and downloaded as PDF.'); await refresh(); }} />}
        {page === 'Connections' && <Connections status={integrations} />}
        {page === 'Audit trail' && <Audit rows={audit} />}
      </div>}
      {selected && <RecommendationModal rec={selected} onClose={() => setSelected(null)} onProposal={() => { setPage('Recommendations'); setSelected(null); }} />}
      <footer>FXNexus MVP · Illustrative synthetic data · All financial actions require qualified human review.</footer>
    </main>
  </div>;
}

function PageIntro({ tag, title, desc, action }: { tag: string; title: string; desc: string; action?: any }) {
  return <div className="pageintro"><div><span className="eyebrow">{tag}</span><h2>{title}</h2><p>{desc}</p></div>{action}</div>;
}
function Stat({ label, value, sub, icon: Icon, tone = 'blue' }: any) {
  return <div className="stat card"><div className={`stat-icon ${tone}`}><Icon size={18} /></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-sub">{sub}</div></div>;
}
function Overview({ dash, exposureData, recs, setPage, setSelected }: any) {
  const open = recs.filter((r: Rec) => ['PENDING_REVIEW', 'UNDER_REVIEW', 'ACTION_PROPOSED'].includes(r.status));
  return <>
    <div className="welcome"><div><div className="eyebrow light">TREASURY SNAPSHOT</div><h2>{dash.company?.name || 'Treasury workspace'} <span>✦</span></h2><p>Monitor expected receipts, foreign-currency cash and hedge alignment in one workflow.</p></div><div className="welcome-chip"><Activity size={16} /> Event-driven monitoring active</div></div>
    <div className="stats-grid"><Stat label="Open invoices" value={dash.open_invoices} sub="Receivables & payables" icon={FileText} /><Stat label="Open hedge contracts" value={dash.open_hedges} sub="Imported / simulated positions" icon={GitCompareArrows} tone="violet" /><Stat label="Pending actions" value={dash.pending_recommendations} sub="Require treasury review" icon={ShieldAlert} tone="amber" /><Stat label="Currencies tracked" value={new Set(dash.exposures.map((x: any) => x.currency)).size} sub="Across open transactions" icon={Globe2} tone="green" /></div>
    <div className="grid-two">
      <section className="card panel"><div className="panel-head"><div><h3>Exposure by currency & direction</h3><p>Outstanding transaction records · gross invoice and foreign-currency cash positions</p></div><button className="textbtn" onClick={() => setPage('Transactions')}>View transactions <ArrowRight size={14} /></button></div>
        <div className="chart-wrap">
          {exposureData.length ? <div className="exposure-bars" role="img" aria-label="Gross exposures grouped by currency and direction. Bar lengths are relative only within each currency.">
            {exposureData.map((row: any) => {
              const max = Math.max(1, ...exposureData.filter((x: any) => x.currency === row.currency).map((x: any) => x.amount));
              return <div className="exposure-bar-row" key={`${row.currency}-${row.direction}`}>
                <div className="exposure-bar-label"><span><b>{row.currency}</b> · {row.direction === 'RECEIVABLE' ? 'Receivable' : row.direction === 'PAYABLE' ? 'Payable' : 'Foreign-currency cash'}</span><strong>{fmt(row.amount, row.currency)}</strong></div>
                <div className="bar-track"><span className={row.direction === 'PAYABLE' ? 'payable' : row.direction === 'ASSET_CASH' ? 'cash' : ''} style={{ width: `${Math.max(2, row.amount / max * 100)}%` }} /></div>
              </div>;
            })}
            <div className="chart-footnote">Each currency has its own scale; bar lengths do not compare EUR with USD.</div>
          </div> : <div className="empty">No open foreign-currency exposures are currently recorded.</div>}
        </div>
        <div className="exposure-list">{dash.exposures.map((x: any) => <div className="exposure-row" key={x.currency + x.direction}><span className="currency-pill">{x.currency}</span><span>{x.direction === 'RECEIVABLE' ? 'Receivable' : x.direction === 'PAYABLE' ? 'Payable' : 'Foreign-currency cash'}</span><b>{fmt(x.amount, x.currency)}</b></div>)}</div>
      </section>
      <section className="card panel"><div className="panel-head"><div><h3>Needs attention</h3><p>Evidence-backed recommendations</p></div><span className="count-pill">{open.length} open</span></div>
        {open.length ? open.slice(0, 4).map((r: Rec) => <button className="alert-row" key={r.id} onClick={() => setSelected(r)}><span className={`alert-icon ${r.severity.toLowerCase()}`}><AlertTriangle size={17} /></span><span className="alert-content"><b>{r.title}</b><small>{r.description.slice(0, 85)}…</small><em>{r.type.replaceAll('_', ' ')}</em></span><ChevronRight size={16} /></button>) : <div className="empty">No open recommendations. Run reconciliation to check current positions.</div>}
        <button className="full-link" onClick={() => setPage('Recommendations')}>Open recommendation centre <ArrowRight size={15} /></button>
      </section>
    </div>
    <div className="card panel"><div className="panel-head"><div><h3>Recent events</h3><p>Latest changes recorded by FXNexus</p></div><button className="textbtn" onClick={() => setPage('Audit trail')}>Audit trail <ArrowRight size={14} /></button></div>
      <div className="event-feed">{dash.events.length ? dash.events.map((e: any) => <div className="feed-row" key={e.id}><span className="feed-dot" /><div><b>{e.type.replaceAll('_', ' ')}</b><small>{e.entity_type} · {e.entity_id}</small></div><time>{new Date(e.created_at).toLocaleString()}</time></div>) : <div className="empty">No events yet. Record a payment or date change to start the event lifecycle.</div>}</div>
    </div>
    <div className="feature-strip"><div><Zap size={19} /><div><b>Beyond a dashboard</b><small>Pre-invoice pipeline · roll watch · shadow cash · netting · liquidity · working capital · hedge-accounting drafts</small></div></div><button onClick={() => setPage('Pipeline')}>Explore modules <ArrowRight size={15} /></button></div>
  </>;
}

function Transactions({ invoices, onPayment, onDueDate }: any) {
  const [invoice, setInvoice] = useState(invoices[0]?.id || '');
  const [amount, setAmount] = useState('5000');
  const [treatment, setTreatment] = useState('CONVERTED');
  const [dest, setDest] = useState('INR');
  const [conversionRate, setConversionRate] = useState('');
  const [dateInvoice, setDateInvoice] = useState(invoices[0]?.id || '');
  const [newDueDate, setNewDueDate] = useState('');
  useEffect(() => { if (!invoice && invoices[0]) setInvoice(invoices[0].id); if (!dateInvoice && invoices[0]) setDateInvoice(invoices[0].id); }, [invoices, invoice, dateInvoice]);
  return <>
    <PageIntro tag="EVENT INGESTION" title="Transaction lifecycle" desc="Invoice and settlement events update exposure, payment treatment and hedge timing. The simulator records evidence; it does not move money." />
    <div className="card panel"><div className="panel-head"><div><h3>Record a payment event</h3><p>Demonstrate how a real business event changes exposure.</p></div><span className="demo-label">SIMULATOR</span></div>
      <div className="form-grid"><label>Invoice<select value={invoice} onChange={e => setInvoice(e.target.value)}>{invoices.filter((x: any) => x.status === 'OPEN' && x.direction === 'RECEIVABLE').map((x: any) => <option key={x.id} value={x.id}>{x.invoice_number} · {x.currency} {x.outstanding_amount}</option>)}</select></label><label>Payment amount<input value={amount} onChange={e => setAmount(e.target.value)} type="number" min="1" /></label><label>Payment treatment<select value={treatment} onChange={e => { setTreatment(e.target.value); setDest(e.target.value === 'CONVERTED' ? 'INR' : 'USD'); setConversionRate(''); }}><option value="CONVERTED">Converted into INR</option><option value="RETAINED">Retained in foreign currency</option><option value="UNKNOWN">Unknown / needs verification</option></select></label><label>Destination currency<input value={dest} onChange={e => setDest(e.target.value.toUpperCase())} /></label><label>Destination units per source unit (cross-currency only)<input value={conversionRate} onChange={e => setConversionRate(e.target.value)} type="number" min="0" step="any" placeholder="e.g. 0.92 EUR per USD" /></label></div>
      <button className="primary" disabled={!invoice || !amount || Number(amount) <= 0} onClick={() => onPayment({ invoice_id: invoice, amount, payment_date: new Date().toISOString().slice(0, 10), treatment, destination_currency: dest, ...(conversionRate && Number(conversionRate) > 0 ? { conversion_rate: conversionRate } : {}), source_record_id: `MANUAL-${Date.now()}` })}><Plus size={16} /> Record payment & process event</button>
      <p className="helper">INR-converted receipts leave foreign-currency exposure. Retained receipts remain cash assets in the source currency. A conversion into another foreign currency requires a destination-units-per-source-unit rate; unknown treatment remains unresolved.</p>
    </div>
    <div className="card panel"><div className="panel-head"><div><h3>Revised shipment / payment date</h3><p>Test the dynamic roll and maturity-mismatch workflow.</p></div><span className="demo-label">EVENT SIMULATOR</span></div>
      <div className="form-grid"><label>Invoice<select value={dateInvoice} onChange={e => setDateInvoice(e.target.value)}>{invoices.filter((x: any) => x.status === 'OPEN' && x.direction === 'RECEIVABLE').map((x: any) => <option key={x.id} value={x.id}>{x.invoice_number} · due {x.due_date}</option>)}</select></label><label>New expected payment date<input type="date" value={newDueDate} onChange={e => setNewDueDate(e.target.value)} /></label></div>
      <button className="secondary" disabled={!dateInvoice || !newDueDate} onClick={() => onDueDate({ event_type: 'DUE_DATE_CHANGED', entity_type: 'invoice', entity_id: dateInvoice, idempotency_key: `due-date:${dateInvoice}:${newDueDate}:${Date.now()}`, payload: { due_date: newDueDate } })}><Clock3 size={15} /> Record date change & run roll watch</button>
    </div>
    <div className="card panel"><div className="panel-head"><div><h3>Open and historical invoices</h3><p>Seeded exporter demo records</p></div><span className="count-pill">{invoices.length} records</span></div><div className="table-scroll"><table><thead><tr><th>Invoice</th><th>Customer</th><th>Direction</th><th>Currency</th><th>Outstanding</th><th>Due date</th><th>Status</th></tr></thead><tbody>{invoices.map((x: any) => <tr key={x.id}><td><b>{x.invoice_number}</b><small>{x.legal_entity}</small></td><td>{x.customer}</td><td>{x.direction}</td><td><span className="currency-pill">{x.currency}</span></td><td className="numeric">{fmt(x.outstanding_amount, x.currency)}</td><td>{x.due_date}</td><td><span className={`status ${x.status.toLowerCase()}`}>{x.status}</span></td></tr>)}</tbody></table></div></div>
  </>;
}

function HedgeAlignment({ hedges, invoices, recs, onReconcile }: any) {
  const rollItems = recs.filter((r: Rec) => r.type === 'MATURITY_MISMATCH' && ['PENDING_REVIEW', 'UNDER_REVIEW', 'ACTION_PROPOSED'].includes(r.status));
  return <>
    <PageIntro tag="RECONCILIATION ENGINE" title="Hedge alignment & roll watch" desc="Compare hedge notional, direction, legal entity and maturity against underlying cash flows. Date changes create reviewable roll/adjustment proposals." action={<button className="primary" onClick={onReconcile}><RefreshCw size={15} /> Run reconciliation</button>} />
    <div className="card panel"><div className="panel-head"><div><h3>Forward contracts</h3><p>Imported contract records · indicative records, not executable orders</p></div></div><div className="table-scroll"><table><thead><tr><th>Contract</th><th>Pair</th><th>Direction</th><th>Remaining notional</th><th>Rate</th><th>Maturity</th><th>Status</th></tr></thead><tbody>{hedges.map((h: any) => <tr key={h.id}><td><b>{h.contract_number}</b></td><td>{h.currency_pair}</td><td>{h.direction}</td><td className="numeric">{fmt(h.remaining_amount, h.currency_pair.split('/')[0])}</td><td>{h.contract_rate}</td><td>{h.maturity_date}</td><td><span className="status open">{h.status}</span></td></tr>)}</tbody></table></div></div>
    <div className="card panel"><div className="panel-head"><div><h3>Dynamic roll / adjustment watch</h3><p>Flagged when expected cash-flow dates move outside the illustrative maturity tolerance.</p></div><span className="count-pill">{rollItems.length} open timing alerts</span></div>
      {rollItems.length ? rollItems.map((r: Rec) => <div className="roll-watch-row" key={r.id}><div><b>{r.title}</b><p>{r.description}</p><small>{r.maturity_difference_days} day maturity difference · {r.evidence.length} evidence records</small></div><span className="severity medium">REVIEW</span></div>) : <div className="empty">No open maturity mismatch alerts. Record a revised expected payment date in Transactions to test the roll workflow.</div>}
    </div>
    <div className="card panel"><h3>Matching policy</h3><div className="policy-grid"><div><b>Currency & direction</b><p>USD receivables can match SELL_BASE USD/INR hedges; USD payables can match BUY_BASE contracts. EUR is not netted against USD.</p></div><div><b>Legal entity</b><p>Cross-entity matching is not assumed unless company policy and legal arrangements support it.</p></div><div><b>Maturity tolerance</b><p>Demo default: seven calendar days. Configure per company; this is not a universal market rule.</p></div><div><b>Incomplete data</b><p>Unknown cash treatment or missing contracts must be surfaced as a data issue, not silently netted.</p></div></div></div>
  </>;
}

function Recommendations({ recs, setSelected, onProposal, canCreate }: any) {
  return <><PageIntro tag="ACTION CENTRE" title="Recommendations" desc="Each finding links to source records, assumptions and a reviewable next step. A recommendation is not an instruction to trade." />
    <div className="recommendation-list">{recs.length ? recs.map((r: Rec) => <div className="card rec-card" key={r.id}><div className="rec-top"><span className={`severity ${r.severity.toLowerCase()}`}>{r.severity}</span><span className="rec-id">{r.id.slice(0, 8).toUpperCase()}</span><span className={`status ${r.status.toLowerCase()}`}>{r.status.replaceAll('_', ' ')}</span></div><h3>{r.title}</h3><p>{r.description}</p><div className="rec-metrics"><div><small>Underlying exposure</small><b>{fmt(r.exposure_amount, r.currency)}</b></div><div><small>Open hedge notional</small><b>{fmt(r.hedge_amount, r.currency)}</b></div><div><small>Potential difference</small><b className="warning-text">{fmt(r.mismatch_amount, r.currency)}</b></div></div><div className="rec-bottom"><span>{r.evidence.length} linked source records · {r.assumptions.length} assumptions{r.type === 'PAYMENT_TREATMENT_REVIEW' ? ' · resolve in Shadow balances' : ''}</span><div><button className="secondary" onClick={() => setSelected(r)}>Inspect evidence</button>{canCreate && r.type !== 'PAYMENT_TREATMENT_REVIEW' && ['PENDING_REVIEW', 'UNDER_REVIEW', 'ACTION_PROPOSED'].includes(r.status) && <button className="primary small" onClick={() => onProposal(r)}>{r.type === 'MATURITY_MISMATCH' ? 'Prepare roll review' : 'Prepare proposal'} <ArrowRight size={14} /></button>}</div></div></div>) : <div className="card empty">No recommendations yet. Record a payment or run reconciliation.</div>}</div>
  </>;
}

function RecommendationModal({ rec, onClose, onProposal }: any) {
  return <div className="overlay" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}><div className="modal-head"><div><span className={`severity ${rec.severity.toLowerCase()}`}>{rec.severity}</span><h2>{rec.title}</h2></div><button className="iconbtn" onClick={onClose}><X size={18} /></button></div><p>{rec.description}</p><div className="rec-metrics"><div><small>Exposure</small><b>{fmt(rec.exposure_amount, rec.currency)}</b></div><div><small>Hedge</small><b>{fmt(rec.hedge_amount, rec.currency)}</b></div><div><small>Difference</small><b className="warning-text">{fmt(rec.mismatch_amount, rec.currency)}</b></div></div><h4>Evidence records</h4>{rec.evidence.map((e: any) => <div className="evidence" key={e.id}><FileText size={15} /><span><b>{e.record}</b><small>{e.type} · {e.id}</small></span></div>)}<h4>Calculation assumptions</h4><ul>{rec.assumptions.map((x: string) => <li key={x}>{x}</li>)}</ul><div className="snapshot"><small>Calculation summary</small><div className="snapshot-grid"><span>Exposure considered</span><b>{fmt(rec.exposure_amount, rec.currency)}</b><span>Open hedge amount</span><b>{fmt(rec.hedge_amount, rec.currency)}</b><span>Unmatched / excess amount</span><b>{fmt(rec.mismatch_amount, rec.currency)}</b>{rec.maturity_difference_days !== null && <><span>Maturity difference</span><b>{rec.maturity_difference_days} days</b></>}</div><details className="snapshot-technical"><summary>Technical trace reference</summary><code>{rec.snapshot_hash}</code><p>This SHA-256 reference identifies the underlying data snapshot used when this recommendation was calculated. It is a trace ID, not a financial calculation.</p></details></div><div className="modal-actions"><button className="secondary" onClick={onClose}>Close</button><button className="primary" onClick={onProposal}>Open action centre</button></div></div></div>;
}

function Approvals({ approvals, onDecision, onSimulate, canApprove }: any) {
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const required = ['underlying_exposure_verified', 'payment_treatment_verified', 'hedge_status_verified', 'maturity_reviewed'];
  const labels: Record<string, string> = { underlying_exposure_verified: 'Underlying exposure verified', payment_treatment_verified: 'Payment treatment verified', hedge_status_verified: 'Hedge contract status verified', maturity_reviewed: 'Maturity and terms reviewed' };
  return <><PageIntro tag="MAKER-CHECKER CONTROL" title="Approval queue" desc="Maker prepares; checker independently verifies. Approval is internal only and does not execute, roll or rebook a derivative." />
    <div className="card panel"><div className="panel-head"><div><h3>Pending approvals</h3><p>Checker-controlled review queue</p></div><span className="count-pill">{approvals.length} pending</span></div>
      {!canApprove && <div className="info-banner"><ShieldCheck size={17} /> You are signed in as Maker. Sign out and enter with the Checker demo account to decide approvals.</div>}
      {approvals.length ? approvals.map((a: any) => <div className="approval-card" key={a.id}><div className="approval-title"><div><span className="eyebrow">{a.action_type}</span><h3>{a.title}</h3></div><span className="status pending">PENDING</span></div><p>{a.description}</p><div className="proposal-summary"><div><small>Proposed amount</small><b>{a.proposed_amount ? fmt(a.proposed_amount, a.currency) : 'Review only'}</b></div><div><small>Requested by</small><b>{a.requested_by}</b></div></div><h4>Required verification</h4><div className="checks">{required.map(k => <label key={k}><input type="checkbox" checked={!!checks[a.id + k]} disabled={!canApprove} onChange={e => setChecks(s => ({ ...s, [a.id + k]: e.target.checked }))} />{labels[k]}</label>)}</div><div className="approval-actions"><button className="danger-outline" disabled={!canApprove} onClick={() => onDecision(a, 'REJECT', {})}><X size={14} /> Reject</button><button className="secondary" disabled={!canApprove} onClick={() => onDecision(a, 'REQUEST_CHANGES', {})}>Request changes</button><button className="primary" disabled={!canApprove || !required.every(k => checks[a.id + k])} onClick={() => onDecision(a, 'APPROVE', Object.fromEntries(required.map(k => [k, true])))}><Check size={15} /> Approve internally</button></div><small className="helper">Approval is not execution. A separate simulation can be run after approval.</small>{canApprove && <button className="textbtn" onClick={() => onSimulate(a)}><Play size={14} /> Simulate approved action</button>}</div>) : <div className="empty">No pending approvals. A Maker can create a proposal from an open recommendation.</div>}
    </div></>;
}

function Pipeline({ rows, onAdd, onUpdate }: any) {
  const [name, setName] = useState('New US customer order');
  const [amount, setAmount] = useState('75000');
  const [prob, setProb] = useState('0.75');
  const [currency, setCurrency] = useState('USD');
  const [customer, setCustomer] = useState('Demo customer');
  const [stage, setStage] = useState('NEGOTIATION');
  const [selectedDeal, setSelectedDeal] = useState('');
  const [updatedAmount, setUpdatedAmount] = useState('75000');
  const [updatedProbability, setUpdatedProbability] = useState('0.85');
  const [updatedPaymentDate, setUpdatedPaymentDate] = useState('');
  const [updatedStage, setUpdatedStage] = useState('NEGOTIATION');
  useEffect(() => {
    if (!selectedDeal && rows[0]) setSelectedDeal(rows[0].id);
    const selected = rows.find((r: any) => r.id === selectedDeal) || (!selectedDeal ? rows[0] : null);
    if (selected) { setUpdatedAmount(String(selected.amount)); setUpdatedProbability(String(selected.probability)); setUpdatedPaymentDate(selected.expected_payment_date); setUpdatedStage(selected.stage); }
  }, [rows, selectedDeal]);
  const currentDeal = rows.find((r: any) => r.id === selectedDeal);
  return <><PageIntro tag="PRE-INVOICE RISK" title="Pipeline-triggered exposure" desc="Probability-weighted scenarios make potential FX exposure visible before an invoice exists. These are forecasts, not booked receivables." />
    <div className="card panel"><div className="panel-head"><div><h3>Add a pipeline opportunity</h3><p>Use CRM stage confidence as an explicit scenario input.</p></div><span className="demo-label">PRE-INVOICE</span></div><div className="form-grid"><label>Deal name<input value={name} onChange={e => setName(e.target.value)} /></label><label>Customer / counterparty<input value={customer} onChange={e => setCustomer(e.target.value)} /></label><label>Gross deal amount<input type="number" value={amount} onChange={e => setAmount(e.target.value)} /></label><label>Currency<select value={currency} onChange={e => setCurrency(e.target.value)}><option>USD</option><option>EUR</option><option>AED</option><option>GBP</option><option>SGD</option><option>JPY</option></select></label><label>Win probability<input type="number" min="0" max="1" step="0.05" value={prob} onChange={e => setProb(e.target.value)} /></label><label>CRM stage<select value={stage} onChange={e => setStage(e.target.value)}><option>LEAD</option><option>QUALIFICATION</option><option>PROPOSAL</option><option>NEGOTIATION</option><option>CONTRACT_SIGNED</option><option>WON</option><option>LOST</option></select></label></div><button className="primary" disabled={!name || !customer || Number(amount) <= 0 || Number(prob) < 0 || Number(prob) > 1} onClick={() => onAdd({ deal_name: name, customer, currency, amount, probability: prob, expected_close_date: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10), expected_payment_date: new Date(Date.now() + 75 * 86400000).toISOString().slice(0, 10), stage })}><Plus size={15} /> Add deal scenario</button></div>
    <div className="card panel"><h3>Pipeline exposures & soft-planning bands</h3><div className="table-scroll"><table><thead><tr><th>Deal</th><th>Customer</th><th>Gross value</th><th>CRM probability</th><th>Planning exposure</th><th>Exposure status</th><th>25% scenario</th><th>50% scenario</th><th>75% scenario</th><th>Payment date</th></tr></thead><tbody>{rows.map((r: any) => { const weighted = Number(r.risk_weighted_amount); return <tr key={r.id}><td><b>{r.deal_name}</b><small>Pipeline forecast · not booked</small></td><td>{r.customer}</td><td>{fmt(r.amount, r.currency)}</td><td>{(Number(r.probability) * 100).toFixed(0)}%</td><td className="numeric">{fmt(weighted, r.currency)}</td><td><span className={`status ${r.exposure_mode === 'FIRM_PRE_INVOICE' ? 'open' : r.exposure_mode === 'EXCLUDED_LOST' ? 'pending' : 'forecast'}`}>{r.exposure_mode === 'FIRM_PRE_INVOICE' ? 'Firm pre-invoice' : r.exposure_mode === 'EXCLUDED_LOST' ? 'Lost / excluded' : 'Weighted forecast'}</span></td><td>{fmt(weighted * .25, r.currency)}</td><td>{fmt(weighted * .5, r.currency)}</td><td>{fmt(weighted * .75, r.currency)}</td><td>{r.expected_payment_date}</td></tr>; })}</tbody></table></div><p className="helper">For open stages, the planning exposure is gross deal value × win probability. At CONTRACT_SIGNED / WON, the pre-invoice planning amount becomes 100% of the deal until the invoice is ingested. LOST / CANCELLED deals are excluded. The 25/50/75% bands are coverage scenarios, not hedge instructions.</p></div>
    <div className="card panel"><div className="panel-head"><div><h3>CRM opportunity update simulator</h3><p>Exercise the event contract used by a future Zoho CRM, HubSpot or Salesforce webhook.</p></div><span className="demo-label">CRM EVENT</span></div><div className="form-grid"><label>Pipeline deal<select value={selectedDeal} onChange={e => { const row = rows.find((x: any) => x.id === e.target.value); setSelectedDeal(e.target.value); if (row) { setUpdatedProbability(String(row.probability)); setUpdatedPaymentDate(row.expected_payment_date); } }}>{rows.map((r: any) => <option key={r.id} value={r.id}>{r.deal_name} · {r.currency}</option>)}</select></label><label>Updated gross amount<input type="number" min="0.01" value={updatedAmount} onChange={e => setUpdatedAmount(e.target.value)} /></label><label>Updated win probability<input type="number" min="0" max="1" step="0.05" value={updatedProbability} onChange={e => setUpdatedProbability(e.target.value)} /></label><label>Updated CRM stage<select value={updatedStage} onChange={e => setUpdatedStage(e.target.value)}><option>LEAD</option><option>QUALIFICATION</option><option>PROPOSAL</option><option>NEGOTIATION</option><option>CONTRACT_SENT</option><option>CONTRACT_SIGNED</option><option>WON</option><option>LOST</option></select></label><label>Revised expected payment date<input type="date" value={updatedPaymentDate} onChange={e => setUpdatedPaymentDate(e.target.value)} /></label></div><button className="secondary" disabled={!currentDeal || Number(updatedAmount) <= 0 || Number(updatedProbability) < 0 || Number(updatedProbability) > 1 || !updatedPaymentDate} onClick={() => onUpdate({ event_type: 'CRM_DEAL_UPDATED', entity_type: 'pipeline_deal', entity_id: selectedDeal, idempotency_key: `crm-deal-update:${selectedDeal}:${updatedProbability}:${updatedPaymentDate}:${Date.now()}`, payload: { amount: updatedAmount, probability: updatedProbability, stage: updatedStage, expected_payment_date: updatedPaymentDate } })}><RefreshCw size={15} /> Process CRM deal update event</button><p className="helper">The demo event updates the existing opportunity and recalculates probability-weighted planning values. No invoice is created.</p></div>
    <div className="info-banner"><Zap size={17} /> CRM connector slots: Zoho CRM / HubSpot / Salesforce can feed the same event-and-pipeline model. This build has a working internal event contract and simulator; live provider authentication, signature verification and webhooks remain integration work.</div>
  </>;
}

function ShadowBalances({ data, onResolve }: any) {
  const snapshots = data.cash_snapshots || [];
  const ledger = data.settlement_ledger || [];
  return <><PageIntro tag="CROSS-CURRENCY RECONCILIATION" title="Shadow balances & settlement treatment" desc="Keep invoice settlement, retained foreign-currency cash and imported bank/GL cash snapshots distinct so receipts are not falsely removed or counted twice." />
    <div className="info-banner"><Database size={17} /> Cash snapshots are point-in-time balances. The payment ledger is shown separately and is not added to the snapshots. A retained USD receipt remains a USD cash asset; a converted INR receipt leaves the USD cash exposure.</div>
    <div className="stats-grid shadow-stats"><Stat label="Cash snapshot rows" value={snapshots.length} sub="Imported / seeded balances" icon={Wallet} /><Stat label="Settlement events" value={ledger.length} sub="Linked payment movements" icon={FileCheck2} tone="violet" /><Stat label="Retained FX receipts" value={ledger.filter((x: any) => x.classification === 'FOREIGN_CURRENCY_CASH').length} sub="Remain foreign-currency assets" icon={Globe2} tone="green" /><Stat label="Unresolved treatments" value={ledger.filter((x: any) => x.classification === 'UNRESOLVED' || x.classification === 'CROSS_CURRENCY_REVIEW').length} sub="Require source verification" icon={AlertTriangle} tone="amber" /></div>
    <div className="card panel"><h3>Cash / GL balance snapshots</h3><div className="table-scroll"><table><thead><tr><th>Legal entity</th><th>Currency</th><th>Book balance</th><th>Available balance</th><th>As of</th></tr></thead><tbody>{snapshots.map((x: any) => <tr key={x.id}><td><b>{x.legal_entity}</b></td><td>{x.currency}</td><td>{fmt(x.balance, x.currency)}</td><td>{fmt(x.available_balance, x.currency)}</td><td>{x.as_of}</td></tr>)}</tbody></table></div></div>
    <div className="card panel"><h3>Invoice-to-cash settlement ledger</h3><div className="table-scroll"><table><thead><tr><th>Payment reference</th><th>Invoice</th><th>Amount</th><th>Payment date</th><th>Treatment</th><th>Destination</th><th>Classification / action</th></tr></thead><tbody>{ledger.map((x: any) => <SettlementRow key={x.id} row={x} onResolve={onResolve} />)}</tbody></table></div></div>
    <p className="helper">{data.warning}</p>
  </>;
}


function SettlementRow({ row, onResolve }: any) {
  const [destination, setDestination] = useState('INR');
  const [rate, setRate] = useState('');
  const needsReview = row.classification === 'UNRESOLVED' || row.classification === 'CROSS_CURRENCY_REVIEW';
  const update = (treatment: string, destinationCurrency: string, conversionRate?: string) => onResolve({
    event_type: 'PAYMENT_TREATMENT_UPDATED', entity_type: 'payment', entity_id: row.id,
    idempotency_key: `payment-treatment:${row.id}:${treatment}:${destinationCurrency}:${Date.now()}`,
    payload: { treatment, destination_currency: destinationCurrency, ...(conversionRate ? { conversion_rate: conversionRate } : {}) },
  });
  return <tr><td><b>{row.source_record_id || row.id.slice(0, 8)}</b></td><td>{row.invoice_number}</td><td>{fmt(row.amount, row.currency)}</td><td>{row.payment_date}</td><td>{row.treatment}</td><td>{row.destination_currency || '—'}</td><td><span className={`status ${needsReview ? 'pending' : 'open'}`}>{row.classification.replaceAll('_', ' ')}</span>{needsReview && <div className="settlement-actions"><button className="textbtn" onClick={() => update('RETAINED', row.currency)}>Retained as {row.currency}</button><div className="settlement-convert"><select aria-label="Settlement destination currency" value={destination} onChange={e => setDestination(e.target.value)}><option>INR</option><option>USD</option><option>EUR</option><option>AED</option><option>GBP</option><option>JPY</option></select><input aria-label="Conversion rate" type="number" min="0" step="any" placeholder="Dest/source rate" value={rate} onChange={e => setRate(e.target.value)} /><button className="textbtn" disabled={destination !== 'INR' && (!(Number(rate) > 0) || destination === row.currency)} onClick={() => update('CONVERTED', destination, rate)}>Confirm conversion</button></div></div>}</td></tr>;
}

function Netting({ rows }: any) {
  return <><PageIntro tag="INTERCOMPANY NETTING" title="Group payment offsets" desc="Identify reciprocal positions across group entities before treasury decides whether legal and operational net settlement is permitted." /><div className="info-banner"><AlertTriangle size={17} /> These calculations are illustrative economic offsets only. Legal netting enforceability, tax, transfer pricing, settlement agreements and jurisdictional restrictions are not assessed.</div><div className="card panel"><div className="table-scroll"><table><thead><tr><th>Entity pair</th><th>Currency</th><th>Gross receivables</th><th>Gross payables</th><th>Illustrative net</th><th>Timing compatibility</th></tr></thead><tbody>{rows.map((r: any, i: number) => <tr key={i}><td><b>{r.entities.join(' ↔ ')}</b></td><td>{r.currency}</td><td>{fmt(r.gross_receivables, r.currency)}</td><td>{fmt(r.gross_payables, r.currency)}</td><td>{r.illustrative_net === null ? '—' : fmt(r.illustrative_net, r.currency)}</td><td><span className={`status ${r.compatible_for_demo_netting ? 'open' : 'pending'}`}>{r.compatible_for_demo_netting ? 'Within demo window' : 'Review timing'}</span></td></tr>)}</tbody></table></div></div></>;
}

function Liquidity({ cashSnapshots }: any) {
  const seededCash = cashSnapshots.filter((x: any) => x.currency === 'INR').reduce((sum: number, x: any) => sum + Number(x.available_balance), 0);
  const [cash, setCash] = useState(String(seededCash || 10500000));
  const [receipts, setReceipts] = useState('2500000'); const [payments, setPayments] = useState('4800000');
  const [margin, setMargin] = useState('1500000'); const [shock, setShock] = useState('-5'); const [creditLimit, setCreditLimit] = useState('3000000'); const [creditDrawn, setCreditDrawn] = useState('750000'); const [result, setResult] = useState<any>(null);
  useEffect(() => { if (seededCash > 0) setCash(String(seededCash)); }, [seededCash]);
  return <><PageIntro tag="LIQUIDITY & MARGIN CO-PILOT" title="Cash-constrained stress test" desc="Stress FX-linked receipts and payments against operating cash, margin calls and committed credit-line headroom." /><div className="card panel"><div className="form-grid">{[['Available INR cash (seeded from snapshot)', cash, setCash], ['FX-linked expected receipts (baseline INR)', receipts, setReceipts], ['Expected payments (INR)', payments, setPayments], ['Illustrative margin call (INR)', margin, setMargin], ['FX shock on linked receipts (%)', shock, setShock], ['Committed credit-line limit (INR)', creditLimit, setCreditLimit], ['Current credit-line drawn (INR)', creditDrawn, setCreditDrawn]].map(([label, value, setter]: any) => <label key={label}>{label}<input value={value} onChange={e => setter(e.target.value)} type="number" /></label>)}</div><button className="primary" onClick={async () => setResult(await post('/api/liquidity/stress', { cash_inr: cash, expected_receipts_inr: receipts, expected_payments_inr: payments, margin_call_inr: margin, fx_shock_pct: shock, credit_line_limit_inr: creditLimit, credit_line_drawn_inr: creditDrawn }))}><Activity size={15} /> Run liquidity stress</button>{result && <div className="result-grid"><Result label="Cash before margin" value={fmt(result.cash_before_margin_inr, 'INR')} /><Result label="Cash after margin" value={fmt(result.cash_after_margin_inr, 'INR')} /><Result label="Potential shortfall before credit" value={fmt(result.liquidity_shortfall_inr, 'INR')} warning={Number(result.liquidity_shortfall_inr) > 0} /><Result label="Undrawn credit capacity" value={fmt(result.undrawn_credit_capacity_inr, 'INR')} /><Result label="Credit-line utilisation" value={`${fmt(result.credit_line_utilisation_pct)}%`} warning={Number(result.credit_line_utilisation_pct) >= 90} /><Result label="Shortfall after available credit" value={fmt(result.shortfall_after_available_credit_inr, 'INR')} warning={Number(result.shortfall_after_available_credit_inr) > 0} /></div>}<p className="helper">Undrawn credit is treated as illustrative committed capacity, not cash already available. Facility covenants and draw conditions are not modelled. Real margin calls depend on derivative valuation, collateral, thresholds, netting sets, CSA and bank terms.</p></div></>;
}
function Result({ label, value, warning }: any) { return <div className="result"><small>{label}</small><b className={warning ? 'warning-text' : ''}>{value}</b></div>; }

function WorkingCapital() {
  const [amount, setAmount] = useState('50000'); const [spot, setSpot] = useState('86'); const [forward, setForward] = useState('86.5');
  const [days, setDays] = useState('60'); const [discount, setDiscount] = useState('1.2'); const [finance, setFinance] = useState('12'); const [result, setResult] = useState<any>(null);
  return <><PageIntro tag="WORKING CAPITAL OPTIMISER" title="Hedge cost vs early payment" desc="Compare an illustrative forward conversion value with the cost of early-payment discounts and local-currency financing." /><div className="card panel"><div className="form-grid">{[['Invoice amount (USD)', amount, setAmount], ['Spot reference (INR/USD)', spot, setSpot], ['Indicative forward rate', forward, setForward], ['Days to payment', days, setDays], ['Early-payment discount (%)', discount, setDiscount], ['Local-currency / supply-chain financing annual rate (%)', finance, setFinance]].map(([label, value, setter]: any) => <label key={label}>{label}<input value={value} onChange={e => setter(e.target.value)} type="number" /></label>)}</div><button className="primary" onClick={async () => setResult(await post('/api/working-capital/compare', { invoice_amount: amount, currency: 'USD', spot_rate: spot, forward_rate: forward, days_to_payment: Number(days), early_discount_pct: discount, financing_annual_pct: finance }))}>Compare scenarios</button>{result && <div className="result-grid"><Result label="Indicative forward value" value={fmt(result.indicative_forward_inr, 'INR')} /><Result label="Early discount cost" value={fmt(result.early_discount_cost_inr, 'INR')} /><Result label="Financing cost" value={fmt(result.financing_cost_inr, 'INR')} /></div>}<p className="helper">Not a recommendation to borrow, discount or hedge. Excludes fees, taxes, forward points, credit terms and counterparty risk.</p></div></>;
}

function ScenarioLab() {
  const [shock, setShock] = useState('-5'); const [delay, setDelay] = useState('15'); const [reduction, setReduction] = useState('10'); const [result, setResult] = useState<any>(null);
  return <><PageIntro tag="WHAT-IF ANALYSIS" title="FX and cash-flow scenario lab" desc="Stress the demo USD receivable book for exchange-rate moves, payment delays and pipeline/invoice reductions. Results are illustrative, not forecasts." /><div className="card panel"><div className="form-grid"><label>USD/INR change (%)<input type="number" value={shock} onChange={e => setShock(e.target.value)} /></label><label>Payment delay (days)<input type="number" min="0" value={delay} onChange={e => setDelay(e.target.value)} /></label><label>Invoice reduction (%)<input type="number" min="0" max="100" value={reduction} onChange={e => setReduction(e.target.value)} /></label></div><button className="primary" onClick={async () => setResult(await post('/api/scenarios/run', { usd_inr_change_pct: shock, payment_delay_days: Number(delay), invoice_reduction_pct: reduction }))}><Activity size={15} /> Run scenario</button>{result && <><div className="result-grid"><Result label="Base USD receivables" value={fmt(result.base_usd_receivables, 'USD')} /><Result label="Stressed USD receivables" value={fmt(result.stressed_usd_receivables, 'USD')} /><Result label="Scenario USD/INR reference" value={fmt(result.reference_rate, 'INR')} /><Result label="Base INR value" value={fmt(result.base_inr_value, 'INR')} /><Result label="Stressed INR value" value={fmt(result.stressed_inr_value, 'INR')} /><Result label="Payment delay" value={`${result.payment_delay_days} days`} /></div><p className="helper">{result.note}</p></>}</div></>;
}

function Accounting({ hedges, onCreate }: any) {
  const [hedge, setHedge] = useState(hedges[0]?.id || ''); const [framework, setFramework] = useState('Ind AS 109');
  return <><PageIntro tag="HEDGE ACCOUNTING COPILOT" title="Documentation drafts" desc="Generate a structured designation memo and evidence checklist for professional review. No automatic journal entry or hedge-effectiveness conclusion." /><div className="card panel"><div className="form-grid"><label>Hedge contract<select value={hedge} onChange={e => setHedge(e.target.value)}>{hedges.map((h: any) => <option value={h.id} key={h.id}>{h.contract_number} · {h.currency_pair}</option>)}</select></label><label>Accounting framework<select value={framework} onChange={e => setFramework(e.target.value)}><option>Ind AS 109</option><option>IFRS 9</option><option>ASC 815</option></select></label></div><button className="primary" disabled={!hedge} onClick={() => onCreate(hedge, framework)}><FileCheck2 size={15} /> Generate draft memo</button><div className="info-banner"><AlertTriangle size={17} /> Hedge accounting eligibility and designation require contemporaneous documentation, valuation inputs and qualified accounting review. This MVP intentionally does not invent journal entries.</div></div></>;
}

function Connections({ status }: any) {
  const [zoho, setZoho] = useState<any>(null); const [rate, setRate] = useState<any>(null); const [busy, setBusy] = useState(''); const [error, setError] = useState('');
  async function testZoho() { setBusy('zoho'); setError(''); setZoho(null); try { setZoho(await api<any>('/api/integrations/zoho/test')); } catch (e: any) { setError(e.message); } finally { setBusy(''); } }
  async function getRate() { setBusy('rate'); setError(''); setRate(null); try { setRate(await api<any>('/api/integrations/fx-rate?symbol=USD/INR')); } catch (e: any) { setError(e.message); } finally { setBusy(''); } }
  return <><PageIntro tag="HEADLESS CONNECTOR LAYER" title="Connections & data sources" desc="Test the credentials and read-only permissions that are actually configured. Provider data is not imported into the demo ledger unless explicitly mapped." />
    <div className="connection-grid">
      <div className="card connection-card"><div className="connection-icon"><Building2 size={20} /></div><div className="connection-heading"><b>Zoho Books</b><span className={`status ${status?.zoho_credentials_configured ? 'open' : 'pending'}`}>{status?.zoho_credentials_configured ? (status?.zoho_organization_selected ? 'Credentials + organization set' : 'Credentials configured · choose org') : 'Credentials missing'}</span></div><p>Read-only OAuth test: validates your refresh token, lists organizations you can access, then checks invoice and customer-payment retrieval when an organization ID is selected.</p><button className="secondary" disabled={!status?.zoho_credentials_configured || !!busy} onClick={testZoho}>{busy === 'zoho' ? 'Testing connection…' : 'Test Zoho read-only access'}</button>{zoho && <div className="connection-result"><b>{zoho.status === 'CONNECTED_READ_ONLY' ? 'Connected — read only' : 'Zoho authenticated'}</b><p>Organizations found: {zoho.organization_count}</p>{zoho.organizations?.map((o: any) => <p key={o.organization_id}>{o.name} · {o.currency_code} · ID: {o.organization_id}{o.is_default_org ? ' · Default' : ''}</p>)}{zoho.invoice_count !== undefined && <p>Invoices retrieved: {zoho.invoice_count} · Customer payments retrieved: {zoho.payment_count}</p>}<small>{zoho.next_step || 'No data was modified.'}</small></div>}</div>
      <div className="card connection-card"><div className="connection-icon"><Globe2 size={20} /></div><div className="connection-heading"><b>Twelve Data</b><span className={`status ${status?.twelve_data_configured ? 'open' : 'pending'}`}>{status?.twelve_data_configured ? 'Credentials configured' : 'Not configured'}</span></div><p>Indicative reference FX rates for scenario context. Not a bank quote or executable forward price.</p><button className="secondary" disabled={!status?.twelve_data_configured || !!busy} onClick={getRate}>{busy === 'rate' ? 'Testing provider…' : 'Test USD/INR reference rate'}</button>{rate && <div className="connection-result"><b>Provider response</b>{Object.entries(rate).map(([k,v]) => <p key={k}>{k.replaceAll('_',' ')}: {String(v)}</p>)}</div>}</div>
      <div className="card connection-card"><div className="connection-icon"><Workflow size={20} /></div><div className="connection-heading"><b>CRM pipeline</b><span className="status pending">Connector extension point</span></div><p>Manual pipeline data supports probability-weighted pre-invoice scenarios. Provider-specific HubSpot / Salesforce OAuth and webhooks are not enabled in this build.</p></div>
      <div className="card connection-card"><div className="connection-icon"><Landmark size={20} /></div><div className="connection-heading"><b>Bank / treasury feeds</b><span className="status pending">Not connected</span></div><p>Shadow cash reconciliation currently uses seeded cash snapshots and payment events. No live bank API or Account Aggregator consent is configured.</p></div>
      <div className="card connection-card"><div className="connection-icon"><Zap size={20} /></div><div className="connection-heading"><b>AI explanations</b><span className="status pending">Not invoked</span></div><p>An API key placeholder exists, but the deterministic exposure and hedge engine does not call an LLM. Financial calculations remain code-driven.</p></div>
      <div className="card connection-card"><div className="connection-icon"><ShieldCheck size={20} /></div><div className="connection-heading"><b>Execution adapter</b><span className="status open">Simulation only</span></div><p>No broker, bank trading API, forward booking or automatic rollover is connected. Approved proposals can only be simulated locally.</p></div>
      <div className="card connection-card"><div className="connection-icon"><Globe2 size={20} /></div><div className="connection-heading"><b>India-first corridor profile</b><span className="status open">INR base model</span></div><p>Currency-pair and legal-entity-aware records support an India exporter starting point (USD/INR, EUR/INR and extensible APAC corridors). No regulatory eligibility, RBI/IFSCA permission or market access is inferred by the software.</p></div>
    </div>
    {error && <div className="toast error"><AlertTriangle size={15} />{error}</div>}
    <div className="info-banner"><ShieldAlert size={17} /> Zoho test requires a Self Client refresh token with <code>ZohoBooks.settings.READ</code>, <code>ZohoBooks.invoices.READ</code> and <code>ZohoBooks.customerpayments.READ</code>. If the account has no Books organisation, the test will confirm authentication and explain that no organisation is available. Secrets remain backend-only.</div>
  </>;
}

function auditDetailSummary(details: any) {
  if (!details || typeof details !== 'object') return String(details ?? '—');
  const payload = details.payload && typeof details.payload === 'object' ? details.payload : details;
  const labels: Record<string,string> = { amount: 'Deal amount', probability: 'Win probability', stage: 'Pipeline stage', expected_payment_date: 'Expected payment date', treatment: 'Settlement treatment', destination_currency: 'Destination currency', conversion_rate: 'Conversion rate', action_type: 'Action type', framework: 'Accounting framework', hedge_contract: 'Hedge contract', note: 'Note' };
  const entries = Object.entries(payload).filter(([k]) => k !== 'event_id' && k !== 'idempotency_key' && k !== 'payload');
  const formatted = entries.map(([key,value]) => {
    const label = labels[key] || key.replaceAll('_',' ').replace(/^./, c => c.toUpperCase());
    let shown = String(value);
    if (key === 'probability' && Number(value) <= 1) shown = `${(Number(value)*100).toFixed(1)}%`;
    if (key === 'amount') shown = Number(value).toLocaleString('en-IN', {maximumFractionDigits:2});
    return {label, shown};
  });
  if (details.event_id) formatted.push({label:'Event reference',shown:String(details.event_id).slice(0,8)});
  if (details.idempotency_key) formatted.push({label:'Duplicate protection key',shown:String(details.idempotency_key).slice(0,12)+'…'});
  return formatted;
}
function Audit({ rows }: any) {
  return <><PageIntro tag="TRACEABILITY" title="Audit trail" desc="Readable summaries of system and user actions. Expand a row for source references and technical payload when needed." /><div className="card panel"><div className="table-scroll"><table><thead><tr><th>Time</th><th>Actor</th><th>Event</th><th>Entity</th><th>What happened</th></tr></thead><tbody>{rows.map((r: any) => { const items = auditDetailSummary(r.details); return <tr key={r.id}><td>{new Date(r.created_at).toLocaleString()}</td><td>{r.actor}</td><td><b>{r.event_type.replaceAll('_',' ')}</b></td><td>{r.entity_type.replaceAll('_',' ')} · {String(r.entity_id).slice(0,8)}</td><td><div className="audit-summary">{Array.isArray(items) ? items.slice(0,4).map((item: any) => <span key={item.label}><small>{item.label}</small><b>{item.shown}</b></span>) : items}<details><summary>Technical details</summary><pre>{JSON.stringify(r.details,null,2)}</pre></details></div></td></tr>; })}</tbody></table></div></div></>;
}
