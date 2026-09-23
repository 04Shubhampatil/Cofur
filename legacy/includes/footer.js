(() => {
  const mount = document.querySelector('[data-include="includes/footer.html"]');
  if (!mount) return;

  const arrow = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M17 18H9a5 5 0 0 1 0-10h11m-3-3 3 3-3 3"/></svg>';

  // TODO (client): supply the real profile URLs and the mobile number, then
  // replace the "#" hrefs below and uncomment the phone line.
  const social = [
    ['LinkedIn', '#', '<path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9h4v12H3zM10 9h3.8v1.7h.05c.53-.95 1.83-1.95 3.77-1.95 4.03 0 4.78 2.5 4.78 5.76V21h-4v-5.6c0-1.34-.03-3.06-1.9-3.06-1.9 0-2.2 1.45-2.2 2.96V21h-4z"/>'],
    ['Instagram', '#', '<path d="M12 2.2c3.2 0 3.58.01 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.8-.25-2.23-.41-.56-.22-.96-.48-1.38-.9-.42-.42-.68-.82-.9-1.38-.16-.42-.36-1.06-.41-2.23C2.21 15.58 2.2 15.2 2.2 12s.01-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.21 8.8 2.2 12 2.2zm0 3.05A6.75 6.75 0 1 0 18.75 12 6.75 6.75 0 0 0 12 5.25zm0 11.13A4.38 4.38 0 1 1 16.38 12 4.38 4.38 0 0 1 12 16.38zm6.99-11.4a1.58 1.58 0 1 1-1.58-1.57 1.58 1.58 0 0 1 1.58 1.57z"/>'],
    ['X', '#', '<path d="M17.5 3h3.1l-6.8 7.77L21.8 21h-6.2l-4.86-6.35L5.18 21H2.07l7.27-8.31L2.2 3h6.36l4.39 5.8zm-1.09 16.1h1.72L7.66 4.81H5.82z"/>']
  ];

  const menu = [
    ['Collections', 'index.html#our-products'],
    ['About', 'about.html'],
    ['Communications', 'about.html#sustainability'],
    ['Catalogues', 'soft-seating.html'],
    ['Contact', 'contact.html']
  ];

  const wrapper = document.createElement('div');
  wrapper.className = 'footer-include';
  wrapper.innerHTML = `
    <footer class="cofur-footer">
      <div class="cofur-footer__inner">
        <div class="cofur-footer__brand">
          <a class="cofur-footer__logo" href="index.html" aria-label="Cofur home"><img src="assets/images/cofur-logo-light.webp" alt="Cofur — Change the way you work"></a>
      
          <address class="cofur-footer__address"><a href="https://maps.google.com/?q=Odessa+Boutique+Offices,+Road+Number+9,+Wagle+Industrial+Estate,+Thane+West,+Maharashtra+400604" target="_blank" rel="noopener">3rd Floor, Odessa Boutique Offices, Road Number 9, Wagle Industrial Estate, Thane West, Maharashtra 400604, India</a></address>
          <ul class="cofur-footer__contact">
            <li><a href="mailto:info@cofur.in">info@cofur.in</a></li>
            <!-- <li><a href="tel:+910000000000">+91 00000 00000</a></li> -->
          </ul>
          <ul class="cofur-footer__social">${social.map(([label, href, path]) =>
            `<li><a href="${href}" aria-label="${label}"${href === '#' ? '' : ' target="_blank" rel="noopener"'}><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">${path}</svg></a></li>`).join('')}
          </ul>
        </div>
        <div class="cofur-footer__cta">
          <p class="cofur-footer__eyebrow">Let's build better workspaces</p>
          <h2 class="cofur-footer__title" data-static-title>We’ll help you find the<br>right solution.</h2>
          <div class="cofur-footer__actions">
            <a class="cofur-footer__btn cofur-footer__btn--ghost" href="contact.html"><span>Contact us</span>${arrow}</a>
            <a class="cofur-footer__btn" href="soft-seating.html"><span>Download catalog</span>${arrow}</a>
          </div>
        </div>
      </div>
      <div class="cofur-footer__bar">
        <p class="cofur-footer__copy">Copyright © ${new Date().getFullYear()} COFUR Pvt. Ltd. All rights reserved.</p>
        <nav class="cofur-footer__menu" aria-label="Footer">${menu.map(([label, href]) => `<a href="${href}">${label}</a>`).join('')}</nav>
      </div>
    </footer>`;
  mount.replaceWith(wrapper);
})();
