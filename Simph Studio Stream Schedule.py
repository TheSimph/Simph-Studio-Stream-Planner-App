import customtkinter as ctk
import tkinter as tk
import json, datetime, time, os, textwrap, re, requests, asyncio, pytz, webbrowser, shutil, calendar, math, random
from PIL import Image, ImageDraw, ImageFont, ImageOps
from tkinter import filedialog, messagebox, colorchooser
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.type import AuthScope
import threading
import sys
import zipfile
import subprocess

class SimphStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- UPDATE SETTINGS ---
        self.APP_VERSION = "0.1.14"
        self.REPO_NAME = "Simph-Studio-Stream-Planner-App"
        self.UPDATE_URL = f"https://raw.githubusercontent.com/TheSimph/{self.REPO_NAME}/main/version.txt"
        self.RELEASE_URL = f"https://github.com/TheSimph/{self.REPO_NAME}/releases/latest"
        self.API_LATEST_URL = f"https://api.github.com/repos/TheSimph/{self.REPO_NAME}/releases/latest"

        self.title(f"Simph Studio - Ver {self.APP_VERSION}")
        self.geometry("1650x1000")
        ctk.set_appearance_mode("dark")
        
        # --- TASKBAR & WINDOW ICON FIX ---
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"simph.studio.app.{self.APP_VERSION}")
        except: pass
        
        icon_path = self.get_resource_path("logo.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except: pass
        elif getattr(sys, 'frozen', False):
            try: self.iconbitmap(sys.executable)
            except: pass
        
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
        self._preview_timer = None 
        self._resize_timer = None
        self.selected_start_date = datetime.date.today()
        
        # --- CLEANED CANVAS RATIOS ---
        self.ratios = {
            "9:16 (TikTok/Reels/Shorts)": (1080, 1920),
            "16:9 (Desktop/YouTube)": (1920, 1080),
            "1:1 (Square/Instagram)": (1080, 1080),
            "4:5 (Vertical Post)": (1080, 1350)
        }

        # --- MASSIVE FONT DICTIONARY ---
        self.font_map = {
            "Arial": "arial.ttf", "Arial Black": "ariblk.ttf", "Bahnschrift": "bahnschrift.ttf",
            "Bookman Old Style": "bookosb.ttf", "Calibri": "calibri.ttf", "Calibri Bold": "calibrib.ttf",
            "Cambria": "cambria.ttf", "Candara": "candara.ttf", "Candara Bold": "candarab.ttf",
            "Century Gothic": "gothicb.ttf", "Comic Sans MS": "comic.ttf", "Comic Sans MS Bold": "comicbd.ttf",
            "Consolas": "consola.ttf", "Constantia Bold": "constanb.ttf", "Corbel Bold": "corbelb.ttf",
            "Courier New": "cour.ttf", "Courier New Bold": "courbd.ttf", "Franklin Gothic": "framd.ttf",
            "Garamond": "gara.ttf", "Garamond Bold": "garabd.ttf", "Georgia": "georgia.ttf",
            "Georgia Bold": "georgiab.ttf", "Impact": "impact.ttf", "Lucida Console": "lucon.ttf",
            "Palatino Linotype": "pala.ttf", "Segoe Script": "segoesc.ttf", "Segoe UI": "segoeui.ttf",
            "Segoe UI Bold": "segoeuib.ttf", "Tahoma": "tahoma.ttf", "Tahoma Bold": "tahomabd.ttf",
            "Times New Roman": "times.ttf", "Times New Roman Bold": "timesbd.ttf",
            "Trebuchet MS": "trebuc.ttf", "Trebuchet MS Bold": "trebucbd.ttf",
            "Verdana": "verdana.ttf", "Verdana Bold": "verdanab.ttf"
        }
        
        # --- TIMEZONE DICTIONARIES ---
        self.tz_map = {
            "UK (GMT/BST)": "Europe/London", "US East (EST/EDT)": "US/Eastern", "US Central (CST/CDT)": "US/Central",
            "US Mountain (MST/MDT)": "US/Mountain", "US Pacific (PST/PDT)": "US/Pacific", 
            "Europe Central (CET/CEST)": "Europe/Berlin", "Australia (AEST/AEDT)": "Australia/Sydney", "UTC": "UTC"
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
        self.update_date_displays()
        
        self.console = ctk.CTkTextbox(self, height=120, font=("Consolas", 12))
        self.console.pack(padx=20, pady=(0, 20), fill="x")
        self.apply_right_click(self.console)
        
        self.bind("<Button-1>", lambda e: self.hide_all_suggest())
        
        self.tabs.set("⚙️ APP SETTINGS")
        self.schedule_preview()
        self.after(1000, self.check_first_run)
        self.after(1200, self.refresh_status)
        self.after(2000, self.check_for_updates)

    def get_resource_path(self, relative_path):
        try: base_path = sys._MEIPASS
        except Exception: base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def log(self, text):
        self.console.insert("end", f"> {text}\n")
        self.console.see("end")

    def load_settings(self):
        local_old = "settings.json"
        if os.path.exists(local_old):
            try: shutil.copy(local_old, self.settings_path); os.remove(local_old)
            except: pass
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r") as f: return json.load(f)
            except: pass
        return {
            "webhook": "", "t_id": "", "t_sec": "", "t_tok": "", "last_msg_id": "",
            "font": "Arial Black", "box_color": "#6E1414", "bg_zoom": 100, "box_opacity": 240,
            "header_txt_color": "#FFFFFF", "sub_txt_color": "#C8C8C8", "box_txt_color": "#FFFFFF",
            "header_text": "STREAMER SCHEDULE", "header_size": 100, "sub_size": 40, "logo_size": 200,
            "my_zone": "UK (GMT/BST)", "sec_zone": "US East (EST/EDT)", "start_day": "MON",
            "canvas_format": "9:16 (TikTok/Reels/Shorts)", "max_box_h": 250, "time_fmt": "24-Hour (20:00)", "show_primary": True,
            "sponsor_title": "", "goal_current": "", "goal_target": "", "sponsor_path": ""
        }

    def schedule_preview(self, *args):
        if self._preview_timer: self.after_cancel(self._preview_timer)
        self._preview_timer = self.after(200, self.generate_preview_image)

    # --- TRUE AUTO-UPDATER LOGIC WITH PYINSTALLER GHOST FIX ---
    def check_for_updates(self):
        self.log("🔍 Checking GitHub for updates...")
        def run_check():
            try:
                cb = f"?cb={random.randint(1, 999999)}"
                response = requests.get(self.UPDATE_URL + cb, timeout=5)
                if response.status_code == 200:
                    latest_v = response.text.strip()
                    if latest_v != self.APP_VERSION:
                        self.log(f"💡 Update found! (Ver {latest_v})")
                        self.after(0, lambda: self.show_update_popup(latest_v))
                    else:
                        self.log("✅ App is up to date.")
            except Exception as e: 
                self.log(f"❌ Update check failed: {e}")
        threading.Thread(target=run_check, daemon=True).start()

    def show_update_popup(self, new_v):
        msg = f"A new version of Simph Studio (Ver {new_v}) is available!\n\nWould you like to download and install it now? (The app will restart)."
        if messagebox.askyesno("Update Available", msg):
            self.perform_update()

    def perform_update(self):
        self.update_window = ctk.CTkToplevel(self)
        self.update_window.title("Updating...")
        self.update_window.geometry("350x150")
        self.update_window.attributes("-topmost", True)
        
        ctk.CTkLabel(self.update_window, text="Downloading update, please wait...", font=("Arial", 16)).pack(pady=20)
        self.progress = ctk.CTkProgressBar(self.update_window, mode="indeterminate")
        self.progress.pack(pady=10, padx=20, fill="x")
        self.progress.start()
        
        threading.Thread(target=self._download_and_apply_update, daemon=True).start()

    def _download_and_apply_update(self):
        try:
            self.log("🛰️ Querying GitHub API for latest release asset...")
            resp = requests.get(self.API_LATEST_URL).json()
            download_url = None
            
            for asset in resp.get("assets", []):
                if asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
            
            if not download_url:
                raise Exception("Could not find a .zip file in the latest GitHub release.")

            self.log(f"📥 Downloading: {download_url}")
            zip_path = os.path.join(self.appdata_dir, "update.zip")
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            self.log("📦 Extracting new files...")
            extract_dir = os.path.join(self.appdata_dir, "update_extracted")
            if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            if getattr(sys, 'frozen', False):
                self.log("🚀 Preparing Ghost Script...")
                current_exe = sys.executable
                exe_name = os.path.basename(current_exe)
                exe_dir = os.path.dirname(current_exe)
                new_exe_path = os.path.join(extract_dir, exe_name)
                
                if not os.path.exists(new_exe_path):
                    for root, dirs, files in os.walk(extract_dir):
                        if exe_name in files:
                            new_exe_path = os.path.join(root, exe_name)
                            break
                
                bat_path = os.path.join(self.appdata_dir, "update.bat")
                
                # --- MEMORY WIPE FIX ---
                # We clear _MEIPASS2 and TCL/TK vars so the newly launched .exe doesn't try to read the dead app's temporary files.
                bat_content = f"""@echo off
echo Installing new Simph Studio Update...
echo Please wait for the old application to close completely.
timeout /t 5 /nobreak > NUL
move /Y "{new_exe_path}" "{current_exe}"
cd /d "{exe_dir}"
set _MEIPASS2=
set TCL_LIBRARY=
set TK_LIBRARY=
start "" "{current_exe}"
rmdir /S /Q "{extract_dir}"
del "{zip_path}"
del "%~f0"
"""
                with open(bat_path, "w") as f: f.write(bat_content)
                
                os.startfile(bat_path)
                self.after(0, self.destroy)
            else:
                self.log("⚠️ Cannot auto-install while running as a .py script. Update downloaded to AppData.")
                self.after(0, self.update_window.destroy)

        except Exception as e:
            self.log(f"❌ Auto-Update failed: {e}")
            self.after(0, self.update_window.destroy)

    # --- HELP POPUPS ---
    def show_help_popup(self):
        msg = (
            "Welcome to the Streamer Schedule Planner!\n\n"
            "► LINK TWITCH: Go to 'App Settings' to link Twitch. This unlocks the game search dropdown and dynamic box art.\n"
            "► TICK DAYS: Use the checkboxes on the left to activate days you plan to stream.\n"
            "► MULTI-EXPORT: Tick the formats you want on the left. Deploying will save them all to a folder on your Desktop!\n"
            "► CUSTOM ART: Click the [🖼️] button next to any day to upload your own custom image instead of Twitch box art.\n"
            "► DEPLOY: Hitting deploy sends the preview image to Discord and updates your actual Twitch schedule automatically!"
        )
        messagebox.showinfo("Simph Studio User Guide", msg)

    def check_first_run(self):
        if not self.cfg.get("t_id") or not self.cfg.get("t_tok"):
            msg = (
                "Welcome to Simph Studio!\n\n"
                "It looks like you haven't linked your Twitch Account yet.\n\n"
                "To unlock official game searches and automatic box art on your schedule, please read the 📘 SYSTEM SETUP GUIDE in the 'APP SETTINGS' tab to get started!"
            )
            messagebox.showinfo("First Time Setup", msg)

    def apply_right_click(self, widget):
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activeborderwidth=0)
        menu.add_command(label="Cut", command=lambda: widget.focus() or widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.focus() or widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.focus() or widget.event_generate("<<Paste>>"))
        target = widget._entry if hasattr(widget, "_entry") else widget
        target.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def get_suffix(self, n):
        if 11 <= n <= 13: return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    def get_discord_header(self):
        try:
            sd = self.selected_start_date
            ed = sd + datetime.timedelta(days=6)
            return f"# __{sd.strftime('%b %d')}{self.get_suffix(sd.day)} - {ed.strftime('%b %d')}{self.get_suffix(ed.day)}__"
        except: return "# __Stream Schedule__"

    def update_auth_link(self, *args):
        cid = self.set_id.get().strip()
        link = f"https://id.twitch.tv/oauth2/authorize?client_id={cid}&redirect_uri=http://localhost:17563&response_type=token&scope=channel:manage:schedule"
        self.link_display.configure(text=link if len(cid) > 5 else "Enter Client ID first...")

    def extract_token(self):
        raw_url = self.url_paste.get().strip()
        match = re.search(r"access_token=([a-z0-9]+)", raw_url)
        if match:
            self.set_tok.delete(0, 'end'); self.set_tok.insert(0, match.group(1)); self.log(f"✅ Token Extracted!")
            messagebox.showinfo("Extraction Successful!", "Click 'SAVE ALL SETTINGS' at the bottom!")
        else: messagebox.showerror("Error", "URL invalid.")

    def hide_all_suggest(self):
        for item in self.days_ui_list:
            [c.destroy() for c in item["suggest"].winfo_children()]; item["suggest"].configure(height=0)

    def open_calendar(self):
        if hasattr(self, "cal_win") and self.cal_win.winfo_exists():
            self.cal_win.focus(); return
        self.cal_win = ctk.CTkToplevel(self); self.cal_win.title("Select Start Date")
        self.cal_win.geometry("320x350"); self.cal_win.attributes("-topmost", True); self.cal_win.resizable(False, False)
        self.cal_view_date = datetime.date.today().replace(day=1)
        self.build_cal_ui()

    def build_cal_ui(self):
        for widget in self.cal_win.winfo_children(): widget.destroy()
        header_f = ctk.CTkFrame(self.cal_win, fg_color="transparent"); header_f.pack(fill="x", pady=10, padx=10)
        ctk.CTkButton(header_f, text="<", width=40, command=lambda: self.change_month(-1)).pack(side="left")
        ctk.CTkLabel(header_f, text=self.cal_view_date.strftime("%B %Y"), font=("Arial", 16, "bold")).pack(side="left", expand=True)
        ctk.CTkButton(header_f, text=">", width=40, command=lambda: self.change_month(1)).pack(side="right")
        
        days_f = ctk.CTkFrame(self.cal_win, fg_color="transparent"); days_f.pack(fill="both", expand=True, padx=10)
        for i, d in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]): ctk.CTkLabel(days_f, text=d, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=5, pady=5)
            
        cal = calendar.monthcalendar(self.cal_view_date.year, self.cal_view_date.month)
        for row, week in enumerate(cal):
            for col, day in enumerate(week):
                if day != 0:
                    btn = ctk.CTkButton(days_f, text=str(day), width=35, height=35, fg_color="#333", command=lambda d=day: self.set_start_date(d))
                    btn.grid(row=row+1, column=col, padx=2, pady=2)
                    if datetime.date(self.cal_view_date.year, self.cal_view_date.month, day) == self.selected_start_date: btn.configure(fg_color="#00FF00", text_color="black")

    def change_month(self, delta):
        m = self.cal_view_date.month - 1 + delta
        y = self.cal_view_date.year + m // 12
        self.cal_view_date = datetime.date(y, m % 12 + 1, 1)
        self.build_cal_ui()

    def set_start_date(self, day):
        self.selected_start_date = datetime.date(self.cal_view_date.year, self.cal_view_date.month, day)
        self.update_date_displays(); self.cal_win.destroy(); self.schedule_preview()

    def update_date_displays(self):
        sd = self.selected_start_date
        ed = sd + datetime.timedelta(days=6)
        self.date_btn.configure(text=f"📅 Start Date: {sd.strftime('%Y-%m-%d')}")
        self.header_sub_entry.configure(state="normal")
        self.header_sub_entry.delete(0, 'end')
        self.header_sub_entry.insert(0, f"{sd.strftime('%B %d')} - {ed.strftime('%B %d')}".upper())

    def get_converted_time(self, time_str, from_zone_display, to_zone_display, show_primary):
        if time_str in ["TBA"]: return [time_str]
        try:
            f_tz = pytz.timezone(self.tz_map.get(from_zone_display, "Europe/London"))
            h, m = map(int, time_str.split(':'))
            now = datetime.datetime.now()
            loc_dt = f_tz.localize(datetime.datetime(now.year, now.month, now.day, h, m))
            
            fmt = '%I:%M %p' if "12" in self.time_fmt.get() else '%H:%M'
            base_time = loc_dt.strftime(fmt).lstrip('0')
            
            res = []
            if show_primary: res.append(f"{base_time} {loc_dt.strftime('%Z')}")
            
            if to_zone_display != "None (Hide)":
                tar_dt = loc_dt.astimezone(pytz.timezone(self.sec_tz_map.get(to_zone_display, "US/Eastern")))
                res.append(f"{tar_dt.strftime(fmt).lstrip('0')} {tar_dt.strftime('%Z')}")
                
            if not res: return [base_time] 
            return res
        except: return [time_str]

    def on_preview_resize(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self.prev_width = event.width
        self.prev_height = event.height
        self._resize_timer = self.after(200, self.schedule_preview)

    def render_schedule_image(self, target_format):
        sp_title = self.sponsor_title.get().strip() if hasattr(self, 'sponsor_title') else ""
        sp_cur_str = self.goal_current.get().strip() if hasattr(self, 'goal_current') else ""
        sp_tgt_str = self.goal_target.get().strip() if hasattr(self, 'goal_target') else ""
        sp_path = self.cfg.get("sponsor_path", "")
        
        has_goal = bool(sp_title or sp_cur_str or sp_tgt_str)
        has_logo = os.path.exists(sp_path)
        
        cw, ch = self.ratios.get(target_format, (1080, 1920))
        is_landscape = cw > ch
        
        if os.path.exists(self.cfg.get("bg_path", "background.jpg")):
            raw_bg = Image.open(self.cfg.get("bg_path", "background.jpg")).convert("RGBA")
            base_fit = ImageOps.fit(raw_bg, (cw, ch), method=Image.Resampling.LANCZOS)
            zoom = int(self.bg_zoom_slider.get()) / 100.0
            if zoom > 1.0:
                new_w, new_h = int(cw / zoom), int(ch / zoom)
                left, top = (cw - new_w) // 2, (ch - new_h) // 2
                img = base_fit.crop((left, top, left + new_w, top + new_h)).resize((cw, ch), Image.Resampling.LANCZOS)
            elif zoom < 1.0:
                img = Image.new("RGBA", (cw, ch), (10, 10, 12, 255))
                fit_w, fit_h = int(cw * zoom), int(ch * zoom)
                scaled = base_fit.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
                img.paste(scaled, (cw//2 - fit_w//2, ch//2 - fit_h//2))
            else: img = base_fit
        else: img = Image.new("RGBA", (cw, ch), (20, 20, 25, 255))
        
        draw = ImageDraw.Draw(img)
        opacity = int(self.box_opacity_slider.get())
        c_box = (*self.hex_to_rgb(self.cfg.get("box_color", "#6E1414")), opacity)
        c_head, c_sub, c_txt = self.hex_to_rgb(self.cfg.get("header_txt_color", "#FFFFFF")), self.hex_to_rgb(self.cfg.get("sub_txt_color", "#C8C8C8")), self.hex_to_rgb(self.cfg.get("box_txt_color", "#FFFFFF"))

        header_y = int(ch * 0.03)
        if os.path.exists(self.cfg.get("logo_path", "logo.png")):
            l_s = int(self.logo_size_slider.get())
            logo = ImageOps.contain(Image.open(self.cfg.get("logo_path", "logo.png")).convert("RGBA"), (l_s, l_s))
            img.paste(logo, (cw//2 - (logo.width//2), header_y), logo)
            header_y += l_s + 20 
        
        h_text, h_size = self.header_entry.get().upper(), int(self.header_size_slider.get())
        for line in textwrap.wrap(h_text, width=max(8, int((cw*0.85) / (h_size * 0.7)))):
            draw.text((cw//2, header_y), line, fill=c_head, font=self.get_f_path(h_size), anchor="mt")
            header_y += h_size + 15
            
        s_text, s_size = self.header_sub_entry.get().upper(), int(self.header_sub_size_slider.get())
        header_y += 10
        for line in textwrap.wrap(s_text, width=max(12, int((cw*0.85) / (s_size * 0.55)))):
            draw.text((cw//2, header_y), line, fill=c_sub, font=self.get_f_path(s_size), anchor="mt")
            header_y += s_size + 15

        checked = [item for item in self.days_ui_list if item["check"].get()]
        if checked:
            count = len(checked)
            bottom_padding = 150 if (sp_title or sp_cur_str or sp_tgt_str or os.path.exists(sp_path)) else 60
            
            available_space = max(10, ch - header_y - bottom_padding)
            
            positions = [] 
            if is_landscape and count > 3:
                cols = 2
                items_per_col = math.ceil(count / 2)
                if count % 2 != 0: 
                    left_items = (count - 1) // 2
                    for idx in range(count):
                        if idx < left_items: positions.append((0, idx))
                        elif idx < count - 1: positions.append((1, idx - left_items))
                        else: positions.append((0.5, items_per_col - 1))
                else:
                    left_items = count // 2
                    for idx in range(count):
                        if idx < left_items: positions.append((0, idx))
                        else: positions.append((1, idx - left_items))
            else:
                cols = 1
                items_per_col = count
                for idx in range(count):
                    positions.append((0, idx))
            
            max_allowed = int(self.max_box_slider.get())
            calc_h = int((available_space / items_per_col) * 0.85)
            box_h = max(10, min(max_allowed, calc_h)) 
            
            spacing = min(40, int((available_space - (box_h * items_per_col)) / (items_per_col + 1))) if items_per_col > 1 else 0
            start_y = header_y + 30
            total_drawn_h = (box_h * items_per_col) + (spacing * (items_per_col - 1))
            if total_drawn_h < available_space: start_y += (available_space - total_drawn_h) // 2

            col_w = (cw - 120) // cols if cols > 1 else (cw - 160)
            box_w = col_w - 40 if cols > 1 else col_w

            overlay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            for idx, item in enumerate(checked):
                c, r = positions[idx]
                box_x = int(80 + (c * col_w))
                if cols > 1 and c == 0.5: box_x = (cw - box_w) // 2
                y = int(start_y + (r * (box_h + spacing)))
                
                is_off = item['offline'].get()
                fill_c = (70, 70, 70, opacity) if is_off else c_box
                draw_overlay.rounded_rectangle([box_x, y, box_x + box_w, y + box_h], 30, fill=fill_c)
                
            img = Image.alpha_composite(img, overlay); draw = ImageDraw.Draw(img) 

            day_f = self.get_f_path(min(65, int(box_h * 0.30))); day_f_size = min(65, int(box_h * 0.30))
            time_f = self.get_f_path(min(30, int(box_h * 0.15))); time_f_size = min(30, int(box_h * 0.15))
            game_f = self.get_f_path(min(45, int(box_h * 0.22))); game_f_size = min(45, int(box_h * 0.22))
            sub_f = self.get_f_path(min(38, int(box_h * 0.18))); sub_f_size = min(38, int(box_h * 0.18))

            for idx, item in enumerate(checked):
                c, r = positions[idx]
                box_x = int(80 + (c * col_w))
                if cols > 1 and c == 0.5: box_x = (cw - box_w) // 2
                y = int(start_y + (r * (box_h + spacing)))
                
                is_off = item['offline'].get()
                
                if is_off:
                    draw.text((box_x + 40, y + (box_h * 0.5)), item["code"], fill=c_txt, font=day_f, anchor="lm")
                    draw.text((box_x + 280, y + (box_h * 0.5)), "OFFLINE", fill=c_sub, font=game_f, anchor="lm")
                    continue

                raw_g = item["game"].get().strip().upper()
                g_val = raw_g if raw_g else "TBA"
                s_val = item["sub"].get().strip()
                
                art_img = None
                if item.get("custom_art") and os.path.exists(item["custom_art"]):
                    art_img = Image.open(item["custom_art"])
                elif item["code"] in self.art_cache and raw_g:
                    art_img = Image.open(self.art_cache[item["code"]])

                draw.text((box_x + 40, y + (box_h * 0.35)), item["code"], fill=c_txt, font=day_f, anchor="lm")
                
                times = self.get_converted_time(item['time'].get(), self.my_zone.get(), self.sec_zone.get(), self.show_primary.get())
                ty = y + (box_h * 0.60)
                for t_str in times:
                    draw.text((box_x + 40, ty), t_str, fill=c_sub, font=time_f, anchor="lm"); ty += time_f_size + 5

                text_x = box_x + 240 
                art_x = box_x + box_w - 20
                
                if art_img and box_h > 50:
                    art_h = box_h - 40; art_w = int(art_h * 0.75)
                    art_x = box_x + box_w - 20 - art_w
                    try:
                        art = ImageOps.fit(art_img.convert("RGBA"), (art_w, art_h))
                        mask = Image.new("L", (art_w, art_h), 0)
                        ImageDraw.Draw(mask).rounded_rectangle([0, 0, art_w, art_h], 15, 255)
                        img.paste(art, (art_x, y + 20), mask)
                    except: pass
                
                max_text_w = max(20, art_x - text_x - 30)
                g_lines = textwrap.wrap(g_val, width=max(8, int(max_text_w / (game_f_size * 0.55))))
                s_lines = textwrap.wrap(s_val, width=max(12, int(max_text_w / (sub_f_size * 0.50)))) if s_val else []
                
                total_h = len(g_lines) * (game_f_size + 8) + (len(s_lines) * (sub_f_size + 8) + 10 if s_lines else 0)
                gy = y + (box_h // 2) - (total_h // 2) 
                
                for line in g_lines:
                    draw.text((text_x, gy), line, fill=c_txt, font=game_f); gy += game_f_size + 8
                if s_lines:
                    gy += 10 
                    for line in s_lines:
                        draw.text((text_x, gy), line, fill=c_sub, font=sub_f); gy += sub_f_size + 8

        if has_goal or has_logo:
            sp_y = ch - 30
            
            if has_goal:
                try:
                    cur_val = float(sp_cur_str) if sp_cur_str else 0
                    tgt_val = float(sp_tgt_str) if sp_tgt_str else 0
                except:
                    cur_val, tgt_val = 0, 0
                
                if tgt_val > 0:
                    bar_w = int(cw * 0.4)
                    bar_h = max(20, int(ch * 0.025))
                    bar_x = cw//2 - bar_w//2
                    bar_y = sp_y - bar_h
                    
                    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=(40, 40, 40, 200), outline=c_sub, width=2)
                    
                    pct = max(0.0, min(1.0, cur_val / tgt_val))
                    fill_w = int(bar_w * pct)
                    if fill_w > 0:
                        fill_w = max(fill_w, bar_h) 
                        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=c_head)
                    
                    prog_font = self.get_f_path(max(12, int(bar_h * 0.6)))
                    prog_text = f"{sp_cur_str} / {sp_tgt_str}"
                    draw.text((cw//2, bar_y + bar_h//2), prog_text, fill=(255, 255, 255), font=prog_font, anchor="mm", stroke_width=1, stroke_fill=(0,0,0))
                    
                    sp_y = bar_y - 15

                if sp_title:
                    sp_font = self.get_f_path(max(20, int(ch * 0.025)))
                    draw.text((cw//2, sp_y), sp_title, fill=c_txt, font=sp_font, anchor="md")
                    sp_y -= int(ch * 0.035) + 5
            
            if has_logo:
                try:
                    s_logo = Image.open(sp_path).convert("RGBA")
                    logo_h = int(ch * 0.08)
                    s_logo = ImageOps.contain(s_logo, (cw//2, logo_h))
                    img.paste(s_logo, (cw//2 - s_logo.width//2, sp_y - s_logo.height), s_logo)
                except: pass

        return img

    def generate_preview_image(self, *args):
        try:
            img = self.render_schedule_image(self.canvas_format.get())
            cw, ch = img.size
            max_preview_w = getattr(self, 'prev_width', 950) - 20
            max_preview_h = getattr(self, 'prev_height', 850) - 20
            if max_preview_w < 100: max_preview_w = 950
            if max_preview_h < 100: max_preview_h = 850
            
            scale = min(max_preview_w/cw, max_preview_h/ch)
            scaled_w, scaled_h = int(cw * scale), int(ch * scale)
            
            p_ready = ctk.CTkImage(light_image=img, dark_image=img, size=(scaled_w, scaled_h))
            self.preview_label.configure(image=p_ready, text="", width=scaled_w, height=scaled_h)
            img.convert("RGB").save("schedule_final.jpg", quality=95)
        except Exception as e: self.log(f"Renderer Note: {e}")

    def start_export(self):
        threading.Thread(target=self.run_export, daemon=True).start()

    def run_export(self):
        self.log("💾 Exporting selected formats to Desktop...")
        export_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'Simph_Schedules')
        os.makedirs(export_dir, exist_ok=True)
        saved_count = 0
        
        for r_name, var in self.export_vars.items():
            if var.get():
                try:
                    e_img = self.render_schedule_image(r_name)
                    safe_name = r_name.split(' ')[0].replace(':', 'x')
                    e_path = os.path.join(export_dir, f"Schedule_{self.selected_start_date.strftime('%b%d')}_{safe_name}.jpg")
                    e_img.convert("RGB").save(e_path, quality=95)
                    saved_count += 1
                except Exception as e: self.log(f"❌ Failed to export {r_name}: {e}")
        
        if saved_count > 0:
            self.log(f"✅ Successfully exported {saved_count} image(s) to Desktop/Simph_Schedules!")
        else:
            self.log("⚠️ No formats ticked for export!")

    def start_deploy(self): threading.Thread(target=lambda: asyncio.run(self.run_engine()), daemon=True).start()
    async def run_engine(self):
        self.log("🚀 Starting Global Deployment...")
        self.generate_preview_image()
        time.sleep(1.5)

        webhook_url = self.cfg.get('webhook', '').strip()
        if webhook_url and self.cfg.get("last_msg_id", ""):
            try: requests.delete(f"{webhook_url}/messages/{self.cfg['last_msg_id']}", timeout=10)
            except: pass

        discord_msg = self.get_discord_header() + "\n\n"
        base_dt = self.selected_start_date

        has_ticked_days = False
        for i, code in enumerate(self.all_days):
            item = self.days_ui_list[i]
            if item["check"].get():
                has_ticked_days = True
                g_val = item['game'].get().strip() or "TBA"
                sub_str = f" | {item['sub'].get()}" if item['sub'].get().strip() else ""
                t_val = item['time'].get()
                is_off = item['offline'].get()
                
                if is_off:
                    discord_msg += f"- `{self.full_days[code]}` - **OFFLINE**\n"
                elif t_val == "TBA":
                    discord_msg += f"- `{self.full_days[code]}` - **{g_val}{sub_str}** (Time TBA)\n"
                else:
                    try:
                        h, m = map(int, t_val.split(':'))
                        loc_tz = pytz.timezone(self.tz_map.get(self.my_zone.get(), "Europe/London"))
                        unix_ts = int(loc_tz.localize(datetime.datetime(base_dt.year, base_dt.month, base_dt.day, h, m) + datetime.timedelta(days=i)).timestamp())
                        discord_msg += f"- `{self.full_days[code]}` - **{g_val}{sub_str}** <t:{unix_ts}:t>\n"
                    except: discord_msg += f"- `{self.full_days[code]}` - **{g_val}** (Time Error)\n"
        
        if not has_ticked_days: discord_msg += "No streams scheduled for this week!"

        if webhook_url:
            try:
                with open("schedule_final.jpg", "rb") as f:
                    r = requests.post(webhook_url + "?wait=true", data={"content": discord_msg}, files={"file": f}, timeout=15)
                    if r.status_code in [200, 204]:
                        self.cfg["last_msg_id"] = r.json().get("id", "")
                        with open(self.settings_path, "w") as jf: json.dump(self.cfg, jf, indent=4)
                        self.log("🏁 Discord: Successfully Uploaded.")
            except Exception as e: self.log(f"❌ Discord: Webhook Error: {e}")

        if self.cfg.get('t_tok'):
            self.log("🛰️ Syncing Twitch Dashboard...")
            try:
                api = await Twitch(self.cfg['t_id'], self.cfg['t_sec'])
                api.auto_refresh_auth = False 
                await api.set_user_authentication(self.cfg['t_tok'], [AuthScope.CHANNEL_MANAGE_SCHEDULE], None)
                user = await first(api.get_users())
                for i, item in enumerate(self.days_ui_list):
                    if item["check"].get() and not item['offline'].get() and item['time'].get() != "TBA":
                        h, m = map(int, item['time'].get().split(':'))
                        start_dt = datetime.datetime(base_dt.year, base_dt.month, base_dt.day, h, m) + datetime.timedelta(days=i)
                        await api.create_channel_stream_schedule_segment(broadcaster_id=user.id, start_time=start_dt, timezone=self.tz_map.get(self.my_zone.get(), "Europe/London"), duration='240', is_recurring=False, category_id=self.game_ids.get(item["game"].get()), title=f"{item['game'].get() or 'TBA'}")
                self.log("✅ Twitch Dashboard: SYNCED.")
            except Exception as e: self.log(f"❌ Twitch Error: {e}")

    def refresh_status(self):
        t_id, t_tok = len(self.cfg.get("t_id", "")) > 5, len(self.cfg.get("t_tok", "")) > 10
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
        
        self.add_manual(hp_f, "1. The Optional Twitch Integration", "You can use this app purely for Discord scheduling by only adding a Webhook URL! However, the 'Game...' search dropdown requires Twitch API keys to fetch official game titles and dynamic box art automatically.", None)
        self.add_manual(hp_f, "2. Get Twitch API Keys", "1. Go to the Twitch Dev Console.\n2. Click 'Register Your Application'.\n3. Set OAuth Redirect URL EXACTLY to: http://localhost:17563\n4. Set Category to 'Application Integration'.\n5. Hit create, then COPY your Client ID and GENERATE A NEW SECRET.\n\n⚠️ IMPORTANT: You MUST copy the Client Secret before closing the page!", "https://dev.twitch.tv/console")
        self.add_manual(hp_f, "3. Link Your Account", "1. Paste your new Client ID on the left.\n2. Click 'OPEN AUTH LINK' and hit Authorize.\n3. Your browser will show a 'Refused to Connect' error—this is totally normal!\n4. COPY the entire long URL from the address bar.\n5. Paste it into the 'PASTE BROKEN URL' box and click EXTRACT.", None)
        self.add_manual(hp_f, "4. Discord Webhook Setup", "Go to your Discord Server Settings > Integrations > Webhooks. Create a new webhook for your schedule channel, copy the URL, and paste it on the left.", "https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks")
        self.add_manual(hp_f, "5. App Layouts & Features", "► OFFLINE MODE: Tick the 'Offline' box next to a day to grey it out. Perfect for showing a full 7-day week when you only stream on 3 days.\n\n► CUSTOM ART: Click the [🖼️] button next to a day to upload custom box art. To remove it, just click the button again.\n\n► EXPORT VS DEPLOY: Use Export to save the ticked layout sizes to a folder on your Desktop. Use Deploy to instantly upload the preview canvas directly to your Discord server and update your Twitch schedule tab.", None)

    def add_section_header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Arial", 11, "bold"), text_color="#777777").pack(pady=(15, 2))

    def setup_planner_tab(self):
        p = ctk.CTkFrame(self.tab_planner); p.pack(fill="both", expand=True)
        side = ctk.CTkScrollableFrame(p, width=320, label_text="VISUAL DESIGN"); side.pack(side="left", fill="y", padx=10, pady=10)
        
        self.header_entry = ctk.CTkEntry(side); self.header_entry.pack(fill="x", padx=10, pady=5); self.header_entry.insert(0, self.cfg.get("header_text", "STREAMER SCHEDULE")); self.header_entry.bind("<KeyRelease>", self.schedule_preview)
        self.header_sub_entry = ctk.CTkEntry(side); self.header_sub_entry.pack(fill="x", padx=10, pady=5); self.header_sub_entry.bind("<KeyRelease>", self.schedule_preview)
        
        # --- SECTION: CANVAS & BACKGROUND ---
        self.add_section_header(side, "--- PREVIEW CANVAS ---")
        self.canvas_format = ctk.CTkOptionMenu(side, values=list(self.ratios.keys()), command=self.schedule_preview)
        self.canvas_format.pack(fill="x", padx=10, pady=5)
        self.canvas_format.set(self.cfg.get("canvas_format", "9:16 (TikTok/Reels/Shorts)"))
        
        btn_f1 = ctk.CTkFrame(side, fg_color="transparent"); btn_f1.pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(btn_f1, text="📁 Set Background", command=self.pick_bg).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(btn_f1, text="🖼️ Set Logo", command=self.pick_logo).pack(side="right", expand=True, padx=2)
        
        self.bg_zoom_slider = self.add_slider(side, "Background Zoom", "bg_zoom", 25, 300, is_pct=True)
        self.logo_size_slider = self.add_slider(side, "Top Logo Size", "logo_size", 100, 500, is_px=True)
        
        # --- SECTION: SPONSOR & GOALS ---
        self.add_section_header(side, "--- SPONSOR & GOALS ---")
        btn_spon = ctk.CTkFrame(side, fg_color="transparent"); btn_spon.pack(fill="x", padx=10, pady=2)
        
        self.btn_sponsor_logo = ctk.CTkButton(btn_spon, text="❌ Remove Logo" if self.cfg.get("sponsor_path") else "📁 Set Sponsor/Goal Logo", fg_color="green" if self.cfg.get("sponsor_path") else ["#3a7ebf", "#1f538d"], command=self.pick_sponsor)
        self.btn_sponsor_logo.pack(fill="x", expand=True)

        self.sponsor_title = ctk.CTkEntry(side, placeholder_text="Goal Title (e.g. Sub Goal)")
        self.sponsor_title.pack(fill="x", padx=10, pady=(5, 2))
        self.sponsor_title.bind("<KeyRelease>", self.schedule_preview)
        self.sponsor_title.insert(0, self.cfg.get("sponsor_title", ""))

        goal_f = ctk.CTkFrame(side, fg_color="transparent"); goal_f.pack(fill="x", padx=10, pady=2)
        self.goal_current = ctk.CTkEntry(goal_f, width=80, placeholder_text="Current (0)")
        self.goal_current.pack(side="left", expand=True, padx=(0, 2))
        self.goal_current.bind("<KeyRelease>", self.schedule_preview)
        self.goal_current.insert(0, self.cfg.get("goal_current", ""))
        
        ctk.CTkLabel(goal_f, text="/").pack(side="left")
        
        self.goal_target = ctk.CTkEntry(goal_f, width=80, placeholder_text="Target (100)")
        self.goal_target.pack(side="right", expand=True, padx=(2, 0))
        self.goal_target.bind("<KeyRelease>", self.schedule_preview)
        self.goal_target.insert(0, self.cfg.get("goal_target", ""))

        # --- SECTION: EXPORT SIZES ---
        self.add_section_header(side, "--- EXPORT OPTIONS ---")
        ctk.CTkLabel(side, text="Select formats to save to Desktop:", text_color="#AAAAAA", font=("Arial", 10)).pack(anchor="w", padx=10)
        self.export_vars = {}
        for r_name in self.ratios.keys():
            var = ctk.BooleanVar(value=True if "9:16" in r_name else False)
            chk = ctk.CTkCheckBox(side, text=r_name, variable=var, height=20, font=("Arial", 11))
            chk.pack(anchor="w", padx=15, pady=2)
            self.export_vars[r_name] = var

        # --- SECTION: TEXT & COLORS ---
        self.add_section_header(side, "--- TEXT & COLORS ---")
        self.font_menu = ctk.CTkOptionMenu(side, values=list(self.font_map.keys()), command=self.schedule_preview); self.font_menu.pack(fill="x", padx=10, pady=5); self.font_menu.set(self.cfg.get("font", "Arial Black"))
        
        self.header_size_slider = self.add_slider(side, "Main Title Size", "header_size", 50, 150)
        self.header_sub_size_slider = self.add_slider(side, "Date Range Size", "sub_size", 20, 80)
        
        col_f = ctk.CTkFrame(side, fg_color="transparent"); col_f.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(col_f, text="🎨 Box Background", command=lambda: self.pick_color_generic("box_color")).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Box Text", command=lambda: self.pick_color_generic("box_txt_color")).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Main Title Text", command=lambda: self.pick_color_generic("header_txt_color")).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Date Range Text", command=lambda: self.pick_color_generic("sub_txt_color")).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        col_f.grid_columnconfigure(0, weight=1); col_f.grid_columnconfigure(1, weight=1)

        # --- SECTION: BOX LAYOUT ---
        self.add_section_header(side, "--- SCHEDULE BOX SETTINGS ---")
        self.max_box_slider = self.add_slider(side, "Max Box Height", "max_box_h", 150, 500, is_px=True)
        self.box_opacity_slider = self.add_slider(side, "Box Opacity", "box_opacity", 0, 255)
        
        # --- SECTION: TIMEZONES ---
        self.add_section_header(side, "--- TIMEZONES & FORMATS ---")
        self.time_fmt = ctk.CTkOptionMenu(side, values=["24-Hour (20:00)", "12-Hour (8:00 PM)"], command=self.schedule_preview); self.time_fmt.pack(fill="x", padx=10, pady=2); self.time_fmt.set(self.cfg.get("time_fmt", "24-Hour (20:00)"))
        
        ctk.CTkLabel(side, text="Primary Local Timezone:").pack()
        self.my_zone = ctk.CTkOptionMenu(side, values=list(self.tz_map.keys()), command=self.schedule_preview); self.my_zone.pack(fill="x", padx=10, pady=2); self.my_zone.set(self.cfg.get("my_zone", "UK (GMT/BST)"))
        self.show_primary = tk.BooleanVar(value=self.cfg.get("show_primary", True))
        ctk.CTkCheckBox(side, text="Show Primary Time on Image", variable=self.show_primary, command=self.schedule_preview).pack(pady=2)

        ctk.CTkLabel(side, text="Secondary Display Timezone:").pack(pady=(5,0))
        self.sec_zone = ctk.CTkOptionMenu(side, values=list(self.sec_tz_map.keys()), command=self.schedule_preview); self.sec_zone.pack(fill="x", padx=10, pady=2); self.sec_zone.set(self.cfg.get("sec_zone", "US East (EST/EDT)"))
        
        ctk.CTkButton(side, text="📘 HOW TO USE THIS APP", fg_color="#333333", command=self.show_help_popup).pack(fill="x", padx=10, pady=(15, 0))
        
        # --- EXPORT / DEPLOY BUTTONS ---
        btn_action_f = ctk.CTkFrame(side, fg_color="transparent"); btn_action_f.pack(fill="x", padx=10, pady=(15, 20))
        ctk.CTkButton(btn_action_f, text="💾 EXPORT", height=50, fg_color="#21612b", font=("Arial", 16, "bold"), command=self.start_export).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_action_f, text="🚀 DEPLOY", height=50, fg_color="#801010", font=("Arial", 16, "bold"), command=self.start_deploy).pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        # --- PLANNER RIGHT SIDE ---
        scroll = ctk.CTkScrollableFrame(p, label_text="WEEKLY SCHEDULE TICKBOXES"); scroll.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.date_btn = ctk.CTkButton(scroll, text="📅 Click to Select Start Date...", height=40, font=("Arial", 14, "bold"), command=self.open_calendar)
        self.date_btn.pack(fill="x", padx=5, pady=(0, 15))

        self.days_ui_list = []
        time_opts = ["TBA"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
        
        for i in range(7):
            df = ctk.CTkFrame(scroll); df.pack(pady=5, fill="x")
            chk = ctk.CTkCheckBox(df, text="", width=20, command=self.schedule_preview); chk.grid(row=0, column=0, padx=2)
            ctk.CTkLabel(df, text=self.all_days[i], width=50, font=("Arial", 12, "bold")).grid(row=0, column=1)
            
            g_wrap = ctk.CTkFrame(df, fg_color="transparent"); g_wrap.grid(row=0, column=2, padx=5)
            gm = ctk.CTkEntry(g_wrap, width=220, placeholder_text="Game..."); gm.pack(); gm.bind("<KeyRelease>", lambda e, idx=i: self.on_key_release(e, idx))
            s_f = ctk.CTkFrame(g_wrap, height=0, fg_color="#222"); s_f.pack(fill="x")
            
            sub = ctk.CTkEntry(df, placeholder_text="Sub...", width=140); sub.grid(row=0, column=3, padx=5); sub.bind("<KeyRelease>", self.schedule_preview)
            tm = ctk.CTkOptionMenu(df, values=time_opts, width=80, command=self.schedule_preview); tm.grid(row=0, column=4, padx=5); tm.set("20:00")
            
            off_chk = ctk.CTkCheckBox(df, text="Offline", width=60, font=("Arial", 12, "bold"), text_color="#AAAAAA", command=self.schedule_preview)
            off_chk.grid(row=0, column=5, padx=10)
            
            art_btn = ctk.CTkButton(df, text="🖼️", width=30, fg_color="#444", command=lambda idx=i: self.pick_custom_art(idx))
            art_btn.grid(row=0, column=6, padx=5)
            
            self.days_ui_list.append({"check": chk, "game": gm, "sub": sub, "time": tm, "suggest": s_f, "code": self.all_days[i], "offline": off_chk, "custom_art": None, "art_btn": art_btn})
            
        self.prev_container = ctk.CTkFrame(p, fg_color="transparent"); self.prev_container.pack(side="right", padx=10, fill="both", expand=True)
        self.preview_label = ctk.CTkLabel(self.prev_container, text="Loading Preview...", fg_color="transparent")
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
        self.prev_container.bind("<Configure>", self.on_preview_resize)

    # --- UTILS ---
    def pick_custom_art(self, idx):
        if self.days_ui_list[idx]["custom_art"]:
            self.days_ui_list[idx]["custom_art"] = None
            self.days_ui_list[idx]["art_btn"].configure(fg_color="#444")
        else:
            p = filedialog.askopenfilename()
            if p:
                self.days_ui_list[idx]["custom_art"] = p
                self.days_ui_list[idx]["art_btn"].configure(fg_color="green")
        self.schedule_preview()
        
    def pick_sponsor(self):
        if self.cfg.get("sponsor_path"):
            self.cfg["sponsor_path"] = ""
            self.btn_sponsor_logo.configure(fg_color=["#3a7ebf", "#1f538d"], text="📁 Set Sponsor/Goal Logo")
        else:
            p = filedialog.askopenfilename()
            if p: 
                self.cfg["sponsor_path"] = p
                self.btn_sponsor_logo.configure(fg_color="green", text="❌ Remove Logo")
        self.schedule_preview()

    def select_game(self, idx, val, gid):
        self.days_ui_list[idx]["game"].delete(0, 'end'); self.days_ui_list[idx]["game"].insert(0, val); self.game_ids[val] = gid
        self.hide_all_suggest(); self.focus(); threading.Thread(target=lambda: asyncio.run(self.up_art(val, self.days_ui_list[idx]["code"])), daemon=True).start()
    
    def save_settings(self):
        self.cfg.update({"webhook":self.set_webhook.get(),"t_id":self.set_id.get(),"t_sec":self.set_sec.get(),"t_tok":self.set_tok.get(),"header_text":self.header_entry.get(),"header_size":self.header_size_slider.get(),"sub_size":self.header_sub_size_slider.get(),"logo_size":self.logo_size_slider.get(),"bg_zoom":self.bg_zoom_slider.get(),"box_opacity":self.box_opacity_slider.get(),"font":self.font_menu.get(),"my_zone":self.my_zone.get(),"sec_zone":self.sec_zone.get(), "canvas_format":self.canvas_format.get(), "max_box_h":self.max_box_slider.get(), "time_fmt":self.time_fmt.get(), "show_primary":self.show_primary.get(), "sponsor_title":self.sponsor_title.get(), "goal_current":self.goal_current.get(), "goal_target":self.goal_target.get()})
        with open(self.settings_path, "w") as f: json.dump(self.cfg, f, indent=4)
        self.refresh_status(); messagebox.showinfo("Saved", "Settings Saved Securely!"); self.schedule_preview()

    def pick_color_generic(self, key):
        c = colorchooser.askcolor(initialcolor=self.cfg.get(key, "#FFFFFF"))
        if c[1]: self.cfg[key] = c[1]; self.schedule_preview()

    def hex_to_rgb(self, hex_color):
        try: return tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except: return (255, 255, 255)

    def add_slider(self, p, lbl_text, key, start, end, is_pct=False, is_px=False):
        lbl = ctk.CTkLabel(p, text=lbl_text)
        lbl.pack(anchor="w", padx=10)
        
        def on_slide(val):
            val_int = int(float(val))
            suffix = "%" if is_pct else (" px" if is_px else "")
            lbl.configure(text=f"{lbl_text}: {val_int}{suffix}")
            self.schedule_preview()
            
        s = ctk.CTkSlider(p, from_=start, to=end, command=on_slide)
        s.pack(fill="x", padx=10, pady=(0, 5))
        s.set(self.cfg.get(key, start))
        
        val_int = int(self.cfg.get(key, start))
        suffix = "%" if is_pct else (" px" if is_px else "")
        lbl.configure(text=f"{lbl_text}: {val_int}{suffix}")
        return s

    def create_set(self, p, lbl, val):
        ctk.CTkLabel(p, text=lbl).pack(); e = ctk.CTkEntry(p, width=400); e.pack(pady=5)
        if val: e.insert(0, val)
        self.apply_right_click(e); return e

    def add_manual(self, p, t, d, u):
        ctk.CTkLabel(p, text=t, font=("Arial", 14, "bold"), text_color="#D11111").pack(pady=(15,0), anchor="w"); ctk.CTkLabel(p, text=d, wraplength=400, justify="left").pack(anchor="w")
        if u: ctk.CTkButton(p, text="🔗 Help Link", height=24, command=lambda u=u: webbrowser.open(u)).pack(pady=5, anchor="w")

    def on_key_release(self, e, idx):
        self.schedule_preview()
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
        if p: self.cfg["bg_path"] = p; self.schedule_preview()

    def pick_logo(self):
        p = filedialog.askopenfilename()
        if p: self.cfg["logo_path"] = p; self.schedule_preview()

    async def up_art(self, c, d):
        try:
            api = await Twitch(self.cfg['t_id'].strip(), self.cfg['t_sec'].strip()); g = await first(api.get_games(names=[c]))
            if g:
                r = requests.get(g.box_art_url.replace("{width}","300").replace("{height}","400"))
                with open(f"cache_{d}.png", "wb") as f: f.write(r.content)
                self.art_cache[d] = f"cache_{d}.png"; self.after(0, self.schedule_preview)
        except: pass

    def get_f_path(self, size):
        font_name = self.font_menu.get()
        font_file = self.font_map.get(font_name, "arialbd.ttf")
        p = os.path.join(os.environ['WINDIR'], 'Fonts', font_file)
        return ImageFont.truetype(p if os.path.exists(p) else "arialbd.ttf", max(1, size))

if __name__ == "__main__":
    app = SimphStudio(); app.mainloop()