import datetime
import pytz

class TimeConverter:
    def __init__(self):
        # Primary timezone map
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
        
        # Secondary timezone map includes the option to hide it
        self.sec_tz_map = {"None (Hide)": "N/A"}
        self.sec_tz_map.update(self.tz_map)

    def get_converted_time(self, time_str, from_zone_display, to_zone_display, show_primary, time_fmt="24-Hour (20:00)"):
        """
        Takes a time string and converts it across the selected timezones.
        Returns a list of formatted time strings for the UI/Image Renderer.
        """
        if time_str in ["TBA"]: 
            return [time_str]
            
        try:
            # Localize the base time to the primary timezone
            f_tz = pytz.timezone(self.tz_map.get(from_zone_display, "Europe/London"))
            h, m = map(int, time_str.split(':'))
            now = datetime.datetime.now()
            loc_dt = f_tz.localize(datetime.datetime(now.year, now.month, now.day, h, m))
            
            # Determine 12-hour or 24-hour format
            fmt = '%I:%M %p' if "12" in time_fmt else '%H:%M'
            base_time = loc_dt.strftime(fmt).lstrip('0')
            
            res = []
            
            # Append primary time if requested
            if show_primary: 
                res.append(f"{base_time} {loc_dt.strftime('%Z')}")
            
            # Append secondary time if it's not set to 'None'
            if to_zone_display != "None (Hide)":
                tar_dt = loc_dt.astimezone(pytz.timezone(self.sec_tz_map.get(to_zone_display, "US/Eastern")))
                res.append(f"{tar_dt.strftime(fmt).lstrip('0')} {tar_dt.strftime('%Z')}")
                
            # Fallback if both displays were somehow toggled off
            if not res: 
                return [base_time] 
                
            return res
            
        except Exception: 
            # If any parsing fails (e.g., bad format), return the raw string safely
            return [time_str]