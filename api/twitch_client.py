import os
import tempfile
import requests
import asyncio

class Category:
    def __init__(self, cat_id, name):
        self.id = cat_id
        self.name = name

class TwitchClient:
    def __init__(self, client_id, client_secret, token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        self.headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.token}'
        }
        
        # PREMIUM GARBAGE COLLECTION: Maps downloads directly to the hidden Windows Temp directory
        # This completely bypasses the desktop and the folder where the .exe is running
        self.temp_dir = os.path.join(tempfile.gettempdir(), "SimphStudio_Temp_Art")
        os.makedirs(self.temp_dir, exist_ok=True)

    async def search_categories(self, query):
        if not self.client_id or not self.token: return []
        url = f"https://api.twitch.tv/helix/search/categories?query={query}"
        
        def fetch():
            try:
                resp = requests.get(url, headers=self.headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    return [Category(item['id'], item['name']) for item in data.get('data', [])]
            except: pass
            return []
            
        return await asyncio.to_thread(fetch)

    async def download_game_art(self, game_name, day_code):
        if not self.client_id or not self.token or not game_name: return None
        url = f"https://api.twitch.tv/helix/games?name={game_name}"
        
        def fetch_and_save():
            try:
                resp = requests.get(url, headers=self.headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('data'):
                        box_art_url = data['data'][0]['box_art_url'].replace('{width}', '285').replace('{height}', '380')
                        img_resp = requests.get(box_art_url, timeout=5)
                        if img_resp.status_code == 200:
                            safe_filename = "".join([c for c in game_name if c.isalnum() or c==' ']).rstrip()
                            
                            # Writes straight to the deep system temporary folder
                            file_path = os.path.join(self.temp_dir, f"{day_code}_{safe_filename}.jpg")
                            with open(file_path, 'wb') as f:
                                f.write(img_resp.content)
                            return file_path
            except: pass
            return None
            
        return await asyncio.to_thread(fetch_and_save)

    async def sync_schedule(self, segments):
        if not self.client_id or not self.token: return
        
        def run_sync():
            try:
                user_url = "https://api.twitch.tv/helix/users"
                user_resp = requests.get(user_url, headers=self.headers, timeout=5)
                if user_resp.status_code != 200: return
                broadcaster_id = user_resp.json()['data'][0]['id']

                schedule_url = f"https://api.twitch.tv/helix/schedule?broadcaster_id={broadcaster_id}"
                sched_resp = requests.get(schedule_url, headers=self.headers, timeout=5)
                if sched_resp.status_code == 200:
                    sched_data = sched_resp.json()
                    if sched_data.get('data') and sched_data['data'].get('segments'):
                        for seg in sched_data['data']['segments']:
                            del_url = f"https://api.twitch.tv/helix/schedule/segment?broadcaster_id={broadcaster_id}&id={seg['id']}"
                            requests.delete(del_url, headers=self.headers, timeout=5)

                for seg in segments:
                    start_time = seg['start_dt'].strftime('%Y-%m-%dT%H:%M:%SZ')
                    payload = {
                        "start_time": start_time,
                        "timezone": seg['timezone'],
                        "duration": seg['duration'],
                        "is_recurring": False,
                        "category_id": seg['category_id'],
                        "title": seg['title'][:140]
                    }
                    post_url = f"https://api.twitch.tv/helix/schedule/segment?broadcaster_id={broadcaster_id}"
                    requests.post(post_url, headers=self.headers, json=payload, timeout=5)
            except: pass
            
        await asyncio.to_thread(run_sync)