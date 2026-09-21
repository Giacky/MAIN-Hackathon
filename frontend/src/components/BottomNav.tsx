import { NavLink } from 'react-router-dom'

const items = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/report', label: 'Report', icon: ReportIcon },
  { to: '/matches', label: 'Matches', icon: MatchesIcon },
  { to: '/map', label: 'Map', icon: MapIcon },
  { to: '/pickup', label: 'Pickup', icon: PickupIcon },
  { to: '/account', label: 'Account', icon: AccountIcon },
] as const

function HomeIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
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
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect
        x="5"
        y="3"
        width="14"
        height="18"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
      />
      <path d="M8 8h8M8 12h8M8 16h5" stroke={filled ? '#f6f3ee' : 'currentColor'} strokeWidth="1.5" />
    </svg>
  )
}

function MatchesIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
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
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
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

function PickupIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 21s7-4.5 7-11a7 7 0 1 0-14 0c0 6.5 7 11 7 11Z"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
      />
      <circle cx="12" cy="10" r="2.25" fill={filled ? '#f6f3ee' : 'currentColor'} />
    </svg>
  )
}

function AccountIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle
        cx="12"
        cy="8"
        r="3.5"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
      />
      <path
        d="M5 19.5c1.5-3.5 4-5 7-5s5.5 1.5 7 5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}

export function BottomNav() {
  return (
    <nav className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <div className="pointer-events-auto flex w-full max-w-md items-stretch gap-0.5 rounded-full border border-hairline/80 bg-card/85 px-1.5 py-1.5 shadow-[0_8px_30px_rgba(28,25,23,0.08)] backdrop-blur-md">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={'end' in item ? item.end : false}
            className={({ isActive }) =>
              [
                'flex flex-1 flex-col items-center gap-0.5 rounded-full px-1 py-1.5 text-[10px] font-medium transition duration-150',
                isActive ? 'bg-ink text-page' : 'text-muted hover:text-ink',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                <item.icon filled={isActive} />
                <span>{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
