"""Load a minimal subset of OpenFlights data or provide fallback sample data.

This loader looks for `airports.dat` and `routes.dat` in the backend folder.
If absent, it returns a small sample set so the demo can run without the full
dataset.
"""

import csv
import os
from typing import List, Dict


def load_airports(path: str = "airports.dat") -> List[Dict]:
    if os.path.exists(path):
        airports = []
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # OpenFlights fields: id, name, city, country, iata, icao, lat, lon, ...
                try:
                    iata = row[4]
                    if not iata or iata == "\\N":
                        continue
                    airports.append({
                        "id": row[0],
                        "name": row[1],
                        "city": row[2],
                        "country": row[3],
                        "iata": iata,
                        "icao": row[5],
                        "lat": float(row[6]),
                        "lon": float(row[7]),
                    })
                except Exception:
                    continue
        return airports

    # fallback sample
    return [
        {"id": "1", "name": "San Francisco Intl", "city": "San Francisco", "country": "USA", "iata": "SFO", "lat": 37.6213, "lon": -122.3790},
        {"id": "2", "name": "Los Angeles Intl", "city": "Los Angeles", "country": "USA", "iata": "LAX", "lat": 33.9416, "lon": -118.4085},
        {"id": "3", "name": "John F Kennedy Intl", "city": "New York", "country": "USA", "iata": "JFK", "lat": 40.6413, "lon": -73.7781},
        {"id": "4", "name": "Heathrow", "city": "London", "country": "UK", "iata": "LHR", "lat": 51.4700, "lon": -0.4543},
        {"id": "5", "name": "Changi", "city": "Singapore", "country": "SG", "iata": "SIN", "lat": 1.3644, "lon": 103.9915},
        {"id": "6", "name": "Dubai Intl", "city": "Dubai", "country": "UAE", "iata": "DXB", "lat": 25.2532, "lon": 55.3657},
        {"id": "7", "name": "Narita Intl", "city": "Tokyo", "country": "Japan", "iata": "NRT", "lat": 35.7647, "lon": 140.3864},
        {"id": "8", "name": "Charles de Gaulle", "city": "Paris", "country": "France", "iata": "CDG", "lat": 49.0097, "lon": 2.5479},
        {"id": "9", "name": "Sydney Intl", "city": "Sydney", "country": "Australia", "iata": "SYD", "lat": -33.9461, "lon": 151.1772},
        {"id": "10", "name": "Indira Gandhi Intl", "city": "New Delhi", "country": "India", "iata": "DEL", "lat": 28.5562, "lon": 77.1000},
        {"id": "11", "name": "O'Hare Intl", "city": "Chicago", "country": "USA", "iata": "ORD", "lat": 41.9742, "lon": -87.9073},
        {"id": "12", "name": "Sao Paulo Guarulhos", "city": "Sao Paulo", "country": "Brazil", "iata": "GRU", "lat": -23.4356, "lon": -46.4731},
        {"id": "13", "name": "Hong Kong Intl", "city": "Hong Kong", "country": "China", "iata": "HKG", "lat": 22.3080, "lon": 113.9185},
        {"id": "14", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "Germany", "iata": "FRA", "lat": 50.0379, "lon": 8.5622},
        {"id": "15", "name": "Johannesburg OR Tambo", "city": "Johannesburg", "country": "South Africa", "iata": "JNB", "lat": -26.1392, "lon": 28.2460},
    ]


def load_routes(path: str = "routes.dat") -> List[Dict]:
    if os.path.exists(path):
        routes = []
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    routes.append({
                        "airline": row[0],
                        "source": row[2],
                        "dest": row[4],
                    })
                except Exception:
                    continue
        return routes

    # fallback: build some routes between sample airports
    return [
        {"airline": "SWA", "source": "SFO", "dest": "LAX"},
        {"airline": "AA", "source": "LAX", "dest": "JFK"},
        {"airline": "BA", "source": "JFK", "dest": "LHR"},
        {"airline": "SQ", "source": "LHR", "dest": "SIN"},
        {"airline": "EK", "source": "DXB", "dest": "DEL"},
        {"airline": "NH", "source": "NRT", "dest": "SFO"},
        {"airline": "AF", "source": "CDG", "dest": "JFK"},
        {"airline": "QF", "source": "SYD", "dest": "SIN"},
        {"airline": "UA", "source": "ORD", "dest": "FRA"},
        {"airline": "LA", "source": "GRU", "dest": "JNB"},
        {"airline": "CX", "source": "HKG", "dest": "NRT"},
        {"airline": "LH", "source": "FRA", "dest": "DXB"},
    ]
