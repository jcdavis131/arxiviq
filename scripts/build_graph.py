#!/usr/bin/env python3
"""
build_graph.py — Knowledge graph builder for arxiviq.com
Stdlib only. Builds graph.json from papers.json
"""
import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PAPERS_PATH = DATA_DIR / "papers.json"
ACNE_STATS_PATH = DATA_DIR / "acne_stats.json"
SITE_DATA_DIR = PROJECT_ROOT / "site" / "public" / "data"

GRAPH_PATH = DATA_DIR / "graph.json"
GRAPH_STATS_PATH = DATA_DIR / "graph_stats.json"
REPORT_PATH = DATA_DIR / "GRAPH_REPORT.md"

ARCH_PATTERNS = [
    ("Dreamer",       r"\bDreamer(?:V2|V3|Pro)?\b"),
    ("JEPA",          r"\bJEPA\b"),
    ("I-JEPA",        r"\bI-?JEPA\b"),
    ("V-JEPA",        r"\bV-?JEPA\b"),
    ("ImageBind",     r"\bImageBind\b"),
    ("Hamiltonian",   r"\bHamiltonian\b"),
    ("Lagrangian",    r"\bLagrangian\b"),
    ("World Model",   r"\bWorld Models?\b"),
    ("Predictive Coding", r"\bPredictive Coding\b"),
    ("Foundation Model",  r"\bFoundation Models?\b"),
    ("DINO",          r"\bDINO(?:v2)?\b"),
    ("CLIP",          r"\bCLIP\b"),
    ("Genie",         r"\bGenie\b"),
    ("MuZero",        r"\bMuZero\b"),
    ("PlaNet",        r"\bPlaNet\b"),
    ("RSSM",          r"\bRSSM\b"),
    ("Transformers",  r"\bTransformer\b"),
    ("Diffusion",     r"\bDiffusion\b"),
]

TOPIC_NODES = {
    "world_models": "World Models",
    "jepa": "JEPA",
    "imagebind": "ImageBind",
    "v_jepa": "V-JEPA",
    "pred_coding": "Predictive Coding",
    "hamiltonian": "Hamiltonian NNs",
    "train_dynamics": "Training Dynamics",
    "foundation_wm": "Foundation World Models",
}

def load_papers():
    if not PAPERS_PATH.exists():
        print(f"! {PAPERS_PATH} missing — empty graph fallback", flush=True)
        return []
    with open(PAPERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_acne_stats():
    if ACNE_STATS_PATH.exists():
        try:
            with open(ACNE_STATS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())

def extract_architectures(text: str):
    found = set()
    for canon, pat in ARCH_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            found.add(canon)
    return found

def build_graph(papers):
    nodes = []
    edges = []
    node_ids = set()

    def add_node(n):
        if n["id"] not in node_ids:
            node_ids.add(n["id"])
            nodes.append(n)
            return True
        return False

    author_to_papers = defaultdict(list)
    org_to_persons = defaultdict(set)
    paper_to_authors = defaultdict(list)
    arch_counter = Counter()
    tag_counter = Counter()
    method_counter = Counter()

    person_nodes = {}
    org_nodes = {}
    paper_nodes = {}
    arch_nodes = {}
    topic_nodes = {}

    for tag, label in TOPIC_NODES.items():
        tid = f"topic:{tag}"
        topic_nodes[tid] = {
            "id": tid,
            "label": label,
            "type": "Topic",
            "meta": {"tag": tag, "label": label}
        }
        add_node(topic_nodes[tid])

    for paper in papers:
        pid_raw = paper.get("id","unknown")
        pid = f"paper:{pid_raw}"
        title = paper.get("title","")
        summary = paper.get("summary","")
        full_text = f"{title} {summary}"

        cats = paper.get("categories", [])
        query_tag = paper.get("query_tag","unknown")
        query_tags = paper.get("query_tags", [query_tag])

        tag_counter[query_tag] += 1

        pnode = {
            "id": pid,
            "label": title[:120],
            "type": "Paper",
            "meta": {
                "title": title,
                "summary": summary[:2000],
                "arxiv_id": pid_raw,
                "arxiv_url": paper.get("arxiv_url"),
                "published": paper.get("published"),
                "query_tag": query_tag,
                "query_tags": query_tags,
                "categories": cats,
            }
        }
        add_node(pnode)
        paper_nodes[pid] = pnode

        for qt in query_tags:
            t_id = f"topic:{qt}"
            if t_id not in node_ids:
                tnode = {"id": t_id, "label": qt, "type": "Topic", "meta": {"tag": qt}}
                add_node(tnode)
                topic_nodes[t_id] = tnode
            edges.append({"src": pid, "dst": t_id, "kind": "RELATED_TO", "weight": 1.0})

        for cat in cats:
            mid = f"method:{cat}"
            if mid not in node_ids:
                mnode = {"id": mid, "label": cat, "type": "Method", "meta": {"category": cat}}
                add_node(mnode)
            edges.append({"src": pid, "dst": mid, "kind": "CATEGORIZED_AS", "weight": 0.6})
            method_counter[cat] += 1

        archs = extract_architectures(full_text)
        for arch in archs:
            aid = f"arch:{arch.lower().replace(' ','_').replace('-','_')}"
            if aid not in arch_nodes:
                anode = {"id": aid, "label": arch, "type": "Architecture", "meta": {"name": arch}}
                arch_nodes[aid] = anode
                add_node(anode)
            edges.append({"src": pid, "dst": aid, "kind": "USES_ARCHITECTURE", "weight": 0.9})
            arch_counter[arch] += 1

        for author in paper.get("authors", []):
            raw_name = author.get("name") if isinstance(author, dict) else str(author)
            if not raw_name:
                continue
            name = normalize_name(raw_name)
            person_id = f"person:{name}"
            if person_id not in person_nodes:
                pn = {
                    "id": person_id,
                    "label": name,
                    "type": "Person",
                    "meta": {
                        "name": name,
                        "first": name.split()[0] if name else "",
                        "last": name.split()[-1] if len(name.split())>1 else name,
                    }
                }
                person_nodes[person_id] = pn
                add_node(pn)

            edges.append({"src": person_id, "dst": pid, "kind": "AUTHORED", "weight": 1.0})
            author_to_papers[person_id].append(pid)
            paper_to_authors[pid].append(person_id)

            affil = author.get("affiliation") if isinstance(author, dict) else None
            if affil and isinstance(affil, str) and affil.strip():
                aff_clean = " ".join(affil.strip().split())
                org_id = f"org:{aff_clean}"
                if org_id not in org_nodes:
                    onode = {"id": org_id, "label": aff_clean, "type": "Org", "meta": {"name": aff_clean}}
                    org_nodes[org_id] = onode
                    add_node(onode)
                edges.append({"src": person_id, "dst": org_id, "kind": "AFFILIATED_WITH", "weight": 0.8})
                org_to_persons[org_id].add(person_id)

    for pid, author_list in paper_to_authors.items():
        for i in range(len(author_list)):
            for j in range(i+1, len(author_list)):
                edges.append({"src": author_list[i], "dst": author_list[j], "kind": "COAUTHORED", "weight": 0.5})

    degree = Counter()
    for e in edges:
        degree[e["src"]] += 1
        degree[e["dst"]] += 1

    top_god = degree.most_common(10)
    god_nodes = [{"id": nid, "degree": deg, "label": next((n["label"] for n in nodes if n["id"]==nid), nid)} for nid, deg in top_god]

    communities_by_tag = {}
    for tag in TOPIC_NODES.keys():
        mem_papers = [p for p in papers if tag in p.get("query_tags", [])]
        mem_paper_ids = [f"paper:{p['id']}" for p in mem_papers]
        mem_persons = set()
        for pid in mem_paper_ids:
            mem_persons.update(paper_to_authors.get(pid, []))
        communities_by_tag[tag] = {
            "papers": len(mem_paper_ids),
            "persons": len(mem_persons),
            "paper_ids": mem_paper_ids[:10],
        }

    communities_by_org = {}
    for org_id, persons in org_to_persons.items():
        communities_by_org[org_id] = {
            "label": next((n["label"] for n in nodes if n["id"]==org_id), org_id),
            "persons": len(persons),
            "persons_sample": list(persons)[:5],
        }
    sorted_org_comms = sorted(communities_by_org.items(), key=lambda x: x[1]["persons"], reverse=True)[:10]

    by_type = Counter(n["type"] for n in nodes)
    by_edge_kind = Counter(e["kind"] for e in edges)

    graph = {"nodes": nodes, "edges": edges}
    graph_stats = {
        "nodes": len(nodes),
        "edges": len(edges),
        "by_type": dict(by_type),
        "by_edge_kind": dict(by_edge_kind),
        "god_nodes": god_nodes,
        "communities": {
            "by_tag": communities_by_tag,
            "by_org_top": {k: v for k,v in sorted_org_comms},
        },
        "architectures_found": dict(arch_counter),
        "methods_found": dict(method_counter),
        "tags_count": dict(tag_counter),
    }

    return graph, graph_stats, {
        "author_to_papers": author_to_papers,
        "paper_to_authors": paper_to_authors,
        "degree": degree,
        "arch_counter": arch_counter,
    }

def render_report(graph_stats, acne_stats, papers_count):
    tag_lines = "\n".join([f"- **{k}**: {v.get('papers',0)} papers, {v.get('persons',0)} authors" for k,v in graph_stats["communities"]["by_tag"].items()])
    god_lines = "\n".join([f"{i+1}. `{g['id']}` ({g['label'][:60]}) — degree {g['degree']}" for i,g in enumerate(graph_stats["god_nodes"])])
    arch_lines = "\n".join([f"- {k}: {v} papers" for k,v in sorted(graph_stats["architectures_found"].items(), key=lambda x: x[1], reverse=True)])
    org_lines = "\n".join([f"- {k.split('org:',1)[-1][:80]} — {v['persons']} persons" for k,v in graph_stats["communities"]["by_org_top"].items()])

    by_type_str = ", ".join([f"{k}={v}" for k,v in graph_stats["by_type"].items()])
    by_edge_str = ", ".join([f"{k}={v}" for k,v in graph_stats["by_edge_kind"].items()])

    if acne_stats:
        acne_summary = f"- ACNE built via {acne_stats.get('built_via','manual')}, nodes={acne_stats.get('tlpg_counts',{}).get('nodes','?')}, edges={acne_stats.get('tlpg_counts',{}).get('edges','?')}, triggers={acne_stats.get('tlpg_counts',{}).get('triggers','?')}, authors={acne_stats.get('unique_authors')}, orgs={acne_stats.get('unique_orgs')}"
    else:
        acne_summary = "- ACNE stats not yet available (run build_acne.py)"

    report = f"""# arxiviq Graph Report

## Pipeline
- Fetch: `scripts/fetch_topics.py` → `data/papers.json` (arXiv Atom API, 30 per 8 topics, retries, synthetic fallback)
- ACNE TLPG: `scripts/build_acne.py` → `acne_store/` (Person / Organization / Citation nodes, AUTHORED, AFFILIATED_WITH, COAUTHORED_WITH, SAME_AS, triggers.jsonl)
- Graph: `scripts/build_graph.py` → `data/graph.json` + `data/graph_stats.json` + this report

Pipeline ensures data pipeline green even if arXiv unreachable (synthetic fallback), dedup by stripped arXiv ID, query_tags merged.

## Landscape Summary — World Models for NN Training

**Total papers**: {papers_count}
**Nodes / Edges**: {graph_stats["nodes"]} / {graph_stats["edges"]}  ({by_type_str}; edges {by_edge_str})

World models for NN training sits at intersection of self-supervised learning (JEPA/I-JEPA/V-JEPA), generative latent dynamics (Dreamer, RSSM, diffusion), multimodal binding (ImageBind), and physics-inspired inductive biases (Hamiltonian/Lagrangian). Training dynamics & loss landscapes tie these together: grokking, double descent, collapse avoidance (VICReg), and spectral properties of Hessians correlate with planning quality.

Core questions:
- Can latent prediction (JEPA) replace pixel reconstruction for scalable world models?
- Do Hamiltonian / conservative priors improve sample efficiency & stable rollouts?
- How do training dynamics (phase transitions, Hessian spectra) explain emergence of planning?
- Foundation world models: does cross-embodiment pretraining yield transferable causal graphs (Platonic World Model hypothesis)?

## Architecture Inventory

Found architectures in titles/abstracts (regex):

{arch_lines if arch_lines else "- none detected (empty corpus?)"}

## God Nodes (Degree Centrality Top 10)

High-degree nodes indicate authors, orgs or topics that bridge the graph.

{god_lines if god_lines else "- none (empty graph)"}

## Communities

### By Query Tag
{tag_lines if tag_lines else "- none"}

### By Organization (Top 10)
{org_lines if org_lines else "- no orgs detected (affiliations often sparse in arXiv)"}

## ACNE Stats Tie-in

{acne_summary}

TLPG nodes mirror graph Person/Org/Citation. Triggers provide phrase→person linking for natural queries.

## Sample Queries

- "dreamer training" – expect papers where Dreamer arch + training dynamics tag intersect
- "hamiltonian world models" – Hamiltonian NNs as world model prior
- "jepa predictive" – JEPA ↔ predictive coding bridge
- "imagebind binding" – six-way multimodal binding

Generated by `scripts/build_graph.py`.
"""
    return report

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    papers = load_papers()
    print(f"[graph] loaded {len(papers)} papers", flush=True)

    acne_stats = load_acne_stats()

    graph, graph_stats, aux = build_graph(papers)

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    with open(GRAPH_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_stats, f, indent=2, ensure_ascii=False)

    try:
        with open(SITE_DATA_DIR / "graph.json", "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        with open(SITE_DATA_DIR / "graph_stats.json", "w", encoding="utf-8") as f:
            json.dump(graph_stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"! warning site copy failed: {e}")

    report_md = render_report(graph_stats, acne_stats, len(papers))
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)

    try:
        with open(SITE_DATA_DIR / "GRAPH_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report_md)
    except:
        pass

    print("\\n=== GRAPH STATS ===")
    print(json.dumps(graph_stats, indent=2)[:4000])
    print(f"\\nSaved graph {graph_stats['nodes']} nodes, {graph_stats['edges']} edges to {GRAPH_PATH}")
    print(f"Report to {REPORT_PATH}")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
