export const API = 'http://localhost:8000'

export async function apiFetch(url, options = {}) {
  return fetch(url, options)
}
