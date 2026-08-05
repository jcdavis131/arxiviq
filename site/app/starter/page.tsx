export default function Starter() {
  return (
    <main className="min-h-screen bg-white text-zinc-900 px-6 py-16">
      <div className="mx-auto max-w-2xl">
        <div className="text-sm text-zinc-500 mb-2">arxiviq.com / starter</div>
        <h1 className="text-3xl font-semibold tracking-tight mb-3">Scout SOTA Starter — v3.3</h1>
        <p className="text-zinc-600 mb-6">One line for teammates. 30 seconds to an agent harness that actually coordinates.</p>
        
        <div className="rounded-xl border bg-zinc-50 p-4 font-mono text-sm mb-6">
          <div className="text-xs text-zinc-500 mb-2">Send your teammate this:</div>
          curl -fsSL https://raw.githubusercontent.com/jcdavis131/scout-sota-starter/main/scripts/install.sh | bash
        </div>

        <div className="space-y-4">
          <div><span className="font-medium">What they get:</span> 13 agents L0-L4, 11 skill packs, 9 lateral lenses, people memory (ACNE), checkpoint timeline, verification econ</div>
          <div><span className="font-medium">Then:</span> Open your agent runtime → paste full prompt from GitHub repo</div>
          <div className="flex gap-3 pt-4">
            <a href="https://github.com/jcdavis131/scout-sota-starter" className="rounded-full bg-black text-white px-5 py-2 text-sm">GitHub — scout-sota-starter</a>
            <a href="https://raw.githubusercontent.com/jcdavis131/scout-sota-starter/main/FULL_HARNESS_PROMPT.md" className="rounded-full border px-5 py-2 text-sm">Full Prompt</a>
          </div>
        </div>

        <div className="mt-10 text-sm text-zinc-500">
          Full system map — MIT 2026 Cameron + Scout
        </div>
      </div>
    </main>
  )
}
