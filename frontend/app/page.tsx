"use client";
import { useEffect, useMemo, useState } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "";
type Slot = {slot_start:string;start_ist:string;end_ist:string;start_et:string;end_et:string;et_date_label:string;ist_label:string;et_label:string;approved:number;pending:number;participants:string[];capacity:number;available:number;full:boolean};
type Session = {date:string;slots:Slot[];legacy?:{label:string;pending:number;approved:number;participants:string[]}|null;approved:number;pending:number;booking_status:string};
type BookingForm = {class_date:string;slot_start:string;full_name:string;email:string;phone:string;learning_goal:string};
const dateKey = (d:Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const monthLabel = (d:Date) => d.toLocaleDateString(undefined,{month:"long",year:"numeric"});
const todayIST = () => {const p=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Kolkata",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());const get=(t:string)=>p.find(x=>x.type===t)?.value||"";return `${get("year")}-${get("month")}-${get("day")}`};
const dualSlotLabel = (slot:Slot) => `${slot.ist_label} · ${slot.et_label}${slot.et_date_label!=="same day"?" (previous day ET)":""}`;
const formatClassTime = (start:string,end:string) => `${new Date(`2000-01-01T${start}:00`).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit",hour12:true}).replace(" AM","")}–${new Date(`2000-01-01T${end}:00`).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit",hour12:true})}`;
export default function Home(){
 const [sessions,setSessions]=useState<Session[]>([]),[message,setMessage]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false),[month,setMonth]=useState(()=>new Date(`${todayIST()}T12:00:00`)),[selectedDate,setSelectedDate]=useState(()=>todayIST()),[showStatus,setShowStatus]=useState(false),[statusEmail,setStatusEmail]=useState(""),[statusRef,setStatusRef]=useState(""),[statusResult,setStatusResult]=useState<{reference:string;class_date:string;class_time:string;status:string;message:string}|null>(null),[statusError,setStatusError]=useState(""),[statusBusy,setStatusBusy]=useState(false);
 const [form,setForm]=useState<BookingForm>({class_date:todayIST(),slot_start:"17:00",full_name:"",email:"",phone:"",learning_goal:""});
 const firstDay = useMemo(()=>new Date(month.getFullYear(),month.getMonth(),1),[month]);
 const calendarCells = useMemo(()=>{const start=new Date(firstDay);start.setDate(1-firstDay.getDay());return Array.from({length:42},(_,i)=>{const d=new Date(start);d.setDate(start.getDate()+i);return d})},[firstDay]);
 async function load(){const start=new Date(month.getFullYear(),month.getMonth(),1);const end=new Date(month.getFullYear(),month.getMonth()+1,0);try{const r=await fetch(`${API}/api/public/calendar?start=${dateKey(start)}&end=${dateKey(end)}`,{cache:"no-store"});const j=await r.json();if(!r.ok)throw new Error(j.detail||"Calendar unavailable");setSessions(j.sessions||[]);setError("")}catch(e){setError(e instanceof Error?e.message:"Calendar is temporarily unavailable.")}}
 useEffect(()=>{load()},[month]);
 const selected = sessions.find(s=>s.date===selectedDate);
 function chooseDate(value:string){setSelectedDate(value);const picked=new Date(`${value}T12:00:00`);if(!Number.isNaN(picked.getTime()))setMonth(new Date(picked.getFullYear(),picked.getMonth(),1));const day=sessions.find(x=>x.date===value);const firstOpen=day?.slots.find(slot=>!slot.full)?.slot_start||"17:00";setForm(f=>({...f,class_date:value,slot_start:firstOpen}));setMessage("")}
 async function submit(e:React.FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setMessage("");setError("");try{const r=await fetch(`${API}/api/bookings`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(form)});const j=await r.json();if(!r.ok)throw new Error(j.detail||"Unable to submit booking");setMessage(`Your request has been received. Booking reference: ${j.reference}. Save this reference to check your status. Your request is Pending approval; your seat is not reserved until approved.`);setForm({class_date:selectedDate,slot_start:form.slot_start,full_name:"",email:"",phone:"",learning_goal:""});await load()}catch(e){setError(e instanceof Error?e.message:"Unable to submit booking")}finally{setBusy(false)}}
 return <main className="public-shell simple-public-shell">
  <header className="public-header simple-header">
   <a className="brand-lockup" href="/"><span className="brand-mark">R</span><span><b>ROYALTICA</b><small>PUBLISHING ACADEMY</small></span></a>
   <a className="header-admin" href="/admin">Admin sign in <span>↗</span></a>
  </header>
  <section className="simple-intro">
   <div className="eyebrow">ROYALTICA PUBLISHING</div>
   <h1>Evening Publishing Class</h1>
   <p>Choose an evening time, book your class, and check your approval status.</p>
   <div className="simple-class-time"><span>Daily · 5:00–10:00 PM IST</span><span>US Eastern (EST/EDT) shown automatically</span></div>
  </section>
  <section className="booking-section simple-booking-section">
   <div className="booking-mode-tabs">
    <button type="button" className={!showStatus?"mode-tab active":"mode-tab"} onClick={()=>setShowStatus(false)}>Book a class</button>
    <button type="button" className={showStatus?"mode-tab active":"mode-tab"} onClick={()=>setShowStatus(true)}>Approval status</button>
   </div>
   {!showStatus&&<div className="booking-layout simple-booking-layout">
    <section className="calendar-card simple-card">
     <div className="calendar-top"><div><span className="eyebrow">CLASS CALENDAR</span><h3>{monthLabel(month)}</h3></div><div className="month-actions"><button aria-label="Previous month" onClick={()=>setMonth(new Date(month.getFullYear(),month.getMonth()-1,1))}>‹</button><button aria-label="Next month" onClick={()=>setMonth(new Date(month.getFullYear(),month.getMonth()+1,1))}>›</button></div></div>
     <div className="weekday-grid">{["SUN","MON","TUE","WED","THU","FRI","SAT"].map(d=><span key={d}>{d}</span>)}</div>
     <div className="calendar-grid">{calendarCells.map(d=>{const key=dateKey(d),s=sessions.find(x=>x.date===key),outside=d.getMonth()!==month.getMonth(),past=key<todayIST();const bookedNames=[...(s?.slots.flatMap(slot=>slot.participants.map(name=>({name,time:slot.start_ist.split("–")[0]})))||[]),...(s?.legacy?.participants.map(name=>({name,time:"Previous schedule"}))||[])];return <button key={key} disabled={outside||past||!s||s.booking_status==="Full"} onClick={()=>chooseDate(key)} className={`calendar-day ${outside?"outside":""} ${selectedDate===key?"selected":""} ${s?.booking_status==="Full"?"full":""}`}><b>{d.getDate()}</b>{s&&<>{bookedNames.slice(0,2).map((item,i)=><small className="day-participant" key={`${key}-${i}`} title={`${item.time} · ${item.name}`}>{item.time} · {item.name}</small>)}{bookedNames.length>2&&<small className="day-more">+{bookedNames.length-2} more</small>}{s.pending>0&&<small className="day-pending">{s.pending} pending</small>}<small className="day-available">{s.booking_status==="Full"?"All slots full":"Slots available"}</small></>}</button>})}</div>
     <div className="calendar-legend"><span><i className="legend-dot open"></i> Available</span><span><i className="legend-dot chosen"></i> Selected</span><span><i className="legend-dot closed"></i> Full</span></div>
     <div className="simple-selected-date"><span className="eyebrow">SELECTED DATE</span><strong>{selectedDate?new Date(`${selectedDate}T12:00:00`).toLocaleDateString(undefined,{weekday:"long",month:"long",day:"numeric"}):"Choose a date"}</strong></div>
     {selected&&<div className="calendar-counts"><span><b>{selected.slots.length}</b> evening slots</span><span><b>{selected.pending}</b> pending requests</span>{(selected.slots.some(slot=>slot.participants.length>0)||!!selected.legacy?.participants.length)&&<div className="participant-roster"><strong>Confirmed participants</strong><ul>{[...selected.slots.flatMap(slot=>slot.participants.map((name,i)=><li key={`${selected.date}-${slot.slot_start}-${i}`}>{name} · {slot.ist_label} ({slot.et_label})</li>)),...(selected.legacy?.participants.map((name,i)=><li key={`${selected.date}-legacy-${i}`}>{name} · Previous schedule (8:00–9:00 AM US Eastern)</li>)||[])]}</ul></div>}</div>}
    </section>
    <section className="request-card simple-card">
     <div className="request-heading"><span className="eyebrow">NEW BOOKING</span><h3>Book your place</h3><p>One active booking is allowed per person. Your request needs approval before your place is confirmed.</p></div>
     {message&&<div className="alert success">{message}</div>}{error&&<div className="alert error">{error}</div>}
     <form onSubmit={submit}>
      <label className="field"><span>Class date</span><input type="date" required min={todayIST()} value={form.class_date} onChange={e=>chooseDate(e.target.value)}/></label>
      <div className="field slot-field"><span>Choose a one-hour time slot</span><div className="slot-options">{(selected?.slots||[]).map(slot=><button type="button" key={slot.slot_start} disabled={slot.full} className={`slot-option ${form.slot_start===slot.slot_start?"chosen":""} ${slot.full?"slot-full":""}`} onClick={()=>setForm({...form,slot_start:slot.slot_start})}><b>{slot.ist_label}</b><small>{slot.et_label}{slot.et_date_label!=="same day"?" · previous day":""}</small>{slot.full&&<em>Full</em>}</button>)}</div><small className="timezone-note">All bookings use India Standard Time (IST). US Eastern Time (EST/EDT) is converted automatically for your reference.</small></div>
      <label className="field"><span>Your name *</span><input required minLength={2} maxLength={160} placeholder="Full name" value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/></label>
      <label className="field"><span>Email address *</span><input required type="email" placeholder="you@example.com" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label>
      <label className="field"><span>Phone number <small>Optional</small></span><input placeholder="Phone number" value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label>
      <label className="field"><span>Learning goals <small>Optional</small></span><textarea maxLength={2000} rows={2} placeholder="What would you like help with?" value={form.learning_goal} onChange={e=>setForm({...form,learning_goal:e.target.value})}/></label>
      <button className="primary-btn full" disabled={busy||!form.class_date||!selected?.slots.some(slot=>!slot.full)}>{busy?"Submitting…":"Submit booking"}</button>
     </form>
    </section>
   </div>}
   {showStatus&&<section className="status-lookup-card simple-card">
    <div className="request-heading"><span className="eyebrow">BOOKING STATUS</span><h3>Check your approval</h3><p>Enter the email address and booking reference from your confirmation to see your selected IST and Eastern Time slot.</p></div>
    <form onSubmit={async e=>{e.preventDefault();setStatusBusy(true);setStatusError("");setStatusResult(null);try{const params=new URLSearchParams({email:statusEmail,reference:statusRef});const r=await fetch(`/api/bookings/status?${params.toString()}`,{cache:"no-store"});const j=await r.json();if(!r.ok)throw new Error(j.detail||"Could not find booking");setStatusResult(j)}catch(e){setStatusError(e instanceof Error?e.message:"Unable to check status")}finally{setStatusBusy(false)}}}>
     <label className="field"><span>Email address *</span><input required type="email" value={statusEmail} onChange={e=>setStatusEmail(e.target.value)} placeholder="Email used for booking"/></label>
     <label className="field"><span>Booking reference *</span><input required value={statusRef} onChange={e=>setStatusRef(e.target.value.toUpperCase())} placeholder="ROY-000123"/></label>
     <button className="primary-btn" disabled={statusBusy}>{statusBusy?"Checking…":"Check status"}</button>
    </form>
    {statusError&&<div className="alert error">{statusError}</div>}
    {statusResult&&<div className="status-result"><div><span className="eyebrow">{statusResult.reference}</span><h4>{new Date(`${statusResult.class_date}T12:00:00`).toLocaleDateString(undefined,{weekday:"long",month:"long",day:"numeric",year:"numeric"})}</h4><p>{statusResult.class_time}</p></div><span className={`status-pill ${statusResult.status.toLowerCase()}`}>{statusResult.status}</span><p>{statusResult.message}</p></div>}
   </section>}
  </section>
  <footer className="public-footer simple-footer"><a className="brand-lockup" href="/"><span className="brand-mark">R</span><span><b>ROYALTICA</b><small>PUBLISHING ACADEMY</small></span></a><span>© Royaltica Publishing</span><a href="/admin">Admin</a></footer>
 </main>;
}
