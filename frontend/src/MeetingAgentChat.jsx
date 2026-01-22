import React, { useState, useEffect } from 'react';

function MeetingAgentChat({ isWidget, onClose }) {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        const fetchHistory = async () => {
            const token = localStorage.getItem('token');
            if (!token) return;
            try {
                const res = await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/chat/history`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const history = await res.json();
                    // Convert DB history to UI messages
                    const uiMessages = history.map(h => ({
                        sender: h.sender,
                        text: h.text
                    }));
                    setMessages(uiMessages);
                }
            } catch (e) {
                console.error("Failed to load history", e);
            }
        };
        fetchHistory();
    }, []);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const newMessages = [...messages, { sender: 'user', text: input }];
        setMessages(newMessages);
        setInput('');

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/meeting-agent/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    message: input,
                    conversation_history: messages
                }),
            });
            const data = await response.json();
            setMessages([...newMessages, { sender: 'agent', text: data.response }]);
        } catch (error) {
            console.error("Error:", error);
            setMessages([...newMessages, { sender: 'system', text: 'Error connecting to agent.' }]);
        }
    };

    return (
        <div className={`flex flex-col ${isWidget ? 'h-full w-full' : 'h-[600px] max-w-2xl mx-auto mt-4'} glass-card overflow-hidden bg-gray-900/95 backdrop-blur-xl`}>
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-white/5">
                <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold shadow-lg shadow-blue-500/20">AI</div>
                    <h2 className="text-lg font-bold text-white">AI Assistant</h2>
                </div>
                <div className="flex items-center space-x-1">
                    <button
                        onClick={async () => {
                            if (window.confirm("Start a new chat? This will clear current history.")) {
                                const token = localStorage.getItem('token');
                                await fetch(`${import.meta.env.VITE_API_URL || 'https://aiagent-cygyd5eaejbbegcg.japanwest-01.azurewebsites.net'}/api/chat/history`, {
                                    method: 'DELETE',
                                    headers: { 'Authorization': `Bearer ${token}` }
                                });
                                setMessages([]);
                            }
                        }}
                        className="text-white/50 hover:text-white hover:bg-white/10 p-2 rounded-lg transition-colors"
                        title="New Chat"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    </button>
                    {isWidget && (
                        <button
                            onClick={onClose}
                            className="text-white/50 hover:text-white hover:bg-white/10 p-2 rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                    )}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 mt-20">
                        <p>I have read your recent emails. Ask me anything!</p>
                        <p className="text-xs mt-2">Try: "What was the last email from Google?" or "Summarize today's updates"</p>
                    </div>
                )}
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div
                            className={`max-w-[80%] p-3 rounded-2xl text-sm ${msg.sender === 'user'
                                ? 'bg-primary text-white rounded-br-none shadow-lg shadow-primary/20'
                                : 'bg-white/10 text-gray-200 border border-white/10 rounded-bl-none backdrop-blur-md'
                                }`}
                        >
                            {msg.text}
                        </div>
                    </div>
                ))}
            </div>

            <div className="p-4 border-t border-white/10 bg-white/5">
                <div className="flex gap-2">
                    <input
                        className="flex-1 bg-dark/50 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your request here..."
                        onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                    />
                    <button
                        onClick={sendMessage}
                        className="btn-primary px-6 rounded-xl flex items-center justify-center"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}

export default MeetingAgentChat;
