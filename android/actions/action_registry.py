"""
Safe Action Whitelist & Registry
Guarantees that only predefined safe actions can ever be dispatched.
Arbitrary command execution is strictly forbidden.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from android.config.constants import SafeActionType


@dataclass
class ActionMetadata:
    """Action metadata definition."""
    name: str
    category: str  # "Navigation", "Interaction", "Media", "System"
    description: str
    is_continuous: bool = False
    requires_accessibility: bool = False


class ActionRegistry:
    """Central registry of verified safe actions."""

    _REGISTRY: Dict[str, ActionMetadata] = {
        SafeActionType.POINTER_MOVE.value: ActionMetadata(
            name="Move Pointer",
            category="Interaction",
            description="Moves the on-screen pointer/cursor based on index fingertip coordinates",
            is_continuous=True,
            requires_accessibility=True
        ),
        SafeActionType.TAP.value: ActionMetadata(
            name="Tap / Click",
            category="Interaction",
            description="Dispatches a click/tap at the current pointer position",
            requires_accessibility=True
        ),
        SafeActionType.SCROLL_UP.value: ActionMetadata(
            name="Scroll Up",
            category="Navigation",
            description="Scrolls page or list view upward",
            requires_accessibility=True
        ),
        SafeActionType.SCROLL_DOWN.value: ActionMetadata(
            name="Scroll Down",
            category="Navigation",
            description="Scrolls page or list view downward",
            requires_accessibility=True
        ),
        SafeActionType.BACK.value: ActionMetadata(
            name="Navigate Back",
            category="Navigation",
            description="Triggers system global Back action",
            requires_accessibility=True
        ),
        SafeActionType.HOME.value: ActionMetadata(
            name="Navigate Home",
            category="Navigation",
            description="Triggers system global Home screen navigation",
            requires_accessibility=True
        ),
        SafeActionType.RECENTS.value: ActionMetadata(
            name="Recent Apps",
            category="Navigation",
            description="Opens system Recent Apps / App Switcher overview",
            requires_accessibility=True
        ),
        SafeActionType.VOLUME_UP.value: ActionMetadata(
            name="Volume Up",
            category="Media",
            description="Increases media audio volume",
            requires_accessibility=False
        ),
        SafeActionType.VOLUME_DOWN.value: ActionMetadata(
            name="Volume Down",
            category="Media",
            description="Decreases media audio volume",
            requires_accessibility=False
        ),
        SafeActionType.MEDIA_PLAY_PAUSE.value: ActionMetadata(
            name="Play / Pause Media",
            category="Media",
            description="Toggles media playback for active media sessions",
            requires_accessibility=False
        ),
        SafeActionType.PAUSE_GESTURES.value: ActionMetadata(
            name="Pause / Resume Gestures",
            category="System",
            description="Temporarily suspends or activates gesture tracking",
            requires_accessibility=False
        ),
        SafeActionType.EMERGENCY_STOP.value: ActionMetadata(
            name="Emergency Stop",
            category="System",
            description="Immediate safety lockout; ceases all action dispatching until manually reset",
            requires_accessibility=False
        ),
    }

    @classmethod
    def is_safe(cls, action_name: str) -> bool:
        """Check if an action is in the verified whitelist."""
        return action_name in cls._REGISTRY

    @classmethod
    def get_metadata(cls, action_name: str) -> Optional[ActionMetadata]:
        """Retrieve metadata for a registered action."""
        return cls._REGISTRY.get(action_name)

    @classmethod
    def list_all_actions(cls) -> List[str]:
        """Return list of all registered safe action names."""
        return list(cls._REGISTRY.keys())

