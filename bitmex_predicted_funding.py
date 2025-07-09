import requests
import pandas as pd
from datetime import datetime, timezone
import time

def get_next_funding_time():
    """Zistí najbližší funding settlement čas (04:00, 12:00, 20:00 UTC)"""
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    
    # Funding časy v UTC
    funding_hours = [4, 12, 20]
    
    # Nájdi najbližší budúci funding čas
    next_funding_hour = None
    for hour in funding_hours:
        if current_hour < hour:
            next_funding_hour = hour
            break
    
    if next_funding_hour is None:
        next_funding_hour = 4  # Ďalší deň
        next_day = now.replace(hour=4, minute=0, second=0, microsecond=0)
        next_day = next_day.replace(day=now.day + 1)
        return next_day
    
    return now.replace(hour=next_funding_hour, minute=0, second=0, microsecond=0)

def get_last_funding_time():
    """Zistí posledný funding settlement čas"""
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    
    funding_hours = [4, 12, 20]
    
    # Nájdi posledný funding čas
    last_funding_hour = None
    for hour in reversed(funding_hours):
        if current_hour >= hour:
            last_funding_hour = hour
            break
    
    if last_funding_hour is None:
        # Ak je pred 04:00, posledný funding bol včera o 20:00
        yesterday = now.replace(day=now.day - 1, hour=20, minute=0, second=0, microsecond=0)
        return yesterday
    
    return now.replace(hour=last_funding_hour, minute=0, second=0, microsecond=0)

def calculate_predicted_funding_rate(symbol="XBTUSD"):
    """Vypočíta predicted funding rate pre daný symbol"""
    
    print(f"🔍 Calculating predicted funding rate for {symbol}")
    print("=" * 60)
    
    # Zisti časy
    now = datetime.now(timezone.utc)
    last_funding = get_last_funding_time()
    next_funding = get_next_funding_time()
    
    # Časové okno od posledného settlement
    start_time = last_funding.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    current_time = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    print(f"⏰ Aktuálny čas (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 Posledný funding settlement: {last_funding.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"📅 Ďalší funding settlement: {next_funding.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Čas od posledného settlement
    time_elapsed = now - last_funding
    hours_elapsed = time_elapsed.total_seconds() / 3600
    print(f"⌛ Čas od posledného settlement: {hours_elapsed:.2f} hodín")
    
    print("\n" + "-" * 40)
    
    try:
        # 1. Získaj Premium Index dáta od posledného settlement
        print(f"📊 Získavam Premium Index od {start_time}...")
        
        # Počet minút od settlement + 10 minút buffer
        minutes_since_settlement = int(time_elapsed.total_seconds() / 60) + 10
        count = min(minutes_since_settlement, 500)  # API limit je 500
        
        url_pi = f"https://www.bitmex.com/api/v1/trade?symbol=.{symbol}PI&count={count}&reverse=true"
        resp_pi = requests.get(url_pi)
        
        if resp_pi.status_code != 200:
            print(f"❌ Chyba pri získavaní PI dát: {resp_pi.status_code}")
            return None
            
        pi_data = resp_pi.json()
        if not pi_data:
            print("❌ Žiadne Premium Index dáta")
            return None
        
        # Filtruj dáta od posledného settlement
        df_pi = pd.DataFrame(pi_data)
        df_pi['timestamp'] = pd.to_datetime(df_pi['timestamp'])
        
        # Zoberie len dáta od posledného settlement
        df_pi_filtered = df_pi[df_pi['timestamp'] >= last_funding]
        
        if df_pi_filtered.empty:
            print("❌ Žiadne Premium Index dáta od posledného settlement")
            return None
        
        # Vypočítaj priemer Premium Index
        avg_premium_index = df_pi_filtered['price'].mean()
        data_points = len(df_pi_filtered)
        
        print(f"📈 Priemer Premium Index: {avg_premium_index:.6f} ({avg_premium_index * 100:.4f}%)")
        print(f"📊 Počet dátových bodov: {data_points}")
        print(f"⏰ Od: {df_pi_filtered.iloc[-1]['timestamp']}")
        print(f"⏰ Do: {df_pi_filtered.iloc[0]['timestamp']}")
        
        # 2. Interest rate (typicky 0.01% pre XBTUSD)
        interest_rate = 0.0001  # 0.01%
        
        # 3. Aplikuj BitMEX vzorec
        # F = P + clamp(I - P, -0.0005, 0.0005)
        diff = interest_rate - avg_premium_index
        clamped_value = max(-0.0005, min(0.0005, diff))
        predicted_funding = avg_premium_index + clamped_value
        
        print("\n" + "-" * 40)
        print("🧮 VÝPOČET PREDICTED FUNDING RATE:")
        print(f"📊 Premium Index (P): {avg_premium_index:.6f}")
        print(f"💰 Interest Rate (I): {interest_rate:.6f} (0.01%)")
        print(f"🔢 I - P: {diff:.6f}")
        print(f"📎 Clamped hodnota: {clamped_value:.6f}")
        print(f"🎯 Predicted Funding: {predicted_funding:.6f}")
        print(f"📈 Predicted Funding %: {predicted_funding * 100:.4f}%")
        
        # Dennný ekvivalent
        daily_rate = predicted_funding * 3
        print(f"📅 Denný ekvivalent: {daily_rate * 100:.4f}%")
        
        return {
            'predicted_funding_rate': predicted_funding,
            'predicted_funding_percent': predicted_funding * 100,
            'premium_index': avg_premium_index,
            'data_points': data_points,
            'hours_since_settlement': hours_elapsed,
            'next_settlement': next_funding
        }
        
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return None

def continuous_monitoring(symbol="XBTUSD", interval_seconds=60):
    """Kontinuálne monitorovanie predicted funding rate"""
    print(f"🔄 Spúšťam kontinuálne monitorovanie {symbol} (každých {interval_seconds}s)")
    print("Stlač Ctrl+C pre zastavenie\n")
    
    try:
        while True:
            result = calculate_predicted_funding_rate(symbol)
            if result:
                print(f"\n✅ AKTUÁLNY PREDICTED FUNDING: {result['predicted_funding_percent']:.4f}%")
                print(f"⏰ Ďalší settlement: {result['next_settlement'].strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            print(f"\n⏳ Čakám {interval_seconds} sekúnd...\n" + "="*80 + "\n")
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n👋 Monitorovanie zastavené")

if __name__ == "__main__":
    # Jednorazový výpočet
    result = calculate_predicted_funding_rate("XBTUSD")
    
    # Ak chceš kontinuálne monitorovanie, odkomentuj nasledujúci riadok:
    continuous_monitoring("XBTUSD", 20)  # Každú minútu