import customtkinter as ctk
import tkinter as tk
import threading
import asyncio
import os
from tkinter import filedialog, colorchooser

class PlannerTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.days_ui_list = []
        self.export_vars = {}
        self.search_timers = {}
        self.setup_ui()

    def add_section_header(self, parent_frame, text):
        ctk.CTkLabel(parent_frame, text=text, font=("Arial", 12, "bold"), text_color="#AAAAAA").pack(pady=(15, 5))

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        
        # Adjusted to 45/55 Split
        self.grid_columnconfigure(0, weight=45) 
        self.grid_columnconfigure(1, weight=55)

        self.left_container = ctk.CTkFrame(self, fg_color="transparent")
        self.left_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.prev_container = ctk.CTkFrame(self, fg_color="transparent")
        self.prev_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.preview_label = ctk.CTkLabel(self.prev_container, text="Loading Preview...", fg_color="transparent")
        self.preview_label.place(relx=0.5, rely=0.5, anchor="center")
        self.prev_container.bind("<Configure>", self.app.on_preview_resize)

        self.build_weekly_view()
        self.build_canvas_view()
        self.build_export_view()

    def switch_view(self, view_name):
        self.weekly_frame.pack_forget()
        self.design_frame.pack_forget()
        self.export_frame.pack_forget()

        if view_name == "weekly":
            self.weekly_frame.pack(side="left", fill="both", expand=True)
        elif view_name == "canvas":
            self.design_frame.pack(side="left", fill="both", expand=True)
        elif view_name == "export":
            self.export_frame.pack(side="left", fill="both", expand=True)

    def build_weekly_view(self):
        self.weekly_frame = ctk.CTkScrollableFrame(self.left_container, label_text="WEEKLY SCHEDULE TICKBOXES")
        
        self.date_btn = ctk.CTkButton(self.weekly_frame, text="📅 Click to Select Start Date...", height=40, font=("Arial", 14, "bold"), command=self.app.open_calendar)
        self.date_btn.pack(fill="x", padx=5, pady=(0, 15))

        time_opts = ["TBA"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
        saved_layout = self.app.cfg.get("saved_schedule_layout", [])
        
        for i in range(7):
            df = ctk.CTkFrame(self.weekly_frame)
            df.pack(pady=5, fill="x")
            
            chk = ctk.CTkCheckBox(df, text="", width=20, command=self.app.schedule_preview)
            chk.grid(row=0, column=0, padx=2)
            
            ctk.CTkLabel(df, text=self.app.all_days[i], width=40, font=("Arial", 12, "bold")).grid(row=0, column=1)
            
            g_wrap = ctk.CTkFrame(df, fg_color="transparent")
            g_wrap.grid(row=0, column=2, padx=2)
            
            gm = ctk.CTkEntry(g_wrap, width=170, placeholder_text="Game...")
            gm.pack()
            gm.bind("<KeyRelease>", lambda e, idx=i: self.on_key_release(e, idx))
            
            s_f = ctk.CTkFrame(g_wrap, height=0, fg_color="#222")
            s_f.pack(fill="x")
            
            sub = ctk.CTkEntry(df, placeholder_text="Sub...", width=110)
            sub.grid(row=0, column=3, padx=2)
            sub.bind("<KeyRelease>", self.app.schedule_preview)
            
            note = ctk.CTkEntry(df, placeholder_text="Discord Note...", width=130)
            note.grid(row=0, column=4, padx=2)
            
            tm = ctk.CTkOptionMenu(df, values=time_opts, width=80, command=self.app.schedule_preview)
            tm.grid(row=0, column=5, padx=2)
            
            off_chk = ctk.CTkCheckBox(df, text="Offline", width=60, font=("Arial", 11, "bold"), text_color="#AAAAAA", command=self.app.schedule_preview)
            off_chk.grid(row=0, column=6, padx=2)

            cancel_chk = ctk.CTkCheckBox(df, text="Cancel", width=60, font=("Arial", 11, "bold"), text_color="#FF4444", command=self.app.schedule_preview)
            cancel_chk.grid(row=0, column=7, padx=2)
            
            art_btn = ctk.CTkButton(df, text="🖼️", width=30, fg_color="#444", command=lambda idx=i: self.pick_custom_art(idx))
            art_btn.grid(row=0, column=8, padx=2)

            custom_art_path = None
            game_to_fetch = None

            if saved_layout and len(saved_layout) == 7:
                sv = saved_layout[i]
                
                if sv.get("check", True): chk.select()
                else: chk.deselect()
                    
                gm.insert(0, sv.get("game", ""))
                sub.insert(0, sv.get("sub", ""))
                if "note" in sv:
                    note.insert(0, sv.get("note", ""))
                tm.set(sv.get("time", "20:00"))
                
                if sv.get("offline"): off_chk.select()
                if sv.get("cancelled"): cancel_chk.select()
                if sv.get("custom_art"):
                    custom_art_path = sv.get("custom_art")
                    art_btn.configure(fg_color="green")
                
                if sv.get("game", "").strip() and not custom_art_path:
                    game_to_fetch = sv.get("game", "").strip()
            else:
                chk.select()
                tm.set("20:00")
            
            self.days_ui_list.append({
                "check": chk, "game": gm, "sub": sub, "note": note, "time": tm, 
                "suggest": s_f, "code": self.app.all_days[i], "offline": off_chk, 
                "cancelled": cancel_chk, "custom_art": custom_art_path, "art_btn": art_btn
            })

            if game_to_fetch:
                threading.Thread(
                    target=lambda v=game_to_fetch, c=self.app.all_days[i]: asyncio.run(self.app.up_art(v, c)), 
                    daemon=True
                ).start()

        btn_action_f2 = ctk.CTkFrame(self.weekly_frame, fg_color="transparent")
        btn_action_f2.pack(fill="x", padx=5, pady=(15, 5))
        ctk.CTkButton(btn_action_f2, text="💾 Save Layout", height=35, fg_color="#21612b", hover_color="#184a1f", font=("Arial", 13, "bold"), command=self.save_schedule_layout).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_action_f2, text="🧹 Clear Days", height=35, fg_color="#801010", hover_color="#5e0b0b", font=("Arial", 13, "bold"), command=self.clear_schedule_layout).pack(side="right", expand=True, padx=(5, 0))

    def build_canvas_view(self):
        self.design_frame = ctk.CTkScrollableFrame(self.left_container, label_text="VISUAL DESIGN")
        
        self.header_entry = ctk.CTkEntry(self.design_frame)
        self.header_entry.pack(fill="x", padx=10, pady=5)
        self.header_entry.insert(0, self.app.cfg.get("header_text", "STREAMER SCHEDULE"))
        self.header_entry.bind("<KeyRelease>", self.app.schedule_preview)
        
        self.header_sub_entry = ctk.CTkEntry(self.design_frame)
        self.header_sub_entry.pack(fill="x", padx=10, pady=5)
        self.header_sub_entry.bind("<KeyRelease>", self.app.schedule_preview)
        
        self.add_section_header(self.design_frame, "--- PREVIEW CANVAS ---")
        
        def on_canvas_change(val):
            self.app.cfg["canvas_format"] = val
            self.app.schedule_preview()
            
        self.canvas_format = ctk.CTkOptionMenu(self.design_frame, values=list(self.app.ratios.keys()), command=on_canvas_change)
        self.canvas_format.pack(fill="x", padx=10, pady=5)
        
        saved_canvas = self.app.cfg.get("canvas_format", "9:16 (TikTok/Reels/Shorts)")
        if saved_canvas in self.app.ratios.keys():
            self.canvas_format.set(saved_canvas)
        else:
            self.canvas_format.set("9:16 (TikTok/Reels/Shorts)")
        
        btn_f1 = ctk.CTkFrame(self.design_frame, fg_color="transparent")
        btn_f1.pack(fill="x", padx=10, pady=2)
        ctk.CTkButton(btn_f1, text="📁 Background", command=self.pick_bg).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(btn_f1, text="🖼️ Logo", command=self.pick_logo).pack(side="right", expand=True, padx=2)
        
        self.bg_zoom_slider = self.add_slider(self.design_frame, "Background Zoom", "bg_zoom", 25, 300)
        self.logo_size_slider = self.add_slider(self.design_frame, "Top Logo Size", "logo_size", 100, 750) 

        self.add_section_header(self.design_frame, "--- SPECIAL EFFECTS ---")
        self.drop_shadow_var = tk.BooleanVar(value=self.app.cfg.get("drop_shadow", True))
        ctk.CTkCheckBox(self.design_frame, text="Enable Drop Shadows", variable=self.drop_shadow_var, command=self.app.schedule_preview).pack(anchor="w", padx=15, pady=2)
        
        self.text_outline_var = tk.BooleanVar(value=self.app.cfg.get("text_outline", True))
        ctk.CTkCheckBox(self.design_frame, text="Enable Text Outlines", variable=self.text_outline_var, command=self.app.schedule_preview).pack(anchor="w", padx=15, pady=(2, 10))
        
        self.add_section_header(self.design_frame, "--- SPONSOR & GOALS ---")
        self.btn_sponsor_logo = ctk.CTkButton(
            self.design_frame, 
            text="❌ Remove Logo" if self.app.cfg.get("sponsor_path") else "📁 Set Sponsor Logo", 
            fg_color="green" if self.app.cfg.get("sponsor_path") else ["#3a7ebf", "#1f538d"], 
            command=self.pick_sponsor
        )
        self.btn_sponsor_logo.pack(fill="x", padx=10, pady=2)
        
        self.sponsor_title = ctk.CTkEntry(self.design_frame, placeholder_text="Goal Title (e.g. Sub Goal)")
        self.sponsor_title.pack(fill="x", padx=10, pady=(5, 2))
        self.sponsor_title.bind("<KeyRelease>", self.app.schedule_preview)
        self.sponsor_title.insert(0, self.app.cfg.get("sponsor_title", ""))

        goal_f = ctk.CTkFrame(self.design_frame, fg_color="transparent")
        goal_f.pack(fill="x", padx=10, pady=2)
        self.goal_current = ctk.CTkEntry(goal_f, width=80, placeholder_text="Current (0)")
        self.goal_current.pack(side="left", expand=True, padx=(0, 2))
        self.goal_current.bind("<KeyRelease>", self.app.schedule_preview)
        self.goal_current.insert(0, self.app.cfg.get("goal_current", ""))
        
        ctk.CTkLabel(goal_f, text="/").pack(side="left")
        
        self.goal_target = ctk.CTkEntry(goal_f, width=80, placeholder_text="Target (100)")
        self.goal_target.pack(side="right", expand=True, padx=(2, 0))
        self.goal_target.bind("<KeyRelease>", self.app.schedule_preview)
        self.goal_target.insert(0, self.app.cfg.get("goal_target", ""))

        self.add_section_header(self.design_frame, "--- TEXT & COLORS ---")
        
        font_f = ctk.CTkFrame(self.design_frame, fg_color="transparent")
        font_f.pack(fill="x", padx=10, pady=5)
        
        def on_font_select(val):
            self.app.cfg["custom_font_path"] = ""
            self.app.schedule_preview()

        self.font_menu = ctk.CTkOptionMenu(font_f, values=list(self.app.font_map.keys()), command=on_font_select)
        self.font_menu.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        if self.app.cfg.get("custom_font_path"):
            self.font_menu.set("--- CUSTOM FONT ---")
        else:
            self.font_menu.set(self.app.cfg.get("font", "Arial Black"))
            
        ctk.CTkButton(font_f, text="📁 Import .TTF", width=100, command=self.pick_custom_font).pack(side="right")
        
        self.header_size_slider = self.add_slider(self.design_frame, "Main Title Size", "header_size", 50, 200)
        self.header_sub_size_slider = self.add_slider(self.design_frame, "Date Range Size", "sub_size", 20, 100)
        self.game_size_slider = self.add_slider(self.design_frame, "Game Title Size", "game_size", 20, 120)
        self.sub_size_slider = self.add_slider(self.design_frame, "Subtitle Size", "subtitle_size", 15, 80)
        
        col_f = ctk.CTkFrame(self.design_frame, fg_color="transparent")
        col_f.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(col_f, text="🎨 Box Background", command=lambda: self.pick_color_generic("box_color")).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Box Text", command=lambda: self.pick_color_generic("box_txt_color")).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Main Title Text", command=lambda: self.pick_color_generic("header_txt_color")).grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Date Range Text", command=lambda: self.pick_color_generic("sub_txt_color")).grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Game Subtitle", command=lambda: self.pick_color_generic("subtitle_color")).grid(row=2, column=0, padx=2, pady=2, sticky="ew")
        ctk.CTkButton(col_f, text="🎨 Time Text", command=lambda: self.pick_color_generic("time_color")).grid(row=2, column=1, padx=2, pady=2, sticky="ew")
        
        col_f.grid_columnconfigure(0, weight=1)
        col_f.grid_columnconfigure(1, weight=1)

        self.add_section_header(self.design_frame, "--- SCHEDULE BOX SETTINGS ---")
        self.max_box_slider = self.add_slider(self.design_frame, "Max Box Height", "max_box_h", 150, 750) 
        self.box_opacity_slider = self.add_slider(self.design_frame, "Box Opacity", "box_opacity", 0, 255)

    def build_export_view(self):
        self.export_frame = ctk.CTkScrollableFrame(self.left_container, label_text="EXPORT OPTIONS")
        
        path_f = ctk.CTkFrame(self.export_frame, fg_color="transparent")
        path_f.pack(fill="x", padx=10, pady=(15, 5))
        self.export_path_var = tk.StringVar(value=self.app.cfg.get("export_path", ""))
        ctk.CTkEntry(path_f, textvariable=self.export_path_var, placeholder_text="Custom Export Folder...", state="normal").pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(path_f, text="📁", width=30, command=self.pick_export_path).pack(side="right")

        self.add_section_header(self.export_frame, "Formats to Local Export:")
        for r_name in self.app.ratios.keys():
            var = ctk.BooleanVar(value=True if "9:16" in r_name else False)
            ctk.CTkCheckBox(self.export_frame, text=r_name, variable=var, height=20, font=("Arial", 11)).pack(anchor="w", padx=15, pady=2)
            self.export_vars[r_name] = var

        ctk.CTkLabel(self.export_frame, text="Discord Deploy Format:", text_color="#AAAAAA", font=("Arial", 10)).pack(anchor="w", padx=10, pady=(20, 0))
        self.deploy_format = ctk.CTkOptionMenu(self.export_frame, values=list(self.app.ratios.keys()))
        self.deploy_format.pack(fill="x", padx=10, pady=5)
        self.deploy_format.set(self.app.cfg.get("deploy_format", "9:16 (TikTok/Reels/Shorts)"))

        btn_action_f = ctk.CTkFrame(self.export_frame, fg_color="transparent")
        btn_action_f.pack(fill="x", padx=10, pady=(30, 20))
        ctk.CTkButton(btn_action_f, text="💾 EXPORT", height=50, fg_color="#21612b", hover_color="#184a1f", font=("Arial", 16, "bold"), command=self.app.start_export).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_action_f, text="🚀 DEPLOY", height=50, fg_color="#801010", hover_color="#5e0b0b", font=("Arial", 16, "bold"), command=self.app.start_deploy).pack(side="right", fill="x", expand=True, padx=(5, 0))

    def add_slider(self, p, lbl_text, key, min_val, max_val):
        lbl = ctk.CTkLabel(p, text=lbl_text)
        lbl.pack(anchor="w", padx=10)
        
        def on_slide(val):
            percent = int(float(val))
            actual_val = int(min_val + (max_val - min_val) * (percent / 100.0))
            self.app.cfg[key] = actual_val
            lbl.configure(text=f"{lbl_text}: {percent}%")
            self.app.schedule_preview()
            
        s = ctk.CTkSlider(p, from_=0, to=100, command=on_slide)
        s.pack(fill="x", padx=10, pady=(0, 5))
        
        current_pixel = self.app.cfg.get(key, min_val)
        if max_val > min_val:
            current_percent = int(((current_pixel - min_val) / (max_val - min_val)) * 100)
        else:
            current_percent = 0
            
        current_percent = max(0, min(100, current_percent))
        
        s.set(current_percent)
        lbl.configure(text=f"{lbl_text}: {current_percent}%")
        return s

    def save_schedule_layout(self):
        sched_data = []
        for item in self.days_ui_list:
            sched_data.append({
                "check": item["check"].get(),
                "game": item["game"].get(),
                "sub": item["sub"].get(),
                "note": item["note"].get(),
                "time": item["time"].get(),
                "offline": item["offline"].get(),
                "cancelled": item["cancelled"].get(),
                "custom_art": item["custom_art"]
            })
        self.app.cfg["saved_schedule_layout"] = sched_data
        self.app.settings.save_settings()
        self.app.log("✅ Weekly schedule layout saved!")

    def clear_schedule_layout(self):
        for item in self.days_ui_list:
            item["game"].delete(0, 'end')
            item["sub"].delete(0, 'end')
            item["note"].delete(0, 'end')
            item["time"].set("20:00")
            item["offline"].deselect()
            item["cancelled"].deselect()
            item["custom_art"] = None
            item["art_btn"].configure(fg_color="#444")
        self.app.schedule_preview()
        self.app.log("🧹 Schedule fields cleared.")

    def pick_export_path(self):
        self.export_path_var.set(filedialog.askdirectory())
        self.app.save_settings()

    def pick_sponsor(self):
        if self.app.cfg.get("sponsor_path"):
            self.app.cfg["sponsor_path"] = ""
            self.btn_sponsor_logo.configure(fg_color=["#3a7ebf", "#1f538d"], text="📁 Set Sponsor/Goal Logo")
        else:
            p = filedialog.askopenfilename()
            if p: 
                self.app.cfg["sponsor_path"] = p
                self.btn_sponsor_logo.configure(fg_color="green", text="❌ Remove Logo")
        self.app.schedule_preview()

    def pick_custom_art(self, idx):
        if self.days_ui_list[idx]["custom_art"]:
            self.days_ui_list[idx]["custom_art"] = None
            self.days_ui_list[idx]["art_btn"].configure(fg_color="#444")
        else:
            p = filedialog.askopenfilename()
            if p:
                self.days_ui_list[idx]["custom_art"] = p
                self.days_ui_list[idx]["art_btn"].configure(fg_color="green")
        self.app.schedule_preview()

    def pick_color_generic(self, key):
        c = colorchooser.askcolor(initialcolor=self.app.cfg.get(key, "#FFFFFF"))
        if c[1]: 
            self.app.cfg[key] = c[1]
            self.app.settings.save_settings()
            self.app.schedule_preview()
            
    def pick_custom_font(self):
        p = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if p:
            self.app.cfg["custom_font_path"] = p
            self.font_menu.set("--- CUSTOM FONT ---")
            self.app.settings.save_settings()
            self.app.schedule_preview()

    def pick_bg(self):
        p = filedialog.askopenfilename()
        if p: 
            self.app.cfg["bg_path"] = p
            self.app.schedule_preview()

    def pick_logo(self):
        p = filedialog.askopenfilename()
        if p: 
            self.app.cfg["logo_path"] = p
            self.app.schedule_preview()

    def on_key_release(self, e, idx):
        self.app.schedule_preview()
        d_code = self.days_ui_list[idx]["code"]
        if d_code in self.search_timers: 
            self.search_timers[d_code].cancel()
        self.search_timers[d_code] = threading.Timer(0.5, lambda: asyncio.run(self.fetch_sugg(idx)))
        self.search_timers[d_code].start()

    async def fetch_sugg(self, idx):
        q = self.days_ui_list[idx]["game"].get()
        if len(q) < 3: return
        try:
            res = await self.app.twitch_client.search_categories(q)
            if res: self.after(0, lambda: self.show_suggest(idx, res[:5]))
        except: pass

    def show_suggest(self, idx, res):
        self.hide_all_suggest()
        f = self.days_ui_list[idx]["suggest"]
        f.configure(height=150)
        for r in res: 
            ctk.CTkButton(f, text=r.name, fg_color="transparent", anchor="w", height=28, command=lambda v=r.name, gid=r.id, i=idx: self.select_game(i, v, gid)).pack(fill="x")

    def hide_all_suggest(self):
        for item in self.days_ui_list:
            item["suggest"].configure(height=0)
            for widget in item["suggest"].winfo_children(): widget.destroy()

    def select_game(self, idx, val, gid):
        self.days_ui_list[idx]["game"].delete(0, 'end')
        self.days_ui_list[idx]["game"].insert(0, val)
        self.app.game_ids[val] = gid
        self.hide_all_suggest()
        self.focus()
        threading.Thread(target=lambda: asyncio.run(self.app.up_art(val, self.days_ui_list[idx]["code"])), daemon=True).start()