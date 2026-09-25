/**
 * Obsidian Quants - Terminal State Store
 * Centralized reactive state container with listener subscriptions.
 */

class StateStore {
    constructor() {
        this.state = {
            activeTab: 'overview',
            environment: 'OFFLINE',
            status: null,         // Authoritative status payload from /api/status
            statusKnown: false,   // True if execution service is reachable
            positions: [],        // Authoritative position list
            history: [],          // Order and trade history
            logs: [],             // System log stream
            latency: null,        // IPC/Network round trip
            lastUpdated: null,    // Timestamp of last successful status poll
            connectionStatus: 'INITIALIZING', // INITIALIZING, ONLINE, STALE, DISCONNECTED
            selectedPosition: null, // For detail drawer
        };
        this.listeners = new Set();
    }

    getState() {
        return this.state;
    }

    setState(patch) {
        this.state = { ...this.state, ...patch };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    notify() {
        for (const listener of this.listeners) {
            try {
                listener(this.state);
            } catch (err) {
                console.error('[StateStore] Listener error:', err);
            }
        }
    }
}

export const store = new StateStore();
