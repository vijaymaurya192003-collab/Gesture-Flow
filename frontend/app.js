/**
 * Gesture Flow — Unified Frontend Application Logic & Android Native Bridge
 * Integrates:
 * 1. Real-Time On-Device MediaPipe Hand Tracking (Camera feed & 21 3D Landmarks)
 * 2. Geometric Feature Extraction, Dynamic Gesture Classification & State Machine Debouncing
 * 3. Screen Coordinate Mapping with Mirroring & Exponential Moving Average Smoothing
 * 4. Capacitor Native Android Accessibility Bridge (dispatchTap, dispatchSwipe, dispatchPinchZoom, Global Actions)
 * 5. Dashboard Telemetry, Cloud Sync (MongoDB Atlas / FastAPI), and 21-Joint Simulator
 */

// =============================================================================
// 1. Global State & Mappings
// =============================================================================

let currentMappings = [
  { gesture: "INDEX_POINT", action: "POINTER_MOVE", sensitivity: 1.2, confidence_threshold: 0.70, cooldown_ms: 20, enabled: true, hardware: "Win32 / Android Pointer" },
  { gesture: "AIR_TAP", action: "TAP", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 400, enabled: true, hardware: "Android Screen Tap (Accessibility)" },
  { gesture: "PINCH", action: "TAP", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 400, enabled: true, hardware: "Hardware Tap Event" },
  { gesture: "PINCH_IN", action: "ZOOM_OUT", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 150, enabled: true, hardware: "Multi-Touch Pinch Out" },
  { gesture: "PINCH_OUT", action: "ZOOM_IN", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 150, enabled: true, hardware: "Multi-Touch Pinch In" },
  { gesture: "SWIPE_UP", action: "SCROLL_UP", sensitivity: 1.0, confidence_threshold: 0.70, cooldown_ms: 450, enabled: true, hardware: "Android Upward Swipe" },
  { gesture: "SWIPE_DOWN", action: "SCROLL_DOWN", sensitivity: 1.0, confidence_threshold: 0.70, cooldown_ms: 450, enabled: true, hardware: "Android Downward Swipe" },
  { gesture: "SWIPE_LEFT", action: "BACK", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 550, enabled: true, hardware: "Android Back / Swipe Left" },
  { gesture: "SWIPE_RIGHT", action: "HOME", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 550, enabled: true, hardware: "Android Home / Swipe Right" },
  { gesture: "OPEN_PALM", action: "PAUSE_GESTURES", sensitivity: 1.0, confidence_threshold: 0.80, cooldown_ms: 700, enabled: true, hardware: "Local Engine Neutral / Pause" },
  { gesture: "TWO_FINGERS", action: "MEDIA_PLAY_PAUSE", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 500, enabled: true, hardware: "Media Play/Pause Key" },
  { gesture: "THUMBS_UP", action: "CONFIRM", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 600, enabled: true, hardware: "Confirm Action" },
  { gesture: "THUMBS_DOWN", action: "REJECT", sensitivity: 1.0, confidence_threshold: 0.75, cooldown_ms: 600, enabled: true, hardware: "Reject Action" },
  { gesture: "FIST", action: "EMERGENCY_STOP", sensitivity: 1.0, confidence_threshold: 0.85, cooldown_ms: 800, enabled: true, hardware: "Safety Lockout" }
];

const SAFE_ACTIONS = [
  "POINTER_MOVE", "TAP", "SCROLL_UP", "SCROLL_DOWN", "ZOOM_IN", "ZOOM_OUT",
  "BACK", "HOME", "RECENTS", "NOTIFICATIONS", "VOLUME_UP", "VOLUME_DOWN",
  "MEDIA_PLAY_PAUSE", "CONFIRM", "REJECT", "PAUSE_GESTURES", "EMERGENCY_STOP"
];

// Calibration Thresholds
let calibrationConfig = {
  pinch_threshold: 0.45,
  hand_scale_baseline: 0.20,
  confidence_threshold: 0.70,
  jitter_deadband: 0.012,
  pointer_sensitivity: 1.2
};

// =============================================================================
// 2. Capacitor Native Android Bridge Controller
// =============================================================================

const NativeGestureBridge = {
  isCapacitor: typeof window.Capacitor !== "undefined",
  isAndroid: false,
  isAccessibilityServiceConnected: false,
  isAndroidControlEnabled: false,
  isEmergencyStopActive: false,
  physicalScreenWidth: window.screen ? window.screen.width * (window.devicePixelRatio || 1) : 1080,
  physicalScreenHeight: window.screen ? window.screen.height * (window.devicePixelRatio || 1) : 2400,
  screenDensity: window.devicePixelRatio || 2.0,
  statusPollTimer: null,

  init() {
    this.isAndroid = this.isCapacitor && window.Capacitor.getPlatform() === "android";
    console.log(`[NativeBridge] Initializing. Platform: ${this.isAndroid ? "Android (Native)" : "Web Browser"}`);

    this.updatePlatformUI();
    this.bindUIControls();

    if (this.isAndroid) {
      this.refreshScreenDimensions();
      this.checkAccessibilityService();
      this.statusPollTimer = setInterval(() => this.checkAccessibilityService(), 3000);
    } else {
      this.setAccessibilityUIStatus(false, "Web Browser (Simulator Mode)");
    }
  },

  getPlugin() {
    return (this.isCapacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.GestureAccessibility) || null;
  },

  async refreshScreenDimensions() {
    const plugin = this.getPlugin();
    if (plugin?.getScreenDimensions) {
      try {
        const dim = await plugin.getScreenDimensions();
        if (dim?.width && dim?.height) {
          this.physicalScreenWidth = dim.width;
          this.physicalScreenHeight = dim.height;
          this.screenDensity = dim.density || 2.0;
          const dimEl = document.getElementById("telScreenDim");
          if (dimEl) dimEl.textContent = `${this.physicalScreenWidth} x ${this.physicalScreenHeight} px`;
        }
      } catch (e) {
        console.warn("[NativeBridge] getScreenDimensions error:", e);
      }
    }
  },

  async checkAccessibilityService() {
    const plugin = this.getPlugin();
    if (plugin?.isServiceEnabled) {
      try {
        const res = await plugin.isServiceEnabled();
        this.isAccessibilityServiceConnected = !!(res && (res.enabled || res.running));
        this.setAccessibilityUIStatus(this.isAccessibilityServiceConnected);
      } catch (e) {
        this.isAccessibilityServiceConnected = false;
        this.setAccessibilityUIStatus(false);
      }
    } else {
      this.isAccessibilityServiceConnected = false;
      this.setAccessibilityUIStatus(false, "Web Browser (Simulator Mode)");
    }
  },

  async openAccessibilitySettings() {
    const plugin = this.getPlugin();
    if (plugin?.openAccessibilitySettings) {
      try {
        await plugin.openAccessibilitySettings();
        showToast("Opening Android Accessibility Settings...");
      } catch (e) {
        showToast("Failed to open accessibility settings: " + e.message, true);
      }
    } else {
      showToast("Accessibility settings are only available when running on Android.", true);
    }
  },

  async dispatchAction(actionCommand) {
    if (this.isEmergencyStopActive) {
      return { success: false, reason: "EMERGENCY_STOP_ACTIVE" };
    }

    const lastActionEl = document.getElementById("telLastNativeAction");
    if (lastActionEl) {
      lastActionEl.textContent = actionCommand.action || "NONE";
    }

    if (!this.isAndroid) {
      return { success: true, mode: "simulated" };
    }

    if (!this.isAndroidControlEnabled) {
      return { success: false, reason: "ANDROID_CONTROL_DISABLED" };
    }

    if (!this.isAccessibilityServiceConnected) {
      return { success: false, reason: "ACCESSIBILITY_SERVICE_NOT_CONNECTED" };
    }

    const plugin = this.getPlugin();
    if (plugin?.dispatchAction) {
      try {
        return await plugin.dispatchAction(actionCommand);
      } catch (err) {
        console.error("[NativeBridge] dispatchAction error:", err);
        return { success: false, error: err.message };
      }
    }

    return { success: false, reason: "PLUGIN_UNAVAILABLE" };
  },

  emergencyStop() {
    this.isEmergencyStopActive = true;
    this.isAndroidControlEnabled = false;

    const toggle = document.getElementById("toggleAndroidControl");
    if (toggle) toggle.checked = false;

    this.updateAndroidControlUI();

    const panel = document.getElementById("androidControlPanel");
    if (panel) panel.classList.remove("active-control");

    showToast("Safety Stop Triggered: All Android gesture actions HALTED.", true);

    const logEntries = document.getElementById("simLogEntries");
    if (logEntries) {
      const timeStr = new Date().toLocaleTimeString();
      const row = document.createElement("div");
      row.className = "log-row";
      row.innerHTML = `<span>[${timeStr}]</span> <strong style="color:#EF4444;">EMERGENCY SAFETY STOP ACTIVATED</strong> (Native actions disabled)`;
      logEntries.prepend(row);
    }
  },

  resumeFromEmergencyStop() {
    this.isEmergencyStopActive = false;
    showToast("Emergency safety lockout cleared.");
  },

  updatePlatformUI() {
    const platformEl = document.getElementById("telPlatformMode");
    if (platformEl) {
      platformEl.textContent = this.isAndroid ? "Capacitor Android (Native OS Control)" : "Web Browser (Simulator Mode)";
    }

    const dimEl = document.getElementById("telScreenDim");
    if (dimEl) {
      dimEl.textContent = `${this.physicalScreenWidth} x ${this.physicalScreenHeight} px`;
    }
  },

  setAccessibilityUIStatus(isEnabled, customText) {
    const pill = document.getElementById("statusPillAccessibility");
    const btnSettings = document.getElementById("btnOpenAccessibilitySettings");

    if (pill) {
      pill.innerHTML = isEnabled
        ? `<span class="dot green pulse"></span> ENABLED`
        : `<span class="dot amber"></span> ${customText || "DISABLED"}`;
    }

    if (btnSettings) {
      btnSettings.style.display = (this.isAndroid && !isEnabled) ? "inline-flex" : "none";
    }
  },

  updateAndroidControlUI() {
    const pill = document.getElementById("statusPillAndroidControl");
    const panel = document.getElementById("androidControlPanel");

    if (pill) {
      pill.innerHTML = this.isAndroidControlEnabled
        ? `<span class="dot green pulse"></span> ENABLED`
        : `<span class="dot red"></span> DISABLED`;
    }

    if (panel) {
      if (this.isAndroidControlEnabled) panel.classList.add("active-control");
      else panel.classList.remove("active-control");
    }
  },

  bindUIControls() {
    const toggleAndroid = document.getElementById("toggleAndroidControl");
    toggleAndroid?.addEventListener("change", (e) => {
      if (e.target.checked) {
        if (this.isEmergencyStopActive) this.resumeFromEmergencyStop();
        if (this.isAndroid && !this.isAccessibilityServiceConnected) {
          showToast("Please enable Gesture Flow Accessibility Service in Android Settings first!", true);
          this.openAccessibilitySettings();
        }
        this.isAndroidControlEnabled = true;
        showToast("Android System Control ENABLED: Front camera gestures will control device.");
      } else {
        this.isAndroidControlEnabled = false;
        showToast("Android System Control DISABLED.");
      }
      this.updateAndroidControlUI();
    });

    document.getElementById("btnOpenAccessibilitySettings")?.addEventListener("click", () => {
      this.openAccessibilitySettings();
    });

    document.getElementById("btnStopGestureControl")?.addEventListener("click", () => {
      this.emergencyStop();
    });
  }
};

// =============================================================================
// 3. Mathematical Coordinate Smoothing & Geometric Feature Extraction
// =============================================================================

function distance2D(p1, p2) {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function distance3D(p1, p2) {
  const dx = p1.x - p2.x;
  const dy = p1.y - p2.y;
  const dz = (p1.z || 0) - (p2.z || 0);
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

class ExponentialSmoother {
  constructor(alpha = 0.35) {
    this.alpha = alpha;
    this.smoothedX = null;
    this.smoothedY = null;
  }

  filter(x, y) {
    if (this.smoothedX === null || this.smoothedY === null) {
      this.smoothedX = x;
      this.smoothedY = y;
    } else {
      this.smoothedX = this.smoothedX + this.alpha * (x - this.smoothedX);
      this.smoothedY = this.smoothedY + this.alpha * (y - this.smoothedY);
    }
    return { x: this.smoothedX, y: this.smoothedY };
  }

  reset() {
    this.smoothedX = null;
    this.smoothedY = null;
  }
}

const cursorSmoother = new ExponentialSmoother(0.35);

function extractGeometricFeatures(landmarks, historyPalmCenters, prevPinchDist, prevIndexZ) {
  if (!landmarks || landmarks.length < 21) return null;

  const wrist = landmarks[0];
  const thumbTip = landmarks[4];
  const thumbIp = landmarks[3];
  const thumbMcp = landmarks[2];

  const indexTip = landmarks[8];
  const indexPip = landmarks[6];
  const indexMcp = landmarks[5];

  const middleTip = landmarks[12];
  const middlePip = landmarks[10];
  const middleMcp = landmarks[9];

  const ringTip = landmarks[16];
  const ringPip = landmarks[14];
  const ringMcp = landmarks[13];

  const pinkyTip = landmarks[20];
  const pinkyPip = landmarks[18];
  const pinkyMcp = landmarks[17];

  // 1. Hand scale reference
  const handScale = Math.max(0.05, distance2D(wrist, middleMcp));

  // 2. Finger extension detection
  const indexExtended = distance2D(wrist, indexTip) > distance2D(wrist, indexPip) * 1.05;
  const middleExtended = distance2D(wrist, middleTip) > distance2D(wrist, middlePip) * 1.08;
  const ringExtended = distance2D(wrist, ringTip) > distance2D(wrist, ringPip) * 1.08;
  const pinkyExtended = distance2D(wrist, pinkyTip) > distance2D(wrist, pinkyPip) * 1.08;
  const thumbExtended = distance2D(pinkyMcp, thumbTip) > distance2D(pinkyMcp, thumbIp) * 1.15;

  let extendedCount = (indexExtended ? 1 : 0) + (middleExtended ? 1 : 0) + (ringExtended ? 1 : 0) + (pinkyExtended ? 1 : 0);
  if (thumbExtended) extendedCount++;

  // 3. Pinch metrics
  const rawPinchDist = distance3D(thumbTip, indexTip);
  const pinchDistNorm = rawPinchDist / handScale;
  let pinchDelta = 0.0;
  if (prevPinchDist !== null && prevPinchDist !== undefined) {
    pinchDelta = pinchDistNorm - prevPinchDist;
  }

  // 4. Palm Center & Velocity
  const palmX = (wrist.x + indexMcp.x + middleMcp.x + pinkyMcp.x) / 4.0;
  const palmY = (wrist.y + indexMcp.y + middleMcp.y + pinkyMcp.y) / 4.0;
  const palmCenter = { x: palmX, y: palmY };

  let vx = 0.0;
  let vy = 0.0;
  if (historyPalmCenters && historyPalmCenters.length >= 1) {
    const oldest = historyPalmCenters[0];
    const n = historyPalmCenters.length;
    vx = (palmCenter.x - oldest.x) / Math.max(1, n);
    vy = (palmCenter.y - oldest.y) / Math.max(1, n);
  }

  // 5. Thumbs Up / Down
  const otherFingersCurled = !indexExtended && !middleExtended && !ringExtended && !pinkyExtended;
  let isThumbsUp = false;
  let isThumbsDown = false;

  if (thumbExtended && otherFingersCurled) {
    if (thumbTip.y < thumbIp.y && thumbIp.y < thumbMcp.y && thumbMcp.y < wrist.y) {
      const dx = Math.abs(thumbTip.x - thumbMcp.x);
      const dy = Math.abs(thumbTip.y - thumbMcp.y);
      if (dy > dx * 0.8) isThumbsUp = true;
    } else if (thumbTip.y > thumbIp.y && thumbIp.y > thumbMcp.y && thumbMcp.y > wrist.y) {
      const dx = Math.abs(thumbTip.x - thumbMcp.x);
      const dy = Math.abs(thumbTip.y - thumbMcp.y);
      if (dy > dx * 0.8) isThumbsDown = true;
    }
  }

  // 6. Air Tap detection (forward Z-depth pulse)
  let isAirTap = false;
  let indexZVelocity = 0.0;
  if (prevIndexZ !== null && prevIndexZ !== undefined && indexTip.z !== undefined) {
    indexZVelocity = indexTip.z - prevIndexZ;
    if (indexExtended && !middleExtended && !ringExtended && !pinkyExtended) {
      if (indexZVelocity < -0.025) isAirTap = true;
    }
  }

  // 7. Fist & Open Palm
  const isFist = extendedCount <= 1 && !indexExtended && !middleExtended && !ringExtended && !pinkyExtended;
  const isOpenPalm = extendedCount >= 4;

  return {
    handScale,
    indexExtended,
    middleExtended,
    ringExtended,
    pinkyExtended,
    thumbExtended,
    extendedCount,
    pinchDistNorm,
    pinchDelta,
    palmCenter,
    velocity: { x: vx, y: vy },
    isThumbsUp,
    isThumbsDown,
    isAirTap,
    indexZVelocity,
    isFist,
    isOpenPalm,
    indexTipPos: { x: indexTip.x, y: indexTip.y, z: indexTip.z }
  };
}

// =============================================================================
// 4. Deterministic Gesture Classifier & State Machine
// =============================================================================

class FrontendGestureClassifier {
  constructor() {
    this.palmHistory = [];
    this.prevPinchDist = null;
    this.prevIndexZ = null;
    this.lastActionTime = 0;
    this.gestureStartTime = 0;
    this.activeHoldGesture = "NONE";
    this.swipeVelocityThreshold = 0.040;
  }

  classify(landmarks) {
    if (!landmarks || landmarks.length < 21) {
      this.reset();
      return { gesture: "NONE", confidence: 0.0, features: null };
    }

    const features = extractGeometricFeatures(landmarks, this.palmHistory, this.prevPinchDist, this.prevIndexZ);
    if (!features) return { gesture: "NONE", confidence: 0.0, features: null };

    this.palmHistory.push(features.palmCenter);
    if (this.palmHistory.length > 5) this.palmHistory.shift();
    this.prevPinchDist = features.pinchDistNorm;
    this.prevIndexZ = features.indexTipPos.z;

    let detectedGesture = "NONE";
    let confidence = 0.85;

    // PRIORITY 1: FIST (Safety Stop / Emergency Lockout)
    if (features.isFist) {
      detectedGesture = "FIST";
      confidence = 0.95;
    }
    // PRIORITY 2: OPEN PALM (Neutral / Pause)
    else if (features.isOpenPalm) {
      detectedGesture = "OPEN_PALM";
      confidence = 0.92;
    }
    // PRIORITY 3: PINCH (Pinch Zoom & Tap)
    else if (features.pinchDistNorm < calibrationConfig.pinch_threshold) {
      if (Math.abs(features.pinchDelta) > 0.015) {
        detectedGesture = features.pinchDelta > 0 ? "PINCH_OUT" : "PINCH_IN";
        confidence = 0.90;
      } else {
        detectedGesture = "PINCH";
        confidence = 0.94;
      }
    }
    // PRIORITY 4: AIR TAP (Z-Axis Forward Motion)
    else if (features.isAirTap) {
      detectedGesture = "AIR_TAP";
      confidence = 0.92;
    }
    // PRIORITY 5: SWIPES (Directional Velocity Vectors)
    else if (Math.sqrt(features.velocity.x * features.velocity.x + features.velocity.y * features.velocity.y) > this.swipeVelocityThreshold) {
      const vx = features.velocity.x;
      const vy = features.velocity.y;
      if (Math.abs(vx) > Math.abs(vy)) {
        detectedGesture = vx > 0 ? "SWIPE_RIGHT" : "SWIPE_LEFT";
      } else {
        detectedGesture = vy > 0 ? "SWIPE_DOWN" : "SWIPE_UP";
      }
      confidence = 0.88;
    }
    // PRIORITY 6: INDEX POINT (Pointer Movement)
    else if (features.indexExtended && !features.middleExtended && !features.ringExtended && !features.pinkyExtended) {
      detectedGesture = "INDEX_POINT";
      confidence = 0.95;
    }
    // PRIORITY 7: THUMBS & PEACE
    else if (features.isThumbsUp) {
      detectedGesture = "THUMBS_UP";
      confidence = 0.92;
    } else if (features.isThumbsDown) {
      detectedGesture = "THUMBS_DOWN";
      confidence = 0.92;
    } else if (features.indexExtended && features.middleExtended && !features.ringExtended && !features.pinkyExtended) {
      detectedGesture = "TWO_FINGERS";
      confidence = 0.90;
    }

    return { gesture: detectedGesture, confidence, features };
  }

  processState(detectedGesture, confidence, features) {
    const now = Date.now();

    if (detectedGesture === "NONE" || confidence < calibrationConfig.confidence_threshold) {
      this.activeHoldGesture = "NONE";
      return { actionToDispatch: null, isContinuous: false };
    }

    const cooldownMap = {
      INDEX_POINT: 15,
      AIR_TAP: 400,
      PINCH: 400,
      PINCH_IN: 150,
      PINCH_OUT: 150,
      SWIPE_UP: 500,
      SWIPE_DOWN: 500,
      SWIPE_LEFT: 500,
      SWIPE_RIGHT: 500,
      OPEN_PALM: 700,
      FIST: 800,
      THUMBS_UP: 600,
      THUMBS_DOWN: 600,
      TWO_FINGERS: 500
    };

    const cooldown = cooldownMap[detectedGesture] || 400;
    const timeSinceLastAction = now - this.lastActionTime;

    if (detectedGesture === "INDEX_POINT") {
      this.lastActionTime = now;
      return { actionToDispatch: { action: "POINTER_MOVE" }, isContinuous: true };
    }

    if (detectedGesture === "PINCH_IN" || detectedGesture === "PINCH_OUT") {
      if (timeSinceLastAction >= cooldown) {
        this.lastActionTime = now;
        return {
          actionToDispatch: {
            action: detectedGesture === "PINCH_OUT" ? "PINCH_OUT" : "PINCH_IN",
            centerX: NativeGestureBridge.physicalScreenWidth * 0.5,
            centerY: NativeGestureBridge.physicalScreenHeight * 0.5,
            distance: 220,
            duration: 250
          },
          isContinuous: true
        };
      }
      return { actionToDispatch: null, isContinuous: true };
    }

    if (timeSinceLastAction < cooldown) {
      return { actionToDispatch: null, isContinuous: false };
    }

    if (detectedGesture === "PINCH") {
      if (this.activeHoldGesture !== "PINCH") {
        this.activeHoldGesture = "PINCH";
        this.gestureStartTime = now;
        return { actionToDispatch: null, isContinuous: false };
      }
      if (now - this.gestureStartTime < 70) {
        return { actionToDispatch: null, isContinuous: false };
      }
    }

    this.lastActionTime = now;
    this.activeHoldGesture = "NONE";

    return {
      actionToDispatch: this.mapGestureToAction(detectedGesture, features),
      isContinuous: false
    };
  }

  mapGestureToAction(gesture, features) {
    const screenW = NativeGestureBridge.physicalScreenWidth;
    const screenH = NativeGestureBridge.physicalScreenHeight;

    switch (gesture) {
      case "AIR_TAP":
      case "PINCH":
        return { action: "TAP", x: latestSmoothedPhysicalCoords.x, y: latestSmoothedPhysicalCoords.y };
      case "SWIPE_LEFT":
        return { action: "SWIPE", startX: screenW * 0.8, startY: screenH * 0.5, endX: screenW * 0.2, endY: screenH * 0.5, duration: 300 };
      case "SWIPE_RIGHT":
        return { action: "SWIPE", startX: screenW * 0.2, startY: screenH * 0.5, endX: screenW * 0.8, endY: screenH * 0.5, duration: 300 };
      case "SWIPE_UP":
        return { action: "SWIPE", startX: screenW * 0.5, startY: screenH * 0.7, endX: screenW * 0.5, endY: screenH * 0.3, duration: 300 };
      case "SWIPE_DOWN":
        return { action: "SWIPE", startX: screenW * 0.5, startY: screenH * 0.3, endX: screenW * 0.5, endY: screenH * 0.7, duration: 300 };
      case "FIST":
        return { action: "EMERGENCY_STOP" };
      case "OPEN_PALM":
        return { action: "PAUSE_GESTURES" };
      case "THUMBS_UP":
        return { action: "CONFIRM" };
      case "THUMBS_DOWN":
        return { action: "REJECT" };
      case "TWO_FINGERS":
        return { action: "MEDIA_PLAY_PAUSE" };
      default:
        return { action: "NONE" };
    }
  }

  reset() {
    this.palmHistory = [];
    this.prevPinchDist = null;
    this.prevIndexZ = null;
    this.activeHoldGesture = "NONE";
  }
}

const classifier = new FrontendGestureClassifier();
let latestSmoothedPhysicalCoords = { x: 540, y: 1200 };

// =============================================================================
// 5. DOM Initialization & Navigation Lifecycle
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  NativeGestureBridge.init();
  initViewRouter();
  initLandingEvents();
  initAuthModal();
  initDashboardTabs();
  initRangeSliders();
  initForms();
  initTiltCards();
  initCanvasSimulator();

  checkBackendHealth();
  if (api.isAuthenticated()) {
    showDashboardView();
  } else {
    showLandingView();
  }
});

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

window.onAuthExpired = () => {
  showToast("Session expired. Please sign in again.", true);
  showLandingView();
  openAuthModal();
};

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

function initLandingEvents() {
  document.getElementById("btnLandingSignIn")?.addEventListener("click", () => openAuthModal(false));
  document.getElementById("btnLandingGetStarted")?.addEventListener("click", () => {
    if (api.isAuthenticated()) showDashboardView();
    else openAuthModal(true);
  });
  document.getElementById("btnHeroGetStarted")?.addEventListener("click", () => {
    if (api.isAuthenticated()) showDashboardView();
    else openAuthModal(true);
  });
  document.getElementById("btnHeroDemo")?.addEventListener("click", () => {
    showDashboardView();
    const simTab = document.querySelector('.nav-item[data-tab="simulator"]');
    if (simTab) simTab.click();
  });
  document.getElementById("btnBottomCta")?.addEventListener("click", () => {
    if (api.isAuthenticated()) showDashboardView();
    else openAuthModal(true);
  });
}

function initDashboardTabs() {
  const navButtons = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const pageTitle = document.getElementById("pageTitle");
  const pageSubtitle = document.getElementById("pageSubtitle");
  const currentCrumb = document.getElementById("currentCrumb");

  const titles = {
    overview: { crumb: "Dashboard", title: "Touchless HCI System Overview", sub: "Real-time computer vision telemetry, local MediaPipe hand landmark pipeline & safe Android Accessibility actions" },
    simulator: { crumb: "Interactive CV", title: "Live Hand Tracking & Android Control", sub: "Real-time on-device MediaPipe vision pipeline, front-camera coordinate mapping & Android Accessibility actions" },
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
// 6. Backend & MongoDB Atlas Data Sync
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
    if (gestures?.length > 0) {
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
        calibrationConfig = { ...calibrationConfig, ...calib };
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

function renderOverviewTable() {
  const tbody = document.getElementById("overviewGesturesTable");
  if (!tbody) return;

  tbody.innerHTML = currentMappings.map(m => `
    <tr>
      <td><strong class="table-gesture-name">${m.gesture}</strong></td>
      <td><span class="action-pill">${m.action}</span></td>
      <td><span class="table-cooldown">${m.cooldown_ms} ms</span></td>
      <td><span class="table-conf">${Math.round(m.confidence_threshold * 100)}%</span></td>
      <td><code class="table-target">${m.hardware || 'AccessibilityService'}</code></td>
      <td><span class="badge badge-green">Ready</span></td>
    </tr>
  `).join("");
}

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

    calibrationConfig.pinch_threshold = parseFloat(document.getElementById("calibPinch").value);
    calibrationConfig.hand_scale_baseline = parseFloat(document.getElementById("calibHandScale").value);
    calibrationConfig.confidence_threshold = parseFloat(document.getElementById("calibConfidence").value);
    calibrationConfig.jitter_deadband = parseFloat(document.getElementById("calibJitter").value);

    try {
      await api.updateCalibration(calibrationConfig);
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
    groupName.style.display = "block";
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
// 7. Interactive Canvas Hand Tracker & Real-Time MediaPipe Pipeline
// =============================================================================

function initCanvasSimulator() {
  const canvas = document.getElementById("handSimulatorCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const gestureHud = document.getElementById("simGestureHud");
  const confHud = document.getElementById("simConfHud");
  const logEntries = document.getElementById("simLogEntries");
  const simButtons = document.querySelectorAll(".btn-gesture-sim");

  const toggleGesture = document.getElementById("toggleGestureControl");
  const toggleCursor = document.getElementById("toggleVirtualCursor");
  const selectSens = document.getElementById("selectTouchpadSens");
  const labelGesture = document.getElementById("labelGestureCtrl");
  const labelCursor = document.getElementById("labelVirtualCursor");
  const statusPillGestures = document.getElementById("statusPillGestures");
  const statusPillCursor = document.getElementById("statusPillCursor");
  const statusPillCamera = document.getElementById("statusPillCamera");
  const telScreenCoords = document.getElementById("telScreenCoords");

  let gestureControlEnabled = true;
  let virtualCursorEnabled = true;
  let touchpadSensitivity = 1.25;

  toggleGesture?.addEventListener("change", (e) => {
    gestureControlEnabled = e.target.checked;
    if (labelGesture) {
      labelGesture.textContent = gestureControlEnabled ? "ON" : "OFF";
      labelGesture.className = gestureControlEnabled ? "text-accent" : "text-danger";
    }
    if (statusPillGestures) {
      statusPillGestures.innerHTML = gestureControlEnabled
        ? `<span class="dot green"></span> ON`
        : `<span class="dot red"></span> OFF`;
    }
  });

  toggleCursor?.addEventListener("change", (e) => {
    virtualCursorEnabled = e.target.checked;
    if (labelCursor) {
      labelCursor.textContent = virtualCursorEnabled ? "ON" : "OFF";
      labelCursor.className = virtualCursorEnabled ? "text-accent" : "text-danger";
    }
    if (statusPillCursor) {
      statusPillCursor.innerHTML = virtualCursorEnabled
        ? `<span class="dot green"></span> ON`
        : `<span class="dot red"></span> OFF`;
    }
  });

  selectSens?.addEventListener("change", (e) => {
    const val = e.target.value;
    touchpadSensitivity = val === "LOW" ? 0.75 : (val === "HIGH" ? 2.0 : 1.25);
    showToast(`Touchpad sensitivity set to ${val} (${touchpadSensitivity}x)`);
  });

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
      {x: 0.50, y: 0.82, z: 0}, {x: 0.44, y: 0.76, z: 0}, {x: 0.38, y: 0.70, z: 0}, {x: 0.32, y: 0.65, z: 0}, {x: 0.40, y: 0.70, z: 0},
      {x: 0.46, y: 0.58, z: 0}, {x: 0.46, y: 0.46, z: 0}, {x: 0.46, y: 0.34, z: 0}, {x: 0.46, y: 0.22, z: 0},
      {x: 0.51, y: 0.57, z: 0}, {x: 0.51, y: 0.66, z: 0}, {x: 0.51, y: 0.72, z: 0}, {x: 0.51, y: 0.68, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.56, y: 0.67, z: 0}, {x: 0.56, y: 0.73, z: 0}, {x: 0.56, y: 0.69, z: 0},
      {x: 0.61, y: 0.61, z: 0}, {x: 0.61, y: 0.69, z: 0}, {x: 0.61, y: 0.75, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    air_tap: [
      {x: 0.50, y: 0.82, z: 0}, {x: 0.44, y: 0.76, z: 0}, {x: 0.38, y: 0.70, z: 0}, {x: 0.32, y: 0.65, z: 0}, {x: 0.40, y: 0.70, z: 0},
      {x: 0.46, y: 0.58, z: 0}, {x: 0.46, y: 0.46, z: 0}, {x: 0.46, y: 0.32, z: -0.04}, {x: 0.46, y: 0.18, z: -0.06},
      {x: 0.51, y: 0.57, z: 0}, {x: 0.51, y: 0.66, z: 0}, {x: 0.51, y: 0.72, z: 0}, {x: 0.51, y: 0.68, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.56, y: 0.67, z: 0}, {x: 0.56, y: 0.73, z: 0}, {x: 0.56, y: 0.69, z: 0},
      {x: 0.61, y: 0.61, z: 0}, {x: 0.61, y: 0.69, z: 0}, {x: 0.61, y: 0.75, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    pinch: [
      {x: 0.50, y: 0.82, z: 0}, {x: 0.44, y: 0.76, z: 0}, {x: 0.40, y: 0.68, z: 0}, {x: 0.42, y: 0.50, z: 0}, {x: 0.45, y: 0.36, z: 0},
      {x: 0.46, y: 0.58, z: 0}, {x: 0.46, y: 0.46, z: 0}, {x: 0.46, y: 0.38, z: 0}, {x: 0.46, y: 0.35, z: 0},
      {x: 0.51, y: 0.57, z: 0}, {x: 0.51, y: 0.66, z: 0}, {x: 0.51, y: 0.72, z: 0}, {x: 0.51, y: 0.68, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.56, y: 0.67, z: 0}, {x: 0.56, y: 0.73, z: 0}, {x: 0.56, y: 0.69, z: 0},
      {x: 0.61, y: 0.61, z: 0}, {x: 0.61, y: 0.69, z: 0}, {x: 0.61, y: 0.75, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    pinch_in: [
      {x: 0.50, y: 0.82, z: 0}, {x: 0.44, y: 0.76, z: 0}, {x: 0.40, y: 0.68, z: 0}, {x: 0.44, y: 0.48, z: 0}, {x: 0.45, y: 0.36, z: 0},
      {x: 0.46, y: 0.58, z: 0}, {x: 0.46, y: 0.46, z: 0}, {x: 0.46, y: 0.38, z: 0}, {x: 0.45, y: 0.36, z: 0},
      {x: 0.51, y: 0.57, z: 0}, {x: 0.51, y: 0.66, z: 0}, {x: 0.51, y: 0.72, z: 0}, {x: 0.51, y: 0.68, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.56, y: 0.67, z: 0}, {x: 0.56, y: 0.73, z: 0}, {x: 0.56, y: 0.69, z: 0},
      {x: 0.61, y: 0.61, z: 0}, {x: 0.61, y: 0.69, z: 0}, {x: 0.61, y: 0.75, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    pinch_out: [
      {x: 0.50, y: 0.82, z: 0}, {x: 0.44, y: 0.76, z: 0}, {x: 0.38, y: 0.68, z: 0}, {x: 0.34, y: 0.52, z: 0}, {x: 0.32, y: 0.40, z: 0},
      {x: 0.46, y: 0.58, z: 0}, {x: 0.46, y: 0.46, z: 0}, {x: 0.48, y: 0.34, z: 0}, {x: 0.50, y: 0.22, z: 0},
      {x: 0.51, y: 0.57, z: 0}, {x: 0.51, y: 0.66, z: 0}, {x: 0.51, y: 0.72, z: 0}, {x: 0.51, y: 0.68, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.56, y: 0.67, z: 0}, {x: 0.56, y: 0.73, z: 0}, {x: 0.56, y: 0.69, z: 0},
      {x: 0.61, y: 0.61, z: 0}, {x: 0.61, y: 0.69, z: 0}, {x: 0.61, y: 0.75, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    touchpad: [
      {x: 0.50, y: 0.82, z: 0}, {x: 0.44, y: 0.76, z: 0}, {x: 0.38, y: 0.70, z: 0}, {x: 0.32, y: 0.65, z: 0}, {x: 0.40, y: 0.70, z: 0},
      {x: 0.46, y: 0.58, z: 0}, {x: 0.46, y: 0.46, z: 0}, {x: 0.46, y: 0.34, z: 0}, {x: 0.46, y: 0.22, z: 0},
      {x: 0.51, y: 0.57, z: 0}, {x: 0.50, y: 0.45, z: 0}, {x: 0.49, y: 0.33, z: 0}, {x: 0.49, y: 0.21, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.56, y: 0.67, z: 0}, {x: 0.56, y: 0.73, z: 0}, {x: 0.56, y: 0.69, z: 0},
      {x: 0.61, y: 0.61, z: 0}, {x: 0.61, y: 0.69, z: 0}, {x: 0.61, y: 0.75, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    touchpad_scroll: [
      {x: 0.50, y: 0.70, z: 0}, {x: 0.44, y: 0.64, z: 0}, {x: 0.38, y: 0.58, z: 0}, {x: 0.32, y: 0.53, z: 0}, {x: 0.40, y: 0.58, z: 0},
      {x: 0.46, y: 0.46, z: 0}, {x: 0.46, y: 0.34, z: 0}, {x: 0.46, y: 0.22, z: 0}, {x: 0.46, y: 0.10, z: 0},
      {x: 0.51, y: 0.45, z: 0}, {x: 0.50, y: 0.33, z: 0}, {x: 0.49, y: 0.21, z: 0}, {x: 0.49, y: 0.09, z: 0},
      {x: 0.56, y: 0.46, z: 0}, {x: 0.56, y: 0.55, z: 0}, {x: 0.56, y: 0.61, z: 0}, {x: 0.56, y: 0.57, z: 0},
      {x: 0.61, y: 0.49, z: 0}, {x: 0.61, y: 0.57, z: 0}, {x: 0.61, y: 0.63, z: 0}, {x: 0.61, y: 0.58, z: 0}
    ],
    thumbs_up: [
      {x: 0.50, y: 0.80, z: 0}, {x: 0.46, y: 0.70, z: 0}, {x: 0.44, y: 0.55, z: 0}, {x: 0.44, y: 0.40, z: 0}, {x: 0.44, y: 0.25, z: 0},
      {x: 0.48, y: 0.65, z: 0}, {x: 0.48, y: 0.70, z: 0}, {x: 0.48, y: 0.74, z: 0}, {x: 0.48, y: 0.70, z: 0},
      {x: 0.52, y: 0.64, z: 0}, {x: 0.52, y: 0.70, z: 0}, {x: 0.52, y: 0.74, z: 0}, {x: 0.52, y: 0.70, z: 0},
      {x: 0.56, y: 0.65, z: 0}, {x: 0.56, y: 0.71, z: 0}, {x: 0.56, y: 0.75, z: 0}, {x: 0.56, y: 0.71, z: 0},
      {x: 0.60, y: 0.66, z: 0}, {x: 0.60, y: 0.72, z: 0}, {x: 0.60, y: 0.76, z: 0}, {x: 0.60, y: 0.72, z: 0}
    ],
    thumbs_down: [
      {x: 0.50, y: 0.35, z: 0}, {x: 0.46, y: 0.45, z: 0}, {x: 0.44, y: 0.60, z: 0}, {x: 0.44, y: 0.75, z: 0}, {x: 0.44, y: 0.90, z: 0},
      {x: 0.48, y: 0.45, z: 0}, {x: 0.48, y: 0.40, z: 0}, {x: 0.48, y: 0.36, z: 0}, {x: 0.48, y: 0.40, z: 0},
      {x: 0.52, y: 0.46, z: 0}, {x: 0.52, y: 0.40, z: 0}, {x: 0.52, y: 0.36, z: 0}, {x: 0.52, y: 0.40, z: 0},
      {x: 0.56, y: 0.45, z: 0}, {x: 0.56, y: 0.39, z: 0}, {x: 0.56, y: 0.35, z: 0}, {x: 0.56, y: 0.39, z: 0},
      {x: 0.60, y: 0.44, z: 0}, {x: 0.60, y: 0.38, z: 0}, {x: 0.60, y: 0.34, z: 0}, {x: 0.60, y: 0.38, z: 0}
    ],
    palm: [
      {x: 0.50, y: 0.85, z: 0}, {x: 0.42, y: 0.78, z: 0}, {x: 0.36, y: 0.70, z: 0}, {x: 0.30, y: 0.62, z: 0}, {x: 0.24, y: 0.55, z: 0},
      {x: 0.44, y: 0.58, z: 0}, {x: 0.43, y: 0.45, z: 0}, {x: 0.42, y: 0.33, z: 0}, {x: 0.41, y: 0.22, z: 0},
      {x: 0.50, y: 0.56, z: 0}, {x: 0.50, y: 0.42, z: 0}, {x: 0.50, y: 0.30, z: 0}, {x: 0.50, y: 0.18, z: 0},
      {x: 0.56, y: 0.58, z: 0}, {x: 0.57, y: 0.45, z: 0}, {x: 0.58, y: 0.33, z: 0}, {x: 0.59, y: 0.22, z: 0},
      {x: 0.62, y: 0.61, z: 0}, {x: 0.64, y: 0.50, z: 0}, {x: 0.66, y: 0.40, z: 0}, {x: 0.68, y: 0.30, z: 0}
    ],
    fist: [
      {x: 0.50, y: 0.80, z: 0}, {x: 0.44, y: 0.75, z: 0}, {x: 0.40, y: 0.70, z: 0}, {x: 0.38, y: 0.66, z: 0}, {x: 0.45, y: 0.64, z: 0},
      {x: 0.46, y: 0.62, z: 0}, {x: 0.46, y: 0.68, z: 0}, {x: 0.46, y: 0.72, z: 0}, {x: 0.46, y: 0.68, z: 0},
      {x: 0.51, y: 0.61, z: 0}, {x: 0.51, y: 0.68, z: 0}, {x: 0.51, y: 0.72, z: 0}, {x: 0.51, y: 0.68, z: 0},
      {x: 0.56, y: 0.62, z: 0}, {x: 0.56, y: 0.68, z: 0}, {x: 0.56, y: 0.72, z: 0}, {x: 0.56, y: 0.68, z: 0},
      {x: 0.61, y: 0.64, z: 0}, {x: 0.61, y: 0.70, z: 0}, {x: 0.61, y: 0.74, z: 0}, {x: 0.61, y: 0.70, z: 0}
    ],
    swipe_up: [
      {x: 0.50, y: 0.65, z: 0}, {x: 0.42, y: 0.58, z: 0}, {x: 0.36, y: 0.50, z: 0}, {x: 0.30, y: 0.42, z: 0}, {x: 0.24, y: 0.35, z: 0},
      {x: 0.44, y: 0.38, z: 0}, {x: 0.43, y: 0.25, z: 0}, {x: 0.42, y: 0.13, z: 0}, {x: 0.41, y: 0.05, z: 0},
      {x: 0.50, y: 0.36, z: 0}, {x: 0.50, y: 0.22, z: 0}, {x: 0.50, y: 0.10, z: 0}, {x: 0.50, y: 0.02, z: 0},
      {x: 0.56, y: 0.38, z: 0}, {x: 0.57, y: 0.25, z: 0}, {x: 0.58, y: 0.13, z: 0}, {x: 0.59, y: 0.05, z: 0},
      {x: 0.62, y: 0.41, z: 0}, {x: 0.64, y: 0.30, z: 0}, {x: 0.66, y: 0.20, z: 0}, {x: 0.68, y: 0.10, z: 0}
    ]
  };

  let currentJoints = JSON.parse(JSON.stringify(baseKeypoints.point));
  let targetJoints = JSON.parse(JSON.stringify(baseKeypoints.point));
  let isLiveVisionActive = false;
  let liveLandmarks = null;
  let mouseOffsetX = 0;
  let mouseOffsetY = 0;

  canvas.addEventListener("mousemove", (e) => {
    if (isLiveVisionActive) return;
    const rect = canvas.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width - 0.5;
    const ny = (e.clientY - rect.top) / rect.height - 0.5;
    mouseOffsetX = nx * 0.15 * touchpadSensitivity;
    mouseOffsetY = ny * 0.15 * touchpadSensitivity;
  });

  canvas.addEventListener("mouseleave", () => {
    mouseOffsetX = 0;
    mouseOffsetY = 0;
  });

  // Manual Simulation Button Clicks
  simButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      simButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const posture = btn.dataset.posture;
      targetJoints = JSON.parse(JSON.stringify(baseKeypoints[posture] || baseKeypoints.point));

      const { gesture, confidence, features } = classifier.classify(targetJoints);
      const { actionToDispatch } = classifier.processState(gesture, confidence, features);

      gestureHud.textContent = `GESTURE: ${gesture} -> ${actionToDispatch ? actionToDispatch.action : 'NONE'}`;
      confHud.textContent = `CONFIDENCE: ${Math.round(confidence * 100)}%`;

      if (actionToDispatch && actionToDispatch.action !== "NONE") {
        if (actionToDispatch.action === "EMERGENCY_STOP") {
          NativeGestureBridge.emergencyStop();
        } else {
          NativeGestureBridge.dispatchAction(actionToDispatch);
        }

        const timeStr = new Date().toLocaleTimeString();
        const row = document.createElement("div");
        row.className = "log-row";
        row.innerHTML = `<span>[${timeStr}]</span> Dispatched: <strong>${actionToDispatch.action}</strong> (Simulator)`;
        logEntries.prepend(row);
        if (logEntries.children.length > 8) logEntries.removeChild(logEntries.lastChild);
      }
    });
  });

  // ===========================================================================
  // Live Camera & MediaPipe Hands Pipeline
  // ===========================================================================

  let webcamStream = null;
  let mediaPipeHands = null;
  let cameraUtilsInstance = null;
  const btnToggleWebcam = document.getElementById("btnToggleWebcam");
  const labelWebcamBtn = document.getElementById("labelWebcamBtn");
  const video = document.getElementById("liveWebcamFeed");

  async function initMediaPipe() {
    if (typeof window.Hands === "undefined") return false;

    if (!mediaPipeHands) {
      mediaPipeHands = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
      });

      mediaPipeHands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.65,
        minTrackingConfidence: 0.60
      });

      mediaPipeHands.onResults(onMediaPipeResults);
    }
    return true;
  }

  function onMediaPipeResults(results) {
    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
      liveLandmarks = results.multiHandLandmarks[0];
      isLiveVisionActive = true;

      const { gesture, confidence, features } = classifier.classify(liveLandmarks);

      if (features?.indexTipPos) {
        const mirroredNormX = 1.0 - features.indexTipPos.x;
        const normY = features.indexTipPos.y;
        const screenW = NativeGestureBridge.physicalScreenWidth;
        const screenH = NativeGestureBridge.physicalScreenHeight;
        const rawPhysX = mirroredNormX * screenW;
        const rawPhysY = normY * screenH;

        latestSmoothedPhysicalCoords = cursorSmoother.filter(rawPhysX, rawPhysY);

        if (telScreenCoords) {
          telScreenCoords.textContent = `(X: ${Math.round(latestSmoothedPhysicalCoords.x)}, Y: ${Math.round(latestSmoothedPhysicalCoords.y)})`;
        }
      }

      const { actionToDispatch, isContinuous } = classifier.processState(gesture, confidence, features);

      gestureHud.textContent = `GESTURE: ${gesture} -> ${actionToDispatch ? actionToDispatch.action : 'TRACKING'}`;
      confHud.textContent = `CONFIDENCE: ${Math.round(confidence * 100)}%`;

      if (gestureControlEnabled && actionToDispatch && actionToDispatch.action !== "NONE") {
        if (actionToDispatch.action === "EMERGENCY_STOP") {
          NativeGestureBridge.emergencyStop();
        } else {
          NativeGestureBridge.dispatchAction(actionToDispatch);
        }

        if (!isContinuous) {
          const timeStr = new Date().toLocaleTimeString();
          const row = document.createElement("div");
          row.className = "log-row";
          row.innerHTML = `<span>[${timeStr}]</span> Dispatched: <strong>${actionToDispatch.action}</strong> [Coord: ${Math.round(latestSmoothedPhysicalCoords.x)}, ${Math.round(latestSmoothedPhysicalCoords.y)}]`;
          logEntries.prepend(row);
          if (logEntries.children.length > 8) logEntries.removeChild(logEntries.lastChild);
        }
      }
    } else {
      liveLandmarks = null;
      gestureHud.textContent = `GESTURE: NO HAND DETECTED`;
      confHud.textContent = `CONFIDENCE: 0%`;
      cursorSmoother.reset();
    }
  }

  btnToggleWebcam?.addEventListener("click", async () => {
    if (webcamStream) {
      if (cameraUtilsInstance) {
        cameraUtilsInstance.stop();
        cameraUtilsInstance = null;
      }
      webcamStream.getTracks().forEach(t => t.stop());
      webcamStream = null;
      if (video) video.srcObject = null;
      isLiveVisionActive = false;
      liveLandmarks = null;

      if (labelWebcamBtn) labelWebcamBtn.textContent = "Start Live Camera";
      btnToggleWebcam.className = "btn btn-primary btn-sm";
      if (statusPillCamera) statusPillCamera.innerHTML = `<span class="dot red"></span> OFF`;
      showToast("Camera stopped.");
      return;
    }

    try {
      showToast("Initializing camera and MediaPipe on-device vision...");
      const hasMediaPipe = await initMediaPipe();

      webcamStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false
      });

      if (video) {
        video.srcObject = webcamStream;
        await video.play();
      }

      if (labelWebcamBtn) labelWebcamBtn.textContent = "Stop Camera";
      btnToggleWebcam.className = "btn btn-secondary btn-sm";
      if (statusPillCamera) statusPillCamera.innerHTML = `<span class="dot green pulse"></span> ON`;

      if (hasMediaPipe && typeof window.Camera !== "undefined") {
        cameraUtilsInstance = new Camera(video, {
          onFrame: async () => {
            if (mediaPipeHands && video.readyState >= 2) {
              await mediaPipeHands.send({ image: video });
            }
          },
          width: 640,
          height: 480
        });
        cameraUtilsInstance.start();
      } else {
        const processFrameFallback = async () => {
          if (webcamStream && mediaPipeHands && video.readyState >= 2) {
            await mediaPipeHands.send({ image: video });
            requestAnimationFrame(processFrameFallback);
          }
        };
        requestAnimationFrame(processFrameFallback);
      }

      showToast("Live camera active! Hand tracking overlay enabled.");
    } catch (err) {
      showToast(`Camera initialization error: ${err.message}`, true);
      console.error("[Camera] Error:", err);
    }
  });

  // Canvas Render Loop
  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (webcamStream && video && video.readyState >= 2) {
      ctx.save();
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      ctx.restore();

      ctx.fillStyle = "rgba(10, 35, 28, 0.42)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    } else {
      ctx.strokeStyle = "rgba(0, 120, 93, 0.08)";
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }
    }

    const displayJoints = liveLandmarks || currentJoints;

    if (!liveLandmarks) {
      for (let i = 0; i < currentJoints.length; i++) {
        currentJoints[i].x += (targetJoints[i].x + mouseOffsetX - currentJoints[i].x) * 0.15;
        currentJoints[i].y += (targetJoints[i].y + mouseOffsetY - currentJoints[i].y) * 0.15;
      }
    }

    // Draw Skeleton Bones
    ctx.strokeStyle = "rgba(50, 191, 219, 0.9)";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";

    connections.forEach(([s, e]) => {
      const p1 = displayJoints[s];
      const p2 = displayJoints[e];
      if (p1 && p2) {
        const x1 = liveLandmarks ? (1.0 - p1.x) * canvas.width : p1.x * canvas.width;
        const y1 = p1.y * canvas.height;
        const x2 = liveLandmarks ? (1.0 - p2.x) * canvas.width : p2.x * canvas.width;
        const y2 = p2.y * canvas.height;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    });

    // Draw Landmark Joints
    displayJoints.forEach((j, idx) => {
      const cx = liveLandmarks ? (1.0 - j.x) * canvas.width : j.x * canvas.width;
      const cy = j.y * canvas.height;

      if (idx === 8) {
        ctx.fillStyle = "#32bfdb";
        ctx.beginPath(); ctx.arc(cx, cy, 8, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2; ctx.stroke();
      } else if (idx === 4) {
        ctx.fillStyle = "#fdc323";
        ctx.beginPath(); ctx.arc(cx, cy, 7, 0, Math.PI * 2); ctx.fill();
      } else if (idx === 12) {
        ctx.fillStyle = "#539ba9";
        ctx.beginPath(); ctx.arc(cx, cy, 6, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.fillStyle = "#ffffff";
        ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill();
      }
    });

    // Draw Virtual Pointer Circle on Canvas
    if (virtualCursorEnabled && gestureControlEnabled && displayJoints[8]) {
      const indexPt = displayJoints[8];
      const cursorX = liveLandmarks ? (1.0 - indexPt.x) * canvas.width : indexPt.x * canvas.width;
      const cursorY = indexPt.y * canvas.height;

      ctx.strokeStyle = "#fdc323";
      ctx.lineWidth = 2.5;
      ctx.beginPath(); ctx.arc(cursorX, cursorY, 16, 0, Math.PI * 2); ctx.stroke();

      ctx.fillStyle = "rgba(253, 195, 35, 0.3)";
      ctx.beginPath(); ctx.arc(cursorX, cursorY, 8, 0, Math.PI * 2); ctx.fill();
    }

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}
