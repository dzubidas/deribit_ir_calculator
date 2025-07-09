import requests
import pandas as pd

# Change symbol to XBTUSD
symbol = "XBTUSD"

# Change dates to May 30, 2025 (8-hour window ending at 20:00)
start_time = "2025-05-29T12:01:00.000Z"  # Start after previous funding period
end_time = "2025-05-29T20:00:00.000Z"    # End at the funding time

print(f"Analyzing XBTUSD funding rate for period: {start_time} to {end_time}")
print("=" * 60)

# 1. Getting the 8-hour Premium Index
print("1. Getting 8-hour Premium Index...")
url_pi8h = f"https://www.bitmex.com/api/v1/trade?symbol=.{symbol}PI8H&count=1&startTime={start_time}&endTime={end_time}"
try:
    resp_pi8h = requests.get(url_pi8h)
    df_pi8h = pd.DataFrame(resp_pi8h.json())
    if not df_pi8h.empty:
        print(f"8-hour Premium Index: {df_pi8h.iloc[0]['price']}")
        print(f"Timestamp: {df_pi8h.iloc[0]['timestamp']}")
    else:
        print("No 8-hour Premium Index data found for this period")
except Exception as e:
    print(f"Error getting PI8H: {e}")

print("\n" + "-" * 40 + "\n")

# 2. Getting the minutely Premium Index and averaging to match the 8-hour PI
print("2. Getting minutely Premium Index data...")
url_pi = f"https://www.bitmex.com/api/v1/trade?symbol=.{symbol}PI&count=500&startTime={start_time}&endTime={end_time}"
try:
    resp_pi = requests.get(url_pi)
    df_pi = pd.DataFrame(resp_pi.json())
    if not df_pi.empty:
        pi8h_calculated = df_pi["price"].mean()
        print(f"Calculated 8-hour average from minutely data: {pi8h_calculated}")
        print(f"Number of minutely data points: {len(df_pi)}")
        print(f"First timestamp: {df_pi.iloc[0]['timestamp']}")
        print(f"Last timestamp: {df_pi.iloc[-1]['timestamp']}")
    else:
        print("No minutely Premium Index data found for this period")
except Exception as e:
    print(f"Error getting minutely PI: {e}")

print("\n" + "-" * 40 + "\n")

# 3. Getting current Instrument Table values and calculating the PI
print("3. Getting current instrument data...")
url_instrument = f"https://www.bitmex.com/api/v1/instrument?symbol={symbol}"
try:
    resp_instrument = requests.get(url_instrument)
    df_instrument = pd.DataFrame(resp_instrument.json())
    
    if not df_instrument.empty:
        # Calculate Premium Index using the formula from the documentation
        df_instrument["bid"] = (df_instrument["impactBidPrice"] - df_instrument["fairPrice"]).clip(lower=0)
        df_instrument["ask"] = (df_instrument["fairPrice"] - df_instrument["impactAskPrice"]).clip(lower=0)
        df_instrument["PI"] = ((df_instrument["bid"] - df_instrument["ask"]) / df_instrument["indicativeSettlePrice"]).fillna(0.0) + df_instrument["fundingRate"]
        
        # Display relevant fields
        relevant_cols = ["impactBidPrice", "impactAskPrice", "fairPrice", "indicativeSettlePrice", "fundingRate", "PI"]
        print("Current instrument data:")
        for col in relevant_cols:
            if col in df_instrument.columns:
                print(f"{col}: {df_instrument.iloc[0][col]}")
    else:
        print("No instrument data found")
except Exception as e:
    print(f"Error getting instrument data: {e}")

print("\n" + "-" * 40 + "\n")

# 4. Comparing to the most recent value of the PI index
print("4. Getting most recent Premium Index...")
url_current_pi = f"https://www.bitmex.com/api/v1/trade?symbol=.{symbol}PI&count=1&reverse=true"
try:
    resp_current_pi = requests.get(url_current_pi)
    df_current_pi = pd.DataFrame(resp_current_pi.json())
    
    if not df_current_pi.empty:
        print("Most recent Premium Index:")
        print(f"Value: {df_current_pi.iloc[0]['price']}")
        print(f"Timestamp: {df_current_pi.iloc[0]['timestamp']}")
    else:
        print("No current Premium Index data found")
except Exception as e:
    print(f"Error getting current PI: {e}")

print("\n" + "=" * 60)

# 5. Calculate funding rate using the formula
print("5. Funding Rate Calculation:")
print("Formula: F = Premium Index (P) + clamp(Interest Rate (I) - Premium Index (P), 0.05%, -0.05%)")

# Interest rate is typically 0.01% for most symbols (0.0001 as decimal)
interest_rate = 0.0001
print(f"Interest Rate: {interest_rate} (0.01%)")

# Try to use the PI8H value if we got it
try:
    if 'df_pi8h' in locals() and not df_pi8h.empty:
        premium_index = df_pi8h.iloc[0]['price']
        print(f"Premium Index (from 8H): {premium_index}")
        
        # Apply the clamp function
        clamped_value = max(-0.0005, min(0.0005, interest_rate - premium_index))
        funding_rate = premium_index + clamped_value
        
        print(f"Clamped value: {clamped_value}")
        print(f"Calculated Funding Rate: {funding_rate}")
        print(f"Funding Rate as percentage: {funding_rate * 100:.4f}%")
except:
    print("Could not calculate funding rate - missing Premium Index data")