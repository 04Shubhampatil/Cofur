function initSite(){
  const header=document.querySelector('.site-header'),menu=document.querySelector('.menu-btn'),links=document.querySelector('.nav-links'),mega=document.querySelector('.mega-menu'),trigger=document.querySelector('[data-mega-trigger]');
  // Pages whose first section is a full-bleed banner: the header sits over the
  // photograph instead of on a band above it. The product page opens on content
  // now, so a white logo on a dark wash would sit on a white page.
  if(['home','cove-collection','about','enquiry','soft-seating'].includes(document.body.dataset.page))header?.classList.add('overlay');
  if(header){const setStuck=()=>header.classList.toggle('is-stuck',(window.scrollY||document.documentElement.scrollTop)>40);setStuck();addEventListener('scroll',setStuck,{passive:true});}
  // Banners with a mobile crop may carry their own alt text for that crop.
  const mobileAltQuery=window.matchMedia('(max-width:767px)');
  const applyBannerAlt=()=>document.querySelectorAll('img[data-mobile-alt]').forEach(img=>{if(!img.dataset.desktopAlt)img.dataset.desktopAlt=img.alt;img.alt=mobileAltQuery.matches?img.dataset.mobileAlt:img.dataset.desktopAlt;});
  applyBannerAlt();mobileAltQuery.addEventListener?.('change',applyBannerAlt);
  document.querySelectorAll('.cove-card img[data-hover-src]').forEach(img=>{
    const hoverImg=img.cloneNode();
    hoverImg.src=img.dataset.hoverSrc;
    hoverImg.removeAttribute('data-hover-src');
    hoverImg.className='cove-hover-image';
    hoverImg.alt='';
    img.classList.add('cove-base-image');
    img.closest('.cove-card-media')?.append(hoverImg);
  });
  // Touch screens never fire hover, so the room shot would be unreachable on a
  // phone. Holding a card shows it instead — the same gesture the related
  // product cards already answer to. Sliding a finger means the visitor is
  // scrolling, so the card returns to its cut-out.
  if(matchMedia('(hover:none)').matches){
    // every product card type, not just the collection ones: the gesture has
    // to do the same thing wherever a card shows a room shot on hover
    document.querySelectorAll('.cove-card, .social-related .product-card, .related-card').forEach(card=>{
      const hold=()=>card.classList.add('is-held'),release=()=>card.classList.remove('is-held');
      card.addEventListener('touchstart',hold,{passive:true});
      ['touchend','touchcancel','touchmove'].forEach(evt=>card.addEventListener(evt,release,{passive:true}));
    });
  }
  // The home category cards open on their own instead: a phone has no hover,
  // and asking someone to press and hold hides the subtitle behind a gesture
  // nobody is told about. Scrolling a card into view opens it and scrolling it
  // away closes it, so the page shows the same thing a desktop hover does —
  // including on a refresh, where whatever is already on screen opens at once.
  if(matchMedia('(hover:none)').matches&&'IntersectionObserver'in window){
    const rail=document.querySelectorAll('.range-card');
    if(rail.length){
      const io=new IntersectionObserver(entries=>entries.forEach(entry=>entry.target.classList.toggle('is-inview',entry.isIntersecting)),{threshold:.6});
      rail.forEach(card=>io.observe(card));
    }
  }
  const closeMega=()=>{mega?.classList.remove('open');mega?.setAttribute('aria-hidden','true');trigger?.setAttribute('aria-expanded','false')};
  trigger?.addEventListener('click',()=>{const open=mega?.classList.toggle('open');mega?.setAttribute('aria-hidden',String(!open));trigger?.setAttribute('aria-expanded',String(open))});
  trigger?.addEventListener('mouseenter',()=>{if(innerWidth>900){mega?.classList.add('open');mega?.setAttribute('aria-hidden','false');trigger.setAttribute('aria-expanded','true')}});
  header?.addEventListener('mouseleave',()=>{if(innerWidth>900)closeMega()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMega();links?.classList.remove('open')}});
  menu?.addEventListener('click',()=>{const open=links.classList.toggle('open');menu.classList.toggle('open',open);menu.setAttribute('aria-expanded',String(open));if(!open)closeMega()});
  document.querySelectorAll('.thumbs img').forEach(img=>img.addEventListener('click',()=>{document.querySelector('.gallery-main').src=img.src;document.querySelectorAll('.thumbs img').forEach(x=>x.classList.remove('active'));img.classList.add('active')}));
  document.querySelectorAll('[data-tab]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('[data-tab],.tab-panel').forEach(x=>x.classList.remove('active'));btn.classList.add('active');document.querySelector('#'+btn.dataset.tab)?.classList.add('active')}));
  const form=document.querySelector('#enquiry-form');form?.addEventListener('submit',e=>{
    if(!form.checkValidity()){e.preventDefault();form.reportValidity();return}
    if(!window.fetch||!form.action)return; // fall back to a normal POST
    e.preventDefault();
    const button=form.querySelector('[type=submit]');const status=form.querySelector('.form-message');
    button.disabled=true;
    form.querySelectorAll('.field-error').forEach(el=>el.remove());
    fetch(form.action,{method:'POST',body:new FormData(form),headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'},credentials:'same-origin'})
      .then(r=>r.json().then(data=>({ok:r.ok,data})))
      .then(({ok,data})=>{
        if(ok&&data.ok){status.textContent=data.message||status.textContent;status.classList.add('show');form.reset();return}
        const errors=data.errors||{};
        Object.keys(errors).forEach(name=>{const field=form.elements[name];const msg=document.createElement('small');msg.className='field-error';msg.textContent=[].concat(errors[name]).join(' ');if(field&&field.closest){field.closest('.cfield')?.append(msg)}else{form.querySelector('.contact-submit')?.prepend(msg)}});
      })
      .catch(()=>{status.textContent='Something went wrong. Please try again or email us.';status.classList.add('show')})
      .finally(()=>{button.disabled=false});
  });
  document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',e=>{const href=a.getAttribute('href');if(href==='#')return;const target=document.querySelector(href);if(target){e.preventDefault();target.scrollIntoView({behavior:'smooth',block:'start'})}}));
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.querySelectorAll('main h1:not([data-static-title]),main h2:not([data-static-title]),main h3:not([data-static-title])').forEach(title => {
      title.setAttribute('aria-label', title.innerText.replace(/\n/g, ' '));
      const walker = document.createTreeWalker(title, NodeFilter.SHOW_TEXT);
      const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(node => {
        const fragment = document.createDocumentFragment();
        node.textContent.split(/(\s+)/).forEach(word => {
          if (!word.trim()) {fragment.append(document.createTextNode(word)); return;}
          const wrapper = document.createElement('span'); wrapper.className = 'title-word'; wrapper.setAttribute('aria-hidden', 'true');
          Array.from(word).forEach(char => {const span = document.createElement('span'); span.className = 'title-char'; span.textContent = char; wrapper.append(span)});
          fragment.append(wrapper);
        });
        node.replaceWith(fragment);
      });
    });
  }
  if(window.gsap&&window.ScrollTrigger&&!matchMedia('(prefers-reduced-motion: reduce)').matches){gsap.registerPlugin(ScrollTrigger);const intro=gsap.timeline({defaults:{ease:'power3.out'}});intro.from('.site-header',{y:-28,autoAlpha:0,duration:.7});const heroes=document.querySelectorAll('.hero h1,.series-title,.enquiry-hero h1');if(heroes.length)intro.from(heroes,{y:45,autoAlpha:0,duration:1},'-.25');gsap.utils.toArray('.reveal').forEach((el,i)=>{gsap.set(el,{autoAlpha:0,y:55});gsap.to(el,{autoAlpha:1,y:0,duration:.95,ease:'power3.out',scrollTrigger:{trigger:el,start:'top 88%',once:true},delay:(i%3)*.05})});gsap.utils.toArray('[data-parallax]').forEach(el=>gsap.to(el,{yPercent:10,scale:1.05,ease:'none',scrollTrigger:{trigger:el.parentElement,start:'top top',end:'bottom top',scrub:.8}}));gsap.utils.toArray('.rule-label span').forEach(line=>gsap.from(line,{scaleX:0,transformOrigin:'left',duration:1,scrollTrigger:{trigger:line,start:'top 90%',once:true}}));
    const motion = gsap.matchMedia();
    motion.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', () => {
      const section = document.querySelector('.collection-story');
      if (!section) return;
      section.classList.add('is-scrolling');
      const track = section.querySelector('.collection-stage');
      const cards = [...section.querySelectorAll('.collection-slide')];
      const distance = () => track.scrollWidth - section.clientWidth;
      const horizontal = gsap.to(track, {
        x: () => -distance(), ease: 'none',
        scrollTrigger: {trigger: section, start: 'top top', end: 'bottom bottom', scrub: .7, invalidateOnRefresh: true}
      });
      cards.forEach((card, index) => {
        const trigger = index === 0
          ? {trigger: section, start: 'top 70%', once: true}
          : {trigger: card, containerAnimation: horizontal, start: 'left 95%', toggleActions: 'play complete play reverse'};
        gsap.from(card.querySelector('.collection-visual img'), {scale: 1.12, duration: 1.15, ease: 'power3.out', scrollTrigger: trigger});
        gsap.from(card.querySelector('.collection-detail img'), {immediateRender: false, clipPath: 'inset(0 100% 0 0)', scale: 1.12, duration: 1.15, ease: 'power3.out', scrollTrigger: trigger});
        gsap.from(card.querySelectorAll('.title-char'), {immediateRender: false, y: 49, opacity: 0, stagger: .025, duration: .75, ease: 'power3.out', scrollTrigger: trigger});
      });
      return () => section.classList.remove('is-scrolling');
    });
    gsap.utils.toArray('main h1,main h2,main h3').filter(el => !el.closest('.collection-story') && el.querySelector('.title-char')).forEach(el => {
      el.classList.remove('reveal');
      gsap.from(el.querySelectorAll('.title-char'), {y: 40, opacity: 0, stagger: .022, duration: .8, ease: 'power3.out', scrollTrigger: {trigger: el, start: 'top 90%', once: true}});
    });
    initSectionMotion(motion);
    initHomeMotion(motion);
    initAboutMotion(motion);
    document.fonts.ready.then(() => ScrollTrigger.refresh());
    window.addEventListener('load', () => ScrollTrigger.refresh(), {once: true});
  }else document.querySelectorAll('.reveal').forEach(x=>x.style.visibility='visible');
}
/* --------------------------------------------------------------------------
   Scroll motion
   --------------------------------------------------------------------------
   Three kinds of motion, kept apart on purpose:

   1. ENTRANCE  — fires once as a block arrives, then the element is left
                  alone. Cheap, and right for text and cards.
   2. PROGRESS  — tied to scroll position and scrubbed, so the image keeps
                  answering the scroll rather than playing a canned clip. Used
                  only for large photography, where it is worth the cost.
   3. PINNED    — already owned by the statement sequence and the collection
                  story. Nothing new is pinned here: a page that holds still
                  twice feels broken, and pinning is the first thing to fail
                  on a phone.

   Each tier is registered through gsap.matchMedia, so a phone is not handed a
   shrunken desktop animation and a reduced-motion visitor gets opacity only,
   with every pixel of content still present.

   The hidden state is always set from JavaScript, never CSS. If this file
   fails to load the page reads normally instead of showing blank space.
   -------------------------------------------------------------------------- */

// Anything an existing timeline already drives, or that owns its own state.
// Animating one element twice reads as a stutter.
const MOTION_SKIP = [
  '.reveal', '[data-parallax]', '.hero', '.page-banner', '.statement-story', '.collection-story',
  '.featured-stage', '.testimonial-window', '.line-cta', '.range-card', '.cove-card',
  '.range-rail__track', '.mosaic', '.about-value', '.site-header', '.cofur-footer',
].join(',');

function motionBlocks() {
  // Walk the page rather than relying on hand-tagged classes: only three
  // elements site-wide carried `reveal`, so most sections had no motion and a
  // new template would have had none either.
  const groups = [];
  document.querySelectorAll('main > section, main > * > section').forEach(section => {
    if (section.matches(MOTION_SKIP) || section.closest('.statement-story,.collection-story')) return;
    // Sections usually wrap their content in a container; animating that keeps
    // full-bleed backgrounds still while the content moves.
    const scope = section.querySelector(':scope > .container') || section;
    const blocks = [...scope.children].filter(child =>
      !child.matches(MOTION_SKIP) && !child.closest(MOTION_SKIP) && child.getBoundingClientRect().height > 0
    );
    if (blocks.length) groups.push({section, blocks});
  });
  return groups;
}

function initSectionMotion(motion) {
  const groups = motionBlocks();

  // ---- entrance: the same choreography, a shorter throw on small screens ----
  const entrance = distance => () => {
    groups.forEach(({section, blocks}) => {
      gsap.set(blocks, {autoAlpha: 0, y: distance});
      gsap.to(blocks, {
        autoAlpha: 1, y: 0, duration: .85, ease: 'power3.out', stagger: .09,
        scrollTrigger: {trigger: section, start: 'top 88%', once: true},
      });
    });
    return () => gsap.set(groups.flatMap(g => g.blocks), {clearProps: 'opacity,visibility,transform'});
  };
  motion.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', entrance(38));
  motion.add('(max-width: 900px) and (prefers-reduced-motion: no-preference)', entrance(22));

  // Reduced motion still gets the content, just without the travel.
  motion.add('(prefers-reduced-motion: reduce)', () => {
    groups.forEach(({section, blocks}) => {
      gsap.set(blocks, {autoAlpha: 0});
      gsap.to(blocks, {autoAlpha: 1, duration: .4, stagger: .05, scrollTrigger: {trigger: section, start: 'top 92%', once: true}});
    });
  });

  // ---- progress: large photography answers the scroll continuously ----
  // Desktop only. On a phone the same scrub costs more than it shows, and the
  // banner is most of the screen, so dimming it as you read is a nuisance.
  motion.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', () => {
    gsap.utils.toArray('.page-banner').forEach(banner => {
      gsap.to(banner, {
        scale: .96, opacity: .55, ease: 'none', transformOrigin: '50% 0%',
        scrollTrigger: {trigger: banner, start: 'top top', end: 'bottom top', scrub: .6},
      });
    });
    // The home hero holds still while it is read, then eases back as the page
    // scrolls over it — a settle, not a zoom.
    gsap.utils.toArray('.hero-slides').forEach(slides => {
      gsap.to(slides, {
        scale: 1.04, yPercent: 4, ease: 'none',
        scrollTrigger: {trigger: slides.closest('.hero') || slides, start: 'top top', end: 'bottom top', scrub: .8},
      });
    });
  });

  // Category photography settles into its frame as the card arrives: 1.04 -> 1,
  // scrubbed, so it tracks the scroll instead of playing to its own clock.
  motion.add('(min-width: 769px) and (prefers-reduced-motion: no-preference)', () => {
    gsap.utils.toArray('.range-card > a > img').forEach(img => {
      gsap.fromTo(img, {scale: 1.04}, {
        scale: 1, ease: 'none',
        scrollTrigger: {trigger: img.closest('.range-card'), start: 'top 95%', end: 'top 45%', scrub: .7},
      });
    });
  });

  // Smaller photographs elsewhere: a single settle on arrival, no scrub.
  motion.add('(prefers-reduced-motion: no-preference)', () => {
    gsap.utils.toArray('main figure img, .contact-card img, .team-card img').forEach(img => {
      if (img.closest(MOTION_SKIP)) return;
      gsap.from(img, {scale: 1.06, duration: 1.1, ease: 'power3.out', scrollTrigger: {trigger: img, start: 'top 90%', once: true}});
    });
  });
}

/* --------------------------------------------------------------------------
   Catalogue preview
   --------------------------------------------------------------------------
   A category card whose catalogue is uploaded opens that PDF in place instead
   of navigating away, so a visitor can look through it and carry on browsing.

   The card stays an ordinary link to the category page. That is deliberate:
   it is what a middle-click, a "open in new tab", a crawler and a visitor
   without JavaScript all get. Only a plain left-click is intercepted.

   iOS and most mobile browsers refuse to render a PDF inside an iframe — the
   frame just comes up blank — so on a touch screen the file is opened in a new
   tab instead of showing an empty box.
   -------------------------------------------------------------------------- */
function initPdfPreview() {
  const cards = document.querySelectorAll('[data-pdf-preview]');
  if (!cards.length) return;
  const inlinePdfWorks = !matchMedia('(hover: none)').matches && !/iPad|iPhone|iPod|Android/i.test(navigator.userAgent);
  let dialog = null, lastFocused = null;

  const close = () => {
    if (!dialog) return;
    dialog.classList.remove('is-open');
    document.body.classList.remove('has-pdf-preview');
    // Drop the iframe so the PDF stops using memory while it is not on screen.
    const frame = dialog.querySelector('iframe');
    if (frame) frame.remove();
    lastFocused?.focus();
  };

  const build = () => {
    const el = document.createElement('div');
    el.className = 'pdf-preview';
    el.innerHTML =
      '<div class="pdf-preview__backdrop" data-pdf-close></div>' +
      '<div class="pdf-preview__panel" role="dialog" aria-modal="true" aria-label="Catalogue preview">' +
        '<header class="pdf-preview__bar">' +
          '<p class="pdf-preview__title"></p>' +
          '<a class="pdf-preview__download" download>Download</a>' +
          '<button class="pdf-preview__close" type="button" data-pdf-close aria-label="Close preview">&times;</button>' +
        '</header>' +
        '<div class="pdf-preview__body"></div>' +
      '</div>';
    el.addEventListener('click', event => { if (event.target.closest('[data-pdf-close]')) close(); });
    document.body.append(el);
    return el;
  };

  const open = (url, title, source) => {
    dialog = dialog || build();
    lastFocused = source;
    dialog.querySelector('.pdf-preview__title').textContent = title || 'Catalogue';
    const download = dialog.querySelector('.pdf-preview__download');
    download.href = url;
    const body = dialog.querySelector('.pdf-preview__body');
    body.innerHTML = '';
    const frame = document.createElement('iframe');
    frame.src = url + '#view=FitH';
    frame.title = title || 'Catalogue preview';
    body.append(frame);
    dialog.classList.add('is-open');
    document.body.classList.add('has-pdf-preview');
    dialog.querySelector('.pdf-preview__close').focus();
  };

  cards.forEach(card => card.addEventListener('click', event => {
    // Leave the browser's own shortcuts alone.
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const url = card.dataset.pdfPreview;
    if (!url) return;
    if (!inlinePdfWorks) { event.preventDefault(); window.open(url, '_blank', 'noopener'); return; }
    event.preventDefault();
    open(url, card.dataset.pdfTitle, card);
  }));

  document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
}


function initCarousels() {
  // every carousel on the page, not just the first: the posts slider and the
  // project carousel are the same component and a page may hold either.
  document.querySelectorAll('[data-carousel]').forEach(initCarousel);
}

function initCarousel(stage) {
  const slides = [...stage.querySelectorAll('.media-slide')];
  if (slides.length < 2) return;
  const dots = [...stage.querySelectorAll('[data-carousel-dot]')];
  let index = 0;

  const show = next => {
    index = (next + slides.length) % slides.length;
    slides.forEach((slide, n) => {
      const active = n === index;
      slide.classList.toggle('is-active', active);
      // hidden slides stay out of the reading order, not just out of sight
      slide.toggleAttribute('aria-hidden', !active);
    });
    dots.forEach((dot, n) => {
      dot.classList.toggle('is-active', n === index);
      dot.setAttribute('aria-selected', String(n === index));
    });
  };

  stage.querySelector('[data-carousel-prev]')?.addEventListener('click', () => show(index - 1));
  stage.querySelector('[data-carousel-next]')?.addEventListener('click', () => show(index + 1));
  dots.forEach((dot, n) => dot.addEventListener('click', () => show(n)));

  // Arrow keys once the carousel has focus, the way a tablist behaves.
  stage.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(index - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); show(index + 1); }
  });
}

document.addEventListener('DOMContentLoaded', initCarousels);

/* Smooth scrolling ------------------------------------------------------------------
   Inertia on the wheel: the page eases toward where the wheel has asked it to go
   rather than jumping there, which is the feel of the reference site.

   Deliberately narrow. It takes over the wheel and nothing else — dragging the
   scrollbar, the keyboard, Page Up/Down, find-in-page and anchor jumps all stay
   native and simply resync the loop. It stays off entirely on touch, where the
   platform already does this better, and for anyone who has asked for reduced
   motion.

   `scroll-behavior: smooth` has to be off while this runs: it would animate every
   frame's scrollTo on top of the easing, which reads as the page sticking. The
   class is set from here so the stylesheet keeps its native-scrolling default for
   anyone this does not apply to. */
function initSmoothScroll() {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const coarse = matchMedia('(hover: none)');
  if (reduced.matches || coarse.matches) return;

  const root = document.documentElement;
  root.classList.add('has-smooth-scroll');

  const EASE = 0.12;          // how much of the remaining distance is covered per frame
  const SETTLE = 0.4;         // below this many pixels the loop stops and hands back
  let target = window.scrollY;
  let running = false;
  // The position this loop last asked for. `scroll` fires asynchronously, so a
  // flag set and cleared around scrollTo is always false by the time the event
  // arrives — the handler would then treat the loop's own scroll as the user's
  // and reset the target, stopping after one frame. Comparing positions tells
  // the two apart reliably.
  let lastSet = -1;

  const maxScroll = () => Math.max(0, root.scrollHeight - window.innerHeight);
  // A modal locks the body; leave scrolling alone while it is up. The vertical
  // axis is the one to read: the body already carries overflow-x: hidden, so the
  // shorthand computes to "hidden auto" normally and matching on it is brittle.
  const locked = () => getComputedStyle(document.body).overflowY === 'hidden';

  const frame = () => {
    const distance = target - window.scrollY;
    if (Math.abs(distance) < SETTLE) {
      running = false;
      return;
    }
    const next = window.scrollY + distance * EASE;
    lastSet = Math.round(next);
    window.scrollTo(0, next);
    window.ScrollTrigger && ScrollTrigger.update();
    requestAnimationFrame(frame);
  };

  const start = () => {
    if (running) return;
    running = true;
    requestAnimationFrame(frame);
  };

  addEventListener('wheel', event => {
    // let the browser handle zoom, and anything scrolling its own box (the rails,
    // the product gallery, the PDF preview)
    if (event.ctrlKey || event.metaKey || locked()) return;
    if (event.target.closest('.range-rail__track, .social-gallery__track, .pdf-preview, .stories-grid')) return;
    event.preventDefault();
    target = Math.min(maxScroll(), Math.max(0, target + event.deltaY));
    start();
  }, {passive: false});

  // Anything that moved the page by other means becomes the new truth.
  addEventListener('scroll', () => {
    if (Math.abs(window.scrollY - lastSet) > 2) target = window.scrollY;
  }, {passive: true});
  addEventListener('resize', () => { target = window.scrollY; }, {passive: true});
  reduced.addEventListener?.('change', e => { if (e.matches) { target = window.scrollY; root.classList.remove('has-smooth-scroll'); } });
}

document.addEventListener('DOMContentLoaded', initSmoothScroll);


document.addEventListener('DOMContentLoaded',initSite);

function initHeroSlider() {
  const stage = document.querySelector('.hero-slides');
  if (!stage) return;
  const slides = [...stage.querySelectorAll('.hero-slide')];
  const dotsWrap = document.querySelector('.hero-dots');
  const video = stage.querySelector('video');
  const STILL = 5200;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let index = 0, timer;

  const dots = slides.map((_, n) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('role', 'tab');
    b.setAttribute('aria-label', n === slides.length - 1 && video ? 'Video slide' : `Slide ${n + 1}`);
    b.setAttribute('aria-selected', String(n === 0));
    b.addEventListener('click', () => go(n));
    dotsWrap.append(b);
    return b;
  });

  function go(n) {
    clearTimeout(timer);
    slides[index].classList.remove('is-active');
    dots[index].setAttribute('aria-selected', 'false');
    index = (n + slides.length) % slides.length;
    slides[index].classList.add('is-active');
    dots[index].setAttribute('aria-selected', 'true');

    const isVideo = slides[index].classList.contains('hero-slide--video');
    if (video) {
      if (isVideo) { try { video.currentTime = 0; } catch (e) {} video.play().catch(() => {}); }
      else video.pause();
    }
    if (reduced) return;
    // A still advances on a timer; the video advances when it ends, with a
    // fallback timer so a missing/blocked file can never stall the slider.
    timer = setTimeout(() => go(index + 1),
      isVideo ? Math.min(((video && video.duration) || 12) * 1000 + 600, 30000) : STILL);
  }

  video?.addEventListener('ended', () => go(index + 1));
  if (!reduced) timer = setTimeout(() => go(1), STILL);
}
document.addEventListener('DOMContentLoaded', initHeroSlider);
/* Posts filters: submit as soon as a box is ticked. The form still works
   without this — the noscript button submits it — so the list is never
   dependent on JavaScript. */
function initStoryFilters() {
  const form = document.querySelector('[data-stories-filters]');
  if (!form) return;
  form.addEventListener('change', event => {
    if (event.target.matches('input[name="kind"]')) form.requestSubmit();
  });
}

document.addEventListener('DOMContentLoaded', initPdfPreview);
document.addEventListener('DOMContentLoaded', initStoryFilters);

/**
 * Pins the statement block and steps through its three sentences as the reader
 * scrolls, crossfading the photograph behind each one.
 *
 * The swap is a class toggle rather than a tween: the display word, the inline
 * verb it replaces and — on a phone — the whole line are handed to CSS
 * transitions, which keeps every part of the change on one clock however fast
 * the scrub runs. Returns a teardown for the breakpoint it was started in.
 */
function initStatementSequence(statement) {
  if (!statement || !window.gsap || !window.ScrollTrigger) return () => {};
  statement.classList.add('is-pinned');
  const lines = statement.querySelectorAll('.statement-line');
  const images = statement.querySelectorAll('.statement-images img');
  const steps = statement.querySelectorAll('.statement-steps i');
  let current = -1;
  const setActive = (index) => {
    if (index === current) return;
    current = index;
    lines.forEach((line, position) => line.classList.toggle('is-active', position === index));
    steps.forEach((step, position) => step.classList.toggle('is-on', position <= index));
  };
  // Timeline positions each line takes over at, recorded while the timeline is
  // built so the thresholds can never drift out of step with the image fades.
  const switchAt = [0];
  // A scrubbed .call() re-fires when the playhead crosses it in reverse, which
  // would strand the wrong line on an upward scroll — reading the playhead on
  // update is direction-agnostic.
  let sequence;
  const sync = () => {
    if (!sequence) return;
    let index = 0;
    for (let position = switchAt.length - 1; position >= 0; position -= 1) {
      if (sequence.time() >= switchAt[position]) { index = position; break; }
    }
    setActive(index);
  };
  sequence = gsap.timeline({
    scrollTrigger: {trigger: statement, start: 'top top', end: 'bottom bottom', scrub: .65},
    onUpdate: sync
  });
  sequence.to({}, {duration: .5});
  [1, 2].forEach((index) => {
    switchAt[index] = sequence.duration();
    // The image crossfade ran for .8 against a .65 hold, so each photograph
    // spent roughly half its scroll distance visibly blended with the one
    // beneath it — it read as a double exposure rather than a fade. A short
    // eased fade plus a longer hold keeps the same transition but spends most
    // of the scroll on a single, clean image.
    sequence.to(images[index], {opacity: 1, duration: .22, ease: 'power2.inOut'})
      .to({}, {duration: 1.2});
  });
  sync();
  return () => {
    sequence.scrollTrigger?.kill();
    sequence.kill();
    statement.classList.remove('is-pinned');
    // Unpinned, the block is a plain stack again, so the first line carries the
    // display word and the images go back to showing only the first.
    gsap.set(images, {clearProps: 'opacity'});
    setActive(0);
  };
}

function initHomeMotion(motion) {
  const statement = document.querySelector('.statement-story');
  if (!statement) return;
  // The statement runs the same scrubbed sequence at every width. What differs
  // is the layout it drives: on a wide screen the three lines sit together and
  // the active one lifts its verb into the left column; on a phone there is no
  // room for that column, so the lines take the screen one at a time. Both are
  // the same three steps, so they share one timeline.
  motion.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', () => {
    const stopStatement = initStatementSequence(statement);
    gsap.fromTo('.featured-stage img', {clipPath:'inset(0 40% 0 40%)', opacity:.35, scale:1.08}, {
      clipPath:'inset(0 0% 0 0%)',opacity:1,scale:1,ease:'none',
      scrollTrigger:{trigger:'.featured-stage',start:'top 85%',end:'top 15%',scrub:.8}
    });
    gsap.from('.featured-title', {y:35,opacity:0,duration:1,ease:'power2.out',scrollTrigger:{trigger:'.featured-stage',start:'top 80%',once:true}});
    return stopStatement;
  });
  motion.add('(max-width: 900px) and (prefers-reduced-motion: no-preference)', () => initStatementSequence(statement));
  motion.add('(min-width: 601px) and (prefers-reduced-motion: no-preference)', () => {
    gsap.utils.toArray('.testimonial-column').forEach((column,index) => {
      gsap.fromTo(column,{y:index===1?30:0},{y:index===1?-160:-90,ease:'none',scrollTrigger:{trigger:'.testimonial-window',start:'top bottom',end:'bottom top',scrub:1}});
    });
  });
  // Below 900px the stage is stacked — heading, photograph, link — so all three
  // ease in together rather than the photograph fading on its own with the
  // words already sitting there. `.featured-title` is display:contents at this
  // width and has no box to animate, so its children are targeted directly.
  // power2.inOut eases at both ends, which reads as deliberate on a phone where
  // the section arrives already most of the way up the screen.
  motion.add('(max-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
    gsap.utils.toArray('.featured-stage').forEach(stage => {
      const parts = [
        stage.querySelector('.featured-title h3'),
        stage.querySelector(':scope > picture') || stage.querySelector('img'),
        stage.querySelector('.featured-title .text-cta'),
      ].filter(Boolean);
      if (!parts.length) return;
      gsap.from(parts, {
        opacity: 0,
        y: 30,
        duration: 1.1,
        ease: 'power2.inOut',
        stagger: 0.14,
        scrollTrigger: {trigger: stage, start: 'top 88%', once: true},
      });
    });
  });
  document.querySelectorAll('.cta-outline path').forEach((path,index) => {
    const length = path.getTotalLength();
    gsap.fromTo(path,{strokeDasharray:length,strokeDashoffset:length},{strokeDashoffset:0,duration:1.8,delay:index*.2,ease:'power2.inOut',scrollTrigger:{trigger:'.line-cta',start:'top 85%',once:true}});
  });
  document.querySelectorAll('.home-lower .why-list>div').forEach((row) => {
    gsap.from(row,{opacity:0,y:15,duration:.7,scrollTrigger:{trigger:row,start:'top 90%',once:true}});
  });
}

function initAboutMotion(motion) {
  const page = document.querySelector('.about-page');
  if (!page) return;
  motion.add('(min-width: 901px) and (prefers-reduced-motion: no-preference)', () => {
    // These used to play once on arrival and finish on their own clock. Tied
    // to scroll progress instead, each value answers the scroll the whole way
    // in — the storytelling feel — while its resting appearance is unchanged.
    gsap.utils.toArray('.about-value').forEach((item,index) => {
      const number=item.querySelector('.about-value__num');
      if(number)gsap.from(number,{x:index%2?70:-70,opacity:0,ease:'none',scrollTrigger:{trigger:item,start:'top 92%',end:'top 52%',scrub:.6}});
      const heading=item.querySelector('h3');
      if(heading)gsap.from(heading,{y:30,opacity:0,ease:'none',scrollTrigger:{trigger:item,start:'top 88%',end:'top 50%',scrub:.6}});
      const copy=item.querySelector('p');
      if(copy)gsap.from(copy,{y:45,opacity:0,ease:'none',scrollTrigger:{trigger:item,start:'top 84%',end:'top 46%',scrub:.65}});
    });
    if(document.querySelector('.about-values__line'))gsap.from('.about-values__line',{scaleY:0,transformOrigin:'top',ease:'none',scrollTrigger:{trigger:'.about-values__list',start:'top 70%',end:'bottom 45%',scrub:true}});
    gsap.utils.toArray('.about-person').forEach((person,index) => {
      const image=person.querySelector('img');
      gsap.fromTo(image,{clipPath:index===1?'inset(0 0 0 100%)':'inset(0 100% 0 0)',scale:1.08},{clipPath:'inset(0 0% 0 0%)',scale:1,duration:1.15,ease:'power3.out',scrollTrigger:{trigger:person,start:'top 78%',once:true}});
      gsap.from(person.querySelectorAll('.about-person__copy,.about-person__role'),{y:35,opacity:0,stagger:.12,duration:.8,scrollTrigger:{trigger:person,start:'top 68%',once:true}});
    });
    gsap.to('.about-tree img',{yPercent:-8,ease:'none',scrollTrigger:{trigger:'.about-tree',start:'top bottom',end:'bottom top',scrub:.8}});
    gsap.from('.about-quote p',{x:60,opacity:0,duration:1,ease:'power3.out',scrollTrigger:{trigger:'.about-quote',start:'top 72%',once:true}});
    gsap.from('.about-quote__mark--open',{x:-35,rotation:-8,opacity:0,duration:.9,ease:'back.out(1.5)',scrollTrigger:{trigger:'.about-quote',start:'top 72%',once:true}});
    gsap.from('.about-quote__mark--close',{x:35,rotation:8,opacity:0,duration:.9,delay:.15,ease:'back.out(1.5)',scrollTrigger:{trigger:'.about-quote',start:'top 72%',once:true}});
  });
  gsap.utils.toArray('.about-rule').forEach(rule => gsap.from(rule,{opacity:0,y:18,duration:.7,scrollTrigger:{trigger:rule,start:'top 90%',once:true}}));
  document.querySelectorAll('.about-line-cta .cta-outline path').forEach((path,index) => {
    const length=path.getTotalLength();
    gsap.fromTo(path,{strokeDasharray:length,strokeDashoffset:length},{strokeDashoffset:0,duration:1.8,delay:index*.18,ease:'power2.inOut',scrollTrigger:{trigger:'.about-line-cta',start:'top 82%',once:true}});
  });
}

/* ==========================================================================
   Category rail arrows
   --------------------------------------------------------------------------
   The rail is an ordinary scroll container, so the arrows only have to move
   scrollLeft by one card and keep their own disabled state in step with it.
   ========================================================================== */
(function initRangeRail(){
  document.querySelectorAll('.range-rail').forEach(rail => {
    const track=rail.querySelector('.range-rail__track');
    // the first tile, whatever it is: the project gallery uses this rail too
    const card=track?.firstElementChild;
    const prev=rail.querySelector('[data-rail-prev]');
    const next=rail.querySelector('[data-rail-next]');
    // Optional: a rail only gets page dots if the markup asks for them.
    const dots=rail.querySelector('[data-rail-dots]');
    if(!track||!card||!prev||!next)return;
    // Measured rather than assumed: the card width and the gap both come from
    // clamp(), so they change with the viewport.
    const step=()=>{
      const gap=parseFloat(getComputedStyle(track).columnGap)||0;
      return card.getBoundingClientRect().width+gap;
    };
    const limit=()=>Math.max(0,track.scrollWidth-track.clientWidth);
    // A page is one visible width of the track, so the dot count follows the
    // viewport rather than the number of cards — four cards are one page on a
    // wide screen and four on a phone.
    // Never more dots than there are items: the gaps make scrollWidth round up
    // to an extra page that is only a sliver of a card wide.
    const pages=()=>Math.min(
      Math.max(1,track.childElementCount),
      Math.max(1,Math.ceil(track.scrollWidth/Math.max(1,track.clientWidth)))
    );
    const buildDots=room=>{
      if(!dots)return;
      const count=room>1?pages():0;
      if(dots.childElementCount===count)return;
      dots.replaceChildren();
      for(let i=0;i<count;i++){
        const dot=document.createElement('button');
        dot.type='button';
        dot.className='range-rail__dot';
        dot.setAttribute('role','tab');
        dot.setAttribute('aria-label','Cards '+(i+1)+' of '+count);
        // Positioned across the scrollable range, not by multiplying the page
        // width: when the last page is a sliver, i*clientWidth overshoots the
        // maximum and that dot can never be reached or highlighted.
        dot.addEventListener('click',()=>{
          const room=limit();
          const span=Math.max(1,dots.childElementCount-1);
          track.scrollTo({left:room*(i/span),behavior:'smooth'});
        });
        dots.append(dot);
      }
    };
    const syncDots=()=>{
      if(!dots||!dots.childElementCount)return;
      const room=limit();
      const span=Math.max(1,dots.childElementCount-1);
      // Which dot the current scroll position is nearest, measured as progress
      // through the range so the last one is always reachable.
      const active=room>0?Math.round((track.scrollLeft/room)*span):0;
      [...dots.children].forEach((dot,i)=>{
        dot.classList.toggle('is-active',i===active);
        dot.setAttribute('aria-selected',String(i===active));
      });
    };
    let frame=0;
    const sync=()=>{
      frame=0;
      const room=limit();
      // No room to move means no arrows: with four categories on a wide screen
      // they all fit, and a pair of permanently greyed buttons reads as broken.
      rail.classList.toggle('has-overflow',room>1);
      prev.disabled=track.scrollLeft<=1;
      next.disabled=track.scrollLeft>=room-1;
      buildDots(room);
      syncDots();
    };
    prev.addEventListener('click',()=>track.scrollBy({left:-step(),behavior:'smooth'}));
    next.addEventListener('click',()=>track.scrollBy({left:step(),behavior:'smooth'}));
    track.addEventListener('scroll',()=>{if(!frame)frame=requestAnimationFrame(sync);},{passive:true});
    addEventListener('resize',sync,{passive:true});
    sync();
  });
})();

/* ==========================================================================
   Floating WhatsApp link — the COFUR "O" mark, as it was
   --------------------------------------------------------------------------
   The green pill is gone: the button wears the original "O" again, blinking
   eyes and all, and the only thing behind it is the WhatsApp link. No panel,
   no state, no scripted questions — one tap opens the chat.
   ========================================================================== */
(function initWhatsAppButton(){
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',initWhatsAppButton);return}
  if(document.querySelector('.cofur-whatsapp'))return;
  const NUMBER=document.body.dataset.whatsapp;
  const MESSAGE=document.body.dataset.whatsappMessage||'Hello Cofur, I would like to know more about your furniture.';
  const ICON=document.body.dataset.whatsappIcon||`${document.body.dataset.staticUrl||'/static/'}images/cofur-o.png`;
  if(!NUMBER)return;
  const link=document.createElement('a');
  link.className='cofur-whatsapp';
  link.href=`https://wa.me/${NUMBER}?text=${encodeURIComponent(MESSAGE)}`;
  link.target='_blank';
  link.rel='noopener';
  link.setAttribute('aria-label','Chat with Cofur on WhatsApp');
  link.innerHTML=`
    <img src="${ICON}" alt="" width="192" height="192">
    <span class="cofur-whatsapp__eyes" aria-hidden="true"><i></i><i></i></span>`;
  document.body.appendChild(link);
})();

/* ==========================================================================
   Mobile menu — the Collections list belongs inside the panel
   --------------------------------------------------------------------------
   The mega-menu is a child of the header, and the header carries a GSAP
   transform, which makes it the containing block for anything positioned
   fixed inside it. So the phone rule `inset: 82px 0 0` resolved against an
   82px-tall header instead of the viewport and the panel opened at zero
   height: the submenu was there, doing everything it was told, with nowhere
   to be. Rather than patch the arithmetic, the list moves into the menu
   panel on a phone, where it reads as an accordion under Collections and is
   positioned by the normal flow. It moves back out above 900px, where the
   full-width mega-menu is the right shape.
   ========================================================================== */
(function initMobileMenu(){
  const start=()=>{
    const panel=document.querySelector('.nav-links');
    const mega=document.querySelector('.mega-menu');
    const trigger=document.querySelector('[data-mega-trigger]');
    const burger=document.querySelector('.menu-btn');
    if(!panel||!mega||!trigger)return;

    const desktopHome=mega.parentElement;
    const phone=matchMedia('(max-width:900px)');

    const collapse=()=>{
      mega.classList.remove('open');
      mega.setAttribute('aria-hidden','true');
      trigger.setAttribute('aria-expanded','false');
    };
    const shut=()=>{
      collapse();
      panel.classList.remove('open');
      burger?.classList.remove('open');
      burger?.setAttribute('aria-expanded','false');
    };

    // Put the list where the current breakpoint can display it.
    const place=()=>{
      if(phone.matches){ if(mega.parentElement!==panel) trigger.after(mega); }
      else if(mega.parentElement!==desktopHome) desktopHome.append(mega);
    };
    place();
    phone.addEventListener('change',()=>{ shut(); place(); });

    // Following a link should leave the menu behind.
    panel.addEventListener('click',e=>{
      if(!phone.matches)return;
      const link=e.target.closest('a');
      if(link&&panel.contains(link))shut();
    });
  };
  document.readyState==='loading'
    ? document.addEventListener('DOMContentLoaded',start)
    : start();
})();
