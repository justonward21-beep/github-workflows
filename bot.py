import os
import requests
import numpy as np
from scipy.stats import poisson
import time
from datetime import datetime

class FootballProBot:
    def __init__(self):
        # جلب المفاتيح من GitHub Secrets
        self.api_key = os.getenv("FOOTBALL_API_KEY")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {'x-rapidapi-key': self.api_key, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        
        self.leagues = [
            {'name': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 الدوري الإنجليزي', 'id': 39},
            {'name': '🇪🇸 الدوري الإسباني', 'id': 140},
            {'name': '🇮🇹 الدوري الإيطالي', 'id': 135},
            {'name': '🇩🇪 الدوري الألماني', 'id': 78},
            {'name': '🇫🇷 الدوري الفرنسي', 'id': 61},
            {'name': '🇧🇷 الدوري البرازيلي', 'id': 71},
            {'name': '🇦🇷 الدوري الأرجنتيني', 'id': 128}
        ]

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"})

    def get_avg_goals(self, team_id, league_id):
        params = {'league': league_id, 'season': 2026, 'team': team_id}
        try:
            res = requests.get(f"{self.base_url}/teams/statistics", headers=self.headers, params=params).json()
            return float(res['response']['goals']['for']['average']['total'])
        except:
            return 1.35

    def calculate_odds(self, avg_h, avg_a):
        p0 = poisson.pmf(0, avg_h) * poisson.pmf(0, avg_a)
        p1 = (poisson.pmf(1, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(1, avg_a))
        p2 = (poisson.pmf(2, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(2, avg_a)) + (poisson.pmf(1, avg_h) * poisson.pmf(1, avg_a))
        
        prob05 = (1 - p0) * 100
        prob15 = (1 - (p0 + p1)) * 100
        prob25 = (1 - (p0 + p1 + p2)) * 100

        return {
            '05': (prob05, 100/prob05 if prob05 > 0 else 0),
            '15': (prob15, 100/prob15 if prob15 > 0 else 0),
            '25': (prob25, 100/prob25 if prob25 > 0 else 0)
        }

    def run_report(self):
        today = datetime.now().strftime('%Y-%m-%d')
        self.send_telegram(f"📊 *توقعات مباريات اليوم ({today})*")

        for league in self.leagues:
            params = {'league': league['id'], 'date': today}
            fixtures = requests.get(f"{self.base_url}/fixtures", headers=self.headers, params=params).json().get('response', [])
            
            if not fixtures: continue

            msg = f"🏆 *{league['name']}*\n`───────────────`\n"
            for fix in fixtures:
                h_id, a_id = fix['teams']['home']['id'], fix['teams']['away']['id']
                h_name, a_name = fix['teams']['home']['name'], fix['teams']['away']['name']

                res = self.calculate_odds(self.get_avg_goals(h_id, league['id']), self.get_avg_goals(a_id, league['id']))
                
                msg += f"⚽ `{h_name} x {a_name}`\n"
                msg += f"🔸 +0.5: %{res['05'][0]:.0f} (Odd: `{res['05'][1]:.2f}`)\n"
                msg += f"🔸 +1.5: %{res['15'][0]:.0f} (Odd: `{res['15'][1]:.2f}`)\n"
                msg += f"🔸 +2.5: %{res['2.5'][0]:.0f} (Odd: `{res['2.5'][1]:.2f}`)\n"
                msg += "───\n"
                time.sleep(1.2)
            
            self.send_telegram(msg)

if __name__ == "__main__":
    bot = FootballProBot()
    bot.run_report()
