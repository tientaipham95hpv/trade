/**
 * Obsidian Quants - Numerical & Data Formatters
 * Institutional precision, tabular numerals, fail-closed null safety.
 */

export const Formatters = {
    /**
     * Formats currency or monetary value with fixed decimals.
     * Displays '—' for null/undefined/NaN.
     */
    currency(val, decimals = 2, prefix = '$') {
        if (val === null || val === undefined || val === '' || isNaN(Number(val))) {
            return '—';
        }
        const num = Number(val);
        const parts = num.toFixed(decimals).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        return `${prefix}${parts.join('.')}`;
    },

    /**
     * Formats PnL with explicit '+' sign and tabular alignment.
     */
    pnl(val, decimals = 2, prefix = '$') {
        if (val === null || val === undefined || val === '' || isNaN(Number(val))) {
            return { text: '—', className: 'text-secondary' };
        }
        const num = Number(val);
        const formatted = this.currency(Math.abs(num), decimals, prefix);
        if (num > 0) {
            return { text: `+${formatted}`, className: 'text-profit' };
        } else if (num < 0) {
            return { text: `-${formatted}`, className: 'text-loss' };
        }
        return { text: formatted, className: 'text-secondary' };
    },

    /**
     * Formats percentage with '+' sign if positive.
     */
    percent(val, decimals = 2) {
        if (val === null || val === undefined || val === '' || isNaN(Number(val))) {
            return { text: '—', className: 'text-secondary' };
        }
        const num = Number(val);
        const text = `${num >= 0 ? '+' : ''}${num.toFixed(decimals)}%`;
        const className = num > 0 ? 'text-profit' : (num < 0 ? 'text-loss' : 'text-secondary');
        return { text, className };
    },

    /**
     * Formats decimal numbers with strict thousands separators.
     */
    number(val, decimals = 4) {
        if (val === null || val === undefined || val === '' || isNaN(Number(val))) {
            return '—';
        }
        const num = Number(val);
        const parts = num.toFixed(decimals).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        return parts.join('.');
    },

    /**
     * Formats timestamp in ISO or HH:mm:ss format.
     */
    timestamp(val) {
        if (!val) return '—';
        try {
            const d = new Date(val);
            if (isNaN(d.getTime())) return String(val);
            return d.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        } catch {
            return String(val);
        }
    },

    /**
     * Formats latency in milliseconds.
     */
    latency(ms) {
        if (ms === null || ms === undefined || isNaN(Number(ms))) {
            return '— ms';
        }
        return `${Math.round(Number(ms))} ms`;
    },

    /**
     * Sanitizes sensitive text by redacting tokens, keys, passwords.
     */
    sanitize(str) {
        if (typeof str !== 'string') return str;
        return str
            .replace(/(bearer\s+)[a-zA-Z0-9_\-\.]{10,}/gi, '$1[REDACTED]')
            .replace(/(token["']?\s*[:=]\s*["']?)[a-zA-Z0-9_\-\.]{10,}/gi, '$1[REDACTED]')
            .replace(/(api[_-]?key["']?\s*[:=]\s*["']?)[a-zA-Z0-9_\-\.]{10,}/gi, '$1[REDACTED]')
            .replace(/(secret["']?\s*[:=]\s*["']?)[a-zA-Z0-9_\-\.]{10,}/gi, '$1[REDACTED]')
            .replace(/(password["']?\s*[:=]\s*["']?)[^\s,"']+/gi, '$1[REDACTED]');
    },

    /**
     * Escape HTML entities to prevent XSS.
     */
    escapeHtml(str) {
        if (!str) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(str).replace(/[&<>"']/g, m => map[m]);
    }
};
