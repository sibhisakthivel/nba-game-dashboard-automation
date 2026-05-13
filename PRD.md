# Dimer Viz — Product Requirements Document

**Version:** 0.1  
**Status:** In Development  
**Last updated:** May 2026

---

## Overview

Dimer Viz is an NBA analytics and prop research platform built for sharp bettors, casual bettors, and NBA fans who want data-driven insight into player performance. Inspired by tools like Outlier Bet, the goal is a personalized, visually polished research experience that makes it fast and intuitive to analyze any player across any stat type.

---

## Target Users

- **Sharp bettors** — need quick access to hit rates, contextual splits, and matchup data to make informed prop decisions
- **Casual bettors** — want a clean, easy-to-navigate UI that surfaces the most relevant data without friction
- **NBA fans** — interested in player trends and performance patterns beyond standard box scores

---

## Current State (v0.1)

### Features shipped
- Player selection by team with prop line input
- Per-game scoring bar chart with prop line overlay and teammate absence markers
- Hit-rate summary table with splits: home/away, win/loss, defensive tier, team scoring thresholds
- Team matchup comparison charts (points scored vs. points allowed by condition)
- Teammate injury filtering — isolate and compare games where selected teammates were absent
- Supabase PostgreSQL backend with SQLAlchemy data access, TTL caching, and SQL-side filtering

### Tech stack
- Frontend: Streamlit
- Database: Supabase (PostgreSQL via connection pooler)
- Data access: SQLAlchemy + psycopg2
- Visualization: Matplotlib
- Language: Python 3.11

### Known limitations
- Points props only — no other stat types
- Manual data pipeline (local ingestion → CSV export → Supabase upload)
- Streamlit UI limits frontend polish and deployment flexibility
- No live or automated data updates
- Single-user, local deployment only

---

## MVP Scope

The MVP transforms Dimer Viz from a personal points-only tool into a deployable, multi-stat research platform with a polished frontend and automated data infrastructure.

---

### 1. Expanded Stat Types

**Goal:** Support all commonly bet NBA player props, not just points.

**Stat types to add:**
- Rebounds (total, offensive, defensive)
- Assists
- Three-pointers made
- Steals
- Blocks
- Turnovers
- Points + Rebounds + Assists (PRA)
- Points + Rebounds (PR)
- Points + Assists (PA)

**Requirements:**
- Stat selector UI — fast switching between stat types without page reload feel
- All existing hit-rate splits and filters apply to every stat type
- Chart labels, axis scaling, and prop line logic adapt dynamically to the selected stat

---

### 2. Frontend Overhaul

**Goal:** Replace Streamlit with a modern, visually polished frontend that looks and feels like a real product.

**Requirements:**
- Migrate from Streamlit to a React frontend
- FastAPI or equivalent Python backend serving data via REST API
- Clean, dark-mode-first design aesthetic (reference: Outlier Bet, PrizePicks)
- Player/stat/filter selection via intuitive UI components (dropdowns, toggles, chips)
- Charts rendered with a modern library (Recharts, Plotly, or D3)
- Responsive layout — usable on desktop and tablet
- Fast render — no full-page reloads on filter changes

---

### 3. Filter UX Enhancements

**Goal:** Make filtering fast, flexible, and overlappable.

**Filters to support:**
- Home / Away
- Win / Loss
- Last N games (5, 10, 15, 20, season)
- Opponent defensive tier (top 10, middle 10, bottom 10)
- Games with / without specific teammates
- Month / part of season
- Back-to-back games

**Requirements:**
- Filters are chips or toggles — one click to apply, one click to remove
- Multiple filters can be active simultaneously
- Hit-rate and chart update instantly on filter change
- Active filters are clearly visible at all times
- "Clear all filters" option always accessible

---

### 4. Automated Data Pipeline

**Goal:** Eliminate manual CSV export/upload workflow. Data should update automatically on a schedule.

**Current workflow (to replace):**
Local ingestion script → CSV export → manual Supabase upload

**Target workflow:**
Scheduled ingestion script → direct write to Supabase (no CSVs)

**Requirements:**
- Ingestion script writes directly to Supabase via SQLAlchemy or Supabase client
- Pipeline runs on a schedule (post-game nightly, or morning-of for same-day data)
- Basic error alerting if ingestion fails
- No manual steps required for routine data updates

---

### 5. Deployment to AWS

**Goal:** Move from local-only to a live, shareable deployment.

**Requirements:**
- Application hosted on AWS (EC2, ECS, or Elastic Beanstalk)
- Database remains on Supabase (no migration needed for MVP)
- Automated data pipeline runs on AWS (Lambda + EventBridge scheduler, or ECS task)
- Environment variables and secrets managed via AWS Secrets Manager or Parameter Store
- HTTPS via AWS Certificate Manager + CloudFront or ALB
- CI/CD pipeline for deployments (GitHub Actions → AWS)
- Live URL suitable for resume and portfolio

---

## Post-MVP Features (Backlog)

These are features worth building after the MVP is stable and deployed:

- **Line movement tracking** — show how the prop line has moved and flag sharp action
- **Comp player overlays** — plot two players on the same chart for quick comparison
- **Trend indicators** — surface hot/cold streaks automatically
- **Player search** — search any player directly rather than navigating by team
- **Bookmarks / watchlist** — save player/stat combos for quick access
- **Game log table** — full scrollable game log alongside the chart
- **Defensive matchup grades** — per-position defensive ratings for the opposing team
- **Push notifications / alerts** — notify when a player hits a streak threshold
- **Multi-sport expansion** — NFL, MLB props using the same platform architecture

---

## Technical Roadmap

| Phase | Focus | Status |
|---|---|---|
| 0 | Security, repo cleanup, codebase consolidation | ✅ Complete |
| 1 | Expanded stat types + filter UX (Streamlit) | 🔲 Next |
| 2 | React frontend + FastAPI backend | 🔲 Planned |
| 3 | Automated data pipeline | 🔲 Planned |
| 4 | AWS deployment + CI/CD | 🔲 Planned |
| 5 | Post-MVP feature buildout | 🔲 Backlog |

---

## Out of Scope (MVP)

- Real-time in-game data
- User accounts or authentication
- Mobile native app
- Paid tier or monetization
- Social or sharing features