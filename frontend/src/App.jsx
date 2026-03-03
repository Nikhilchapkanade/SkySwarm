import React, { useState, useEffect } from 'react'
import GlobeComponent from './Globe'
import ControlPanel from './ControlPanel'
import FlightInfoPanel from './FlightInfoPanel'
import { apiFetch } from './api'

const App = () => {
    const [selectedFlightId, setSelectedFlightId] = useState(null)
    const [analytics, setAnalytics] = useState({})
    const [comparison, setComparison] = useState({})
    const [backendOk, setBackendOk] = useState(false)

    // Poll analytics + comparison + backend health
    useEffect(() => {
        let mounted = true
        const poll = async () => {
            try {
                const [aRes, cRes] = await Promise.all([
                    apiFetch('/api/analytics'),
                    apiFetch('/api/comparison'),
                ])
                const aJson = await aRes.json()
                const cJson = await cRes.json()
                if (mounted) {
                    setAnalytics(aJson)
                    setComparison(cJson)
                    setBackendOk(true)
                }
            } catch (_) {
                if (mounted) setBackendOk(false)
            }
        }
        const id = setInterval(poll, 2000)
        poll()
        return () => { mounted = false; clearInterval(id) }
    }, [])

    return (
        <div style={{
            display: 'flex',
            width: '100vw',
            height: '100vh',
            overflow: 'hidden',
            background: '#071029',
        }}>
            <ControlPanel analytics={analytics} comparison={comparison} />
            <div style={{ flex: 1, position: 'relative', minWidth: 0, overflow: 'hidden' }}>
                <GlobeComponent onSelect={(id) => setSelectedFlightId(id)} />
            </div>
            <FlightInfoPanel selectedFlightId={selectedFlightId} backendOk={backendOk} />
        </div>
    )
}

export default App
