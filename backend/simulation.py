"""Simulation manager for SkySwarm demo.

Enhanced with:
- Moving weather cells system
- Airport capacity management
- More crisis types (volcanic ash, ATC strike, solar flare, airspace closure)
- RULE vs LLM comparison metrics
- WebSocket-ready state broadcasting
"""

import threading
import time
import uuid
import random
import math
from typing import List, Dict, Any

from agents import FlightAgent, haversine_interpolate, batch_llm_decisions, negotiate_landing_slots
from openflights_loader import load_airports, load_routes


# ---------------------------------------------------------------------------
# Weather Cell System
# ---------------------------------------------------------------------------

class WeatherCell:
    """A storm cell that moves across the globe over time."""

    def __init__(self, lat: float, lon: float, intensity: float, radius_km: float,
                 speed_lat: float, speed_lon: float, cell_type: str = "storm"):
        self.id = str(uuid.uuid4())[:6]
        self.lat = lat
        self.lon = lon
        self.intensity = intensity  # 0-100
        self.radius_km = radius_km  # effect radius
        self.speed_lat = speed_lat  # degrees per tick
        self.speed_lon = speed_lon
        self.cell_type = cell_type  # storm, volcanic_ash, turbulence
        self.age = 0
        self.max_age = random.randint(60, 200)  # ticks before dissipating

    def tick(self):
        self.lat += self.speed_lat
        self.lon += self.speed_lon
        self.age += 1
        # Intensity fades as cell ages
        if self.age > self.max_age * 0.7:
            self.intensity *= 0.97

    @property
    def alive(self) -> bool:
        return self.age < self.max_age and self.intensity > 5

    def affects_position(self, lat: float, lon: float) -> float:
        """Return weather intensity at a given position (0 if out of range)."""
        # Simple distance check using haversine approximation
        dlat = math.radians(self.lat - lat)
        dlon = math.radians(self.lon - lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(
            math.radians(self.lat)) * math.sin(dlon / 2) ** 2
        dist_km = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        if dist_km > self.radius_km:
            return 0.0
        # Falloff: full intensity at center, 0 at edge
        return self.intensity * (1 - dist_km / self.radius_km)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "lat": round(self.lat, 2),
            "lon": round(self.lon, 2),
            "intensity": round(self.intensity, 1),
            "radius_km": round(self.radius_km, 0),
            "type": self.cell_type,
            "age": self.age,
            "alive": self.alive,
        }


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

class Simulation:
    def __init__(self, tick_interval: float = 1.0):
        self.flights: List[FlightAgent] = []
        self.running = False
        self.tick_interval = tick_interval
        self._thread = None
        self.tick_count = 0
        self.airports = {a['iata']: a for a in load_airports()}
        self.routes = load_routes()

        # Airport capacity system
        self.airport_capacities: Dict[str, int] = {}
        for iata in self.airports:
            self.airport_capacities[iata] = random.randint(3, 8)

        # Weather system
        self.weather_cells: List[WeatherCell] = []
        self.weather_intensity = 20

        # Simulation parameters
        self.congestion_multiplier = 1
        self.speed_multiplier = 1.0
        self.global_mode = 'RULE'

        # Metrics
        self.metrics = {
            "llm_tokens": 0,
            "llm_calls": 0,
            "llm_latency_ms": 0,
            "decisions": 0,
        }

        # Comparison tracking
        self.comparison = {
            "rule": {"total_flights": 0, "emergency_landings": 0, "holds": 0, "reroutes": 0, "avg_fuel_at_arrival": []},
            "llm": {"total_flights": 0, "emergency_landings": 0, "holds": 0, "reroutes": 0, "avg_fuel_at_arrival": []},
        }

        # Shutdown airports
        self.shutdown_airports: set = set()

        # Event log for the frontend
        self.event_log: List[Dict] = []

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _loop(self):
        while self.running:
            self.run_tick()
            time.sleep(self.tick_interval / self.speed_multiplier)

    def _log_event(self, event_type: str, message: str, flight_id: str = ""):
        self.event_log.append({
            "tick": self.tick_count,
            "type": event_type,
            "message": message,
            "flight_id": flight_id,
            "timestamp": time.time(),
        })
        if len(self.event_log) > 100:
            self.event_log = self.event_log[-100:]

    def add_flight(self, origin_iata: str, dest_iata: str, mode: str = None) -> FlightAgent:
        origin = self.airports.get(origin_iata)
        dest = self.airports.get(dest_iata)
        fid = str(uuid.uuid4())[:8]
        if not origin or not dest:
            keys = list(self.airports.keys())
            origin = self.airports[keys[0]]
            dest = self.airports[keys[1]]
        flight_mode = mode if mode else self.global_mode
        flight = FlightAgent(fid, origin, dest, mode=flight_mode)
        flight.weather_risk = self.weather_intensity * random.uniform(0.5, 1.5)
        self.flights.append(flight)
        # Track comparison
        mode_key = flight_mode.lower()
        if mode_key in self.comparison:
            self.comparison[mode_key]["total_flights"] += 1
        return flight

    def _spawn_weather_cell(self):
        """Randomly spawn a weather cell somewhere on the globe."""
        cell = WeatherCell(
            lat=random.uniform(-60, 60),
            lon=random.uniform(-180, 180),
            intensity=random.uniform(30, 90),
            radius_km=random.uniform(200, 1500),
            speed_lat=random.uniform(-0.3, 0.3),
            speed_lon=random.uniform(-0.5, 0.5),
            cell_type=random.choice(["storm", "turbulence", "storm"]),
        )
        self.weather_cells.append(cell)
        self._log_event("weather", f"New {cell.cell_type} cell spawned at ({cell.lat:.0f}°, {cell.lon:.0f}°)")

    def run_tick(self):
        self.tick_count += 1

        # Weather cell lifecycle
        for cell in self.weather_cells:
            cell.tick()
        self.weather_cells = [c for c in self.weather_cells if c.alive]
        # Random chance to spawn new weather cell
        if random.random() < 0.03 and len(self.weather_cells) < 10:
            self._spawn_weather_cell()

        # Progress all flights
        for flight in list(self.flights):
            progress_increment = 0.01 * self.speed_multiplier
            flight.progress = min(1.0, flight.progress + progress_increment)
            lat, lon = haversine_interpolate(
                flight.origin['lat'], flight.origin['lon'],
                flight.destination['lat'], flight.destination['lon'],
                flight.progress
            )
            flight.lat = lat
            flight.lon = lon

            # Distance-based fuel burn
            flight.fuel_level = max(0.0, flight.fuel_level - flight.fuel_burn_rate)

            # Weather risk from all active cells
            total_weather = self.weather_intensity * random.uniform(0.3, 0.8)
            for cell in self.weather_cells:
                cell_effect = cell.affects_position(flight.lat, flight.lon)
                total_weather += cell_effect
            flight.weather_risk = min(100, total_weather)

            # Congestion
            flight.congestion_memory = flight.congestion_memory * 0.95 + (self.congestion_multiplier * random.uniform(0, 10))

            # Trail tracking
            if self.tick_count % 2 == 0:
                flight.update_trail()

        # Multi-agent negotiation
        if self.flights:
            negotiate_landing_slots(self.flights, self.airport_capacities)

        # LLM-mode flights
        llm_flights = [f for f in self.flights if f.mode == 'LLM']
        MAX_LLM_CALLS = 40
        if len(llm_flights) > MAX_LLM_CALLS:
            llm_flights = llm_flights[:MAX_LLM_CALLS]

        if llm_flights:
            try:
                decisions, metrics = batch_llm_decisions(llm_flights)
                for f in llm_flights:
                    dec = decisions.get(f.id, {"action": "CONTINUE", "reason": "no decision", "chain_of_thought": ""})
                    f._record_decision(dec)

                self.metrics['llm_tokens'] += metrics.get('tokens', 0)
                self.metrics['llm_calls'] += metrics.get('calls', 0)
                self.metrics['llm_latency_ms'] += metrics.get('latency_ms', 0)
                self.metrics['decisions'] += len(llm_flights)
            except Exception as e:
                import traceback
                traceback.print_exc()
                for f in llm_flights:
                    f.reasoning = f"LLM call failed: {e}"
                    f.last_action = "CONTINUE"

        # RULE decisions + flight removal
        to_remove = []
        for flight in list(self.flights):
            if flight.mode == 'LLM' and flight in llm_flights:
                pass  # Already decided
            else:
                decision = flight.rule_based_decision()
                flight._record_decision(decision)

            # Track comparison
            mode_key = flight.mode.lower()
            if mode_key in self.comparison:
                if flight.last_action == "EMERGENCY_LAND":
                    self.comparison[mode_key]["emergency_landings"] += 1
                elif flight.last_action == "HOLD":
                    self.comparison[mode_key]["holds"] += 1
                elif flight.last_action == "REROUTE":
                    self.comparison[mode_key]["reroutes"] += 1

            # Remove completed or emergency landed flights
            if flight.last_action == 'EMERGENCY_LAND' or flight.progress >= 1.0:
                if flight.progress >= 1.0 and mode_key in self.comparison:
                    self.comparison[mode_key]["avg_fuel_at_arrival"].append(flight.fuel_level)
                    # Keep only last 100
                    if len(self.comparison[mode_key]["avg_fuel_at_arrival"]) > 100:
                        self.comparison[mode_key]["avg_fuel_at_arrival"] = self.comparison[mode_key]["avg_fuel_at_arrival"][-100:]
                to_remove.append(flight)

        for f in to_remove:
            try:
                self.flights.remove(f)
            except ValueError:
                pass

    def inject_crisis(self, crisis_type: str):
        """Inject a crisis event affecting all flights."""
        crisis_effects = {
            'storm': {'congestion_add': 30, 'weather_add': 40},
            'airport_shutdown': {'congestion_add': 50, 'weather_add': 10},
            'fuel_shortage': {'fuel_penalty': 0.3},
            'volcanic_ash': {'congestion_add': 40, 'weather_add': 60},
            'atc_strike': {'congestion_add': 70, 'delay_add': 30},
            'solar_flare': {'congestion_add': 20, 'weather_add': 30, 'delay_add': 15},
            'airspace_closure': {'congestion_add': 60, 'delay_add': 25},
        }
        effect = crisis_effects.get(crisis_type, {'congestion_add': 20})
        self._log_event("crisis", f"Crisis injected: {crisis_type}", "")

        for f in self.flights:
            f.congestion_memory += effect.get('congestion_add', 0)
            f.weather_risk = min(100, f.weather_risk + effect.get('weather_add', 0))
            if 'fuel_penalty' in effect:
                f.fuel_level -= effect['fuel_penalty'] * f.fuel_level
            f.delay_score += effect.get('delay_add', 0)

        # Storm crisis: spawn actual weather cells
        if crisis_type == 'storm':
            for _ in range(3):
                self._spawn_weather_cell()

        # Volcanic ash: spawn a large, slow-moving cell
        if crisis_type == 'volcanic_ash':
            cell = WeatherCell(
                lat=random.uniform(-30, 30), lon=random.uniform(-180, 180),
                intensity=85, radius_km=2000,
                speed_lat=random.uniform(-0.1, 0.1), speed_lon=random.uniform(-0.2, 0.2),
                cell_type="volcanic_ash"
            )
            cell.max_age = 300
            self.weather_cells.append(cell)

        # Airport shutdown: randomly close an airport
        if crisis_type == 'airport_shutdown':
            keys = list(self.airports.keys())
            if keys:
                shutdown = random.choice(keys)
                self.airport_capacities[shutdown] = 0
                self.shutdown_airports.add(shutdown)
                self._log_event("crisis", f"Airport {shutdown} SHUT DOWN", "")

    def set_weather(self, intensity: float):
        self.weather_intensity = intensity

    def set_congestion(self, multiplier: float):
        self.congestion_multiplier = multiplier

    def set_speed(self, speed: float):
        self.speed_multiplier = max(0.25, min(4.0, speed))

    def set_mode(self, mode: str):
        self.global_mode = mode
        if mode == 'LLM':
            for f in self.flights:
                f.mode = 'LLM'

    def get_state(self):
        return [f.to_dict() for f in self.flights]

    def get_weather_cells(self):
        return [c.to_dict() for c in self.weather_cells]

    def get_comparison(self):
        """Get RULE vs LLM comparison stats."""
        result = {}
        for mode in ["rule", "llm"]:
            data = self.comparison[mode]
            arrivals = data["avg_fuel_at_arrival"]
            result[mode] = {
                "total_flights": data["total_flights"],
                "emergency_landings": data["emergency_landings"],
                "holds": data["holds"],
                "reroutes": data["reroutes"],
                "avg_fuel_arrival": round(sum(arrivals) / len(arrivals), 1) if arrivals else 0,
            }
        return result

    def get_capacities(self):
        """Get airport capacity info for frontend."""
        return {
            iata: {
                "capacity": cap,
                "inbound": sum(1 for f in self.flights if f.destination.get("iata") == iata),
                "shutdown": iata in self.shutdown_airports,
            }
            for iata, cap in self.airport_capacities.items()
            if any(f.destination.get("iata") == iata or f.origin.get("iata") == iata for f in self.flights)
        }
