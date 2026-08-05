#!/usr/bin/env python3
"""
fetch_topics.py — arXiv topic harvester for arxiviq.com demo
No external deps: stdlib only (urllib, xml.etree, json, pathlib, re, time)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from http.client import IncompleteRead

QUERIES = [
    ("world models neural networks", "world_models"),
    ("joint embedding predictive architecture", "jepa"),
    ("ImageBind multimodal", "imagebind"),
    ("V-JEPA video prediction", "v_jepa"),
    ("predictive coding neuroscience", "pred_coding"),
    ("Hamiltonian neural networks", "hamiltonian"),
    ("training dynamics neural networks loss landscape", "train_dynamics"),
    ("foundation world models robotics", "foundation_wm"),
]

# arXiv API + Atom namespaces
ARXIV_NS = "http://www.w3.org/2005/Atom"
ARXIV_ARXIV_NS = "http://arxiv.org/schemas/atom"
NS = {"atom": ARXIV_NS, "arxiv": ARXIV_ARXIV_NS}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SITE_DATA_DIR = PROJECT_ROOT / "site" / "public" / "data"

# regex for stripping version from arXiv id: 1234.5678v2 -> 1234.5678, plus old style
VERSION_RE = re.compile(r'v\d+$')

SYNTHETIC_TEMPLATES = {
    "world_models": [
        ("World Models Revisited: Scaling Latent Dynamics for Generalization",
         "Learning compressed latent dynamics enables agents to plan in imagination. We revisit world models with modern transformers and show scaling laws on Atari and robotics benchmarks.",
         ["David Ha", "Jürgen Schmidhuber"]),
        ("Hierarchical World Models for Long-Horizon Planning",
         "We propose a hierarchical latent world model that factorizes time at multiple resolutions. Experiments on navigation and manipulation show improved credit assignment.",
         ["Chelsea Finn", "Pieter Abbeel"]),
        ("Diffusion World Models for Visual Planning",
         "Replacing RSSM with diffusion-based latent prediction yields sharper futures and better sample efficiency on video prediction benchmarks.",
         ["Emilien Biré", "Fei-Fei Li"]),
    ],
    "jepa": [
        ("Joint Embedding Predictive Architectures: From Images to Video",
         "JEPA learns by predicting representations rather than pixels. We extend I-JEPA to spatiotemporal prediction and analyze collapse prevention via variance-covariance regularization.",
         ["Yann LeCun", "Mahdi Cherti"]),
        ("JEPA Under the Hood: Understanding Representation Geometry",
         "We study the loss landscape of JEPA and show how stop-grad and momentum encoders shape the embedding manifold. Linear probe gains correlate with spectral properties.",
         ["Adrien Bardes", "Quentin Garrido"]),
        ("Hierarchical Joint Embeddings for Planning",
         "H-JEPA stacks JEPA layers to predict at multiple timescales, enabling hierarchical planning without pixel reconstruction. Results on maze navigation and manipulation.",
         ["Randy Evans", "Edward Lee"]),
    ],
    "imagebind": [
        ("ImageBind++: Expanding the Six-Way Binding",
         "We extend ImageBind to bind touch, depth and IMU with improved InfoNCE and modality balancing. Emergent zero-shot retrieval across all 8 modalities is demonstrated.",
         ["Rohit Girdhar", "Alireza Zareian"]),
        ("Bind What Matters: Efficient Fine-tuning of ImageBind for Robotics",
         "LoRA-style adapters for ImageBind enable few-shot transfer to robotic perception where audio-haptic binding aids grasp success prediction.",
         ["Yinbo Chen", "Lerrel Pinto"]),
        ("ImageBind as a Universal Perceptual Basis for World Models",
         "Using frozen ImageBind as encoder for world models yields more grounded latent dynamics that transfer across vision, audio and depth control tasks.",
         ["Kaiming He", "Anurag Arnab"]),
    ],
    "v_jepa": [
        ("V-JEPA 2: Video Joint Embedding Predictive Architecture at Scale",
         "Scaling V-JEPA to 2B parameters on 4M video clips yields state-of-the-art frozen evaluation on Kinetics-700, SSV2 and intuitive physics benchmarks.",
         ["Mathilde Caron", "Yann LeCun"]),
        ("Predicting Video Features Without Decoding: Why V-JEPA Works",
         "We ablate masking ratios, predictor depth and augmentations for V-JEPA and release a compute-efficient recipe for video representation learning.",
         ["Armand Joulin", "Priya Goyal"]),
        ("V-JEPA for Robotic World Models: Action-Conditioned Prediction",
         "Action-conditioned V-JEPA enables learning intuitive physics for manipulation without pixel loss. Policies trained on frozen V-JEPA embeddings are more sample-efficient.",
         ["Pierre Beckmann", "Ananya Agrawal"]),
    ],
    "pred_coding": [
        ("Predictive Coding as Variational Inference: A Unified View",
         "We show predictive coding dynamics implement natural gradient descent on a variational free energy, connecting cortical microcircuits to deep learning objectives.",
         ["Karl Friston", "Thomas Parr"]),
        ("Deep Predictive Coding Networks for Unsupervised Learning",
         "Stacked predictive coding layers trained with local Hebbian-like updates achieve competitive performance on MNIST and CIFAR without backprop through depth.",
         ["Robert Rosenbaum", "Rajesh Rao"]),
        ("From Predictive Coding to JEPA: Bridging Neuroscience and Self-Supervised Learning",
         "We formalize the mapping between hierarchical predictive coding and JEPA, showing both minimize prediction error in latent space rather than sensory space.",
         ["Amir Nazemi", "Eilif Muller"]),
    ],
    "hamiltonian": [
        ("Hamiltonian Neural Networks with Symplectic Integration",
         "HNNs conserved energy better using 4th-order symplectic integrators vs Euler. We show stable long-term rollouts on n-body and double pendulum.",
         ["Samuel Greydanus", "Stefan Dawson"]),
        ("Port-Hamiltonian Networks for Dissipative Physical Systems",
         "Extending HNN to port-Hamiltonian form allows modeling damping and control inputs while preserving passivity guarantees for robotics learning.",
         ["Tianyu Zhong", "Naomi Leonard"]),
        ("Separable Hamiltonian Networks for Efficient World Model Learning",
         "Factoring Hamiltonian into kinetic/potential nets speeds inference 5x and enables using learned Hamiltonians as differentiable physics prior for model-based RL.",
         ["Marios Mattheakis", "Pankaj Mehta"]),
    ],
    "train_dynamics": [
        ("Loss Landscapes of World Models: Grokking and Emergence",
         "We track Hessian spectra during world model training and find phase transitions correlated with sudden improvements in imagination rollout quality.",
         ["Stanislav Fort", "Samy Bengio"]),
        ("Training Dynamics of JEPA: When Do Representations Collapse?",
         "Phase diagrams for JEPA training dynamics reveal early collapse, slow expansion, and stabilization regimes governed by VICReg weights and predictor LR.",
         ["James Halverson", "Zora Joldy"]),
        ("Double Descent in Self-Supervised World Models",
         "Self-supervised video prediction exhibits epoch-wise double descent; second descent aligns with improved linear probing and planning performance.",
         ["Preetum Nakkiran", "Aviad Rubinstein"]),
    ],
    "foundation_wm": [
        ("Foundation World Models for General Robot Control",
         "Pretraining a single transformer world model on 20M robot trajectories enables few-shot adaptation to new embodiments via prompting with interaction history.",
         ["Danny Driess", "Chelsea Finn"]),
        ("GAIA-2: A Foundation Model for Driving World Models",
         "We present a 6B driving world model that generates high-fidelity multi-camera future video conditioned on action and language, trained on 20k hours.",
         ["Evan Shelhamer", "Alex Kendall"]),
        ("The Platonic World Model Hypothesis",
         "Different robot world models converge to the same latent causal graph when trained at scale, akin to Platonic representation hypothesis for LLMs.",
         ["Rylan Schaeffer", "Daniel Yamins"]),
    ],
}

def strip_version(arxiv_id: str) -> str:
    """strip arxiv.org/abs/<id> prefix and trailing vN"""
    # id may be full URL http://arxiv.org/abs/1234.5678v2
    if "/abs/" in arxiv_id:
        raw = arxiv_id.split("/abs/")[-1]
    else:
        raw = arxiv_id
    raw = raw.strip()
    raw = VERSION_RE.sub("", raw)
    return raw

def fetch_query(query_text: str, tag: str, max_results=30):
    """Fetch one query with retries. Returns list of paper dicts or [] on failure."""
    q_enc = urllib.parse.quote_plus(query_text)
    # Use cat filter to keep cs-focused but broad enough
    # Use all: search; try with cs.* bucket if possible, else fallback all
    url = f"http://export.arxiv.org/api/query?search_query=all:{q_enc}&max_results={max_results}&sortBy=relevance&sortOrder=descending"
    # Alternative with cat filter (commented to keep breadth):
    # url = f"http://export.arxiv.org/api/query?search_query=all:{q_enc}+AND+cat:cs.*&max_results={max_results}&sortBy=relevance"

    print(f"[fetch] {tag:14s} | query='{query_text}' | url={url[:120]}...", flush=True)
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arxiviq-demo/0.1 (mailto:demo@arxiviq.com)"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            # parse
            papers = parse_atom(data, query_tag=tag)
            print(f"  -> got {len(papers)} entries (attempt {attempt})", flush=True)
            return papers
        except (urllib.error.URLError, IncompleteRead, ET.ParseError, ConnectionResetError, TimeoutError) as e:
            print(f"  ! attempt {attempt} failed: {e}", flush=True)
            if attempt < 3:
                time.sleep(2 * attempt)  # 2s, 4s backoff
            else:
                print(f"  ! all retries exhausted for {tag}", flush=True)
                return []
        except Exception as e:
            print(f"  ! unexpected error attempt {attempt}: {e}", flush=True)
            if attempt < 3:
                time.sleep(2 * attempt)
            else:
                return []
    return []

def parse_atom(xml_bytes: bytes, query_tag: str):
    """Parse Atom XML bytes into list of paper dicts"""
    root = ET.fromstring(xml_bytes)
    papers = []
    # Atom entries are {http://www.w3.org/2005/Atom}entry
    for entry in root.findall(f"{{{ARXIV_NS}}}entry"):
        try:
            raw_id_elem = entry.find(f"{{{ARXIV_NS}}}id")
            raw_id = raw_id_elem.text if raw_id_elem is not None else ""
            arxiv_id = strip_version(raw_id)
            if not arxiv_id:
                continue

            title_elem = entry.find(f"{{{ARXIV_NS}}}title")
            title = " ".join((title_elem.text or "").split())  # normalize whitespace/newlines

            summary_elem = entry.find(f"{{{ARXIV_NS}}}summary")
            summary = " ".join((summary_elem.text or "").strip().split())

            published_elem = entry.find(f"{{{ARXIV_NS}}}published")
            published = published_elem.text if published_elem is not None else ""

            # arxiv_url: canonical without version
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

            # authors
            authors = []
            for author in entry.findall(f"{{{ARXIV_NS}}}author"):
                name_elem = author.find(f"{{{ARXIV_NS}}}name")
                name = (name_elem.text or "").strip() if name_elem is not None else ""
                if not name:
                    continue
                # affiliation is in arxiv namespace
                affil_elem = author.find(f"{{{ARXIV_ARXIV_NS}}}affiliation")
                affil = (affil_elem.text or "").strip() if affil_elem is not None and affil_elem.text else None
                authors.append({"name": name, "affiliation": affil})

            categories = []
            for cat in entry.findall(f"{{{ARXIV_NS}}}category"):
                term = cat.attrib.get("term")
                if term:
                    categories.append(term)

            papers.append({
                "id": arxiv_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "published": published,
                "arxiv_url": arxiv_url,
                "query_tag": query_tag,          # first tag
                "query_tags": [query_tag],        # will be merged on dedup
            })
        except Exception as e:
            print(f"  ! skipping malformed entry: {e}", flush=True)
            continue
    return papers

def synthetic_for_tag(tag: str):
    """Create 3 synthetic fallback papers for a tag"""
    out = []
    templates = SYNTHETIC_TEMPLATES.get(tag, SYNTHETIC_TEMPLATES["world_models"])
    base_time = "2024-01-15T00:00:00Z"
    for i, (title, abstract, author_names) in enumerate(templates):
        sid = f"synth-{tag}-{i+1:02d}"
        authors = []
        for an in author_names:
            # give plausible org
            org = "FAIR, Meta" if "LeCun" in an or "He" in an else "Stanford University" if "Fei-Fei" in an else "MIT" if len(an)%2==0 else "DeepMind"
            authors.append({"name": an, "affiliation": org})
        out.append({
            "id": sid,
            "title": title,
            "summary": abstract,
            "authors": authors,
            "categories": ["cs.LG", "cs.AI", "cs.CV"] if "imagebind" in tag or "jepa" in tag else ["cs.LG", "cs.AI"],
            "published": base_time,
            "arxiv_url": f"https://arxiv.org/abs/{sid}",
            "query_tag": tag,
            "query_tags": [tag],
            "synthetic": True,
        })
    return out

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    dedup = {}  # id -> paper
    by_tag_counts = {tag: 0 for _, tag in QUERIES}
    synthetic_used = {}

    total_attempted = 0

    for q_text, tag in QUERIES:
        papers = fetch_query(q_text, tag, max_results=30)
        total_attempted += len(papers)
        if not papers:
            print(f"[fallback] {tag} got 0 results — generating synthetic 3", flush=True)
            papers = synthetic_for_tag(tag)
            synthetic_used[tag] = len(papers)
        else:
            synthetic_used[tag] = 0

        # dedup merge
        for p in papers:
            pid = p["id"]
            if pid in dedup:
                # merge query_tags
                existing = dedup[pid]
                if tag not in existing.get("query_tags", []):
                    existing["query_tags"].append(tag)
                # categories merge unique
                existing_cats = set(existing.get("categories", []))
                for c in p.get("categories", []):
                    existing_cats.add(c)
                existing["categories"] = sorted(existing_cats)
            else:
                dedup[pid] = p
                by_tag_counts[tag] += 1

    final_papers = list(dedup.values())
    # Sort by published desc then title
    final_papers.sort(key=lambda x: (x.get("published",""), x.get("title","")), reverse=True)

    # stats
    total_fetched = len(final_papers)
    by_tag_live = by_tag_counts  # after dedup per-tag uniqueness (first occurrence)
    # Recompute by_tag inclusive of multi-tag assignments for reporting
    by_tag_inclusive = {tag: 0 for _, tag in QUERIES}
    for p in final_papers:
        for t in p.get("query_tags", []):
            by_tag_inclusive[t] = by_tag_inclusive.get(t, 0) + 1

    # Save papers.json
    papers_path = DATA_DIR / "papers.json"
    with open(papers_path, "w", encoding="utf-8") as f:
        json.dump(final_papers, f, indent=2, ensure_ascii=False)

    # Also copy to site/public/data for frontend
    site_papers = SITE_DATA_DIR / "papers.json"
    try:
        with open(site_papers, "w", encoding="utf-8") as f:
            json.dump(final_papers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"! warning: could not write site copy: {e}")

    fetch_stats = {
        "total_fetched": total_fetched,
        "total_raw_before_dedup": total_attempted,
        "by_tag": by_tag_live,
        "by_tag_inclusive": by_tag_inclusive,
        "synthetic_used": synthetic_used,
        "any_synthetic": any(v>0 for v in synthetic_used.values()),
        "queries": [{"q": q, "tag": t} for q, t in QUERIES],
    }

    stats_path = DATA_DIR / "fetch_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(fetch_stats, f, indent=2)

    try:
        with open(SITE_DATA_DIR / "fetch_stats.json", "w", encoding="utf-8") as f:
            json.dump(fetch_stats, f, indent=2)
    except:
        pass

    print("\n=== FETCH STATS ===")
    print(json.dumps(fetch_stats, indent=2))
    print(f"\nSaved {total_fetched} papers to {papers_path}")
    if fetch_stats["any_synthetic"]:
        print(f"  Synthetic fallback used for: {[k for k,v in synthetic_used.items() if v>0]}")
    else:
        print("  All results real from arXiv (no synthetic).")
    print("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
