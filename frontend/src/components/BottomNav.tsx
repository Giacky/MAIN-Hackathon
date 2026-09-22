import { NavLink } from 'react-router-dom'
import { useAlerts } from '../auth/AlertsContext'

const items = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/report', label: 'Report', icon: ReportIcon },
  { to: '/matches', label: 'Matches', icon: MatchesIcon },
  { to: '/map', label: 'Map', icon: MapIcon },
] as const

function HomeIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ReportIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect
        x="5"
        y="3"
        width="14"
        height="18"
        rx="2.5"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
      />
      <path
        d="M8 8h8M8 12h8M8 16h5"
        stroke={filled ? 'var(--color-primary-light)' : 'currentColor'}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}

function MatchesIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle
        cx="9"
        cy="10"
        r="4"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
      />
      <circle
        cx="15"
        cy="14"
        r="4"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
        opacity={filled ? 0.7 : 1}
      />
    </svg>
  )
}

function MapIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 4 3 6.5V19l6-2.5L15 19l6-2.5V4L15 6.5 9 4Z"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinejoin="round"
        fill={filled ? 'currentColor' : 'none'}
      />
    </svg>
  )
}

/** Floating glass capsule with four tabs; the active tab is a primary-light pill. */
export function BottomNav() {
  const { unreadCount } = useAlerts()

  return (
    <nav className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <div className="glass-strong pointer-events-auto flex w-full max-w-md items-stretch gap-1 rounded-full p-1.5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={'end' in item ? item.end : false}
            className={({ isActive }) =>
              [
                'flex flex-1 flex-col items-center gap-0.5 rounded-full px-2 py-1.5 text-[11px] font-medium transition-colors duration-200',
                isActive ? 'bg-primary-light text-primary' : 'text-muted hover:text-ink',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                <span className="relative inline-flex">
                  <item.icon filled={isActive} />
                  {item.to === '/matches' && unreadCount > 0 ? (
                    <span
                      className="absolute -right-2.5 -top-1 min-w-4 rounded-full bg-accent px-1 text-center text-[10px] font-bold leading-4 text-white shadow-[0_2px_8px_rgba(242,140,104,.45)]"
                      aria-label={`${unreadCount} unread ${unreadCount === 1 ? 'alert' : 'alerts'}`}
                    >
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  ) : null}
                </span>
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
