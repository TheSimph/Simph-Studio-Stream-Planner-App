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
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title_lbl = ctk.CTkLabel(header_frame, text="💬 LIVE DISCORD DEPLOYMENT PREVIEW", font=("Arial Black", 18), text_color="#FFFFFF")
        title_lbl.pack(side="left")
        
        refresh_btn = ctk.CTkButton(header_frame, text="🔄 Sync Latest Changes", font=("Arial", 13, "bold"), fg_color="#5865F2", hover_color="#4752C4", corner_radius=6, height=35, command=self.refresh_preview)
        refresh_btn.pack(side="right")

        # --- DISCORD MOCKUP WINDOW (The Premium Container) ---
        self.discord_bg = ctk.CTkFrame(self, fg_color="#313338", corner_radius=8, border_width=1, border_color="#1E1F22") 
        self.discord_bg.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.discord_bg.grid_columnconfigure(0, weight=1)
        self.discord_bg.grid_rowconfigure(1, weight=1)

        # Fake Discord Channel Header
        channel_header = ctk.CTkFrame(self.discord_bg, height=48, fg_color="#313338", corner_radius=8)
        channel_header.grid(row=0, column=0, sticky="ew")
        channel_header.pack_propagate(False)
        
        # Subtle bottom border for channel header
        border_line = ctk.CTkFrame(self.discord_bg, height=1, fg_color="#1E1F22")
        border_line.grid(row=0, column=0, sticky="ews", pady=(47, 0))

        ctk.CTkLabel(channel_header, text="#", font=("Arial", 22, "bold"), text_color="#80848E").pack(side="left", padx=(15, 5), pady=10)
        ctk.CTkLabel(channel_header, text="schedule-updates", font=("Arial", 15, "bold"), text_color="#FFFFFF").pack(side="left", pady=10)
        ctk.CTkLabel(channel_header, text="|", font=("Arial", 15), text_color="#4E5058").pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(channel_header, text="Live preview of your next deployment", font=("Arial", 13), text_color="#B5BAC1").pack(side="left", pady=10)

        # Scrollable chat area
        self.chat_scroll = ctk.CTkScrollableFrame(self.discord_bg, fg_color="transparent")
        self.chat_scroll.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        # --- SINGLE MESSAGE BLOCK ---
        self.msg_container = ctk.CTkFrame(self.chat_scroll, fg_color="transparent", corner_radius=0)
        self.msg_container.grid(row=0, column=0, sticky="ew", pady=15)
        self.msg_container.grid_columnconfigure(1, weight=1)

        # Profile Picture Column
        pfp_col = ctk.CTkFrame(self.msg_container, fg_color="transparent", width=60)
        pfp_col.grid(row=0, column=0, sticky="nw", padx=(15, 5))
        
        # Premium PFP with a letter inside
        self.avatar = ctk.CTkLabel(pfp_col, text="S", font=("Arial Black", 20), text_color="#FFFFFF", width=42, height=42, fg_color="#5865F2", corner_radius=21)
        self.avatar.pack(pady=(5, 0))

        # Content Column
        content_col = ctk.CTkFrame(self.msg_container, fg_color="transparent")
        content_col.grid(row=0, column=1, sticky="nsew")
        content_col.grid_columnconfigure(0, weight=1)

        # Name and Timestamp
        meta_frame = ctk.CTkFrame(content_col, fg_color="transparent")
        meta_frame.grid(row=0, column=0, sticky="ew", pady=(2, 5))
        
        ctk.CTkLabel(meta_frame, text="Simph Studio Bot", font=("Segoe UI", 15, "bold"), text_color="#F2F3F5").pack(side="left")
        
        # Bot Badge
        bot_badge = ctk.CTkFrame(meta_frame, fg_color="#5865F2", corner_radius=3, width=32, height=16)
        bot_badge.pack(side="left", padx=5)
        bot_badge.pack_propagate(False)
        ctk.CTkLabel(bot_badge, text="APP", font=("Segoe UI", 10, "bold"), text_color="#FFFFFF").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(meta_frame, text="Today at 12:00 PM", font=("Segoe UI", 12), text_color="#949BA4").pack(side="left", padx=5)

        # Markdown Text Area
        self.message_text = ctk.CTkTextbox(content_col, fg_color="transparent", text_color="#DBDEE1", font=("Segoe UI", 15), wrap="word", height=20)
        self.message_text.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=0)
        self.message_text.configure(state="disabled")

        # Image Embed Container (Discord style left-border)
        embed_container = ctk.CTkFrame(content_col, fg_color="#2B2D31", corner_radius=4)
        embed_container.grid(row=2, column=0, sticky="w", pady=(0, 10))
        
        # Accent line
        embed_color_bar = ctk.CTkFrame(embed_container, width=4, fg_color="#1E1F22", corner_radius=0)
        embed_color_bar.pack(side="left", fill="y")
        
        img_padding = ctk.CTkFrame(embed_container, fg_color="transparent")
        img_padding.pack(side="left", padx=12, pady=12)

        self.image_preview_label = ctk.CTkLabel(img_padding, text="Awaiting render...", fg_color="#1E1F22", width=800, height=450, corner_radius=6, font=("Segoe UI", 13), text_color="#949BA4")
        self.image_preview_label.pack()

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
        
        # Scale textbox height based on line count dynamically
        lines = discord_msg.count('\n') + 2
        self.message_text.configure(height=lines * 24, state="disabled")

        # 3. Pull the active Image and scale it to Discord Embed constraints
        current_image = self.app.planner_tab.preview_label.cget("image")
        if current_image and current_image != "":
            try:
                # Extract the raw, unscaled PIL image from the current preview
                raw_img = current_image._light_image
                cw, ch = raw_img.size
                
                # Scaled up for large monitors to utilize space better
                max_w = 850
                max_h = 650
                
                # Calculate the ratio to shrink it perfectly into the box
                scale = min(max_w / cw, max_h / ch)
                scaled_w = int(cw * scale)
                scaled_h = int(ch * scale)
                
                # Generate a brand new, thumbnail-sized image specifically for this tab
                discord_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(scaled_w, scaled_h))
                self.image_preview_label.configure(image=discord_img, text="", width=scaled_w, height=scaled_h)
            except Exception:
                # Safe fallback just in case
                self.image_preview_label.configure(image=current_image, text="")
        else:
            self.image_preview_label.configure(text="No Canvas Rendered Yet. Configure Schedule first.", image="")