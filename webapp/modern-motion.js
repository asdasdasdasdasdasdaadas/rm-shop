/* Cosmetic motion only: never delay navigation, payment, or input handling. */
(function () {
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  const active = new Set();
  const enabled = () => document.documentElement.dataset.design === 'modern' && !media.matches && !document.hidden;
  const ease = 'cubic-bezier(.22,1,.36,1)';
  function stop() {
    active.forEach(animation => animation.cancel());
    active.clear();
  }
  function animate(element, frames, duration, delay = 0) {
    if (!enabled() || !element || typeof element.animate !== 'function') return;
    const animation = element.animate(frames, {duration, delay, easing: ease, fill: 'backwards'});
    active.add(animation);
    animation.finished.then(() => active.delete(animation), () => active.delete(animation));
  }
  function enter(view, direction = 'fade') {
    stop();
    if (!enabled() || !view || view.classList.contains('hidden')) return;
    // Animate the heading and top-level surfaces, never both a card and its contents.
    const targets = [...view.querySelectorAll('.view-head,.modern-overview,.status-card,.section,.topup-card,.pay-methods,.ref-stats,.ref-actions,.dev-hero,.dev-info,.dev-link,.dev-fix,.dev-warn,.offer-stage,.support-faq')]
      .filter(el => !el.classList.contains('hidden') && !el.closest('[hidden]'))
      .filter((el, _, list) => !list.some(parent => parent !== el && parent.contains(el)))
      .filter(el => {const r = el.getBoundingClientRect();return r.height > 0 && r.top < innerHeight && r.bottom > 0;});
    if (!targets.length) targets.push(view);
    const x = direction === 'push' ? 18 : direction === 'pop' ? -12 : 0;
    targets.forEach((el, i) => animate(el, [
      {opacity: 0, transform: `translate3d(${x}px,${x ? 0 : 12}px,0) scale(.985)`},
      {opacity: 1, transform: 'translate3d(0,0,0) scale(1)'}
    ], 380, Math.min(i * 35, 140)));
  }
  function value(element) {
    // Keep the actual server value intact; no invented intermediate balances.
    if (!element || !element.getClientRects().length) return;
    active.forEach(animation => {
      if (animation.effect && animation.effect.target === element) { animation.cancel(); active.delete(animation); }
    });
    animate(element, [{opacity: .45, transform: 'translateY(5px)'}, {opacity: 1, transform: 'translateY(0)'}], 240);
  }
  window.WayMotion = {enter, value, stop};
  media.addEventListener?.('change', stop);
  document.addEventListener('visibilitychange', () => {if (document.hidden) stop();});
  window.addEventListener('appearancechange', () => {
    stop();
    if (enabled()) enter(document.querySelector('#app:not(.hidden) .view:not(.hidden)'));
  });
})();
