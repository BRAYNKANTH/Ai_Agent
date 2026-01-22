import { useState, useEffect } from 'react';

const ComposeModal = ({ isOpen, onClose, initialData = {} }) => {
    const [to, setTo] = useState('');
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [sending, setSending] = useState(false);

    const [rewriting, setRewriting] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setTo(initialData.to || '');
            setSubject(initialData.subject || '');
            setBody(initialData.body || '');
        }
    }, [isOpen, initialData]);

    const handleRewrite = async (style) => {
        if (!body.trim()) return;
        setRewriting(true);
        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/agent/rewrite`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: body, style })
            });
            if (res.ok) {
                const data = await res.json();
                setBody(data.result);
            } else {
                alert("Rewrite failed.");
            }
        } catch (e) {
            console.error(e);
            alert("Error rewriting.");
        } finally {
            setRewriting(false);
        }
    };

    const handleSend = async () => {
        setSending(true);
        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/send-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ to, subject, body })
            });

            if (res.ok) {
                alert("Email sent successfully!");
                onClose();
                setTo('');
                setSubject('');
                setBody('');
            } else {
                const err = await res.json();
                alert("Failed to send: " + err.detail);
            }
        } catch (e) {
            console.error(e);
            alert("Error sending email.");
        } finally {
            setSending(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden animate-scale-in">
                {/* Header */}
                <div className="bg-white/5 p-4 border-b border-white/5 flex justify-between items-center">
                    <h3 className="text-lg font-bold text-white">Compose Email</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    <div>
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">To</label>
                        <input
                            type="email"
                            value={to}
                            onChange={(e) => setTo(e.target.value)}
                            className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary transition-colors"
                            placeholder="recipient@example.com"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Subject</label>
                        <input
                            type="text"
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                            className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary transition-colors"
                            placeholder="Meeting Update"
                        />
                    </div>
                    <div>
                        <div className="flex justify-between items-center mb-2">
                            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider">Message</label>

                            {/* Magic Toolbar */}
                            <div className="flex space-x-1">
                                {[
                                    { label: 'Formal', icon: '👔', style: 'formal' },
                                    { label: 'Casual', icon: '😌', style: 'casual' },
                                    { label: 'Shorten', icon: '✂️', style: 'shorten' },
                                    { label: 'Fix Grammar', icon: '📝', style: 'fix_grammar' },
                                ].map(btn => (
                                    <button
                                        key={btn.style}
                                        onClick={() => handleRewrite(btn.style)}
                                        disabled={rewriting || !body.trim()}
                                        className="text-[10px] bg-white/5 hover:bg-white/10 text-gray-300 px-2 py-1 rounded border border-white/10 transition-colors disabled:opacity-50"
                                        title={`Make it ${btn.label}`}
                                    >
                                        {rewriting ? '...' : `${btn.icon} ${btn.label}`}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <textarea
                            value={body}
                            onChange={(e) => setBody(e.target.value)}
                            rows={8}
                            className={`w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary transition-colors font-mono text-sm ${rewriting ? 'animate-pulse' : ''}`}
                            placeholder="Write your message here..."
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="bg-white/5 p-4 border-t border-white/5 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg text-sm font-bold text-gray-400 hover:bg-white/5 transition-colors"
                    >
                        Discard
                    </button>
                    <button
                        onClick={handleSend}
                        disabled={sending}
                        className={`btn-primary px-6 py-2 rounded-lg text-sm font-bold flex items-center gap-2 ${sending ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {sending ? 'Sending...' : (
                            <>
                                <span>Send</span>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ComposeModal;
