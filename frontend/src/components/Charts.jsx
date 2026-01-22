import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#EF4444'];

export const PriorityChart = ({ data }) => {
    // Aggregate data by priority
    const count = data.reduce((acc, email) => {
        acc[email.priority] = (acc[email.priority] || 0) + 1;
        return acc;
    }, {});

    const chartData = Object.keys(count).map(key => ({ name: key, value: count[key] }));

    return (
        <div className="h-64 w-full">
            <ResponsiveContainer>
                <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        fill="#8884d8"
                        paddingAngle={5}
                        dataKey="value"
                    >
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} itemStyle={{ color: '#fff' }} />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
};

export const CategoryChart = ({ data }) => {
    // 1. Safety Check: If no data, don't render chart to prevent "width -1" error
    if (!data || data.length === 0) return <div className="h-64 flex items-center justify-center text-gray-500">No data available</div>;

    // Aggregate data by intent
    const count = data.reduce((acc, email) => {
        // Handle potentially null intents or comma-separated lists
        // If "intent" is "Urgent,Finance", we might want to count both or just primary.
        // For simplicity, handle single string or default to 'Unknown'
        const intent = email.intent || 'Unknown';
        acc[intent] = (acc[intent] || 0) + 1;
        return acc;
    }, {});

    const chartData = Object.keys(count).map(key => ({ name: key, value: count[key] }));

    return (
        <div style={{ width: '100%', height: 300 }}>
            {/* Use absolute pixel height instead of just class to be safer for Recharts */}
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                    <XAxis dataKey="name" stroke="#9ca3af" fontSize={10} tickLine={false} axisLine={false} interval={0} angle={-30} textAnchor="end" height={60} />
                    <YAxis stroke="#9ca3af" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: 'rgba(255, 255, 255, 0.1)' }} contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} itemStyle={{ color: '#fff' }} />
                    <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};
