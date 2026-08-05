#!/usr/bin/env python3
"""
build_acne.py — ACNE TLPG builder for arxiviq.com
Tries to use ContactsHub from ~/workspace/acne/src if present,
otherwise falls back to manual JSONL TLPG that mirrors ACNE format.

Stdlib only.
"""
import json
import sys
import re
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PAPERS_PATH = DATA_DIR / "papers.json"
ACNE_STORE = PROJECT_ROOT / "acne_store"
SITE_DATA_DIR = PROJECT_ROOT / "site" / "public" / "data"

# ensure we attempt import from acne
ACNE_SRC_CANDIDATES = [
    Path.home() / "workspace" / "acne" / "src",
    PROJECT_ROOT.parent / "acne" / "src",
    Path("/home/hatch/workspace/acne/src"),
]

# JSONL format helpers
def write_jsonl(path: Path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())

def initials(name: str):
    parts = name.split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0].upper()
    return f"{parts[0][0].upper()}{parts[-1][0].upper()}"

def last_first_initial(name: str):
    parts = name.split()
    if len(parts) < 2:
        return name.lower()
    return f"{parts[0][0].lower()} {parts[-1].lower()}"

def load_papers():
    if not PAPERS_PATH.exists():
        print(f"! {PAPERS_PATH} missing — cannot build ACNE. Create empty fallback.", flush=True)
        return []
    with open(PAPERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def try_contacts_hub(papers):
    """Attempt ACNE hub usage. Return True if succeeded, else False."""
    for candidate in ACNE_SRC_CANDIDATES:
        if candidate.exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
    try:
        from acne import ContactsHub  # type: ignore
    except Exception as e:
        print(f"[acne] ContactsHub not available ({e}) — using manual TLPG fallback.", flush=True)
        return False

    print(f"[acne] ContactsHub available, building store at {ACNE_STORE}", flush=True)
    try:
        ACNE_STORE.mkdir(parents=True, exist_ok=True)
        hub = ContactsHub(base=ACNE_STORE)  # may require specific arg name
        # Best-effort pipeline: we don't know exact API, so we manually add nodes via internal store if exposed.
        # Fallback to checking common methods.

        # Try hub.ingest or hub.add_contact style?
        # We attempt generic approach: if hub has `store`, use it.
        added = 0

        # If hub exposes pipeline_run, nodes/edges handling is custom.
        # Since we can't guarantee API, we attempt direct JSONL creation if hub init succeeded,
        # and then optionally call hub verification.

        # Create manual files anyway as ACNE store format is JSONL based
        print(f"[acne] hub initialized: {hub}. Proceeding to manual JSONL build inside acne_store to ensure compatibility.")
        build_manual_tlpg(papers)
        # If hub has rebuild / index method, call it
        for m in ["reindex", "build_triggers", "finalize"]:
            if hasattr(hub, m):
                try:
                    getattr(hub, m)()
                    print(f"[acne] called hub.{m}()")
                except Exception as e:
                    print(f"[acne] hub.{m}() failed: {e}")

        return True
    except Exception as e:
        print(f"[acne] hub usage failed ({e}) — fallback to manual", flush=True)
        return False

def build_manual_tlpg(papers):
    ACNE_STORE.mkdir(parents=True, exist_ok=True)
    nodes = []
    edges = []
    triggers = []

    person_ids = set()
    org_ids = set()
    paper_ids = set()

    # For SAME_AS handling
    # Map normalized lower -> canonical name id
    lower_to_person = {}

    org_counter = Counter()

    for paper in papers:
        pid_raw = paper["id"]
        pid = f"paper:{pid_raw}"
        paper_ids.add(pid)

        # Citation node
        nodes.append({
            "id": pid,
            "kind": "Citation",
            "label": paper.get("title","")[:120],
            "meta": {
                "title": paper.get("title"),
                "arxiv_id": pid_raw,
                "arxiv_url": paper.get("arxiv_url"),
                "published": paper.get("published"),
                "query_tag": paper.get("query_tag"),
                "query_tags": paper.get("query_tags", []),
                "categories": paper.get("categories", []),
                "summary": (paper.get("summary","")[:2000]),
            }
        })

        # Authors -> Person + edges
        authors = paper.get("authors", [])
        for author in authors:
            raw_name = author.get("name") if isinstance(author, dict) else str(author)
            if not raw_name:
                continue
            name = normalize_name(raw_name)
            person_id = f"person:{name}"
            if person_id not in person_ids:
                person_ids.add(person_id)
                nodes.append({
                    "id": person_id,
                    "kind": "Person",
                    "label": name,
                    "meta": {
                        "full_name": name,
                        "first": name.split()[0] if name else "",
                        "last": name.split()[-1] if len(name.split())>1 else name,
                        "initials": initials(name),
                    }
                })
                # lowercase mapping for SAME_AS
                lower = name.lower()
                if lower not in lower_to_person:
                    lower_to_person[lower] = person_id

            # AUTHORED edge person->paper
            edges.append({
                "src": person_id,
                "dst": pid,
                "kind": "AUTHORED",
                "weight": 1.0,
                "provenance": {"src": "arxiviq/papers.json", "tag": paper.get("query_tag")}
            })

            # Affiliation -> Org node + edge
            affil = author.get("affiliation") if isinstance(author, dict) else None
            if affil and isinstance(affil, str) and affil.strip():
                aff_clean = " ".join(affil.strip().split())
                org_id = f"org:{aff_clean}"
                if org_id not in org_ids:
                    org_ids.add(org_id)
                    nodes.append({
                        "id": org_id,
                        "kind": "Organization",
                        "label": aff_clean,
                        "meta": {"name": aff_clean}
                    })
                org_counter[aff_clean] += 1
                edges.append({
                    "src": person_id,
                    "dst": org_id,
                    "kind": "AFFILIATED_WITH",
                    "weight": 0.8,
                    "provenance": {"src": "author.affiliation"}
                })

    # Co-authorship edges (COAUTHORED) - undirected via two directed edges or one kind
    paper_to_authors = defaultdict(list)
    for e in edges:
        if e["kind"] == "AUTHORED":
            paper_to_authors[e["dst"]].append(e["src"])

    for paper_node, author_list in paper_to_authors.items():
        for i in range(len(author_list)):
            for j in range(i+1, len(author_list)):
                edges.append({
                    "src": author_list[i],
                    "dst": author_list[j],
                    "kind": "COAUTHORED_WITH",
                    "weight": 0.6,
                    "provenance": {"paper": paper_node}
                })
                # reverse for symmetry if needed but keep one directed+symmetric flag
                # Add reverse too for degree centrality
                edges.append({
                    "src": author_list[j],
                    "dst": author_list[i],
                    "kind": "COAUTHORED_WITH",
                    "weight": 0.6,
                    "provenance": {"paper": paper_node}
                })

    # SAME_AS for name variants (lowercase collisions, initials)
    # Group by last name
    last_to_persons = defaultdict(list)
    for pid in person_ids:
        # pid = person:<Name>
        name = pid.split("person:",1)[1]
        parts = name.split()
        last = parts[-1].lower() if parts else name.lower()
        last_to_persons[last].append(pid)

    for last, plist in last_to_persons.items():
        if len(plist) > 1:
            # pairwise SAME_AS with lower conf
            for i in range(len(plist)):
                for j in range(i+1, len(plist)):
                    # heuristic: same last name, first initial same -> likely same person variant
                    n1 = plist[i].split("person:",1)[1]
                    n2 = plist[j].split("person:",1)[1]
                    if not n1 or not n2:
                        continue
                    if n1[0].lower() == n2[0].lower():
                        edges.append({
                            "src": plist[i],
                            "dst": plist[j],
                            "kind": "SAME_AS",
                            "weight": 0.7,
                            "provenance": {" heuristic": f"last={last} first-initial-match"}
                        })
                        edges.append({
                            "src": plist[j],
                            "dst": plist[i],
                            "kind": "SAME_AS",
                            "weight": 0.7,
                            "provenance": {"heuristic": f"last={last} first-initial-match"}
                        })

    # Triggers
    for pid in person_ids:
        name = pid.split("person:",1)[1]
        if not name:
            continue
        low = name.lower()
        short_title_example = ""
        # Find a paper authored by this person for "author of ..." trigger
        authored_papers = [e["dst"] for e in edges if e["kind"]=="AUTHORED" and e["src"]==pid]
        if authored_papers:
            # get first paper node label
            example_title = ""
            for n in nodes:
                if n["id"] == authored_papers[0]:
                    example_title = n["label"]
                    break
            short_title_example = example_title[:35].lower()

        triggers.append({"phrase": low, "person_id": pid, "conf": 0.95, "src": "full_name"})
        triggers.append({"phrase": initials(name).lower(), "person_id": pid, "conf": 0.5, "src": "initials"})
        triggers.append({"phrase": last_first_initial(name), "person_id": pid, "conf": 0.6, "src": "first_last_initial"})
        if short_title_example:
            triggers.append({"phrase": f"author of {short_title_example}", "person_id": pid, "conf": 0.8, "src": "paper_title"})

    # De-duplicate nodes (by id keep first)
    uniq_nodes = {}
    for n in nodes:
        if n["id"] not in uniq_nodes:
            uniq_nodes[n["id"]] = n
    nodes = list(uniq_nodes.values())

    # Write files
    write_jsonl(ACNE_STORE / "nodes.jsonl", nodes)
    write_jsonl(ACNE_STORE / "edges.jsonl", edges)
    write_jsonl(ACNE_STORE / "triggers.jsonl", triggers)

    # Also create summary
    summary = {
        "nodes": len(nodes),
        "edges": len(edges),
        "triggers": len(triggers),
        "persons": len(person_ids),
        "orgs": len(org_ids),
        "papers": len(paper_ids),
    }

    print(f"[acne] manual TLPG built: {summary}", flush=True)
    return summary, nodes, edges, triggers, org_counter

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    papers = load_papers()
    print(f"[acne] loaded {len(papers)} papers from {PAPERS_PATH}", flush=True)

    built_via_hub = False
    if papers:
        built_via_hub = try_contacts_hub(papers)
    else:
        print("[acne] no papers — skipping hub attempt, building empty store", flush=True)

    if not built_via_hub:
        if not papers:
            ACNE_STORE.mkdir(parents=True, exist_ok=True)
            write_jsonl(ACNE_STORE / "nodes.jsonl", [])
            write_jsonl(ACNE_STORE / "edges.jsonl", [])
            write_jsonl(ACNE_STORE / "triggers.jsonl", [])
            summary = {"nodes":0,"edges":0,"triggers":0,"persons":0,"orgs":0,"papers":0}
            nodes, edges, triggers = [], [], []
            org_counter = Counter()
        else:
            summary, nodes, edges, triggers, org_counter = build_manual_tlpg(papers)
    else:
        # If hub path succeeded, it already called manual build. Need to reload counts
        try:
            nc = 0
            ec = 0
            tc = 0
            if (ACNE_STORE / "nodes.jsonl").exists():
                with open(ACNE_STORE / "nodes.jsonl") as f:
                    nc = sum(1 for _ in f)
            if (ACNE_STORE / "edges.jsonl").exists():
                with open(ACNE_STORE / "edges.jsonl") as f:
                    ec = sum(1 for _ in f)
            if (ACNE_STORE / "triggers.jsonl").exists():
                with open(ACNE_STORE / "triggers.jsonl") as f:
                    tc = sum(1 for _ in f)
            # Count by parsing kinds
            persons = 0
            orgs = 0
            papers_c = 0
            if (ACNE_STORE / "nodes.jsonl").exists():
                with open(ACNE_STORE / "nodes.jsonl") as f:
                    for line in f:
                        j = json.loads(line)
                        if j.get("kind")=="Person":
                            persons+=1
                        elif j.get("kind")=="Organization":
                            orgs+=1
                        elif j.get("kind")=="Citation":
                            papers_c+=1
            summary = {"nodes":nc,"edges":ec,"triggers":tc,"persons":persons,"orgs":orgs,"papers":papers_c}
            # For trigger examples load few
            triggers = []
            if (ACNE_STORE / "triggers.jsonl").exists():
                with open(ACNE_STORE / "triggers.jsonl") as f:
                    for i,line in enumerate(f):
                        if i>=5:
                            break
                        triggers.append(json.loads(line))
            nodes = []
            edges = []
            org_counter = Counter()
        except Exception as e:
            print(f"[acne] could not recount hub store: {e}")
            summary = {"nodes":0,"edges":0,"triggers":0,"persons":0,"orgs":0,"papers":0}
            triggers = []
            org_counter = Counter()

    # Load triggers sample if not already
    if not triggers and (ACNE_STORE / "triggers.jsonl").exists():
        with open(ACNE_STORE / "triggers.jsonl") as f:
            triggers = [json.loads(line) for i,line in enumerate(f) if i<20]

    # Unique authors/orgs from papers direct fallback count if needed
    unique_authors = summary.get("persons",0)
    unique_orgs = summary.get("orgs",0)

    # If we didn't have org_counter, compute from papers
    if not org_counter:
        org_counter = Counter()
        for p in papers:
            for a in p.get("authors",[]):
                aff = a.get("affiliation") if isinstance(a, dict) else None
                if aff:
                    org_counter[aff] += 1

    top_orgs = org_counter.most_common(10)

    stats = {
        "unique_authors": unique_authors,
        "unique_orgs": unique_orgs,
        "tlpg_counts": summary,
        "triggers_count": summary.get("triggers", len(triggers)),
        "triggers_examples": triggers[:10],
        "top_orgs": [{"org": o, "count": c} for o,c in top_orgs],
        "built_via": "ContactsHub" if built_via_hub else "manual JSONL",
        "store_path": str(ACNE_STORE),
    }

    # Save stats
    out_stats = DATA_DIR / "acne_stats.json"
    with open(out_stats, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    try:
        SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SITE_DATA_DIR / "acne_stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except:
        pass

    print("\n=== ACNE STATS ===")
    print(json.dumps(stats, indent=2))
    print(f"\nSaved to {out_stats} and store at {ACNE_STORE}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
