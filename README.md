# AI Dreams — Personal Data Synthesis Engine

**Your data. Your patterns. Your insights. No corporation sees it.**

A synthesis engine that ingests your exported digital life and distills it into navigable kernels of meaning — surfacing patterns, unfinished business, and cross-source connections with full provenance back to the raw data.

Built for [The Data Portability Hackathon](https://trapezoidal-shake-91a.notion.site/The-Data-Portability-Hackathon-30e0743dff2c81c58434f79d754a05ae) — Track 3: Personal Data, Personal Value.

**[Live Demo](https://dreamai.solutions/)**

<!-- TODO: replace with Nanobanana infographic -->

## Architecture

<img width="1376" height="768" alt="Gemini_Generated_Image_xoc13wxoc13wxoc1" src="https://github.com/user-attachments/assets/81c99e62-c502-40a1-b70b-aaf3edb2e35b" />

**95% of computation runs locally.** The only cloud step is a single Claude API call for final synthesis (~15K tokens). All raw data stays on your machine.

## Quick Start

```bash
# Clone
git clone https://github.com/symbolic01/ai-dreams.git
cd ai-dreams

# Dependencies
pip install anthropic   # only needed for sutra synthesis
# Ollama must be running locally: https://ollama.ai
ollama pull qwen2.5:7b

# Set up API key OR use Claude Code CLI fallback (for synthesis step only)
export ANTHROPIC_API_KEY=sk-ant-...   # option A: direct API
# option B: if Claude Code is installed, synthesis falls back to `claude --print` automatically

# Run the full pipeline on a persona
python pipeline.py all --persona p05

# Or run individual stages
python pipeline.py merge --persona p05       # merge data sources → timeline
python pipeline.py extract --persona p05     # extract kernels (Ollama)
python pipeline.py synthesize --persona p05  # synthesize sutras (Claude API)
python pipeline.py report --persona p05      # generate report data JSON
```

Then open `report.html` in a browser — it loads `output/p05_report_data.json` automatically.

## How It Works

### Pipeline Stages

| Stage | Model | What it does | Cost |
|-------|-------|-------------|------|
| **Timeline Merge** | Python (no LLM) | Merges 7 data sources into one chronological stream | Free |
| **Kernel Extraction** | Qwen 2.5 7B (Ollama) | Processes 20-entry sliding windows, extracts typed insight kernels with source refs | Free (local) |
| **Sutra Synthesis** | Claude Sonnet (API) | Compresses kernels into ranked sutras organized by theme | ~15K tokens/persona |
| **Report Generation** | Template (no LLM) | Assembles JSON from all pipeline artifacts for the interactive UI | Free |

### Kernel Types

Each kernel is a typed insight extracted from raw data entries:

- **truth** — a factual pattern or stable reality
- **learning** — growth, skill development, mindset shift
- **urgent** — something that needs attention now
- **question** — an unresolved decision they're wrestling with
- **pattern** — recurring behavior, especially cross-source
- **unfinished** — something started but not completed
- **empathy** — an emotional state that deserves acknowledgment

### Provenance Chain

Every sutra traces back to its evidence:

```
Sutra (ranked insight)
  └── Kernel (typed observation + source_refs)
        └── Raw Entry (original data with timestamp, source, tags)
```

The report UI makes this chain navigable — click any sutra to see its backing kernels, click any kernel to see the raw entries that support it. Nothing is a black box.

### Cross-Source Detection

The most valuable insights emerge at intersections between data sources:

- **Spending + stress**: transaction spikes correlated with lifelog anxiety entries
- **Social vs reality**: public posts versus private conversations
- **Calendar + avoidance**: scheduled tasks that never got completed

The sutra synthesis prompt explicitly targets these cross-source patterns and flags contradictions between stated goals and actual behavior.

## Personas

Pipeline tested on all 5 hackathon personas (2,641 total entries → 1,071 kernels → 51 sutras):

| Persona | Age | Role | Entries | Kernels | Sutras |
|---------|-----|------|---------|---------|--------|
| **Jordan Lee** (p01) | 32 | Senior Product Manager | 530 | 215 | 10 |
| **Maya Patel** (p02) | 26 | Medical Resident | 528 | 218 | 10 |
| **Darius Webb** (p03) | 41 | Founder & CEO | 528 | 210 | 10 |
| **Sunita Rajan** (p04) | 58 | Chemistry Teacher | 527 | 219 | 12 |
| **Theo Nakamura** (p05) | 23 | Freelance Designer | 528 | 209 | 9 |

Each persona surfaces unique themes — from Darius's "Revenue-Cash Flow Paradox" to Maya's "AI as Surrogate Emotional Support" to Theo's revision policy started 6 times and never shipped.

## Tech Stack

- **Python 3** — pipeline orchestrator, data loading, timeline merge
- **Ollama** — local LLM runtime ([ollama.ai](https://ollama.ai))
- **Qwen 2.5 7B** — kernel extraction model (runs on 8GB VRAM)
- **Claude Sonnet** — sutra synthesis via Anthropic API (single call)
- **Vanilla HTML/CSS/JS** — report UI, no framework, no build step

## Datasets

Uses the [hackathon-provided synthetic persona datasets](https://drive.google.com/drive/folders/1MGrww1b3U7Kewlb7f6pKA_aoWYS08f2u) (5 personas). Each persona includes:

- `lifelog.jsonl` — daily activities, moods, observations
- `conversations.jsonl` — AI assistant chat history
- `emails.jsonl` — email threads
- `calendar.jsonl` — scheduled events
- `transactions.jsonl` — financial transactions
- `social_posts.jsonl` — social media posts
- `files_index.jsonl` — documents and files metadata
- `persona_profile.json` — demographics, goals, pain points

Place datasets in `data/Hackathon_Datasets/persona_<id>/` (e.g. `persona_p01` through `persona_p05`).

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...  # For sutra synthesis (optional if Claude Code CLI is installed)
```

Ollama must be running on `localhost:11434` (default).

## Project Structure

```
ai-dreams/
├── pipeline.py              # CLI: merge → extract → synthesize → report
├── index.html               # Dashboard — persona selector
├── report.html              # Interactive report UI (?persona=p01..p05)
├── data/
│   └── Hackathon_Datasets/
│       ├── persona_p01/     # Jordan Lee (7 JSONL + profile JSON)
│       ├── persona_p02/     # Maya Patel
│       ├── persona_p03/     # Darius Webb
│       ├── persona_p04/     # Sunita Rajan
│       └── persona_p05/     # Theo Nakamura
├── output/
│   ├── {id}_timeline.jsonl  # Merged timeline per persona
│   ├── {id}_kernels.json    # Extracted kernels (after dedup)
│   ├── {id}_sutras.json     # Synthesized sutras
│   └── {id}_report_data.json # Combined report data for UI
└── README.md
```

## Vision

AI Dreams is a visible fragment of a larger research program called [Superempathy](https://independent.academia.edu/JayaramaMarks) — the thesis that superintelligence without proportional empathy is incomplete.

<!-- TODO: link to superempathy repo when public -->

This pipeline demonstrates a core capability: turning exported personal data into navigable, provenanced insight with full drill-down from compressed truth back to raw evidence. The person's data tells them something they couldn't see before — and they can verify every claim.

Where this leads:

- **Logarithmic context compaction** — the sutra/kernel/entry hierarchy is a compression scheme. Each layer reduces volume by ~25x while preserving provenance. This generalizes to arbitrary depth: meta-sutras over sutras, life chapters over meta-sutras.
- **Provenance as semantic address space** — every insight has an address chain back to source data. This isn't just auditability — it's a navigable meaning structure that a person (or their agent) can traverse.
- **Graph topologies** — the current pipeline is linear (entries → kernels → sutras). Future iterations explore branching (what-if sutras from the same kernels), self-reflecting cycles (dream loops that re-process their own output), and temporal overlays (how sutras shift across time windows).

The dream: your data doesn't just sit in exports. It becomes a living, navigable structure that helps you see yourself more clearly than any single platform ever could.

## Known Limitations

- **Dedup by ref overlap** — kernels with >50% source ref overlap are merged (keeps longest content, unions refs/tags); very different phrasings from non-overlapping windows may still survive
- **No streaming** — full pipeline runs batch; a production version would stream results as each stage completes
- **Synthetic data** — hackathon datasets are synthetic personas, not real user exports
- **No consent UI** — the pipeline assumes consent (data is already exported); a production version needs explicit consent flow per data source
- **Ollama dependency** — requires local GPU; a hosted fallback would broaden accessibility

## License

MIT

---

Built for the [AITX Data Portability Hackathon](https://trapezoidal-shake-91a.notion.site/The-Data-Portability-Hackathon-30e0743dff2c81c58434f79d754a05ae), March 2026.
