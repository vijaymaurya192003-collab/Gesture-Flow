package org.gestureflow;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;
import android.content.Context;
import android.content.Intent;
import android.graphics.Path;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;

/**
 * GestureAccessibilityService
 * 
 * Native Android AccessibilityService that enables system-wide touchless HCI actions
 * (simulated taps, drag/scroll gestures, and global OS navigation).
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
}

