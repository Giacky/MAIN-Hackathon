import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Card } from '../components/ui/Card'
import { WarmupBanner } from '../components/WarmupBanner'

export function HomePage() {
  const { user, loading } = useAuth()

  return (
    <div className="space-y-6 animate-in">
      <header className="space-y-2 pt-2">
        <p className="text-sm text-muted">
          {loading
            ? 'Checking session…'
            : user
              ? `Hi, ${user.display_name}`
              : 'Demo accounts on Account · password demo'}
        </p>
        <h1 className="font-display text-[2rem] leading-tight text-ink">
          Lost something nearby?
        </h1>
        <p className="max-w-[22rem] text-[15px] leading-relaxed text-muted">
          Report what you lost or found, then rank photo and place matches around
          Maastricht.
        </p>
      </header>

      <WarmupBanner />

      <div className="space-y-3">
        <Link to="/report?type=lost" className="block">
          <Card className="transition duration-150 hover:border-primary/40 hover:shadow-sm">
            <h2 className="font-display text-xl text-ink">I lost something</h2>
            <p className="mt-1 text-sm text-muted">
              Pin where you last had it and add a photo if you can.
            </p>
          </Card>
        </Link>
        <Link to="/report?type=found" className="block">
          <Card className="transition duration-150 hover:border-primary/40 hover:shadow-sm">
            <h2 className="font-display text-xl text-ink">I found something</h2>
            <p className="mt-1 text-sm text-muted">
              Leave a holding note and optionally stay anonymous.
            </p>
          </Card>
        </Link>
      </div>

      <ol className="grid grid-cols-3 gap-2 text-center">
        {[
          { n: '1', t: 'Report' },
          { n: '2', t: 'Match' },
          { n: '3', t: 'Meet up' },
        ].map((step) => (
          <li key={step.n} className="rounded-xl px-2 py-3">
            <span className="font-display text-lg text-ink">{step.n}</span>
            <p className="mt-0.5 text-xs text-muted">{step.t}</p>
          </li>
        ))}
      </ol>
    </div>
  )
}
