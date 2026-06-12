import customtkinter as ctk
import datetime
import pytz

class DiscordTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- HEADER ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(header_frame, text="DISCORD DEPLOYMENT PREVIEW", font=("Arial Black", 18)).pack(side="left", padx=10)
        ctk.CTkButton(header_frame, text="🔄 Refresh Preview", font=("Arial", 13, "bold"), fg_color="#5865F2", hover_color="#4752C4", command=self.refresh_preview).pack(side="right", padx=10)

        # --- DISCORD MOCKUP WINDOW ---
        # Uses Discord's native hex color codes for the mock UI
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#313338", corner_radius=8) 
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        profile_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        profile_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 0))
        
        # Bot Avatar Placeholder
        avatar = ctk.CTkFrame(profile_frame, width=42, height=42, corner_radius=21, fg_color="#5865F2")
        avatar.pack(side="left", padx=(0, 15))
        
        name_label = ctk.CTkLabel(profile_frame, text="Simph Studio Bot", font=("Arial", 15, "bold"), text_color="#FFFFFF")
        name_label.pack(side="left")
        
        time_label = ctk.CTkLabel(profile_frame, text="Today at 12:00 PM", font=("Arial", 11), text_color="#949BA4")
        time_label.pack(side="left", padx=10)

        # The Generated Markdown Text
        self.message_text = ctk.CTkTextbox(self.scroll_frame, fg_color="transparent", text_color="#DBDEE1", font=("Consolas", 14), wrap="word", height=200)
        self.message_text.grid(row=1, column=0, sticky="ew", padx=65, pady=(5, 10))
        self.message_text.configure(state="disabled")

        # The Generated Image Attachment
        self.image_preview_label = ctk.CTkLabel(self.scroll_frame, text="Click 'Refresh Preview' to generate...", fg_color="#2B2D31", width=400, height=225, corner_radius=8)
        self.image_preview_label.grid(row=2, column=0, sticky="w", padx=65, pady=(0, 20))

    def refresh_preview(self):
        # 1. Construct the exact Markdown string that the bot uses
        sub_text = self.app.planner_tab.header_sub_entry.get().strip()
        discord_msg = f"# {sub_text}\n\n" if sub_text else "# STREAM SCHEDULE\n\n"
        
        base_dt = self.app.selected_start_date
        has_ticked_days = False

        for i, code in enumerate(self.app.all_days):
            item = self.app.planner_tab.days_ui_list[i]
            if item["check"].get():
                has_ticked_days = True
                g_val = item['game'].get().strip() or "TBA"
                sub_val = item['sub'].get().strip()
                sub_str = f" | {sub_val}" if sub_val else ""
                
                # Safely pull the note if the UI has loaded it
                note_val = item.get('note').get().strip() if 'note' in item else ""
                
                t_val = item['time'].get()
                is_off = item['offline'].get()
                is_can = item['cancelled'].get()
                
                if is_can:
                    discord_msg += f"- ~~`{self.app.full_days[code]}` - {g_val}{sub_str}~~ **[CANCELLED]**\n"
                elif is_off:
                    discord_msg += f"- `{self.app.full_days[code]}` - **OFFLINE**\n"
                elif t_val == "TBA":
                    discord_msg += f"- `{self.app.full_days[code]}` - **{g_val}**{sub_str} (Time TBA)\n"
                else:
                    try:
                        h, m = map(int, t_val.split(':'))
                        tz_str = self.app.tz_map.get(self.app.settings_tab.my_zone.get(), "Europe/London")
                        loc_tz = pytz.timezone(tz_str)
                        target_dt = loc_tz.localize(datetime.datetime(base_dt.year, base_dt.month, base_dt.day, h, m) + datetime.timedelta(days=i))
                        unix_ts = int(target_dt.timestamp())
                        discord_msg += f"- `{self.app.full_days[code]}` - **{g_val}**{sub_str} <t:{unix_ts}:t>\n"
                    except: 
                        discord_msg += f"- `{self.app.full_days[code]}` - **{g_val}**{sub_str} (Time Error)\n"
                
                if note_val:
                    discord_msg += f"*{note_val}*\n"
        
        if not has_ticked_days: 
            discord_msg += "No streams scheduled for this week!"

        # 2. Inject text into the UI
        self.message_text.configure(state="normal")
        self.message_text.delete("1.0", "end")
        self.message_text.insert("1.0", discord_msg)
        
        # Scale textbox height based on line count
        lines = discord_msg.count('\n') + 2
        self.message_text.configure(height=lines * 22, state="disabled")

        # 3. Pull the active Image directly from the Planner Tab's canvas renderer
        current_image = self.app.planner_tab.preview_label.cget("image")
        if current_image and current_image != "":
            self.image_preview_label.configure(image=current_image, text="")
        else:
            self.image_preview_label.configure(text="No Canvas Rendered Yet. Configure Schedule first.", image="")