/**
 * Obsidian Quants - Authenticated API Client
 * Fail-closed requests, latency tracking, 401 interceptor.
 */

export class ApiClient {
    constructor() {
        this.lastLatency = null;
    }

    async get(endpoint) {
        const start = performance.now();
        try {
            const resp = await fetch(endpoint, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json'
                }
            });
            this.lastLatency = performance.now() - start;

            if (resp.status === 401) {
                window.location.href = '/portal/login?expired=1';
                return { success: false, error: 'UNAUTHORIZED', status: 401 };
            }

            const data = await resp.json();
            return {
                success: resp.ok,
                status: resp.status,
                data: data,
                latency: this.lastLatency
            };
        } catch (err) {
            this.lastLatency = performance.now() - start;
            return {
                success: false,
                status: 0,
                error: err.message || 'NETWORK_ERROR',
                latency: this.lastLatency
            };
        }
    }

    async post(endpoint, body = {}) {
        const start = performance.now();
        try {
            const resp = await fetch(endpoint, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(body)
            });
            this.lastLatency = performance.now() - start;

            if (resp.status === 401) {
                window.location.href = '/portal/login?expired=1';
                return { success: false, error: 'UNAUTHORIZED', status: 401 };
            }

            const data = await resp.json();
            return {
                success: resp.ok,
                status: resp.status,
                data: data,
                latency: this.lastLatency
            };
        } catch (err) {
            this.lastLatency = performance.now() - start;
            return {
                success: false,
                status: 0,
                error: err.message || 'NETWORK_ERROR',
                latency: this.lastLatency
            };
        }
    }
}

export const api = new ApiClient();
