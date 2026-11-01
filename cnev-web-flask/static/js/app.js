/* 极简交互脚本：提示条淡出、小屏侧栏开关、侧栏状态记忆，页面渲染全部由 Flask 完成 */
(function () {
  // 提示条 6 秒后淡出
  document.querySelectorAll('.flash').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s, transform .4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-6px)';
      setTimeout(function () { el.remove(); }, 420);
    }, 6000);
  });

  // 日期框：有值时隐藏自定义提示，避免盖住已填的日期
  document.querySelectorAll('.date-field').forEach(function (box) {
    var inp = box.querySelector('input');
    if (!inp) return;
    var sync = function () { box.classList.toggle('has-value', !!inp.value); };
    inp.addEventListener('input', sync);
    inp.addEventListener('change', sync);
    sync();
  });

  // ---------------- 侧栏：记住分组展开状态与滚动位置 ----------------
  // 导航是普通链接跳转，不做这件事的话每点一次都会「全部展开 + 滚回顶部」
  (function () {
    var nav = document.querySelector('.nav');
    if (!nav) return;

    var GROUP_KEY = 'cnev.nav.groups';
    var SCROLL_KEY = 'cnev.nav.scroll';

    function readGroups() {
      try { return JSON.parse(localStorage.getItem(GROUP_KEY)) || {}; } catch (e) { return {}; }
    }
    function writeGroups(o) {
      try { localStorage.setItem(GROUP_KEY, JSON.stringify(o)); } catch (e) {}
    }

    var groups = Array.prototype.slice.call(nav.querySelectorAll('details.nav-group'));
    var saved = readGroups();

    groups.forEach(function (d) {
      var key = d.getAttribute('data-group');
      if (!key) return;
      // 当前页所属分组必须展开，否则看不到高亮项
      if (d.getAttribute('data-active') === '1') {
        d.open = true;
        saved[key] = true;
        return;
      }
      if (Object.prototype.hasOwnProperty.call(saved, key)) d.open = !!saved[key];
    });
    writeGroups(saved);

    groups.forEach(function (d) {
      d.addEventListener('toggle', function () {
        var key = d.getAttribute('data-group');
        if (!key) return;
        var cur = readGroups();
        cur[key] = d.open;
        writeGroups(cur);
      });
    });

    // 滚动位置：进入页面时还原，离开前保存
    var y = 0;
    try { y = parseInt(localStorage.getItem(SCROLL_KEY) || '0', 10) || 0; } catch (e) {}
    if (y > 0) {
      var restore = function () { nav.scrollTop = y; };
      restore();
      // 字体/图标加载后高度可能变化，再补一次
      requestAnimationFrame(function () { restore(); setTimeout(restore, 60); });
    }
    window.addEventListener('beforeunload', function () {
      try { localStorage.setItem(SCROLL_KEY, String(nav.scrollTop)); } catch (e) {}
    });
  })();

  // 小屏：注入菜单按钮，控制侧栏展开
  if (window.innerWidth <= 900) {
    var bar = document.querySelector('.topbar');
    var side = document.querySelector('.sidebar');
    if (bar && side) {
      var btn = document.createElement('button');
      btn.className = 'btn ghost';
      btn.type = 'button';
      btn.textContent = '☰ 菜单';
      btn.style.marginRight = '10px';
      btn.addEventListener('click', function () {
        side.classList.toggle('open');
      });
      bar.insertBefore(btn, bar.firstChild);
      document.addEventListener('click', function (e) {
        if (!side.contains(e.target) && e.target !== btn) side.classList.remove('open');
      });
    }
  }
})();

/* ============================================================
   外键组合框（combo）
   原来的 <select> 只能从「库里已有」的记录里挑：要填一张单子、而它引用的
   那家公司还没入库时，用户只能先跳去新建、再回来重填一遍，表单数据全丢。
   这里改成：输入即筛选（数据多了也能找到）+ 右边「＋」现场新增，
   新增完通过 postMessage 把新记录带回本表单并自动选中。
   ============================================================ */
(function () {
  var combos = Array.prototype.slice.call(document.querySelectorAll('.combo'));
  if (!combos.length) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // 把命中的关键字标出来，长列表里一眼看到匹配在哪
  function hl(text, q) {
    var s = esc(text);
    if (!q) return s;
    var eq = esc(q);
    var i = s.toLowerCase().indexOf(eq.toLowerCase());
    if (i < 0) return s;
    return s.slice(0, i) + '<b>' + s.slice(i, i + eq.length) + '</b>' + s.slice(i + eq.length);
  }

  function fetchItems(url, q, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url + (url.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(q), true);
    xhr.timeout = 8000;
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      var data = null;
      try { data = JSON.parse(xhr.responseText); } catch (e) {}
      cb((data && data.items) || []);
    };
    xhr.send();
  }

  /* ---------------- 浮层：现场新增外键记录 ---------------- */
  var modal = null;

  function closeModal(notifyClosed) {
    if (!modal) return;
    var m = modal;
    modal = null;
    document.body.classList.remove('modal-open');
    if (m.mask.parentNode) m.mask.parentNode.removeChild(m.mask);
    if (!m.done && notifyClosed && m.onClosed) m.onClosed();
  }

  function openModal(url, title, onCreated, onClosed) {
    closeModal(false);
    var mask = document.createElement('div');
    mask.className = 'modal-mask';
    mask.innerHTML =
      '<div class="modal-box" role="dialog" aria-modal="true">' +
        '<div class="modal-head"><b>' + esc(title) + '</b>' +
          '<button class="modal-x" type="button" aria-label="关闭">' +
            '<svg class="ic" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
          '</button></div>' +
        '<iframe class="modal-frame" src="' + esc(url) + '" title="' + esc(title) + '"></iframe>' +
      '</div>';
    document.body.appendChild(mask);
    document.body.classList.add('modal-open');
    modal = { mask: mask, onCreated: onCreated, onClosed: onClosed, done: false };
    mask.querySelector('.modal-x').addEventListener('click', function () { closeModal(true); });
    mask.addEventListener('mousedown', function (e) { if (e.target === mask) closeModal(true); });
    requestAnimationFrame(function () { mask.classList.add('in'); });
  }

  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || d.cnev !== 'ref-created' || !modal) return;
    var m = modal;
    m.done = true;
    closeModal(false);
    if (m.onCreated) m.onCreated(d);
  });

  /* ---------------- 组合框 ---------------- */
  function Combo(root) {
    var self = this;
    this.root = root;
    this.hidden = root.querySelector('input[type=hidden]');
    this.text = root.querySelector('.combo-input');
    this.panel = root.querySelector('.combo-panel');
    this.list = root.querySelector('.combo-list');
    this.countEl = root.querySelector('.combo-count');
    this.clearBtn = root.querySelector('.combo-clear');
    this.err = root.parentNode ? root.parentNode.querySelector('.combo-err') : null;
    this.required = root.getAttribute('data-required') === '1';
    this.url = root.getAttribute('data-lookup');
    this.newUrl = root.getAttribute('data-new');
    this.table = root.getAttribute('data-table');
    this.refLabel = root.getAttribute('data-ref-label') || '记录';
    this.items = [];
    this.active = -1;
    this.seq = 0;
    this.opened = false;
    this.timer = null;

    this.text.addEventListener('focus', function () { self.open(); });
    this.text.addEventListener('click', function () { self.open(); });
    this.text.addEventListener('input', function () { self.onType(); });
    this.text.addEventListener('keydown', function (e) { self.onKey(e); });
    this.text.addEventListener('blur', function () {
      setTimeout(function () {
        if (!self.root.contains(document.activeElement)) self.close();
      }, 130);
    });

    root.querySelector('.combo-add').addEventListener('click', function (e) {
      e.preventDefault();
      self.create();
    });
    root.querySelector('.combo-new').addEventListener('click', function (e) {
      e.preventDefault();
      self.create();
    });
    if (this.clearBtn) {
      this.clearBtn.addEventListener('click', function (e) { e.preventDefault(); self.clear(); });
    }
    this.list.addEventListener('click', function (e) {
      var el = e.target.closest ? e.target.closest('.combo-item') : null;
      if (!el) return;
      self.pick(self.items[+el.getAttribute('data-i')]);
    });
  }

  Combo.prototype.open = function () {
    if (this.opened) return;
    this.opened = true;
    this.panel.hidden = false;
    this.root.classList.add('open');
    this.fit();
    this.load('');
  };

  // 面板别超出窗口：下方不够就往上弹，两边都不够就压缩列表高度，保证「＋ 新增」始终点得到
  Combo.prototype.fit = function () {
    var r = this.text.getBoundingClientRect();
    var vh = window.innerHeight || 800;
    var ideal = 268;
    var below = vh - r.bottom - 16;
    var above = r.top - 16;
    var up = below < ideal && above > below;
    this.panel.classList.toggle('up', up);
    var avail = Math.max(132, Math.min(ideal, up ? above : below));
    this.panel.style.setProperty('--pmax', avail + 'px');
  };

  Combo.prototype.close = function () {
    if (!this.opened) return;
    this.opened = false;
    this.seq += 1;
    this.panel.hidden = true;
    this.root.classList.remove('open');
  };

  Combo.prototype.load = function (q) {
    var self = this;
    var my = ++this.seq;
    this.list.innerHTML = '<div class="combo-loading">加载中…</div>';
    fetchItems(this.url, q, function (items) {
      if (my !== self.seq || !self.opened) return;
      self.items = items;
      self.active = items.length ? 0 : -1;
      self.render(q);
    });
  };

  Combo.prototype.render = function (q) {
    var self = this;
    if (!this.items.length) {
      this.list.innerHTML = '<div class="combo-empty">没有匹配的' + esc(this.refLabel) +
        '<br><span>换个关键字，或点下方「＋ 新增」</span></div>';
      this.countEl.textContent = '0 条';
      return;
    }
    this.list.innerHTML = this.items.map(function (o, i) {
      var cls = 'combo-item';
      if (String(o.v) === String(self.hidden.value)) cls += ' sel';
      if (i === self.active) cls += ' on';
      return '<div class="' + cls + '" data-i="' + i + '" role="option">' +
        '<span class="combo-l">' + hl(o.l, q) + '</span>' +
        '<code class="combo-v">' + esc(o.v) + '</code></div>';
    }).join('');
    this.countEl.textContent = this.items.length >= 60
      ? '前 60 条 · 继续输入可缩小范围'
      : this.items.length + ' 条';
  };

  Combo.prototype.onType = function () {
    var self = this;
    // 手一改文本，之前选中的值就作废，避免「文字是 A、实际提交 B」
    this.hidden.value = '';
    this.root.classList.remove('has-value');
    if (this.clearBtn) this.clearBtn.hidden = true;
    if (!this.opened) this.open();
    clearTimeout(this.timer);
    this.timer = setTimeout(function () { self.load(self.text.value.trim()); }, 160);
  };

  Combo.prototype.onKey = function (e) {
    if (e.key === 'Escape') {
      this.close();
      this.text.blur();
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!this.opened) { this.open(); return; }
      e.preventDefault();
      var n = this.items.length;
      if (!n) return;
      this.active = (this.active + (e.key === 'ArrowDown' ? 1 : n - 1)) % n;
      this.render(this.text.value.trim());
      var on = this.list.querySelector('.combo-item.on');
      if (on && on.scrollIntoView) on.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (e.key === 'Enter' && this.opened) {
      e.preventDefault();
      this.pick(this.items[this.active]);
    }
  };

  Combo.prototype.pick = function (o) {
    if (!o) return;
    this.hidden.value = o.v;
    this.text.value = o.l;
    this.root.classList.add('has-value');
    if (this.clearBtn) this.clearBtn.hidden = false;
    this.hideErr();
    this.close();
  };

  Combo.prototype.clear = function () {
    this.hidden.value = '';
    this.text.value = '';
    this.root.classList.remove('has-value');
    if (this.clearBtn) this.clearBtn.hidden = true;
    this.close();
    this.text.focus();
  };

  Combo.prototype.showErr = function () { if (this.err) this.err.hidden = false; };
  Combo.prototype.hideErr = function () { if (this.err) this.err.hidden = true; };

  Combo.prototype.create = function () {
    var self = this;
    this.close();
    var url = this.newUrl + (this.newUrl.indexOf('?') >= 0 ? '&' : '?') + 'embed=1';
    openModal(url, '新增' + this.refLabel, function (msg) {
      var item = { v: msg.v, l: msg.l || msg.v };
      self.items.unshift(item);
      self.pick(item);
      var total = (parseInt(self.root.getAttribute('data-total'), 10) || 0) + 1;
      self.root.setAttribute('data-total', total);
      self.text.placeholder = '输入名称或代码筛选，共 ' + total + ' 条';
    }, function () {
      if (self.opened) self.load('');
    });
  };

  var list = combos.map(function (el) { return new Combo(el); });

  // 点空白处收起
  document.addEventListener('click', function (e) {
    list.forEach(function (c) {
      if (c.opened && !c.root.contains(e.target)) c.close();
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal) closeModal(true);
  });

  // 必填外键：hidden 兜底校验（原生 required 对隐藏域无效）
  var forms = document.querySelectorAll('form.form-card');
  Array.prototype.forEach.call(forms, function (form) {
    form.addEventListener('submit', function (e) {
      var bad = null;
      list.forEach(function (c) {
        if (c.required && !c.hidden.value && !bad && form.contains(c.root)) bad = c;
      });
      if (!bad) return;
      e.preventDefault();
      bad.showErr();
      bad.text.focus();
      if (bad.root.scrollIntoView) bad.root.scrollIntoView({ block: 'center', behavior: 'smooth' });
    });
  });
})();
