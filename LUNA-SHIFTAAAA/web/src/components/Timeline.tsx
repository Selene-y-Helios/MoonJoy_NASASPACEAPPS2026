import { useId, useMemo } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  Earth, 
  Moon, 
  Calendar 
} from 'lucide-react';
import { addDaysToDateString, minutesToTimeString } from '../lib/astronomy';

interface TimelineProps {
  date: string;
  onDateChange: (nextDate: string) => void;
  minutes: number;
  onMinutesChange: (nextMinutes: number) => void;
  earthDegrees: number;
  moonDegrees: number;
  isPlaying: boolean;
  onTogglePlay: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  scientific?: boolean;
}

const QUICK_TICKS = [
  { label: '00:00', min: 0 },
  { label: '03:00', min: 180 },
  { label: '06:00', min: 360 },
  { label: '09:00', min: 540 },
  { label: '12:00', min: 720 },
  { label: '15:00', min: 900 },
  { label: '18:00', min: 1080 },
  { label: '21:00', min: 1260 },
  { label: '24:00', min: 1440 },
  { label: '24:59', min: 1499 },
];

export default function Timeline({
  date,
  onDateChange,
  minutes,
  onMinutesChange,
  earthDegrees,
  moonDegrees,
  isPlaying,
  onTogglePlay,
  speed,
  onSpeedChange,
  scientific = false,
}: TimelineProps) {
  const sliderId = useId();
  const timeString = useMemo(() => minutesToTimeString(minutes), [minutes]);

  // Format the selected date
  const formattedDate = useMemo(() => {
    try {
      const [y, m, d] = date.split('-').map(Number);
      const dt = new Date(Date.UTC(y, m - 1, d));
      return dt.toLocaleDateString('en-US', { 
        weekday: 'short', 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric',
        timeZone: 'UTC'
      }).toUpperCase();
    } catch {
      return date;
    }
  }, [date]);

  const maxMinutes = scientific ? 1439 : 1499;
  const progressPercent = (Math.min(minutes,maxMinutes) / maxMinutes) * 100;

  return (
    <div className="timeline-container" role="region" aria-label={scientific ? "NASA SPICE timeline" : "Orbital timeline"}>
      <div className="timeline-header">
        {/* Date and day navigation */}
        <div className="timeline-date-group">
          <button 
            type="button"
            className="timeline-btn icon-only"
            title="Previous day" 
            aria-label="Previous day"
            onClick={() => onDateChange(addDaysToDateString(date, -1))}
          >
            <ChevronLeft size={16} />
          </button>
          
          <div className="timeline-date-badge" title="Selected UTC date">
            <Calendar size={13} className="timeline-accent-icon" />
            <span>{formattedDate}</span>
          </div>

          <button 
            type="button"
            className="timeline-btn icon-only" 
            title="Next day" 
            aria-label="Next day"
            onClick={() => onDateChange(addDaysToDateString(date, 1))}
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Playback and speed */}
        <div className="timeline-playback-group">
          <button 
            type="button"
            className={`timeline-play-btn ${isPlaying ? 'playing' : ''}`}
            onClick={onTogglePlay}
            title={scientific ? (isPlaying ? 'Pause SPICE timeline' : 'Play SPICE timeline') : (isPlaying ? 'Pause rotation' : 'Play orbital animation')}
            aria-label={scientific ? (isPlaying ? 'Pause SPICE timeline' : 'Play SPICE timeline') : (isPlaying ? 'Pause rotation' : 'Play orbital animation')}
          >
            {isPlaying ? <Pause size={15} /> : <Play size={15} style={{ marginLeft: 2 }} />}
            <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
          </button>

          <div className="timeline-speed-selector">
            {[1, 10, 60].map(s => (
              <button
                key={s}
                type="button"
                className={`timeline-speed-btn ${speed === s ? 'active' : ''}`}
                onClick={() => onSpeedChange(s)}
                title={`Speed ${s}x`}
              >
                {s}x
              </button>
            ))}
          </div>

          <button
            type="button"
            className="timeline-btn icon-only"
            title="Reset to 00:00"
            aria-label="Reset to 00:00"
            onClick={() => onMinutesChange(0)}
          >
            <RotateCcw size={14} />
          </button>
        </div>

        {/* Digital clock and axial rotation indicators */}
        <div className="timeline-metrics-group">
          <div className="timeline-time-display">
            <Clock size={14} className="timeline-accent-icon" />
            <strong className="timeline-time-text">{timeString}</strong>
            <small className="timeline-utc-tag">UTC</small>
          </div>

          {scientific ? <span className="science-timeline-source">SPICE / LOLA</span> : <div className="timeline-degrees">
            <span className="degree-pill earth" title="Earth axial rotation">
              <Earth size={12} />
              <span>{Math.round(earthDegrees)}°</span>
            </span>
            <span className="degree-pill moon" title="Moon axial rotation">
              <Moon size={12} />
              <span>{Math.round(moonDegrees)}°</span>
            </span>
          </div>}
        </div>
      </div>

      {/* Interactive timeline slider */}
      <div className="timeline-slider-wrapper">
        <input
          id={sliderId}
          type="range"
          min={0}
          max={maxMinutes}
          step={1}
          value={Math.min(minutes,maxMinutes)}
          onChange={e => onMinutesChange(Number(e.target.value))}
          className="timeline-range"
          aria-label={scientific ? "SPICE timeline from 00:00 to 23:59 UTC" : "Timeline from 00:00 to 24:59"}
          style={{
            background: `linear-gradient(to right, #48d6e3 0%, #48d6e3 ${progressPercent}%, #1b283d ${progressPercent}%, #1b283d 100%)`
          }}
        />

        {/* Static timeline tick labels */}
        <div className="timeline-ticks">
          {QUICK_TICKS.filter(t=>!scientific||t.min<=1439).map(t => (
            <button
              key={t.label}
              type="button"
              className="timeline-tick static"
              onClick={() => onMinutesChange(t.min)}
              title={`Jump to ${t.label}`}
            >
              <span className="tick-dot" />
              <span className="tick-label">{t.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
