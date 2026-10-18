<div align="center">

# BetterU

### Your nutrition, fitness, and wellness companion

Personalized guidance powered by nutrition data, deterministic calculations,
retrieval-augmented AI, and practical workout planning.

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Frontend-Vanilla%20JS-F7DF1E?style=for-the-badge&logo=javascript&logoColor=111827" alt="Vanilla JavaScript">
  <img src="https://img.shields.io/badge/Vector%20DB-Pinecone-8B5CF6?style=for-the-badge" alt="Pinecone">
</p>

<p>
  <a href="#-features">Features</a> ·
  <a href="#-quick-start">Quick start</a> ·
  <a href="#-api-reference">API reference</a> ·
  <a href="#-project-structure">Project structure</a>
</p>

</div>

---

## ✨ What is BetterU?

BetterU is a full-stack nutrition and fitness assistant built around **Alden**,
an AI coach that helps users make more informed decisions about food, health,
and training.

Use BetterU to:

- Ask nutrition questions and compare foods
- Calculate BMI, BMR, TDEE, calorie targets, and macros
- Search USDA FoodData Central
- Generate structured workout plans
- Get recipe-video suggestions
- Save profile notes and workout progress in the browser

> **Built for:** students, athletes, beginners, and anyone working toward a
> healthier routine.

## 🚀 Features

| Area | What it does |
| --- | --- |
| **Alden chat** | Streams personalized nutrition answers using retrieved food data and user context |
| **Nutrition calculator** | Calculates BMI, BMR, TDEE, calorie targets, and macros deterministically |
| **Food search** | Looks up structured nutrient information from USDA FoodData Central |
| **Workout builder** | Combines wger exercises with AI-generated plans tailored to the user |
| **Recipe videos** | Surfaces optional YouTube recipe suggestions from chat |
| **Personal profile** | Stores profile details, notes, and workout progress locally in the browser |

## 🧭 How it works

```text
┌──────────────┐      ┌────────────────┐      ┌─────────────────────┐
│  HTML / CSS  │ ───► │    FastAPI     │ ───► │  Groq / Cerebras    │
│  Vanilla JS  │      │    Backend     │      │  AI responses       │
└──────────────┘      └───────┬────────┘      └─────────────────────┘
                              │
                  ┌───────────┴───────────┐
                  │                       │
           ┌──────▼──────┐        ┌───────▼────────┐
           │   Pinecone  │        │ USDA / wger /  │
           │  Food data  │        │ Tavily / YouTube│
           └─────────────┘        └────────────────┘
```

The backend uses `all-MiniLM-L6-v2` embeddings with Pinecone retrieval. The
nutrition calculator remains deterministic and does not rely on an AI model.

## ⚡ Quick start

### 1. Clone the project

```bash
git clone <repository-url>
cd BetterU
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows
```

### 3. Install dependencies

```bash
pip install -r Backend/requirements.txt
```

### 4. Configure environment variables

Create `Backend/.env`:

```dotenv
GROQ_API_KEY=...
CEREBRAS_API_KEY=...
PINECONE_API_KEY=...
TAVILY_API_KEY=...
USDA_API_KEY=...
YOUTUBE_API_KEY=...
```

The Pinecone index must be named `betteru-data`. Keep `.env` private; it is
ignored by Git and must never be committed.

### 5. Start the API

```bash
cd Backend
python -m uvicorn app:app --reload
```

The API will be available at **http://127.0.0.1:8000**.

## 🌐 Run the frontend

The API serves the main chat and profile pages:

| Page | URL |
| --- | --- |
| Alden chat | [127.0.0.1:8000](http://127.0.0.1:8000/) |
| Profile | [127.0.0.1:8000/profile](http://127.0.0.1:8000/profile) |
| API docs | [127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |

To serve the static landing, About, Team, and Workout pages:

```bash
python -m http.server 5500 --directory Frontend
```

Open [127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html). The static
frontend expects the API at `http://127.0.0.1:8000`.

## 📡 API reference

| Method | Endpoint | Description |
| :---: | --- | --- |
| `GET` | `/` | Serve the Alden chat page |
| `GET` | `/profile` | Serve the profile page |
| `POST` | `/chat` | Stream nutrition chat responses |
| `POST` | `/alden` | Stream calculator and profile coaching responses |
| `POST` | `/calculate` | Calculate nutrition targets |
| `POST` | `/food` | Search USDA FoodData Central |
| `POST` | `/workout/generate` | Generate a structured workout plan |
| `GET` | `/health` | Check API and Pinecone status |

## 🗂️ Project structure

```text
BetterU/
├── Backend/
│   ├── app.py              # FastAPI application and API routes
│   ├── calculator.py      # Pure nutrition calculations
│   ├── calculator_tool.py # Calculator wrapper used by the API
│   ├── injest.py          # Optional Pinecone knowledge-base ingestion
│   ├── nodes.py           # Alden prompts and intent helpers
│   └── requirements.txt
├── Frontend/
│   ├── index.html         # Landing page
│   ├── chat.html          # Alden nutrition chat
│   ├── profile.html       # Profile and nutrition targets
│   ├── workout.html       # Workout-plan viewer
│   ├── about.html
│   ├── team.html
│   └── assets/
└── .gitignore
```

## 🧠 Optional knowledge-base ingestion

`Backend/injest.py` can add USDA, Health Canada, and other source material to
the `betteru-data` Pinecone index:

```bash
cd Backend
python injest.py
```

Ingestion downloads source archives into `Backend/raw_downloads/` and writes
`Backend/ingestion.log`. These local runtime artifacts are excluded from Git.

## 🛠️ Development notes

- Python **3.10+** is recommended.
- Sentence Transformers downloads `all-MiniLM-L6-v2` on first start and caches
  it locally.
- Nutrition calculations live in `Backend/calculator.py` and are deterministic.
- Cross-origin requests are enabled so the static frontend can call the API.
- Do not commit `.env`, downloaded datasets, model caches, logs, or bytecode.

---

<div align="center">

Made with intention for better everyday choices.

</div>
