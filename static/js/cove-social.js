document.addEventListener('DOMContentLoaded', () => {
  initProductNav();
  initEnquireModal();
  initRelatedCarousels();
  let stopMotion = initSocialProductMotion();
  let stopLine = initSocialSectionImageMotion();
  window.addEventListener('pagehide', () => { stopMotion(); stopLine(); });
  window.addEventListener('pageshow', event => { if (event.persisted) { stopMotion = initSocialProductMotion(); stopLine = initSocialSectionImageMotion(); } });

  const finish = document.querySelector('.finish-detail');
  const finishSources = [...document.querySelectorAll('.swatch-grid button')].map(button => button.dataset.finishSrc || '');
  let finishTimer;
  document.querySelector('.swatch-grid button')?.setAttribute('aria-pressed', 'true');
  document.querySelectorAll('.swatch-grid button').forEach((button, i) => button.addEventListener('click', () => {
    document.querySelectorAll('.swatch-grid button').forEach(item => { item.classList.remove('active'); item.setAttribute('aria-pressed', 'false'); });
    button.classList.add('active');
    button.setAttribute('aria-pressed', 'true');
    // the enquiry form is optional on this page now, so its colour select may
    // not be there to keep in step with the swatch
    const colour = document.querySelector('#social-color');
    if (colour) colour.selectedIndex = i;
    if (!finish || !finishSources[i]) return;
    finish.classList.add('is-changing');
    clearTimeout(finishTimer);
    finishTimer = setTimeout(() => { finish.src = finishSources[i]; finish.alt = `${button.title || button.querySelector('img')?.alt || ''} upholstery detail`; finish.classList.remove('is-changing'); }, 180);
  }));

  // The enquiry section can be absent from a product page; everything below it
  // is the form's own behaviour, so there is nothing to wire up without it.
  const form = document.querySelector('#social-enquiry-form');
  if (!form) return;
  document.querySelectorAll('[data-resource]').forEach(link => link.addEventListener('click', () => {
    form.elements.message.value = `Please send me the ${link.dataset.resource} for Cove Social.`;
    form.querySelector('.form-message').textContent = 'This file is available on request. Send your details to our team by email.';
  }));
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const values = new FormData(form);
    const body = [...values.entries()].map(([key, value]) => `${key}: ${value}`).join('\n');
    window.location.href = `mailto:info@cofur.in?subject=${encodeURIComponent('Cove Social product enquiry')}&body=${encodeURIComponent(body)}`;
    form.querySelector('.form-message').textContent = 'Please send the enquiry from your email app. If it did not open, email info@cofur.in.';
  });
});

/** Moves the featured section images along the annotated visual route. */
function initSocialSectionImageMotion() {
  const page = document.querySelector('.social-page');
  if (!page || !window.gsap || !window.ScrollTrigger) return () => {};
  gsap.registerPlugin(ScrollTrigger);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = matchMedia('(max-width: 600px)');
  const anchorNames = ['hero', 'collage', 'applications', 'finish'];
  const anchors = anchorNames.map(name => page.querySelector(`[data-motion-anchor="${name}"]`)).filter(Boolean);
  // The travelling image needs a route: at least a section to leave and one to
  // arrive at. The rebuilt product page lays its images out directly, so with
  // nothing to pair the effect has nothing to do — and `images.at(-1)` inside
  // the ScrollTrigger below would throw on an empty list.
  if (anchors.length < 2) return () => {};
  const abort = new AbortController();
  const animations = [];
  const travelers = [];
  const images = anchors.map(anchor => anchor.matches('img') ? anchor : anchor.querySelector('img'));

  const smoothstep = value => {
    const progress = gsap.utils.clamp(0, 1, value);
    return progress * progress * (3 - 2 * progress);
  };

  function renderImageVisibility() {
    images.forEach((image, index) => {
      if (!image) return;
      const incoming = index === 0 ? 1 : smoothstep(((animations[index - 1]?.scrollTrigger?.progress || 0) - .82) / .18);
      const outgoing = index === images.length - 1 ? 1 : 1 - smoothstep((animations[index]?.scrollTrigger?.progress || 0) / .12);
      image.style.opacity = String(incoming * outgoing);
    });
  }

  const box = image => {
    const root = page.getBoundingClientRect();
    const rect = image.getBoundingClientRect();
    return {left: rect.left - root.left, top: rect.top - root.top, width: rect.width, height: rect.height};
  };

  if (!reduced.matches && !mobile.matches) {
    images.forEach((image, index) => { if (image) image.style.opacity = index ? '0' : '1'; });
    images.slice(0, -1).forEach((source, index) => {
      const target = images[index + 1];
      if (!source || !target) return;
      const traveler = document.createElement('div');
      traveler.className = 'social-image-traveler';
      traveler.setAttribute('aria-hidden', 'true');
      const sourceLayer = source.cloneNode(false);
      [sourceLayer].forEach(layer => {
        layer.removeAttribute('class');
        layer.removeAttribute('data-motion-anchor');
        layer.alt = '';
      });
      sourceLayer.style.objectFit = getComputedStyle(source).objectFit;
      sourceLayer.style.objectPosition = getComputedStyle(source).objectPosition;
      sourceLayer.style.opacity = '1';
      traveler.append(sourceLayer);
      traveler.style.opacity = '0';
      page.appendChild(traveler);
      travelers.push(traveler);

      const tween = gsap.fromTo(traveler,
        {left: () => box(source).left, top: () => box(source).top, width: () => box(source).width, height: () => box(source).height},
        {left: () => box(target).left, top: () => box(target).top, width: () => box(target).width, height: () => box(target).height, ease: 'none', scrollTrigger: {
          trigger: anchors[index],
          endTrigger: anchors[index + 1],
          start: 'bottom 50%',
          end: 'center 50%',
          scrub: .32,
          invalidateOnRefresh: true,
          onUpdate(self) {
            const progress = self.progress;
            const fadeOutStart = index === images.length - 2 ? .68 : .84;
            const fadeIn = smoothstep(progress / .1);
            const fadeOut = 1 - smoothstep((progress - fadeOutStart) / (1 - fadeOutStart));
            const targetTop = box(target).top;
            const sectionBoundaryFade = index === images.length - 2
              ? 1 - smoothstep((scrollY - (targetTop - innerHeight * .92)) / (innerHeight * .14))
              : 1;
            const edgeFade = Math.min(fadeIn, fadeOut, sectionBoundaryFade);
            const arc = Math.sin(progress * Math.PI);
            traveler.style.opacity = String(edgeFade);
            traveler.style.transform = `translate3d(0,${(-14 * arc).toFixed(2)}px,0) scale(${(1 + .008 * arc).toFixed(4)})`;
            traveler.style.filter = `drop-shadow(0 ${(12 * arc).toFixed(1)}px ${(24 * arc).toFixed(1)}px rgba(19,31,55,${(.10 * arc).toFixed(3)}))`;
            renderImageVisibility();
            if (index === images.length - 2 && sectionBoundaryFade <= .01) target.style.opacity = '1';
          }
        }}
      );
      animations.push(tween);
    });
    animations.push(ScrollTrigger.create({
      trigger: '#finishes',
      start: 'top 92%',
      onEnter: () => { travelers.forEach(traveler => { traveler.style.opacity = '0'; }); images.at(-1).style.opacity = '1'; },
      onEnterBack: () => { travelers.forEach(traveler => { traveler.style.opacity = '0'; }); images.at(-1).style.opacity = '1'; }
    }));
    renderImageVisibility();
  }
  const refresh = () => ScrollTrigger.refresh();
  page.querySelectorAll('img').forEach(image => { if (!image.complete) image.addEventListener('load', refresh, {once: true, signal: abort.signal}); });
  document.fonts?.ready.then(refresh);
  addEventListener('scroll', () => {
    if (scrollY <= 2) {
      travelers.forEach(traveler => { traveler.style.opacity = '0'; });
      images.forEach((image, index) => { if (image) image.style.opacity = index ? '0' : '1'; });
    }
  }, {passive: true, signal: abort.signal});
  addEventListener('orientationchange', refresh, {signal: abort.signal});

  return () => {
    abort.abort();
    animations.forEach(tween => { tween.scrollTrigger?.kill(); tween.kill?.(); });
    travelers.forEach(traveler => traveler.remove());
    images.forEach(image => { if (image) image.style.opacity = ''; });
  };
}

/** Page-local interaction lifecycle; product selection and enquiry logic stay above. */
function initSocialProductMotion() {
  const page = document.querySelector('.social-page');
  if (!page) return () => {};
  const abort = new AbortController();
  const on = (node, event, handler, options = {}) => node?.addEventListener(event, handler, {...options, signal: abort.signal});
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const desktop = matchMedia('(min-width: 901px)');
  const media = [];
  const scroller = page.querySelector('.social-gallery__scroller');
  const track = scroller.querySelector('.social-gallery__track');
  const slides = [...track.querySelectorAll('.gallery-slide')];
  const previous = page.querySelector('.gallery-arrow--prev');
  const next = page.querySelector('.gallery-arrow--next');
  // The gallery can be built with arrows only, so the progress strip is optional.
  const progress = page.querySelector('.gallery-progress');
  const status = page.querySelector('.gallery-status');
  let disposed = false, geometry = [], offsets = [], limit = 0, selected = 0;
  let motionFrame = 0, scrollFrame = 0, animationFrame = 0, wheelTimer = 0;
  let target = 0, drag = null, observer;
  const dots = !progress ? [] : slides.map((slide, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', `Show gallery image ${index + 1}`);
    on(button, 'click', () => go(index));
    return button;
  });
  progress?.replaceChildren(...dots);

  function renderStatus(index) {
    selected = index;
    slides.forEach((slide, i) => {
      slide.classList.toggle('is-active', i === index);
      slide.setAttribute('aria-hidden', i === index ? 'false' : 'true');
    });
    dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
      dot.setAttribute('aria-current', i === index ? 'true' : 'false');
    });
    previous.disabled = scroller.scrollLeft <= 1;
    next.disabled = scroller.scrollLeft >= limit - 1;
    status.textContent = `Gallery image ${index + 1} of ${slides.length}: ${slides[index].querySelector('figcaption').textContent}`;
  }
  function nearest(position) {
    return offsets.reduce((best, offset, i) => Math.abs(offset - position) < Math.abs(offsets[best] - position) ? i : best, 0);
  }
  function cancelMovement() {
    cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    clearTimeout(wheelTimer);
    scroller.classList.remove('is-moving');
    target = scroller.scrollLeft;
  }
  function moveTo(value, smooth = true) {
    cancelAnimationFrame(animationFrame);
    target = Math.max(0, Math.min(limit, value));
    if (reduced.matches || !smooth) {
      scroller.scrollLeft = target;
      scroller.classList.remove('is-moving');
      renderStatus(nearest(target));
      animationFrame = 0;
      return;
    }
    scroller.classList.add('is-moving');
    const origin = scroller.scrollLeft, distance = target - origin;
    const started = performance.now(), duration = Math.min(450, 180 + Math.abs(distance) * .25);
    function step(now) {
      if (disposed) return;
      const p = Math.min(1, (now - started) / duration);
      scroller.scrollLeft = origin + distance * (1 - Math.pow(1 - p, 3));
      if (p < 1) animationFrame = requestAnimationFrame(step);
      else {
        animationFrame = 0;
        scroller.classList.remove('is-moving');
        renderStatus(nearest(scroller.scrollLeft));
      }
    }
    animationFrame = requestAnimationFrame(step);
  }
  function go(index) {
    clearTimeout(wheelTimer);
    const i = Math.max(0, Math.min(slides.length - 1, index));
    renderStatus(i);
    moveTo(offsets[i]);
  }
  function updateMotion() {
    motionFrame = 0;
    geometry.forEach(({element, start, distance}) => {
      const p = desktop.matches && !reduced.matches ? Math.max(0, Math.min(1, (scrollY - start) / distance)) : 0;
      const amount = innerWidth < 1200 ? .012 : .025;
      element.style.setProperty('--social-image-scale', String(1 - amount * p));
      element.style.setProperty('--social-image-y', `${-4 * p}px`);
    });
  }
  function scheduleMotion() {
    if (!motionFrame) motionFrame = requestAnimationFrame(updateMotion);
  }
  function measure() {
    if (disposed) return;
    cancelMovement();
    // Whichever bar is present on this page owns the sticky offset: the site
    // header, the old sub-nav, or the product nav that replaced them.
    const bars = ['.site-header', '.social-subnav', '.product-nav']
      .map(selector => document.querySelector(selector)?.getBoundingClientRect().height || 0);
    const top = Math.ceil(Math.max(0, ...bars)) + 16;
    page.style.setProperty('--social-sticky-top', `${top}px`);
    geometry = media.map(element => {
      const parent = element.parentElement.getBoundingClientRect();
      return {element, start: parent.top + scrollY - top, distance: Math.max(1, parent.height - element.getBoundingClientRect().height)};
    });
    limit = Math.max(0, scroller.scrollWidth - scroller.clientWidth);
    const first = slides[0].offsetLeft;
    offsets = slides.map(slide => Math.max(0, Math.min(limit, slide.offsetLeft - first)));
    scroller.scrollLeft = offsets[selected];
    target = scroller.scrollLeft;
    renderStatus(selected);
    scheduleMotion();
  }
  on(previous, 'click', () => go(selected - 1));
  on(next, 'click', () => go(selected + 1));
  on(scroller, 'keydown', event => {
    const destinations = {ArrowLeft: selected - 1, ArrowRight: selected + 1, Home: 0, End: slides.length - 1};
    if (!(event.key in destinations)) return;
    event.preventDefault();
    go(destinations[event.key]);
  });
  on(scroller, 'scroll', () => {
    if (!scrollFrame) scrollFrame = requestAnimationFrame(() => {
      scrollFrame = 0;
      if (!animationFrame && !drag) renderStatus(nearest(scroller.scrollLeft));
      previous.disabled = scroller.scrollLeft <= 1;
      next.disabled = scroller.scrollLeft >= limit - 1;
    });
  }, {passive: true});
  on(scroller, 'wheel', event => {
    // Leave pinch zoom and horizontal trackpad gestures to the browser.
    if (event.ctrlKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
      cancelMovement();
      return;
    }
    const factor = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? scroller.clientWidth : 1;
    const delta = event.deltaY * factor;
    const position = animationFrame ? target : scroller.scrollLeft;
    if (!delta || delta < 0 && position <= 1 || delta > 0 && position >= limit - 1) return;
    event.preventDefault();
    moveTo(position + delta);
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => go(nearest(target)), 180);
  }, {passive: false});
  on(scroller, 'pointerdown', event => {
    cancelMovement();
    // Native touch scrolling supplies axis locking, swipe momentum and snapping.
    if (event.pointerType !== 'mouse' || event.button !== 0) return;
    drag = {id:event.pointerId, x:event.clientX, scroll:scroller.scrollLeft, lastX:event.clientX, time:performance.now(), velocity:0};
    scroller.classList.add('is-dragging');
    scroller.setPointerCapture(event.pointerId);
  });
  on(scroller, 'pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    const now = performance.now();
    drag.velocity = (drag.lastX - event.clientX) / Math.max(1, now - drag.time);
    drag.lastX = event.clientX; drag.time = now;
    scroller.scrollLeft = Math.max(0, Math.min(limit, drag.scroll + drag.x - event.clientX));
  });
  function endDrag(event) {
    if (!drag || drag.id !== event.pointerId) return;
    const momentum = event.type === 'pointercancel' || reduced.matches || performance.now() - drag.time > 100 ? 0 : Math.max(-240, Math.min(240, drag.velocity * 130));
    const destination = scroller.scrollLeft + momentum;
    const id = drag.id;
    drag = null;
    scroller.classList.remove('is-dragging');
    if (scroller.hasPointerCapture(id)) scroller.releasePointerCapture(id);
    go(nearest(destination));
  }
  on(scroller, 'pointerup', endDrag);
  on(scroller, 'pointercancel', endDrag);
  on(scroller, 'lostpointercapture', endDrag);
  on(window, 'scroll', scheduleMotion, {passive:true});
  on(window, 'resize', measure, {passive:true});
  on(reduced, 'change', measure);
  on(desktop, 'change', measure);
  on(document, 'visibilitychange', () => { if (document.hidden) cancelMovement(); });
  observer = new ResizeObserver(measure);
  [scroller, ...media.map(e => e.parentElement), document.querySelector('.site-header'), page.querySelector('.social-subnav')].filter(Boolean).forEach(e => observer.observe(e));
  document.fonts.ready.then(() => { if (!disposed) measure(); });
  measure();
  return () => {
    disposed = true;
    abort.abort();
    observer.disconnect();
    cancelMovement();
    cancelAnimationFrame(motionFrame);
    cancelAnimationFrame(scrollFrame);
    scroller.classList.remove('is-dragging');
    if (drag && scroller.hasPointerCapture(drag.id)) scroller.releasePointerCapture(drag.id);
    media.forEach(e => { e.style.removeProperty('--social-image-scale'); e.style.removeProperty('--social-image-y'); });
    page.style.removeProperty('--social-sticky-top');
    progress?.replaceChildren();
  };
}

/**
 * Product nav: the page's second bar.
 * The site header owns the top of the page. Once the banner has scrolled past,
 * the header steps aside and this bar slides in, marking the section in view.
 */
function initProductNav() {
  const nav = document.querySelector('.product-nav');
  if (!nav) return;
  const banner = document.querySelector('.pdp-banner');
  const header = document.querySelector('.site-header');
  const links = [...nav.querySelectorAll('.product-nav__links a')];
  const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);

  // Where the handover happens depends on what the page opens with. With a
  // banner it is just before the banner ends. Without one the site header owns
  // the top of the page, so the product bar waits until the header has scrolled
  // out of the way and takes over from there.
  const handoverPoint = () => (banner
    ? Math.max(0, banner.offsetHeight - nav.offsetHeight * 1.5)
    : Math.max(120, (header?.offsetHeight || 0) + 40));
  let frame = 0;
  const update = () => {
    frame = 0;
    const active = scrollY >= handoverPoint();
    nav.classList.toggle('is-active', active);
    // The header is hidden from the body rather than from the header element
    // itself, because the header is injected by the include after this runs.
    document.body.classList.toggle('is-product-nav', active);
  };
  addEventListener('scroll', () => { if (!frame) frame = requestAnimationFrame(update); }, {passive: true});
  addEventListener('resize', update, {passive: true});
  update();

  if (sections.length) {
    const mark = (index) => links.forEach((link, i) => link.classList.toggle('is-current', i === index));
    // rootMargin pulls the detection line just under the bar, so a section
    // counts as current from the moment its top clears the nav.
    const spy = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        mark(sections.indexOf(entry.target));
      });
    }, {rootMargin: '-96px 0px -60% 0px', threshold: 0});
    sections.forEach(section => spy.observe(section));
  }
}

/** Related products: one item in view per card, stepped by the arrow buttons. */
function initRelatedCarousels() {
  document.querySelectorAll('[data-related-carousel]').forEach(card => {
    const track = card.querySelector('.product-related__track');
    const items = track ? [...track.children] : [];
    const previous = card.querySelector('[data-prev]');
    const next = card.querySelector('[data-next]');
    if (items.length < 2) {
      previous?.setAttribute('disabled', '');
      next?.setAttribute('disabled', '');
      return;
    }
    let index = 0;
    const render = () => {
      track.style.transform = `translate3d(-${index * 100}%,0,0)`;
      // Items out of view are taken out of the tab order, or keyboard focus
      // scrolls the viewport sideways and the transform fights it.
      items.forEach((item, i) => {
        item.setAttribute('aria-hidden', i === index ? 'false' : 'true');
        item.querySelector('a')?.setAttribute('tabindex', i === index ? '0' : '-1');
      });
      previous.disabled = index === 0;
      next.disabled = index === items.length - 1;
    };
    previous.addEventListener('click', () => { index = Math.max(0, index - 1); render(); });
    next.addEventListener('click', () => { index = Math.min(items.length - 1, index + 1); render(); });
    render();
  });
}

/**
 * Enquiry popup. A native <dialog>, so the modal behaviour — focus trap,
 * Escape, backdrop, inertness of the page behind — comes from the browser.
 * Submitting hands the details to the visitor's email app, the same route the
 * old in-page form used.
 */
function initEnquireModal() {
  const modal = document.querySelector('.enquire-modal');
  if (!modal) return;
  const form = modal.querySelector('form');
  const note = modal.querySelector('.enquire-modal__note');
  const defaultNote = note?.textContent;
  let opener = null;

  const open = (event) => {
    opener = event.currentTarget;
    if (note) note.textContent = defaultNote;
    // showModal() is what makes it modal; .show() would leave the page live.
    if (typeof modal.showModal === 'function') modal.showModal();
    else modal.setAttribute('open', '');
    modal.querySelector('input')?.focus({preventScroll: true});
  };

  document.querySelectorAll('[data-enquire]').forEach(button => button.addEventListener('click', open));
  modal.querySelector('[data-enquire-close]')?.addEventListener('click', () => modal.close());
  // A click on the backdrop lands on the dialog itself, never on its panel.
  modal.addEventListener('click', event => { if (event.target === modal) modal.close(); });
  modal.addEventListener('close', () => opener?.focus({preventScroll: true}));

  form?.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const button = form.querySelector('[type=submit]');
    button.disabled = true;
    form.querySelectorAll('.field-error').forEach(el => el.remove());
    fetch(form.action, {method: 'POST', body: new FormData(form), headers: {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}, credentials: 'same-origin'})
      .then(response => response.json().then(data => ({ok: response.ok, data})))
      .then(({ok, data}) => {
        if (ok && data.ok) {
          if (note) note.textContent = data.message || 'Thank you. Our team will be in touch shortly.';
          form.querySelectorAll('input:not([type=hidden]),textarea').forEach(field => { field.value = ''; });
          setTimeout(() => modal.close(), 2200);
          return;
        }
        const errors = data.errors || {};
        Object.keys(errors).forEach(name => {
          const field = form.elements[name];
          const message = document.createElement('small');
          message.className = 'field-error';
          message.textContent = [].concat(errors[name]).join(' ');
          const host = (field && field.closest) ? field.closest('.field') : null;
          (host || form.querySelector('.enquire-modal__foot')).prepend(message);
        });
      })
      .catch(() => { if (note) note.textContent = 'Something went wrong. Please try again or email us.'; })
      .finally(() => { button.disabled = false; });
  });
}
