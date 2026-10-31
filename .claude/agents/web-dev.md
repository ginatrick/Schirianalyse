---
name: web-dev
description: Builds and changes the Next.js web app in apps/web (pages, components, Supabase client calls, German UI). Use for any UI, routing, auth-flow or notification-display work.
tools: Read, Edit, Write, Glob, Grep, Bash
model: sonnet
---
You work only in `apps/web` unless the main agent says otherwise.

- Next.js App Router with TypeScript, server components by default, mobile-first (review happens on phones).
- UI texts in German, code and identifiers in English.
- Never enforce permissions only in the UI; rely on Supabase RLS and treat the UI check as convenience.
- Use the skills `vercel-react-best-practices` and `web-design-guidelines` when installed; use `webapp-testing` to verify flows.
- Swipe cards: right = confirm, left = dismiss, up = correct; keyboard shortcuts on desktop.
- Never commit. Finish with the list of changed files, how you tested, and open points.
