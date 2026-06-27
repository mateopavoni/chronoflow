import { Link } from 'react-router-dom'
import { Workflow, GitBranch, Braces, History, ArrowRight } from 'lucide-react'
import { ThemeToggle } from '../components/ui/ThemeToggle'

/**
 * Public landing page (route "/"). Explains the product and routes into the
 * app at "/app". No backend, no auth — purely marketing/positioning.
 */
const FEATURES = [
  {
    icon: GitBranch,
    title: 'Async ready-set scheduler',
    body: 'Not a CRUD. A DAG engine that runs independent branches in real parallel — fan-in waits for N inputs, fan-out fires N in parallel — instead of stepping level by level.',
  },
  {
    icon: Braces,
    title: 'Dynamic JSONPath, no eval',
    body: 'Pass payloads between nodes with JSONPath expressions and branch on conditions evaluated by a sandboxed parser — never eval(). Safe by construction.',
  },
  {
    icon: History,
    title: 'Time-travel debugging',
    body: 'Every run is an append-only log of immutable per-node snapshots. Scrub any execution backwards and forwards to inspect exactly what each node saw.',
  },
]

export function Landing() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-on-surface">
      {/* Top bar */}
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-outline-variant bg-surface px-container-margin">
        <div className="flex items-center gap-2">
          <Workflow size={16} className="text-on-surface-variant" aria-hidden="true" />
          <span className="font-mono text-code-sm font-bold uppercase tracking-wider">ChronoFlow</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/app"
            className="font-mono text-label-xs uppercase tracking-wide text-on-surface-variant transition-colors hover:text-on-surface"
          >
            Open app
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-4xl px-container-margin py-24 text-center">
          <p className="mb-4 font-mono text-label-xs uppercase tracking-widest text-on-surface-variant">
            DAG Engine // Time-Travel Debugging
          </p>
          <h1 className="text-display-lg">Design, run and replay event-driven workflows.</h1>
          <p className="mx-auto mt-6 max-w-2xl text-body-sm text-on-surface-variant">
            ChronoFlow is a visual workflow engine: draw a graph of tasks, execute it with real
            async parallelism, wire payloads with JSONPath, and step through any past run with a
            time-travel debugger.
          </p>
          <div className="mt-10 flex items-center justify-center gap-3">
            <Link
              to="/app"
              className="inline-flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-code-sm font-bold uppercase tracking-wide text-on-primary transition-opacity hover:opacity-90"
            >
              Open the app
              <ArrowRight size={14} aria-hidden="true" />
            </Link>
            <a
              href="https://github.com/mateopavoni/chronoflow"
              className="inline-flex items-center gap-2 border border-outline-variant px-4 py-2 font-mono text-code-sm uppercase tracking-wide text-on-surface-variant transition-colors hover:text-on-surface"
            >
              Source
            </a>
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto grid max-w-5xl gap-px border-y border-outline-variant bg-outline-variant md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="bg-background p-6">
              <Icon size={18} className="text-on-surface-variant" aria-hidden="true" />
              <h2 className="mt-4 text-headline-md">{title}</h2>
              <p className="mt-2 text-body-sm text-on-surface-variant">{body}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="border-t border-outline-variant bg-surface px-container-margin py-4 text-center font-mono text-label-xs uppercase tracking-wide text-on-surface-variant">
        ChronoFlow — Mateo Pavoni
      </footer>
    </div>
  )
}
