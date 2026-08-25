/**
 * Gesture Flow — Unified Frontend Application Logic
 * Integrates Landing Page, Authentication Lifecycle, Dashboard, and Interactive CV Simulator.
 */

// Global state
let currentMappings = [
  { gesture: "INDEX_POINT", action: "POINTER_MOVE", sensitivity: 1.2, confidence_threshold: 0.70, cooldown_ms: 20, enabled: true, hardware: "Win32 / Android Pointer" },
  { gesture: "PINCH", action: "TAP", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 400, enabled: true, hardware: "Hardware Tap Event" },
  { gesture: "SWIPE_UP", action: "SCROLL_UP", sensitivity: 1.0, confidence_threshold: 0.70, cooldown_ms: 450, enabled: true, hardware: "Scroll Wheel Event" },
  { gesture: "SWIPE_DOWN", action: "SCROLL_DOWN", sensitivity: 1.0, confidence_threshold: 0.70, cooldown_ms: 450, enabled: true, hardware: "Scroll Wheel Event" },
  { gesture: "SWIPE_LEFT", action: "BACK", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 550, enabled: true, hardware: "Alt+Left / Back Action" },
  { gesture: "SWIPE_RIGHT", action: "HOME", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 550, enabled: true, hardware: "Win+D / Home Action" },
  { gesture: "OPEN_PALM", action: "PAUSE_GESTURES", sensitivity: 1.0, confidence_threshold: 0.80, cooldown_ms: 700, enabled: true, hardware: "Local Engine Toggle" },
  { gesture: "TWO_FINGERS", action: "MEDIA_PLAY_PAUSE", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 500, enabled: true, hardware: "Media Play/Pause Key" },
  { gesture: "FIST", action: "EMERGENCY_STOP", sensitivity: 1.0, confidence_threshold: 0.85, cooldown_ms: 800, enabled: true, hardware: "Safety Lockout" }
];

const SAFE_ACTIONS = [
  "POINTER_MOVE", "TAP", "SCROLL_UP", "SCROLL_DOWN", "BACK", "HOME", "RECENTS",
  "VOLUME_UP", "VOLUME_DOWN", "MEDIA_PLAY_PAUSE", "PAUSE_GESTURES", "EMERGENCY_STOP"
];

// =============================================================================
// DOM Initialization & Lifecycle
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  initViewRouter();
  initLandingEvents();
  initAuthModal();
  initDashboardTabs();
  initRangeSliders();
  initForms();
  initTiltCards();
  initCanvasSimulator();

  // Initial Sync
  checkBackendHealth();
  if (api.isAuthenticated()) {
    showDashboardView();
  } else {
    showLandingView();
  }
});

// Toast Notification
function showToast(message, isError = false) {
  const toast = document.getElementById("toastNotification");
  if (!toast) return;

  toast.className = `toast-container ${isError ? "toast-error" : "toast-success"}`;
  toast.textContent = message;
  toast.style.opacity = "1";
  toast.style.transform = "translateY(0)";

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(15px)";
  }, 3500);
}

// Session Expired Hook
window.onAuthExpired = () => {
  showToast("Session expired. Please sign in again.", true);
  showLandingView();
  openAuthModal();
};

// =============================================================================
// View Router (Landing vs Dashboard)
// =============================================================================

function initViewRouter() {
  document.getElementById("btnReturnToLanding")?.addEventListener("click", () => {
    showLandingView();
  });
}

function showLandingView() {
  document.getElementById("landingView").style.display = "block";
  document.getElementById("dashboardView").style.display = "none";
  window.scrollTo(0, 0);
  if (window.lucide) lucide.createIcons();
}

function showDashboardView() {
  document.getElementById("landingView").style.display = "none";
  document.getElementById("dashboardView").style.display = "flex";
  window.scrollTo(0, 0);
  updateUserUI();
  loadCloudData();
  if (window.lucide) lucide.createIcons();
}

// Landing Page Event Listeners
function initLandingEvents() {
  document.getElementById("btnLandingSignIn")?.addEventListener("click", () => {
    openAuthModal(false);
  });
  document.getElementById("btnLandingGetStarted")?.addEventListener("click", () => {
    if (api.isAuthenticated()) {
      showDashboardView();
    } else {
      openAuthModal(true);
    }
  });
  document.getElementById("btnHeroGetStarted")?.addEventListener("click", () => {
    if (api.isAuthenticated()) {
      showDashboardView();
    } else {
      openAuthModal(true);
    }
  });
  document.getElementById("btnHeroDemo")?.addEventListener("click", () => {
    showDashboardView();
    const simTab = document.querySelector('.nav-item[data-tab="simulator"]');
    if (simTab) simTab.click();
  });
  document.getElementById("btnBottomCta")?.addEventListener("click", () => {
    if (api.isAuthenticated()) {
      showDashboardView();
    } else {
      openAuthModal(true);
    }
  });
}

// =============================================================================
// Dashboard Navigation & Tabs
// =============================================================================

function initDashboardTabs() {
  const navButtons = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const pageTitle = document.getElementById("pageTitle");
  const pageSubtitle = document.getElementById("pageSubtitle");
  const currentCrumb = document.getElementById("currentCrumb");

  const titles = {
    overview: { crumb: "Dashboard", title: "Touchless HCI System Overview", sub: "Real-time computer vision telemetry, local MediaPipe hand landmark pipeline & safe Android Accessibility actions" },
    simulator: { crumb: "Interactive CV", title: "Live Hand Tracking Simulator", sub: "Interactive 21-joint skeleton kinematics and gesture state machine visualizer" },
    mappings: { crumb: "Mappings", title: "Gesture-to-Action Mappings", sub: "Configure touchless actions, sensitivity multipliers, and debounce cooldowns" },
    calibration: { crumb: "Calibration", title: "Hand Geometry Calibration", sub: "Fine-tune biometric hand size baseline, pinch threshold, and tremor deadband" },
    settings: { crumb: "Settings", title: "Application Preferences", sub: "Camera resolution, UI themes, and cloud synchronization settings" },
    documentation: { crumb: "Documentation", title: "Project Methodology & Report", sub: "College capstone architecture, security model, and academic implementation report" }
  };

  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.dataset.tab;
      navButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(`tab-${tabId}`);
      if (targetPane) targetPane.classList.add("active");

      if (titles[tabId]) {
        currentCrumb.textContent = titles[tabId].crumb;
        pageTitle.textContent = titles[tabId].title;
        pageSubtitle.textContent = titles[tabId].sub;
      }

      if (window.lucide) lucide.createIcons();
    });
  });

  document.getElementById("btnRefreshStats")?.addEventListener("click", () => {
    checkBackendHealth();
    loadCloudData();
    showToast("Synchronizing with MongoDB Atlas...");
  });

  document.getElementById("btnOverviewRefresh")?.addEventListener("click", () => {
    loadCloudData();
    showToast("Refreshed gesture matrix.");
  });

  document.getElementById("btnLogoutBtn")?.addEventListener("click", () => {
    if (confirm("Are you sure you want to sign out?")) {
      api.clearSession();
      showLandingView();
      showToast("Signed out successfully.");
    }
  });
}

// 3D Card Hover Tilt
function initTiltCards() {
  const cards = document.querySelectorAll(".hover-tilt");
  cards.forEach(card => {
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -5;
      const rotateY = ((x - centerX) / centerX) * 5;

      card.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "perspective(800px) rotateX(0) rotateY(0) translateY(0)";
    });
  });
}

// Sliders initialization
function initRangeSliders() {
  const ranges = ["calibPinch", "calibHandScale", "calibConfidence", "calibJitter"];
  ranges.forEach(id => {
    const el = document.getElementById(id);
    const valEl = document.getElementById(`${id}Val`);
    if (el && valEl) {
      el.addEventListener("input", () => {
        valEl.textContent = el.value;
      });
    }
  });
}

// =============================================================================
// Backend & MongoDB Atlas Health & Sync
// =============================================================================

async function checkBackendHealth() {
  const card = document.getElementById("backendStatusCard");
  const text = document.getElementById("backendStatusText");
  const statDbState = document.getElementById("statDbState");

  try {
    const data = await api.checkHealth();
    if (card) {
      card.classList.remove("offline");
      card.classList.add("online");
    }
    if (text) text.textContent = "FastAPI + Atlas Connected";
    if (statDbState) {
      statDbState.textContent = data.database === "connected" ? "MongoDB Atlas (Live)" : "Local SQLite Cache";
    }
  } catch (err) {
    if (card) {
      card.classList.remove("online");
      card.classList.add("offline");
    }
    if (text) text.textContent = "FastAPI Offline / Local Mode";
    if (statDbState) statDbState.textContent = "Local SQLite Cache";
  }
}

async function loadCloudData() {
  try {
    const gestures = await api.getGestures();
    if (gestures && gestures.length > 0) {
      currentMappings = gestures;
    }
  } catch (err) {
    // Keep local fallback
  }

  renderOverviewTable();
  renderMappingCards();

  if (api.isAuthenticated()) {
    try {
      const calib = await api.getCalibration();
      if (calib) {
        const pEl = document.getElementById("calibPinch");
        const sEl = document.getElementById("calibHandScale");
        const cEl = document.getElementById("calibConfidence");
        const jEl = document.getElementById("calibJitter");

        if (pEl) { pEl.value = calib.pinch_threshold; document.getElementById("calibPinchVal").textContent = calib.pinch_threshold; }
        if (sEl) { sEl.value = calib.hand_scale_baseline; document.getElementById("calibHandScaleVal").textContent = calib.hand_scale_baseline; }
        if (cEl) { cEl.value = calib.confidence_threshold; document.getElementById("calibConfidenceVal").textContent = calib.confidence_threshold; }
        if (jEl) { jEl.value = calib.jitter_deadband; document.getElementById("calibJitterVal").textContent = calib.jitter_deadband; }
      }
    } catch {}

    try {
      const settings = await api.getSettings();
      if (settings) {
        if (settings.theme) document.getElementById("settingTheme").value = settings.theme;
        if (settings.camera_resolution) document.getElementById("settingResolution").value = settings.camera_resolution;
        if (settings.target_fps) document.getElementById("settingTargetFps").value = settings.target_fps;
        if (settings.pointer_sensitivity) document.getElementById("settingPointerSens").value = settings.pointer_sensitivity;
      }
    } catch {}
  }
}

// Render Overview Matrix Table
function renderOverviewTable() {
  const tbody = document.getElementById("overviewGesturesTable");
  if (!tbody) return;

  tbody.innerHTML = currentMappings.map(m => `
    <tr>
      <td><strong style="color:#f1f5f9;font-weight:700;">${m.gesture}</strong></td>
      <td><span class="action-pill">${m.action}</span></td>
      <td><span style="font-family:var(--font-mono);font-size:0.8rem;color:#94a3b8;">${m.cooldown_ms} ms</span></td>
      <td><span style="font-family:var(--font-mono);font-weight:700;color:#38bdf8;">${Math.round(m.confidence_threshold * 100)}%</span></td>
      <td><code style="font-size:0.75rem;color:#a5b4fc;">${m.hardware || 'AccessibilityService'}</code></td>
      <td><span class="pill-badge" style="background:rgba(16,185,129,0.15);color:#34d399;border-color:rgba(16,185,129,0.3);">Ready</span></td>
    </tr>
  `).join("");
}

// Render Mapping Customization Cards
function renderMappingCards() {
  const container = document.getElementById("mappingsContainer");
  if (!container) return;

  container.innerHTML = currentMappings.map((m, idx) => `
    <div class="mapping-card">
      <div class="mapping-card-header">
        <span class="mapping-gesture-name">${m.gesture}</span>
        <label style="display:flex;align-items:center;gap:6px;font-size:0.78rem;font-weight:700;color:#94a3b8;cursor:pointer;">
          <input type="checkbox" ${m.enabled ? 'checked' : ''} onchange="updateMappingField(${idx}, 'enabled', this.checked)"> Active
        </label>
      </div>

      <div class="form-group-glass" style="padding:10px;">
        <label style="font-size:0.75rem;">Dispatched Safe Action</label>
        <select class="form-control" onchange="updateMappingField(${idx}, 'action', this.value)">
          ${SAFE_ACTIONS.map(act => `<option value="${act}" ${act === m.action ? 'selected' : ''}>${act}</option>`).join("")}
        </select>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group-glass" style="padding:10px;">
          <label style="font-size:0.75rem;">Cooldown (ms)</label>
          <input type="number" class="form-control" value="${m.cooldown_ms}" min="20" max="3000" step="50" onchange="updateMappingField(${idx}, 'cooldown_ms', parseInt(this.value))">
        </div>
        <div class="form-group-glass" style="padding:10px;">
          <label style="font-size:0.75rem;">Min Confidence</label>
          <input type="number" class="form-control" value="${m.confidence_threshold}" min="0.4" max="0.95" step="0.05" onchange="updateMappingField(${idx}, 'confidence_threshold', parseFloat(this.value))">
        </div>
      </div>
    </div>
  `).join("");
}

window.updateMappingField = function(idx, field, value) {
  if (currentMappings[idx]) {
    currentMappings[idx][field] = value;
  }
};

// =============================================================================
// Forms & Settings
// =============================================================================

function initForms() {
  document.getElementById("btnSaveMappings")?.addEventListener("click", async () => {
    if (!api.isAuthenticated()) {
      openAuthModal();
      showToast("Please sign in to save mappings to MongoDB Atlas.", true);
      return;
    }

    try {
      for (const m of currentMappings) {
        await api.updateGesture(m.gesture, m);
      }
      showToast("All gesture mappings saved to MongoDB Atlas!");
      renderOverviewTable();
    } catch (e) {
      showToast(e.message, true);
    }
  });

  document.getElementById("calibrationForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!api.isAuthenticated()) {
      openAuthModal();
      return;
    }

    const payload = {
      pinch_threshold: parseFloat(document.getElementById("calibPinch").value),
      hand_scale_baseline: parseFloat(document.getElementById("calibHandScale").value),
      confidence_threshold: parseFloat(document.getElementById("calibConfidence").value),
      jitter_deadband: parseFloat(document.getElementById("calibJitter").value)
    };

    try {
      await api.updateCalibration(payload);
      showToast("Calibration profile synced to MongoDB Atlas!");
    } catch (err) {
      showToast(err.message, true);
    }
  });

  document.getElementById("settingsForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!api.isAuthenticated()) {
      openAuthModal();
      return;
    }

    const payload = {
      theme: document.getElementById("settingTheme").value,
      camera_resolution: document.getElementById("settingResolution").value,
      target_fps: parseInt(document.getElementById("settingTargetFps").value),
      pointer_sensitivity: parseFloat(document.getElementById("settingPointerSens").value)
    };

    try {
      await api.updateSettings(payload);
      showToast("Application settings updated in MongoDB Atlas!");
    } catch (err) {
      showToast(err.message, true);
    }
  });
}

// =============================================================================
// Authentication Modal
// =============================================================================

function initAuthModal() {
  const modal = document.getElementById("authModal");
  const closeBtn = document.getElementById("authModalClose");
  const tabLogin = document.getElementById("tabLoginBtn");
  const tabRegister = document.getElementById("tabRegisterBtn");
  const groupName = document.getElementById("groupName");
  const authForm = document.getElementById("authForm");
  const modalTitle = document.getElementById("authModalTitle");
  const submitBtn = document.getElementById("authSubmitBtn");
  const errorMsg = document.getElementById("authErrorMsg");

  let isRegisterMode = false;

  window.openAuthModal = (startWithRegister = false) => {
    modal.classList.add("open");
    errorMsg.textContent = "";
    if (startWithRegister) {
      tabRegister.click();
    } else {
      tabLogin.click();
    }
  };

  closeBtn?.addEventListener("click", () => modal.classList.remove("open"));

  tabLogin?.addEventListener("click", () => {
    isRegisterMode = false;
    tabLogin.classList.add("active");
    tabRegister.classList.remove("active");
    groupName.style.display = "none";
    modalTitle.textContent = "Sign In to Gesture Flow";
    submitBtn.querySelector("span").textContent = "Sign In";
    errorMsg.textContent = "";
  });

  tabRegister?.addEventListener("click", () => {
    isRegisterMode = true;
    tabRegister.classList.add("active");
    tabLogin.classList.remove("active");
    groupName.style.display = "flex";
    modalTitle.textContent = "Create Account";
    submitBtn.querySelector("span").textContent = "Create Account";
    errorMsg.textContent = "";
  });

  authForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorMsg.textContent = "";

    const email = document.getElementById("inputEmail").value;
    const password = document.getElementById("inputPassword").value;
    const name = document.getElementById("inputName").value || "Demo Student";

    try {
      const data = isRegisterMode
        ? await api.register(name, email, password)
        : await api.login(email, password);

      modal.classList.remove("open");
      showDashboardView();
      showToast(`Welcome back, ${data.user.name}!`);
    } catch (err) {
      errorMsg.textContent = err.message || "Authentication failed.";
    }
  });
}

function updateUserUI() {
  const user = api.getUser();
  const userNameEl = document.getElementById("userNameDisplay");
  const userEmailEl = document.getElementById("userEmailDisplay");
  const userAvatarEl = document.getElementById("userAvatar");

  if (user) {
    if (userNameEl) userNameEl.textContent = user.name || "Student User";
    if (userEmailEl) userEmailEl.textContent = user.email || "";
    if (userAvatarEl) userAvatarEl.textContent = (user.name || "U")[0].toUpperCase();
  } else {
    if (userNameEl) userNameEl.textContent = "Demo Student User";
    if (userEmailEl) userEmailEl.textContent = "Local Offline Mode";
    if (userAvatarEl) userAvatarEl.textContent = "U";
  }
}

// =============================================================================
// Interactive Canvas Hand Landmark Simulator
// =============================================================================

function initCanvasSimulator() {
  const canvas = document.getElementById("handSimulatorCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const gestureHud = document.getElementById("simGestureHud");
  const confHud = document.getElementById("simConfHud");
  const logEntries = document.getElementById("simLogEntries");
  const simButtons = document.querySelectorAll(".btn-gesture-sim");

  const connections = [
    [0, 1], [1, 2], [2, 3], [3, 4],
    [0, 5], [5, 6], [6, 7], [7, 8],
    [5, 9], [9, 10], [10, 11], [11, 12],
    [9, 13], [13, 14], [14, 15], [15, 16],
    [13, 17], [17, 18], [18, 19], [19, 20],
    [0, 17]
  ];

  const baseKeypoints = {
    point: [
      {x: 0.50, y: 0.82}, {x: 0.44, y: 0.76}, {x: 0.38, y: 0.70}, {x: 0.32, y: 0.65}, {x: 0.40, y: 0.70},
      {x: 0.46, y: 0.58}, {x: 0.46, y: 0.46}, {x: 0.46, y: 0.34}, {x: 0.46, y: 0.22},
      {x: 0.51, y: 0.57}, {x: 0.51, y: 0.66}, {x: 0.51, y: 0.72}, {x: 0.51, y: 0.68},
      {x: 0.56, y: 0.58}, {x: 0.56, y: 0.67}, {x: 0.56, y: 0.73}, {x: 0.56, y: 0.69},
      {x: 0.61, y: 0.61}, {x: 0.61, y: 0.69}, {x: 0.61, y: 0.75}, {x: 0.61, y: 0.70}
    ],
    pinch: [
      {x: 0.50, y: 0.82}, {x: 0.44, y: 0.76}, {x: 0.40, y: 0.68}, {x: 0.42, y: 0.50}, {x: 0.45, y: 0.36},
      {x: 0.46, y: 0.58}, {x: 0.46, y: 0.46}, {x: 0.46, y: 0.38}, {x: 0.46, y: 0.35},
      {x: 0.51, y: 0.57}, {x: 0.51, y: 0.66}, {x: 0.51, y: 0.72}, {x: 0.51, y: 0.68},
      {x: 0.56, y: 0.58}, {x: 0.56, y: 0.67}, {x: 0.56, y: 0.73}, {x: 0.56, y: 0.69},
      {x: 0.61, y: 0.61}, {x: 0.61, y: 0.69}, {x: 0.61, y: 0.75}, {x: 0.61, y: 0.70}
    ],
    palm: [
      {x: 0.50, y: 0.85}, {x: 0.42, y: 0.78}, {x: 0.36, y: 0.70}, {x: 0.30, y: 0.62}, {x: 0.24, y: 0.55},
      {x: 0.44, y: 0.58}, {x: 0.43, y: 0.45}, {x: 0.42, y: 0.33}, {x: 0.41, y: 0.22},
      {x: 0.50, y: 0.56}, {x: 0.50, y: 0.42}, {x: 0.50, y: 0.30}, {x: 0.50, y: 0.18},
      {x: 0.56, y: 0.58}, {x: 0.57, y: 0.45}, {x: 0.58, y: 0.33}, {x: 0.59, y: 0.22},
      {x: 0.62, y: 0.61}, {x: 0.64, y: 0.50}, {x: 0.66, y: 0.40}, {x: 0.68, y: 0.30}
    ],
    peace: [
      {x: 0.50, y: 0.82}, {x: 0.44, y: 0.76}, {x: 0.38, y: 0.70}, {x: 0.32, y: 0.65}, {x: 0.40, y: 0.70},
      {x: 0.46, y: 0.58}, {x: 0.44, y: 0.46}, {x: 0.42, y: 0.34}, {x: 0.40, y: 0.22},
      {x: 0.51, y: 0.57}, {x: 0.53, y: 0.45}, {x: 0.55, y: 0.33}, {x: 0.57, y: 0.21},
      {x: 0.56, y: 0.58}, {x: 0.56, y: 0.67}, {x: 0.56, y: 0.73}, {x: 0.56, y: 0.69},
      {x: 0.61, y: 0.61}, {x: 0.61, y: 0.69}, {x: 0.61, y: 0.75}, {x: 0.61, y: 0.70}
    ],
    fist: [
      {x: 0.50, y: 0.80}, {x: 0.44, y: 0.75}, {x: 0.40, y: 0.70}, {x: 0.38, y: 0.66}, {x: 0.45, y: 0.64},
      {x: 0.46, y: 0.62}, {x: 0.46, y: 0.68}, {x: 0.46, y: 0.72}, {x: 0.46, y: 0.68},
      {x: 0.51, y: 0.61}, {x: 0.51, y: 0.68}, {x: 0.51, y: 0.72}, {x: 0.51, y: 0.68},
      {x: 0.56, y: 0.62}, {x: 0.56, y: 0.68}, {x: 0.56, y: 0.72}, {x: 0.56, y: 0.68},
      {x: 0.61, y: 0.64}, {x: 0.61, y: 0.70}, {x: 0.61, y: 0.74}, {x: 0.61, y: 0.70}
    ],
    swipe_up: [
      {x: 0.50, y: 0.65}, {x: 0.42, y: 0.58}, {x: 0.36, y: 0.50}, {x: 0.30, y: 0.42}, {x: 0.24, y: 0.35},
      {x: 0.44, y: 0.38}, {x: 0.43, y: 0.25}, {x: 0.42, y: 0.13}, {x: 0.41, y: 0.05},
      {x: 0.50, y: 0.36}, {x: 0.50, y: 0.22}, {x: 0.50, y: 0.10}, {x: 0.50, y: 0.02},
      {x: 0.56, y: 0.38}, {x: 0.57, y: 0.25}, {x: 0.58, y: 0.13}, {x: 0.59, y: 0.05},
      {x: 0.62, y: 0.41}, {x: 0.64, y: 0.30}, {x: 0.66, y: 0.20}, {x: 0.68, y: 0.10}
    ]
  };

  let currentJoints = JSON.parse(JSON.stringify(baseKeypoints.point));
  let targetJoints = JSON.parse(JSON.stringify(baseKeypoints.point));
  let mouseOffsetX = 0;
  let mouseOffsetY = 0;

  canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width - 0.5;
    const ny = (e.clientY - rect.top) / rect.height - 0.5;
    mouseOffsetX = nx * 0.15;
    mouseOffsetY = ny * 0.15;
  });

  canvas.addEventListener("mouseleave", () => {
    mouseOffsetX = 0;
    mouseOffsetY = 0;
  });

  simButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      simButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const posture = btn.dataset.posture;
      targetJoints = JSON.parse(JSON.stringify(baseKeypoints[posture] || baseKeypoints.point));

      const labels = {
        point: { name: "INDEX_POINT", action: "POINTER_MOVE", conf: 92 },
        pinch: { name: "PINCH", action: "TAP / CLICK", conf: 96 },
        palm: { name: "OPEN_PALM", action: "PAUSE_GESTURES", conf: 95 },
        peace: { name: "TWO_FINGERS", action: "MEDIA_PLAY_PAUSE", conf: 88 },
        fist: { name: "FIST", action: "EMERGENCY_STOP", conf: 94 },
        swipe_up: { name: "SWIPE_UP", action: "SCROLL_UP", conf: 89 }
      };

      const info = labels[posture] || labels.point;
      gestureHud.textContent = `GESTURE: ${info.name} -> ${info.action}`;
      confHud.textContent = `CONFIDENCE: ${info.conf}%`;

      const timeStr = new Date().toLocaleTimeString();
      const row = document.createElement("div");
      row.className = "log-row";
      row.innerHTML = `<span>[${timeStr}]</span> Dispatched: <strong>${info.action}</strong> (Debounce: OK)`;
      logEntries.prepend(row);
      if (logEntries.children.length > 8) logEntries.removeChild(logEntries.lastChild);
    });
  });

  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    for (let i = 0; i < currentJoints.length; i++) {
      currentJoints[i].x += (targetJoints[i].x + mouseOffsetX - currentJoints[i].x) * 0.15;
      currentJoints[i].y += (targetJoints[i].y + mouseOffsetY - currentJoints[i].y) * 0.15;
    }

    ctx.strokeStyle = "rgba(70, 240, 210, 0.85)";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";

    connections.forEach(([s, e]) => {
      const p1 = currentJoints[s];
      const p2 = currentJoints[e];
      ctx.beginPath();
      ctx.moveTo(p1.x * canvas.width, p1.y * canvas.height);
      ctx.lineTo(p2.x * canvas.width, p2.y * canvas.height);
      ctx.stroke();
    });

    currentJoints.forEach((j, idx) => {
      const cx = j.x * canvas.width;
      const cy = j.y * canvas.height;

      if (idx === 8) {
        ctx.fillStyle = "#46f0d2";
        ctx.beginPath(); ctx.arc(cx, cy, 7, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2; ctx.stroke();
      } else if (idx === 4) {
        ctx.fillStyle = "#fbe2b4";
        ctx.beginPath(); ctx.arc(cx, cy, 6, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.fillStyle = "#ffffff";
        ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill();
      }
    });

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}
