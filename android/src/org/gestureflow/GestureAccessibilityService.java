package org.gestureflow;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.accessibilityservice.GestureDescription;
import android.content.Context;
import android.content.Intent;
import android.graphics.Path;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityManager;
import java.util.List;

/**
 * GestureAccessibilityService
 * 
 * Native Android AccessibilityService that enables system-wide touchless HCI actions
 * (simulated taps, drag/scroll gestures, multi-touch zoom strokes, and global OS navigation).
 * 
 * Must be explicitly enabled by the user in Android Accessibility Settings.
 */
public class GestureAccessibilityService extends AccessibilityService {

    private static final String TAG = "GestureFlowService";
    private static volatile GestureAccessibilityService sInstance = null;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.i(TAG, "GestureAccessibilityService created.");
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        sInstance = this;
        Log.i(TAG, "GestureAccessibilityService connected and ready.");
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // We do not inspect user window content or keystrokes for strict privacy
    }

    @Override
    public void onInterrupt() {
        Log.w(TAG, "GestureAccessibilityService interrupted.");
    }

    @Override
    public boolean onUnbind(Intent intent) {
        if (sInstance == this) {
            sInstance = null;
        }
        Log.i(TAG, "GestureAccessibilityService unbound.");
        return super.onUnbind(intent);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (sInstance == this) {
            sInstance = null;
        }
        Log.i(TAG, "GestureAccessibilityService destroyed.");
    }

    /**
     * Check if the service is currently enabled and connected.
     */
    public static boolean isServiceRunning() {
        return sInstance != null;
    }

    /**
     * Get the active service instance.
     */
    public static GestureAccessibilityService getInstance() {
        return sInstance;
    }

    /**
     * Check if the service is configured and enabled in system settings.
     */
    public static boolean isServiceConfigured(Context context) {
        if (isServiceRunning()) return true;
        if (context == null) return false;
        try {
            AccessibilityManager am = (AccessibilityManager) context.getSystemService(Context.ACCESSIBILITY_SERVICE);
            if (am == null) return false;
            List<AccessibilityServiceInfo> enabledServices = am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK);
            if (enabledServices == null) return false;
            String targetName = GestureAccessibilityService.class.getName();
            for (AccessibilityServiceInfo info : enabledServices) {
                if (info.getId() != null && info.getId().contains(targetName)) {
                    return true;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Error checking accessibility service status", e);
        }
        return false;
    }

    /**
     * Open Android Accessibility Settings so the user can enable Gesture Flow.
     */
    public static boolean openAccessibilitySettings(Context context) {
        if (context == null) return false;
        try {
            Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
            return true;
        } catch (Exception e) {
            Log.e(TAG, "Failed to open accessibility settings", e);
            return false;
        }
    }

    /**
     * Perform global system navigation (Back, Home, Recents, Notifications).
     */
    public boolean performGlobalActionSafe(int actionId) {
        try {
            return performGlobalAction(actionId);
        } catch (Exception e) {
            Log.e(TAG, "Error performing global action " + actionId, e);
            return false;
        }
    }

    /**
     * Dispatch a tap gesture at the specified screen coordinates.
     */
    public boolean dispatchTap(float x, float y) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            Log.e(TAG, "GestureDescription requires Android 7.0 (API 24+)");
            return false;
        }

        try {
            Path path = new Path();
            path.moveTo(x, y);

            GestureDescription.StrokeDescription stroke = 
                new GestureDescription.StrokeDescription(path, 0, 50);

            GestureDescription.Builder builder = new GestureDescription.Builder();
            builder.addStroke(stroke);
            GestureDescription gesture = builder.build();

            return dispatchGesture(gesture, null, null);
        } catch (Exception e) {
            Log.e(TAG, "Error dispatching tap at (" + x + ", " + y + ")", e);
            return false;
        }
    }

    /**
     * Dispatch a continuous scroll/swipe gesture between two points.
     */
    public boolean dispatchScroll(float startX, float startY, float endX, float endY, long durationMs) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            Log.e(TAG, "GestureDescription requires Android 7.0 (API 24+)");
            return false;
        }

        try {
            Path path = new Path();
            path.moveTo(startX, startY);
            path.lineTo(endX, endY);

            long duration = (durationMs > 50 && durationMs < 2000) ? durationMs : 250;
            GestureDescription.StrokeDescription stroke = 
                new GestureDescription.StrokeDescription(path, 0, duration);

            GestureDescription.Builder builder = new GestureDescription.Builder();
            builder.addStroke(stroke);
            GestureDescription gesture = builder.build();

            return dispatchGesture(gesture, null, null);
        } catch (Exception e) {
            Log.e(TAG, "Error dispatching scroll", e);
            return false;
        }
    }

    /**
     * Dispatch a directional swipe gesture from (startX, startY) to (endX, endY).
     */
    public boolean dispatchSwipe(float startX, float startY, float endX, float endY, long durationMs) {
        return dispatchScroll(startX, startY, endX, endY, durationMs);
    }

    /**
     * Dispatch a multi-touch pinch-to-zoom gesture around a focal center point.
     * Zoom In: fingers start close together and move outward.
     * Zoom Out: fingers start apart and move inward.
     */
    public boolean dispatchPinchZoom(float centerX, float centerY, boolean zoomIn, float distance, long durationMs) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) {
            Log.e(TAG, "dispatchPinchZoom requires Android 7.0 (API 24+)");
            return false;
        }

        try {
            float delta = (distance > 20 && distance < 600) ? distance : 200;
            long duration = (durationMs >= 100 && durationMs <= 1000) ? durationMs : 250;

            float stroke1StartX, stroke1StartY, stroke1EndX, stroke1EndY;
            float stroke2StartX, stroke2StartY, stroke2EndX, stroke2EndY;

            if (zoomIn) {
                // Moving outward
                stroke1StartX = centerX - (delta * 0.25f);
                stroke1StartY = centerY;
                stroke1EndX = centerX - delta;
                stroke1EndY = centerY;

                stroke2StartX = centerX + (delta * 0.25f);
                stroke2StartY = centerY;
                stroke2EndX = centerX + delta;
                stroke2EndY = centerY;
            } else {
                // Moving inward
                stroke1StartX = centerX - delta;
                stroke1StartY = centerY;
                stroke1EndX = centerX - (delta * 0.25f);
                stroke1EndY = centerY;

                stroke2StartX = centerX + delta;
                stroke2StartY = centerY;
                stroke2EndX = centerX + (delta * 0.25f);
                stroke2EndY = centerY;
            }

            Path path1 = new Path();
            path1.moveTo(stroke1StartX, stroke1StartY);
            path1.lineTo(stroke1EndX, stroke1EndY);

            Path path2 = new Path();
            path2.moveTo(stroke2StartX, stroke2StartY);
            path2.lineTo(stroke2EndX, stroke2EndY);

            GestureDescription.StrokeDescription stroke1 =
                new GestureDescription.StrokeDescription(path1, 0, duration);
            GestureDescription.StrokeDescription stroke2 =
                new GestureDescription.StrokeDescription(path2, 0, duration);

            GestureDescription.Builder builder = new GestureDescription.Builder();
            builder.addStroke(stroke1);
            builder.addStroke(stroke2);
            GestureDescription gesture = builder.build();

            return dispatchGesture(gesture, null, null);
        } catch (Exception e) {
            Log.e(TAG, "Error dispatching pinch zoom", e);
            return false;
        }
    }
}

