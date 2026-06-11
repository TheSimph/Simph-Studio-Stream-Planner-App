import os
import requests
import datetime
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.type import AuthScope

class TwitchClient:
    def __init__(self, client_id, client_secret, token=None):
        """
        Initializes the Twitch Client with necessary credentials.
        The token is optional for public endpoints (like search and box art) 
        but required for private endpoints (like updating the schedule).
        """
        self.client_id = client_id.strip() if client_id else ""
        self.client_secret = client_secret.strip() if client_secret else ""
        self.token = token.strip() if token else ""

    async def search_categories(self, query):
        """
        Searches Twitch for game categories matching the query.
        Returns a list of category objects (max 5 is usually handled by the caller).
        """
        if len(query) < 3 or not self.client_id or not self.client_secret:
            return []
            
        try:
            api = await Twitch(self.client_id, self.client_secret)
            results = []
            async for category in api.search_categories(query):
                results.append(category)
            return results
        except Exception as e:
            print(f"Twitch Search Error: {e}")
            return []

    async def download_game_art(self, game_name, day_code, width=300, height=400):
        """
        Fetches the box art for a specific game and downloads it locally.
        Returns the local file path if successful, or None if it fails.
        """
        if not self.client_id or not self.client_secret:
            return None
            
        try:
            api = await Twitch(self.client_id, self.client_secret)
            game = await first(api.get_games(names=[game_name]))
            
            if game:
                # Twitch returns a generic URL string with {width} and {height} placeholders
                url = game.box_art_url.replace("{width}", str(width)).replace("{height}", str(height))
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    cache_path = f"cache_{day_code}.png"
                    with open(cache_path, "wb") as f:
                        f.write(response.content)
                    return cache_path
        except Exception as e:
            print(f"Twitch Art Download Error: {e}")
            
        return None

    async def sync_schedule(self, schedule_segments):
        """
        Syncs the generated schedule to the authenticated user's Twitch Dashboard.
        
        Expected structure for schedule_segments (list of dicts):
        [
            {
                "start_dt": datetime.datetime object,
                "timezone": "Europe/London",
                "duration": "240",
                "category_id": "123456",
                "title": "Game Title"
            },
            ...
        ]
        """
        if not self.client_id or not self.client_secret or not self.token:
            raise ValueError("Missing Twitch credentials or token. Cannot sync schedule.")
            
        try:
            api = await Twitch(self.client_id, self.client_secret)
            
            # Disable auto-refresh because we are forcing a user-provided token
            api.auto_refresh_auth = False 
            await api.set_user_authentication(self.token, [AuthScope.CHANNEL_MANAGE_SCHEDULE], None)
            
            user = await first(api.get_users())
            if not user:
                raise Exception("Could not retrieve Twitch User. Token might be invalid.")
                
            for segment in schedule_segments:
                await api.create_channel_stream_schedule_segment(
                    broadcaster_id=user.id,
                    start_time=segment['start_dt'],
                    timezone=segment['timezone'],
                    duration=segment.get('duration', '240'),
                    is_recurring=False,
                    category_id=segment.get('category_id', ''),
                    title=segment.get('title', 'TBA')
                )
            return True
            
        except Exception as e:
            raise Exception(f"Failed to sync Twitch schedule: {e}")