/**
 * admin.js — Admin pages logic for Road Hazard Detection System
 * 
 * Handles:
 * - Dashboard data loading and rendering
 * - Reports listing with client-side filtering and pagination
 * - Report details loading and authority actions
 * - Confirmation dialogs
 * - Logout flow
 * 
 * Depends on auth.js being loaded first.
 */

const ADMIN_CONFIG = {
  API_BASE_URL: "http://localhost:5000",
  ENDPOINTS: {
    DASHBOARD_SUMMARY: "/api/admin/dashboard",
    REPORTS:           "/api/admin/reports",
    REPORT_DETAIL:     "/api/admin/reports/",   // + reportId
    UPDATE_REPORT:     "/api/admin/reports/",   // + reportId (PATCH)
    VERIFY_REPORT:     "/api/admin/reports/",   // + reportId + /verify (POST)
    REJECT_REPORT:     "/api/admin/reports/"    // + reportId + /reject (POST)
  },
  REPORTS_PER_PAGE: 6,
  REQUEST_TIMEOUT_MS: 15000
};

/* ============================================================
   FETCH HELPER
   ============================================================ */

async function adminFetch(url, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ADMIN_CONFIG.REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(ADMIN_CONFIG.API_BASE_URL + url, {
      credentials: "include",
      signal: controller.signal,
      ...options
    });

    clearTimeout(timeoutId);

    if (response.status === 401) {
      window.location.replace("index.html?expired=true");
      return null;
    }

    if (!response.ok) {
      throw new Error("Server error: " + response.status);
    }

    return await response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

/* ============================================================
   CONFIRMATION DIALOG
   ============================================================ */

function showConfirmDialog({ title, message, confirmText, cancelText, onConfirm, onCancel }) {
  // Remove existing dialog if any
  const existing = document.getElementById('confirm-dialog-overlay');
  if (existing) existing.remove();

  const overlay = document.createElement('div');
  overlay.id = 'confirm-dialog-overlay';
  overlay.className = 'modal-overlay confirm-dialog-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'confirm-dialog-title');

  overlay.innerHTML = `
    <div class="modal-content confirm-dialog">
      <div class="modal-header">
        <h2 id="confirm-dialog-title" class="modal-title">${escapeHtml(title)}</h2>
        <button type="button" class="btn-icon confirm-cancel-btn" aria-label="Close dialog">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
      <div class="modal-body">
        <p class="confirm-message">${escapeHtml(message)}</p>
      </div>
      <div class="confirm-actions">
        <button type="button" class="btn-secondary confirm-cancel-btn">${escapeHtml(cancelText || 'Cancel')}</button>
        <button type="button" class="btn-primary confirm-confirm-btn">${escapeHtml(confirmText || 'Confirm')}</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  const confirmBtn = overlay.querySelector('.confirm-confirm-btn');
  const cancelBtns = overlay.querySelectorAll('.confirm-cancel-btn');
  let triggerElement = document.activeElement;

  function closeDialog() {
    overlay.remove();
    if (triggerElement && triggerElement.focus) {
      triggerElement.focus();
    }
  }

  confirmBtn.addEventListener('click', () => {
    closeDialog();
    if (onConfirm) onConfirm();
  });

  cancelBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      closeDialog();
      if (onCancel) onCancel();
    });
  });

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeDialog();
      if (onCancel) onCancel();
    }
  });

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      closeDialog();
      if (onCancel) onCancel();
    }
    // Trap focus within dialog
    if (e.key === 'Tab') {
      const focusable = overlay.querySelectorAll('button:not([disabled])');
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  document.addEventListener('keydown', handleKeydown);

  // Store cleanup function
  const originalClose = closeDialog;
  overlay._closeDialog = () => {
    document.removeEventListener('keydown', handleKeydown);
    originalClose();
  };

  // Override closeDialog to also clean up
  const wrappedClose = overlay._closeDialog;
  confirmBtn.onclick = () => { wrappedClose(); if (onConfirm) onConfirm(); };
  cancelBtns.forEach(btn => {
    btn.onclick = () => { wrappedClose(); if (onCancel) onCancel(); };
  });
  overlay.onclick = (e) => {
    if (e.target === overlay) { wrappedClose(); if (onCancel) onCancel(); }
  };

  // Focus the confirm button
  confirmBtn.focus();
}

/* ============================================================
   TOAST / FEEDBACK NOTIFICATIONS
   ============================================================ */

function showToast(message, type) {
  // type: 'success' or 'error'
  const existing = document.getElementById('admin-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'admin-toast';
  toast.className = 'admin-toast admin-toast-' + type;
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');

  const icon = type === 'success' ? 'check_circle' : 'error';
  toast.innerHTML = `
    <span class="material-symbols-outlined" style="font-size:18px;">${icon}</span>
    <span>${escapeHtml(message)}</span>
  `;

  document.body.appendChild(toast);

  // Auto-remove after 4 seconds
  setTimeout(() => {
    toast.classList.add('admin-toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ============================================================
   UTILITY FUNCTIONS
   ============================================================ */

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

function formatTime(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  } catch {
    return '';
  }
}

function formatConfidence(val) {
  if (typeof val === 'string' && val.includes('%')) return val;
  if (typeof val === 'number') {
    return val <= 1 ? Math.round(val * 100) + '%' : Math.round(val) + '%';
  }
  return val || '—';
}

function getPriorityClass(priority) {
  if (!priority) return 'priority-low';
  switch (priority.toLowerCase()) {
    case 'critical': return 'priority-critical';
    case 'high': return 'priority-high';
    case 'medium': return 'priority-medium';
    case 'low': return 'priority-low';
    default: return 'priority-low';
  }
}

function getStatusClass(status) {
  if (!status) return 'status-pending';
  const s = status.toLowerCase().replace(/\s+/g, '-');
  switch (s) {
    case 'pending-review': return 'status-pending';
    case 'pending': return 'status-pending';
    case 'verified': return 'status-verified';
    case 'in-progress': return 'status-in-progress';
    case 'resolved': return 'status-resolved';
    case 'rejected': return 'status-rejected';
    default: return 'status-pending';
  }
}

/* ============================================================
   ADMIN HEADER SETUP (shared across admin pages)
   ============================================================ */

function setupAdminHeader(user) {
  displayUsername(user ? user.username : null);

  // Mobile menu toggle
  const menuToggle = document.getElementById('admin-menu-toggle');
  const mobileNav = document.getElementById('admin-mobile-nav');
  if (menuToggle && mobileNav) {
    menuToggle.addEventListener('click', () => {
      const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
      menuToggle.setAttribute('aria-expanded', !expanded);
      mobileNav.classList.toggle('hidden');
    });
  }

  // Logout buttons
  const logoutBtns = document.querySelectorAll('.btn-logout');
  logoutBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      showConfirmDialog({
        title: 'Confirm Logout',
        message: 'Are you sure you want to log out of the authority portal?',
        confirmText: 'LOGOUT',
        cancelText: 'CANCEL',
        onConfirm: () => performLogout()
      });
    });
  });
}

/* ============================================================
   DASHBOARD PAGE
   ============================================================ */

async function initDashboard(user) {
  setupAdminHeader(user);

  const cardsContainer = document.getElementById('dashboard-cards');
  const tableContainer = document.getElementById('dashboard-table-body');
  const dashboardDefault = document.getElementById('dashboard-default');
  const dashboardEmpty = document.getElementById('dashboard-empty');
  const dashboardError = document.getElementById('dashboard-error');
  const retryBtn = document.getElementById('dashboard-retry');

  function showState(state) {
    if (dashboardDefault) dashboardDefault.classList.toggle('hidden', state !== 'default');
    if (dashboardEmpty) dashboardEmpty.classList.toggle('hidden', state !== 'empty');
    if (dashboardError) dashboardError.classList.toggle('hidden', state !== 'error');
  }

  async function loadDashboard() {
    showState('default');
    // Show loading placeholders
    if (cardsContainer) {
      const cards = cardsContainer.querySelectorAll('.summary-value');
      cards.forEach(c => { c.textContent = '—'; c.classList.add('loading-pulse'); });
    }
    if (tableContainer) {
      tableContainer.innerHTML = '<tr><td colspan="8" class="table-loading">Loading reports...</td></tr>';
    }

    try {
      const data = await adminFetch(ADMIN_CONFIG.ENDPOINTS.DASHBOARD_SUMMARY);

      if (!data) return; // redirected

      // Populate summary cards
      const summary = data.summary || {};
      setCardValue('card-total', summary.total_reports);
      setCardValue('card-pending', summary.pending_review);
      setCardValue('card-high-priority', summary.high_priority);
      setCardValue('card-resolved', summary.resolved);

      // Populate recent reports
      const reports = data.recent_reports || [];
      if (reports.length === 0) {
        showState('empty');
        return;
      }

      renderDashboardTable(reports);
    } catch (err) {
      showState('error');
    }
  }

  function setCardValue(id, value) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value !== undefined && value !== null ? value : '—';
      el.classList.remove('loading-pulse');
    }
  }

  function renderDashboardTable(reports) {
    if (!tableContainer) return;
    tableContainer.innerHTML = '';

    reports.forEach(report => {
      const tr = document.createElement('tr');
      tr.className = 'table-row-hover';

      const conf = formatConfidence(report.confidence);
      const date = formatDate(report.submitted_at || report.date);
      const time = formatTime(report.submitted_at || report.date);

      tr.innerHTML = `
        <td class="table-cell cell-id">${escapeHtml(report.id || report.report_id || '—')}</td>
        <td class="table-cell cell-thumb">
          <div class="report-thumbnail">
            ${report.thumbnail || report.image_url ? 
              `<img src="${escapeHtml(report.thumbnail || report.image_url)}" alt="Report thumbnail" class="thumb-img">` :
              `<div class="thumb-placeholder"><span class="material-symbols-outlined" style="font-size:20px;color:var(--text-muted);">image</span></div>`
            }
          </div>
        </td>
        <td class="table-cell cell-type">${escapeHtml(report.hazard_type || '—')}</td>
        <td class="table-cell cell-conf">${escapeHtml(conf)}</td>
        <td class="table-cell cell-priority"><span class="priority-badge ${getPriorityClass(report.priority)}">${escapeHtml((report.priority || '—').toUpperCase())}</span></td>
        <td class="table-cell cell-status"><span class="status-badge ${getStatusClass(report.status)}">${escapeHtml((report.status || '—').toUpperCase())}</span></td>
        <td class="table-cell cell-date"><div>${escapeHtml(date)}</div><div class="cell-time">${escapeHtml(time)}</div></td>
        <td class="table-cell cell-action">
          <a href="admin-report-details.html?id=${encodeURIComponent(report.id || report.report_id || '')}" class="btn-view-details">
            <span>DETAILS</span>
            <span class="material-symbols-outlined" style="font-size:14px;">arrow_outward</span>
          </a>
        </td>
      `;

      tableContainer.appendChild(tr);
    });
  }

  if (retryBtn) {
    retryBtn.addEventListener('click', loadDashboard);
  }

  loadDashboard();
}

/* ============================================================
   REPORTS PAGE
   ============================================================ */

async function initReports(user) {
  setupAdminHeader(user);

  const tableBody = document.getElementById('reports-table-body');
  const stateTable = document.getElementById('reports-state-table');
  const stateEmpty = document.getElementById('reports-state-empty');
  const stateError = document.getElementById('reports-state-error');
  const stateLoading = document.getElementById('reports-state-loading');
  const paginationContainer = document.getElementById('reports-pagination');
  const showingText = document.getElementById('reports-showing-text');

  const searchInput = document.getElementById('reports-search');
  const filterType = document.getElementById('filter-type');
  const filterStatus = document.getElementById('filter-status');
  const filterPriority = document.getElementById('filter-priority');
  const filterDate = document.getElementById('filter-date');
  const clearFiltersBtn = document.getElementById('btn-clear-filters');
  const retryBtn = document.getElementById('reports-retry');
  const resetFiltersBtn = document.getElementById('reports-reset-filters');

  let allReports = [];
  let currentPage = 1;

  function showState(state) {
    if (stateTable) stateTable.classList.toggle('hidden', state !== 'table');
    if (stateEmpty) stateEmpty.classList.toggle('hidden', state !== 'empty');
    if (stateError) stateError.classList.toggle('hidden', state !== 'error');
    if (stateLoading) stateLoading.classList.toggle('hidden', state !== 'loading');
    if (paginationContainer) paginationContainer.classList.toggle('hidden', state !== 'table');
  }

  async function loadReports() {
    showState('loading');

    try {
      const data = await adminFetch(ADMIN_CONFIG.ENDPOINTS.REPORTS);
      if (!data) return;

      allReports = data.reports || [];
      currentPage = 1;
      applyFilters();
    } catch (err) {
      showState('error');
    }
  }

  function applyFilters() {
    let filtered = [...allReports];

    // Search by ID
    const searchVal = (searchInput ? searchInput.value.trim().toLowerCase() : '');
    if (searchVal) {
      filtered = filtered.filter(r => {
        const id = (r.id || r.report_id || '').toLowerCase();
        return id.includes(searchVal);
      });
    }

    // Filter by type
    const typeVal = filterType ? filterType.value : 'ALL';
    if (typeVal !== 'ALL') {
      filtered = filtered.filter(r => {
        const t = (r.hazard_type || '').toLowerCase().replace(/\s+/g, '_');
        return t === typeVal.toLowerCase() || 
               (r.hazard_type || '').toLowerCase() === typeVal.toLowerCase().replace(/_/g, ' ');
      });
    }

    // Filter by status
    const statusVal = filterStatus ? filterStatus.value : 'ALL';
    if (statusVal !== 'ALL') {
      filtered = filtered.filter(r => {
        const s = (r.status || '').toLowerCase().replace(/\s+/g, '_');
        return s === statusVal.toLowerCase() ||
               (r.status || '').toLowerCase() === statusVal.toLowerCase().replace(/_/g, ' ');
      });
    }

    // Filter by priority
    const priorityVal = filterPriority ? filterPriority.value : 'ALL';
    if (priorityVal !== 'ALL') {
      filtered = filtered.filter(r => 
        (r.priority || '').toLowerCase() === priorityVal.toLowerCase()
      );
    }

    // Filter by date
    const dateVal = filterDate ? filterDate.value : 'ALL';
    if (dateVal !== 'ALL') {
      const now = Date.now();
      const ranges = { '24H': 86400000, '7D': 604800000, '30D': 2592000000 };
      const range = ranges[dateVal];
      if (range) {
        filtered = filtered.filter(r => {
          const d = new Date(r.submitted_at || r.date);
          return !isNaN(d.getTime()) && (now - d.getTime()) <= range;
        });
      }
    }

    renderReportsTable(filtered);
  }

  function renderReportsTable(filtered) {
    if (filtered.length === 0) {
      showState('empty');
      return;
    }

    showState('table');

    const perPage = ADMIN_CONFIG.REPORTS_PER_PAGE;
    const totalPages = Math.ceil(filtered.length / perPage);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * perPage;
    const pageReports = filtered.slice(start, start + perPage);

    if (tableBody) {
      tableBody.innerHTML = '';
      pageReports.forEach(report => {
        const tr = document.createElement('tr');
        tr.className = 'table-row-hover';

        const conf = formatConfidence(report.confidence);
        const date = formatDate(report.submitted_at || report.date);
        const time = formatTime(report.submitted_at || report.date);

        tr.innerHTML = `
          <td class="table-cell cell-id">${escapeHtml(report.id || report.report_id || '—')}</td>
          <td class="table-cell cell-thumb">
            <div class="report-thumbnail">
              ${report.thumbnail || report.image_url ? 
                `<img src="${escapeHtml(report.thumbnail || report.image_url)}" alt="Report thumbnail" class="thumb-img">` :
                `<div class="thumb-placeholder"><span class="material-symbols-outlined" style="font-size:20px;color:var(--text-muted);">image</span></div>`
              }
            </div>
          </td>
          <td class="table-cell cell-type"><div class="cell-type-name">${escapeHtml(report.hazard_type || '—')}</div></td>
          <td class="table-cell cell-conf">${escapeHtml(conf)}</td>
          <td class="table-cell cell-priority"><span class="priority-badge ${getPriorityClass(report.priority)}">${escapeHtml((report.priority || '—').toUpperCase())}</span></td>
          <td class="table-cell cell-status"><span class="status-badge ${getStatusClass(report.status)}">${escapeHtml((report.status || '—').toUpperCase())}</span></td>
          <td class="table-cell cell-date"><div>${escapeHtml(date)}</div><div class="cell-time">${escapeHtml(time)}</div></td>
          <td class="table-cell cell-action">
            <a href="admin-report-details.html?id=${encodeURIComponent(report.id || report.report_id || '')}" class="btn-view-details">
              <span>VIEW</span>
              <span>→</span>
            </a>
          </td>
        `;

        tableBody.appendChild(tr);
      });
    }

    // Update showing text
    if (showingText) {
      const end = Math.min(start + perPage, filtered.length);
      showingText.innerHTML = `SHOWING <strong>${start + 1}–${end}</strong> OF <strong>${filtered.length}</strong> REPORTS`;
    }

    // Render pagination
    renderPagination(totalPages, filtered.length);
  }

  function renderPagination(totalPages) {
    if (!paginationContainer) return;
    const pagBtns = paginationContainer.querySelector('.pagination-buttons');
    if (!pagBtns) return;
    pagBtns.innerHTML = '';

    // Previous
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-btn';
    prevBtn.textContent = 'PREV';
    prevBtn.disabled = currentPage <= 1;
    prevBtn.addEventListener('click', () => { currentPage--; applyFilters(); });
    pagBtns.appendChild(prevBtn);

    // Page numbers
    const maxVisible = 5;
    let startP = Math.max(1, currentPage - 2);
    let endP = Math.min(totalPages, startP + maxVisible - 1);
    if (endP - startP < maxVisible - 1) startP = Math.max(1, endP - maxVisible + 1);

    if (startP > 1) {
      pagBtns.appendChild(createPageBtn(1));
      if (startP > 2) {
        const dots = document.createElement('span');
        dots.className = 'pagination-dots';
        dots.textContent = '...';
        pagBtns.appendChild(dots);
      }
    }

    for (let i = startP; i <= endP; i++) {
      pagBtns.appendChild(createPageBtn(i));
    }

    if (endP < totalPages) {
      if (endP < totalPages - 1) {
        const dots = document.createElement('span');
        dots.className = 'pagination-dots';
        dots.textContent = '...';
        pagBtns.appendChild(dots);
      }
      pagBtns.appendChild(createPageBtn(totalPages));
    }

    // Next
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-btn';
    nextBtn.textContent = 'NEXT';
    nextBtn.disabled = currentPage >= totalPages;
    nextBtn.addEventListener('click', () => { currentPage++; applyFilters(); });
    pagBtns.appendChild(nextBtn);
  }

  function createPageBtn(page) {
    const btn = document.createElement('button');
    btn.className = 'pagination-btn pagination-num' + (page === currentPage ? ' pagination-active' : '');
    btn.textContent = page;
    btn.addEventListener('click', () => { currentPage = page; applyFilters(); });
    return btn;
  }

  function resetFilters() {
    if (searchInput) searchInput.value = '';
    if (filterType) filterType.value = 'ALL';
    if (filterStatus) filterStatus.value = 'ALL';
    if (filterPriority) filterPriority.value = 'ALL';
    if (filterDate) filterDate.value = 'ALL';
    currentPage = 1;
    applyFilters();
  }

  // Event listeners for filters
  if (searchInput) searchInput.addEventListener('input', () => { currentPage = 1; applyFilters(); });
  if (filterType) filterType.addEventListener('change', () => { currentPage = 1; applyFilters(); });
  if (filterStatus) filterStatus.addEventListener('change', () => { currentPage = 1; applyFilters(); });
  if (filterPriority) filterPriority.addEventListener('change', () => { currentPage = 1; applyFilters(); });
  if (filterDate) filterDate.addEventListener('change', () => { currentPage = 1; applyFilters(); });
  if (clearFiltersBtn) clearFiltersBtn.addEventListener('click', resetFilters);
  if (resetFiltersBtn) resetFiltersBtn.addEventListener('click', resetFilters);
  if (retryBtn) retryBtn.addEventListener('click', loadReports);

  loadReports();
}

/* ============================================================
   REPORT DETAILS PAGE
   ============================================================ */

async function initReportDetails(user) {
  setupAdminHeader(user);

  const params = new URLSearchParams(window.location.search);
  const reportId = params.get('id');

  const loadingState = document.getElementById('detail-loading');
  const errorState = document.getElementById('detail-error');
  const contentState = document.getElementById('detail-content');
  const retryBtn = document.getElementById('detail-retry');

  if (!reportId) {
    showDetailState('error');
    return;
  }

  function showDetailState(state) {
    if (loadingState) loadingState.classList.toggle('hidden', state !== 'loading');
    if (errorState) errorState.classList.toggle('hidden', state !== 'error');
    if (contentState) contentState.classList.toggle('hidden', state !== 'content');
  }

  let currentReport = null;

  async function loadReport() {
    showDetailState('loading');

    try {
      const data = await adminFetch(ADMIN_CONFIG.ENDPOINTS.REPORT_DETAIL + encodeURIComponent(reportId));
      if (!data) return;

      currentReport = data.report || data;
      renderReport(currentReport);
      showDetailState('content');
    } catch (err) {
      showDetailState('error');
    }
  }

  function renderReport(report) {
    // Page title
    const titleEl = document.getElementById('detail-report-id');
    if (titleEl) titleEl.textContent = 'REPORT ' + (report.id || report.report_id || reportId);

    // Status badge in header
    const statusBadge = document.getElementById('detail-header-status');
    if (statusBadge) {
      statusBadge.textContent = (report.status || 'Pending Review').toUpperCase();
      statusBadge.className = 'status-badge-large ' + getStatusClass(report.status);
    }

    // Image
    const imageEl = document.getElementById('detail-image');
    if (imageEl) {
      if (report.image_url) {
        imageEl.src = report.image_url;
        imageEl.alt = 'Detection image for report ' + (report.id || reportId);
      } else {
        imageEl.alt = 'No image available';
      }
    }

    // Render bounding boxes if provided
    const bboxContainer = document.getElementById('detail-bboxes');
    if (bboxContainer && report.detections && report.detections.length > 0) {
      bboxContainer.innerHTML = '';
      report.detections.forEach((det, i) => {
        if (det.bbox) {
          const box = document.createElement('div');
          box.className = 'detail-bbox';
          const imgEl = document.getElementById('detail-image');
          if (imgEl && imgEl.naturalWidth) {
            const w = imgEl.clientWidth;
            const h = imgEl.clientHeight;
            const nw = imgEl.naturalWidth;
            const nh = imgEl.naturalHeight;
            box.style.left = (det.bbox.x1 / nw * w) + 'px';
            box.style.top = (det.bbox.y1 / nh * h) + 'px';
            box.style.width = ((det.bbox.x2 - det.bbox.x1) / nw * w) + 'px';
            box.style.height = ((det.bbox.y2 - det.bbox.y1) / nh * h) + 'px';
          }
          const label = document.createElement('div');
          label.className = 'detail-bbox-label';
          label.textContent = (det.class_name || det.hazard_type || 'Hazard') + ' · ' + formatConfidence(det.confidence);
          box.appendChild(label);
          bboxContainer.appendChild(box);
        }
      });
    }

    // Image metadata
    setText('detail-filename', report.filename || report.image_filename || '—');
    setText('detail-submitted', formatDate(report.submitted_at || report.date) + ' · ' + formatTime(report.submitted_at || report.date));

    // Report details metadata
    setText('detail-meta-id', report.id || report.report_id || reportId);
    setText('detail-meta-type', report.hazard_type || '—');
    setText('detail-meta-confidence', formatConfidence(report.confidence));
    setText('detail-meta-date', formatDate(report.submitted_at || report.date) + ' · ' + formatTime(report.submitted_at || report.date));
    setText('detail-meta-location', report.location || 'Location not provided');

    // Confidence bar
    const confBar = document.getElementById('detail-conf-bar');
    if (confBar) {
      let confVal = report.confidence;
      if (typeof confVal === 'number' && confVal <= 1) confVal = confVal * 100;
      confBar.style.width = (confVal || 0) + '%';
    }

    // Priority badge
    const priBadge = document.getElementById('detail-meta-priority');
    if (priBadge) {
      priBadge.textContent = (report.priority || '—').toUpperCase();
      priBadge.className = 'priority-badge ' + getPriorityClass(report.priority);
    }

    // Status badge in details
    const stBadge = document.getElementById('detail-meta-status');
    if (stBadge) {
      stBadge.textContent = (report.status || '—').toUpperCase();
      stBadge.className = 'status-badge ' + getStatusClass(report.status);
    }

    // Set form values
    const prioritySelect = document.getElementById('action-priority');
    if (prioritySelect) prioritySelect.value = report.priority || 'Low';

    const statusSelect = document.getElementById('action-status');
    if (statusSelect) statusSelect.value = report.status || 'Pending Review';

    const notesField = document.getElementById('action-notes');
    if (notesField) notesField.value = report.admin_notes || report.notes || '';

    // Activity timeline
    const activityContainer = document.getElementById('detail-activity');
    if (activityContainer && report.activity && report.activity.length > 0) {
      activityContainer.innerHTML = '';
      report.activity.forEach(event => {
        const card = document.createElement('div');
        card.className = 'activity-event';
        card.innerHTML = `
          <div class="activity-event-header">
            <span class="activity-event-title">
              <span class="material-symbols-outlined" style="font-size:14px;color:var(--accent-orange);">check_circle</span>
              ${escapeHtml(event.title || event.action || '—')}
            </span>
            <span class="activity-event-time">${escapeHtml(formatTime(event.timestamp || event.date) || '')}</span>
          </div>
          <p class="activity-event-desc">${escapeHtml(event.description || '')}</p>
        `;
        activityContainer.appendChild(card);
      });
      const activitySection = document.getElementById('detail-activity-section');
      if (activitySection) activitySection.classList.remove('hidden');
    }
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  // --- Authority Actions ---
  const saveBtn = document.getElementById('btn-save-changes');
  const verifyBtn = document.getElementById('btn-verify');
  const rejectBtn = document.getElementById('btn-reject');

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const priority = document.getElementById('action-priority').value;
      const status = document.getElementById('action-status').value;
      const notes = document.getElementById('action-notes').value;

      saveBtn.disabled = true;
      saveBtn.textContent = 'SAVING...';

      try {
        await adminFetch(ADMIN_CONFIG.ENDPOINTS.UPDATE_REPORT + encodeURIComponent(reportId), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ priority, status, notes })
        });
        showToast('Report updated successfully.', 'success');
        loadReport(); // Refresh data
      } catch (err) {
        showToast('Failed to update report. Please try again.', 'error');
      } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<span class="material-symbols-outlined" style="font-size:16px;">check</span> SAVE CHANGES';
      }
    });
  }

  if (verifyBtn) {
    verifyBtn.addEventListener('click', async () => {
      verifyBtn.disabled = true;
      try {
        await adminFetch(ADMIN_CONFIG.ENDPOINTS.VERIFY_REPORT + encodeURIComponent(reportId) + '/verify', {
          method: 'POST'
        });
        showToast('Detection verified successfully.', 'success');
        loadReport();
      } catch (err) {
        showToast('Failed to verify detection. Please try again.', 'error');
      } finally {
        verifyBtn.disabled = false;
      }
    });
  }

  if (rejectBtn) {
    rejectBtn.addEventListener('click', () => {
      showConfirmDialog({
        title: 'Mark as False Detection',
        message: 'Are you sure you want to mark this detection as false? This will set the status to Rejected.',
        confirmText: 'MARK AS FALSE',
        cancelText: 'CANCEL',
        onConfirm: async () => {
          rejectBtn.disabled = true;
          try {
            await adminFetch(ADMIN_CONFIG.ENDPOINTS.REJECT_REPORT + encodeURIComponent(reportId) + '/reject', {
              method: 'POST'
            });
            showToast('Detection marked as false.', 'success');
            loadReport();
          } catch (err) {
            showToast('Failed to reject detection. Please try again.', 'error');
          } finally {
            rejectBtn.disabled = false;
          }
        }
      });
    });
  }

  if (retryBtn) retryBtn.addEventListener('click', loadReport);

  loadReport();
}
