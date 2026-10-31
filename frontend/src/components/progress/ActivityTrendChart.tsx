import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { ActivitySummary } from '../../types';

interface ActivityTrendChartProps {
  data: ActivitySummary[];
}

export const ActivityTrendChart: React.FC<ActivityTrendChartProps> = ({ data }) => {
  return (
    <div
      className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft"
      data-testid="activity-trend-chart"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-sm text-slate-100">7-Day Learning Activity</h3>
          <p className="text-[11px] text-slate-400">Questions answered & study minutes</p>
        </div>
        <div className="flex items-center gap-4 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400" />
            <span className="text-slate-300">Questions</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-electric-600" />
            <span className="text-slate-300">Minutes</span>
          </div>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
            <XAxis
              dataKey="day"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
            />
            <YAxis
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#111827',
                borderColor: '#334155',
                borderRadius: '0.75rem',
                fontSize: '12px',
                color: '#F8FAFC',
                boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              }}
              formatter={(value: any, name: any) => [
                value,
                name === 'questionsAnswered' ? 'Questions Answered' : 'Study Minutes',
              ]}
              labelFormatter={(label) => `Day: ${label}`}
            />
            <Bar dataKey="questionsAnswered" fill="#22D3EE" radius={[4, 4, 0, 0]} maxBarSize={22} />
            <Bar dataKey="studyMinutes" fill="#2563EB" radius={[4, 4, 0, 0]} maxBarSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
