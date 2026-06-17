import os
import json

class SettingsManager:
    def __init__(self):
        self.APP_VERSION = "0.1.61"
        self.appdata_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'SimphStudio')
        os.makedirs(self.appdata_dir, exist_ok=True)
        
        self.settings_path = os.path.join(self.appdata_dir, "settings.json")
        self.config = self.load_settings()

    def get_default_settings(self):
        """Returns the base fallback configuration dictionary."""
        return {
            "webhook": "",
            "t_id": "",
            "t_sec": "",
            "t_tok": "",
            "last_msg_id": "",
            "window_geometry": "1650x1000",
            "font": "Arial Black",
            "box_color": "#6E1414",
            "bg_zoom": 100,
            "box_opacity": 240,
            "header_txt_color": "#FFFFFF",
            "sub_txt_color": "#C8C8C8",
            "box_txt_color": "#FFFFFF",
            "header_text": "STREAMER SCHEDULE",
            "header_size": 100,
            "sub_size": 40,
            "logo_size": 200,
            "game_size": 45,
            "subtitle_size": 30,
            "export_path": "",
            "deploy_format": "9:16 (TikTok/Reels/Shorts)",
            "my_zone": "UK (GMT/BST)",
            "sec_zone": "US East (EST/EDT)",
            "start_day": "MON",
            "canvas_format": "9:16 (TikTok/Reels/Shorts)",
            "max_box_h": 250,
            "time_fmt": "24-Hour (20:00)",
            "show_primary": True,
            "sponsor_title": "",
            "goal_current": "",
            "goal_target": "",
            "sponsor_path": ""
        }

    def load_settings(self):
        """Loads settings from the JSON file, or falls back to defaults."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r") as f:
                    loaded_data = json.load(f)
                    # Merge with defaults to ensure missing keys are populated across updates
                    defaults = self.get_default_settings()
                    defaults.update(loaded_data)
                    return defaults
            except Exception:
                pass
        return self.get_default_settings()

    def save_settings(self):
        """Writes the current configuration dictionary securely to the JSON file."""
        with open(self.settings_path, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        """Retrieves a specific setting value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Sets a specific setting value. Call save_settings() to write to disk."""
        self.config[key] = value

    def update(self, data_dict):
        """Bulk updates multiple settings at once."""
        self.config.update(data_dict)