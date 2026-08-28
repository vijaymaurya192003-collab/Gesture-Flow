package org.gestureflow.app;

import android.accessibilityservice.AccessibilityService;
import android.content.Context;
import android.graphics.Point;
import android.media.AudioManager;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Display;
import android.view.WindowManager;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * GestureAccessibilityPlugin
 *
 * Capacitor Plugin bridging web-layer MediaPipe gesture detections to
 * native Android AccessibilityService actions and hardware APIs.
 */
@CapacitorPlugin(name = "GestureAccessibility")
public class GestureAccessibilityPlugin extends Plugin {

    private static final String TAG = "GestureAccessPlugin";

    /**
     * Query whether the Gesture Flow AccessibilityService is enabled and connected.
     */
    @PluginMethod
    public void isServiceEnabled(PluginCall call) {
        Context context = getContext();
        boolean running = GestureAccessibilityService.isServiceRunning();
        boolean configured = GestureAccessibilityService.isServiceConfigured(context);

        JSObject ret = new JSObject();
        ret.put("enabled", running);
        ret.put("configured", configured);
        ret.put("running", running);
        ret.put("platform", "android");
        call.resolve(ret);
    }

    /**
     * Direct the user to Android Accessibility Settings.
     */
    @PluginMethod
    public void openAccessibilitySettings(PluginCall call) {
        Context context = getContext();
        boolean success = GestureAccessibilityService.openAccessibilitySettings(context);
        JSObject ret = new JSObject();
        ret.put("success", success);
        call.resolve(ret);
    }

    /**
     * Retrieve real physical screen dimensions and display metrics.
     */
    @PluginMethod
    public void getScreenDimensions(PluginCall call) {
        Context context = getContext();
        WindowManager wm = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
        int width = 1080;
        int height = 2400;
        float density = 2.0f;
        int densityDpi = 420;

        if (wm != null) {
            Display display = wm.getDefaultDisplay();
            Point size = new Point();
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                try {
                    android.view.WindowMetrics metrics = wm.getMaximumWindowMetrics();
                    android.graphics.Rect bounds = metrics.getBounds();
                    width = bounds.width();
                    height = bounds.height();
                } catch (Exception e) {
                    display.getRealSize(size);
                    width = size.x;
                    height = size.y;
                }
            } else {
                display.getRealSize(size);
                width = size.x;
                height = size.y;
            }

            DisplayMetrics dm = new DisplayMetrics();
            display.getMetrics(dm);
            density = dm.density;
            densityDpi = dm.densityDpi;
        }

        JSObject ret = new JSObject();
        ret.put("width", width);
        ret.put("height", height);
        ret.put("density", density);
        ret.put("densityDpi", densityDpi);
        call.resolve(ret);
    }

    /**
     * Dispatch structured action to Android OS via GestureAccessibilityService.
     */
    @PluginMethod
    public void dispatchAction(PluginCall call) {
        String action = call.getString("action", "NONE");
        if (action == null || action.equals("NONE")) {
            call.resolve(new JSObject().put("success", false).put("message", "Empty action"));
            return;
        }

        GestureAccessibilityService service = GestureAccessibilityService.getInstance();
        if (service == null) {
            JSObject ret = new JSObject();
            ret.put("success", false);
            ret.put("error", "ACCESSIBILITY_SERVICE_NOT_ENABLED");
            ret.put("message", "Gesture Accessibility Service is not enabled. Please enable it in Android Settings.");
            call.resolve(ret);
            return;
        }

        boolean success = false;

        try {
            switch (action.toUpperCase()) {
                case "TAP": {
                    Double x = call.getDouble("x");
                    Double y = call.getDouble("y");
                    if (x != null && y != null) {
                        success = service.dispatchTap(x.floatValue(), y.floatValue());
                        triggerHaptic(30);
                    }
                    break;
                }

                case "SWIPE": {
                    Double startX = call.getDouble("startX");
                    Double startY = call.getDouble("startY");
                    Double endX = call.getDouble("endX");
                    Double endY = call.getDouble("endY");
                    Integer duration = call.getInt("duration", 300);

                    if (startX != null && startY != null && endX != null && endY != null) {
                        success = service.dispatchSwipe(
                            startX.floatValue(), startY.floatValue(),
                            endX.floatValue(), endY.floatValue(),
                            duration != null ? duration.longValue() : 300L
                        );
                        triggerHaptic(35);
                    }
                    break;
                }

                case "PINCH_IN": {
                    Double centerX = call.getDouble("centerX");
                    Double centerY = call.getDouble("centerY");
                    Double distance = call.getDouble("distance", 200.0);
                    Integer duration = call.getInt("duration", 250);

                    float cx = (centerX != null) ? centerX.floatValue() : 540f;
                    float cy = (centerY != null) ? centerY.floatValue() : 1200f;
                    float dist = (distance != null) ? distance.floatValue() : 200f;
                    long dur = (duration != null) ? duration.longValue() : 250L;

                    success = service.dispatchPinchZoom(cx, cy, false, dist, dur);
                    break;
                }

                case "PINCH_OUT": {
                    Double centerX = call.getDouble("centerX");
                    Double centerY = call.getDouble("centerY");
                    Double distance = call.getDouble("distance", 200.0);
                    Integer duration = call.getInt("duration", 250);

                    float cx = (centerX != null) ? centerX.floatValue() : 540f;
                    float cy = (centerY != null) ? centerY.floatValue() : 1200f;
                    float dist = (distance != null) ? distance.floatValue() : 200f;
                    long dur = (duration != null) ? duration.longValue() : 250L;

                    success = service.dispatchPinchZoom(cx, cy, true, dist, dur);
                    break;
                }

                case "BACK": {
                    success = service.performGlobalActionSafe(AccessibilityService.GLOBAL_ACTION_BACK);
                    triggerHaptic(40);
                    break;
                }

                case "HOME": {
                    success = service.performGlobalActionSafe(AccessibilityService.GLOBAL_ACTION_HOME);
                    triggerHaptic(40);
                    break;
                }

                case "RECENTS": {
                    success = service.performGlobalActionSafe(AccessibilityService.GLOBAL_ACTION_RECENTS);
                    triggerHaptic(40);
                    break;
                }

                case "NOTIFICATIONS": {
                    success = service.performGlobalActionSafe(AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS);
                    triggerHaptic(40);
                    break;
                }

                case "QUICK_SETTINGS": {
                    success = service.performGlobalActionSafe(AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS);
                    triggerHaptic(40);
                    break;
                }

                case "VOLUME_UP": {
                    AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
                    if (am != null) {
                        am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI);
                        success = true;
                        triggerHaptic(25);
                    }
                    break;
                }

                case "VOLUME_DOWN": {
                    AudioManager am = (AudioManager) getContext().getSystemService(Context.AUDIO_SERVICE);
                    if (am != null) {
                        am.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI);
                        success = true;
                        triggerHaptic(25);
                    }
                    break;
                }

                default:
                    Log.w(TAG, "Unhandled action command: " + action);
                    break;
            }
        } catch (Exception e) {
            Log.e(TAG, "Error executing action: " + action, e);
        }

        JSObject ret = new JSObject();
        ret.put("success", success);
        ret.put("action", action);
        call.resolve(ret);
    }

    /**
     * Provide brief haptic vibration pulse.
     */
    @PluginMethod
    public void vibrate(PluginCall call) {
        Integer duration = call.getInt("duration", 35);
        triggerHaptic(duration != null ? duration : 35);
        call.resolve(new JSObject().put("success", true));
    }

    private void triggerHaptic(int durationMs) {
        try {
            Context context = getContext();
            Vibrator vibrator = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator != null && vibrator.hasVibrator()) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    vibrator.vibrate(durationMs);
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "Haptic vibration failed", e);
        }
    }
}

