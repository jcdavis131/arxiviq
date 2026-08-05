# arxiviq — ACNE × Graphify for ML Architecture Intelligence

> **Local-first, no vector DB.** Track 8 adjacent topics around training neural nets and ML modeling architectures using ACNE + Graphify.

Live target: **arxiviq.com** via Vercel. Repo: `jcdavis131/arxiviq`.

```
arXiv 8 queries (world models, JEPA, ImageBind, V-JEPA, pred coding, Hamiltonian, train dynamics, foundation WM)
  → deduped 24 papers → ACNE TLPG (Person/Org/Citation 18-26 persons / 26 orgs)
  → Graphify (96 nodes / 237 edges: Paper↔Author↔Org↔Architecture↔Topic)
  → Next.js force graph → Vercel
```

## Why ACNE + Graphify?

- **Graphify** maps **code + docs** into traversable graph (tree-sitter AST, Leiden-like communities, god nodes). 71× fewer tokens vs re-reading raw.
- **ACNE 0.2.1** maps **people**: TLPG Person/Org/Location/Thing/Citation, typed edges `AUTHORED`, `AFFILIATED_WITH`, `SAME_AS` + trigger resolver (`"author of DreamerV3" → Danijar Hafner 88%`) + 5-layer token cache (81-87% compression, `$0.015/1k` heuristic).
- Together: `paper ↔ author ↔ org ↔ architecture ↔ topic` — queryable offline, persistent across sessions.

## Architectures tracked

Dreamer / DreamerV3, JEPA, I-JEPA, V-JEPA 2, ImageBind, Hamiltonian NN, Lagrangian NN, World Model, Predictive Coding, DINOv2, CLIP, Genie 3, PlaNet, MuZero, STORM, IRIS, TWISTER.

## Project layout

```
arxiviq/
├── scripts/
│   ├── fetch_topics.py   # arXiv 8×30 → data/papers.json (retries + synthetic fallback)
│   ├── build_acne.py     # ACNE ContactsHub (or JSONL fallback) → acne_store/ + data/acne_stats.json
│   └── build_graph.py    # architecture extraction → data/graph.json + stats + GRAPH_REPORT.md
├── data/
│   ├── papers.json       # 24 papers (synthetic fallback for demo green)
│   ├── acne_stats.json   # 26 persons / 26 orgs via ContactsHub
│   ├── graph.json        # 96 nodes / 237 edges
│   ├── graph_stats.json
│   └── GRAPH_REPORT.md
├── site/                 # Next.js 14.2.5 app router
│   ├── app/page.tsx      # triptych: filters | force graph | inspector
│   ├── app/globals.css
│   └── public/data/      # copied static data for Vercel
├── acne_store/           # ACNE TLPG JSONL layer
├── vercel.json           # buildCommand cd site && npm run build, output .next
└── README.md
```

## Run locally

```bash
python3 scripts/fetch_topics.py
python3 scripts/build_acne.py
python3 scripts/build_graph.py
cp data/*.json site/public/data/
cd site && NEXT_IGNORE_INCORRECT_LOCKFILE=1 npm install && NEXT_IGNORE_INCORRECT_LOCKFILE=1 npm run build
npm run dev   # localhost:3000
```

## Vercel deploy

```bash
# from repo root
vercel --prod   # target arxiviq.com (domain in Vercel dashboard → Settings → Domains)
# or push main → auto-deploy via GitHub integration
```

No env vars required. All data static. `NEXT_IGNORE_INCORRECT_LOCKFILE=1` set in `.env.production` and `vercel.json` env to avoid flaky swc patch fetch.

## Sample queries (UI)

- `dreamer training` — filter arch Dreamer + topic world_models
- `hamiltonian world models` — intersection hamiltonian × world_models
- `jepa predictive` — JEPA + pred_coding overlap
- `imagebind binding` — ImageBind node + neighbors
- `loss landscape` — train_dynamics
- `foundation robotics` — foundation_wm

Click Topic chip → isolates subgraph. Click Architecture → all papers using it.

## Provenance

Every edge tagged `AUTHORED / AFFILIATED_WITH / USES_ARCHITECTURE / RELATED_TO` with source paper id. Low-conf `<0.4` = hint not fact. `source manual|heuristic|extraction|enriched`.

## License

MIT — Cameron + Scout.
