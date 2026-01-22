import { toast, Toaster } from 'react-hot-toast'


import { useState, useEffect } from 'react'
import { PriorityChart, CategoryChart } from './components/Charts'
import MeetingAgentChat from './MeetingAgentChat'
import MeetingDashboard from './components/MeetingDashboard'
import ComposeModal from './components/ComposeModal'
import Tutorial from './components/Tutorial'

function App() {
  const [view, setView] = useState('landing') // landing, dashboard
  const [tab, setTab] = useState('overview') // overview, inbox
  const [category, setCategory] = useState('All') // Filter state
  const [user, setUser] = useState(null)
  const [emails, setEmails] = useState([])
  const [syncing, setSyncing] = useState(false)
  const [expandedEmailId, setExpandedEmailId] = useState(null)

  // Compose Modal State
  const [isComposeOpen, setIsComposeOpen] = useState(false)
  const [composeData, setComposeData] = useState({})

  // Chat Widget State
  const [showChat, setShowChat] = useState(false)

  const openCompose = (data = {}) => {
    setComposeData(data)
    setIsComposeOpen(true)
  }

  // Check Session & Extract Token
  useEffect(() => {
    // 1. Check for Token in URL (Login Redirect)
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');

    if (urlToken) {
      localStorage.setItem('token', urlToken);
      // Clean URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    const token = localStorage.getItem('token');

    if (token) {
      fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
        .then(res => {
          if (res.ok) return res.json()
          throw new Error('Not authenticated')
        })
        .then(data => {
          setUser(data)
          setView('dashboard')
          fetchEmails() // Fetch on load
        })
        .catch(() => {
          localStorage.removeItem('token');
          setUser(null);
        })
    }

    // Request Notification Permission (Optional now with toasts, but keeping for completeness if we want system fallback)
    if (Notification.permission !== "granted") {
      Notification.requestPermission();
    }
  }, [])

  // Poll for upcoming meetings for notifications
  useEffect(() => {
    const checkMeetings = async () => {
      const token = localStorage.getItem('token');
      if (!token) return;

      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/meetings`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const meetings = await res.json();
          const now = new Date();

          meetings.forEach(m => {
            const start = new Date(m.start_time);
            const diffMs = start - now;
            const diffMins = diffMs / (1000 * 60);

            // Notification logic: 1 day (around 1440 mins), 2 hours (120 mins), 0 mins
            // We use a small window (e.g., 0-1 min) to avoid duplicate alerts.

            // 24 hours before (1439-1441 mins)
            if (diffMins >= 1439 && diffMins <= 1441) {
              toast(`Upcoming Meeting Tomorrow: ${m.title} at ${start.toLocaleTimeString()}`, { icon: '📅' });
            }
            // 2 hours before (119-121 mins)
            if (diffMins >= 119 && diffMins <= 121) {
              toast(`Meeting in 2 Hours: ${m.title}`, { icon: '⏳' });
            }
            // Starting now (0-2 mins)
            if (diffMins >= 0 && diffMins <= 2) {
              toast(`Meeting Starting Now: ${m.title}`, { icon: '🚀', duration: 10000 });
            }
          });
        }
      } catch (e) { console.error(e) }
    };

    // Check every minute
    const interval = setInterval(checkMeetings, 60000);
    checkMeetings(); // Initial check
    return () => clearInterval(interval);
  }, []);

  const fetchEmails = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/emails`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setEmails(data)
      }
    } catch (e) { console.error(e) }
  }

  const handleSync = async () => {
    setSyncing(true)
    const token = localStorage.getItem('token');

    if (!token) {
      toast.error("Please log in first.");
      setSyncing(false);
      return;
    }

    const toastId = toast.loading('Syncing emails...');

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/sync`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (res.status === 401) {
        toast.error("Session expired. Please Log In again.", { id: toastId });
        localStorage.removeItem('token');
        setUser(null);
        return
      }

      const data = await res.json()
      if (data.count && data.count > 0) {
        toast.success(`${data.count} new emails analyzed.`, { id: toastId });
        fetchEmails()
      } else {
        toast.success("No new emails found.", { id: toastId });
      }
    } catch (e) {
      console.error(e)
      toast.error("Sync failed. Check console.", { id: toastId });
    } finally {
      setSyncing(false)
    }
  }

  const handleReset = async () => {
    if (!localStorage.getItem('token')) return;
    if (!window.confirm("⚠️ DANGER: This will delete all emails in the local database. Proceed?")) return;

    const toastId = toast.loading('Reseting Database...');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/admin/reset-emails`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        toast.success("Database Reset & Schema Fixed!", { id: toastId });
        setEmails([]);
      } else {
        const err = await res.json();
        toast.error(`Reset Failed: ${err.detail}`, { id: toastId });
      }
    } catch (e) {
      toast.error("Network Error on Reset", { id: toastId });
    }
  }

  const handleLogin = () => {
    // Redirect to backend login, which will redirect back with ?token=...
    window.location.href = `${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/auth/login`
  }

  const handleLogout = async () => {
    // Just clear local state, backend session is stateless JWT (mostly)
    localStorage.removeItem('token');
    setUser(null)
    setView('landing')
  }

  return (
    <div className="min-h-screen bg-dark text-white selection:bg-primary selection:text-white font-sans">
      <Toaster position="bottom-right" toastOptions={{
        style: {
          background: '#333',
          color: '#fff',
        },
      }} />
      {/* Navbar */}
      <nav className="p-6 flex justify-between items-center max-w-7xl mx-auto border-b border-white/5">
        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
          AI Personal Assistant
        </h1>
        <div className="flex items-center gap-6">
          <ul className="hidden md:flex space-x-6 text-sm font-medium text-gray-300">
            {view === 'landing' && (
              <>
                <li><a href="#about" className="hover:text-primary transition-colors">About</a></li>
                <li><a href="#contact" className="hover:text-primary transition-colors">Contact</a></li>
              </>
            )}
            <li><button onClick={() => setView('tutorial')} className="hover:text-primary transition-colors">Tutorial</button></li>
          </ul>

          {user ? (
            <div className="flex items-center space-x-4">
              <div className="bg-white/5 py-1 px-3 rounded-full border border-white/10 hidden md:flex items-center space-x-2 cursor-pointer hover:bg-white/10 transition-colors" onClick={() => setView('dashboard')}>
                <span className="text-sm font-bold text-gray-400">Dashboard</span>
              </div>

              <div className="flex items-center space-x-2 bg-white/5 px-3 py-1 rounded-full border border-white/10">
                <img src={user.picture} alt={user.name} className="w-6 h-6 rounded-full" />
                <span className="text-sm font-medium">{user.name}</span>
              </div>
              <button onClick={handleLogout} className="text-sm text-gray-400 hover:text-white">
                Log Out
              </button>
            </div>
          ) : (
            <button onClick={handleLogin} className="btn-primary text-sm px-4 py-2">
              Login
            </button>
          )}
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {view === 'tutorial' ? (
          <Tutorial onComplete={() => setView(user ? 'dashboard' : 'landing')} />
        ) : view === 'landing' ? (
          <div className="flex flex-col min-h-screen relative">
            {/* Hero Section with Background */}
            <div className="relative flex flex-col items-center justify-center text-center space-y-8 min-h-[80vh] w-full">
              <div
                className="absolute inset-0 bg-cover bg-center z-0"
                style={{ backgroundImage: `url('/landing-bg.png')` }}
              >
                <div className="absolute inset-0 bg-gradient-to-b from-dark/90 via-dark/70 to-dark z-10"></div>
              </div>

              <div className="relative z-20 max-w-4xl px-4 animate-fade-in-up">
                <h2 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 text-white drop-shadow-lg">
                  Your Inbox, <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-cyan-400">Mastered</span>.
                </h2>
                <p className="text-xl text-gray-200 max-w-2xl mx-auto mb-8 drop-shadow-md font-medium">
                  Stop drowning in emails. Let our AI analyze, prioritize, and draft responses for you in real-time.
                </p>
                <button
                  onClick={handleLogin}
                  className="btn-primary text-lg px-8 py-4 shadow-lg shadow-primary/30 hover:shadow-primary/50 transform hover:-translate-y-1 transition-all rounded-full"
                >
                  Get Started with Google
                </button>
              </div>
            </div>

            {/* About Us Section */}
            <section id="about" className="py-20 px-6 bg-dark">
              <div className="max-w-6xl mx-auto">
                <h3 className="text-3xl font-bold text-center mb-12 bg-clip-text text-transparent bg-gradient-to-r from-teal-400 to-blue-500">
                  Our Hybrid AI Architecture
                </h3>

                <div className="grid md:grid-cols-3 gap-8 text-center relative z-10">
                  {/* Layer 1 */}
                  <div className="p-8 bg-white/5 rounded-2xl border border-white/10 hover:border-primary/50 transition-colors group">
                    <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">🛡️</div>
                    <h4 className="text-xl font-bold mb-3 text-red-400">Layer 1: The Gatekeeper</h4>
                    <p className="text-gray-400 text-sm mb-4">Local Spam Filter (Naive Bayes)</p>
                    <p className="text-gray-300">
                      Instantly blocks 99% of spam locally in <span className="font-bold text-white">5ms</span>. Zero API cost.
                    </p>
                  </div>

                  {/* Layer 2 */}
                  <div className="p-8 bg-white/5 rounded-2xl border border-white/10 hover:border-primary/50 transition-colors group">
                    <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">🏷️</div>
                    <h4 className="text-xl font-bold mb-3 text-yellow-400">Layer 2: The Tagger</h4>
                    <p className="text-gray-400 text-sm mb-4">Intent Classifier (SVM)</p>
                    <p className="text-gray-300">
                      Automatically detects 10+ categories like <span className="text-white">Finance, Urgent, Work</span> using a custom-trained multi-label model.
                    </p>
                  </div>

                  {/* Layer 3 */}
                  <div className="p-8 bg-white/5 rounded-2xl border border-white/10 hover:border-primary/50 transition-colors group">
                    <div className="text-4xl mb-4 group-hover:scale-110 transition-transform">🧠</div>
                    <h4 className="text-xl font-bold mb-3 text-purple-400">Layer 3: The Analyst</h4>
                    <p className="text-gray-400 text-sm mb-4">Google Gemini 2.5 (LLM)</p>
                    <p className="text-gray-300">
                      Deep reasoning. Drafts replies, summarizes deadlines, and analyzes sentiment with human-like intelligence.
                    </p>
                  </div>
                </div>

                {/* Connecting Line (Visual Flair) */}
                <div className="hidden md:block absolute top-1/2 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent -z-10 transform -translate-y-12"></div>
              </div>
            </section>

            {/* Contact Us Section */}
            <section id="contact" className="py-20 px-6 bg-gradient-to-b from-dark to-black border-t border-white/5">
              <div className="max-w-4xl mx-auto text-center">
                <h3 className="text-3xl font-bold mb-8 text-white">Contact Us</h3>
                <p className="text-gray-400 mb-8">Have questions or feedback? We'd love to hear from you.</p>
                <div className="flex flex-col md:flex-row justify-center gap-6">
                  <a href="mailto:support@aiassistant.com" className="px-6 py-3 bg-white/10 rounded-lg hover:bg-white/20 transition-colors flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                    support@aiassistant.com
                  </a>
                  <a href="#" className="px-6 py-3 bg-white/10 rounded-lg hover:bg-white/20 transition-colors flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" /></svg>
                    Live Chat
                  </a>
                </div>
              </div>
            </section>
          </div>
        ) : (
          <div>
            {/* Dashboard Controls */}
            <div className="flex justify-between items-center mb-8">
              <div className="flex space-x-1 bg-white/5 p-1 rounded-lg">
                {['overview', 'inbox', 'calendar'].map(t => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-4 py-2 rounded-md text-sm font-bold capitalize transition-all ${tab === t ? 'bg-primary text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => openCompose()}
                  className="btn-primary flex items-center space-x-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 border-none"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                  <span>Compose</span>
                </button>
                <button
                  onClick={handleSync}
                  disabled={syncing}
                  className={`btn-primary flex items-center space-x-2 ${syncing ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {syncing ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  )}
                  <span>{syncing ? 'Syncing...' : 'Sync Gmail'}</span>
                </button>

              </div>
            </div>

            {/* OVERVIEW TAB */}
            {tab === 'overview' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in">
                <div className="glass-card">
                  <h3 className="text-lg font-bold mb-4 text-gray-300">Priority Distribution</h3>
                  {emails.length > 0 ? <PriorityChart data={emails} /> : <p className="text-center text-gray-500 py-10">No data available. Sync your email!</p>}
                </div>
                <div className="glass-card">
                  <h3 className="text-lg font-bold mb-4 text-gray-300">Intent Categories</h3>
                  {emails.length > 0 ? <CategoryChart data={emails} /> : <p className="text-center text-gray-500 py-10">No data available.</p>}
                </div>

                {/* Summary Stats */}
                <div className="col-span-1 md:col-span-2 grid grid-cols-3 gap-4">
                  <div className="glass-card flex flex-col items-center justify-center p-6">
                    <span className="text-3xl font-bold text-white">{emails.length}</span>
                    <span className="text-sm text-gray-500 uppercase tracking-wider">Total Emails</span>
                  </div>
                  <div className="glass-card flex flex-col items-center justify-center p-6">
                    <span className="text-3xl font-bold text-red-400">{emails.filter(e => e.priority === 'P1').length}</span>
                    <span className="text-sm text-gray-500 uppercase tracking-wider">Urgent (P1)</span>
                  </div>
                  <div className="glass-card flex flex-col items-center justify-center p-6">
                    <span className="text-3xl font-bold text-green-400">{emails.filter(e => e.requires_action).length}</span>
                    <span className="text-sm text-gray-500 uppercase tracking-wider">Action Items</span>
                  </div>
                </div>
              </div>
            )}

            {/* INBOX TAB */}
            {tab === 'inbox' && (
              <div className="space-y-4 animate-fade-in">
                {/* Filters */}
                <div className="flex space-x-2 pb-2 overflow-x-auto no-scrollbar">
                  {['All', 'Urgent', 'Finance', 'Meeting', 'Work', 'Personal', 'Newsletter', 'Receipts', 'Notification', 'Phishing', 'Spam'].map(cat => {
                    // Calculate Count
                    const count = cat === 'All'
                      ? emails.length
                      : emails.filter(e => (e.intent && e.intent.includes(cat)) || (cat === 'Urgent' && e.priority === 'P1')).length;

                    return (
                      <button
                        key={cat}
                        onClick={() => setCategory(cat)}
                        className={`px-4 py-1.5 rounded-full text-xs font-bold border whitespace-nowrap transition-all ${category === cat ? 'bg-white text-dark border-white shadow-md transform scale-105' : 'border-gray-600 text-gray-400 hover:border-gray-400 hover:text-white'}`}
                      >
                        {cat} <span className={`ml-1 opacity-60 ${count > 0 ? 'text-primary' : ''}`}>({count})</span>
                      </button>
                    )
                  })}
                </div>

                {emails
                  .filter(email => {
                    if (category === 'All') return true;

                    const intent = email.intent ? email.intent.toLowerCase() : '';

                    // SMART MAPPING: Map Frontend Tabs to AI Intents
                    if (category === 'Urgent') return email.priority === 'P1' || intent.includes('urgent');

                    if (category === 'Personal') {
                      // "Personal" tab catches: Social, Party, Family, Personal, Invitation
                      return intent.includes('personal') || intent.includes('social') || intent.includes('party') || intent.includes('invitation') || intent.includes('family');
                    }

                    if (category === 'Finance') {
                      // "Finance" tab catches: Invoice, Bank, Statement, Receipt, Loan
                      return intent.includes('finance') || intent.includes('invoice') || intent.includes('bank') || intent.includes('statement') || intent.includes('receipt') || intent.includes('loan');
                    }

                    if (category === 'Work') {
                      return intent.includes('work') || intent.includes('job') || intent.includes('meeting') || intent.includes('schedule');
                    }

                    // Default: Strict Match (Newsletter -> Newsletter)
                    return email.intent && email.intent.includes(category);
                  })
                  .map(email => (
                    <div
                      key={email.id}
                      onClick={() => setExpandedEmailId(email.id === expandedEmailId ? null : email.id)}
                      className={`relative group p-6 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-primary/50 transition-all duration-300 shadow-lg hover:shadow-primary/20 backdrop-blur-md overflow-hidden cursor-pointer ${email.id === expandedEmailId ? 'ring-2 ring-primary' : ''}`}
                    >
                      {/* Decorative Gradient Line */}
                      <div className={`absolute left-0 top-0 bottom-0 w-1 ${email.priority === 'P1' ? 'bg-gradient-to-b from-red-500 to-orange-500' :
                        email.requires_action ? 'bg-gradient-to-b from-green-400 to-emerald-500' :
                          'bg-gradient-to-b from-blue-500 to-purple-500'
                        }`}></div>

                      <div className="pl-4">
                        {/* Header: Sender & Time */}
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-xs font-bold text-white ring-1 ring-white/20">
                              {email.sender.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <h4 className="font-bold text-white text-sm">{email.sender}</h4>
                              <span className="text-xs text-gray-400">{new Date(email.received_time).toLocaleDateString()} • {new Date(email.received_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {email.priority === 'P1' && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/20 uppercase tracking-wider">Urgent</span>}
                            {email.requires_action && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500/20 text-green-400 border border-green-500/20 uppercase tracking-wider">Action</span>}
                          </div>
                        </div>

                        {/* Subject */}
                        <h3 className="text-lg font-bold text-gray-100 mb-3 group-hover:text-primary transition-colors leading-tight">
                          {email.subject}
                        </h3>

                        {/* Expanded View: Full Body */}
                        {email.id === expandedEmailId && (
                          <div className="mt-4 mb-6 p-4 bg-black/40 rounded-lg text-sm text-gray-300 whitespace-pre-wrap border border-white/5 animate-fade-in font-sans leading-relaxed">
                            {email.body || email.snippet}
                          </div>
                        )}

                        {/* AI Insight Box */}
                        <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-white/5 rounded-lg p-3 mb-4 backdrop-blur-sm">
                          <div className="flex items-start gap-2">
                            <span className="text-lg">✨</span>
                            <div>
                              <p className="text-sm font-medium text-blue-200">
                                {email.summary || email.snippet.substring(0, 100) + "..."}
                              </p>
                              {/* Tags */}
                              <div className="flex flex-wrap gap-2 mt-2">
                                <span className="text-[10px] uppercase tracking-wide text-gray-400 bg-white/5 px-2 py-1 rounded border border-white/5">{email.intent}</span>
                                {email.sentiment && (
                                  <span className={`text-[10px] px-2 py-1 rounded border border-white/5 uppercase tracking-wide font-bold ${email.sentiment === 'Positive' ? 'text-green-400 bg-green-900/20' :
                                    email.sentiment === 'Negative' ? 'text-red-400 bg-red-900/20' : 'text-gray-400 bg-gray-800/40'
                                    }`}>
                                    {email.sentiment}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Actions Row */}
                        <div className="mt-4 flex flex-wrap gap-3">

                          {/* Standard Reply */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openCompose({
                                to: email.sender,
                                subject: `Re: ${email.subject}`,
                                body: ''
                              });
                            }}
                            className="btn-secondary text-xs bg-white/5 hover:bg-white/10 text-white px-4 py-2 rounded-lg transition-all flex items-center gap-2 border border-white/10"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                            Reply
                          </button>


                          {/* AI Suggested Reply Button - Only show if AI actually generated one */}
                          {email.suggested_reply && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                openCompose({
                                  to: email.sender,
                                  subject: `Re: ${email.subject}`,
                                  body: email.suggested_reply
                                });
                              }}
                              className="btn-primary text-xs px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-400 hover:to-purple-400 border-none flex items-center gap-2 rounded-lg shadow-lg shadow-purple-500/20"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                              AI Suggested Reply
                            </button>
                          )}

                          {/* Show Preview Box Only if it exists AND we are expanded */}
                          {email.suggested_reply && email.id === expandedEmailId && (
                            <div className="w-full mt-2 p-3 bg-gradient-to-br from-indigo-900/20 to-purple-900/20 rounded-lg border border-indigo-500/20 text-xs text-gray-300 italic">
                              <span className="font-bold text-indigo-300 not-italic block mb-1">Preview:</span>
                              "{email.suggested_reply}"
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                {emails.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-500 opacity-50">
                    <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>
                    <p className="text-lg">Inbox Zero</p>
                  </div>
                )}
              </div>
            )}


            {/* CALENDAR TAB */}
            {tab === 'calendar' && (
              <div className="animate-fade-in">
                <MeetingDashboard />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Floating Chat Widget */}
      {view === 'dashboard' && (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
          {/* Chat Window Popover */}
          {showChat && (
            <div className="mb-4 w-[400px] h-[600px] shadow-2xl rounded-2xl overflow-hidden animate-scale-in origin-bottom-right">
              <MeetingAgentChat isWidget={true} onClose={() => setShowChat(false)} />
            </div>
          )}

          {/* Floating Action Button */}
          <button
            onClick={() => setShowChat(!showChat)}
            className={`p-4 rounded-full shadow-lg shadow-primary/30 transition-all transform hover:scale-105 ${showChat ? 'bg-gray-700 text-white rotate-90' : 'btn-primary'}`}
          >
            {showChat ? (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            ) : (
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
            )}
          </button>
        </div>
      )}


      <ComposeModal
        isOpen={isComposeOpen}
        onClose={() => setIsComposeOpen(false)}
        initialData={composeData}
      />
    </div>
  )
}

export default App
