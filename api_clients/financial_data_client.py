import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.investing.com/api/financialdata/economiccalendar"

def get_upcoming_economic_events():
    """
    Recupera gli eventi economici ad alto impatto per le prossime 48 ore.
    Usa un fornitore alternativo che non richiede API Key.
    """
    try:
        now = datetime.utcnow()
        from_date = now.strftime('%Y-%m-%d')
        to_date = (now + timedelta(days=2)).strftime('%Y-%m-%d')

        params = {
            "timeZone": "8", "timeFilter": "timeRemain", "currentTab": "custom",
            "startDate": from_date, "endDate": to_date, "importance": "3", "countries": "5,72"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.investing.com/"
        }

        res = requests.get(BASE_URL, params=params, headers=headers)
        res.raise_for_status()
        data = res.json()

        if not data or 'data' not in data: return []

        formatted_events = []
        for event in data['data']:
            formatted_events.append({
                'time': event.get('time_only'), 'country': event.get('country_name'),
                'event': event.get('event_name'), 'impact': 'high'
            })
        return formatted_events

    except Exception as e:
        print(f"ERRORE: Impossibile contattare il servizio di calendario economico. {e}")
        return []
