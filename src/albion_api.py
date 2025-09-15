import requests
import aiohttp
import asyncio
from datetime import datetime, timedelta
from config import Config

class AlbionAPI:
    def __init__(self):
        self.base_url = Config.ALBION_API_BASE
    
    async def get_events(self, location, limit=50, range=1000):
        """Get recent events in a location"""
        try:
            url = f"{self.base_url}/events"
            params = {
                'limit': limit,
                'range': range,
                'location': location
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"API Error: {response.status}")
                        return []
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []
    
    async def search_player(self, player_name):
        """Search for player by name"""
        try:
            url = f"{self.base_url}/search"
            params = {'q': player_name}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('players', [])
                    return []
        except Exception as e:
            print(f"Error searching player: {e}")
            return []
    
    async def get_player_info(self, player_id):
        """Get detailed player information"""
        try:
            url = f"{self.base_url}/players/{player_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            print(f"Error getting player info: {e}")
            return None
    
    async def get_player_kill_stats(self, player_id, limit=10):
        """Get player's recent kill statistics"""
        try:
            url = f"{self.base_url}/events"
            params = {
                'playerId': player_id,
                'limit': limit,
                'type': 'kill'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        events = await response.json()
                        return len(events), events
                    return 0, []
        except Exception as e:
            print(f"Error getting kill stats: {e}")
            return 0, []
    
    def is_resource_event(self, event):
        """Check if event is related to resource gathering"""
        if not event.get('Victim'):
            return False
        
        victim_name = event['Victim'].get('Name', '').lower()
        resource_keywords = ['ore', 'rock', 'wood', 'fiber', 'hide', 'stone', 'tree']
        
        return any(keyword in victim_name for keyword in resource_keywords)
    
    def is_player_event(self, event):
        """Check if event involves player vs player"""
        return (event.get('Killer') and event.get('Victim') and 
                event['Killer'].get('Type') == 'Player' and 
                event['Victim'].get('Type') == 'Player')
    
    def is_pve_event(self, event):
        """Check if event involves player vs environment"""
        return (event.get('Killer') and event.get('Victim') and 
                event['Killer'].get('Type') == 'Player' and 
                event['Victim'].get('Type') == 'Creature')

# Global API instance
albion_api = AlbionAPI()
