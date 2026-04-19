import os
import requests
import numpy as np
from scipy.stats import poisson
import time
from datetime import datetime

class FootballFinalBot:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_API_KEY")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {'x-rapidapi-key': self.api_key, 'x-rapidapi-host': 'v3.football.api-sports.io'}
        
        # قائمة الدوريات مع البحث في موسمين لضمان جلب البيانات (الأوروبي 2025 واللاتيني 2026)
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
        try:
            params = {'league': league_id, 'season': season, 'team': team_id}
            res = requests.get(f"{self.base_url}/teams/statistics", headers=self.headers, params=params).json()
            avg = res['response']['goals']['for']['average']['total']
            return float(avg)
        except:
            return 1.45

    def calculate_odds(self, avg_h, avg_a):
        p0 = poisson.pmf(0, avg_h) * poisson.pmf(0, avg_a)
        p1 = (poisson.pmf(1, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(1, avg_a))
        p2 = (poisson.pmf(2, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(2, avg_a)) + (poisson.pmf(1, avg_h) * poisson.pmf(1, avg_a))
        
        # حماية من القسمة على صفر
        prob05 = max((1 - p0) * 100, 1)
        prob15 = max((1 - (p0 + p1)) * 100, 1)
        prob25 = max((1 - (p0 + p1 + p2)) * 100, 1)
        
        return {'05': (prob05, 100/prob05), '15': (prob15, 100/prob15), '25': (prob25, 100/prob25)}

    def run_safe_report(self):
        self.send_telegram("🔍 *بدء الفحص الشامل للمباريات القادمة...*")
        found_any = False

        for league in self.leagues:
            # هنا التعديل: نطلب "القادم" (next=10) بدلاً من تاريخ محدد
            params = {'league': league['id'], 'next': 10}
            response = requests.get(f"{self.base_url}/fixtures", headers=self.headers, params=params).json()
            fixtures = response.get('response', [])

            if not fixtures:
                continue
            
            found_any = True
            msg = f"🏆 *{league['name']}*\n`───────────────`\n"
            for fix in fixtures:
                f_date = fix['fixture']['date'][:10] # تاريخ المباراة
                h_name, a_name = fix['teams']['home']['name'], fix['teams']['away']['name']
                
                res = self.calculate_odds(
                    self.get_avg_goals(fix['teams']['home']['id'], league['id'], league['s']),
                    self.get_avg_goals(fix['teams']['away']['id'], league['id'], league['s'])
                )
                
                msg += f"📅 `{f_date}` | ⚽ `{h_name} x {a_name}`\n"
                msg += f"🟢 +0.5: %{res['05'][0]:.0f} | 🟡 +1.5: %{res['15'][0]:.0f}\n"
                msg += f"🔴 +2.5: %{res['25'][0]:.0f}\n"
                msg += "───\n"
                time.sleep(1) # لتجنب ضغط الـ API
            
            self.send_telegram(msg)
            time.sleep(2)

        if not found_any:
            self.send_telegram("❌ فشل جلب البيانات. تأكد من صلاحية الـ API Key الخاص بك.")

if __name__ == "__main__":
    bot = FootballFinalBot()
    bot.run_safe_report()
