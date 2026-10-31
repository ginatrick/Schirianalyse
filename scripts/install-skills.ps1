# Installiert externe Agent-Skills für Claude Code in .claude/skills
# Ausführen im Projektordner (PowerShell): .\scripts\install-skills.ps1
# Vorher die jeweiligen Repos kurz ansehen.

$ErrorActionPreference = "Stop"

# Immer im Projektordner installieren, egal von wo das Skript gestartet wird
Set-Location (Join-Path $PSScriptRoot "..")

# Supabase: Postgres- und Schema-Best-Practices (MIT)
npx -y skills add supabase/agent-skills --skill supabase-postgres-best-practices --agent claude-code -y

# Vercel: React/Next.js-Performance und UI-Richtlinien (MIT)
npx -y skills add vercel-labs/agent-skills --skill vercel-react-best-practices --agent claude-code -y
npx -y skills add vercel-labs/agent-skills --skill web-design-guidelines --agent claude-code -y

# Anthropic: Web-App per Playwright testen, UI-Gestaltung
npx -y skills add anthropics/skills --skill webapp-testing --agent claude-code -y
npx -y skills add anthropics/skills --skill frontend-design --agent claude-code -y

Write-Host "Fertig. Installierte Skills liegen in .claude/skills"
