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

  /* ---------------------------------------------------------------- searchable select
     Progressive enhancement over a real <select>: the select keeps the value and
     submits as normal, so a failure here leaves a working dropdown rather than a
     dead field. Options come from the page, which is why there is no request to
     make while typing. */
  function bindCombobox(select) {
    if (select.dataset.comboboxBound) return;
    select.dataset.comboboxBound = 'true';

    const options = [...select.options];
    const wrap = document.createElement('div');
    wrap.className = 'combo';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'combo__input';
    input.autocomplete = 'off';
    input.placeholder = select.dataset.searchPlaceholder || 'Search…';
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-autocomplete', 'list');
    const list = document.createElement('ul');
    list.className = 'combo__list';
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    const listId = `${select.id || select.name}-combo-list`;
    list.id = listId;
    input.setAttribute('aria-controls', listId);

    // The label points at the select; move it to the input the editor types in.
    const label = select.id && document.querySelector(`label[for="${select.id}"]`);
    if (label) {
      input.id = `${select.id}-combo`;
      label.setAttribute('for', input.id);
    }

    select.parentNode.insertBefore(wrap, select);
    wrap.append(input, list, select);
    select.classList.add('combo__native');

    const labelFor = value => (options.find(o => o.value === value) || {}).textContent || '';
    const setValue = value => {
      select.value = value;
      input.value = value ? labelFor(value).trim() : '';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    };
    let active = -1;

    function close() {
      list.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      active = -1;
      // Typing without choosing must not look like a selection.
      input.value = select.value ? labelFor(select.value).trim() : '';
    }

    function render(query) {
      const q = query.trim().toLowerCase();
      const matches = options.filter(o => !q || o.textContent.toLowerCase().includes(q));
      list.innerHTML = '';
      if (!matches.length) {
        const li = document.createElement('li');
        li.className = 'combo__empty';
        li.textContent = 'No matching products';
        list.append(li);
      }
      matches.forEach((o, i) => {
        const li = document.createElement('li');
        li.className = 'combo__option';
        li.textContent = o.textContent.trim();
        li.setAttribute('role', 'option');
        li.dataset.value = o.value;
        li.setAttribute('aria-selected', String(o.value === select.value));
        li.addEventListener('mousedown', e => { e.preventDefault(); setValue(o.value); close(); });
        li.addEventListener('mouseenter', () => { active = i; highlight(); });
        list.append(li);
      });
      active = matches.findIndex(o => o.value === select.value);
      highlight();
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function highlight() {
      $$('.combo__option', list).forEach((li, i) => li.classList.toggle('is-active', i === active));
      const el = $$('.combo__option', list)[active];
      el && el.scrollIntoView({ block: 'nearest' });
    }

    input.value = select.value ? labelFor(select.value).trim() : '';
    input.addEventListener('focus', () => render(''));
    input.addEventListener('input', () => render(input.value));
    input.addEventListener('blur', () => setTimeout(close, 0));
    input.addEventListener('keydown', e => {
      const items = $$('.combo__option', list);
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (list.hidden) return render(input.value);
        active = Math.max(0, Math.min(items.length - 1, active + (e.key === 'ArrowDown' ? 1 : -1)));
        highlight();
      } else if (e.key === 'Enter') {
        if (list.hidden || !items[active]) return;
        e.preventDefault();
        setValue(items[active].dataset.value);
        close();
      } else if (e.key === 'Escape') {
        close();
      }
    });
  }
  $$('select[data-searchable]').forEach(bindCombobox);

  /* ---------------------------------------------------------------- multi-select
     Chips over a real <select multiple>, so the field still submits — and still
     works — if this never runs. Order matters: a browser submits options in DOM
     order, so picking one moves its <option> to the end of the select, and the
     server reads the order straight off the POST. */
  function bindMultiSelect(select) {
    if (select.dataset.multiselectBound) return;
    select.dataset.multiselectBound = 'true';

    const options = [...select.options];
    const byValue = new Map(options.map(o => [o.value, o]));
    const labelOf = value => (byValue.get(value) || {}).textContent.trim();

    const wrap = document.createElement('div');
    wrap.className = 'multi';
    const box = document.createElement('div');
    box.className = 'multi__box';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'multi__input';
    input.autocomplete = 'off';
    input.placeholder = select.dataset.searchPlaceholder || 'Search…';
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    const list = document.createElement('ul');
    list.className = 'multi__list';
    list.setAttribute('role', 'listbox');
    list.hidden = true;

    const label = select.id && document.querySelector(`label[for="${select.id}"]`);
    if (label) { input.id = `${select.id}-multi`; label.setAttribute('for', input.id); }

    select.parentNode.insertBefore(wrap, select);
    box.append(input);
    wrap.append(box, list, select);
    select.classList.add('multi__native');

    // Server-rendered order wins; fall back to whatever the select says.
    let chosen = (select.dataset.selectedOrder || '').split(',').filter(Boolean);
    if (!chosen.length) chosen = options.filter(o => o.selected).map(o => o.value);
    chosen = [...new Set(chosen.filter(v => byValue.has(v)))];

    let active = -1, dragging = null;

    function syncNative() {
      options.forEach(o => { o.selected = false; });
      chosen.forEach(v => { const o = byValue.get(v); o.selected = true; select.append(o); });
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function renderChips() {
      $$('.multi__chip', box).forEach(c => c.remove());
      chosen.forEach(value => {
        const chip = document.createElement('span');
        chip.className = 'multi__chip';
        chip.draggable = true;
        chip.dataset.value = value;
        const name = document.createElement('b');
        name.textContent = labelOf(value);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'multi__remove';
        remove.setAttribute('aria-label', `Remove ${labelOf(value)}`);
        remove.textContent = '×';
        remove.addEventListener('click', () => { chosen = chosen.filter(v => v !== value); apply(); });
        chip.append(name, remove);

        chip.addEventListener('dragstart', e => { dragging = value; chip.classList.add('is-dragging'); e.dataTransfer.effectAllowed = 'move'; });
        chip.addEventListener('dragend', () => { dragging = null; chip.classList.remove('is-dragging'); });
        chip.addEventListener('dragover', e => { if (dragging && dragging !== value) e.preventDefault(); });
        chip.addEventListener('drop', e => {
          e.preventDefault();
          if (!dragging || dragging === value) return;
          const rest = chosen.filter(v => v !== dragging);
          rest.splice(rest.indexOf(value), 0, dragging);
          chosen = rest;
          apply();
        });

        box.insertBefore(chip, input);
      });
    }

    function renderList(query) {
      const q = query.trim().toLowerCase();
      const left = options.filter(o => o.value && !chosen.includes(o.value) && (!q || o.textContent.toLowerCase().includes(q)));
      list.innerHTML = '';
      if (!left.length) {
        const li = document.createElement('li');
        li.className = 'multi__empty';
        li.textContent = q ? 'No matching products' : 'Every product is already chosen';
        list.append(li);
      }
      left.forEach((o, i) => {
        const li = document.createElement('li');
        li.className = 'multi__option';
        li.textContent = o.textContent.trim();
        li.setAttribute('role', 'option');
        li.dataset.value = o.value;
        li.addEventListener('mousedown', e => {
          e.preventDefault();
          chosen.push(o.value);
          input.value = '';
          apply();
          input.focus();
        });
        li.addEventListener('mouseenter', () => { active = i; highlight(); });
        list.append(li);
      });
      active = left.length ? 0 : -1;
      highlight();
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function highlight() {
      $$('.multi__option', list).forEach((li, i) => li.classList.toggle('is-active', i === active));
    }

    function close() {
      list.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      active = -1;
    }

    function apply() {
      renderChips();
      syncNative();
      if (!list.hidden) renderList(input.value);
    }

    input.addEventListener('focus', () => renderList(input.value));
    input.addEventListener('input', () => renderList(input.value));
    input.addEventListener('blur', () => setTimeout(close, 0));
    input.addEventListener('keydown', e => {
      const items = $$('.multi__option', list);
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (list.hidden) return renderList(input.value);
        active = Math.max(0, Math.min(items.length - 1, active + (e.key === 'ArrowDown' ? 1 : -1)));
        highlight();
      } else if (e.key === 'Enter') {
        if (list.hidden || !items[active]) return;
        e.preventDefault();
        chosen.push(items[active].dataset.value);
        input.value = '';
        apply();
      } else if (e.key === 'Backspace' && !input.value && chosen.length) {
        chosen.pop();
        apply();
      } else if (e.key === 'Escape') {
        close();
      }
    });
    box.addEventListener('click', e => { if (e.target === box) input.focus(); });

    renderChips();
    syncNative();
  }
  $$('select[data-multiselect]').forEach(bindMultiSelect);

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
      $$('select[data-searchable]', row).forEach(bindCombobox);
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

/* Rich text -------------------------------------------------------------------------
   A toolbar over a contenteditable surface, synced back into the original
   <textarea> so the form posts exactly as it always did. No library: the site
   has no build step and nothing else here is vendored, so a few hundred bytes
   of DOM beats shipping an editor bundle.

   Everything written here is sanitised again on the server before it reaches a
   page — see apps/core/html.py. The toolbar decides what is convenient to
   write; the allow-list decides what is safe to render. */
(() => {
  const AREAS = document.querySelectorAll('textarea[data-richtext]');
  if (!AREAS.length) return;

  // Chrome wraps new lines in <div> by default. Paragraphs are what the page
  // renders, so ask for those instead of translating them back later.
  try { document.execCommand('defaultParagraphSeparator', false, 'p'); } catch (e) { /* older engines */ }

  const BUTTONS = [
    { cmd: 'bold', label: 'B', title: 'Bold', style: 'font-weight:700' },
    { cmd: 'italic', label: 'I', title: 'Italic', style: 'font-style:italic' },
    { cmd: 'formatBlock', value: 'h2', label: 'H2', title: 'Heading' },
    { cmd: 'formatBlock', value: 'h3', label: 'H3', title: 'Sub-heading' },
    { cmd: 'insertUnorderedList', label: '• List', title: 'Bulleted list' },
    { cmd: 'insertOrderedList', label: '1. List', title: 'Numbered list' },
    { cmd: 'formatBlock', value: 'blockquote', label: '❝', title: 'Quote' },
    { cmd: 'createLink', label: 'Link', title: 'Add a link' },
    { cmd: 'removeFormat', label: 'Clear', title: 'Remove formatting' },
  ];

  // A body saved before the editor existed is plain text with blank lines
  // between paragraphs. Show it as the paragraphs it is meant to be.
  const toHtml = text => {
    if (/<(p|h2|h3|ul|ol|li|strong|em|blockquote|br|a)\b/i.test(text)) return text;
    return text.trim().split(/\n\s*\n/).filter(Boolean)
      .map(block => '<p>' + block.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])).replace(/\n/g, '<br>') + '</p>')
      .join('');
  };

  AREAS.forEach(area => {
    const wrap = document.createElement('div');
    wrap.className = 'richtext';

    const bar = document.createElement('div');
    bar.className = 'richtext__bar';

    const surface = document.createElement('div');
    surface.className = 'richtext__surface';
    surface.contentEditable = 'true';
    surface.setAttribute('role', 'textbox');
    surface.setAttribute('aria-multiline', 'true');
    surface.setAttribute('aria-label', (area.labels && area.labels[0] ? area.labels[0].textContent.trim() : 'Body') + ' editor');
    surface.innerHTML = toHtml(area.value || '');

    BUTTONS.forEach(spec => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'richtext__btn';
      b.title = spec.title;
      b.setAttribute('aria-label', spec.title);
      if (spec.style) b.setAttribute('style', spec.style);
      b.textContent = spec.label;
      b.addEventListener('mousedown', e => e.preventDefault()); // keep the selection
      b.addEventListener('click', () => {
        surface.focus();
        if (spec.cmd === 'createLink') {
          const href = window.prompt('Link address', 'https://');
          if (!href) return;
          document.execCommand('createLink', false, href);
        } else if (spec.value) {
          document.execCommand(spec.cmd, false, spec.value);
        } else {
          document.execCommand(spec.cmd, false, null);
        }
        sync();
      });
      bar.append(b);
    });

    const sync = () => { area.value = surface.innerHTML.trim(); };
    surface.addEventListener('input', sync);
    surface.addEventListener('blur', sync);
    area.form && area.form.addEventListener('submit', sync);

    // Pasting from Word or a web page drags styling in; keep the words only.
    surface.addEventListener('paste', e => {
      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData).getData('text/plain');
      document.execCommand('insertText', false, text);
    });

    area.classList.add('richtext__source');
    area.setAttribute('aria-hidden', 'true');
    area.tabIndex = -1;
    area.after(wrap);
    wrap.append(bar, surface);
    sync();
  });
})();
