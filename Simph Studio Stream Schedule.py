import customtkinter as ctk
import tkinter as tk
import json, datetime, time, os, textwrap, re, requests, asyncio, pytz, webbrowser, shutil
from PIL import Image, ImageDraw, ImageFont, ImageOps
from tkinter import filedialog, messagebox, colorchooser
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.type import AuthScope
import threading

class SimphStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- UPDATE SETTINGS ---
        # Change this number before you compile a new version for your friends!
        self.APP_VERSION = "0.1"
        self.UPDATE_URL = "https://raw.githubusercontent.com/TheSimph/Simph-Studio/main/version.txt"
        self.RELEASE_URL = "https://github.com/TheSimph/Simph-Studio/releases/latest"

        self.title(f"Simph Stream Schedule App - Ver {self.APP_VERSION} Beta")
        self.geometry("1550x1000")
        ctk.set_appearance_mode("dark")
        
        # --- APPDATA VAULT SETUP ---
        self.appdata_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), 'SimphStudio')
        os.makedirs(self.appdata_dir, exist_ok=True)
        self.settings_path = os.path.join(self.appdata_dir, "settings.json")
        
        self.all_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        self.full_days = {"MON":"Monday","TUE":"Tuesday","WED":"Wednesday","THU":"Thursday","FRI":"Friday","SAT":"Saturday","SUN":"Sunday"}
        self.cfg = self.load_settings()
        self.search_timers = {} 
        self.art_cache = {} 
        self.game_ids = {} 
        
        # --- TIMEZONE DICTIONARIES ---
        self.tz_map = {
            "UK (GMT/BST)": "Europe/London",
            "US East (EST/EDT)": "US/Eastern",
            "US Central (CST/CDT)": "US/Central",
            "US Mountain (MST/MDT)": "US/Mountain",
            "US Pacific (PST/PDT)": "US/Pacific",
            "Europe Central (CET/CEST)": "Europe/Berlin",
            "Australia (AEST/AEDT)": "Australia/Sydney",
            "UTC": "UTC"
        }
        self.sec_tz_map = {"None (Hide)": "N/A"}
        self.sec_tz_map.update(self.tz_map)
        
        if self.cfg.get("my_zone") not in self.tz_map: self.cfg["my_zone"] = "UK (GMT/BST)"
        if self.cfg.get("sec_zone") not in self.sec_tz_map: self.cfg["sec_zone"] = "US East (EST/EDT)"

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(padx=20, pady=20, fill="both", expand=True)
        self.tab_planner = self.tabs.add("📅 WEEKLY PLANNER")
        self.tab_settings = self.tabs.add("⚙️ APP SETTINGS")

        self.setup_planner_tab()
        self.setup_settings_tab()
        
        self.console = ctk.CTkTextbox(self, height=120, font=("Consolas", 12))
        self.console.pack(padx=20, pady=(0, 20), fill="x")
        self.apply_right_click(self.console)
        
        self.bind("<Button-1>", lambda e: self.hide_all_suggest())
        
        self.tabs.set("⚙️ APP SETTINGS")
        self.after(500, self.generate_preview_image)
        self.after(1000, self.check_first_run)
        self.after(1200, self.refresh_status)
        self.after(2000, self.check_for_updates)

    def log(self, text):
        self.console.insert("end", f"> {text}\n")
        self.console.see("end")

    # --- VAULT & SETTINGS LOGIC ---
    def load_settings(self):
        local_old_path = "settings.json"
        if os.path.exists(local_old_path):
            try:
                shutil.copy(local_old_path, self.settings_path)
                os.remove(local_old_path)
            except: pass

        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r") as f: return json.load(f)
            except: pass
        return {
            "webhook": "", "t_id": "", "t_sec": "", "t_tok": "", "last_msg_id": "",
            "font": "Arial Black", "box_color": "#6E1414", "bg_zoom": 100, "box_opacity": 240,
            "header_txt_color": "#FFFFFF", "sub_txt_color": "#C8C8C8", "box_txt_color": "#FFFFFF",
            "header_text": "STREAMER SCHEDULE", "header_sub": "PICK DATE IN SIDEBAR",
            "header_size": 100, "sub_size": 40, "logo_size": 200,
            "my_zone": "UK (GMT/BST)", "sec_zone": "US East (EST/EDT)", "start_day": "MON"
        }

    # --- AUTO-UPDATER LOGIC ---
    def check_for_updates(self):
        def run_check():
            try:
                response = requests.get(self.UPDATE_URL, timeout=3)
                if response.status_code == 200:
                    latest_v = response.text.strip()
                    if latest_v != self.APP_VERSION and len(latest_v) < 10:
                        self.after(0, lambda: self.show_update_popup(latest_v))
            except: pass 
        threading.Thread(target=run_check, daemon=True).start()

    def show_update_popup(self, new_v):
        msg = f"A new version of Simph Studio (Ver {new_v}) is available!\n\nWould you like to download it now?\n(Your settings are safely backed up to your system automatically.)"
        if messagebox.askyesno("Update Available", msg):
            webbrowser.open(self.RELEASE_URL)

    # --- RIGHT CLICK INJECTION ---
    def apply_right_click(self, widget):
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#1f538d", activeborderwidth=0)
        menu.add_command(label="Cut", command=lambda: widget.focus() or widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.focus() or widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.focus() or widget.event_generate("<<Paste>>"))
        target = widget._entry if hasattr(widget, "_entry") else widget
        target.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    # --- DISCORD SUMMARY LOGIC ---
    def get_suffix(self, n):
        if 11 <= n <= 13: return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    def get_discord_header(self):
        try:
            sd = datetime.datetime.strptime(self.date_menu.get(), "%Y-%m-%d")
            ed = sd + datetime.timedelta(days=6)
            return f"# __{sd.strftime('%b %d')}{self.get_suffix(sd.day)} - {ed.strftime('%b %d')}{self.get_suffix(ed.day)}__"
        except: return "# __Stream Schedule__"

    # --- TOKEN EXTRACTION LOGIC ---
    def update_auth_link(self, *args):
        cid = self.set_id.get().strip()
        link = f"https://id.twitch.tv/oauth2/authorize?client_id={cid}&redirect_uri=http://localhost:17563&response_type=token&scope=channel:manage:schedule"
        self.link_display.configure(text=link if len(cid) > 5 else "Enter Client ID first...")

    def extract_token(self):
        raw_url = self.url_paste.get().strip()
        match = re.search(r"access_token=([a-z0-9]+)", raw_url)
        if match:
            token = match.group(1)
            self.set_tok.delete(0, 'end')
            self.set_tok.insert(0, token)
            self.log(f"✅ Token Extracted!")
            messagebox.showinfo("Extraction Successful!", "Your Twitch account is now linked to the app.\n\nIMPORTANT: Please click the green 'SAVE ALL SETTINGS' button at the bottom so you don't have to do this again next time!")
        else:
            messagebox.showerror("Extraction Error", "URL invalid. Please make sure you copied the FULL link from the top of your browser on the 'refused to connect' page.")

    def hide_all_suggest(self):
        for item in self.days_ui_list:
            f = item["suggest"]
            [c.destroy() for c in f.winfo_children()]
            f.configure(height=0)

    def get_converted_time(self, time_str, from_zone_display, to_zone_display):
        try:
            f_tz_str = self.tz_map.get(from_zone_display, "Europe/London")
            f_tz = pytz.timezone(f_tz_str)
            h, m = map(int, time_str.split(':'))
            now = datetime.datetime.now()
            loc_dt = f_tz.localize(datetime.datetime(now.year, now.month, now.day, h, m))
            
            if to_zone_display == "None (Hide)":
                return f"{time_str} {loc_dt.strftime('%Z')}"
                
            t_tz_str = self.sec_tz_map.get(to_zone_display, "US/Eastern")
            t_tz = pytz.timezone(t_tz_str)
            tar_dt = loc_dt.astimezone(t_tz)
            return f"{time_str} {loc_dt.strftime('%Z')} / {tar_dt.strftime('%H:%M')} {tar_dt.strftime('%Z')}"
        except: return time_str

    # --- MASTER DRAWING ENGINE ---
    def generate_preview_image(self, *args):
        try:
            if os.path.exists(self.cfg.get("bg_path", "background.jpg")):
                raw_bg = Image.open(self.cfg.get("bg_path", "background.jpg")).convert("RGBA")
                base_fit = ImageOps.fit(raw_bg, (1080, 1920), method=Image.Resampling.LANCZOS)
                
                zoom = int(self.bg_zoom_slider.get()) / 100.0
                if zoom > 1.0:
                    new_w, new_h = int(1080 / zoom), int(1920 / zoom)
                    left = (1080 - new_w) // 2
                    top = (1920 - new_h) // 2
                    cropped = base_fit.crop((left, top, left + new_w, top + new_h))
                    img = cropped.resize((1080, 1920), Image.Resampling.LANCZOS)
                elif zoom < 1.0:
                    img = Image.new("RGBA", (1080, 1920), (10, 10, 12, 255))
                    fit_w, fit_h = int(1080 * zoom), int(1920 * zoom)
                    scaled = base_fit.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
                    img.paste(scaled, (540 - fit_w//2, 960 - fit_h//2))
                else:
                    img = base_fit
            else: img = Image.new("RGBA", (1080, 1920), (20, 20, 25, 255))
            
            draw = ImageDraw.Draw(img)
            
            opacity = int(self.box_opacity_slider.get())
            c_box = (*self.hex_to_rgb(self.cfg.get("box_color", "#6E1414")), opacity)
            c_head, c_sub, c_txt = self.hex_to_rgb(self.cfg.get("header_txt_color", "#FFFFFF")), self.hex_to_rgb(self.cfg.get("sub_txt_color", "#C8C8C8")), self.hex_to_rgb(self.cfg.get("box_txt_color", "#FFFFFF"))

            header_y = 60
            if os.path.exists(self.cfg.get("logo_path", "logo.png")):
                l_s = int(self.logo_size_slider.get())
                logo = ImageOps.contain(Image.open(self.cfg.get("logo_path", "logo.png")).convert("RGBA"), (l_s, l_s))
                img.paste(logo, (540 - (logo.width//2), 30), logo)
                header_y = 30 + l_s + 30 
            
            h_text = self.header_entry.get().upper()
            h_size = int(self.header_size_slider.get())
            h_font = self.get_f_path(h_size)
            h_chars = max(10, int(980 / (h_size * 0.6)))
            for line in textwrap.wrap(h_text, width=h_chars):
                draw.text((540, header_y), line, fill=c_head, font=h_font, anchor="mt")
                header_y += h_size + 15
                
            s_text = self.header_sub_entry.get().upper()
            s_size = int(self.header_sub_size_slider.get())
            s_font = self.get_f_path(s_size)
            s_chars = max(15, int(980 / (s_size * 0.5)))
            header_y += 10
            for line in textwrap.wrap(s_text, width=s_chars):
                draw.text((540, header_y), line, fill=c_sub, font=s_font, anchor="mt")
                header_y += s_size + 15

            checked = [item for item in self.days_ui_list if item["check"].get()]
            if checked:
                count = len(checked)
                available_space = 1920 - header_y - 80 
                
                is_stacked = count <= 3
                max_box_h = 450 if is_stacked else 250 
                calculated_box_h = int((available_space / count) * 0.85)
                box_h = min(max_box_h, calculated_box_h)
                
                spacing = min(40, int((available_space - (box_h * count)) / (count + 1))) if count > 1 else 0
                
                start_y = header_y + 40
                total_drawn_h = (box_h * count) + (spacing * (count - 1))
                if total_drawn_h < available_space:
                    start_y += (available_space - total_drawn_h) // 2

                overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
                draw_overlay = ImageDraw.Draw(overlay)

                for idx, item in enumerate(checked):
                    y = start_y + (idx * (box_h + spacing))
                    draw_overlay.rounded_rectangle([80, y, 1000, y + box_h], 30, fill=c_box)

                img = Image.alpha_composite(img, overlay)
                draw = ImageDraw.Draw(img) 

                if is_stacked:
                    game_f = self.get_f_path(min(45, int(box_h * 0.12)))
                    game_f_size = min(45, int(box_h * 0.12))
                    sub_f = self.get_f_path(min(32, int(box_h * 0.08)))
                    sub_f_size = min(32, int(box_h * 0.08))
                    day_f = self.get_f_path(min(38, int(box_h * 0.10)))
                    day_f_size = min(38, int(box_h * 0.10))
                else:
                    day_f = self.get_f_path(min(65, int(box_h * 0.30)))
                    time_f = self.get_f_path(min(28, int(box_h * 0.14)))
                    game_f = self.get_f_path(min(40, int(box_h * 0.22)))
                    game_f_size = min(40, int(box_h * 0.22))
                    sub_f = self.get_f_path(min(28, int(box_h * 0.15)))
                    sub_f_size = min(28, int(box_h * 0.15))

                for idx, item in enumerate(checked):
                    y = start_y + (idx * (box_h + spacing))
                    
                    if is_stacked:
                        art_margin = 25
                        art_h = int(box_h * 0.45)
                        art_w = int(art_h * 0.75)
                        art_x = 540 - (art_w // 2)
                        art_y = y + art_margin

                        if item["code"] in self.art_cache:
                            art = ImageOps.fit(Image.open(self.art_cache[item["code"]]), (art_w, art_h))
                            mask = Image.new("L", (art_w, art_h), 0)
                            ImageDraw.Draw(mask).rounded_rectangle([0, 0, art_w, art_h], 15, 255)
                            img.paste(art, (art_x, art_y), mask)

                        gy = art_y + art_h + 20
                        g_val = item["game"].get().strip().upper()
                        g_lines = textwrap.wrap(g_val, width=45) if g_val else []
                        for line in g_lines[:2]:
                            draw.text((540, gy), line, fill=c_txt, font=game_f, anchor="mt")
                            gy += game_f_size + 8

                        s_val = item["sub"].get().strip()
                        if s_val:
                            gy += 5
                            s_lines = textwrap.wrap(s_val, width=55)
                            for line in s_lines[:2]:
                                draw.text((540, gy), line, fill=c_sub, font=sub_f, anchor="mt")
                                gy += sub_f_size + 8

                        gy += 15
                        dual_t = self.get_converted_time(item['time'].get(), self.my_zone.get(), self.sec_zone.get())
                        draw.text((540, gy), f"{item['code']}  |  {dual_t}", fill=c_txt, font=day_f, anchor="mt")

                    else:
                        draw.text((120, y + (box_h * 0.35)), item["code"], fill=c_txt, font=day_f, anchor="lm")
                        dual_t = self.get_converted_time(item['time'].get(), self.my_zone.get(), self.sec_zone.get())
                        draw.text((120, y + (box_h * 0.75)), dual_t, fill=c_sub, font=time_f, anchor="lm")

                        art_margin = 20
                        art_h = box_h - (art_margin * 2)
                        art_w = int(art_h * 0.75) 
                        art_x = 1000 - art_margin - art_w
                        
                        if item["code"] in self.art_cache:
                            art = ImageOps.fit(Image.open(self.art_cache[item["code"]]), (art_w, art_h))
                            mask = Image.new("L", (art_w, art_h), 0)
                            ImageDraw.Draw(mask).rounded_rectangle([0, 0, art_w, art_h], 15, 255)
                            img.paste(art, (art_x, y + art_margin), mask)

                        text_x = 330 
                        max_text_w = art_x - text_x - 30
                        
                        g_val = item["game"].get().strip().upper()
                        g_lines = textwrap.wrap(g_val, width=max(12, int(max_text_w / (game_f_size * 0.55)))) if g_val else []
                        
                        s_val = item["sub"].get().strip()
                        s_lines = textwrap.wrap(s_val, width=max(15, int(max_text_w / (sub_f_size * 0.50)))) if s_val else []
                        
                        total_text_h = len(g_lines) * (game_f_size + 8)
                        if s_lines: total_text_h += 10 + (len(s_lines) * (sub_f_size + 8))
                        
                        gy = y + (box_h // 2) - (total_text_h // 2)
                        
                        for line in g_lines:
                            draw.text((text_x, gy), line, fill=c_txt, font=game_f)
                            gy += game_f_size + 8
                            
                        if s_lines:
                            gy += 10 
                            for line in s_lines:
                                draw.text((text_x, gy), line, fill=c_sub, font=sub_f)
                                gy += sub_f_size + 8

            p_ready = ctk.CTkImage(light_image=img, dark_image=img, size=(int(750*(1080/1920)), 750))
            self.preview_label.configure(image=p_ready, text="")
            img.convert("RGB").save("schedule_final.jpg", quality=95)
        except Exception as e: self.log(f"Renderer Note: {e}")

    # --- DEPLOY ENGINE ---
    def start_deploy(self): threading.Thread(target=lambda: asyncio.run(self.run_engine()), daemon=True).start()
    async def run_engine(self):
        self.log("🚀 Starting Global Deployment...")
        self.generate_preview_image()
        time.sleep(1.5)

        webhook_url = self.cfg.get('webhook', '').strip()
        if webhook_url:
            last_msg = self.cfg.get("last_msg_id", "")
            if last_msg:
                try:
                    self.log("🗑️ Deleting previous schedule from Discord...")
                    requests.delete(f"{webhook_url}/messages/{last_msg}", timeout=10)
                except Exception as e:
                    self.log("⚠️ Could not delete old message (it may have been deleted manually).")

        discord_msg = self.get_discord_header() + "\n\n"
        base_dt = datetime.datetime.strptime(self.date_menu.get(), "%Y-%m-%d")

        has_ticked_days = False
        for i, code in enumerate(self.all_days):
            item = self.days_ui_list[i]
            if item["check"].get():
                has_ticked_days = True
                try:
                    h, m = map(int, item['time'].get().split(':'))
                    event_dt = (base_dt + datetime.timedelta(days=i)).replace(hour=h, minute=m)
                    primary_tz_str = self.tz_map.get(self.my_zone.get(), "Europe/London")
                    local_tz = pytz.timezone(primary_tz_str)
                    localized_dt = local_tz.localize(event_dt)
                    unix_ts = int(localized_dt.timestamp())
                    sub_str = f" | {item['sub'].get()}" if item['sub'].get().strip() else ""
                    discord_msg += f"- `{self.full_days[code]}` - **{item['game'].get()}{sub_str}** <t:{unix_ts}:t>\n"
                except: discord_msg += f"- `{self.full_days[code]}` - **{item['game'].get()}** (Time Error)\n"
        
        if not has_ticked_days:
            discord_msg += "No streams scheduled for this week!"

        if webhook_url:
            try:
                with open("schedule_final.jpg", "rb") as f:
                    response = requests.post(webhook_url + "?wait=true", data={"content": discord_msg}, files={"file": f}, timeout=15)
                    if response.status_code in [200, 204]:
                        msg_data = response.json()
                        self.cfg["last_msg_id"] = msg_data.get("id", "")
                        with open(self.settings_path, "w") as jf:
                            json.dump(self.cfg, jf, indent=4)
                        self.log("🏁 Discord: Successfully Uploaded and ID Saved.")
                    else:
                        self.log(f"⚠️ Discord Uploaded, but failed to retrieve ID (Code: {response.status_code}).")
            except Exception as e:
                self.log(f"❌ Discord: Webhook Error: {e}")

        if self.cfg.get('t_tok'):
            self.log("🛰️ Syncing Twitch schedule...")
            try:
                api = await Twitch(self.cfg['t_id'], self.cfg['t_sec'])
                api.auto_refresh_auth = False 
                await api.set_user_authentication(self.cfg['t_tok'], [AuthScope.CHANNEL_MANAGE_SCHEDULE], None)
                user = await first(api.get_users())
                primary_tz_str = self.tz_map.get(self.my_zone.get(), "Europe/London")
                for i, item in enumerate(self.days_ui_list):
                    if item["check"].get() and item["game"].get() != "Game...":
                        h, m = map(int, item['time'].get().split(':'))
                        start_dt = (base_dt + datetime.timedelta(days=i)).replace(hour=h, minute=m)
                        sub_str = f" | {item['sub'].get()}" if item['sub'].get().strip() else ""
                        await api.create_channel_stream_schedule_segment(broadcaster_id=user.id, start_time=start_dt, timezone=primary_tz_str, duration='240', is_recurring=False, category_id=self.game_ids.get(item["game"].get()), title=f"{item['game'].get()}{sub_str}")
                self.log("✅ Twitch Dashboard: SYNCED.")
            except Exception as e: self.log(f"❌ Twitch Error: {e}")

    def refresh_status(self):
        t_id = len(self.cfg.get("t_id", "")) > 5
        t_tok = len(self.cfg.get("t_tok", "")) > 10
        disc = "discord.com" in self.cfg.get("webhook", "").lower()
        self.st_twitch_api.configure(text=f"● Twitch Keys: {'READY' if t_id else 'MISSING'}", text_color="#00FF00" if t_id else "#FF3333")
        self.st_twitch_tok.configure(text=f"● Access Token: {'ACTIVE' if t_tok else 'MISSING'}", text_color="#00FF00" if t_tok else "#FF3333")
        self.st_discord.configure(text=f"● Discord Webhook: {'READY' if disc else 'MISSING'}", text_color="#00FF00" if disc else "#FF3333")

    def setup_settings_tab(self):
        f = self.tab_settings; f.grid_columnconfigure(0, weight=1); f.grid_columnconfigure(1, weight=1)
        
        in_f = ctk.CTkFrame(f); in_f.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(in_f, text="CONNECTION HUB", font=("Arial", 22, "bold")).pack(pady=10)
        
        self.set_id = self.create_set(in_f, "1. Twitch Client ID", self.cfg.get("t_id", "")); self.set_id.bind("<KeyRelease>", self.update_auth_link)
        self.set_sec = self.create_set(in_f, "2. Twitch Client Secret", self.cfg.get("t_sec", ""))
        
        ctk.CTkLabel(in_f, text="3. Generate & Extract Token", font=("Arial", 14, "bold")).pack(pady=(15,0))
        self.link_display = ctk.CTkLabel(in_f, text="Enter Client ID first...", font=("Arial", 10), wraplength=400, text_color="cyan")
        self.link_display.pack(pady=5); self.update_auth_link()
        
        ctk.CTkButton(in_f, text="🌐 OPEN AUTH LINK", fg_color="#6441a5", command=lambda: webbrowser.open(self.link_display.cget("text"))).pack(pady=5)
        self.url_paste = self.create_set(in_f, "PASTE BROKEN URL HERE...", "")
        ctk.CTkButton(in_f, text="📥 EXTRACT TOKEN", command=self.extract_token).pack(pady=5)
        
        self.set_tok = self.create_set(in_f, "Current Access Token", self.cfg.get("t_tok", ""))
        self.set_webhook = self.create_set(in_f, "Discord Webhook URL", self.cfg.get("webhook", ""))
        
        ctk.CTkButton(in_f, text="💾 SAVE ALL SETTINGS", fg_color="green", height=50, command=self.save_settings).pack(pady=20)
        
        st_f = ctk.CTkFrame(in_f, fg_color="#1a1a1a", corner_radius=10); st_f.pack(fill="x", padx=40, pady=10)
        self.st_twitch_api = ctk.CTkLabel(st_f, text="● Checking..."); self.st_twitch_api.pack(anchor="w", padx=20, pady=(10,0))
        self.st_twitch_tok = ctk.CTkLabel(st_f, text="● Checking..."); self.st_twitch_tok.pack(anchor="w", padx=20)
        self.st_discord = ctk.CTkLabel(st_f, text="● Checking..."); self.st_discord.pack(anchor="w", padx=20, pady=(0,10))

        hp_f = ctk.CTkScrollableFrame(f, label_text="📘 SYSTEM SETUP GUIDE")
        hp_f.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.add_manual(hp_f, "Step 1: Get Twitch API Keys", 
                        "1. Go to the Twitch Dev Console.\n2. Click 'Register Your Application'.\n3. Set OAuth Redirect URL EXACTLY to: http://localhost:17563\n4. Set Category to 'Application Integration'.\n5. Hit create, then COPY your Client ID and GENERATE A NEW SECRET.\n\n⚠️ IMPORTANT: You MUST copy the Client Secret before closing the page, or Twitch will hide it forever!", 
                        "https://dev.twitch.tv/console")
        
        self.add_manual(hp_f, "Step 2: Link Your Account", 
                        "1. Paste your new Client ID on the left.\n2. Click 'OPEN AUTH LINK' and hit Authorize.\n3. Your browser will show a 'Refused to Connect' error—this is totally normal!\n4. COPY the entire long URL from the address bar.\n5. Paste it into the 'PASTE BROKEN URL' box and click EXTRACT.", 
                        None)
        
        self.add_manual(hp_f, "Step 3: Discord Webhooks", 
                        "Go to your Discord Server Settings > Integrations > Webhooks. Create a new webhook for your schedule channel, copy the URL, and paste it on the left.", 
                        "https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks")
        
        self.add_manual(hp_f, "Step 4: Smart Deployment", 
                        "When you hit DEPLOY on the Planner tab, the app will automatically delete last week's schedule from Discord, post the new one with localized Unix timestamps, and push the segments directly to your Twitch Dashboard.", 
                        None)

    def setup_planner_tab(self):
        p = ctk.CTkFrame(self.tab_planner); p.pack(fill="both", expand=True)
        side = ctk.CTkScrollableFrame(p, width=320, label_text="VISUAL DESIGN"); side.pack(side="left", fill="y", padx=10, pady=10)
        
        self.header_entry = ctk.CTkEntry(side); self.header_entry.pack(fill="x", padx=10, pady=5); self.header_entry.insert(0, self.cfg.get("header_text", "STREAMER SCHEDULE")); self.header_entry.bind("<KeyRelease>", lambda e: self.generate_preview_image())
        self.apply_right_click(self.header_entry)
        
        self.date_menu = ctk.CTkOptionMenu(side, values=self.get_upcoming_dates("MON"), command=self.on_date_select); self.date_menu.pack(fill="x", padx=10, pady=5)
        
        self.header_sub_entry = ctk.CTkEntry(side); self.header_sub_entry.pack(fill="x", padx=10, pady=5); self.header_sub_entry.insert(0, self.cfg.get("header_sub", "PICK DATE ABOVE")); self.header_sub_entry.bind("<KeyRelease>", lambda e: self.generate_preview_image())
        self.apply_right_click(self.header_sub_entry)
        
        self.header_size_slider = self.add_slider(side, "Header Size", "header_size", 50, 150)
        self.header_sub_size_slider = self.add_slider(side, "Date Size", "sub_size", 20, 80)
        self.logo_size_slider = self.add_slider(side, "Logo Size", "logo_size", 100, 500)
        self.bg_zoom_slider = self.add_slider(side, "Background Zoom %", "bg_zoom", 25, 300)
        self.box_opacity_slider = self.add_slider(side, "Box Transparency", "box_opacity", 0, 255)
        
        fonts = ["Arial Black", "Impact", "Segoe UI Bold", "Verdana Bold", "Tahoma Bold", "Trebuchet MS", "Courier New", "Comic Sans MS", "Georgia Bold", "Calibri Bold", "Times New Roman Bold", "Lucida Console"]
        self.font_menu = ctk.CTkOptionMenu(side, values=fonts, command=lambda c: self.generate_preview_image()); self.font_menu.pack(pady=5); self.font_menu.set(self.cfg.get("font", "Arial Black"))
        
        self.my_zone = ctk.CTkOptionMenu(side, values=list(self.tz_map.keys()), command=lambda c: self.generate_preview_image()); self.my_zone.pack(pady=2); self.my_zone.set(self.cfg.get("my_zone", "UK (GMT/BST)"))
        self.sec_zone = ctk.CTkOptionMenu(side, values=list(self.sec_tz_map.keys()), command=lambda c: self.generate_preview_image()); self.sec_zone.pack(pady=2); self.sec_zone.set(self.cfg.get("sec_zone", "US East (EST/EDT)"))
        
        ctk.CTkButton(side, text="Box Color", command=lambda: self.pick_color_generic("box_color")).pack(pady=2)
        ctk.CTkButton(side, text="📁 Background", command=self.pick_bg).pack(pady=2)
        ctk.CTkButton(side, text="🖼️ Logo", command=self.pick_logo).pack(pady=2)
        self.deploy_btn = ctk.CTkButton(side, text="🚀 DEPLOY", height=60, fg_color="#801010", font=("Arial", 20, "bold"), command=self.start_deploy); self.deploy_btn.pack(side="bottom", pady=20)
        
        scroll = ctk.CTkScrollableFrame(p, label_text="TICK DAYS"); scroll.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.days_ui_list = []
        time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
        
        for i in range(7):
            df = ctk.CTkFrame(scroll); df.pack(pady=5, fill="x")
            chk = ctk.CTkCheckBox(df, text="", width=20, command=self.generate_preview_image); chk.grid(row=0, column=0, padx=2)
            lbl = ctk.CTkLabel(df, text=self.all_days[i], width=50, font=("Arial", 12, "bold")); lbl.grid(row=0, column=1)
            g_wrap = ctk.CTkFrame(df, fg_color="transparent"); g_wrap.grid(row=0, column=2, padx=5)
            
            gm = ctk.CTkEntry(g_wrap, width=220, placeholder_text="Game..."); gm.pack(); gm.bind("<KeyRelease>", lambda e, idx=i: self.on_key_release(e, idx))
            self.apply_right_click(gm)
            
            s_f = ctk.CTkFrame(g_wrap, height=0, fg_color="#222"); s_f.pack(fill="x")
            
            sub = ctk.CTkEntry(df, placeholder_text="Sub...", width=140); sub.grid(row=0, column=3, padx=5); sub.bind("<KeyRelease>", lambda e: self.generate_preview_image())
            self.apply_right_click(sub)
            
            tm = ctk.CTkOptionMenu(df, values=time_options, width=80, command=lambda e: self.generate_preview_image()); tm.grid(row=0, column=4, padx=5); tm.set("20:00")
            self.days_ui_list.append({"check": chk, "game": gm, "sub": sub, "time": tm, "suggest": s_f, "code": self.all_days[i]})
            
        self.preview_label = ctk.CTkLabel(p, text="Preview...", width=400, height=750, fg_color="#111"); self.preview_label.pack(side="right", padx=10)

    # --- UTILS ---
    def select_game(self, idx, val, gid):
        self.days_ui_list[idx]["game"].delete(0, 'end'); self.days_ui_list[idx]["game"].insert(0, val); self.game_ids[val] = gid
        self.hide_all_suggest(); self.focus(); threading.Thread(target=lambda: asyncio.run(self.up_art(val, self.days_ui_list[idx]["code"])), daemon=True).start()
    
    def save_settings(self):
        self.cfg.update({"webhook":self.set_webhook.get(),"t_id":self.set_id.get(),"t_sec":self.set_sec.get(),"t_tok":self.set_tok.get(),"header_text":self.header_entry.get(),"header_sub":self.header_sub_entry.get(),"header_size":self.header_size_slider.get(),"sub_size":self.header_sub_size_slider.get(),"logo_size":self.logo_size_slider.get(),"bg_zoom":self.bg_zoom_slider.get(),"box_opacity":self.box_opacity_slider.get(),"font":self.font_menu.get(),"my_zone":self.my_zone.get(),"sec_zone":self.sec_zone.get()})
        with open(self.settings_path, "w") as f: json.dump(self.cfg, f, indent=4)
        self.refresh_status(); messagebox.showinfo("Success", "Settings Saved Securely to Windows Vault!"); self.generate_preview_image()
    
    def get_upcoming_dates(self, start_day):
        dates = []; today = datetime.date.today()
        target_idx = self.all_days.index(start_day)
        last_start = today - datetime.timedelta(days=(today.weekday() - target_idx) % 7)
        for i in range(4): dates.append((last_start + datetime.timedelta(weeks=i)).strftime("%Y-%m-%d"))
        return dates

    def pick_color_generic(self, key):
        c = colorchooser.askcolor(initialcolor=self.cfg.get(key, "#FFFFFF"))
        if c[1]: self.cfg[key] = c[1]; self.generate_preview_image()

    def hex_to_rgb(self, hex_color):
        try: return tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except: return (255, 255, 255)

    def add_slider(self, p, lbl, key, start, end):
        ctk.CTkLabel(p, text=lbl).pack(); s = ctk.CTkSlider(p, from_=start, to=end, command=lambda e: self.generate_preview_image()); s.pack(fill="x", padx=10); s.set(self.cfg.get(key, start)); return s

    def create_set(self, p, lbl, val):
        ctk.CTkLabel(p, text=lbl).pack()
        e = ctk.CTkEntry(p, width=400)
        e.pack(pady=5)
        if val: e.insert(0, val)
        self.apply_right_click(e)
        return e

    def add_manual(self, p, t, d, u):
        ctk.CTkLabel(p, text=t, font=("Arial", 16, "bold"), text_color="#D11111").pack(pady=(15,0), anchor="w"); ctk.CTkLabel(p, text=d, wraplength=400, justify="left").pack(anchor="w")
        if u: ctk.CTkButton(p, text="🔗 Help Link", height=24, command=lambda u=u: webbrowser.open(u)).pack(pady=5, anchor="w")

    def on_key_release(self, e, idx):
        d_code = self.days_ui_list[idx]["code"]
        if d_code in self.search_timers: self.search_timers[d_code].cancel()
        self.search_timers[d_code] = threading.Timer(0.5, lambda: asyncio.run(self.fetch_sugg(idx))); self.search_timers[d_code].start()

    async def fetch_sugg(self, idx):
        q = self.days_ui_list[idx]["game"].get()
        if len(q) < 3: return
        try:
            api = await Twitch(self.cfg['t_id'].strip(), self.cfg['t_sec'].strip())
            res = []; [res.append(g) async for g in api.search_categories(q)]
            if res: self.after(0, lambda: self.show_suggest(idx, res[:5]))
        except: pass

    def show_suggest(self, idx, res):
        self.hide_all_suggest(); f = self.days_ui_list[idx]["suggest"]; f.configure(height=150)
        for r in res: ctk.CTkButton(f, text=r.name, fg_color="transparent", anchor="w", height=28, command=lambda v=r.name, gid=r.id, i=idx: self.select_game(i, v, gid)).pack(fill="x")

    def pick_bg(self):
        p = filedialog.askopenfilename()
        if p: self.cfg["bg_path"] = p; self.generate_preview_image()

    def pick_logo(self):
        p = filedialog.askopenfilename()
        if p: self.cfg["logo_path"] = p; self.generate_preview_image()

    async def up_art(self, c, d):
        try:
            api = await Twitch(self.cfg['t_id'].strip(), self.cfg['t_sec'].strip())
            g = await first(api.get_games(names=[c]))
            if g:
                r = requests.get(g.box_art_url.replace("{width}","300").replace("{height}","400"))
                with open(f"cache_{d}.png", "wb") as f: f.write(r.content)
                self.art_cache[d] = f"cache_{d}.png"; self.after(0, self.generate_preview_image)
        except: pass

    def get_f_path(self, size):
        f_map = {
            "Arial Black": "ariblk.ttf", "Impact": "impact.ttf", "Segoe UI Bold": "segoeuib.ttf", 
            "Tahoma Bold": "tahomabd.ttf", "Trebuchet MS": "trebucbd.ttf", "Courier New": "courbd.ttf", 
            "Comic Sans MS": "comicbd.ttf", "Georgia Bold": "georgiab.ttf", "Calibri Bold": "calibrib.ttf", 
            "Times New Roman Bold": "timesbd.ttf", "Lucida Console": "lucon.ttf", "Verdana Bold": "verdanab.ttf"
        }
        path = os.path.join(os.environ['WINDIR'], 'Fonts', f_map.get(self.font_menu.get(), "arialbd.ttf"))
        return ImageFont.truetype(path if os.path.exists(path) else "arialbd.ttf", size)

    def on_date_select(self, choice):
        sd = datetime.datetime.strptime(choice, "%Y-%m-%d")
        ed = sd + datetime.timedelta(days=6)
        self.header_sub_entry.delete(0, 'end'); self.header_sub_entry.insert(0, f"{sd.strftime('%B %d')} - {ed.strftime('%B %d')}".upper()); self.generate_preview_image()

    def check_first_run(self):
        if not self.cfg.get("t_id") or not self.cfg.get("t_tok"):
            messagebox.showinfo("Welcome to Simph Studio!", "Welcome! To get started, please head over to the '⚙️ APP SETTINGS' tab.\n\nYou'll need to link your Twitch Account and Discord Webhook using the Setup Guide on the right before you can deploy schedules. You only have to do this once!")

if __name__ == "__main__":
    app = SimphStudio(); app.mainloop()