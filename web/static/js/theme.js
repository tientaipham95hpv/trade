// === DUAL THEME PERSISTENT CONTROLLER ===
function initTheme() {
    const savedTheme = localStorage.getItem('astra-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButtonText(savedTheme);
}

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('astra-theme', next);
    updateThemeButtonText(next);
    
    // Trigger chart re-draw if chart engine exists
    if (window.renderAstraChart) {
        window.renderAstraChart();
    }
}

function updateThemeButtonText(theme) {
    const btns = document.querySelectorAll('.btn-theme-toggle');
    btns.forEach(btn => {
        const icon = btn.querySelector('.theme-toggle-icon');
        const label = btn.querySelector('.theme-toggle-label');
        if (icon) icon.dataset.mode = theme === 'dark' ? 'light' : 'dark';
        if (label) label.textContent = theme === 'dark' ? 'Light' : 'Cyberpunk';
        btn.setAttribute('aria-label', theme === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện Cyberpunk');
    });
}

// Mobile sidebar drawer toggle
function toggleMobileSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.mobile-overlay');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
    if (overlay) {
        overlay.classList.toggle('active');
    }
}

// Mobile client nav toggle
function toggleMobileNav() {
    const nav = document.querySelector('.client-nav-links');
    const toggle = document.querySelector('.mobile-nav-toggle');
    if (nav) {
        nav.classList.toggle('mobile-open');
        if (toggle) toggle.setAttribute('aria-expanded', nav.classList.contains('mobile-open') ? 'true' : 'false');
    }
}

document.addEventListener('DOMContentLoaded', initTheme);
