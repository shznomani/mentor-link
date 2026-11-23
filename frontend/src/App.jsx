import { useMemo, useState } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight, Bookmark, Check, ChevronDown, CircleHelp, Compass, GraduationCap, LockKeyhole, Menu, MessageCircle, Search, ShieldCheck, Sparkles, Users, X } from 'lucide-react';

const mentors = [
  { id: 1, name: 'Ananya Rao', initials: 'AR', year: '4th year', branch: 'CSE', avatar: 'coral', topics: ['Internships', 'Frontend', 'React', 'Resume review'], about: 'Frontend engineer intern @ Razorpay. Happy to help you land your first opportunity and build a portfolio that feels like you.', sessions: 18, featured: true, availability: 'Open to requests', cgpa: '8.8 demo' },
  { id: 2, name: 'Rohan Kulkarni', initials: 'RK', year: '4th year', branch: 'ISE', avatar: 'blue', topics: ['Hackathons', 'Product design', 'Startups'], about: 'Two-time hackathon finalist who loves turning a rough idea into a demo people remember.', sessions: 12, availability: 'Limited slots this week', cgpa: '8.5 demo' },
  { id: 3, name: 'Meera Shetty', initials: 'MS', year: '3rd year', branch: 'CSE', avatar: 'lilac', topics: ['Electives', 'Machine learning', 'Research'], about: 'Research assistant exploring applied ML. Let’s map your interests to electives and a project you’ll be proud of.', sessions: 9, availability: 'Open to requests', cgpa: null },
  { id: 4, name: 'Aditya Hegde', initials: 'AH', year: '4th year', branch: 'ECE', avatar: 'mint', topics: ['Internships', 'Interview prep', 'DSA'], about: 'Software intern @ Cisco. I can help with interview practice, DSA plans, and figuring out where to begin.', sessions: 21, availability: 'Open to requests', cgpa: '8.2 demo' },
  { id: 5, name: 'Nisha Pai', initials: 'NP', year: '3rd year', branch: 'ISE', avatar: 'peach', topics: ['UI/UX', 'Portfolio', 'Hackathons'], about: 'Designer and builder. I’m happy to review a project, talk through a design portfolio, or brainstorm your next hack.', sessions: 7, availability: 'Taking a few requests', cgpa: null },
  { id: 6, name: 'Karthik M', initials: 'KM', year: '4th year', branch: 'CSE', avatar: 'slate', topics: ['Open source', 'Git & GitHub', 'Internships'], about: 'Open-source contributor who enjoys making the first PR feel a lot less intimidating.', sessions: 15, availability: 'At capacity this week', cgpa: '8.6 demo' },
];
const topics = ['All topics', 'Internships', 'Hackathons', 'Electives', 'Frontend', 'Machine learning', 'UI/UX'];
const interestOptions = ['Internships', 'Hackathons', 'Electives', 'Frontend', 'React', 'Machine learning', 'UI/UX', 'DSA'];
function App() {
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState('All topics');
  const [requests, setRequests] = useState(() => JSON.parse(localStorage.getItem('mentor-link-requests') || '[]'));
  const [saved, setSaved] = useState(() => JSON.parse(localStorage.getItem('mentor-link-saved') || '[]'));
  const [view, setView] = useState('discover');
  const [demoRole, setDemoRole] = useState('junior');
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState('');
  const [toast, setToast] = useState('');
  const [mobileNav, setMobileNav] = useState(false);
  const [connectSkill, setConnectSkill] = useState('');
  const [connectInterests, setConnectInterests] = useState([]);

  const filtered = useMemo(() => mentors.filter(m => {
    const text = `${m.name} ${m.branch} ${m.topics.join(' ')} ${m.about}`.toLowerCase();
    return (!query || text.includes(query.toLowerCase())) && (topic === 'All topics' || m.topics.includes(topic));
  }), [query, topic]);
  const connectMatches = useMemo(() => mentors
    .filter(m => (!connectInterests.length || connectInterests.some(i => m.topics.includes(i))) && (!connectSkill.trim() || `${m.topics.join(' ')} ${m.about}`.toLowerCase().includes(connectSkill.trim().toLowerCase())))
    .sort((a, b) => {
      const score = m => connectInterests.filter(i => m.topics.includes(i)).length;
      return score(b) - score(a) || Number(Boolean(b.featured)) - Number(Boolean(a.featured));
    }), [connectInterests, connectSkill]);
  const persistRequests = (next) => { setRequests(next); localStorage.setItem('mentor-link-requests', JSON.stringify(next)); };
  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(''), 2600); };
  const toggleSave = (id) => { const next = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id]; setSaved(next); localStorage.setItem('mentor-link-saved', JSON.stringify(next)); };
  const sendRequest = () => {
    if (!selected) return;
    if (requests.some(r => r.mentorId === selected.id)) { setSelected(null); showToast('You already have a request with this mentor.'); return; }
    const requestTopic = connectSkill.trim() || connectInterests.find(i => selected.topics.includes(i)) || selected.topics[0];
    persistRequests([{ mentorId: selected.id, status: 'pending', note: note.trim(), topic: requestTopic, createdAt: Date.now() }, ...requests]);
    setSelected(null); setNote(''); setView('requests'); showToast('Request sent. Your contact stays private for now.');
  };
  const updateRequest = (id, status) => persistRequests(requests.map(r => r.mentorId === id ? { ...r, status } : r));

  return <div className="app-shell">
    <header className="topbar">
      <a className="brand" href="#home" onClick={() => setView('discover')}><span className="brand-mark"><span></span><span></span><span></span><span></span></span><span>mentor<span className="brand-dot">.</span>link</span></a>
      <nav className={mobileNav ? 'nav-links open' : 'nav-links'}>
        <button className={view === 'discover' ? 'nav-item active' : 'nav-item'} onClick={() => { setView('discover'); setMobileNav(false); }}>Find a mentor</button>
        <button className={view === 'connect' ? 'nav-item active' : 'nav-item'} onClick={() => { setView('connect'); setMobileNav(false); }}>Connect</button>
        <button className={view === 'requests' ? 'nav-item active' : 'nav-item'} onClick={() => { setView('requests'); setMobileNav(false); }}>My requests <span className="nav-count">{requests.length}</span></button>
      </nav>
      <div className="top-actions"><span className="privacy-chip"><ShieldCheck size={14}/> Private by design</span><button className="role-switch" onClick={() => { setDemoRole(demoRole === 'junior' ? 'mentor' : 'junior'); setView('requests'); }}>{demoRole === 'junior' ? 'Junior demo' : 'Mentor demo'} <ChevronDown size={13}/></button><button className="mobile-menu" onClick={() => setMobileNav(!mobileNav)} aria-label="Toggle navigation">{mobileNav ? <X/> : <Menu/>}</button></div>
    </header>

    <main id="home" hidden={view === 'connect' || view === 'requests'}>
      <section className="hero">
        <div className="hero-image"></div><div className="hero-shade"></div>
        <div className="hero-content">
          <div className="eyebrow hero-eyebrow"><span className="live-dot"></span> NIE students, growing together</div>
          <h1>Your next step<br/>starts with <em>someone.</em></h1>
          <p>Real advice from someone who’s been there.<br className="desktop-break"/> Find your people, find your path.</p>
          <button className="hero-cta" onClick={() => setView('connect')}>Meet your mentor <ArrowDownRight size={17}/></button>
          <div className="hero-note"><LockKeyhole size={13}/> Your details stay yours. Always.</div>
        </div>
        <div className="hero-stamp"><span>GOOD THINGS</span><strong>GROW<br/>TOGETHER</strong><ArrowUpRight size={15}/></div>
        <div className="marquee-wrap"><div className="marquee-track">{Array.from({length: 4}, (_, i) => <span key={i}>LET’S LEARN &amp; GROW TOGETHER <b>✳</b> ASK BIGGER QUESTIONS <b>✳</b> FIND YOUR PEOPLE <b>✳</b>&nbsp;</span>)}</div></div>
      </section>

      <section className="intro-row" id="how-it-works">
        <div><div className="eyebrow"><span className="eyebrow-line"></span> A little help goes a long way</div><h2>One good conversation<br/>can change your <em>direction.</em></h2></div>
        <p className="intro-copy">The internship question. The elective you’re unsure about. The hackathon idea you haven’t said out loud yet. There’s a senior who remembers being right where you are.</p>
      </section>

      <section className="research-section"><div className="research-heading"><div className="eyebrow"><span className="eyebrow-line"></span>Built from student conversations</div><h2>Make the first ask<br/><em>feel easier.</em></h2></div><div className="research-cards"><article><span className="research-number">01 / KNOW WHEN TO ASK</span><blockquote>“Honestly, the hesitation of bothering them out of the blue without knowing if they are busy, have exams, or are even open to answering doubts.”</blockquote><span className="research-role">1st-year CSE student</span></article><article><span className="research-number">02 / SEE WHAT MATTERS</span><blockquote>“CGPA.”</blockquote><span className="research-role">1st-year CSE student, on senior profiles</span></article><article><span className="research-number">03 / LET SENIORS CHOOSE</span><blockquote>“I'd selectively choose the requests which are aligning with the task I'd be doing to answer and ignore the rest during that time.”</blockquote><span className="research-role">3rd-year senior</span></article></div></section>

      <section className="directory" id="mentor-directory">
        <div className="section-heading"><div><div className="eyebrow"><span className="eyebrow-line"></span> Your campus, your community</div><h2>Meet the <em>mentors.</em></h2></div><div className="mentor-total"><span>{mentors.length.toString().padStart(2, '0')}</span> generous humans</div></div>
        <div className="filter-row"><label className="search-box"><Search size={17}/><input aria-label="Search mentors" placeholder="Try “internships” or “design”" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button onClick={() => setQuery('')} aria-label="Clear search"><X size={15}/></button>}</label><div className="topic-wrap"><label className="sr-only" htmlFor="topic-filter">Filter by topic</label><select id="topic-filter" value={topic} onChange={e => setTopic(e.target.value)}>{topics.map(t => <option key={t}>{t}</option>)}</select><ChevronDown size={15}/></div><span className="result-count">Showing {filtered.length} mentors</span></div>
        {filtered.length ? <div className="mentor-grid">{filtered.map((m, index) => <article className={`mentor-card ${m.featured ? 'featured' : ''}`} key={m.id} style={{'--delay': `${index * 70}ms`}}>
          <div className="card-top"><div className={`mentor-avatar ${m.avatar}`}><span>{m.initials}</span><span className="avatar-orbit"></span></div><button className={`save-btn ${saved.includes(m.id) ? 'saved' : ''}`} onClick={() => toggleSave(m.id)} aria-label={saved.includes(m.id) ? 'Remove saved mentor' : 'Save mentor'}><Bookmark size={16} fill={saved.includes(m.id) ? 'currentColor' : 'none'}/></button></div>
          <div className="mentor-meta"><span>{m.year}</span><span className="meta-dot">·</span><span>{m.branch}</span>{m.featured && <span className="mentor-featured"><Sparkles size={11}/> Community pick</span>}</div>
          <h3>{m.name}</h3><div className="profile-details"><span className={m.availability.includes('capacity') || m.availability.includes('Limited') ? 'availability busy' : 'availability'}><i></i>{m.availability}</span><span className="cgpa-detail">CGPA {m.cgpa ? `${m.cgpa} · shared by mentor` : 'not shared'}</span></div><p className="mentor-about">{m.about}</p>
          <div className="topic-pills">{m.topics.slice(0, 3).map(t => <button key={t} onClick={() => setTopic(t)}>{t}</button>)}</div>
          <div className="card-footer"><span className="session-count"><Users size={14}/>{m.sessions} chats shared</span>{m.availability.includes('capacity') ? <span className="busy-button">Busy this week</span> : <button className="request-btn" onClick={() => { setSelected(m); setNote(''); }}>Request a chat <ArrowRight size={15}/></button>}</div>
        </article>)}</div> : <div className="empty-state"><Search size={22}/><strong>No mentors found just yet.</strong><span>Try another topic or clear your search.</span><button onClick={() => { setQuery(''); setTopic('All topics'); }}>Clear filters</button></div>}
      </section>

      <section className="privacy-band"><div className="privacy-icon"><LockKeyhole size={20}/></div><div><div className="eyebrow">A promise, not a setting</div><h3>Your privacy comes <em>first.</em></h3><p>Your contact details are never public. They’re only shared after a mentor accepts your request.</p></div><div className="privacy-steps"><div><span>01</span><b>Send a request</b><small>Your details stay hidden</small></div><ArrowRight size={15}/><div><span>02</span><b>They say yes</b><small>You both feel good</small></div><ArrowRight size={15}/><div><span>03</span><b>Connect</b><small>Now you can chat</small></div></div></section>

      <footer className="footer"><a className="brand" href="#home"><span className="brand-mark"><span></span><span></span><span></span><span></span></span><span>mentor<span className="brand-dot">.</span>link</span></a><span>Made for the curious at NIE, Mysuru.</span><a href="#how-it-works">Good things grow together <ArrowUpRight size={13}/></a></footer>
    </main>

    {view === 'connect' && <section className="connect-page">
      <button className="back-link" onClick={() => setView('discover')}><ArrowRight className="back-arrow" size={15}/> Back to home</button>
      <div className="connect-hero"><div><div className="eyebrow"><span className="eyebrow-line"></span>Tell us what you’re working toward</div><h1>Find your <em>person.</em></h1><p>Start with what you want to learn. We’ll bring you seniors who have been there.</p></div><div className="connect-illustration"><div className="connect-orbit orbit-one"></div><div className="connect-orbit orbit-two"></div><div className="connect-illustration-center"><Compass size={30}/></div><span className="orbit-tag tag-top">your interests</span><span className="orbit-tag tag-bottom">their experience</span></div></div>
      <div className="connect-controls"><div className="connect-control-heading"><span className="eyebrow">01 / Pick what you’re curious about</span><button className="clear-interests" onClick={() => setConnectInterests([])} disabled={!connectInterests.length}>Clear choices</button></div><div className="interest-chips">{interestOptions.map(i => <button key={i} className={connectInterests.includes(i) ? 'interest-chip selected' : 'interest-chip'} onClick={() => setConnectInterests(current => current.includes(i) ? current.filter(x => x !== i) : [...current, i])}><span>{connectInterests.includes(i) ? '✓' : '+'}</span>{i}</button>)}</div>
        <div className="skill-search-label"><div><span className="eyebrow">02 / Or search for a skill</span><small>Search by what you want help with, not by a person’s name.</small></div><label className="skill-search"><Search size={17}/><input aria-label="Search mentor skills" placeholder="Try React, DSA, resume review…" value={connectSkill} onChange={e => setConnectSkill(e.target.value)}/>{connectSkill && <button onClick={() => setConnectSkill('')} aria-label="Clear skill search"><X size={15}/></button>}</label></div>
      </div>
      <div className="connect-results-head"><div><div className="eyebrow"><span className="eyebrow-line"></span>Good people, right where you need them</div><h2>{connectInterests.length || connectSkill ? 'Your mentor matches.' : 'A few people to get you started.'}</h2></div><span>{connectMatches.length} {connectMatches.length === 1 ? 'mentor' : 'mentors'}</span></div>
      {connectMatches.length ? <div className="mentor-grid">{connectMatches.map((m, index) => <article className={`mentor-card ${m.featured ? 'featured' : ''}`} key={m.id} style={{'--delay': `${index * 70}ms`}}>
        <div className="card-top"><div className={`mentor-avatar ${m.avatar}`}><span>{m.initials}</span><span className="avatar-orbit"></span></div><button className={`save-btn ${saved.includes(m.id) ? 'saved' : ''}`} onClick={() => toggleSave(m.id)} aria-label={saved.includes(m.id) ? 'Remove saved mentor' : 'Save mentor'}><Bookmark size={16} fill={saved.includes(m.id) ? 'currentColor' : 'none'}/></button></div>
        <div className="mentor-meta"><span>{m.year}</span><span className="meta-dot">·</span><span>{m.branch}</span><span className="mentor-featured"><Sparkles size={11}/> {connectInterests.length ? `${connectInterests.filter(i => m.topics.includes(i)).length} shared interests` : 'Open to mentor'}</span></div>
        <h3>{m.name}</h3><div className="profile-details"><span className={m.availability.includes('capacity') || m.availability.includes('Limited') ? 'availability busy' : 'availability'}><i></i>{m.availability}</span><span className="cgpa-detail">CGPA {m.cgpa ? `${m.cgpa} · shared by mentor` : 'not shared'}</span></div><p className="mentor-about">{m.about}</p><div className="topic-pills">{m.topics.slice(0, 4).map(t => <button key={t} onClick={() => setConnectSkill(t)}>{t}</button>)}</div>
        <div className="card-footer"><span className="session-count"><Users size={14}/>{m.sessions} chats shared</span>{m.availability.includes('capacity') ? <span className="busy-button">Busy this week</span> : <button className="request-btn" onClick={() => { setSelected(m); setNote(''); }}>Request a chat <ArrowRight size={15}/></button>}</div>
      </article>)}</div> : <div className="empty-state"><Search size={22}/><strong>No mentors match that skill yet.</strong><span>Try a related skill or clear some interests.</span><button onClick={() => {setConnectSkill('');setConnectInterests([])}}>Reset search</button></div>}
      <div className="connect-privacy"><LockKeyhole size={16}/> Your contact details stay private until a mentor accepts your request.</div>
    </section>}

    {view === 'requests' && <div className="requests-panel"><div className="requests-head"><div><button className="back-link" onClick={() => setView('discover')}><ArrowRight className="back-arrow" size={15}/> Back to mentors</button><div className="eyebrow"><span className="eyebrow-line"></span> {demoRole === 'junior' ? 'Your next conversation' : 'Your mentoring inbox'}</div><h2>{demoRole === 'junior' ? <>My <em>requests.</em></> : <>Incoming <em>requests.</em></>}</h2><p>{demoRole === 'junior' ? 'Your contact details stay private until a mentor accepts.' : 'Review a request. Contact details stay hidden until you accept.'}</p></div><div className="request-private"><LockKeyhole size={17}/><span>Contact details hidden<br/><small>until a mentor accepts</small></span></div></div>
      {requests.length === 0 ? <div className="empty-state request-empty"><MessageCircle size={24}/><strong>{demoRole === 'junior' ? 'Your next conversation is out there.' : 'No requests waiting just yet.'}</strong><span>{demoRole === 'junior' ? 'Explore mentors and send your first request.' : 'New mentee requests will show up here.'}</span><button onClick={() => {setDemoRole('junior');setView('connect')}}>{demoRole === 'junior' ? <>Find a mentor <ArrowRight size={15}/></> : 'Back to discovery'}</button></div> : <div className="request-list">{requests.map(r => {const m = mentors.find(x => x.id === r.mentorId); if (!m) return null; return <article className="request-card" key={r.mentorId}><div className={`mentor-avatar small ${m.avatar}`}><span>{m.initials}</span></div><div className="request-info"><strong>{demoRole === 'junior' ? m.name : 'NIE junior'}</strong><span>{demoRole === 'junior' ? `${m.year} · ${m.branch} · ${r.topic || m.topics[0]}` : `Request topic: ${r.topic || m.topics[0]} · review whether it fits what you can help with`}</span>{r.note && <p>“{r.note}”</p>}</div><div className={`status-pill ${r.status}`}><span></span>{r.status === 'accepted' ? 'Accepted' : r.status === 'declined' ? 'Not available' : 'Awaiting reply'}</div>{demoRole === 'mentor' && r.status === 'pending' ? <div className="request-actions"><button className="demo-accept" onClick={() => updateRequest(m.id, 'accepted')}><Check size={14}/> Accept</button><button className="demo-decline" onClick={() => updateRequest(m.id, 'declined')}>Decline</button></div> : demoRole === 'junior' && r.status === 'accepted' ? <div className="unlocked"><ShieldCheck size={15}/> You’re connected!<small>Senior demo: {m.name.toLowerCase().replace(' ', '.')}@nie.edu</small></div> : demoRole === 'mentor' && r.status === 'accepted' ? <div className="unlocked"><ShieldCheck size={15}/> You’re connected!<small>Junior demo: junior.demo@nie.edu</small></div> : null}</article>;})}</div>}
    </div>}

    {selected && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setSelected(null); }}><section className="request-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button className="modal-close" onClick={() => setSelected(null)} aria-label="Close"><X size={18}/></button><div className={`mentor-avatar modal-avatar ${selected.avatar}`}><span>{selected.initials}</span></div><div className="eyebrow"><span className="eyebrow-line"></span> Start with a hello</div><h2 id="modal-title">Ask <em>{selected.name.split(' ')[0]}.</em></h2><p className="modal-intro">Tell them what’s on your mind. A little context makes it easier to say yes.</p><label className="note-label" htmlFor="request-note">What would you like to talk about? <span>optional</span></label><textarea id="request-note" maxLength={240} placeholder="I’d love some advice on…" value={note} onChange={e => setNote(e.target.value)} /><div className="char-count">{note.length}/240</div><div className="modal-privacy"><LockKeyhole size={16}/><span>Your phone and email are never shown. Contact is shared only if {selected.name.split(' ')[0]} accepts.</span></div><button className="send-request" onClick={sendRequest}>Send a request <ArrowRight size={16}/></button><button className="maybe-later" onClick={() => setSelected(null)}>Maybe later</button></section></div>}
    {toast && <div className="toast"><Check size={16}/>{toast}</div>}
    <button className="help-fab" title="Privacy promise"><CircleHelp size={19}/></button>
  </div>;
}

export default App;
