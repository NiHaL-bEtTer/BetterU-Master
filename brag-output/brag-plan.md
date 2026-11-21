# Brag Plan: BetterU

## What is this app?
A nutrition, fitness and wellness companion: track food against targets set for your body, train with a plan built for your equipment, and ask Alden, a coach whose numbers come from USDA data, not from the language model.

## The angle
"Eat with evidence." The project's own tagline is the spine. Every scene is a real BetterU screen doing its job, and every number on screen is a real one from the project (the landing page's USDA demo: 2 large eggs + a slice of whole-wheat toast = 240 kcal against a sample 1,650 kcal target). The user asked for **all features**, so this is a fast tour through all seven screens in app order: Onboarding → Today → Alden → Log → Train → Progress → Me. Alden gets the longest hold because it's the most impressive.

**Exclusion (user request):** no founders, team, "Meet the team" or ALDEN-acronym content anywhere.

## Hook (0–3.7s)
Forest-green ground. The leaf mark lands on the first strong beat (1.60s), then **"Eat with evidence."** blurs in word by word, with "BetterU" small underneath. It looks premium and calm, and it's specific because it's the product's own line.

## Key moments
- **Targets with the working shown**: "Your daily targets" with 1,650 kcal / day counting up, and the "How we worked this out" line (Mifflin–St Jeor).
- **Today dashboard**: "Good morning, Nia", with the four metric cards (Calories, Protein, Carbohydrate, Fat) arriving one by one.
- **Alden does the maths** (centerpiece): the user types "I had 2 eggs and a slice of toast for breakfast". Alden answers with 240 kcal plus the macros, a "USDA FoodData Central" source chip, and a **Log breakfast** button that gets tapped. Then the toast "Saved only when you tap."
- **Log**: search "greek yogurt", results drop in, and a barcode lookup chip.
- **Train**: "Full body, 45 minutes", set rows, "Beat last time", and a rest timer ticking.
- **Progress**: the weight trend line draws, and "Maintenance calories, from your data".
- **Me**: "Download all your data" / "Delete your account".

## Outro / punchline
Source names slide by (USDA FoodData Central · MedlinePlus · World Health Organization · Health Canada · Open Food Facts). Then the BetterU wordmark with **"Start eating with evidence."** and the CTA pill **"Open BetterU, free"**. It holds for 2s or more.

## User flow worth showing
Set targets (onboarding) → tell Alden what you ate → one tap logs it → see the day on Today. Alden is the key action, Today and Progress are the result.

## Tone
- Preset: `app-store`
- Creative direction: "quiet premium product film for a nutrition app that shows its working"
- Interpretation: clean feature cards in the app's own design system, smooth slides and a morph-like card handoff, no jokes, confident holds on the numbers.

## Format: landscape, 1920×1080, 30fps
## Duration: 24.5s (scenes cut on the track's strong cues; at the top of the 15–25 window because the user asked for all seven features)

## Visual identity (from the project: apps/web/src/shell/theme.css, index.css, index.html)
- Hero ground: brand forest `#0a2416` (canopy `#12351f`)
- App surfaces: `#ffffff` background, card `#f6f8f3`, mist `#f2f6ec`, border `#e1e7dc`
- Text: `#0b140e`, muted `#5f6b62`
- Accent: avocado `#4e6b12`; highlight leaf `#b9e06a`; metric colours: kcal `#0a2416`, protein `#4e6b12`, carbs `#7aa33a`, fat `#a3b86c`
- Display/UI font: Geist (dashboard); marketing font: Archivo (index.html loads it from Google Fonts)
- Strongest visual element: the leaf mark (`components/Logo.tsx`) and the metric cards / calorie ring in the Bionis-style dashboard

## Share copy (draft)
BetterU: tell Alden what you ate and get the real numbers from USDA data, with one tap to log it. Targets, training and progress included. Eat with evidence.

## Audio direction
- Role: warm bed with sparse, motion-matched UI accents
- Music: `happy-beats-business-moves-vol-11-by-ende-dot-app.mp3` (bundled, 114.84 BPM)
- Music treatment: starts at 0 at full bed level (~0.55), short fade-in, fade out over the last 1.2s under the end card
- Music cue guidance (preset `cues/happy-beats-business-moves-vol-11…music-cues.md`), beat ≈ 0.522s:
  - Strong-cue locks: **1.60s** leaf mark lands; **8.96s** cut into Alden; **22.65s** end-card wordmark
  - Scene cuts on strong beats/bars: 3.70, 5.80, 8.96, 14.22, 16.34, 18.44, 20.54, 22.65
  - Beat-grid window for the Today metric cards: 6.86 / 7.38 / 7.91 / 8.44 (non-reading cards; values hold until the cut)
- Audio-reactive treatment: subtle. The hero leaf's glow and the end-card glow breathe with music RMS. No waveforms.
- SFX posture: sparse and motion-matched. Soft key ticks under the typed Alden message, a click on "Log breakfast", a soft drop when the toast lands, a gentle whoosh on two or three scene slides, one resonant hit on the end card.
- Restraint rule: no sound on every card, and no harsh or high-frequency repeats.

## Storyboard

> **As built (supersedes the order below; Today greets "Nihal" at the user's request):** Hook 0–3.70 → Onboarding 3.70–5.80 → **Alden 5.80–11.06** → **Today 11.06–14.22** (shows the breakfast Alden just logged; cards on beats 11.60/12.12/12.65/13.18) → Log 14.22–16.34 → Train 16.34–18.44 → Progress & Me 18.44–20.54 → Outro 20.54–25.00 (wordmark beat-locked at 22.65). Today was moved after Alden so the numbers follow the story. The invented "Breakfast logged" toast was dropped; the button turning into "Logged ✓" carries the tap.

### Scene 1: Hook, 0.00–3.70 (3.7s)
Forest ground with a soft radial glow. The leaf mark scales in and lands at 1.60. "Eat with evidence." blurs in word by word, then holds at least 1.5s. "BetterU" sits small under it.
Sequential/interaction: words one by one.
Audio intent: the bed opens; one soft hit on the leaf landing.
Transition mood: the forest ground slides up to reveal the white app surface → Scene 2.

### Scene 2: Onboarding targets, 3.70–5.80 (2.1s)
Card "Your daily targets": **1,650** counts up, then "kcal / day", plus a line under it: "How we worked this out: Resting burn (BMR, Mifflin–St Jeor) × activity factor = maintenance (TDEE)". Small feature label: "Onboarding".
Sequential/interaction: count-up.
Transition mood: clean slide → Scene 3.

### Scene 3: Today, 5.80–8.96 (3.2s)
"Good morning, Nihal" (name requested by the user) and "78 g of protein to go today." Four metric cards arrive on the beat grid: Calories eaten, Protein, Carbohydrate, Fat, with real metric colours. Label: "Today".
Sequential/interaction: 4 cards one by one.
Transition mood: cards slide out and the chat panel slides in → Scene 4.

### Scene 4: Alden, 8.96–14.22 (5.3s): centerpiece
Chat UI. The input "Ask Alden, or tell it what you ate…" types "I had 2 eggs and a slice of toast for breakfast" and is sent. Alden's reply card shows **240 kcal**, then the macro rows Protein 16.9 g, Carbohydrate 16.6 g, Fat 11.3 g, a source chip "USDA FoodData Central", and a **Log breakfast** button. The cursor taps it, and the toast "Saved only when you tap." appears. Label: "Alden".
Sequential/interaction: typing, the reply building, then a simulated tap.
Audio: key ticks, a click, a soft drop.
Transition mood: slide → Scene 5.

### Scene 5: Log, 14.22–16.34 (2.1s)
Search box "Search foods, e.g. greek yogurt" types "greek yogurt"; three result rows drop in (illustrative USDA-style names); chip "Packaged food? Look it up by barcode". Label: "Log · 13,600 USDA foods".
Transition mood: slide → Scene 6.

### Scene 6: Train, 16.34–18.44 (2.1s)
Plan header "Full body, 45 minutes"; two set rows with a "Beat last time" badge; rest timer ticking 1:30 → 1:28. Label: "Train · 870+ exercises".
Transition mood: slide → Scene 7.

### Scene 7: Progress + Me, 18.44–20.54 (2.1s)
Weight trend line draws (7-day average); "Maintenance calories, from your data". Beside it a small Me card: "Download all your data" / "Delete your account". Labels: "Progress", "Me".
Transition mood: dip back to forest → Scene 8.

### Scene 8: Sources → End card, 20.54–24.50 (4.0s)
The source names slide by once (20.54–22.4). The wordmark lands at 22.65: leaf + "BetterU", then "Start eating with evidence." and the CTA pill "Open BetterU, free". It holds to the end and the music fades.
Audio: one resonant hit at 22.65.

**Music mood for this video:** upbeat, warm, clean
**Audio summary:** a bright bed from frame 0, small UI sounds only where something is clicked, typed or lands, one hit on the end card, and a fade under the CTA.

## Privacy note
All on-screen people and data are placeholders. "Nia" and the eggs-and-toast demo come from the landing page's sample, not from the database. No real user rows, keys, hostnames or founder content.

## Voiceover script
Voice: ElevenLabs "Laurel - Warm, Kind & Confident" (eleven_v4), requested by the user in place of the default Kokoro voice. Lines are placed on their scenes; music ducks under the voice.

| Scene | Line |
|---|---|
| Hook | Every number, with a source. |
| Onboarding | Targets built for your body, with the maths shown. |
| Alden | Tell Alden what you ate. It finds the real numbers, cites them, and logs only when you tap. |
| Today | Your whole day, at a glance. |
| Log | Search thousands of foods. |
| Train | Train with the kit you've got. |
| Progress & Me | And learn what your body really burns. |
| End card | BetterU. Eat with evidence. |
