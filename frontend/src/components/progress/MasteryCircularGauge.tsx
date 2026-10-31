import React from 'react';
import { Award, Zap } from 'lucide-react';

interface MasteryCircularGaugeProps {
  percentage: number; // 0 to 100
  size?: number;
  strokeWidth?: number;
}

export const MasteryCircularGauge: React.FC<MasteryCircularGaugeProps> = ({
  percentage,
  size = 150,
  strokeWidth = 12,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  let tierColor = '#00F0FF';
  let tierLabel = 'Weak';
  if (percentage >= 90) {
    tierColor = '#10B981';
    tierLabel = 'Mastered';
  } else if (percentage >= 70) {
    tierColor = '#3B82F6';
    tierLabel = 'Good';
  } else if (percentage >= 40) {
    tierColor = '#F59E0B';
    tierLabel = 'Developing';
  }

  return (
    <div
      className="flex flex-col items-center justify-center relative select-none"
      data-testid="mastery-circular-gauge"
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full transform -rotate-90" viewBox={`0 0 ${size} ${size}`}>
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#1E293B"
            strokeWidth={strokeWidth}
            fill="transparent"
          />

          {/* Glowing Animated Progress Stroke */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="url(#gauge-gradient)"
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />

          <defs>
            <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#2563EB" />
              <stop offset="100%" stopColor="#00F0FF" />
            </linearGradient>
          </defs>
        </svg>

        {/* Center Percentage Display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-3xl font-extrabold gradient-text-blue-cyan leading-none">
            {percentage}%
          </span>
          <span className="text-[11px] font-semibold text-slate-300 mt-1 uppercase tracking-wider">
            {tierLabel}
          </span>
        </div>
      </div>
    </div>
  );
};
