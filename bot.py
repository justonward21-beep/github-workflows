import os
import requests
import numpy as np
from scipy.stats import poisson
import time
from datetime import datetime, timedelta

class FootballFutureBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {'x-rapidapi-key': self.api_key, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        
        # تحديد المواسم بدقة: الأوروبي بدأ في 2025، اللاتيني في 2026
        self.leagues = [
            {'name': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 الدوري الإنجليزي', 'id': 39, 's': 2025},
            {'name': '🇪🇸 الدوري الإسباني', 'id': 140, 's': 2025},
            {'name': '🇮🇹 الدوري الإيطالي', 'id': 135, 's': 2025},
            {'name': '🇩🇪 الدوري الألماني', 'id': 78, 's': 2025},
            {'name': '🇫🇷 الدوري الفرنسي', 'id': 61, 's': 2025},
            {'name': '🇧🇷 الدوري البرازيلي', 'id': 71, 's': 2026},
            {'name': '🇦🇷 الدوري الأرجنتيني', 'id': 128, 's': 2026}
        ]

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"})

    def get_avg_goals(self, team_id, league_id, season):
        params = {'league': league_id, 'season': season, 'team': team_id}
        try:
            res = requests.get(f"{self.base_url}/teams/statistics", headers=self.headers, params=params).json()
            return float(res['response']['goals']['for']['average']['total'])
        except:
            return 1.42

    def calculate_odds(self, avg_h, avg_a):
        p0 = poisson.pmf(0, avg_h) * poisson.pmf(0, avg_a)
        p1 = (poisson.pmf(1, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(1, avg_a))
        p2 = (poisson.pmf(2, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(2, avg_a)) + (poisson.pmf(1, avg_h) * poisson.pmf(1, avg_a))
        
        prob05, prob15, prob25 = (1-p0)*100, (1-(p0+p1))*100, (1-(p0+p1+p2))*100
        return {'05': (prob05, 100/prob05 if prob05>0 else 0), 
                '15': (prob15, 100/prob15 if prob15>0 else 0), 
                '25': (prob25, 100/prob25 if prob25>0 else 0)}

    def fetch_and_send(self, target_date, label):
        self.send_telegram(f"📅 *تقرير مباريات {label}* ({target_date})")
        found_any = False
        
        for league in self.leagues:
            params = {'league': league['id'], 'date': target_date}
            fixtures = requests.get(f"{self.base_url}/fixtures", headers=self.headers, params=params).json().get('response', [])

            if not fixtures: continue
            
            found_any = True
            msg = f"🏆 *{league['name']}*\n`───────────────`\n"
            for fix in fixtures:
                h_id, a_id = fix['teams']['home']['id'], fix['teams']['away']['id']
                res = self.calculate_odds(self.get_avg_goals(h_id, league['id'], league['s']), 
                                         self.get_avg_goals(a_id, league['id'], league['s']))
                
                msg += f"⚽ `{fix['teams']['home']['name']} x {fix['teams']['away']['name']}`\n"
                msg += f"🔹 +0.5: %{res['05'][0]:.0f} (Odd: `{res['05'][1]:.2f}`)\n"
                msg += f"🔹 +1.5: %{res['15'][0]:.0f} (Odd: `{res['15'][1]:.2f}`)\n"
                msg += f"🔹 +2.5: %{res['2.5'][0]:.0f} (Odd: `{res['2.5'][1]:.2f}`)\n"
                msg += "───\n"
                time.sleep(1.2)
            self.send_telegram(msg)
        
        if not found_any:
            self.send_telegram(f"📭 لا توجد مباريات في {label}.")

    def run_all(self):
        # توقيت اليوم وتوقيت الغد
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        self.fetch_and_send(today, "اليوم")
        self.fetch_and_send(tomorrow, "الغد")

if __name__ == "__main__":
    bot = FootballFutureBot()
    bot.run_all()
