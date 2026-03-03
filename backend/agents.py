"""
Agent layer for SkySwarm using the real Agno framework.

Enhanced with:
- Agent personality (risk tolerance, experience)
- Multi-agent negotiation (landing slot coordination)
- Chain-of-thought reasoning display
- Decision history tracking
"""

import json
import math
import asyncio
import subprocess
import random
from typing import Dict, Any, List

# Lazy imports – only needed when LLM mode is actually used
_Agent = None
_Ollama = None

def _ensure_agno():
    global _Agent, _Ollama
    if _Agent is None:
        from agno.agent import Agent
        from agno.models.ollama import Ollama
        _Agent = Agent
        _Ollama = Ollama


# ---------------------------------------------------------------------------
# Model detection
# ---------------------------------------------------------------------------

def _list_ollama_models() -> List[str]:
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=3)
        lines = out.stdout.splitlines()
        models = [l.split()[0] for l in lines if l.strip()]
        if models and models[0] == "NAME":
            models = models[1:]
        return [m for m in models if "embed" not in m.lower()]
    except Exception:
        return []


def _pick_model() -> str:
    models = _list_ollama_models()
    for candidate in ("llama3.2:latest", "qwen3:4b", "gemma3:4b", "llama3.2", "qwen2.5"):
        if any(candidate in m for m in models):
            return candidate
    return models[0] if models else "llama3.2:latest"


_OLLAMA_MODEL = None

def _get_model():
    global _OLLAMA_MODEL
    if _OLLAMA_MODEL is None:
        _OLLAMA_MODEL = _pick_model()
    return _OLLAMA_MODEL


# ---------------------------------------------------------------------------
# Personality archetypes for agent diversity
# ---------------------------------------------------------------------------

PERSONALITIES = [
    {"name": "Cautious", "risk_tolerance": 0.3, "fuel_threshold": 30, "weather_threshold": 50, "congestion_threshold": 35},
    {"name": "Balanced", "risk_tolerance": 0.5, "fuel_threshold": 20, "weather_threshold": 70, "congestion_threshold": 50},
    {"name": "Aggressive", "risk_tolerance": 0.8, "fuel_threshold": 12, "weather_threshold": 85, "congestion_threshold": 70},
    {"name": "Veteran", "risk_tolerance": 0.6, "fuel_threshold": 15, "weather_threshold": 75, "congestion_threshold": 60},
    {"name": "Rookie", "risk_tolerance": 0.4, "fuel_threshold": 35, "weather_threshold": 45, "congestion_threshold": 30},
]


# ---------------------------------------------------------------------------
# Prompt & parsing
# ---------------------------------------------------------------------------

_DECISION_PROMPT_TEMPLATE = (
    "You are Flight {id}, a {personality} pilot.\n\n"
    "Origin: {origin_name} ({origin_iata})\n"
    "Destination: {dest_name} ({dest_iata})\n"
    "Fuel: {fuel}%\n"
    "Distance remaining: {distance_remaining}%\n"
    "Congestion at destination: {congestion}\n"
    "Weather risk: {weather}%\n"
    "Airport capacity available: {capacity_available}\n"
    "Nearby flights negotiating: {nearby_count}\n"
    "Past decisions: {past_decisions}\n"
    "Past congestion memory: {memory}\n\n"
    "Your risk tolerance is {risk_tolerance} (0=very cautious, 1=very aggressive).\n"
    "You have made {total_decisions} decisions so far this flight.\n\n"
    "Think step-by-step about the best action:\n"
    "1. Assess fuel sufficiency for remaining distance\n"
    "2. Evaluate weather risks and congestion\n"
    "3. Consider airport capacity at destination\n"
    "4. Factor in your personality and risk tolerance\n\n"
    "Choose exactly ONE action: CONTINUE | HOLD | REROUTE | EMERGENCY_LAND\n"
    "Respond with pure JSON only, no markdown, under 200 tokens.\n"
    '{{"action": "...", "reason": "...", "chain_of_thought": "Step 1: ... Step 2: ... Step 3: ..."}}'
)


def _build_prompt(flight: "FlightAgent") -> str:
    past = ", ".join([d.get("action", "?") for d in flight.decision_history[-5:]]) or "none"
    return _DECISION_PROMPT_TEMPLATE.format(
        id=flight.id,
        personality=flight.personality["name"],
        origin_name=flight.origin.get("name", "?"),
        origin_iata=flight.origin.get("iata", "?"),
        dest_name=flight.destination.get("name", "?"),
        dest_iata=flight.destination.get("iata", "?"),
        fuel=int(flight.fuel_level),
        distance_remaining=int((1.0 - flight.progress) * 100),
        congestion=int(flight.congestion_memory),
        weather=int(flight.weather_risk),
        capacity_available=flight.dest_capacity_available,
        nearby_count=flight.nearby_flight_count,
        past_decisions=past,
        memory=int(flight.congestion_memory),
        risk_tolerance=flight.personality["risk_tolerance"],
        total_decisions=len(flight.decision_history),
    )


def _parse_json_decision(text: str) -> Dict[str, str]:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            # Ensure required keys
            if "action" not in parsed:
                parsed["action"] = "CONTINUE"
            if "reason" not in parsed:
                parsed["reason"] = "No reason provided"
            return parsed
        except json.JSONDecodeError:
            pass
    return {"action": "CONTINUE", "reason": "LLM returned invalid JSON", "chain_of_thought": ""}


async def _run_single_llm(flight: "FlightAgent", model_id: str) -> Dict[str, str]:
    """Async Agno agent call for a single flight decision."""
    _ensure_agno()
    agent = _Agent(
        model=_Ollama(id=model_id),
        name=f"flight-{flight.id}",
        markdown=False,
    )
    prompt = _build_prompt(flight)
    try:
        result = await agent.arun(prompt, stream=False)
        text = result.content if hasattr(result, "content") else str(result)
        return _parse_json_decision(text)
    except Exception as e:
        return {"action": "CONTINUE", "reason": f"LLM error: {e}", "chain_of_thought": ""}


def batch_llm_decisions(flights: List["FlightAgent"]) -> tuple[Dict[str, Dict], Dict]:
    """
    Run Agno+Ollama decisions concurrently for all LLM-mode flights.
    Returns (decisions dict keyed by flight.id, metrics dict).
    """
    import time

    models = _list_ollama_models() or [_get_model()]

    async def _run_all():
        tasks = []
        for i, flight in enumerate(flights):
            model_id = models[i % len(models)]
            tasks.append(_run_single_llm(flight, model_id))
        return await asyncio.gather(*tasks, return_exceptions=True)

    t0 = time.time()
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _run_all())
                raw_results = future.result(timeout=30)
        else:
            raw_results = asyncio.run(_run_all())
    except Exception as e:
        import traceback
        traceback.print_exc()
        raw_results = [{"action": "CONTINUE", "reason": f"async error: {str(e)}", "chain_of_thought": ""}] * len(flights)

    latency_ms = int((time.time() - t0) * 1000)

    decisions: Dict[str, Dict] = {}
    total_tokens = 0
    for flight, res in zip(flights, raw_results):
        if isinstance(res, Exception):
            decisions[flight.id] = {"action": "CONTINUE", "reason": str(res), "chain_of_thought": ""}
        else:
            decisions[flight.id] = res
        total_tokens += max(1, len(_build_prompt(flight)) // 4 + 50)

    metrics = {
        "tokens": total_tokens,
        "latency_ms": latency_ms,
        "calls": len(flights),
    }
    return decisions, metrics


# ---------------------------------------------------------------------------
# Multi-Agent Negotiation
# ---------------------------------------------------------------------------

def negotiate_landing_slots(flights: List["FlightAgent"], airport_capacities: Dict[str, int]) -> Dict[str, str]:
    """
    Flights approaching the same destination negotiate for landing priority.
    Returns a dict of flight_id -> negotiation_result.
    """
    # Group flights by destination
    dest_groups: Dict[str, List["FlightAgent"]] = {}
    for f in flights:
        dest_iata = f.destination.get("iata", "?")
        if dest_iata not in dest_groups:
            dest_groups[dest_iata] = []
        dest_groups[dest_iata].append(f)

    results = {}
    for dest, group in dest_groups.items():
        capacity = airport_capacities.get(dest, 5)
        # Sort by priority: lower fuel = higher priority, then progress closer to arrival
        group.sort(key=lambda f: (f.fuel_level, -(f.progress)))

        for i, flight in enumerate(group):
            flight.nearby_flight_count = len(group) - 1
            if i < capacity:
                results[flight.id] = "CLEARED"
                flight.dest_capacity_available = capacity - i
            else:
                results[flight.id] = "HOLD_PATTERN"
                flight.dest_capacity_available = 0
                # Force hold if capacity exceeded
                if flight.mode == "RULE":
                    flight.last_action = "HOLD"
                    flight.reasoning = f"Holding: {dest} at capacity ({capacity} slots, {len(group)} inbound)"

    return results


# ---------------------------------------------------------------------------
# FlightAgent
# ---------------------------------------------------------------------------

class FlightAgent:
    """
    Represents one flight as an Agno-backed autonomous agent.
    Enhanced with personality, memory, decision history, and negotiation state.
    """

    def __init__(
        self,
        id: str,
        origin: Dict[str, Any],
        destination: Dict[str, Any],
        fuel_level: float = 100.0,
        congestion_memory: float = 0.0,
        weather_risk: float = 0.0,
        delay_score: float = 0.0,
        mode: str = "RULE",
    ):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.fuel_level = fuel_level
        self.congestion_memory = congestion_memory
        self.weather_risk = weather_risk
        self.delay_score = delay_score
        self.mode = mode  # "RULE" | "LLM"

        self.progress = 0.0
        self.reasoning = ""
        self.last_action = "CONTINUE"
        self.chain_of_thought = ""

        # Current interpolated position (set by simulation tick)
        self.lat = origin.get("lat", 0)
        self.lon = origin.get("lon", 0)

        # Personality system
        self.personality = random.choice(PERSONALITIES)
        self.experience = 0  # increases with each decision

        # Decision history
        self.decision_history: List[Dict] = []

        # Negotiation state
        self.nearby_flight_count = 0
        self.dest_capacity_available = 5
        self.negotiation_status = "CLEARED"

        # Fuel system
        self.total_distance = self._calc_distance()
        self.fuel_burn_rate = max(0.05, self.total_distance / 20000.0 * 0.15)  # rate based on distance

        # Position history for trails
        self.position_history: List[Dict] = []
        self.max_trail_length = 20

    def _calc_distance(self) -> float:
        """Calculate great-circle distance between origin and destination in km."""
        lat1 = math.radians(self.origin.get("lat", 0))
        lon1 = math.radians(self.origin.get("lon", 0))
        lat2 = math.radians(self.destination.get("lat", 0))
        lon2 = math.radians(self.destination.get("lon", 0))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return 6371 * c  # Earth radius in km

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "origin": self.origin,
            "destination": self.destination,
            "fuel_level": round(self.fuel_level, 1),
            "congestion_memory": round(self.congestion_memory, 1),
            "weather_risk": round(self.weather_risk, 1),
            "delay_score": round(self.delay_score, 1),
            "mode": self.mode,
            "progress": round(self.progress, 4),
            "reasoning": self.reasoning,
            "last_action": self.last_action,
            "chain_of_thought": self.chain_of_thought,
            "lat": round(self.lat, 4),
            "lon": round(self.lon, 4),
            "personality": self.personality["name"],
            "risk_tolerance": self.personality["risk_tolerance"],
            "experience": self.experience,
            "total_distance_km": round(self.total_distance, 0),
            "fuel_burn_rate": round(self.fuel_burn_rate, 3),
            "nearby_flights": self.nearby_flight_count,
            "dest_capacity": self.dest_capacity_available,
            "negotiation_status": self.negotiation_status,
            "decision_count": len(self.decision_history),
            "decision_history": self.decision_history[-10:],  # last 10
            "position_history": self.position_history,
        }

    # ------------------------------------------------------------------
    # Decision logic
    # ------------------------------------------------------------------

    def decide_action(self) -> Dict[str, Any]:
        """Make a decision (RULE mode only here; LLM batched externally)."""
        decision = self.rule_based_decision()
        self._record_decision(decision)
        return decision

    def _record_decision(self, decision: Dict):
        """Record a decision in history."""
        self.reasoning = decision.get("reason", "")
        self.last_action = decision.get("action", "CONTINUE")
        self.chain_of_thought = decision.get("chain_of_thought", "")
        self.experience += 1
        self.decision_history.append({
            "action": self.last_action,
            "reason": self.reasoning,
            "fuel": round(self.fuel_level, 1),
            "progress": round(self.progress, 3),
            "weather": round(self.weather_risk, 1),
            "tick": self.experience,
        })
        # Keep history manageable
        if len(self.decision_history) > 50:
            self.decision_history = self.decision_history[-50:]

    def rule_based_decision(self) -> Dict[str, str]:
        p = self.personality
        cot_steps = []

        # Step 1: Fuel check
        cot_steps.append(f"Step 1: Fuel at {self.fuel_level:.0f}%, threshold {p['fuel_threshold']}%")
        if self.fuel_level < p["fuel_threshold"]:
            cot_steps.append("CRITICAL: Fuel below safety threshold")
            return {
                "action": "EMERGENCY_LAND",
                "reason": f"Fuel below {p['fuel_threshold']}% ({p['name']} pilot)",
                "chain_of_thought": " → ".join(cot_steps),
            }

        # Step 2: Weather check
        cot_steps.append(f"Step 2: Weather risk {self.weather_risk:.0f}%, threshold {p['weather_threshold']}%")
        if self.weather_risk > p["weather_threshold"]:
            cot_steps.append("CAUTION: Weather exceeds comfort level")
            return {
                "action": "HOLD",
                "reason": f"Weather risk {self.weather_risk:.0f}% exceeds {p['name']} threshold ({p['weather_threshold']}%)",
                "chain_of_thought": " → ".join(cot_steps),
            }

        # Step 3: Congestion check
        cot_steps.append(f"Step 3: Congestion {self.congestion_memory:.0f}, threshold {p['congestion_threshold']}")
        if self.congestion_memory > p["congestion_threshold"]:
            cot_steps.append("ALERT: Destination congested, rerouting")
            return {
                "action": "REROUTE",
                "reason": f"Congestion ({self.congestion_memory:.0f}) above {p['name']} threshold ({p['congestion_threshold']})",
                "chain_of_thought": " → ".join(cot_steps),
            }

        # Step 4: Capacity check
        cot_steps.append(f"Step 4: Destination capacity available: {self.dest_capacity_available}")
        if self.dest_capacity_available <= 0 and self.progress > 0.7:
            cot_steps.append("HOLD: No landing slots available at destination")
            return {
                "action": "HOLD",
                "reason": f"No landing capacity at destination, entering hold pattern",
                "chain_of_thought": " → ".join(cot_steps),
            }

        cot_steps.append("All checks passed, proceeding")
        return {
            "action": "CONTINUE",
            "reason": f"Conditions nominal ({p['name']} assessment)",
            "chain_of_thought": " → ".join(cot_steps),
        }

    def update_trail(self):
        """Add current position to trail history."""
        self.position_history.append({"lat": round(self.lat, 4), "lon": round(self.lon, 4)})
        if len(self.position_history) > self.max_trail_length:
            self.position_history = self.position_history[-self.max_trail_length:]


# ---------------------------------------------------------------------------
# Haversine / great-circle interpolation
# ---------------------------------------------------------------------------

def haversine_interpolate(a_lat, a_lon, b_lat, b_lon, fraction):
    """Great-circle interpolation using SLERP."""
    lat1 = math.radians(a_lat)
    lon1 = math.radians(a_lon)
    lat2 = math.radians(b_lat)
    lon2 = math.radians(b_lon)

    x1 = math.cos(lat1) * math.cos(lon1)
    y1 = math.cos(lat1) * math.sin(lon1)
    z1 = math.sin(lat1)

    x2 = math.cos(lat2) * math.cos(lon2)
    y2 = math.cos(lat2) * math.sin(lon2)
    z2 = math.sin(lat2)

    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega = math.acos(dot)
    if abs(omega) < 1e-6:
        return (a_lat, a_lon)

    sin_omega = math.sin(omega)
    t1 = math.sin((1 - fraction) * omega) / sin_omega
    t2 = math.sin(fraction * omega) / sin_omega

    x = t1 * x1 + t2 * x2
    y = t1 * y1 + t2 * y2
    z = t1 * z1 + t2 * z2

    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))
    return (lat, lon)
