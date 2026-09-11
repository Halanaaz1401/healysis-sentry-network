# Healysis — UI Specification

## Brand
Healysis

## Palette
- Obsidian: `#020617` / `#090d16`
- Surface: `#0f172a` / `#1e293b`
- Cyan: `#06b6d4`
- Sky: `#38bdf8`
- Critical: `#ef4444` / `#f43f5e`
- Warning: `#f59e0b`
- Safe: `#10b981` / `#22c55e`
- White: `#f8fafc`
- Muted: `#94a3b8`

## Principle
**Operational command center, not generic AI dashboard.**

Avoid:
- excessive gradients
- decorative AI graphics
- meaningless chat UI
- giant empty hero sections
- template-looking dashboards

Use:
- dense but readable information hierarchy
- tables
- evidence panels
- maps where useful
- risk states
- timeline views
- clear actions

## Seven core screens
1. `/dashboard` — Executive command center
2. `/facilities` — State/district/facility intelligence
3. `/resources` — Medicine + beds + personnel
4. `/forecasts` — Demand forecasting + stock-out prediction
5. `/recommendations` — Redistribution + approval
6. `/advisor` — Grounded Gemini advisor
7. `/audit` — Integrity + anomaly investigation + action history

## Shared shell
- Healysis logo
- navigation
- role
- backend health
- alert count
- session control

## Severity
- red = critical
- amber = warning
- green = safe
- cyan = information/action

Every screen answers:
**What is happening? Why does it matter? What can I do?**
