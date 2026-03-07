#!/usr/bin/env python3
"""
Personal Data Synthesis Engine — AITX Hackathon
Track 3: Personal Data, Personal Value

Pipeline: raw data → timeline merge → kernel extraction → sutra synthesis → report
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from collections import Counter
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data" / "Hackathon_Datasets"
OUTPUT_DIR = Path(__file__).parent / "output"

# --- Stage 1: Timeline Merge ---

def load_jsonl(path):
    """Load a JSONL file into a list of dicts."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def merge_timeline(persona_id="p05"):
    """Merge all data sources for a persona into a unified chronological timeline."""
    persona_dir = DATA_DIR / f"persona_{persona_id}"

    sources = [
        "lifelog.jsonl",
        "calendar.jsonl",
        "emails.jsonl",
        "social_posts.jsonl",
        "transactions.jsonl",
        "conversations.jsonl",
        "files_index.jsonl",
    ]

    timeline = []
    source_counts = {}

    for source_file in sources:
        path = persona_dir / source_file
        if not path.exists():
            print(f"  [skip] {source_file} not found")
            continue
        entries = load_jsonl(path)
        source_counts[source_file] = len(entries)
        timeline.extend(entries)

    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("ts", ""))

    return timeline, source_counts


def print_timeline_stats(timeline, source_counts):
    """Print validation stats for the merged timeline."""
    print(f"\n{'='*60}")
    print(f"TIMELINE STATS")
    print(f"{'='*60}")
    print(f"Total entries: {len(timeline)}")
    print()

    # Source breakdown
    print("Source breakdown:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source:<25} {count:>4} entries")
    print()

    # Source field distribution
    source_field_counts = Counter(e.get("source", "unknown") for e in timeline)
    print("By 'source' field:")
    for source, count in source_field_counts.most_common():
        print(f"  {source:<25} {count:>4}")
    print()

    # Tag distribution (top 20)
    all_tags = [tag for e in timeline for tag in e.get("tags", [])]
    print(f"Tag distribution (top 20 of {len(set(all_tags))} unique):")
    for tag, count in Counter(all_tags).most_common(20):
        print(f"  {tag:<25} {count:>4}")
    print()

    # Date range
    dates = [e.get("ts", "") for e in timeline if e.get("ts")]
    if dates:
        print(f"Date range: {dates[0][:10]} → {dates[-1][:10]}")

    # Ref field usage
    has_refs = sum(1 for e in timeline if e.get("refs"))
    print(f"Entries with refs: {has_refs}/{len(timeline)}")
    print()


def save_timeline(timeline, persona_id="p05"):
    """Save merged timeline to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{persona_id}_timeline.jsonl"
    with open(out_path, "w") as f:
        for entry in timeline:
            f.write(json.dumps(entry) + "\n")
    print(f"Saved: {out_path} ({len(timeline)} entries)")
    return out_path


# --- Stage 2: Kernel Extraction (Ollama) ---

KERNEL_SYSTEM_PROMPT = """You are a personal data analyst. You extract meaningful kernels from a person's life data.

A kernel is a typed insight extracted from raw data entries. Each kernel has:
- type: one of [truth, learning, urgent, question, pattern, unfinished, empathy]
- content: a concise insight (1-2 sentences)
- source_refs: list of entry IDs that support this kernel
- tags: relevant topic tags

Kernel types:
- truth: A factual pattern or stable reality about this person's life
- learning: Growth, skill development, or mindset shift
- urgent: Something that needs attention or is time-sensitive
- question: An unresolved question or decision they're wrestling with
- pattern: A recurring behavior, especially cross-source (spending + stress, social vs reality)
- unfinished: Something they started but didn't complete, or a cycle that was interrupted
- empathy: An emotional state or need that deserves acknowledgment

Rules:
- Extract 3-8 kernels per window of entries
- Focus on NON-OBVIOUS insights — patterns across sources, contradictions, hidden connections
- Always cite source_refs (the entry IDs)
- Prefer cross-source connections over single-source observations
- "Unfinished" kernels are especially valuable — what did they start and not complete?

Output valid JSON array of kernels. No markdown, no explanation — just the JSON array."""

KERNEL_USER_TEMPLATE = """Here are {count} entries from {name}'s personal data timeline. Extract meaningful kernels.

ENTRIES:
{entries}

Output a JSON array of kernels. Each kernel: {{"type": "...", "content": "...", "source_refs": ["id1", "id2"], "tags": ["tag1"]}}"""


def window_timeline(timeline, window_size=20, overlap=5):
    """Split timeline into overlapping windows for kernel extraction."""
    windows = []
    i = 0
    while i < len(timeline):
        window = timeline[i:i + window_size]
        windows.append(window)
        i += window_size - overlap
    return windows


def format_entries_for_prompt(entries):
    """Format timeline entries as compact text for the LLM prompt."""
    lines = []
    for e in entries:
        tags_str = ", ".join(e.get("tags", []))
        lines.append(f'[{e["id"]}] {e["ts"][:10]} ({e["source"]}) [{tags_str}] {e["text"][:200]}')
    return "\n".join(lines)


def extract_kernels_ollama(window, persona_name="Theo Nakamura", model="qwen2.5:7b"):
    """Extract kernels from a window of timeline entries using Ollama."""
    entries_text = format_entries_for_prompt(window)
    user_prompt = KERNEL_USER_TEMPLATE.format(
        count=len(window),
        name=persona_name,
        entries=entries_text,
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": KERNEL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
        "format": "json",
    }

    result = subprocess.run(
        ["curl", "-s", "http://localhost:11434/api/chat", "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=120,
    )

    response = json.loads(result.stdout)
    content = response.get("message", {}).get("content", "")

    # Parse kernels from response
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            for key in ("kernels", "results", "data", "items", "output"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            if "type" in parsed and "content" in parsed:
                return [parsed]
            print(f"  [warn] Dict keys: {list(parsed.keys())}")
            return []
        else:
            print(f"  [warn] Unexpected response shape: {type(parsed)}")
            return []
    except json.JSONDecodeError as e:
        print(f"  [error] JSON parse failed: {e}")
        print(f"  Content: {content[:200]}")
        return []


def run_kernel_extraction(timeline, persona_name="Theo Nakamura", model="qwen2.5:7b"):
    """Run kernel extraction across all timeline windows."""
    windows = window_timeline(timeline, window_size=20, overlap=5)
    print(f"\nExtracting kernels from {len(windows)} windows (model: {model})...")

    all_kernels = []
    for i, window in enumerate(windows):
        print(f"  Window {i+1}/{len(windows)} ({window[0]['ts'][:10]} → {window[-1]['ts'][:10]})...", end=" ")
        kernels = extract_kernels_ollama(window, persona_name, model)
        print(f"{len(kernels)} kernels")
        all_kernels.extend(kernels)

    # Deduplicate by content similarity (exact match for now)
    seen = set()
    unique_kernels = []
    for k in all_kernels:
        key = k.get("content", "").strip().lower()
        if key not in seen:
            seen.add(key)
            unique_kernels.append(k)

    print(f"\nTotal: {len(all_kernels)} raw → {len(unique_kernels)} unique kernels")
    return unique_kernels


def save_kernels(kernels, persona_id="p05"):
    """Save extracted kernels to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{persona_id}_kernels.json"
    with open(out_path, "w") as f:
        json.dump(kernels, f, indent=2)
    print(f"Saved: {out_path} ({len(kernels)} kernels)")
    return out_path


def print_kernel_stats(kernels):
    """Print kernel extraction stats."""
    print(f"\n{'='*60}")
    print(f"KERNEL STATS")
    print(f"{'='*60}")
    print(f"Total kernels: {len(kernels)}")

    type_counts = Counter(k.get("type", "unknown") for k in kernels)
    print("\nBy type:")
    for ktype, count in type_counts.most_common():
        print(f"  {ktype:<20} {count:>4}")

    all_tags = [tag for k in kernels for tag in k.get("tags", [])]
    print(f"\nTop tags ({len(set(all_tags))} unique):")
    for tag, count in Counter(all_tags).most_common(10):
        print(f"  {tag:<20} {count:>4}")

    # Count cross-source kernels (refs from multiple sources)
    cross_source = sum(1 for k in kernels if len(set(
        r.split("_")[0] for r in k.get("source_refs", []) if "_" in r
    )) > 1)
    print(f"\nCross-source kernels: {cross_source}/{len(kernels)}")


# --- Stage 3: Sutra Synthesis (Claude API) ---

SUTRA_SYSTEM_PROMPT = """You are a personal insight synthesizer. You take extracted kernels from someone's life data and compress them into sutras — maximally dense, actionable insights.

A sutra is:
- A concise, human-readable truth (1-2 sentences)
- Backed by multiple kernels (cite their indices)
- Organized by theme
- Ranked by importance (how much would this insight change the person's life if they truly internalized it?)

You also identify:
- CROSS-SOURCE PATTERNS: insights that only emerge when combining data from different sources (spending + stress, social posts vs private reality, calendar vs lifelog)
- UNFINISHED BUSINESS: things that were started but not completed, decisions avoided, cycles interrupted
- CONTRADICTIONS: where the person's behavior in one domain conflicts with their stated goals in another

Output valid JSON with this structure:
{
  "themes": [
    {
      "name": "theme name",
      "sutras": [
        {
          "text": "the insight",
          "importance": 1-10,
          "kernel_indices": [0, 5, 12],
          "cross_source": true/false,
          "category": "pattern|truth|urgent|unfinished|contradiction|growth"
        }
      ]
    }
  ],
  "top_insights": ["the 3 most important things this person needs to hear"],
  "unfinished_business": ["list of incomplete cycles"],
  "data_story": "2-3 sentence narrative of this person's arc over the time period"
}"""

SUTRA_USER_TEMPLATE = """Here are {count} kernels extracted from {name}'s personal data spanning {date_range}.

{name}'s profile: {age} year old {job} in {location}.
Goals: {goals}
Pain points: {pain_points}

KERNELS:
{kernels}

Synthesize these into themed sutras. Focus on NON-OBVIOUS cross-source patterns and unfinished business. Be specific — use names, numbers, and dates from the kernels."""


def synthesize_sutras_claude(kernels, persona_profile, timeline):
    """Synthesize kernels into sutras using Claude API or claude --print fallback."""
    kernel_lines = []
    for i, k in enumerate(kernels):
        refs = ", ".join(k.get("source_refs", []))
        tags = ", ".join(k.get("tags", []))
        kernel_lines.append(f"[{i}] ({k.get('type', '?')}) {k.get('content', '')} [refs: {refs}] [tags: {tags}]")

    dates = [e.get("ts", "")[:10] for e in timeline if e.get("ts")]
    date_range = f"{dates[0]} to {dates[-1]}" if dates else "unknown"

    user_prompt = SUTRA_USER_TEMPLATE.format(
        count=len(kernels),
        name=persona_profile.get("name", "Unknown"),
        date_range=date_range,
        age=persona_profile.get("age", "?"),
        job=persona_profile.get("job", "?"),
        location=persona_profile.get("location", "?"),
        goals="; ".join(persona_profile.get("goals", [])),
        pain_points="; ".join(persona_profile.get("pain_points", [])),
        kernels="\n".join(kernel_lines),
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic()
        print(f"  Calling Claude API (sonnet) with {len(kernels)} kernels...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SUTRA_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = response.content[0].text
    else:
        print(f"  Using claude --print fallback ({len(kernels)} kernels)...")
        full_prompt = SUTRA_SYSTEM_PROMPT + "\n\n" + user_prompt + "\n\nRespond with ONLY valid JSON, no markdown fences."
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            ["claude", "--print", "--model", "claude-sonnet-4-20250514"],
            input=full_prompt, env=env,
            capture_output=True, text=True, timeout=180,
        )
        content = result.stdout.strip()
        if result.returncode != 0:
            print(f"  [error] claude --print exit code {result.returncode}")
            print(f"  stderr: {result.stderr[:300]}")

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  [error] JSON parse failed: {e}")
        print(f"  Content: {content[:500]}")
        return None


def save_sutras(sutras, persona_id="p05"):
    """Save synthesized sutras to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{persona_id}_sutras.json"
    with open(out_path, "w") as f:
        json.dump(sutras, f, indent=2)
    print(f"Saved: {out_path}")
    return out_path


def print_sutra_summary(sutras):
    """Print sutra synthesis summary."""
    if not sutras:
        print("No sutras generated.")
        return

    print(f"\n{'='*60}")
    print(f"SUTRA SYNTHESIS")
    print(f"{'='*60}")
    print(f"\nData story: {sutras.get('data_story', 'N/A')}")
    print(f"\nTop insights:")
    for i, insight in enumerate(sutras.get("top_insights", []), 1):
        print(f"  {i}. {insight}")
    print(f"\nUnfinished business:")
    for item in sutras.get("unfinished_business", []):
        print(f"  - {item}")
    themes = sutras.get("themes", [])
    print(f"\n{len(themes)} themes:")
    for theme in themes:
        sutra_count = len(theme.get("sutras", []))
        cross = sum(1 for s in theme.get("sutras", []) if s.get("cross_source"))
        print(f"  [{theme.get('name', '?')}] {sutra_count} sutras ({cross} cross-source)")
        for s in theme.get("sutras", [])[:3]:
            print(f"    {'*' if s.get('cross_source') else ' '} ({s.get('importance', '?')}/10) {s.get('text', '')}")


# --- Stage 4: Report Data ---

def generate_report_data(persona_id="p05"):
    """Generate JSON data file for the HTML report."""
    profile_path = DATA_DIR / f"persona_{persona_id}" / "persona_profile.json"
    timeline_path = OUTPUT_DIR / f"{persona_id}_timeline.jsonl"
    kernels_path = OUTPUT_DIR / f"{persona_id}_kernels.json"
    sutras_path = OUTPUT_DIR / f"{persona_id}_sutras.json"

    profile = json.loads(profile_path.read_text())
    timeline = load_jsonl(str(timeline_path))
    kernels = json.load(open(kernels_path))
    sutras = json.load(open(sutras_path))

    report_data = {
        "profile": profile,
        "sutras": sutras,
        "kernels": kernels,
        "timeline_entries": timeline,
        "generated": datetime.now().isoformat(),
    }

    data_path = OUTPUT_DIR / f"{persona_id}_report_data.json"
    with open(data_path, "w") as f:
        json.dump(report_data, f)
    print(f"Saved report data: {data_path}")
    return data_path


# --- CLI ---

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Personal Data Synthesis Pipeline")
    parser.add_argument("stage", choices=["merge", "extract", "synthesize", "report", "all"],
                        help="Pipeline stage to run")
    parser.add_argument("--persona", default="p05", help="Persona ID (default: p05)")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model for extraction")
    parser.add_argument("--test", action="store_true", help="Test mode: only first 2 windows")
    args = parser.parse_args()

    profile_path = DATA_DIR / f"persona_{args.persona}" / "persona_profile.json"
    if profile_path.exists():
        profile = json.loads(profile_path.read_text())
        persona_name = profile.get("name", f"Persona {args.persona}")
    else:
        profile = {}
        persona_name = f"Persona {args.persona}"

    print(f"Pipeline: persona={args.persona} ({persona_name})")

    if args.stage in ("merge", "all"):
        timeline, source_counts = merge_timeline(args.persona)
        print_timeline_stats(timeline, source_counts)
        save_timeline(timeline, args.persona)

    if args.stage in ("extract", "all"):
        timeline_path = OUTPUT_DIR / f"{args.persona}_timeline.jsonl"
        if args.stage == "extract":
            timeline = load_jsonl(str(timeline_path))
            print(f"Loaded timeline: {len(timeline)} entries")
        if args.test:
            print("[TEST MODE] Using first 40 entries only")
            timeline = timeline[:40]
        kernels = run_kernel_extraction(timeline, persona_name, args.model)
        print_kernel_stats(kernels)
        save_kernels(kernels, args.persona)

    if args.stage in ("synthesize", "all"):
        timeline_path = OUTPUT_DIR / f"{args.persona}_timeline.jsonl"
        kernels_path = OUTPUT_DIR / f"{args.persona}_kernels.json"
        if args.stage == "synthesize":
            timeline = load_jsonl(str(timeline_path))
            kernels = json.load(open(kernels_path))
            print(f"Loaded: {len(timeline)} entries, {len(kernels)} kernels")
        sutras = synthesize_sutras_claude(kernels, profile, timeline)
        if sutras:
            print_sutra_summary(sutras)
            save_sutras(sutras, args.persona)

    if args.stage in ("report", "all"):
        generate_report_data(args.persona)


if __name__ == "__main__":
    main()
