# Healysis Design System Tokens

Extracted from existing Healysis design assets, CSS variables, and components.

## 1. Color Palette

### Primary & Brand Colors
- **Deep Navy (Primary Brand):** `#0C2B4E` (Header, Primary Buttons, Main Headings)
- **Teal / Slate Accent (Secondary Brand):** `#1D546C` (Subheaders, Active Accents, Monogram Icon)
- **Navy Hover State:** `#1A3D64`

### Surface & Backgrounds
- **App Background:** `#F4F4F4` (Light grey neutral background)
- **Card / Module Surface:** `#FFFFFF` (Pure white card containers)
- **Header Background:** `#FFFFFF` with `backdrop-blur-md`
- **Dark Surface:** `#0A0A0A` (Dark mode / monospace badges)

### Status & Severity Colors
- **Safe / Success:**
  - Text: `#047857` (emerald-700)
  - Background: `#ECFDF5` (emerald-50)
  - Border: `#A7F3D0` (emerald-200)
- **Warning:**
  - Text: `#D97706` (amber-600) / `#92400E` (amber-800)
  - Background: `#FFFBEB` (amber-50)
  - Border: `#FDE68A` (amber-200)
- **Critical / Danger:**
  - Text: `#E11D48` (rose-600) / `#9F1239` (rose-800)
  - Background: `#FFF1F2` (rose-50)
  - Border: `#FECDD3` (rose-200)

## 2. Typography & Fonts

- **Sans Font Family:** Geist Sans (`var(--font-geist-sans)`), `-apple-system`, `Arial`, `sans-serif`
- **Mono Font Family:** Geist Mono (`var(--font-geist-mono)`), `monospace`
- **Font Weights:**
  - Normal: `400`
  - Medium: `500`
  - Semibold: `600`
  - Bold: `700`
  - Black: `900` (`font-black`)

## 3. UI Component Tokens

- **Border Radius:** `rounded-lg` (8px), `rounded-xl` (12px), `rounded-full` (9999px)
- **Borders:** `1px solid #E2E8F0` (`border-slate-200`)
- **Shadows:** `shadow-2xs`, `shadow-xs`, `shadow-sm`, `shadow-md`
- **Icon Set:** `@tabler/icons-react` & `lucide-react`
- **Logo Asset:** `/logo.png` & Inline SVG Telemetry Monogram (`#0C2B4E` base with `#1D546C` delta)
