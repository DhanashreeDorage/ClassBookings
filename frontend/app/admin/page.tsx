"use client";
import { useEffect, useMemo, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "";
type Booking = { id:number; class_date:string; name:string; email:string; phone?:string; learning_goal?:string; status:string; created_at?:string };
const statuses = ["Pending", "Approved", "Rejected", "Cancelled", "All"];
const prettyDate = (value:string) => new Date(`${value}T12:00:00`).toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric",year:"numeric"});
export default function Admin() {
  const [token,setToken] = useState("");
  const [username,setUsername] = useState("");
  const [password,setPassword] = useState("");
  const [rows,setRows] = useState<Booking[]>([]);
  const [filter,setFilter] = useState("Pending");
  const [query,setQuery] = useState("");
  const [dateFilter,setDateFilter] = useState("");
  const [error,setError] = useState("");
  const [message,setMessage] = useState("");
  const [busy,setBusy] = useState(false);
  const counts = useMemo(()=>({total:rows.length,pending:rows.filter(x=>x.status==="Pending").length,approved:rows.filter(x=>x.status==="Approved").length,rejected:rows.filter(x=>x.status==="Rejected").length}),[rows]);

  async function load(activeToken=token) {
    if(!activeToken) return;
    const params = new URLSearchParams();
    if(dateFilter) params.set("class_date",dateFilter);
    if(query.trim()) params.set("q",query.trim());
    const response = await fetch(`${API}/api/admin/bookings?${params.toString()}`,{headers:{Authorization:`Bearer ${activeToken}`},cache:"no-store"});
    const payload = await response.json();
    if(!response.ok) { setError(payload.detail||"Could not load bookings"); if(response.status===401) setToken(""); return; }
    setRows(payload);
    setError("");
  }
  async function login(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch(`${API}/api/admin/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,password})});
      const payload = await response.json();
      if(!response.ok) throw new Error(payload.detail||"Login failed");
      setToken(payload.access_token); setPassword(""); await load(payload.access_token);
    } catch(e) { setError(e instanceof Error?e.message:"Unable to sign in"); }
    finally { setBusy(false); }
  }
  async function changeStatus(id:number,action:"approve"|"reject"|"cancel") {
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch(`${API}/api/admin/bookings/${id}/${action}`,{method:"POST",headers:{Authorization:`Bearer ${token}`}});
      const payload = await response.json();
      if(!response.ok) throw new Error(payload.detail||"Action failed");
      setMessage(`Booking #${id}: ${payload.status}`); await load();
    } catch(e) { setError(e instanceof Error?e.message:"Unable to update booking"); }
    finally { setBusy(false); }
  }
  useEffect(()=>{ if(token) load(); },[filter,dateFilter]);
  const visibleRows = rows.filter(row=>filter==="All"||row.status===filter);
  const today = new Date().toLocaleDateString("en-CA");

  if(!token) return <main className="admin-shell">
    <div className="admin-brand"><a href="/" className="brand-lockup"><span className="brand-mark">R</span><span><b>ROYALTICA</b><small>PUBLISHING ACADEMY</small></span></a><a className="quiet-link" href="/">← Back to booking page</a></div>
    <section className="login-layout"><div className="login-copy"><div className="eyebrow">ROYALTICA · CLASS OPERATIONS</div><h1>Your class,<br/><em>beautifully managed.</em></h1><p>Review student requests, confirm seats, and keep every morning session organized.</p><div className="login-points"><span>✦ Approval-based registration</span><span>✦ 25 approved seats per class</span><span>✦ Private participant records</span></div></div>
      <form className="login-card" onSubmit={login}><div className="login-icon">✦</div><div className="eyebrow">ADMINISTRATOR ACCESS</div><h2>Welcome back</h2><p className="muted">Sign in to manage Morning Publishing Class.</p>{error&&<div className="alert error">{error}</div>}<label className="field"><span>Administrator email</span><input type="email" placeholder="admin@yourdomain.com" autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} required/></label><label className="field"><span>Password</span><input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></label><button className="primary-btn full" disabled={busy}>{busy?"Signing in…":"Sign in to dashboard →"}</button><small className="security-note">Secure administrator access · Sessions expire after 8 hours</small></form>
    </section><footer className="site-footer">© Royaltica Publishing · Learn · Write · Publish · Grow</footer>
  </main>;

  return <main className="dashboard-shell"><aside className="sidebar"><a href="/" className="brand-lockup"><span className="brand-mark">R</span><span><b>ROYALTICA</b><small>PUBLISHING ACADEMY</small></span></a><div className="side-label">WORKSPACE</div><a className="side-item active" href="/admin">▦ <span>Overview</span></a><a className="side-item" href="/">◷ <span>Public booking page</span></a><div className="sidebar-bottom"><div className="admin-avatar">A</div><div><b>Administrator</b><small>Class operations</small></div><button className="icon-btn" title="Sign out" onClick={()=>{setToken("");setRows([])}}>↪</button></div></aside>
    <section className="dashboard-main"><header className="dash-top"><div><div className="eyebrow">ROYALTICA / MORNING CLASS</div><h1>Booking overview</h1></div><div className="top-actions"><span className="live-dot">Live workspace</span><button className="outline-btn" onClick={()=>load()} disabled={busy}>↻ Refresh</button></div></header>
      <div className="welcome-strip"><div><span className="welcome-tag">DAILY SESSION · EASTERN TIME</span><h2>Good morning. Let’s make room for great stories.</h2><p>Manage registrations for your 8:00–9:00 AM publishing class.</p></div><div className="welcome-time"><b>08:00 <span>AM</span></b><small>— 09:00 AM · ET</small></div></div>
      <div className="stat-grid"><article className="stat-card"><span>Total shown</span><b>{counts.total}</b><small>Current filtered results</small></article><article className="stat-card"><span>Pending review</span><b>{counts.pending}</b><small>Awaiting your decision</small></article><article className="stat-card"><span>Approved bookings</span><b>{counts.approved}</b><small>Across selected results</small></article><article className="stat-card"><span>Not approved</span><b>{counts.rejected}</b><small>Rejected requests shown</small></article></div>
      <section className="table-card"><div className="table-heading"><div><div className="eyebrow">PARTICIPANT MANAGEMENT</div><h2>Class registrations</h2><p>Review requests and manage approved seats.</p></div><span className="capacity-chip">25 seats per class</span></div>
        <div className="filters"><label className="search-field">⌕ <input placeholder="Search name or email" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&load()}/></label><select value={filter} onChange={e=>setFilter(e.target.value)}>{statuses.map(x=><option key={x} value={x}>{x} status</option>)}</select><input aria-label="Filter by class date" type="date" value={dateFilter} min={today} onChange={e=>setDateFilter(e.target.value)}/><button className="outline-btn" onClick={()=>load()}>Apply filters</button><button className="text-btn" onClick={()=>{setQuery("");setDateFilter("");setFilter("Pending");setRows(current=>current.filter(x=>x.status==="Pending"))}}>Reset</button></div>
        {error&&<div className="alert error">{error}</div>}{message&&<div className="alert success">{message}</div>}
        <div className="table-wrap"><table className="booking-table"><thead><tr><th>CLASS DATE</th><th>PARTICIPANT</th><th>LEARNING GOAL</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{visibleRows.map(b=><tr key={b.id}><td><b>{prettyDate(b.class_date)}</b><small>8:00–9:00 AM ET</small></td><td><b>{b.name}</b><a href={`mailto:${b.email}`}>{b.email}</a>{b.phone&&<small>{b.phone}</small>}</td><td className="goal-cell">{b.learning_goal||"—"}</td><td><span className={`status-pill ${b.status.toLowerCase()}`}>{b.status}</span></td><td><div className="action-group">{b.status==="Pending"&&<><button className="approve-btn" disabled={busy} onClick={()=>changeStatus(b.id,"approve")}>Approve</button><button className="reject-btn" disabled={busy} onClick={()=>changeStatus(b.id,"reject")}>Reject</button></>}{b.status==="Approved"&&<button className="reject-btn" disabled={busy} onClick={()=>changeStatus(b.id,"cancel")}>Cancel seat</button>}</div></td></tr>)}</tbody></table>{!visibleRows.length&&<div className="empty-state"><span>✦</span><b>No registrations found</b><p>Try changing your filters or refresh the list.</p></div>}</div>
      </section><footer className="site-footer">Participant information is private and visible only to authorized administrators.</footer>
    </section></main>;
}
