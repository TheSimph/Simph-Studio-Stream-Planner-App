import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps

class ImageRenderer:
    def __init__(self):
        self.ratios = {
            "9:16 (TikTok/Reels/Shorts)": (1080, 1920),
            "16:9 (Desktop/YouTube)": (1920, 1080),
            "16:9 (Desktop Transparent)": (1920, 1080),
            "1:1 (Square/Instagram)": (1080, 1080),
            "4:5 (Vertical Post)": (1080, 1350)
        }

        # Expanded font library
        self.font_map = {
            "Arial": "arial.ttf", "Arial Black": "ariblk.ttf", "Bahnschrift": "bahnschrift.ttf",
            "Bookman Old Style": "bookosb.ttf", "Calibri": "calibri.ttf", "Calibri Bold": "calibrib.ttf",
            "Cambria": "cambria.ttc", "Candara": "candara.ttf", "Century Gothic": "gothicb.ttf", 
            "Comic Sans MS": "comic.ttf", "Consolas": "consola.ttf", "Constantia": "constan.ttf",
            "Corbel": "corbel.ttf", "Courier New": "cour.ttf", "Franklin Gothic Medium": "framd.ttf",
            "Gabriola": "gabriola.ttf", "Georgia": "georgia.ttf", "Impact": "impact.ttf",
            "Lucida Console": "lucon.ttf", "Lucida Sans Unicode": "l_10646.ttf", 
            "Microsoft Sans Serif": "micross.ttf", "Palatino Linotype": "pala.ttf", 
            "Segoe UI": "segoeui.ttf", "Segoe UI Black": "seguibl.ttf", "Tahoma": "tahoma.ttf", 
            "Times New Roman": "times.ttf", "Trebuchet MS": "trebuc.ttf", "Verdana": "verdana.ttf"
        }

    def hex_to_rgb(self, hex_color):
        try: return tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        except: return (255, 255, 255)

    def get_f_path(self, font_name, size, custom_font_path=None):
        if custom_font_path and os.path.exists(custom_font_path):
            try: return ImageFont.truetype(custom_font_path, max(1, size))
            except: pass
            
        font_file = self.font_map.get(font_name, "ariblk.ttf")
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        p = os.path.join(windir, 'Fonts', font_file)
        if not os.path.exists(p): p = os.path.join(windir, 'Fonts', 'arial.ttf')
        return ImageFont.truetype(p if os.path.exists(p) else "arial.ttf", max(1, size))

    def wrap_text_pil(self, text, font, max_width):
        if not text: return []
        lines = []
        words = text.split()
        current_line = ""
        for word in words:
            test_line = current_line + word + " " if current_line else word + " "
            if font.getlength(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = word + " "
                else:
                    lines.append(word)
                    current_line = ""
        if current_line: lines.append(current_line.strip())
        return lines

    def render_styled_text(self, draw, pos, text, font, fill, anchor="la", use_shadow=False, use_outline=False):
        x, y = pos
        if use_shadow:
            draw.text((x + 4, y + 4), text, fill=(0, 0, 0, 200), font=font, anchor=anchor)
        if use_outline:
            draw.text(pos, text, fill=fill, font=font, anchor=anchor, stroke_width=2, stroke_fill=(0, 0, 0, 255))
        else:
            draw.text(pos, text, fill=fill, font=font, anchor=anchor)

    def render(self, target_format, config, ui_state, checked_days, art_cache, time_converter):
        sp_title = ui_state.get('sponsor_title', "").strip()
        sp_cur_str = ui_state.get('goal_current', "").strip()
        sp_tgt_str = ui_state.get('goal_target', "").strip()
        sp_path = config.get("sponsor_path", "")
        
        has_goal = bool(sp_title or sp_cur_str or sp_tgt_str)
        has_logo = os.path.exists(sp_path)
        
        cw, ch = self.ratios.get(target_format, (1080, 1920))
        is_landscape = cw > ch
        is_transparent = "Transparent" in target_format
        
        if is_transparent:
            img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        else:
            if os.path.exists(config.get("bg_path", "")) and os.path.isfile(config.get("bg_path", "")):
                base_fit = ImageOps.fit(Image.open(config["bg_path"]).convert("RGBA"), (cw, ch), method=Image.Resampling.LANCZOS)
                zoom = float(ui_state.get("bg_zoom", 100)) / 100.0
                if zoom > 1.0:
                    new_w, new_h = int(cw / zoom), int(ch / zoom)
                    left, top = (cw - new_w) // 2, (ch - new_h) // 2
                    img = base_fit.crop((left, top, left + new_w, top + new_h)).resize((cw, ch), Image.Resampling.LANCZOS)
                elif zoom < 1.0:
                    img = Image.new("RGBA", (cw, ch), (10, 10, 12, 255))
                    fit_w, fit_h = int(cw * zoom), int(ch * zoom)
                    scaled = base_fit.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
                    img.paste(scaled, (cw//2 - fit_w//2, ch//2 - fit_h//2))
                else: 
                    img = base_fit
            else: 
                img = Image.new("RGBA", (cw, ch), (20, 20, 25, 255))
        
        draw = ImageDraw.Draw(img)
        opacity = int(ui_state.get("box_opacity", 240))
        
        # New Independent Color Hooks
        c_box = (*self.hex_to_rgb(config.get("box_color", "#6E1414")), opacity)
        c_head = self.hex_to_rgb(config.get("header_txt_color", "#FFFFFF"))
        c_txt = self.hex_to_rgb(config.get("box_txt_color", "#FFFFFF"))
        c_sub = self.hex_to_rgb(config.get("sub_txt_color", "#C8C8C8")) # Used for Date Range
        c_subtitle = self.hex_to_rgb(config.get("subtitle_color", "#C8C8C8")) # Used for Game Subtitle
        c_time = self.hex_to_rgb(config.get("time_color", "#C8C8C8")) # Used for Timestamp
        
        font_name = ui_state.get("font", "Arial Black")
        custom_font_path = config.get("custom_font_path", None)
        do_shadow = ui_state.get("drop_shadow", True)
        do_outline = ui_state.get("text_outline", True)

        header_y = int(ch * 0.03)
        if os.path.exists(config.get("logo_path", "")):
            l_s = int(ui_state.get("logo_size", 200))
            logo = ImageOps.contain(Image.open(config["logo_path"]).convert("RGBA"), (l_s, l_s))
            img.paste(logo, (cw//2 - (logo.width//2), header_y), logo)
            header_y += l_s + 20 
        
        h_text = ui_state.get("header_text", "STREAMER SCHEDULE").upper()
        h_size = int(ui_state.get("header_size", 100))
        h_lines = self.wrap_text_pil(h_text, self.get_f_path(font_name, h_size, custom_font_path), cw * 0.85)
        for line in h_lines:
            self.render_styled_text(draw, (cw//2, header_y), line, self.get_f_path(font_name, h_size, custom_font_path), c_head, anchor="mt", use_shadow=do_shadow, use_outline=do_outline)
            header_y += h_size + 15
            
        s_text = ui_state.get("header_sub_text", "").upper()
        s_size = int(ui_state.get("sub_size", 40))
        header_y += 10
        s_lines = self.wrap_text_pil(s_text, self.get_f_path(font_name, s_size, custom_font_path), cw * 0.85)
        for line in s_lines:
            self.render_styled_text(draw, (cw//2, header_y), line, self.get_f_path(font_name, s_size, custom_font_path), c_sub, anchor="mt", use_shadow=do_shadow, use_outline=do_outline)
            header_y += s_size + 15

        if checked_days:
            count = len(checked_days)
            
            bottom_padding = 60
            if has_goal: bottom_padding += int(ch * 0.08)
            if sp_title: bottom_padding += int(ch * 0.04)
            if has_logo: bottom_padding += int(ch * 0.12)
            
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
            
            max_allowed = int(ui_state.get("max_box_h", 250))
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
            
            for idx, item in enumerate(checked_days):
                c, r = positions[idx]
                box_x = int(80 + (c * col_w))
                if cols > 1 and c == 0.5: box_x = (cw - box_w) // 2
                y = int(start_y + (r * (box_h + spacing)))
                
                is_off = item.get('offline', False)
                is_can = item.get('cancelled', False)
                
                if is_can: fill_c = (45, 15, 15, opacity)
                elif is_off: fill_c = (70, 70, 70, opacity)
                else: fill_c = c_box
                    
                draw_overlay.rounded_rectangle([box_x, y, box_x + box_w, y + box_h], 30, fill=fill_c)
                
            img = Image.alpha_composite(img, overlay); draw = ImageDraw.Draw(img) 

            raw_g_size = int(ui_state.get("game_size", 45))
            raw_s_size = int(ui_state.get("subtitle_size", 30))

            day_f_size = min(65, int(box_h * 0.30))
            day_f = self.get_f_path(font_name, day_f_size, custom_font_path)
            
            max_day_w = max([day_f.getlength(item["code"]) for item in checked_days])
            
            time_f_size = min(30, int(box_h * 0.15))
            time_f = self.get_f_path(font_name, time_f_size, custom_font_path)
            
            my_zone = ui_state.get('my_zone', 'UK (GMT/BST)')
            sec_zone = ui_state.get('sec_zone', 'US East (EST/EDT)')
            show_primary = ui_state.get('show_primary', True)
            time_fmt = ui_state.get('time_fmt', '24-Hour (20:00)')

            while time_f_size > 8:
                max_t_w = 0
                for item in checked_days:
                    if not item.get('offline', False) or item.get('cancelled', False):
                        times = time_converter.get_converted_time(item.get('time', 'TBA'), my_zone, sec_zone, show_primary, time_fmt)
                        for t_str in times:
                            w = time_f.getlength(t_str)
                            if w > max_t_w: max_t_w = w
                if max_t_w <= max_day_w: break 
                time_f_size -= 1
                time_f = self.get_f_path(font_name, time_f_size, custom_font_path)
                
            left_col_w = max_day_w 
            
            for idx, item in enumerate(checked_days):
                c, r = positions[idx]
                box_x = int(80 + (c * col_w))
                if cols > 1 and c == 0.5: box_x = (cw - box_w) // 2
                y = int(start_y + (r * (box_h + spacing)))
                
                is_off = item.get('offline', False)
                is_can = item.get('cancelled', False)
                left_margin = 25
                
                local_g_size = max(10, raw_g_size)
                local_s_size = max(10, raw_s_size)
                
                if is_off and not is_can:
                    game_f_off = self.get_f_path(font_name, max(10, min(raw_g_size, int(box_h * 0.4))), custom_font_path)
                    self.render_styled_text(draw, (box_x + left_margin, y + (box_h * 0.5)), item["code"], day_f, c_txt, anchor="lm", use_shadow=do_shadow, use_outline=do_outline)
                    # Use custom timestamp/offline color here
                    self.render_styled_text(draw, (box_x + left_margin + left_col_w + 25, y + (box_h * 0.5)), "OFFLINE", game_f_off, c_time, anchor="lm", use_shadow=do_shadow, use_outline=do_outline)
                    continue

                raw_g = item.get("game", "").strip().upper()
                g_val = raw_g if raw_g else "TBA"
                s_val = item.get("sub", "").strip()
                
                art_img = None
                is_custom = False
                if item.get("custom_art") and os.path.exists(item["custom_art"]):
                    art_img = Image.open(item["custom_art"])
                    is_custom = True
                elif item["code"] in art_cache and raw_g:
                    try: art_img = Image.open(art_cache[item["code"]])
                    except: pass

                self.render_styled_text(draw, (box_x + left_margin, y + (box_h * 0.35)), item["code"], day_f, c_txt, anchor="lm", use_shadow=do_shadow, use_outline=do_outline)
                
                times = time_converter.get_converted_time(item.get('time', 'TBA'), my_zone, sec_zone, show_primary, time_fmt)
                ty = y + (box_h * 0.60)
                
                for t_str in times:
                    # Apply dedicated Time color
                    self.render_styled_text(draw, (box_x + left_margin, ty), t_str, time_f, c_time, anchor="lm", use_shadow=do_shadow, use_outline=do_outline)
                    if is_can:
                        draw.line([(box_x + left_margin, ty + time_f_size/2), (box_x + left_margin + time_f.getlength(t_str), ty + time_f_size/2)], fill=(255, 50, 50), width=3)
                    ty += time_f_size + 5

                text_x = box_x + left_margin + left_col_w + 25 
                art_x = box_x + box_w - 20
                
                if art_img and box_h > 30:
                    art_h = int(box_h * 0.85) 
                    if is_custom:
                        orig_w, orig_h = art_img.size
                        ratio = orig_w / float(orig_h)
                        art_w = int(art_h * ratio)
                        max_w = int(box_w * 0.4) 
                        if art_w > max_w:
                            art_w = max_w
                            art_h = int(art_w / ratio)
                    else:
                        art_w = int(art_h * 0.75) 
                        
                    art_y = y + (box_h - art_h) // 2
                    art_x = box_x + box_w - int(box_h * 0.075) - art_w
                    
                    try:
                        art = ImageOps.fit(art_img.convert("RGBA"), (art_w, art_h), method=Image.Resampling.LANCZOS)
                        mask = Image.new("L", (art_w, art_h), 0)
                        ImageDraw.Draw(mask).rounded_rectangle([0, 0, art_w, art_h], int(art_h * 0.1), 255)
                        img.paste(art, (art_x, art_y), mask)
                    except: pass
                
                max_text_w = max(20, art_x - text_x - 20)
                if is_can: max_text_w -= int(box_w * 0.15) 
                
                game_words = g_val.split()
                if game_words:
                    game_f = self.get_f_path(font_name, local_g_size, custom_font_path)
                    max_word_w = max([game_f.getlength(w) for w in game_words])
                    if max_word_w > max_text_w:
                        local_g_size = max(10, int(local_g_size * (max_text_w / float(max_word_w))))

                sub_words = s_val.split()
                if sub_words:
                    sub_f = self.get_f_path(font_name, local_s_size, custom_font_path)
                    max_sub_w = max([sub_f.getlength(w) for w in sub_words])
                    if max_sub_w > max_text_w:
                        local_s_size = max(10, int(local_s_size * (max_text_w / float(max_sub_w))))

                game_f = self.get_f_path(font_name, local_g_size, custom_font_path)
                sub_f = self.get_f_path(font_name, local_s_size, custom_font_path)
                g_lines = self.wrap_text_pil(g_val, game_f, max_text_w)[:3] 
                s_lines = self.wrap_text_pil(s_val, sub_f, max_text_w)[:2] if s_val else []
                
                total_h = len(g_lines) * (local_g_size + 8) + (len(s_lines) * (local_s_size + 8) + 10 if s_lines else 0)
                
                if total_h > (box_h * 0.85):
                    scale_ratio = (box_h * 0.85) / float(total_h)
                    local_g_size = max(10, int(local_g_size * scale_ratio))
                    local_s_size = max(10, int(local_s_size * scale_ratio))
                    
                    game_f = self.get_f_path(font_name, local_g_size, custom_font_path)
                    sub_f = self.get_f_path(font_name, local_s_size, custom_font_path)
                    g_lines = self.wrap_text_pil(g_val, game_f, max_text_w)[:3] 
                    s_lines = self.wrap_text_pil(s_val, sub_f, max_text_w)[:2] if s_val else []
                    total_h = len(g_lines) * (local_g_size + 8) + (len(s_lines) * (local_s_size + 8) + 10 if s_lines else 0)

                gy = y + (box_h // 2) - (total_h // 2) 
                
                for line in g_lines:
                    self.render_styled_text(draw, (text_x, gy), line, game_f, c_txt, anchor="la", use_shadow=do_shadow, use_outline=do_outline)
                    if is_can:
                        draw.line([(text_x, gy + local_g_size/2), (text_x + game_f.getlength(line), gy + local_g_size/2)], fill=(255, 50, 50), width=4)
                    gy += local_g_size + 8

                if s_lines:
                    gy += 10 
                    for line in s_lines:
                        # Apply dedicated Subtitle color
                        self.render_styled_text(draw, (text_x, gy), line, sub_f, c_subtitle, anchor="la", use_shadow=do_shadow, use_outline=do_outline)
                        if is_can:
                            draw.line([(text_x, gy + local_s_size/2), (text_x + sub_f.getlength(line), gy + local_s_size/2)], fill=(255, 50, 50), width=3)
                        gy += local_s_size + 8
                
                if is_can:
                    stamp_size = max(20, int(box_h * 0.25))
                    stamp_f = self.get_f_path(font_name, stamp_size, custom_font_path)
                    draw.text((box_x + box_w - 20, y + (box_h // 2)), "CANCELLED", fill=(255, 50, 50), font=stamp_f, anchor="rm", stroke_width=2, stroke_fill=(0,0,0))

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
                    
                    prog_font = self.get_f_path(font_name, max(12, int(bar_h * 0.6)), custom_font_path)
                    prog_text = f"{sp_cur_str} / {sp_tgt_str}"
                    self.render_styled_text(draw, (cw//2, bar_y + bar_h//2), prog_text, prog_font, (255, 255, 255), anchor="mm", use_shadow=do_shadow, use_outline=do_outline)
                    sp_y = bar_y - 15

                if sp_title:
                    sp_font = self.get_f_path(font_name, max(20, int(ch * 0.025)), custom_font_path)
                    self.render_styled_text(draw, (cw//2, sp_y), sp_title, sp_font, c_txt, anchor="md", use_shadow=do_shadow, use_outline=do_outline)
                    sp_y -= int(ch * 0.035) + 5
            
            if has_logo:
                try:
                    s_logo = Image.open(sp_path).convert("RGBA")
                    logo_h = int(ch * 0.08)
                    s_logo = ImageOps.contain(s_logo, (cw//2, logo_h))
                    img.paste(s_logo, (cw//2 - s_logo.width//2, sp_y - s_logo.height), s_logo)
                except: pass

        return img