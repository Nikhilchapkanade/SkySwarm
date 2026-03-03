import React, { useState, useEffect } from 'react'
import { apiFetch } from './api'

const panelWidth = 260

const btnStyle = (color) => ({
    padding: '7px 12px',
    border: `1px solid ${color}`,
    borderRadius: 8,
    background: 'transparent',
    color: color,
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: 12,
    transition: 'all 0.2s',
})

const sectionStyle = {
    borderLeft: '2px solid rgba(0,255,213,0.15)',
    paddingLeft: 10,
    marginBottom: 6,
}

const labelStyle = {
    color: 'rgba(255,255,255,0.4)',
    fontWeight: 700,
    fontSize: 10,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    marginBottom: 4,
}

const statRow = (label, value, color = '#00ffd5') => (
    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
        <span style={{ color: 'rgba(255,255,255,0.5)' }}>{label}</span>
        <span style={{ color, fontWeight: 600, fontFamily: 'monospace' }}>{value}</span>
    </div>
)

const ControlPanel = ({ analytics, comparison }) => {
    const [running, setRunning] = useState(false)
    const [mode, setMode] = useState('RULE')
    const [speed, setSpeed] = useState(1)

    const handleStart = async () => {
        await apiFetch('/api/start', { method: 'POST' })
        setRunning(true)
    }
    const handleReset = async () => {
        await apiFetch('/api/reset', { method: 'POST' })
        setRunning(false)
    }
    const toggleMode = async (m) => {
        setMode(m)
        await apiFetch('/api/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: m }),
        })
    }
    const spawn = async (n) => {
        await apiFetch('/api/spawn_many', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ n, mode }),
        })
    }
    const inject = async (type) => {
        await apiFetch('/api/inject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type }),
        })
    }
    const setSpeedApi = async (s) => {
        setSpeed(s)
        await apiFetch('/api/speed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ speed: s }),
        })
    }

    const a = analytics || {}
    const met = a.metrics || {}
    const personalities = a.personalities || {}
    const comp = comparison || {}

    return (
        <div style={{
            width: panelWidth,
            minWidth: panelWidth,
            flexShrink: 0,
            height: '100vh',
            background: 'rgba(7, 16, 41, 0.92)',
            backdropFilter: 'blur(16px)',
            borderRight: '1px solid rgba(0,255,213,0.1)',
            padding: '12px 10px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            zIndex: 10,
        }}>
            {/* Header */}
            <div style={{ color: '#00ffd5', fontWeight: 800, fontSize: 16, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                🛰 <span>Control Center</span>
            </div>

            {/* Sim state */}
            <div style={sectionStyle}>
                <div style={labelStyle}>Simulation</div>
                <div style={{ display: 'flex', gap: 6 }}>
                    <button style={btnStyle('#00ffd5')} onClick={handleStart}>▶ Start</button>
                    <button style={btnStyle('#ff507a')} onClick={handleReset}>↺ Reset</button>
                </div>
            </div>

            {/* Speed control */}
            <div style={sectionStyle}>
                <div style={labelStyle}>Speed</div>
                <div style={{ display: 'flex', gap: 4 }}>
                    {[0.5, 1, 2, 4].map(s => (
                        <button
                            key={s}
                            style={{
                                ...btnStyle(speed === s ? '#00ffd5' : '#555'),
                                background: speed === s ? 'rgba(0,255,213,0.15)' : 'transparent',
                                fontSize: 11,
                                padding: '4px 8px',
                            }}
                            onClick={() => setSpeedApi(s)}
                        >{s}x</button>
                    ))}
                </div>
            </div>

            {/* Mode toggle */}
            <div style={sectionStyle}>
                <div style={labelStyle}>Decision Engine (Agno)</div>
                <div style={{ display: 'flex', gap: 6 }}>
                    {['RULE', 'LLM'].map(m => (
                        <button
                            key={m}
                            style={{
                                ...btnStyle(m === mode ? (m === 'RULE' ? '#00ffd5' : '#ff6060') : '#555'),
                                background: m === mode ? 'rgba(0,255,213,0.12)' : 'transparent',
                                flex: 1,
                            }}
                            onClick={() => toggleMode(m)}
                        >
                            {m === 'RULE' ? '⚡ RULE' : '🧠 LLM'}
                        </button>
                    ))}
                </div>
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>
                    LLM = each flight queries Ollama via Agno
                </div>
            </div>

            {/* Spawn */}
            <div style={sectionStyle}>
                <div style={labelStyle}>Spawn Flights</div>
                <div style={{ display: 'flex', gap: 4 }}>
                    {[5, 10, 25, 50].map(n => (
                        <button key={n} style={btnStyle('#00ffd5')} onClick={() => spawn(n)}>+{n}</button>
                    ))}
                </div>
            </div>

            {/* Crisis injection */}
            <div style={sectionStyle}>
                <div style={labelStyle}>⚡ Inject Crisis</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <div style={{ display: 'flex', gap: 4 }}>
                        <button style={{ ...btnStyle('#ff6b6b'), flex: 1, fontSize: 10 }} onClick={() => inject('storm')}>🌩 Storm</button>
                        <button style={{ ...btnStyle('#ff6b6b'), flex: 1, fontSize: 10 }} onClick={() => inject('volcanic_ash')}>🌋 Volcanic</button>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                        <button style={{ ...btnStyle('#ff9f43'), flex: 1, fontSize: 10 }} onClick={() => inject('airport_shutdown')}>🚫 Shutdown</button>
                        <button style={{ ...btnStyle('#ff9f43'), flex: 1, fontSize: 10 }} onClick={() => inject('fuel_shortage')}>⛽ Fuel</button>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                        <button style={{ ...btnStyle('#e056fd'), flex: 1, fontSize: 10 }} onClick={() => inject('atc_strike')}>📡 ATC</button>
                        <button style={{ ...btnStyle('#e056fd'), flex: 1, fontSize: 10 }} onClick={() => inject('solar_flare')}>☀ Solar</button>
                    </div>
                    <button style={{ ...btnStyle('#778beb'), fontSize: 10 }} onClick={() => inject('airspace_closure')}>🔒 Airspace Closure</button>
                </div>
            </div>

            {/* Analytics */}
            <div style={sectionStyle}>
                <div style={labelStyle}>📊 Analytics</div>
                {statRow('Active Flights', a.active_flights ?? 0)}
                {statRow('Total Delays', a.total_delays ?? 0, '#ff9f43')}
                {statRow('Emergencies', a.emergency_landings ?? 0, '#ff507a')}
                {statRow('Holding', a.holding ?? 0, '#ffaa33')}
                {statRow('Rerouting', a.rerouting ?? 0, '#ff88ff')}
                {statRow('Avg Fuel', `${a.avg_fuel ?? 0}%`, '#00c7ff')}
                {statRow('Weather Cells', a.weather_cells ?? 0, '#ff6b6b')}
                {statRow('Tick', a.tick ?? 0, 'rgba(255,255,255,0.3)')}
            </div>

            {/* Personality distribution */}
            {Object.keys(personalities).length > 0 && (
                <div style={sectionStyle}>
                    <div style={labelStyle}>🎭 Personalities</div>
                    {Object.entries(personalities).map(([name, count]) => (
                        <div key={name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 1 }}>
                            <span style={{ color: 'rgba(255,255,255,0.5)' }}>{name}</span>
                            <span style={{ color: '#00ffd5', fontFamily: 'monospace' }}>{count}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* LLM Metrics */}
            <div style={sectionStyle}>
                <div style={labelStyle}>🧠 LLM Metrics</div>
                {statRow('Total Calls', met.llm_calls ?? 0)}
                {statRow('Total Tokens', met.llm_tokens ?? 0)}
                {statRow('Latency (ms)', met.llm_latency_ms ?? 0)}
                {statRow('Decisions', met.decisions ?? 0)}
                {met.llm_calls > 0 && statRow('Avg Latency', `${Math.round((met.llm_latency_ms || 0) / (met.llm_calls || 1))}ms`, '#ffaa33')}
            </div>

            {/* Comparison */}
            {(comp.rule || comp.llm) && (
                <div style={sectionStyle}>
                    <div style={labelStyle}>⚖ RULE vs LLM</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2, fontSize: 10 }}>
                        <span style={{ color: 'rgba(255,255,255,0.3)' }}></span>
                        <span style={{ color: '#00ffd5', fontWeight: 600, textAlign: 'center' }}>RULE</span>
                        <span style={{ color: '#ff6060', fontWeight: 600, textAlign: 'center' }}>LLM</span>

                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Flights</span>
                        <span style={{ color: '#00ffd5', textAlign: 'center', fontFamily: 'monospace' }}>{comp.rule?.total_flights ?? 0}</span>
                        <span style={{ color: '#ff6060', textAlign: 'center', fontFamily: 'monospace' }}>{comp.llm?.total_flights ?? 0}</span>

                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Emg Land</span>
                        <span style={{ color: '#00ffd5', textAlign: 'center', fontFamily: 'monospace' }}>{comp.rule?.emergency_landings ?? 0}</span>
                        <span style={{ color: '#ff6060', textAlign: 'center', fontFamily: 'monospace' }}>{comp.llm?.emergency_landings ?? 0}</span>

                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Holds</span>
                        <span style={{ color: '#00ffd5', textAlign: 'center', fontFamily: 'monospace' }}>{comp.rule?.holds ?? 0}</span>
                        <span style={{ color: '#ff6060', textAlign: 'center', fontFamily: 'monospace' }}>{comp.llm?.holds ?? 0}</span>

                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Reroutes</span>
                        <span style={{ color: '#00ffd5', textAlign: 'center', fontFamily: 'monospace' }}>{comp.rule?.reroutes ?? 0}</span>
                        <span style={{ color: '#ff6060', textAlign: 'center', fontFamily: 'monospace' }}>{comp.llm?.reroutes ?? 0}</span>

                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Avg Fuel Arrival</span>
                        <span style={{ color: '#00ffd5', textAlign: 'center', fontFamily: 'monospace' }}>{comp.rule?.avg_fuel_arrival ?? '—'}%</span>
                        <span style={{ color: '#ff6060', textAlign: 'center', fontFamily: 'monospace' }}>{comp.llm?.avg_fuel_arrival ?? '—'}%</span>
                    </div>
                </div>
            )}
        </div>
    )
}

export default ControlPanel
