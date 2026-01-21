import React, { useEffect, useState } from 'react';

const MeetingDashboard = () => {
    const [meetings, setMeetings] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchMeetings();
    }, []);

    const fetchMeetings = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/meetings');
            if (response.ok) {
                const data = await response.json();
                setMeetings(data);
            }
        } catch (error) {
            console.error("Failed to fetch meetings", error);
        } finally {
            setLoading(false);
        }
    };

    const deleteMeeting = async (id) => {
        if (!confirm("Are you sure you want to cancel this meeting?")) return;
        try {
            const res = await fetch(`http://localhost:8000/api/meetings/${id}`, { method: 'DELETE' });
            if (res.ok) {
                fetchMeetings(); // Reload
            } else {
                alert("Failed to delete meeting.");
            }
        } catch (e) {
            console.error(e);
        }
    };

    const now = new Date();
    const upcoming = meetings.filter(m => new Date(m.end_time) >= now);
    const past = meetings.filter(m => new Date(m.end_time) < now);

    const renderMeetingGroup = (list, title, isPast = false) => {
        if (list.length === 0) return null;

        const groupMeetingsByDate = () => {
            const groups = {};
            list.forEach(meeting => {
                const date = new Date(meeting.start_time).toLocaleDateString('en-US', {
                    weekday: 'long', month: 'long', day: 'numeric'
                });
                if (!groups[date]) groups[date] = [];
                groups[date].push(meeting);
            });
            return groups;
        };

        const grouped = groupMeetingsByDate();
        // Sort dates: Ascending for upcoming, Descending for past
        const sortedDates = Object.keys(grouped).sort((a, b) => {
            return isPast ? new Date(b) - new Date(a) : new Date(a) - new Date(b);
        });

        return (
            <div className={`space-y-6 ${isPast ? 'opacity-60 grayscale' : ''}`}>
                <h2 className={`text-2xl font-bold ${isPast ? 'text-gray-500' : 'text-white'}`}>{title}</h2>
                <div className="space-y-8">
                    {sortedDates.map(date => (
                        <div key={date}>
                            <h3 className="text-xl font-semibold text-white/80 mb-3 border-b border-white/10 pb-2 flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${isPast ? 'bg-gray-500' : 'bg-primary/80'}`}></span>
                                {date}
                            </h3>
                            <div className="grid gap-4 md:grid-cols-2">
                                {grouped[date].map(meeting => (
                                    <div key={meeting.id} className="glass-card hover:bg-white/10 transition-colors group relative overflow-hidden">
                                        <div className={`absolute left-0 top-0 bottom-0 w-1 ${isPast ? 'bg-gray-600' : 'bg-gradient-to-b from-blue-500 to-purple-500'}`}></div>
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <h4 className="font-bold text-lg text-white">{meeting.title}</h4>
                                                    {!isPast && (
                                                        <button
                                                            onClick={() => deleteMeeting(meeting.id)}
                                                            className="text-gray-500 hover:text-red-500 transition-colors"
                                                            title="Cancel Meeting"
                                                        >
                                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                                        </button>
                                                    )}
                                                </div>
                                                <div className="text-sm text-gray-300 mt-1 flex items-center gap-2">
                                                    <svg className="w-4 h-4 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                                    {new Date(meeting.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} -
                                                    {new Date(meeting.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </div>
                                                <div className="text-xs text-gray-400 mt-2 flex items-center gap-2">
                                                    <svg className="w-4 h-4 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                                                    {meeting.participants}
                                                </div>
                                            </div>
                                            <span className={`px-2 py-1 rounded-md text-xs font-medium ${isPast ? 'bg-gray-700 text-gray-400' :
                                                meeting.status === 'scheduled' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
                                                }`}>
                                                {isPast ? 'Completed' : meeting.status}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    if (loading) return <div className="text-center text-white p-10">Loading schedule...</div>;

    return (
        <div className="max-w-4xl mx-auto space-y-12">
            <div className="flex justify-between items-center">
                <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                    Your Calendar
                </h2>
                <button
                    onClick={fetchMeetings}
                    className="btn-primary text-sm px-4 py-2 flex items-center gap-2 hover:bg-white/10"
                >
                    <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh
                </button>
            </div>

            {upcoming.length === 0 && past.length === 0 ? (
                <div className="glass-card p-10 text-center text-gray-400">
                    <p className="text-xl">No meetings found.</p>
                    <p className="text-sm mt-2">Ask the assistant to schedule one!</p>
                </div>
            ) : (
                <>
                    {upcoming.length > 0 ? renderMeetingGroup(upcoming, "Upcoming Events") : (
                        <div className="text-center py-10 text-gray-500 border border-dashed border-white/10 rounded-lg">
                            No upcoming meetings.
                        </div>
                    )}

                    {past.length > 0 && (
                        <>
                            <div className="border-t border-white/10 my-8"></div>
                            {renderMeetingGroup(past, "Past Events", true)}
                        </>
                    )}
                </>
            )}
        </div>
    );
};

export default MeetingDashboard;
