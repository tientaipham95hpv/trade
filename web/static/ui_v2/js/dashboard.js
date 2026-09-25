/**
 * Obsidian Quants - Master Dashboard Coordinator
 * Coordinates tab switching, telemetry bar synchronization, and reactive rendering.
 */

import { store } from './state.js';
import { poller } from './polling.js';
import { Formatters } from './formatters.js';
import { renderOverview } from './overview.js';
import { renderPositions } from './positions.js';
import { renderRisk } from './risk.js';
import { renderActivity } from './activity.js';
import { renderSystem } from './system.js';

class DashboardApp {
    constructor() {
        this.viewContainer = document.getElementById('terminal-viewport');
        this.navLinks = document.querySelectorAll('.terminal-nav-link');
        this.clockEl = document.getElementById('telemetry-clock');
        this.envBadge = document.getElementById('telemetry-env');
        this.execBadge = document.getElementById('telemetry-exec');
        this.webBadge = document.getElementById('telemetry-web');
        this.tgBadge = document.getElementById('telemetry-tg');
        this.haltBadge = document.getElementById('telemetry-halt');
        this.recoveryBadge = document.getElementById('telemetry-recovery');
        this.latencyEl = document.getElementById('telemetry-latency');

        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupClock();
        this.setupLogout();

        // Subscribe to state updates
        store.subscribe((state) => {
            this.updateTelemetryBar(state);
            this.renderCurrentView(state);
        });

        // Start polling
        poller.start();
    }

    setupNavigation() {
        this.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tab = link.getAttribute('data-tab');
                if (tab) {
                    this.navLinks.forEach(l => l.classList.remove('terminal-nav-link--active'));
                    link.classList.add('terminal-nav-link--active');
                    store.setState({ activeTab: tab });
                }
            });
        });
    }

    setupClock() {
        const update = () => {
            if (this.clockEl) {
                const now = new Date();
                const utc = now.toISOString().replace('T', ' ').substring(11, 19) + ' UTC';
                this.clockEl.textContent = utc;
            }
        };
        update();
        setInterval(update, 1000);
    }

    setupLogout() {
        const logoutBtn = document.getElementById('btn-terminal-logout');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                try {
                    await fetch('/portal/logout', { method: 'GET', credentials: 'same-origin' });
                } catch {}
                window.location.href = '/portal/login';
            });
        }
    }

    updateTelemetryBar(state) {
        const status = state.status || {};
        const isHealthy = state.statusKnown && status.status === 'HEALTHY';
        const isHalted = state.statusKnown && (status.status === 'HALTED' || status.is_paused === true);

        // ENV
        if (this.envBadge) {
            const env = (status.environment || state.environment || 'UNKNOWN').toUpperCase();
            this.envBadge.textContent = env;
            let badgeClass = 'env-unknown env-badge--unknown';
            if (env === 'OFFLINE') badgeClass = 'env-offline env-badge--offline';
            else if (env === 'TESTNET') badgeClass = 'env-testnet env-badge--testnet';
            else if (env === 'LIVE') badgeClass = 'env-live env-badge--live';
            this.envBadge.className = `env-badge ${badgeClass}`;
        }

        // EXEC
        if (this.execBadge) {
            if (!state.statusKnown) {
                this.execBadge.textContent = 'UNKNOWN';
                this.execBadge.className = 'status-badge status-badge--degraded';
            } else if (isHalted) {
                this.execBadge.textContent = 'HALTED';
                this.execBadge.className = 'status-badge status-badge--halt';
            } else if (isHealthy) {
                this.execBadge.textContent = 'HEALTHY';
                this.execBadge.className = 'status-badge status-badge--healthy';
            } else {
                this.execBadge.textContent = status.status || 'DEGRADED';
                this.execBadge.className = 'status-badge status-badge--degraded';
            }
        }

        // WEB
        if (this.webBadge) {
            this.webBadge.textContent = 'READY';
            this.webBadge.className = 'status-badge status-badge--healthy';
        }

        // TELEGRAM
        if (this.tgBadge) {
            this.tgBadge.textContent = 'READY';
            this.tgBadge.className = 'status-badge status-badge--healthy';
        }

        // HALT
        if (this.haltBadge) {
            if (isHalted) {
                this.haltBadge.textContent = `ACTIVE (#${status.halt_generation || '1'})`;
                this.haltBadge.className = 'status-badge status-badge--halt';
            } else {
                this.haltBadge.textContent = 'INACTIVE';
                this.haltBadge.className = 'status-badge status-badge--healthy';
            }
        }

        // RECOVERY
        if (this.recoveryBadge) {
            if (status.recovery_required) {
                this.recoveryBadge.textContent = 'REQUIRED';
                this.recoveryBadge.className = 'status-badge status-badge--halt';
            } else {
                this.recoveryBadge.textContent = 'CLEAR';
                this.recoveryBadge.className = 'status-badge status-badge--healthy';
            }
        }

        // LATENCY
        if (this.latencyEl) {
            this.latencyEl.textContent = Formatters.latency(state.latency);
        }
    }

    renderCurrentView(state) {
        if (!this.viewContainer) return;

        switch (state.activeTab) {
            case 'overview':
                renderOverview(state, this.viewContainer);
                break;
            case 'positions':
                renderPositions(state, this.viewContainer);
                break;
            case 'risk':
                renderRisk(state, this.viewContainer);
                break;
            case 'activity':
                renderActivity(state, this.viewContainer);
                break;
            case 'system':
                renderSystem(state, this.viewContainer);
                break;
            default:
                renderOverview(state, this.viewContainer);
        }
    }
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    window.quantApp = new DashboardApp();
});
