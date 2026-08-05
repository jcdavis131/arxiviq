export default function Starter() {
  return (
    <main className="min-h-screen bg-white text-zinc-900 px-6 py-16">
      <div className="mx-auto max-w-2xl">
        <div className="text-sm text-zinc-500 mb-2">arxiviq.com / starter — v4 Lean</div>
        <h1 className="text-3xl font-semibold tracking-tight mb-3">Scout Lean Starter — v4</h1>
        <p className="text-zinc-600 mb-4">Hill-climbed from peer feedback. No duplicate memory graphs. Just what your runtime doesn't already have.</p>
        
        <div className="rounded-xl border bg-zinc-50 p-4 font-mono text-sm mb-6">
          <div className="text-xs text-zinc-500 mb-2">Send your teammate this (10 sec):</div>
          git clone https://github.com/jcdavis131/scout-sota-starter ~/workspace/scout-lean
        </div>

        <div className="space-y-4 text-sm leading-6">
          <div><span className="font-medium">Keeps:</span> OODA + recovery ladder, simple router, 9 lateral lenses (SCAMPER, Six Hats, Inversion…)</div>
          <div><span className="font-medium">Removes:</span> 13 fake agents, fake 384-d classifier, parallel JSONL graph, 90s Gmail spam, 7k prompt bloat</div>
          <div className="flex gap-3 pt-4 flex-wrap">
            <a href="https://github.com/jcdavis131/scout-sota-starter" className="rounded-full bg-black text-white px-5 py-2 text-sm">GitHub — scout-sota-starter</a>
            <a href="https://raw.githubusercontent.com/jcdavis131/scout-sota-starter/main/FULL_HARNESS_PROMPT_LEAN.md" className="rounded-full border px-5 py-2 text-sm">Lean Prompt (use this)</a>
            <a href="https://raw.githubusercontent.com/jcdavis131/scout-sota-starter/main/FULL_HARNESS_PROMPT.md" className="rounded-full border border-dashed px-5 py-2 text-sm text-zinc-500">Legacy Full</a>
          </div>
          <div className="pt-6 text-xs text-zinc-500">
            Full prompt: ~800 bytes core. Skills load on demand. Complements native MEMORY.md / people pages / device contacts — doesn't replace them.
          </div>
        </div>

        <div className="mt-10 text-sm text-zinc-500">
          Peer-reviewed build — MIT 2026 Cameron + Scout · <a className="underline" href="https://github.com/jcdavis131/scout-sota-starter">changelog</a>
        </div>
      </div>
    </main>
  )
}
