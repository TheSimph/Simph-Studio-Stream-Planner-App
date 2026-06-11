import customtkinter as ctk
import datetime
import calendar

class CalendarModal:
    def __init__(self, parent, current_selected_date, on_date_selected):
        """
        Initializes the calendar popup modal.
        parent: The main application window (used for centering).
        current_selected_date: The currently active date to highlight.
        on_date_selected: A callback function that takes a datetime.date object.
        """
        self.parent = parent
        self.selected_start_date = current_selected_date
        self.on_date_selected = on_date_selected
        
        self.cal_win = ctk.CTkToplevel(self.parent)
        self.cal_win.title("Select Start Date")
        self.cal_win.geometry("320x350")
        
        # Center the modal relative to the parent window
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 160
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 175
        self.cal_win.geometry(f"+{x}+{y}")
        
        self.cal_win.attributes("-topmost", True)
        self.cal_win.resizable(False, False)
        
        self.cal_view_date = datetime.date.today().replace(day=1)
        self.build_cal_ui()

    def build_cal_ui(self):
        for widget in self.cal_win.winfo_children(): 
            widget.destroy()
            
        header_f = ctk.CTkFrame(self.cal_win, fg_color="transparent")
        header_f.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkButton(header_f, text="<", width=40, command=lambda: self.change_month(-1)).pack(side="left")
        ctk.CTkLabel(header_f, text=self.cal_view_date.strftime("%B %Y"), font=("Arial", 16, "bold")).pack(side="left", expand=True)
        ctk.CTkButton(header_f, text=">", width=40, command=lambda: self.change_month(1)).pack(side="right")
        
        days_f = ctk.CTkFrame(self.cal_win, fg_color="transparent")
        days_f.pack(fill="both", expand=True, padx=10)
        
        for i, d in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]): 
            ctk.CTkLabel(days_f, text=d, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=5, pady=5)
            
        cal = calendar.monthcalendar(self.cal_view_date.year, self.cal_view_date.month)
        
        for row, week in enumerate(cal):
            for col, day in enumerate(week):
                if day != 0:
                    btn = ctk.CTkButton(days_f, text=str(day), width=35, height=35, fg_color="#333", command=lambda d=day: self.set_start_date(d))
                    btn.grid(row=row+1, column=col, padx=2, pady=2)
                    
                    if datetime.date(self.cal_view_date.year, self.cal_view_date.month, day) == self.selected_start_date: 
                        btn.configure(fg_color="#00FF00", text_color="black")

    def change_month(self, delta):
        m = self.cal_view_date.month - 1 + delta
        y = self.cal_view_date.year + m // 12
        self.cal_view_date = datetime.date(y, m % 12 + 1, 1)
        self.build_cal_ui()

    def set_start_date(self, day):
        chosen_date = datetime.date(self.cal_view_date.year, self.cal_view_date.month, day)
        self.cal_win.destroy()
        self.on_date_selected(chosen_date)

    def focus(self):
        """Brings the calendar window back to the front if it already exists."""
        self.cal_win.focus()