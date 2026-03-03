# Entry point for the FastAPI backend

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import asyncio
import json

from simulation import Simulation

app = FastAPI(title="SkySwarm Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim = Simulation(tick_interval=1.0)


# ---------------------------------------------------------------------------
# WebSocket connections
# ---------------------------------------------------------------------------

ws_clients: List[WebSocket] = []


async def broadcast_state():
    """Broadcast simulation state to all connected WebSocket clients."""
    if not ws_clients:
        return
    state = {
        "flights": sim.get_state(),
        "weather_cells": sim.get_weather_cells(),
        "analytics": _get_analytics_data(),
        "comparison": sim.get_comparison(),
        "tick": sim.tick_count,
    }
    data = json.dumps(state)
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        try:
            ws_clients.remove(ws)
        except ValueError:
            pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        while True:
            # Keep connection alive, also handle incoming messages
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                # Handle client commands via WebSocket
                try:
                    cmd = json.loads(msg)
                    if cmd.get("type") == "spawn":
                        n = cmd.get("n", 5)
                        mode = cmd.get("mode", sim.global_mode)
                        import random
                        keys = list(sim.airports.keys())
                        for _ in range(n):
                            o = random.choice(keys)
                            d = random.choice([k for k in keys if k != o])
                            sim.add_flight(o, d, mode=mode)
                except (json.JSONDecodeError, Exception):
                    pass
            except asyncio.TimeoutError:
                pass
            # Broadcast current state
            await broadcast_state()
    except WebSocketDisconnect:
        try:
            ws_clients.remove(websocket)
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# REST API endpoints (kept for backward compatibility)
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "SkySwarm Backend is running!", "version": "2.0.0"}


@app.post("/api/start")
def api_start():
    sim.start()
    return {"status": "started"}


@app.post("/api/stop")
def api_stop():
    sim.stop()
    return {"status": "stopped"}


@app.post("/api/reset")
def api_reset():
    sim.stop()
    sim.flights.clear()
    sim.weather_cells.clear()
    sim.event_log.clear()
    sim.shutdown_airports.clear()
    # Reset airport capacities
    import random
    for iata in sim.airports:
        sim.airport_capacities[iata] = random.randint(3, 8)
    sim.metrics = {
        "llm_tokens": 0,
        "llm_calls": 0,
        "llm_latency_ms": 0,
        "decisions": 0,
    }
    sim.comparison = {
        "rule": {"total_flights": 0, "emergency_landings": 0, "holds": 0, "reroutes": 0, "avg_fuel_at_arrival": []},
        "llm": {"total_flights": 0, "emergency_landings": 0, "holds": 0, "reroutes": 0, "avg_fuel_at_arrival": []},
    }
    sim.tick_count = 0
    return {"status": "reset"}


@app.post("/api/spawn")
def api_spawn(payload: Dict):
    origin = payload.get('origin', 'SFO')
    dest = payload.get('dest', 'LAX')
    mode = payload.get('mode', 'RULE')
    flight = sim.add_flight(origin, dest, mode=mode)
    return {"flight": flight.to_dict()}


@app.post("/api/spawn_many")
def api_spawn_many(payload: Dict):
    n = int(payload.get('n', 50))
    mode = payload.get('mode', 'RULE')
    created = []
    keys = list(sim.airports.keys())
    if len(keys) < 2:
        return {"created": []}
    import random
    for i in range(n):
        o = random.choice(keys)
        d = random.choice([k for k in keys if k != o])
        f = sim.add_flight(o, d, mode=mode)
        created.append(f.to_dict())
    return {"created": created}


@app.post("/api/inject")
def api_inject(payload: Dict):
    crisis = payload.get('type', 'storm')
    sim.inject_crisis(crisis)
    return {"status": "injected", "type": crisis}


@app.post("/api/weather")
def api_weather(payload: Dict):
    intensity = payload.get('intensity', 50)
    sim.set_weather(intensity)
    return {"status": "updated", "intensity": intensity}


@app.post("/api/congestion")
def api_congestion(payload: Dict):
    multiplier = payload.get('multiplier', 1)
    sim.set_congestion(multiplier)
    return {"status": "updated", "multiplier": multiplier}


@app.post("/api/speed")
def api_speed(payload: Dict):
    speed = payload.get('speed', 1)
    sim.set_speed(speed)
    return {"status": "updated", "speed": speed}


@app.post("/api/mode")
def api_mode(payload: Dict):
    mode = payload.get('mode', 'RULE')
    sim.set_mode(mode)
    return {"status": "updated", "mode": mode}


@app.get("/api/airports")
def api_airports():
    airports = list(sim.airports.values())
    return airports[:500]


@app.get("/api/flights")
def api_flights():
    return sim.get_state()


@app.get("/api/weather_cells")
def api_weather_cells():
    return sim.get_weather_cells()


@app.get("/api/comparison")
def api_comparison():
    return sim.get_comparison()


@app.get("/api/capacities")
def api_capacities():
    return sim.get_capacities()


@app.get("/api/events")
def api_events():
    return sim.event_log[-50:]


def _get_analytics_data():
    flights = sim.get_state()
    total_delays = sum(f.get('delay_score', 0) for f in flights)
    emergency = sum(1 for f in flights if f.get('last_action') == 'EMERGENCY_LAND')
    avg_fuel = (sum(f.get('fuel_level', 0) for f in flights) / len(flights)) if flights else 0
    holding = sum(1 for f in flights if f.get('last_action') == 'HOLD')
    rerouting = sum(1 for f in flights if f.get('last_action') == 'REROUTE')
    personalities = {}
    for f in flights:
        p = f.get('personality', 'Unknown')
        personalities[p] = personalities.get(p, 0) + 1
    return {
        "total_delays": round(total_delays, 1),
        "emergency_landings": emergency,
        "avg_fuel": round(avg_fuel, 1),
        "holding": holding,
        "rerouting": rerouting,
        "active_flights": len(flights),
        "weather_cells": len(sim.weather_cells),
        "metrics": sim.metrics,
        "personalities": personalities,
        "tick": sim.tick_count,
    }


@app.get("/api/analytics")
def api_analytics():
    return _get_analytics_data()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
