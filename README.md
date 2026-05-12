# nfactorial-llm-engineer-course

Code for projects and seminars from the nfactorial **LLM Engineer** online course.

## Structure

```
projects/
  1-movie-agent/          # Project 1: Movie Agent (Киноманьяк)

seminar/
  06-mcp-auto-website/    # Seminar 6: AutoHunt — Car Selling Website
```

---

## Projects

### Project 1 — Movie Agent (Киноманьяк)

An AI-powered movie recommendation agent built with Claude API. Takes user preferences and suggests films with explanations.

---

## Seminars

### Seminar 6 — AutoHunt Car Selling Website (MCP + Agents)

A full-stack car marketplace website built using **Figma MCP** for design reference and **parallel Claude subagents** for frontend/backend generation. Agent templates from [aitmpl.com](https://www.aitmpl.com/) were used.

**Stack:**
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- Backend: Node.js + Express + TypeScript

**Features:**
- Home page with hero, search bar, featured listings, and stats
- Browse page with sidebar filters (make, fuel, transmission, price, year), sorting, and pagination
- Car detail page with image gallery, spec tabs, and contact modal
- Sell a Car — 4-step form with validation
- REST API with 20 seeded car listings, full filter/sort/paginate support

**Run locally:**
```bash
# Backend (port 3001)
cd seminar/06-mcp-auto-website/backend
npm install && npm run dev

# Frontend (port 5173)
cd seminar/06-mcp-auto-website/frontend
npm install && npm run dev
```
