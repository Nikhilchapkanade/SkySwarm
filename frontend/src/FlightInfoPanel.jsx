import React, { useState, useEffect } from 'react'
import { apiFetch } from './api'

const panelWidth = 300

const FlightInfoPanel = ({ selectedFlightId, backendOk }) => {
    const [flights, setFlights] = useState([])
    const [inspectedFlight, setInspectedFlight] = useState(null)
    const [events, setEvents] = useState([])
    const [showTimeline, setShowTimeline] = useState(false)

    // Poll flights
    useEffect(() => {
        let mounted = true
        const poll = async () => {
            try {
                const [fRes, eRes] = await Promise.all([
                    apiFetch('/api/flights'),
                    apiFetch('/api/events'),
                ])
                const fJson = await fRes.json()
                const eJson = await eRes.json()
                if (mounted) {
                    setFlights(Array.isArray(fJson) ? fJson : [])
                    setEvents(Array.isArray(eJson) ? eJson : [])
                }
            } catch (_) { }
        }
        const id = setInterval(poll, 1500)
        poll()
        return () => { mounted = false; clearInterval(id) }
    }, [])

    // When selectedFlightId changes, find the flight
    useEffect(() => {
        if (selectedFlightId) {
            const f = flights.find(fl => fl.id === selectedFlightId)
            if (f) setInspectedFlight(f)
        }
    }, [selectedFlightId, flights])

    const llmFlights = flights.filter(f => f.mode === 'LLM')
    const activeThoughts = llmFlights.slice(0, 6)

    // Decision history for inspected flight
    const history = inspectedFlight?.decision_history || []

    // Action color map
    const actionColor = (action) => {
        switch (action) {
            case 'CONTINUE': return '#00ffd5'
            case 'HOLD': return '#ffaa33'
            case 'REROUTE': return '#ff88ff'
            case 'EMERGENCY_LAND': return '#ff2222'
            default: return '#888'
        }
    }

    return (
        <div style={{
            width: panelWidth,
            minWidth: panelWidth,
            flexShrink: 0,
            height: '100vh',
            background: 'rgba(7, 16, 41, 0.92)',
            backdropFilter: 'blur(16px)',
            borderLeft: '1px solid rgba(0,255,213,0.1)',
            padding: '12px 10px',
            overflowY: 'auto',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
        }}>
            {/* Backend status */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                <span style={{ color: 'rgba(255,255,255,0.4)' }}>Backend:</span>
                <span style={{
                    color: backendOk ? '#00ffd5' : '#ff507a',
                    fontWeight: 700,
                    display: 'flex', alignItems: 'center', gap: 4,
                }}>
                    <span style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: backendOk ? '#00ffd5' : '#ff507a',
                        boxShadow: `0 0 8px ${backendOk ? '#00ffd5' : '#ff507a'}`,
                        display: 'inline-block',
                    }} />
                    {backendOk ? 'OK' : 'OFFLINE'}
                </span>
            </div>

            {/* Agent Thoughts */}
            <div>
                <div style={{ color: '#ff88ff', fontWeight: 700, fontSize: 14, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    🧠 <span>Live Agent Thoughts</span>
                </div>
                {activeThoughts.length === 0 && (
                    <div style={{
                        color: 'rgba(255,255,255,0.3)',
                        fontSize: 11,
                        padding: 8,
                        border: '1px solid rgba(255,255,255,0.05)',
                        borderRadius: 6,
                    }}>
                        Waiting for LLM decisions... (Switch to LLM mode and spawn flights)
                    </div>
                )}
                {activeThoughts.map(f => (
                    <div key={f.id} style={{
                        padding: 6,
                        marginBottom: 4,
                        borderRadius: 6,
                        background: 'rgba(255,136,255,0.06)',
                        border: '1px solid rgba(255,136,255,0.12)',
                        cursor: 'pointer',
                    }} onClick={() => setInspectedFlight(f)}>
                        <div style={{ fontSize: 10, display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: '#ff6060', fontWeight: 600 }}>✈ {f.id}</span>
                            <span style={{
                                color: actionColor(f.last_action),
                                fontWeight: 700,
                                fontSize: 9,
                                background: 'rgba(0,0,0,0.3)',
                                padding: '1px 6px',
                                borderRadius: 4,
                            }}>{f.last_action}</span>
                        </div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: 2, lineHeight: 1.3 }}>
                            {f.reasoning?.slice(0, 80) || 'Processing...'}
                        </div>
                        {f.personality && (
                            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', marginTop: 1 }}>
                                Pilot: {f.personality} | Risk: {(f.risk_tolerance * 100).toFixed(0)}%
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Event Log */}
            {events.length > 0 && (
                <div>
                    <div style={{ color: '#ffaa33', fontWeight: 700, fontSize: 12, marginBottom: 4 }}>📋 Event Log</div>
                    <div style={{
                        maxHeight: 80,
                        overflowY: 'auto',
                        border: '1px solid rgba(255,255,255,0.05)',
                        borderRadius: 6,
                        padding: 4,
                    }}>
                        {events.slice(-8).reverse().map((e, i) => (
                            <div key={i} style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', marginBottom: 1 }}>
                                <span style={{ color: e.type === 'crisis' ? '#ff6b6b' : '#00ffd5', fontWeight: 600 }}>
                                    [{e.type}]
                                </span> {e.message}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Inspected Flight */}
            {inspectedFlight && (
                <div style={{
                    borderTop: '1px solid rgba(0,255,213,0.1)',
                    paddingTop: 8,
                }}>
                    <div style={{
                        color: '#00ffd5',
                        fontWeight: 700,
                        fontSize: 13,
                        marginBottom: 6,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                    }}>
                        <span>🔍 Flight {inspectedFlight.id}</span>
                        <button
                            onClick={() => setInspectedFlight(null)}
                            style={{
                                background: 'none', border: '1px solid rgba(255,255,255,0.1)',
                                color: 'rgba(255,255,255,0.4)', borderRadius: 4,
                                cursor: 'pointer', fontSize: 10, padding: '1px 6px',
                            }}
                        >✕</button>
                    </div>

                    {/* Flight stats grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
                        {[
                            ['Route', `${inspectedFlight.origin?.iata} → ${inspectedFlight.destination?.iata}`, '#00ffd5'],
                            ['Mode', inspectedFlight.mode, inspectedFlight.mode === 'LLM' ? '#ff6060' : '#00ffd5'],
                            ['Personality', inspectedFlight.personality, '#ff88ff'],
                            ['Risk Tolerance', `${((inspectedFlight.risk_tolerance || 0) * 100).toFixed(0)}%`, '#ffaa33'],
                            ['Fuel', `${inspectedFlight.fuel_level?.toFixed(1)}%`, inspectedFlight.fuel_level < 20 ? '#ff2222' : '#00c7ff'],
                            ['Progress', `${(inspectedFlight.progress * 100).toFixed(1)}%`, '#00ffd5'],
                            ['Distance', `${inspectedFlight.total_distance_km?.toFixed(0)} km`, 'rgba(255,255,255,0.5)'],
                            ['Fuel Burn', `${inspectedFlight.fuel_burn_rate?.toFixed(3)}/tick`, 'rgba(255,255,255,0.5)'],
                            ['Weather Risk', `${inspectedFlight.weather_risk?.toFixed(0)}%`, '#ff6b6b'],
                            ['Congestion', `${inspectedFlight.congestion_memory?.toFixed(0)}`, '#ff9f43'],
                            ['Nearby Flights', inspectedFlight.nearby_flights ?? 0, '#778beb'],
                            ['Dest Capacity', inspectedFlight.dest_capacity ?? '?', '#00c7ff'],
                            ['Negotiation', inspectedFlight.negotiation_status ?? '?', inspectedFlight.negotiation_status === 'HOLD_PATTERN' ? '#ffaa33' : '#00ffd5'],
                            ['Decisions', inspectedFlight.decision_count ?? 0, 'rgba(255,255,255,0.5)'],
                        ].map(([label, value, color]) => (
                            <div key={label} style={{ fontSize: 10 }}>
                                <span style={{ color: 'rgba(255,255,255,0.35)' }}>{label}: </span>
                                <span style={{ color, fontWeight: 600, fontFamily: 'monospace' }}>{value}</span>
                            </div>
                        ))}
                    </div>

                    {/* Action */}
                    <div style={{
                        marginTop: 6,
                        padding: 6,
                        borderRadius: 6,
                        background: `${actionColor(inspectedFlight.last_action)}11`,
                        border: `1px solid ${actionColor(inspectedFlight.last_action)}33`,
                    }}>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>Action:</div>
                        <div style={{ color: actionColor(inspectedFlight.last_action), fontWeight: 700, fontSize: 14 }}>
                            {inspectedFlight.last_action}
                        </div>
                        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>
                            {inspectedFlight.reasoning}
                        </div>
                    </div>

                    {/* Chain of Thought */}
                    {inspectedFlight.chain_of_thought && (
                        <div style={{
                            marginTop: 6,
                            padding: 6,
                            borderRadius: 6,
                            background: 'rgba(120,139,235,0.06)',
                            border: '1px solid rgba(120,139,235,0.12)',
                        }}>
                            <div style={{ fontSize: 10, color: '#778beb', fontWeight: 600, marginBottom: 3 }}>
                                🔗 Chain of Thought
                            </div>
                            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', lineHeight: 1.4 }}>
                                {inspectedFlight.chain_of_thought.split(' → ').map((step, i) => (
                                    <div key={i} style={{ marginBottom: 2, paddingLeft: 8, borderLeft: '2px solid rgba(120,139,235,0.2)' }}>
                                        {step}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Decision Timeline */}
                    <div style={{ marginTop: 6 }}>
                        <div
                            style={{
                                cursor: 'pointer',
                                fontSize: 11,
                                color: '#00ffd5',
                                fontWeight: 600,
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                            }}
                            onClick={() => setShowTimeline(!showTimeline)}
                        >
                            <span>📜 Decision Timeline ({history.length})</span>
                            <span style={{ fontSize: 14 }}>{showTimeline ? '▾' : '▸'}</span>
                        </div>
                        {showTimeline && history.length > 0 && (
                            <div style={{
                                maxHeight: 160,
                                overflowY: 'auto',
                                marginTop: 4,
                                paddingLeft: 8,
                                borderLeft: '2px solid rgba(0,255,213,0.1)',
                            }}>
                                {history.slice().reverse().map((d, i) => (
                                    <div key={i} style={{
                                        fontSize: 9,
                                        marginBottom: 3,
                                        padding: '3px 6px',
                                        borderRadius: 4,
                                        background: 'rgba(0,0,0,0.2)',
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: actionColor(d.action), fontWeight: 700 }}>{d.action}</span>
                                            <span style={{ color: 'rgba(255,255,255,0.2)' }}>tick {d.tick}</span>
                                        </div>
                                        <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 8, marginTop: 1 }}>
                                            Fuel: {d.fuel}% | Progress: {(d.progress * 100).toFixed(0)}% | Weather: {d.weather}%
                                        </div>
                                        <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 8 }}>
                                            {d.reason?.slice(0, 60)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

export default FlightInfoPanel
