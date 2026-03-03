export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function apiFetch(path, opts) {
    const url = `${API_BASE}${path}`
    return fetch(url, opts)
}
