import React, { useEffect, useRef, useState } from 'react'
import GlobeGL from 'globe.gl'
import { apiFetch } from './api'

// Stable fingerprint of active routes
function routeKey(flights) {
    return flights.map(f => f.id).sort().join(',')
}

const GlobeComponent = ({ onSelect }) => {
    const containerRef = useRef(null)
    const globeRef = useRef(null)
    const [flights, setFlights] = useState([])
    const [weatherCells, setWeatherCells] = useState([])
    const arcKeyRef = useRef('')
    const weatherKeyRef = useRef('')

    // Initialize globe.gl ONCE
    useEffect(() => {
        if (!containerRef.current) return

        const Globe = GlobeGL.default ?? GlobeGL
        const g = Globe()(containerRef.current)
        globeRef.current = g

        // Dark earth with atmosphere
        g.globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
            .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
            .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
            .showAtmosphere(true)
            .atmosphereColor('#0af')
            .atmosphereAltitude(0.18)

        // Controls
        const controls = g.controls()
        controls.autoRotate = false
        controls.enableDamping = true
        controls.dampingFactor = 0.05
        controls.zoomSpeed = 0.6
        controls.rotateSpeed = 0.6
        controls.minDistance = 110
        controls.maxDistance = 500

        // Airport labels — glowing markers
        g.labelsData([])
            .labelLat('lat')
            .labelLng('lon')
            .labelText('iata')
            .labelSize(1.4)
            .labelDotRadius(0.6)
            .labelColor((d) => d.shutdown ? 'rgba(255, 60, 60, 0.95)' : 'rgba(0, 255, 213, 0.9)')
            .labelResolution(2)
            .labelAltitude(0.005)

        // Flight arcs — animated dashed arcs
        g.arcsData([])
            .arcStartLat((d) => d.origin?.lat ?? 0)
            .arcStartLng((d) => d.origin?.lon ?? 0)
            .arcEndLat((d) => d.destination?.lat ?? 0)
            .arcEndLng((d) => d.destination?.lon ?? 0)
            .arcColor((d) =>
                d.mode === 'LLM'
                    ? ['rgba(255,80,80,0.8)', 'rgba(255,180,80,0.4)']
                    : ['rgba(0,255,213,0.7)', 'rgba(0,180,255,0.3)']
            )
            .arcAltitudeAutoScale(0.35)
            .arcStroke((d) => (d.mode === 'LLM' ? 0.9 : 0.6))
            .arcDashLength(0.4)
            .arcDashGap(0.2)
            .arcDashAnimateTime(1500)

        // Weather cell rings
        g.ringsData([])
            .ringLat(d => d.lat)
            .ringLng(d => d.lon)
            .ringAltitude(0.003)
            .ringColor(d => {
                if (d.type === 'volcanic_ash') return () => 'rgba(180, 80, 0, 0.6)'
                return () => 'rgba(255, 100, 100, 0.5)'
            })
            .ringMaxRadius(d => d.radius_km / 200)
            .ringPropagationSpeed(2)
            .ringRepeatPeriod(800)

        // ✈ Flight icons as HTML elements
        g.htmlElementsData([])
            .htmlLat((d) => d.lat)
            .htmlLng((d) => d.lon)
            .htmlAltitude(0.025)
            .htmlElement((d) => {
                const el = document.createElement('div')
                const isLLM = d.mode === 'LLM'
                const action = d.last_action || 'CONTINUE'
                let color = isLLM ? '#ff6060' : '#00ffd5'
                if (action === 'HOLD') color = '#ffaa33'
                if (action === 'EMERGENCY_LAND') color = '#ff2222'
                if (action === 'REROUTE') color = '#ff88ff'

                el.innerHTML = '✈'
                el.style.cssText = [
                    `color: ${color}`,
                    'font-size: 22px',
                    `text-shadow: 0 0 10px ${color}, 0 0 20px ${color}55`,
                    'cursor: pointer',
                    'transform: translate(-50%, -50%)',
                    'user-select: none',
                    'pointer-events: auto',
                    'transition: color 0.3s ease',
                ].join(';')
                el.title = `${d.id} | ${d.mode} | ${d.personality} | Fuel: ${Math.round(d.fuel_level ?? 0)}% | ${action}`
                el.onclick = () => { if (d.id && onSelect) onSelect(d.id) }
                return el
            })

        return () => {
            try { g._destructor?.() } catch (_) { }
        }
    }, [])

    // Update globe whenever flights/weather change
    useEffect(() => {
        const g = globeRef.current
        if (!g) return

        const valid = flights.filter(f =>
            f.origin && f.destination &&
            typeof f.origin.lat === 'number' && !isNaN(f.origin.lat) &&
            typeof f.origin.lon === 'number' && !isNaN(f.origin.lon) &&
            typeof f.destination.lat === 'number' && !isNaN(f.destination.lat) &&
            typeof f.destination.lon === 'number' && !isNaN(f.destination.lon) &&
            typeof f.lat === 'number' && !isNaN(f.lat) &&
            typeof f.lon === 'number' && !isNaN(f.lon)
        )

        // Arcs: only update when routes change
        const key = routeKey(valid)
        if (key !== arcKeyRef.current) {
            arcKeyRef.current = key
            g.arcsData(valid)

            // Airport labels with shutdown status
            const airportMap = new Map()
            valid.forEach(f => {
                if (f.origin?.iata && f.origin.lat && f.origin.lon)
                    airportMap.set(f.origin.iata, { iata: f.origin.iata, lat: f.origin.lat, lon: f.origin.lon, shutdown: false })
                if (f.destination?.iata && f.destination.lat && f.destination.lon)
                    airportMap.set(f.destination.iata, { iata: f.destination.iata, lat: f.destination.lat, lon: f.destination.lon, shutdown: false })
            })
            g.labelsData(Array.from(airportMap.values()))
        }

        // HTML icons update every tick
        g.htmlElementsData(valid)

        // Weather cell rings
        const wKey = JSON.stringify(weatherCells.map(w => w.id))
        if (wKey !== weatherKeyRef.current) {
            weatherKeyRef.current = wKey
            g.ringsData(weatherCells.filter(w => w.alive))
        }
    }, [flights, weatherCells])

    // Poll backend every 1.2s
    useEffect(() => {
        let mounted = true
        const poll = async () => {
            try {
                const [flightsRes, weatherRes] = await Promise.all([
                    apiFetch('/api/flights'),
                    apiFetch('/api/weather_cells'),
                ])
                const flightsJson = await flightsRes.json()
                const weatherJson = await weatherRes.json()
                if (mounted) {
                    setFlights(Array.isArray(flightsJson) ? flightsJson : [])
                    setWeatherCells(Array.isArray(weatherJson) ? weatherJson : [])
                }
            } catch (_) { }
        }
        const id = setInterval(poll, 1200)
        poll()
        return () => { mounted = false; clearInterval(id) }
    }, [])

    // Count by action
    const holding = flights.filter(f => f.last_action === 'HOLD').length
    const rerouting = flights.filter(f => f.last_action === 'REROUTE').length

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative', background: '#000' }}>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
            {flights.length > 0 && (
                <div style={{
                    position: 'absolute',
                    bottom: 16,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'rgba(0,0,0,0.7)',
                    backdropFilter: 'blur(10px)',
                    color: '#00ffd5',
                    padding: '8px 20px',
                    borderRadius: 20,
                    fontSize: 12,
                    fontFamily: 'monospace',
                    border: '1px solid rgba(0,255,213,0.3)',
                    pointerEvents: 'none',
                    whiteSpace: 'nowrap',
                    display: 'flex',
                    gap: 12,
                    alignItems: 'center',
                }}>
                    <span>✈ {flights.length} active</span>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>|</span>
                    <span style={{ color: '#00c7ff' }}>{flights.filter(f => f.mode === 'RULE').length} RULE</span>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}>/</span>
                    <span style={{ color: '#ff6b6b' }}>{flights.filter(f => f.mode === 'LLM').length} LLM</span>
                    {holding > 0 && <>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>|</span>
                        <span style={{ color: '#ffaa33' }}>⏸ {holding} holding</span>
                    </>}
                    {rerouting > 0 && <>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>|</span>
                        <span style={{ color: '#ff88ff' }}>↻ {rerouting} rerouting</span>
                    </>}
                    {weatherCells.length > 0 && <>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}>|</span>
                        <span style={{ color: '#ff6b6b' }}>🌩 {weatherCells.length} storms</span>
                    </>}
                </div>
            )}
        </div>
    )
}

export default GlobeComponent
