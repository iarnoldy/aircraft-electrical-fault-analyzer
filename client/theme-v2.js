/* Glass Cockpit theme adapter.
   - Mirrors voltage spans into vertical column gauges.
   - Drives the Diagnostic Results modal: opens when app.js populates any
     result section, closes via X button, backdrop click, or Esc key.
   No modifications to app.js; all coupling is via DOM observation.
*/
(function () {
    'use strict';

    // ---- Vertical gauge adapter -------------------------------------------
    function bindVGauge(vgaugeEl) {
        if (!vgaugeEl) return;
        const min = parseFloat(vgaugeEl.dataset.min);
        const max = parseFloat(vgaugeEl.dataset.max);
        const sourceEl = document.getElementById(vgaugeEl.dataset.source);
        if (!sourceEl || !isFinite(min) || !isFinite(max) || max <= min) return;

        const apply = () => {
            const raw = parseFloat(sourceEl.textContent);
            if (!isFinite(raw)) {
                vgaugeEl.style.setProperty('--fill', '0%');
                return;
            }
            const clamped = Math.max(min, Math.min(max, raw));
            const pct = ((clamped - min) / (max - min)) * 100;
            vgaugeEl.style.setProperty('--fill', pct.toFixed(2) + '%');
        };
        apply();
        new MutationObserver(apply).observe(sourceEl, {
            characterData: true, childList: true, subtree: true
        });
    }

    // ---- Results modal ----------------------------------------------------
    const MODAL_OPEN_CLASS = 'results-modal-open';
    const RESULT_SECTIONS = ['safetyWarnings', 'troubleshootingSteps', 'expectedResults', 'recommendations'];

    function hasVisibleResults() {
        return RESULT_SECTIONS.some((id) => {
            const el = document.getElementById(id);
            return el && el.style.display !== 'none';
        });
    }

    function openModal() {
        document.body.classList.add(MODAL_OPEN_CLASS);
        const modal = document.getElementById('resultsModal');
        if (modal) modal.setAttribute('aria-hidden', 'false');
    }

    function closeModal() {
        document.body.classList.remove(MODAL_OPEN_CLASS);
        const modal = document.getElementById('resultsModal');
        if (modal) modal.setAttribute('aria-hidden', 'true');
    }

    function wireModal() {
        const modal = document.getElementById('resultsModal');
        if (!modal) return;

        // Observe the four result-section divs for display changes driven by app.js.
        // When app.js sets display:block on any of them, open the modal.
        RESULT_SECTIONS.forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            new MutationObserver(() => {
                if (hasVisibleResults()) openModal();
            }).observe(el, { attributes: true, attributeFilter: ['style'] });
        });

        // Dismiss: any element with [data-modal-dismiss] (X button + backdrop)
        modal.querySelectorAll('[data-modal-dismiss]').forEach((el) => {
            el.addEventListener('click', closeModal);
        });

        // Dismiss: Esc key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.body.classList.contains(MODAL_OPEN_CLASS)) {
                closeModal();
            }
        });
    }

    // ---- Universal viewport-fit scaler ------------------------------------
    // Design target is 1600×900. Compute a uniform zoom factor so the whole
    // UI fills any resolution proportionally (Chrome/Edge/Safari/FF 126+).
    // Match the intrinsic content box: max-width 1560, natural stack ~780.
    // Anything wider/taller creates dead space; anything smaller triggers
    // horizontal clipping on < 16:9 viewports. Measured empirically.
    const DESIGN_W = 1560;
    const DESIGN_H = 780;

    function applyUiScale() {
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const scale = Math.min(vw / DESIGN_W, vh / DESIGN_H);
        // Set both: CSS var (for any rules that reference it) and the
        // zoom/transform fallback on body (more portable than CSS-var zoom).
        document.documentElement.style.setProperty('--ui-scale', scale.toFixed(4));
        // `zoom` on the root element scales layout cleanly in Chromium/Edge/
        // Safari and Firefox 126+. It's the simplest way to make the whole
        // page render at a uniform fraction of the viewport.
        document.documentElement.style.zoom = scale.toFixed(4);
    }

    function init() {
        document.body.classList.add('theme-cockpit');
        applyUiScale();
        window.addEventListener('resize', applyUiScale);
        document.querySelectorAll('.vgauge').forEach(bindVGauge);
        wireModal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
