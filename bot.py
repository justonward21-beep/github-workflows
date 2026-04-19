import os
import requests
import numpy as np
from scipy.stats import poisson
import time
from datetime import datetime

class FootballProBot:
    def __init__(self):
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
        proxies = None # لا نحتاج بروكسي في GitHub Actions
        try:
            resp = requests.post(url, data={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
            print(f"Telegram Response: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Failed to send Telegram: {e}")

    def get_avg_goals(self, team_id, league_id):
        # محاولة جلب الموسم الحالي آلياً أو استخدام 2024/2025 كاحتياط
        year = datetime.now().year
        params = {'league': league_id, 'season': year, 'team': team_id}
        try:
            res = requests.get(f"{self.base_url}/teams/statistics", headers=self.headers, params=params).json()
            # إذا لم يجد بيانات لهذا العام، نجرب العام السابق
            if not res.get('response'):
                params['season'] = year - 1
                res = requests.get(f"{self.base_url}/teams/statistics", headers=self.headers, params=params).json()
            
            avg = res['response']['goals']['for']['average']['total']
            return float(avg)
        except:
            return 1.4 # متوسط افتراضي آمن

    def calculate_odds(self, avg_h, avg_a):
        # حساب الاحتمالات (Poisson Distribution)
        p0 = poisson.pmf(0, avg_h) * poisson.pmf(0, avg_a)
        p1 = (poisson.pmf(1, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(1, avg_a))
        p2 = (poisson.pmf(2, avg_h) * poisson.pmf(0, avg_a)) + (poisson.pmf(0, avg_h) * poisson.pmf(2, avg_a)) + (poisson.pmf(1, avg_h) * poisson.pmf(1, avg_a))
        
        prob05 = max((1 - p0) * 100, 1)
        prob15 = max((1 - (p0 + p1)) * 100, 1)
        prob25 = max((1 - (p0 + p1 + p2)) * 100, 1)

        return {
            '05': (prob05, 100/prob05),
            '15': (prob15, 100/prob15),
            '25': (prob25, 100/prob25)
        }

    def run_report(self):
        today = datetime.now().strftime('%Y-%m-%d')
        # رسالة تأكيد لبدء العمل تظهر في تلجرام فوراً
        self.send_telegram(f"⚡ *البوت متصل ويعمل الآن!*\nتاريخ الفحص: `{today}`")

        found_matches = False
        for league in self.leagues:
            # نغير 'date' إلى 'next: 5' مؤقتاً للتأكد من أن الكود يجلب بيانات
            params = {'league': league['id'], 'next': 5} 
            try:
                response = requests.get(f"{self.base_url}/fixtures", headers=self.headers, params=params).json()
                fixtures = response.get('response', [])
            except:
                continue

            if not fixtures:
                continue
            
            found_matches = True
            msg = f"🏆 *{league['name']}*\n`───────────────`\n"
            for fix in fixtures:
                h_name = fix['teams']['home']['name']
                a_name = fix['teams']['away']['name']
                
                res = self.calculate_odds(self.get_avg_goals(fix['teams']['home']['id'], league['id']), 
                                         self.get_avg_goals(fix['teams']['away']['id'], league['id']))
                
                msg += f"⚽ `{h_name} x {a_name}`\n"
                msg += f"🔸 +0.5: %{res['05'][0]:.0f} (Odd: `{res['05'][1]:.2f}`)\n"
                msg += f"🔸 +1.5: %{res['15'][0]:.0f} (Odd: `{res['15'][1]:.2f}`)\n"
                msg += f"🔸 +2.5: %{res['2.5'][0]:.0f} (Odd: `{res['2.5'][1]:.2f}`)\n"
                msg += "───\n"
                time.sleep(0.5)
            
            self.send_telegram(msg)
        
        if not found_matches:
            self.send_telegram("⚠️ لم يتم العثور على مباريات قادمة في الدوريات المحددة حالياً.")

if __name__ == "__main__":
    bot = FootballProBot()
    bot.run_report()
