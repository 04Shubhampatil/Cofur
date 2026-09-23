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
    initHomeMotion(motion);
    initAboutMotion(motion);
    document.fonts.ready.then(() => ScrollTrigger.refresh());
    window.addEventListener('load', () => ScrollTrigger.refresh(), {once: true});
  }else document.querySelectorAll('.reveal').forEach(x=>x.style.visibility='visible');
}
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
    gsap.fromTo('.featured-stage>img', {clipPath:'inset(0 40% 0 40%)', opacity:.35, scale:1.08}, {
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
  motion.add('(max-width: 900px) and (prefers-reduced-motion: no-preference)', () => {
    gsap.from('.featured-stage>img',{opacity:0,duration:1.2,scrollTrigger:{trigger:'.featured-stage',start:'top 85%',once:true}});
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
    gsap.utils.toArray('.about-value').forEach((item,index) => {
      const number=item.querySelector('.about-value__num');
      if(number)gsap.from(number,{x:index%2?70:-70,opacity:0,duration:1.1,ease:'power3.out',scrollTrigger:{trigger:item,start:'top 82%',once:true}});
      const copy=item.querySelector('p');
      if(copy)gsap.from(copy,{y:45,opacity:0,duration:.9,ease:'power2.out',scrollTrigger:{trigger:item,start:'top 72%',once:true}});
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
    const card=track?.querySelector('.range-card');
    const prev=rail.querySelector('[data-rail-prev]');
    const next=rail.querySelector('[data-rail-next]');
    if(!track||!card||!prev||!next)return;
    // Measured rather than assumed: the card width and the gap both come from
    // clamp(), so they change with the viewport.
    const step=()=>{
      const gap=parseFloat(getComputedStyle(track).columnGap)||0;
      return card.getBoundingClientRect().width+gap;
    };
    const limit=()=>Math.max(0,track.scrollWidth-track.clientWidth);
    let frame=0;
    const sync=()=>{
      frame=0;
      const room=limit();
      // No room to move means no arrows: with four categories on a wide screen
      // they all fit, and a pair of permanently greyed buttons reads as broken.
      rail.classList.toggle('has-overflow',room>1);
      prev.disabled=track.scrollLeft<=1;
      next.disabled=track.scrollLeft>=room-1;
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
