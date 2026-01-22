import React, { useState } from 'react';

const steps = [
    {
        title: "Welcome to AI Assistant",
        content: "Your new personal productivity powerhouse. We manage your inbox so you can focus on work.",
        icon: "👋"
    },
    {
        title: "Step 1: Secure Login",
        content: "Click 'Get Started with Google'. We use official Google OAuth for maximum security. We never store your password.",
        icon: "🔐"
    },
    {
        title: "Step 2: Grant Permissions",
        content: (
            <div className="space-y-4">
                <p><strong>CRITICAL:</strong> When prompted, you MUST check the boxes to allow access to your Gmail and Calendar.</p>
                <div className="bg-white/10 p-4 rounded-lg border border-yellow-500/50 text-left text-sm">
                    <p className="text-yellow-300 font-bold mb-2">⚠ Look for these checkboxes:</p>
                    <ul className="list-disc list-inside space-y-1 text-gray-300">
                        <li>Read, compose, send, and permanently delete all your email from Gmail</li>
                        <li>See, edit, share, and permanently delete all the calendars you can access using Google Calendar</li>
                    </ul>
                    <p className="mt-3 text-xs opacity-70">If you don't check these, the AI cannot read your emails or schedule meetings!</p>
                </div>
            </div>
        ),
        icon: "✅"
    },
    {
        title: "Step 3: Sync & Relax",
        content: "Once logged in, click 'Sync Gmail'. The AI will analyze your last 10 emails, categorize them, and prepare drafts. Sit back and watch the magic.",
        icon: "✨"
    }
];

const Tutorial = ({ onComplete }) => {
    const [currentStep, setCurrentStep] = useState(0);

    return (
        <div className="min-h-screen bg-dark flex flex-col items-center justify-center p-6 relative overflow-hidden">
            {/* Background Decoration */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0">
                <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-[100px]"></div>
                <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-secondary/20 rounded-full blur-[100px]"></div>
            </div>

            <div className="relative z-10 max-w-2xl w-full glass-card p-1">
                <div className="p-8 md:p-12">
                    {/* Progress Bar */}
                    <div className="flex gap-2 mb-8">
                        {steps.map((_, idx) => (
                            <div
                                key={idx}
                                className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${idx <= currentStep ? 'bg-gradient-to-r from-primary to-secondary' : 'bg-white/10'}`}
                            ></div>
                        ))}
                    </div>

                    {/* Content */}
                    <div className="text-center min-h-[300px] flex flex-col items-center justify-center animate-fade-in">
                        <div className="text-6xl mb-6 animate-bounce-slow">
                            {steps[currentStep].icon}
                        </div>
                        <h2 className="text-3xl font-bold text-white mb-4">
                            {steps[currentStep].title}
                        </h2>
                        <div className="text-gray-300 text-lg leading-relaxed">
                            {steps[currentStep].content}
                        </div>
                    </div>

                    {/* Navigation */}
                    <div className="flex justify-between items-center mt-8 pt-8 border-t border-white/10">
                        <button
                            onClick={() => setCurrentStep(prev => Math.max(0, prev - 1))}
                            disabled={currentStep === 0}
                            className={`px-6 py-2 rounded-lg text-sm font-bold transition-colors ${currentStep === 0 ? 'opacity-0 cursor-default' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
                        >
                            Back
                        </button>

                        {currentStep < steps.length - 1 ? (
                            <button
                                onClick={() => setCurrentStep(prev => Math.min(steps.length - 1, prev + 1))}
                                className="btn-primary px-8 py-3 rounded-xl shadow-lg shadow-primary/20"
                            >
                                Next Step
                            </button>
                        ) : (
                            <button
                                onClick={onComplete}
                                className="btn-primary px-8 py-3 rounded-xl shadow-lg shadow-primary/20 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400 hover:to-emerald-500 border-none"
                            >
                                Go to App
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <button onClick={onComplete} className="mt-8 text-gray-500 hover:text-white text-sm relative z-10">
                Skip Tutorial
            </button>
        </div>
    );
};

export default Tutorial;
