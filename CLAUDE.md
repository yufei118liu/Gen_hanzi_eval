# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **Hanzi Generation Evaluation UI** — a Streamlit web app for crowdsourced human evaluation of machine-generated Chinese characters. It is the evaluation frontend for the paper "Generatively Modeling the Hanzi". Users compare 230 pairs of generated characters in pairwise A/B tests, and votes are stored in Google Sheets.

This repo is the evaluation companion to the main model codebase at `~/hanzi/`.

## Agent Behavior & Commit Rules

**CRITICAL RULES FOR EXECUTION:**
1. **Plan First:** Always operate in plan mode first before implementing any code changes. Outline what files you will touch and what changes you will make.
2. **Manual Check:** Always pause for manual review and explicit approval after proposing a plan, before writing any code.
3. **Commit Protocol:** Always ask for the exact commit message before committing. Do NOT include "Claude" as the author or co-author, and NEVER leave any commit message or description other than the exact text provided.
4. **No execution unless asked:** Your job is to write the code. Do not execute unless explicitly asked.

## Common Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the app:**
```bash
streamlit run app.py
```

## Architecture

Single-file Streamlit application (`app.py`, ~170 lines).

### Data flow
1. User clicks "Start Experiment" on welcome screen
2. Image pairs loaded from numbered folders in `samples/` (0–229)
3. User votes: Option A, Option B, or Neither
4. Votes buffered in `st.session_state.votes_buffer`
5. Buffer syncs to Google Sheets every 20 votes (rate limit protection)
6. Final sync on completion, then success screen with balloons

### Key files
- `app.py` — entire application (UI, state management, Google Sheets sync)
- `samples/` — 230 numbered subdirectories, each containing 2 PNG images (`a_*` and `b_*`)
- `samples/pairing_metadata.json` — statistical metadata (quality buckets, log-prob distributions, transitivity triples)
- `perfect_example_*.png`, `rendered_example_*.png` — reference images shown on welcome screen
- `requirements.txt` — dependencies: `streamlit`, `st-gsheets-connection`, `pandas`

### Configuration
- Google Sheets connection configured via `.streamlit/secrets.toml` (not committed)
- Requires `connections.gsheets.spreadsheet` secret pointing to the target spreadsheet URL

## Key Conventions

- Session state keys: `user_id`, `current_idx`, `votes_buffer`, `started`
- User IDs are 8-char UUID prefixes, generated per session
- Image filenames encode metadata: `{a|b}_{id}_logprob{value}_depth{n}_{components}.png`
- Pairs sorted by natural numeric order of folder names
- `conn.read()` uses `ttl=0` to avoid stale cached data
- Vote records include: `user_id`, `pair_id`, `winner` (filename or "Neither"), `timestamp`
