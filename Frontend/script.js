document.addEventListener('DOMContentLoaded', () => {
  const navbar = document.querySelector('.navbar');
  const revealTargets = document.querySelectorAll('.feature-card, .team-card, .capability-item, .stat-tile, .macro-tile, .form-card');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (navbar) {
    const toggleNavbarShadow = () => {
      navbar.classList.toggle('navbar-elevated', window.scrollY > 10);
    };
    toggleNavbarShadow();
    window.addEventListener('scroll', toggleNavbarShadow, { passive: true });
  }

  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const targetSelector = anchor.getAttribute('href');
      if (!targetSelector || targetSelector.length < 2) return;

      const target = document.querySelector(targetSelector);
      if (!target) return;

      e.preventDefault();
      target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  });

  if (!reduceMotion && revealTargets.length > 0) {
    revealTargets.forEach((el) => el.classList.add('reveal'));

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    revealTargets.forEach((el, i) => {
      el.style.transitionDelay = `${Math.min(i * 35, 240)}ms`;
      observer.observe(el);
    });
  }
});
