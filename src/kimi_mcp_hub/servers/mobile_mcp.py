"""Mobile MCP server configuration."""

from typing import Any


class MobileMCPServer:
    """Mobile MCP -- iOS/Android automation on simulators, emulators, and real devices."""

    name = "mobile"
    display_name = "Mobile MCP"
    description = "iOS and Android mobile automation, testing, and app interaction."
    icon = "📱"

    @classmethod
    def get_stdio_config(cls) -> dict[str, Any]:
        """Local stdio server via npx."""
        return {
            "command": "npx",
            "args": ["-y", "@mobilenext/mobile-mcp@latest"],
            "env": {},
        }

    @classmethod
    def get_tools(cls) -> list[dict[str, str]]:
        return [
            {"name": "mobile_list_available_devices", "desc": "List simulators, emulators, and real devices"},
            {"name": "mobile_launch_app", "desc": "Launch an app by package/bundle ID"},
            {"name": "mobile_terminate_app", "desc": "Terminate a running app"},
            {"name": "mobile_install_app", "desc": "Install an app from file"},
            {"name": "mobile_take_screenshot", "desc": "Take a screenshot"},
            {"name": "mobile_list_elements_on_screen", "desc": "List UI elements with coordinates"},
            {"name": "mobile_click_on_screen_at_coordinates", "desc": "Tap at x,y coordinates"},
            {"name": "mobile_swipe_on_screen", "desc": "Swipe in a direction"},
            {"name": "mobile_type_keys", "desc": "Type text into focused elements"},
        ]
