/* COFUR CMS dashboard behaviours — vanilla JS, no dependencies. */
(function () {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const csrf = () => (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || ($('input[name=csrfmiddlewaretoken]') || {}).value || '';

  /* ---------------------------------------------------------------- toasts */
  const toastHost = $('#toasts');
  function toast(message, type = 'info', timeout = 4200) {
    if (!toastHost) return;
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = message;
    toastHost.append(el);
    setTimeout(() => { el.classList.add('is-leaving'); setTimeout(() => el.remove(), 260); }, timeout);
  }
  $$('[data-toast]').forEach((el, i) => setTimeout(() => { el.classList.add('is-leaving'); setTimeout(() => el.remove(), 260); }, 4200 + i * 400));
  window.cmsToast = toast;

  /* ---------------------------------------------------------------- sidebar */
  $$('[data-sidebar-open]').forEach(btn => btn.addEventListener('click', () => { document.body.classList.add('sidebar-open'); $('.dash__overlay').hidden = false; }));
  $$('[data-sidebar-close]').forEach(btn => btn.addEventListener('click', () => { document.body.classList.remove('sidebar-open'); $('.dash__overlay').hidden = true; }));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { document.body.classList.remove('sidebar-open'); const o = $('.dash__overlay'); if (o) o.hidden = true; } });

  /* ---------------------------------------------------------------- confirm dialog */
  const confirmDialog = $('#confirm-dialog');
  function confirmAction(text, title) {
    return new Promise(resolve => {
      if (!confirmDialog || typeof confirmDialog.showModal !== 'function') { resolve(window.confirm(text)); return; }
      $('[data-confirm-text]', confirmDialog).textContent = text || 'This action cannot be undone.';
      $('[data-confirm-title]', confirmDialog).textContent = title || 'Are you sure?';
      const ok = $('[data-confirm-ok]', confirmDialog), cancel = $('[data-confirm-cancel]', confirmDialog);
      const done = value => { confirmDialog.close(); ok.onclick = cancel.onclick = null; resolve(value); };
      ok.onclick = () => done(true);
      cancel.onclick = () => done(false);
      confirmDialog.addEventListener('close', () => resolve(false), { once: true });
      confirmDialog.showModal();
    });
  }
  window.cmsConfirm = confirmAction;
  document.addEventListener('submit', e => {
    const form = e.target;
    if (!form.matches('form[data-confirm]') || form.dataset.confirmed) return;
    e.preventDefault();
    confirmAction(form.dataset.confirm).then(ok => { if (ok) { form.dataset.confirmed = '1'; form.requestSubmit(); } });
  });

  /* ---------------------------------------------------------------- tabs */
  $$('[data-tabs]').forEach(tabs => {
    const buttons = $$('.tabs__tab', tabs), panels = $$('.tabs__panel', tabs);
    const key = tabs.dataset.tabsRemember ? `cms-tab-${tabs.dataset.tabsRemember}` : null;
    const activate = id => {
      buttons.forEach(b => b.classList.toggle('is-active', b.dataset.tab === id));
      panels.forEach(p => p.classList.toggle('is-active', p.id === id));
      if (key) try { sessionStorage.setItem(key, id); } catch (_) {}
    };
    buttons.forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));
    panels.forEach(p => { if ($('.has-error', p)) { const b = buttons.find(x => x.dataset.tab === p.id); b && b.classList.add('has-error'); } });
    const errorPanel = panels.find(p => $('.has-error', p));
    let initial = errorPanel ? errorPanel.id : null;
    if (!initial && key) try { initial = sessionStorage.getItem(key); } catch (_) {}
    if (initial && panels.some(p => p.id === initial)) activate(initial);
  });

  /* ---------------------------------------------------------------- dirty check */
  $$('form[data-dirty-check]').forEach(form => {
    let dirty = false, submitting = false;
    form.addEventListener('input', () => { dirty = true; });
    form.addEventListener('submit', () => { submitting = true; const btn = $('[data-submit]', form); if (btn) btn.disabled = true; });
    window.addEventListener('beforeunload', e => { if (dirty && !submitting) { e.preventDefault(); e.returnValue = ''; } });
  });

  /* ---------------------------------------------------------------- image picker widget */
  function bindImagePicker(picker) {
    const input = $('[data-file-input]', picker), preview = $('[data-preview]', picker), hint = $('[data-picker-hint]', picker);
    const showPreview = (url, label) => {
      preview.innerHTML = url ? `<img src="${url}" alt="">` : '<span>No image</span>';
      preview.classList.toggle('is-empty', !url);
      if (hint && label) hint.textContent = label;
    };
    input && input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;
      if (file.size > 10 * 1024 * 1024) { toast(`${file.name} is larger than 10 MB.`, 'error'); input.value = ''; return; }
      showPreview(URL.createObjectURL(file), file.name);
    });
    ['dragenter', 'dragover'].forEach(ev => picker.addEventListener(ev, e => { e.preventDefault(); picker.classList.add('is-dragover'); }));
    ['dragleave', 'drop'].forEach(ev => picker.addEventListener(ev, e => { e.preventDefault(); picker.classList.remove('is-dragover'); }));
    picker.addEventListener('drop', e => {
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file || !input) return;
      const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files;
      input.dispatchEvent(new Event('change'));
    });
  }
  $$('[data-image-picker]').forEach(bindImagePicker);

  /* ---------------------------------------------------------------- formsets */
  $$('[data-formset]').forEach(formset => {
    const prefix = formset.dataset.prefix, rows = $('[data-formset-rows]', formset), total = $(`#id_${prefix}-TOTAL_FORMS`), tpl = $('[data-formset-empty]', formset), note = $('[data-formset-empty-note]', formset);
    const renumberOrder = () => $$('[data-formset-row]', rows).forEach((row, i) => { const o = $('input[name$="-order"]', row); if (o) o.value = i; });
    $('[data-formset-add]', formset).addEventListener('click', () => {
      const index = parseInt(total.value, 10);
      const html = tpl.innerHTML.replace(/__prefix__/g, index);
      const wrap = document.createElement('div'); wrap.innerHTML = html.trim();
      const row = wrap.firstElementChild;
      rows.append(row);
      total.value = index + 1;
      note && note.remove();
      $$('[data-image-picker]', row).forEach(bindImagePicker);
      bindRow(row);
      renumberOrder();
      const first = $('input:not([type=hidden]), select, textarea', row); first && first.focus();
    });
    function bindRow(row) {
      const del = $('.formset__delete input', row);
      del && del.addEventListener('change', () => row.classList.toggle('is-deleted', del.checked));
      const handle = $('.drag', row);
      if (!handle) return;
      handle.addEventListener('dragstart', e => { row.classList.add('is-dragging'); e.dataTransfer.effectAllowed = 'move'; formset._dragging = row; });
      handle.addEventListener('dragend', () => { row.classList.remove('is-dragging'); $$('.drop-before,.drop-after', rows).forEach(r => r.classList.remove('drop-before', 'drop-after')); formset._dragging = null; });
      row.addEventListener('dragover', e => { if (!formset._dragging || formset._dragging === row) return; e.preventDefault(); const before = e.offsetY < row.offsetHeight / 2; row.classList.toggle('drop-before', before); row.classList.toggle('drop-after', !before); });
      row.addEventListener('dragleave', () => row.classList.remove('drop-before', 'drop-after'));
      row.addEventListener('drop', e => { e.preventDefault(); const d = formset._dragging; if (!d || d === row) return; const before = row.classList.contains('drop-before'); row.classList.remove('drop-before', 'drop-after'); before ? row.before(d) : row.after(d); renumberOrder(); });
    }
    $$('[data-formset-row]', rows).forEach(bindRow);
  });

  /* ---------------------------------------------------------------- sortable tables */
  $$('table[data-sortable]').forEach(table => {
    const body = $('tbody', table); let dragging = null;
    const save = () => {
      const order = $$('tr[data-id]', body).map(tr => parseInt(tr.dataset.id, 10));
      fetch(table.dataset.reorderUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify({ order }), credentials: 'same-origin' })
        .then(r => r.ok ? toast('Order saved.', 'success', 1800) : toast('Could not save the order.', 'error'))
        .catch(() => toast('Could not save the order.', 'error'));
    };
    $$('tr[data-id]', body).forEach(tr => {
      const handle = $('.drag', tr); if (!handle) return;
      handle.addEventListener('dragstart', e => { dragging = tr; tr.classList.add('is-dragging'); e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', tr.dataset.id); } catch (_) {} });
      handle.addEventListener('dragend', () => { dragging && dragging.classList.remove('is-dragging'); dragging = null; $$('.drop-before,.drop-after', body).forEach(r => r.classList.remove('drop-before', 'drop-after')); });
      tr.addEventListener('dragover', e => { if (!dragging || dragging === tr) return; if (tr.dataset.parent !== undefined && tr.dataset.parent !== dragging.dataset.parent) return; e.preventDefault(); const rect = tr.getBoundingClientRect(); const before = e.clientY < rect.top + rect.height / 2; tr.classList.toggle('drop-before', before); tr.classList.toggle('drop-after', !before); });
      tr.addEventListener('dragleave', () => tr.classList.remove('drop-before', 'drop-after'));
      tr.addEventListener('drop', e => { e.preventDefault(); if (!dragging || dragging === tr) return; const before = tr.classList.contains('drop-before'); tr.classList.remove('drop-before', 'drop-after'); before ? tr.before(dragging) : tr.after(dragging); save(); });
    });
  });

  /* ---------------------------------------------------------------- dropzone uploads */
  $$('[data-dropzone]').forEach(zone => {
    const input = $('[data-dropzone-input]', zone), queue = $('[data-dropzone-queue]', zone), kindSelect = $('[data-dropzone-kind]', zone);
    const url = zone.dataset.uploadUrl;
    let pending = 0;
    ['dragenter', 'dragover'].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('is-dragover'); }));
    ['dragleave', 'drop'].forEach(ev => zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove('is-dragover'); }));
    zone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
    input && input.addEventListener('change', () => { handleFiles(input.files); input.value = ''; });
    zone.addEventListener('submit', e => e.preventDefault());
    function handleFiles(files) {
      const list = [...files].filter(f => f.type.startsWith('image/'));
      if (!list.length) { toast('Only image files can be uploaded.', 'error'); return; }
      list.forEach(file => {
        const item = document.createElement('div');
        item.className = 'upload-item';
        item.innerHTML = `<img src="${URL.createObjectURL(file)}" alt=""><div class="upload-item__bar"><i></i></div><div class="upload-item__name">${file.name}</div><button type="button" class="upload-item__remove" aria-label="Remove">×</button>`;
        queue.append(item);
        $('.upload-item__remove', item).addEventListener('click', () => item.remove());
        if (file.size > 10 * 1024 * 1024) { item.classList.add('is-error'); $('.upload-item__name', item).textContent = `${file.name}: larger than 10 MB`; return; }
        // Preview only until the user confirms with "Upload"? Keep it simple: upload immediately, allow removal of finished items.
        upload(file, item);
      });
    }
    function upload(file, item) {
      const fd = new FormData();
      const fieldName = zone.dataset.reloadOnDone ? 'files' : 'images';
      fd.append(fieldName, file);
      if (kindSelect) fd.append('kind', kindSelect.value); else if (zone.dataset.kind) fd.append('kind', zone.dataset.kind);
      const xhr = new XMLHttpRequest();
      pending += 1;
      xhr.open('POST', url);
      xhr.setRequestHeader('X-CSRFToken', csrf());
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.upload.onprogress = e => { if (e.lengthComputable) $('.upload-item__bar i', item).style.width = `${Math.round(e.loaded / e.total * 100)}%`; };
      xhr.onload = () => {
        pending -= 1;
        let data = {};
        try { data = JSON.parse(xhr.responseText); } catch (_) {}
        if (xhr.status < 300 && data.ok) {
          $('.upload-item__bar i', item).style.width = '100%';
          if (data.errors && data.errors.length) { item.classList.add('is-error'); $('.upload-item__name', item).textContent = data.errors.join(' '); }
          else { $('.upload-item__remove', item).remove(); toast(`${file.name} uploaded.`, 'success', 1600); }
        } else {
          item.classList.add('is-error');
          $('.upload-item__name', item).textContent = (data.errors || [data.error || 'Upload failed']).join(' ');
        }
        if (pending === 0 && zone.dataset.reloadOnDone) setTimeout(() => window.location.reload(), 700);
        if (pending === 0 && !zone.dataset.reloadOnDone && !$('.upload-item.is-error', queue)) setTimeout(() => window.location.reload(), 900);
      };
      xhr.onerror = () => { pending -= 1; item.classList.add('is-error'); $('.upload-item__name', item).textContent = 'Network error'; };
      xhr.send(fd);
    }
  });

  /* ---------------------------------------------------------------- misc */
  $$('[data-check-all]').forEach(btn => btn.addEventListener('click', () => {
    const boxes = $$(`#${btn.dataset.checkAll} input[type=checkbox]`);
    const allChecked = boxes.every(b => b.checked);
    boxes.forEach(b => { b.checked = !allChecked; });
  }));
  // Show/hide navigation link fields based on link type
  const linkType = $('select[name=link_type]');
  if (linkType) {
    const map = { internal: 'internal_page', collection: 'collection', category: 'category', product: 'product', external: 'external_url' };
    const sync = () => Object.entries(map).forEach(([type, field]) => { const wrap = $(`[data-field="${field}"]`); if (wrap) wrap.hidden = linkType.value !== type; });
    linkType.addEventListener('change', sync); sync();
  }
  // Auto-slug helper
  const nameInput = $('input[name=name]'), slugInput = $('input[name=slug]');
  if (nameInput && slugInput && !slugInput.value) {
    nameInput.addEventListener('input', () => { if (slugInput.dataset.touched) return; slugInput.value = nameInput.value.toLowerCase().normalize('NFKD').replace(/[^\w\s-]/g, '').trim().replace(/[\s_]+/g, '-').slice(0, 180); });
    slugInput.addEventListener('input', () => { slugInput.dataset.touched = '1'; });
  }
})();

/* Catalog: switches, star toggles, select-all + bulk actions, action dropdown. */
(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const csrf = () => (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || ($('input[name=csrfmiddlewaretoken]') || {}).value || '';
  const toast = (m, t) => window.cmsToast && window.cmsToast(m, t, 1800);

  function ajaxForm(form, onOk) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      const btn = $('button[type=submit]', form);
      btn.disabled = true;
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
        .then(r => r.json())
        .then(d => { if (d.ok) onOk(btn, d); else toast('Could not update.', 'error'); })
        .catch(() => toast('Could not update.', 'error'))
        .finally(() => { btn.disabled = false; });
    });
  }
  $$('form[data-switch]').forEach(f => ajaxForm(f, (btn, d) => {
    const on = d.value !== undefined ? !!d.value : d.status === 'published';
    btn.classList.toggle('is-on', on); btn.setAttribute('aria-checked', on);
    const card = btn.closest('.pcard'); if (card && d.status) card.classList.toggle('is-draft', d.status !== 'published');
    toast('Saved.', 'success');
  }));
  $$('form[data-ajax-toggle]').forEach(f => ajaxForm(f, (btn, d) => { btn.classList.toggle(btn.dataset.toggleClass || 'is-on', !!d.value); toast('Saved.', 'success'); }));

  const selectAll = $('[data-select-all]');
  if (selectAll) selectAll.addEventListener('change', () => $$('[data-row-check]').forEach(c => { c.checked = selectAll.checked; }));
  $$('[data-dropdown]').forEach(dd => {
    $('[data-dropdown-toggle]', dd).addEventListener('click', e => { e.stopPropagation(); dd.classList.toggle('is-open'); });
    document.addEventListener('click', () => dd.classList.remove('is-open'));
  });
  const bulk = $('[data-bulk-form]');
  if (bulk) {
    bulk.addEventListener('submit', e => {
      const ids = $$('[data-row-check]:checked').map(c => c.value);
      if (!ids.length) { e.preventDefault(); toast('Select at least one product first.', 'error'); return; }
      const submitter = e.submitter;
      if (submitter && submitter.dataset.bulkConfirm && !bulk.dataset.confirmed) {
        e.preventDefault();
        window.cmsConfirm(submitter.dataset.bulkConfirm).then(ok => { if (ok) { bulk.dataset.confirmed = '1'; addIds(ids); submitter.click(); } });
        return;
      }
      addIds(ids);
    });
    function addIds(ids) { $$('input[name=ids]', bulk).forEach(i => i.remove()); ids.forEach(id => { const i = document.createElement('input'); i.type = 'hidden'; i.name = 'ids'; i.value = id; bulk.append(i); }); }
  }
})();
