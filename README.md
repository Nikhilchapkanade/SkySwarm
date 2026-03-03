# 🛰 SkySwarm — AI-Powered Air Traffic Simulator

<div align="center">

**Real-time 3D air traffic simulation with LLM-powered autonomous flight agents**

Built with **FastAPI** · **Agno Framework** · **Ollama** · **React** · **globe.gl** · **Three.js**

</div>

---


https://github.com/user-attachments/assets/24a99509-d689-44c4-bbcb-51e1b1dc95cd


## ✨ Features

### 🌍 3D Globe Visualization
- Real-time animated flight arcs on a photorealistic night-mode Earth
- Animated dashed arcs with color-coded modes (teal for RULE, red for LLM)
- Weather cell ring visualization showing moving storm systems
- Action-colored ✈ icons (green=continue, orange=hold, magenta=reroute, red=emergency)
- Interactive airport labels with shutdown indicators

### 🧠 Agentic AI System
- **Dual Decision Engine**: Toggle between rule-based and LLM-powered flight decisions
- **Agno + Ollama**: Each flight queries a local LLM via the Agno framework
- **Agent Personalities**: 5 pilot archetypes (Cautious, Balanced, Aggressive, Veteran, Rookie) with different risk tolerances
- **Multi-Agent Negotiation**: Flights approaching the same airport negotiate landing slots
- **Chain-of-Thought**: Full step-by-step reasoning display for every decision
- **Decision History Timeline**: Scrollable timeline of all decisions per flight

### ⚡ Crisis System
7 injectable crisis types that affect live flights:
| Crisis | Effect |
|--------|--------|
| 🌩 Severe Storm | Spawns moving weather cells, increases weather risk |
| 🌋 Volcanic Ash | Creates large, slow-moving ash cloud |
| 🚫 Airport Shutdown | Closes a random airport (capacity → 0) |
| ⛽ Fuel Shortage | Reduces fuel levels across all flights |
| 📡 ATC Strike | Massive congestion spike + delays |
| ☀ Solar Flare | Weather + congestion disruption |
| 🔒 Airspace Closure | Congestion + delay increase |

### 📊 Advanced Analytics
- Real-time flight statistics (fuel, delays, emergencies)
- 🎭 Personality distribution across active flights
- ⚖ RULE vs LLM comparison (emergency landings, holds, reroutes, avg fuel at arrival)
- 🧠 LLM metrics (tokens, latency, calls)
- 📋 Live event log

### 🏗 Architecture
- **WebSocket** real-time state broadcasting
- **Airport Capacity System** with gates/runway limits
- **Moving Weather Cells** that travel across the globe and dissipate
- **Distance-based fuel burn** rates
- **Position trails** for flight path tracking

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Ollama** (optional, for LLM mode) — [Download](https://ollama.com/)

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python main.py
```
Backend runs on **http://localhost:8000**

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on **http://localhost:5174**

### LLM Mode (Optional)
```bash
ollama run llama3.2
```
Then toggle to **LLM** mode in the Control Center.

---

## 🏛 Architecture

```
┌─────────────┐    REST/WS     ┌──────────────────┐    Agno    ┌──────────┐
│   React +   │ ◄────────────► │   FastAPI +       │ ◄────────►│  Ollama  │
│   globe.gl  │                │   Simulation      │           │ (llama3) │
│   Three.js  │                │   Engine          │           └──────────┘
└─────────────┘                └──────────────────┘
     Frontend                       Backend                    LLM Layer
```

---

## 📁 Project Structure

```
SkySwarm/
├── backend/
│   ├── main.py               # FastAPI + WebSocket server
│   ├── simulation.py          # Simulation engine + weather cells
│   ├── agents.py              # FlightAgent + Agno/Ollama + negotiation
│   ├── openflights_loader.py  # Airport/route data loader
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main layout
│   │   ├── Globe.jsx          # 3D globe + arcs + weather rings
│   │   ├── ControlPanel.jsx   # Simulation controls
│   │   ├── FlightInfoPanel.jsx # Agent thoughts + decision timeline
│   │   ├── api.js             # API helpers
│   │   ├── main.jsx           # React entry
│   │   └── styles.css         # Dark theme + animations
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + Vite | UI framework |
| 3D Globe | globe.gl + Three.js | Earth visualization |
| Backend | Python + FastAPI | REST API + WebSocket |
| AI Framework | Agno | Agent orchestration |
| LLM | Ollama (llama3.2) | Local inference |
| Data | OpenFlights | Airport/route data |

---

## 📜 License

MIT
