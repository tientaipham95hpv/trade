/**
 * Obsidian Quants - Polling Manager
 * Controlled polling with concurrency guards, visibility awareness, and stale detection.
 */

import { api } from './api.js';
import { store } from './state.js';

export class PollingManager {
    constructor() {
        this.statusInterval = 5000;    // 5 seconds for core status & positions
        this.activityInterval = 10000; // 10 seconds for history & logs
        this.statusTimer = null;
        this.activityTimer = null;

        this.inFlight = {
            status: false,
            history: false,
            logs: false,
        };

        this.consecutiveFailures = 0;
        this.isTabActive = !document.hidden;

        this.setupVisibilityListener();
    }

    setupVisibilityListener() {
        document.addEventListener('visibilitychange', () => {
            this.isTabActive = !document.hidden;
            if (this.isTabActive) {
                // Instantly poll on focus
                this.pollStatus();
                this.pollActivity();
            }
        });
    }

    start() {
        this.pollStatus();
        this.pollActivity();

        this.statusTimer = setInterval(() => {
            if (this.isTabActive) this.pollStatus();
        }, this.statusInterval);

        this.activityTimer = setInterval(() => {
            if (this.isTabActive) this.pollActivity();
        }, this.activityInterval);
    }

    stop() {
        if (this.statusTimer) clearInterval(this.statusTimer);
        if (this.activityTimer) clearInterval(this.activityTimer);
    }

    async pollStatus() {
        if (this.inFlight.status) return;
        this.inFlight.status = true;

        try {
            const res = await api.get('/api/status');
            if (res.success && res.data) {
                this.consecutiveFailures = 0;
                const data = res.data;

                // Normalize positions into an array
                let positionsList = [];
                if (Array.isArray(data.positions)) {
                    positionsList = data.positions;
                } else if (data.positions && typeof data.positions === 'object') {
                    positionsList = Object.entries(data.positions).map(([k, v]) => {
                        return typeof v === 'object' && v !== null ? { symbol: k, ...v } : { symbol: k, raw: v };
                    });
                }

                store.setState({
                    status: data,
                    statusKnown: data.status === 'HEALTHY' || data.status === 'HALTED',
                    positions: positionsList,
                    environment: data.mode === 'LIVE' ? 'LIVE' : (data.mode === 'TESTNET' ? 'TESTNET' : 'OFFLINE'),
                    latency: res.latency,
                    lastUpdated: new Date(),
                    connectionStatus: 'ONLINE',
                });
            } else {
                this.consecutiveFailures++;
                store.setState({
                    latency: res.latency,
                    connectionStatus: this.consecutiveFailures > 2 ? 'DISCONNECTED' : 'STALE',
                    statusKnown: false,
                });
            }
        } catch (err) {
            this.consecutiveFailures++;
            store.setState({
                connectionStatus: this.consecutiveFailures > 2 ? 'DISCONNECTED' : 'STALE',
                statusKnown: false,
            });
        } finally {
            this.inFlight.status = false;
        }
    }

    async pollActivity() {
        if (this.inFlight.history || this.inFlight.logs) return;
        this.inFlight.history = true;
        this.inFlight.logs = true;

        try {
            const [histRes, logsRes] = await Promise.all([
                api.get('/api/history'),
                api.get('/api/logs?limit=50')
            ]);

            const patch = {};
            if (histRes.success && Array.isArray(histRes.data)) {
                patch.history = histRes.data;
            } else if (histRes.success && histRes.data && Array.isArray(histRes.data.history)) {
                patch.history = histRes.data.history;
            }

            if (logsRes.success && Array.isArray(logsRes.data)) {
                patch.logs = logsRes.data;
            } else if (logsRes.success && logsRes.data && Array.isArray(logsRes.data.logs)) {
                patch.logs = logsRes.data.logs;
            }

            if (Object.keys(patch).length > 0) {
                store.setState(patch);
            }
        } catch (err) {
            // Fail silent on background activity poll
        } finally {
            this.inFlight.history = false;
            this.inFlight.logs = false;
        }
    }
}

export const poller = new PollingManager();
