import customtkinter as ctk
import webbrowser
import re

class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        # Removed the conflicting self.pack(...) line here!
        self.setup_ui()

    def setup_ui(self):
        # --- API CREDENTIALS FRAME ---
        api_frame = ctk.CTkFrame(self)
        api_frame.pack(fill="x", pady=(0, 15), padx=10, ipady=10)
        
        ctk.CTkLabel(api_frame, text="Twitch Client ID", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15, pady=(10, 0))
        self.set_id = ctk.CTkEntry(api_frame, placeholder_text="Enter Client ID")
        self.set_id.pack(fill="x", padx=15, pady=(2, 10))
        self.set_id.insert(0, self.app.cfg.get("t_id", ""))
        
        ctk.CTkLabel(api_frame, text="Twitch Client Secret", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15)
        self.set_sec = ctk.CTkEntry(api_frame, placeholder_text="Enter Client Secret", show="*")
        self.set_sec.pack(fill="x", padx=15, pady=(2, 10))
        self.set_sec.insert(0, self.app.cfg.get("t_sec", ""))
        
        ctk.CTkLabel(api_frame, text="Twitch Access Token", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15)
        self.set_tok = ctk.CTkEntry(api_frame, placeholder_text="Generated Token will appear here", show="*")
        self.set_tok.pack(fill="x", padx=15, pady=(2, 10))
        self.set_tok.insert(0, self.app.cfg.get("t_tok", ""))

        ctk.CTkLabel(api_frame, text="Primary Discord Webhook URL", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15)
        self.set_webhook = ctk.CTkEntry(api_frame, placeholder_text="https://discord.com/api/webhooks/...")
        self.set_webhook.pack(fill="x", padx=15, pady=(2, 10))
        self.set_webhook.insert(0, self.app.cfg.get("webhook", ""))
        
        ctk.CTkLabel(api_frame, text="Secondary Discord Webhook URL (Optional)", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15)
        self.set_webhook_sec = ctk.CTkEntry(api_frame, placeholder_text="Optional second channel...")
        self.set_webhook_sec.pack(fill="x", padx=15, pady=(2, 15))
        self.set_webhook_sec.insert(0, self.app.cfg.get("webhook_sec", ""))

        ctk.CTkButton(
            api_frame, 
            text="💾 SAVE CONNECTIONS", 
            fg_color="#21612b", 
            hover_color="#184a1f",
            font=("Arial", 12, "bold"),
            command=self.app.save_settings
        ).pack(fill="x", padx=15, pady=(0, 10), ipady=5)

        # --- TOKEN GENERATOR FRAME ---
        token_frame = ctk.CTkFrame(self)
        token_frame.pack(fill="x", pady=(0, 15), padx=10, ipady=10)
        
        ctk.CTkLabel(token_frame, text="Token Generator", font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        auth_url_display = "https://id.twitch.tv/oauth2/authorize?client_id={YOUR_ID}&redirect_uri=http://localhost:17563&response_type=token&scope=channel:manage:schedule"
        ctk.CTkLabel(token_frame, text=auth_url_display, font=("Consolas", 9), text_color="#00FFFF", wraplength=500, justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        
        ctk.CTkButton(
            token_frame, 
            text="🌐 OPEN AUTH LINK", 
            fg_color="#333333", 
            hover_color="#444444",
            command=self.open_auth_link
        ).pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(token_frame, text="Paste Broken URL Here:", font=("Arial", 11, "bold"), text_color="#AAAAAA").pack(anchor="w", padx=15)
        self.token_url_entry = ctk.CTkEntry(token_frame, placeholder_text="http://localhost:17563/#access_token=...")
        self.token_url_entry.pack(fill="x", padx=15, pady=(2, 10))
        
        ctk.CTkButton(
            token_frame, 
            text="🔑 EXTRACT TOKEN", 
            fg_color="#333333", 
            hover_color="#444444",
            command=self.extract_token
        ).pack(fill="x", padx=15, pady=(0, 10))

        # --- GLOBAL TIMEZONES FRAME ---
        tz_frame = ctk.CTkFrame(self)
        tz_frame.pack(fill="x", pady=(0, 5), padx=10, ipady=10)
        
        ctk.CTkLabel(tz_frame, text="Global Timezones", font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=(10, 10))
        
        self.time_fmt = ctk.CTkOptionMenu(tz_frame, values=["24-Hour (20:00)", "12-Hour (8:00 PM)"], command=self.trigger_preview)
        self.time_fmt.pack(fill="x", padx=15, pady=5)
        self.time_fmt.set(self.app.cfg.get("time_fmt", "24-Hour (20:00)"))
        
        self.my_zone = ctk.CTkOptionMenu(tz_frame, values=list(self.app.tz_map.keys()), command=self.trigger_preview)
        self.my_zone.pack(fill="x", padx=15, pady=5)
        self.my_zone.set(self.app.cfg.get("my_zone", "UK (GMT/BST)"))
        
        self.sec_zone = ctk.CTkOptionMenu(tz_frame, values=list(self.app.sec_tz_map.keys()), command=self.trigger_preview)
        self.sec_zone.pack(fill="x", padx=15, pady=5)
        self.sec_zone.set(self.app.cfg.get("sec_zone", "US East (EST/EDT)"))
        
        import tkinter as tk
        self.show_primary = tk.BooleanVar(value=self.app.cfg.get("show_primary", True))
        ctk.CTkCheckBox(tz_frame, text="Show Timezone Labels", variable=self.show_primary, command=self.trigger_preview).pack(anchor="w", padx=15, pady=(10, 5))

    def trigger_preview(self, *args):
        if hasattr(self.app, 'schedule_preview'):
            self.app.schedule_preview()

    def open_auth_link(self):
        client_id = self.set_id.get().strip()
        if not client_id:
            self.app.log("⚠️ Error: Please enter your Twitch Client ID first!")
            return
            
        auth_url = f"https://id.twitch.tv/oauth2/authorize?client_id={client_id}&redirect_uri=http://localhost:17563&response_type=token&scope=channel:manage:schedule"
        webbrowser.open(auth_url)
        self.app.log("🌐 Opened browser for Twitch Authentication.")

    def extract_token(self):
        url = self.token_url_entry.get().strip()
        if not url:
            self.app.log("⚠️ Error: Paste the localhost URL into the box first!")
            return
            
        match = re.search(r'access_token=([a-zA-Z0-9_]+)', url)
        if match:
            extracted_token = match.group(1)
            self.set_tok.delete(0, 'end')
            self.set_tok.insert(0, extracted_token)
            self.token_url_entry.delete(0, 'end')
            self.app.log("✅ Token successfully extracted! Click 'Save Connections'.")
        else:
            self.app.log("❌ Error: Could not find an access token in that URL.")