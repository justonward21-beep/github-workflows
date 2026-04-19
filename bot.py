import os
import requests
import numpy as np
from scipy.stats import poisson
import time

class FootballFastBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.headers = {'x-rapidapi-key': self.api_key, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        
        self.leagues = [
            {'name': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 الدوري الإنجليزي', 'id': 39},
            {'name': '🇪🇸 الدوري الإسباني', 'id': 140},
            {'name': '🇮🇹 الدوري الإيطالي', 'id': 135},
            {'name': '🇩🇪 الدوري الألماني', 'id': 78},
            {'name': '🇫🇷 الدوري الفرنسي', 'id': 61},
            {'name': '🇧🇷 الدوري البرازيلي', 'id': 71}
        ]

    def send_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        requests.post(url, data={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"})

    def calculate_simple_odds(self, avg_goals=1.45):
        # حساب سريع مبني على متوسط أهداف ثابت (توفيراً للطلبات)
        avg_h, avg_a = avg_goals, avg_goals - 0.1
        p0 = poisson.pmf(0, avg_h) * poisson.pmf(0, avg_a)
        p1 = (poisson.pmf(1, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(1, avg_a))
        p2 = (poisson.pmf(2, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(2, avg_a)) + (poisson.pmf(1, avg_h) * poisson.pmf(1, avg_a))
        
        return {'05': (1-p0)*100, '15': (1-(p0+p1))*100, '25': (1-(p0+p1+p2))*100}

    def run(self):
        self.send_telegram("✅ *جاري جلب توقعات الدوريات الكبرى...*")
        
        for league in self.leagues:
            # نطلب 10 مباريات قادمة (هذا يستهلك طلب واحد فقط لكل دوري)
            url = f"https://v3.football.api-sports.io/fixtures?league={league['id']}&next=10"
            res = requests.get(url, headers=self.headers).json()
            fixtures = res.get('response', [])

            if not fixtures: continue

            msg = f"🏆 *{league['name']}*\n`───────────────`\n"
            for fix in fixtures:
                h, a = fix['teams']['home']['name'], fix['teams']['away']['name']
                date = fix['fixture']['date'][5:10] # MM-DD
                probs = self.calculate_simple_odds()
                
                msg += f"📅 `{date}` | ⚽ `{h} x {a}`\n"
                msg += f"🟢 +0.5: %{probs['05']:.0f} | 🟡 +1.5: %{probs['15']:.0f} | 🔴 +2.5: %{probs['25']:.0f}\n"
                msg += "───\n"
            
            self.send_telegram(msg)
            time.sleep(1)

if __name__ == "__main__":
    FootballFastBot().run()
