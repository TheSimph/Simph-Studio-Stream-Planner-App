import customtkinter as ctk
import tkinter as tk
import os, sys, time, threading, asyncio, requests, shutil, zipfile, subprocess, datetime
from tkinter import messagebox

# Modular Imports
from config.settings_manager import SettingsManager
from engines.time_converter import TimeConverter
from engines.image_renderer import ImageRenderer
from api.twitch_client import TwitchClient
from api.discord_client import DiscordClient
from ui.tabs.planner_tab import PlannerTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.discord_tab import DiscordTab
from ui.components.calendar_modal import CalendarModal
from ui.components.setup_guide import SetupGuide

class SimphStudioWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.APP_VERSION = "0.1.79"
        self.REPO_NAME = "Simph-Studio-Stream-Planner-App"
        self.UPDATE_URL = f"https://raw.githubusercontent.com/TheSimph/{self.REPO_NAME}/main/version.txt"
        self.RELEASE_URL = f"https://github.com/TheSimph/{self.REPO_NAME}/releases/latest"
        self.API_LATEST_URL = f"https://api.github.com/repos/TheSimph/{self.REPO_NAME}/releases/latest"

        self.title(f"Simph Studio - Ver {self.APP_VERSION}")
        ctk.set_appearance_mode("dark")

        self.settings = SettingsManager()
        self.cfg = self.settings.config

        try:
            cache_dir = os.path.join(self.settings.appdata_dir, "art_cache")
            if os.path.exists(cache_dir): 
                shutil.rmtree(cache_dir, ignore_errors=True)
            os.makedirs(cache_dir, exist_ok=True)
        except: pass

        def cleanup_updater_files():
            time.sleep(3) 
            try:
                if getattr(sys, 'frozen', False):
                    old_exe = sys.executable + ".old"
                    if os.path.exists(old_exe): os.remove(old_exe)
                appdata_update = os.path.join(self.settings.appdata_dir, "update.zip")
                if os.path.exists(appdata_update): os.remove(appdata_update)
                extract_path = os.path.join(self.settings.appdata_dir, "update_extracted")
                if os.path.exists(extract_path): shutil.rmtree(extract_path, ignore_errors=True)
                bat_path = os.path.join(self.settings.appdata_dir, "update.bat")
                if os.path.exists(bat_path): os.remove(bat_path)
            except: pass
            
        threading.Thread(target=cleanup_updater_files, daemon=True).start()
        
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

        self.time_converter = TimeConverter()
        self.renderer = ImageRenderer()
        self.setup_guide = SetupGuide(self)
        
        self.twitch_client = TwitchClient(self.cfg.get('t_id', ''), self.cfg.get('t_sec', ''), self.cfg.get('t_tok', ''))
        
        # --- FIXED: Initialize BOTH Discord Webhooks ---
        self.discord_client = DiscordClient(self.cfg.get('webhook', ''))
        self.discord_client_sec = DiscordClient(self.cfg.get('webhook_sec', ''))

        self.all_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        self.full_days = {"MON":"Monday","TUE":"Tuesday","WED":"Wednesday","THU":"Thursday","FRI":"Friday","SAT":"Saturday","SUN":"Sunday"}
        
        self.ratios = self.renderer.ratios
        self.font_map = self.renderer.font_map
        self.tz_map = self.time_converter.tz_map
        self.sec_tz_map = self.time_converter.sec_tz_map

        saved_geo = self.cfg.get("window_geometry", "1650x1000")
        self.geometry(saved_geo)
        
        if sys.platform.startswith("win"):
            self.after(100, lambda: self.state("zoomed"))
            
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.art_cache = {} 
        self.game_ids = {} 
        self._preview_timer = None 
        self._resize_timer = None
        self.selected_start_date = datetime.date.today()

        self.setup_layout()
        self.update_date_displays()
        
        self.bind("<Button-1>", lambda e: self.planner_tab.hide_all_suggest())
        self.schedule_preview()
        
        self.after(1200, self.refresh_status)
        self.after(2000, self.check_for_updates)
        
        def fix_placeholders():
            if self.planner_tab.days_ui_list: 
                self.planner_tab.days_ui_list[0]["game"].focus_set()
            self.focus_set()
        self.after(200, fix_placeholders)

    def setup_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SIMPH STUDIO", font=("Arial Black", 18))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_weekly = ctk.CTkButton(self.sidebar_frame, text="📅 Weekly Schedule", anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.select_frame_by_name("weekly"))
        self.btn_weekly.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.btn_canvas = ctk.CTkButton(self.sidebar_frame, text="🎨 Canvas & Design", anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.select_frame_by_name("canvas"))
        self.btn_canvas.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.btn_export = ctk.CTkButton(self.sidebar_frame, text="🚀 Export & Deploy", anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.select_frame_by_name("export"))
        self.btn_export.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.btn_discord = ctk.CTkButton(self.sidebar_frame, text="💬 Discord Preview", anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.select_frame_by_name("discord"))
        self.btn_discord.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self.btn_connections = ctk.CTkButton(self.sidebar_frame, text="⚙️ Connections", anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.select_frame_by_name("connections"))
        self.btn_connections.grid(row=5, column=0, padx=10, pady=5, sticky="ew")

        self.btn_guide = ctk.CTkButton(self.sidebar_frame, text="📘 Setup Guide", anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=self.show_help_popup)
        self.btn_guide.grid(row=7, column=0, padx=10, pady=(10, 20), sticky="ew")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.planner_tab = PlannerTab(self.main_container, self)
        self.settings_tab = SettingsTab(self.main_container, self)
        self.discord_tab = DiscordTab(self.main_container, self)
        
        self.status_bar = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#1a1a1a")
        self.status_bar.grid(row=1, column=1, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)
        self.status_bar.grid_columnconfigure(1, weight=0)

        self.console = ctk.CTkTextbox(self.status_bar, height=60, font=("Consolas", 11), fg_color="transparent", text_color="#00FF00")
        self.console.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        self.console.bind("<Button-3>", lambda e: self.console.focus())

        indicator_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        indicator_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        self.st_twitch_api = ctk.CTkLabel(indicator_frame, text="● Twitch: MISSING", text_color="#FF3333", font=("Arial", 12, "bold"))
        self.st_twitch_api.pack(side="left", padx=10)
        
        self.st_twitch_tok = ctk.CTkLabel(indicator_frame, text="● Token: MISSING", text_color="#FF3333", font=("Arial", 12, "bold"))
        self.st_twitch_tok.pack(side="left", padx=10)
        
        self.st_discord = ctk.CTkLabel(indicator_frame, text="● Discord: MISSING", text_color="#FF3333", font=("Arial", 12, "bold"))
        self.st_discord.pack(side="left", padx=10)

        if self.cfg.get("t_tok") and self.cfg.get("webhook"):
            self.select_frame_by_name("weekly")
        else:
            self.select_frame_by_name("connections")

    def select_frame_by_name(self, name):
        default_color = "transparent"
        active_color = "#7044c4"
        
        self.btn_weekly.configure(fg_color=active_color if name == "weekly" else default_color)
        self.btn_canvas.configure(fg_color=active_color if name == "canvas" else default_color)
        self.btn_export.configure(fg_color=active_color if name == "export" else default_color)
        self.btn_discord.configure(fg_color=active_color if name == "discord" else default_color)
        self.btn_connections.configure(fg_color=active_color if name == "connections" else default_color)

        self.planner_tab.grid_forget()
        self.settings_tab.grid_forget()
        self.discord_tab.grid_forget()

        if name in ["weekly", "canvas", "export"]:
            self.planner_tab.grid(row=0, column=0, sticky="nsew")
            self.planner_tab.switch_view(name)
        elif name == "discord":
            self.discord_tab.grid(row=0, column=0, sticky="nsew")
            self.discord_tab.refresh_preview()
        elif name == "connections":
            self.settings_tab.grid(row=0, column=0, sticky="nsew")

    def get_resource_path(self, relative_path):
        try: base_path = sys._MEIPASS
        except Exception: base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def log(self, text):
        self.console.insert("end", f"> {text}\n")
        self.console.see("end")

    def on_closing(self):
        self.cfg["window_geometry"] = self.geometry()
        try:
            if hasattr(self, 'planner_tab') and self.planner_tab.days_ui_list:
                sched_data = []
                for item in self.planner_tab.days_ui_list:
                    sched_data.append({
                        "check": item["check"].get(),
                        "game": item["game"].get(),
                        "sub": item["sub"].get(),
                        "note": item["note"].get() if "note" in item else "",
                        "time": item["time"].get(),
                        "offline": item["offline"].get(),
                        "cancelled": item["cancelled"].get(),
                        "custom_art": item["custom_art"]
                    })
                self.cfg["saved_schedule_layout"] = sched_data
        except Exception: pass

        self.settings.save_settings()
        
        try:
            cache_dir = os.path.join(self.settings.appdata_dir, "art_cache")
            if os.path.exists(cache_dir): shutil.rmtree(cache_dir, ignore_errors=True)
        except: pass
        
        self.destroy()
        os._exit(0)

    def save_settings(self):
        self.cfg.update({
            "webhook": self.settings_tab.set_webhook.get(),
            "webhook_sec": self.settings_tab.set_webhook_sec.get(),
            "t_id": self.settings_tab.set_id.get(),
            "t_sec": self.settings_tab.set_sec.get(),
            "t_tok": self.settings_tab.set_tok.get(),
            "time_fmt": self.settings_tab.time_fmt.get(),
            "my_zone": self.settings_tab.my_zone.get(),
            "sec_zone": self.settings_tab.sec_zone.get(),
            "show_primary": self.settings_tab.show_primary.get(),
            "header_text": self.planner_tab.header_entry.get(),
            "font": self.planner_tab.font_menu.get(),
            "canvas_format": self.planner_tab.canvas_format.get(), 
            "sponsor_title": self.planner_tab.sponsor_title.get(), 
            "goal_current": self.planner_tab.goal_current.get(), 
            "goal_target": self.planner_tab.goal_target.get(), 
            "export_path": self.planner_tab.export_path_var.get(), 
            "deploy_format": self.planner_tab.deploy_format.get(),
            "drop_shadow": self.planner_tab.drop_shadow_var.get(),
            "text_outline": self.planner_tab.text_outline_var.get()
        })
        
        try:
            if hasattr(self, 'planner_tab') and self.planner_tab.days_ui_list:
                sched_data = []
                for item in self.planner_tab.days_ui_list:
                    sched_data.append({
                        "check": item["check"].get(),
                        "game": item["game"].get(),
                        "sub": item["sub"].get(),
                        "note": item["note"].get() if "note" in item else "",
                        "time": item["time"].get(),
                        "offline": item["offline"].get(),
                        "cancelled": item["cancelled"].get(),
                        "custom_art": item["custom_art"]
                    })
                self.cfg["saved_schedule_layout"] = sched_data
        except Exception: pass
            
        self.settings.save_settings()
        
        self.twitch_client = TwitchClient(self.cfg.get('t_id', ''), self.cfg.get('t_sec', ''), self.cfg.get('t_tok', ''))
        
        # --- FIXED: Update BOTH Discord Webhooks on Save ---
        self.discord_client = DiscordClient(self.cfg.get('webhook', ''))
        self.discord_client_sec = DiscordClient(self.cfg.get('webhook_sec', ''))
        
        self.refresh_status()
        messagebox.showinfo("Saved", "Settings Saved Securely!")
        self.schedule_preview()

    def check_for_updates(self):
        self.log("checking github for updates...")
        def run_check():
            try:
                import random
                cb = f"?cb={random.randint(1, 999999)}"
                response = requests.get(self.UPDATE_URL + cb, timeout=5)
                if response.status_code == 200:
                    latest_v = response.text.strip()
                    if latest_v != self.APP_VERSION:
                        self.log(f"Update found! (Ver {latest_v})")
                        self.after(0, lambda: self.show_update_popup(latest_v))
                    else:
                        self.log("app is up to date.")
            except Exception as e: self.log(f"Update check failed: {e}")
        threading.Thread(target=run_check, daemon=True).start()

    def show_update_popup(self, new_v):
        if messagebox.askyesno("Update Available", f"A new version of Simph Studio (Ver {new_v}) is available!\n\nWould you like to download and install it now? (The app will restart)."):
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
            resp = requests.get(self.API_LATEST_URL).json()
            download_url = next(a["browser_download_url"] for a in resp.get("assets", []) if a["name"].endswith(".zip"))
            zip_path = os.path.join(self.settings.appdata_dir, "update.zip")
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)

            extract_dir = os.path.join(self.settings.appdata_dir, "update_extracted")
            if os.path.exists(extract_dir): shutil.rmtree(extract_dir, ignore_errors=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(extract_dir)

            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
                exe_name = os.path.basename(current_exe)
                new_exe_path = next((os.path.join(r, f) for r, d, f_list in os.walk(extract_dir) for f in f_list if f.lower().endswith('.exe')), None)
                
                if not new_exe_path:
                    raise Exception("No executable found in the downloaded update zip.")

                bat_path = os.path.join(self.settings.appdata_dir, "update.bat")
                
                bat_content = f"""@echo off\necho Installing Update...\ntimeout /t 3 /nobreak > NUL\ntaskkill /F /IM "{exe_name}" > NUL 2>&1\ntimeout /t 1 /nobreak > NUL\nren "{current_exe}" "{exe_name}.old" > NUL 2>&1\nmove /Y "{new_exe_path}" "{current_exe}" > NUL 2>&1\nstart "" "{current_exe}"\nrmdir /S /Q "{extract_dir}" > NUL 2>&1\ndel "{zip_path}" > NUL 2>&1\ndel "%~f0" > NUL 2>&1\n"""
                with open(bat_path, "w") as f: f.write(bat_content)
                
                subprocess.Popen(['cmd.exe', '/c', bat_path], env=os.environ, creationflags=0x08000000)
                self.quit()
                self.destroy()
                os._exit(0) 
            else:
                self.after(0, self.update_window.destroy)
        except Exception as e:
            self.log(f"Auto-Update failed: {e}")
            self.after(0, self.update_window.destroy)

    def open_calendar(self):
        CalendarModal(self, self.selected_start_date, self.on_date_selected)

    def on_date_selected(self, chosen_date):
        self.selected_start_date = chosen_date
        self.update_date_displays()
        self.schedule_preview()

    def update_date_displays(self):
        sd = self.selected_start_date
        ed = sd + datetime.timedelta(days=6)
        self.planner_tab.date_btn.configure(text=f"📅 Start Date: {sd.strftime('%Y-%m-%d')}")
        self.planner_tab.header_sub_entry.configure(state="normal")
        self.planner_tab.header_sub_entry.delete(0, 'end')
        self.planner_tab.header_sub_entry.insert(0, f"{sd.strftime('%B %d')} - {ed.strftime('%B %d')}".upper())

    def show_help_popup(self):
        self.setup_guide.show_help_popup()

    def on_preview_resize(self, event):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self.prev_width = event.width
        self.prev_height = event.height
        self._resize_timer = self.after(200, self.schedule_preview)

    def schedule_preview(self, *args):
        if self._preview_timer:
            self.after_cancel(self._preview_timer)
        self._preview_timer = self.after(300, self._generate_preview_image)

    def _generate_preview_image(self):
        try:
            ui_state = {
                "header_text": self.planner_tab.header_entry.get(),
                "header_sub_text": self.planner_tab.header_sub_entry.get(),
                "header_size": self.cfg.get("header_size", 100),
                "sub_size": self.cfg.get("sub_size", 40),
                "logo_size": self.cfg.get("logo_size", 200),
                "bg_zoom": self.cfg.get("bg_zoom", 100),
                "box_opacity": self.cfg.get("box_opacity", 240),
                "font": self.planner_tab.font_menu.get(),
                "my_zone": self.settings_tab.my_zone.get(),
                "sec_zone": self.settings_tab.sec_zone.get(),
                "max_box_h": self.cfg.get("max_box_h", 250),
                "time_fmt": self.settings_tab.time_fmt.get(),
                "show_primary": self.settings_tab.show_primary.get(),
                "sponsor_title": self.planner_tab.sponsor_title.get(),
                "goal_current": self.planner_tab.goal_current.get(),
                "goal_target": self.planner_tab.goal_target.get(),
                "game_size": self.cfg.get("game_size", 45),
                "subtitle_size": self.cfg.get("subtitle_size", 30),
                "drop_shadow": self.planner_tab.drop_shadow_var.get(),
                "text_outline": self.planner_tab.text_outline_var.get()
            }

            checked_days = []
            for item in self.planner_tab.days_ui_list:
                if item["check"].get():
                    day_data = {
                        "code": item["code"],
                        "game": item["game"].get(),
                        "sub": item["sub"].get(),
                        "note": item["note"].get() if "note" in item else "",
                        "time": item["time"].get(),
                        "offline": item["offline"].get(),
                        "cancelled": item["cancelled"].get(),
                        "custom_art": item["custom_art"]
                    }
                    checked_days.append(day_data)

            img = self.renderer.render(
                target_format=self.planner_tab.canvas_format.get(), 
                config=self.cfg, 
                ui_state=ui_state, 
                checked_days=checked_days, 
                art_cache=self.art_cache, 
                time_converter=self.time_converter
            )

            cw, ch = img.size
            max_preview_w = getattr(self, 'prev_width', 950) - 20
            max_preview_h = getattr(self, 'prev_height', 850) - 20
            if max_preview_w < 100: max_preview_w = 950
            if max_preview_h < 100: max_preview_h = 850
            
            scale = min(max_preview_w/cw, max_preview_h/ch)
            scaled_w, scaled_h = int(cw * scale), int(ch * scale)
            
            p_ready = ctk.CTkImage(light_image=img, dark_image=img, size=(scaled_w, scaled_h))
            self.planner_tab.preview_label.configure(image=p_ready, text="", width=scaled_w, height=scaled_h)
        except Exception as e: 
            pass

    async def up_art(self, game_name, day_code):
        cache_path = await self.twitch_client.download_game_art(game_name, day_code)
        if cache_path and os.path.exists(cache_path):
            cache_dir = os.path.join(self.settings.appdata_dir, "art_cache")
            
            if day_code in self.art_cache and self.art_cache[day_code] and os.path.exists(self.art_cache[day_code]):
                try: os.remove(self.art_cache[day_code])
                except: pass
            
            safe_path = os.path.join(cache_dir, f"art_{day_code}_{int(time.time())}.jpg")
            try:
                shutil.move(cache_path, safe_path)
                self.art_cache[day_code] = safe_path
            except Exception:
                self.art_cache[day_code] = cache_path
                
            self.after(0, self.schedule_preview)

    def start_export(self):
        base_dir = self.planner_tab.export_path_var.get().strip()
        if not base_dir or not os.path.isdir(base_dir):
            base_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'Simph_Schedules')
        
        os.makedirs(base_dir, exist_ok=True)
        self.log(f"Exporting selected formats to: {base_dir} ...")
        
        ui_state = {
            "header_text": self.planner_tab.header_entry.get(),
            "header_sub_text": self.planner_tab.header_sub_entry.get(),
            "header_size": self.cfg.get("header_size", 100),
            "sub_size": self.cfg.get("sub_size", 40),
            "logo_size": self.cfg.get("logo_size", 200),
            "bg_zoom": self.cfg.get("bg_zoom", 100),
            "box_opacity": self.cfg.get("box_opacity", 240),
            "font": self.planner_tab.font_menu.get(),
            "my_zone": self.settings_tab.my_zone.get(),
            "sec_zone": self.settings_tab.sec_zone.get(),
            "max_box_h": self.cfg.get("max_box_h", 250),
            "time_fmt": self.settings_tab.time_fmt.get(),
            "show_primary": self.settings_tab.show_primary.get(),
            "sponsor_title": self.planner_tab.sponsor_title.get(),
            "goal_current": self.planner_tab.goal_current.get(),
            "goal_target": self.planner_tab.goal_target.get(),
            "game_size": self.cfg.get("game_size", 45),
            "subtitle_size": self.cfg.get("subtitle_size", 30),
            "drop_shadow": self.planner_tab.drop_shadow_var.get(),
            "text_outline": self.planner_tab.text_outline_var.get()
        }
        
        checked_days = [ {"code": i["code"], "game": i["game"].get(), "sub": i["sub"].get(), "note": i["note"].get() if "note" in i else "", "time": i["time"].get(), "offline": i["offline"].get(), "cancelled": i["cancelled"].get(), "custom_art": i["custom_art"]} for i in self.planner_tab.days_ui_list if i["check"].get() ]

        saved_count = 0
        for r_name, var in self.planner_tab.export_vars.items():
            if var.get():
                try:
                    e_img = self.renderer.render(r_name, self.cfg, ui_state, checked_days, self.art_cache, self.time_converter)
                    safe_name = r_name.split(' ')[0].replace(':', 'x')
                    e_path = os.path.join(base_dir, f"Schedule_{self.selected_start_date.strftime('%b%d')}_{safe_name}.png")
                    e_img.convert("RGBA").save(e_path)
                    saved_count += 1
                    self.update() 
                except Exception as e: self.log(f"Failed to export {r_name}: {e}")
        
        if saved_count > 0: self.log(f"Successfully exported {saved_count} image(s)!")
        else: self.log("No formats ticked for export!")
        self.after(100, self.schedule_preview)

    def start_deploy(self): 
        threading.Thread(target=lambda: asyncio.run(self.run_engine()), daemon=True).start()

    async def run_engine(self):
        self.log("Starting Global Deployment...")
        self.update()
        
        deploy_target = self.planner_tab.deploy_format.get()
        ui_state = {
            "header_text": self.planner_tab.header_entry.get(),
            "header_sub_text": self.planner_tab.header_sub_entry.get(),
            "header_size": self.cfg.get("header_size", 100),
            "sub_size": self.cfg.get("sub_size", 40),
            "logo_size": self.cfg.get("logo_size", 200),
            "bg_zoom": self.cfg.get("bg_zoom", 100),
            "box_opacity": self.cfg.get("box_opacity", 240),
            "font": self.planner_tab.font_menu.get(),
            "my_zone": self.settings_tab.my_zone.get(),
            "sec_zone": self.settings_tab.sec_zone.get(),
            "max_box_h": self.cfg.get("max_box_h", 250),
            "time_fmt": self.settings_tab.time_fmt.get(),
            "show_primary": self.settings_tab.show_primary.get(),
            "sponsor_title": self.planner_tab.sponsor_title.get(),
            "goal_current": self.planner_tab.goal_current.get(),
            "goal_target": self.planner_tab.goal_target.get(),
            "game_size": self.cfg.get("game_size", 45),
            "subtitle_size": self.cfg.get("subtitle_size", 30),
            "drop_shadow": self.planner_tab.drop_shadow_var.get(),
            "text_outline": self.planner_tab.text_outline_var.get()
        }
        
        checked_days = [ {"code": i["code"], "game": i["game"].get(), "sub": i["sub"].get(), "note": i["note"].get() if "note" in i else "", "time": i["time"].get(), "offline": i["offline"].get(), "cancelled": i["cancelled"].get(), "custom_art": i["custom_art"]} for i in self.planner_tab.days_ui_list if i["check"].get() ]

        try:
            deploy_img = self.renderer.render(deploy_target, self.cfg, ui_state, checked_days, self.art_cache, self.time_converter)
            self.temp_deploy_path = os.path.join(self.settings.appdata_dir, "temp_deploy.jpg")
            deploy_img.convert("RGB").save(self.temp_deploy_path, quality=95)
        except Exception as e:
            self.log(f"Failed to render deployment image: {e}")
            return
            
        time.sleep(1.5)

        # --- FIXED: Delete old schedules from BOTH channels ---
        del_success, del_msg = self.discord_client.delete_old_schedule(self.cfg.get("last_msg_id", ""))
        self.log(f"Primary Discord: {del_msg}")
        
        if self.cfg.get('webhook_sec'):
            del_sec, del_msg_sec = self.discord_client_sec.delete_old_schedule(self.cfg.get("last_msg_id_sec", ""))
            self.log(f"Secondary Discord: {del_msg_sec}")

        sub_text = self.planner_tab.header_sub_entry.get().strip()
        discord_msg = f"# {sub_text}\n\n" if sub_text else "# STREAM SCHEDULE\n\n"
        
        base_dt = self.selected_start_date
        has_ticked_days = False
        
        twitch_segments = []

        for i, code in enumerate(self.all_days):
            item = self.planner_tab.days_ui_list[i]
            if item["check"].get():
                has_ticked_days = True
                g_val = item['game'].get().strip() or "TBA"
                
                sub_val = item['sub'].get().strip()
                sub_str = f" | {sub_val}" if sub_val else ""
                
                note_val = item['note'].get().strip() if "note" in item else ""
                
                t_val = item['time'].get()
                is_off = item['offline'].get()
                is_can = item['cancelled'].get()
                
                if is_can:
                    discord_msg += f"- ~~`{self.full_days[code]}` - {g_val}{sub_str}~~ **[CANCELLED]**\n"
                elif is_off:
                    discord_msg += f"- `{self.full_days[code]}` - **OFFLINE**\n"
                elif t_val == "TBA":
                    discord_msg += f"- `{self.full_days[code]}` - **{g_val}**{sub_str} (Time TBA)\n"
                else:
                    try:
                        import pytz
                        h, m = map(int, t_val.split(':'))
                        tz_str = self.tz_map.get(self.settings_tab.my_zone.get(), "Europe/London")
                        loc_tz = pytz.timezone(tz_str)
                        target_dt = loc_tz.localize(datetime.datetime(base_dt.year, base_dt.month, base_dt.day, h, m) + datetime.timedelta(days=i))
                        unix_ts = int(target_dt.timestamp())
                        discord_msg += f"- `{self.full_days[code]}` - **{g_val}**{sub_str} <t:{unix_ts}:t>\n"
                        
                        twitch_segments.append({
                            "start_dt": target_dt.replace(tzinfo=None), 
                            "timezone": tz_str,
                            "duration": "240",
                            "category_id": self.game_ids.get(g_val, ""),
                            "title": g_val
                        })
                    except: discord_msg += f"- `{self.full_days[code]}` - **{g_val}**{sub_str} (Time Error)\n"
                
                if note_val:
                    discord_msg += f"*{note_val}*\n"
        
        if not has_ticked_days: discord_msg += "No streams scheduled for this week!"

        # --- FIXED: Deploy to Primary Channel ---
        up_success, new_msg_id, up_msg = self.discord_client.deploy_schedule(discord_msg, self.temp_deploy_path)
        if up_success:
            self.cfg["last_msg_id"] = new_msg_id
            self.settings.save_settings()
            self.log(f"Primary Discord: {up_msg}")
        else:
            self.log(f"Primary Discord: {up_msg}")

        # --- FIXED: Deploy to Secondary Channel ---
        if self.cfg.get('webhook_sec'):
            up_sec, new_id_sec, up_msg_sec = self.discord_client_sec.deploy_schedule(discord_msg, self.temp_deploy_path)
            if up_sec:
                self.cfg["last_msg_id_sec"] = new_id_sec
                self.settings.save_settings()
                self.log(f"Secondary Discord: {up_msg_sec}")
            else:
                self.log(f"Secondary Discord: {up_msg_sec}")
        
        # Clean up the file instantly after both deploys finish
        try:
            if os.path.exists(self.temp_deploy_path):
                os.remove(self.temp_deploy_path)
        except: pass

        if self.cfg.get('t_tok'):
            self.log("Syncing Twitch Dashboard...")
            try:
                await self.twitch_client.sync_schedule(twitch_segments)
                self.log("Twitch Dashboard: SYNCED.")
            except Exception as e:
                self.log(f"Twitch Error: {e}")

    def refresh_status(self):
        t_id = len(self.cfg.get("t_id", "")) > 5
        t_tok = len(self.cfg.get("t_tok", "")) > 10
        disc = "discord.com" in self.cfg.get("webhook", "").lower()
        
        self.st_twitch_api.configure(text=f"● Twitch: {'READY' if t_id else 'MISSING'}", text_color="#00FF00" if t_id else "#FF3333")
        self.st_twitch_tok.configure(text=f"● Token: {'ACTIVE' if t_tok else 'MISSING'}", text_color="#00FF00" if t_tok else "#FF3333")
        self.st_discord.configure(text=f"● Discord: {'READY' if disc else 'MISSING'}", text_color="#00FF00" if disc else "#FF3333")