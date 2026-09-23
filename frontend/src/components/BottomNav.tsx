import { useMemo } from 'react'
import { NavLink } from 'react-router-dom'
import { isUnreadNotification } from '../api/alerts'
import { useAlerts } from '../auth/AlertsContext'

const items = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/reports', label: 'Reports', icon: ReportsIcon },
  { to: '/map', label: 'Map', icon: MapIcon },
  { to: '/account', label: 'Account', icon: AccountIcon },
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

function ReportsIcon({ filled }: { filled: boolean }) {
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

function AccountIcon({ filled }: { filled: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle
        cx="12"
        cy="8"
        r="3.25"
        stroke="currentColor"
        strokeWidth="1.75"
        fill={filled ? 'currentColor' : 'none'}
      />
      <path
        d="M5.5 19.5c1.6-3 4-4.5 6.5-4.5s4.9 1.5 6.5 4.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}

/** Floating glass capsule with four tabs; the active tab is a primary-light pill. */
export function BottomNav() {
  const { notifications } = useAlerts()
  /** Reports tab badge = how many of the viewer's reports have a circle, not raw alert count. */
  const dottedReportCount = useMemo(() => {
    const ids = new Set<string>()
    for (const n of notifications) {
      if (!isUnreadNotification(n) || !n.report_id) continue
      ids.add(n.report_id)
    }
    return ids.size
  }, [notifications])

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
                  {item.to === '/reports' && dottedReportCount > 0 ? (
                    <span
                      className="absolute -right-2.5 -top-1 min-w-4 rounded-full bg-accent px-1 text-center text-[10px] font-bold leading-4 text-white shadow-[0_2px_8px_rgba(242,140,104,.45)]"
                      aria-label={`${dottedReportCount} ${dottedReportCount === 1 ? 'report' : 'reports'} with unread activity`}
                    >
                      {dottedReportCount > 9 ? '9+' : dottedReportCount}
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
