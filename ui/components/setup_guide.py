import customtkinter as ctk
import webbrowser

class SetupGuide:
    def __init__(self, parent):
        """
        Initializes the Setup Guide / Help Modal logic.
        """
        self.parent = parent
        self.help_win = None

    def show_help_popup(self):
        """
        Builds and displays the How-To guide.
        """
        if self.help_win and self.help_win.winfo_exists():
            self.help_win.focus()
            return

        self.help_win = ctk.CTkToplevel(self.parent)
        self.help_win.title("How to Use Simph Studio")
        self.help_win.geometry("750x650")
        self.help_win.attributes("-topmost", True)
        
        scroll = ctk.CTkScrollableFrame(self.help_win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(scroll, text="SYSTEM SETUP GUIDE", font=("Arial", 18, "bold")).pack(anchor="w", pady=(0, 10))

        # --- Section 1: Twitch ---
        t1 = "1. Twitch API Setup (Crucial!)"
        d1 = ("To use dynamic game art and sync your Twitch schedule automatically, you need a Twitch App:\n"
              "• Go to the Twitch Developer Console.\n"
              "• Click 'Register Your Application'.\n"
              "• Name it whatever you like, set Category to 'Application Integration'.\n"
              "• ⚠️ CRITICAL: Set the OAuth Redirect URL EXACTLY to: http://localhost:17563\n"
              "• Click Create, then copy your Client ID and generate a Client Secret.")
        self.add_manual(scroll, t1, d1, "https://dev.twitch.tv/console", "Open Twitch Dev Console")

        # --- Section 2: Discord ---
        t2 = "2. Discord Webhook Setup"
        d2 = ("To deploy your schedule directly to a Discord channel:\n"
              "• Open your Discord Server Settings.\n"
              "• Go to Integrations > Webhooks.\n"
              "• Create a 'New Webhook', pick your schedule channel, and copy the Webhook URL.\n"
              "• Paste that URL into the 'APP SETTINGS' tab of this app.")
        self.add_manual(scroll, t2, d2, "https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks", "Discord Webhook Guide")

        # --- Section 3: Features ---
        t3 = "3. App Features"
        d3 = ("▶ MULTI-EXPORT: Tick the formats you want on the Export tab. Deploying saves them all to your chosen local folder!\n"
              "▶ DISCORD DEPLOY: Choose exactly which ratio gets posted to Discord from the dropdown.\n"
              "▶ DEPLOY BUTTON: Sends the chosen format to Discord AND updates your Twitch schedule simultaneously.")
        self.add_manual(scroll, t3, d3, None, None)

        # --- Dismiss Button ---
        ctk.CTkButton(
            scroll, 
            text="Got it!", 
            fg_color="#7044c4", 
            hover_color="#5a369e", 
            command=self.help_win.destroy
        ).pack(pady=40)

    def add_manual(self, p, t, d, url, btn_text):
        """
        Helper method to standardize the layout of help sections.
        """
        ctk.CTkLabel(p, text=t, font=("Arial", 14, "bold"), text_color="#a970ff").pack(pady=(20,0), anchor="w")
        ctk.CTkLabel(p, text=d, wraplength=700, justify="left").pack(anchor="w", pady=(5, 5))
        
        if url and btn_text: 
            ctk.CTkButton(
                p, 
                text=f"🔗 {btn_text}", 
                height=28, 
                fg_color="#333333", 
                hover_color="#444444", 
                command=lambda u=url: webbrowser.open(u)
            ).pack(pady=5, anchor="w")