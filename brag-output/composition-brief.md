# Hyperframes Composition Brief: BetterU

## Objective
Create a short launch-style brag video for BetterU that tours all seven app screens.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape, 1920x1080, 30fps
- Duration: 24.5s

## Source Material
- Project root: /Users/nihalmrahar/Downloads/BetterU
- Primary files read: README.md, apps/web/index.html, apps/web/src/shell/theme.css, apps/web/src/index.css, site/Landing.tsx, pages/{Today,Alden,Train,Progress,Onboarding}.tsx, components/{Logo,FoodPicker,ProfileForm}.tsx
- Product name: BetterU
- Tagline: "Eat with evidence."
- Key UI to recreate: the Alden chat answer with real USDA numbers and the "Log breakfast" button; the Today metric cards
- Copy that must appear verbatim:
  - Eat with evidence.
  - Your daily targets / kcal / day / How we worked this out
  - Good morning, Nia / 78 g of protein to go today.
  - Ask Alden, or tell it what you ate…
  - Saved only when you tap.
  - Full body, 45 minutes
  - Maintenance calories / from your data
  - Download all your data / Delete your account
  - Start eating with evidence. / Open BetterU, free

## Creative Direction
- Tone preset: app-store
- Creative direction: quiet premium product film for a nutrition app that shows its working
- Angle / hook / outro: see brag-plan.md
- Avoid: generic SaaS language, abstract filler, any founders/team content (user request)

## Visual Identity
- Background (hero): #0a2416; app surface #ffffff, card #f6f8f3, mist #f2f6ec, border #e1e7dc
- Text: #0b140e, muted #5f6b62
- Accent: #4e6b12, leaf #b9e06a; metrics kcal #0a2416, protein #4e6b12, carbs #7aa33a, fat #a3b86c
- Fonts: Geist (UI/display), Archivo (marketing lines), shipped as woff2 in assets/fonts
- Visual references: leaf mark from components/Logo.tsx; Bionis-style metric cards and rounded 16px cards

## Storyboard
Contract: brag-plan.md. Scene cuts at 3.70, 5.80, 8.96, 14.22, 16.34, 18.44, 20.54; end card at 22.65.

## Audio
- Music: happy-beats-business-moves-vol-11-by-ende-dot-app.mp3, bed ~0.55, fade-in 0.3s, fade-out 1.2s at the end
- Cue guidance: strong-cue locks at 1.60 / 8.96 / 22.65; beat grid 6.86/7.38/7.91/8.44 for the Today cards
- Audio-reactive: subtle RMS glow on the hero leaf and end card
- SFX: key ticks under typing, click on Log breakfast, drop on toast, 2–3 soft whooshes on slides, one bell/impact on the end card; low-HF-risk files from sfx-analysis.md
- Audio files copied into composition/assets/

## Hyperframes Instructions
Local creation and render only. `hyperframes check` is the gate. Telemetry disabled for this run (HYPERFRAMES_NO_TELEMETRY=1).
