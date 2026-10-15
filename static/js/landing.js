/* Marketing landing pages (/acoustic-wall-panels-for-offices/,
   /acoustic-ceilings-for-offices/).

   These pages do not load main.js — they have no header, no footer and no
   carousels, so all they need is the site's entrance motion and a small
   convenience on the enquiry form. Everything is optional: with the script
   blocked the page still renders and the form still submits. */
(function () {
  "use strict";

  var root = document.documentElement;
  var still = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* Blocks are only hidden once we know we can bring them back, so a failed
     script can never leave the page blank. */
  function reveal() {
    var blocks = document.querySelectorAll("[data-lp-reveal]");
    if (!blocks.length) return;
    if (!("IntersectionObserver" in window)) return;

    root.classList.add("lp-js");

    var watcher = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        watcher.unobserve(entry.target);
      });
      // threshold 0: the moment any part of a block crosses the line it is
      // revealed, so nothing can be left stranded at opacity 0.
    }, { rootMargin: "0px 0px -5% 0px", threshold: 0 });

    blocks.forEach(function (block, i) {
      // A short stagger inside a row, so a grid arrives as a group.
      if (!still.matches) block.style.transitionDelay = (i % 4) * 70 + "ms";
      watcher.observe(block);
    });
  }

  /* "Enquire about this product" buttons preselect their own product in the
     form, so the lead says which design the visitor was looking at. */
  function productShortcuts() {
    var select = document.getElementById("id_product");
    if (!select) return;

    document.querySelectorAll("[data-lp-product]").forEach(function (trigger) {
      trigger.addEventListener("click", function () {
        var value = trigger.getAttribute("data-lp-product");
        if (!value) return;
        var match = select.querySelector('option[value="' + value + '"]');
        if (match) select.value = value;
      });
    });
  }

  function start() {
    reveal();
    productShortcuts();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
