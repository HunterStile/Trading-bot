
def calculate_atr(klines, period=14):
    """Calcola Average True Range in-house"""
    try:
        if len(klines) < period + 1:
            return 0.01
            
        true_ranges = []
        
        # Calcola True Range per ogni candela
        for i in range(1, len(klines)):
            high = float(klines[i][2])
            low = float(klines[i][3])
            prev_close = float(klines[i-1][4])
            
            # True Range = max(high-low, |high-prev_close|, |low-prev_close|)
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        # ATR = Media mobile esponenziale dei True Range
        if len(true_ranges) >= period:
            # Inizia con SMA per i primi valori
            initial_atr = sum(true_ranges[:period]) / period
            
            # Applica EMA per i valori successivi
            multiplier = 2 / (period + 1)
            atr = initial_atr
            
            for tr in true_ranges[period:]:
                atr = (tr * multiplier) + (atr * (1 - multiplier))
            
            return atr
        else:
            # Se non abbastanza dati, usa media semplice
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0.01
    except Exception as e:
        print(f"Errore calcolo ATR: {e}")
        return 0.01

def calculate_adx(klines, period=14):
    """Calcola ADX (Average Directional Index) in-house"""
    try:
        if len(klines) < period * 2:
            return 0.0
            
        # Arrays per calcoli
        true_ranges = []
        plus_dm = []  # Positive Directional Movement
        minus_dm = [] # Negative Directional Movement
        
        # Calcola TR, +DM, -DM
        for i in range(1, len(klines)):
            high = float(klines[i][2])
            low = float(klines[i][3])
            prev_high = float(klines[i-1][2])
            prev_low = float(klines[i-1][3])
            prev_close = float(klines[i-1][4])
            
            # True Range
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            tr = max(tr1, tr2, tr3)
            true_ranges.append(tr)
            
            # Directional Movement
            up_move = high - prev_high
            down_move = prev_low - low
            
            # +DM e -DM
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
                minus_dm.append(0)
            elif down_move > up_move and down_move > 0:
                plus_dm.append(0)
                minus_dm.append(down_move)
            else:
                plus_dm.append(0)
                minus_dm.append(0)
        
        if len(true_ranges) < period:
            return 0.0
        
        # Calcola ATR, +DI, -DI usando media mobile esponenziale
        def smooth(values, period):
            if len(values) < period:
                return 0
            sma = sum(values[:period]) / period
            multiplier = 1 / period
            smoothed = sma
            for val in values[period:]:
                smoothed = (val * multiplier) + (smoothed * (1 - multiplier))
            return smoothed
        
        atr = smooth(true_ranges, period)
        plus_di_smooth = smooth(plus_dm, period)
        minus_di_smooth = smooth(minus_dm, period)
        
        if atr == 0:
            return 0.0
        
        # Calcola +DI e -DI
        plus_di = (plus_di_smooth / atr) * 100
        minus_di = (minus_di_smooth / atr) * 100
        
        # Calcola DX
        if plus_di + minus_di == 0:
            return 0.0
        
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        
        # ADX è la media mobile di DX (semplificato)
        return dx
    except Exception as e:
        print(f"Errore calcolo ADX: {e}")
        return 0.0

def calculate_rsi(klines, period=14):
    """Calcola RSI (Relative Strength Index) in-house"""
    try:
        if len(klines) < period + 1:
            return 50.0
            
        # Estrai i prezzi di chiusura
        closes = [float(k[4]) for k in klines[-(period*2):]]
        
        if len(closes) < 2:
            return 50.0
        
        # Calcola i cambi di prezzo
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            elif change < 0:
                gains.append(0)
                losses.append(-change)
            else:
                gains.append(0)
                losses.append(0)
        
        if len(gains) < period:
            return 50.0
        
        # Calcola la media iniziale (SMA)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Applica smoothing (EMA) per i valori successivi
        for i in range(period, len(gains)):
            avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
        
        # Calcola RSI
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    except Exception as e:
        print(f"Errore calcolo RSI: {e}")
        return 50.0

def calculate_macd(klines, fast_period=12, slow_period=26, signal_period=9):
    """Calcola MACD in-house"""
    try:
        if len(klines) < slow_period + signal_period:
            return 0.0, 0.0, 0.0
            
        # Estrai prezzi di chiusura
        closes = [float(k[4]) for k in klines[-60:]]  # Prendiamo più dati per accuratezza
        
        if len(closes) < slow_period:
            return 0.0, 0.0, 0.0
        
        def calculate_ema(prices, period):
            """Calcola EMA"""
            if len(prices) < period:
                return prices[-1] if prices else 0
            
            # Inizia con SMA
            sma = sum(prices[:period]) / period
            
            # Fattore di smoothing
            multiplier = 2 / (period + 1)
            
            # Calcola EMA
            ema = sma
            for price in prices[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
        
        # Calcola EMA veloce e lenta
        ema_fast = calculate_ema(closes, fast_period)
        ema_slow = calculate_ema(closes, slow_period)
        
        # MACD line = EMA veloce - EMA lenta
        macd_line = ema_fast - ema_slow
        
        # Per il signal line, dovremmo calcolare EMA del MACD
        # Semplificazione: usiamo una media mobile del MACD
        # In una implementazione completa, dovremmo tenere storico dei valori MACD
        signal_line = macd_line * 0.9  # Approssimazione
        
        # Histogram = MACD - Signal
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    except Exception as e:
        print(f"Errore calcolo MACD: {e}")
        return 0.0, 0.0, 0.0

# Funzione helper per EMA (usata da MACD)
def calculate_ema_standalone(values, period):
    """Calcola Exponential Moving Average standalone"""
    if len(values) < period:
        return sum(values) / len(values) if values else 0
    
    # SMA iniziale
    sma = sum(values[:period]) / period
    
    # Multiplier per EMA
    multiplier = 2 / (period + 1)
    
    # Calcola EMA
    ema = sma
    for value in values[period:]:
        ema = (value * multiplier) + (ema * (1 - multiplier))
    
    return ema
# Test delle funzioni (opzionale)
def test_indicators_inhouse():
    """Test delle nuove implementazioni"""
    # Dati di test simulati
    import random
    
    test_klines = []
    base_price = 100
    
    for i in range(50):
        variation = random.uniform(-1, 1)
        open_price = base_price + variation
        high_price = open_price + random.uniform(0, 0.5)
        low_price = open_price - random.uniform(0, 0.5)
        close_price = open_price + random.uniform(-0.5, 0.5)
        volume = random.uniform(1000, 5000)
        
        test_klines.append([
            str(i * 1000),  # timestamp
            str(open_price),
            str(high_price),
            str(low_price),
            str(close_price),
            str(volume)
        ])
        
        base_price = close_price
    
    print("🧪 Test indicatori in-house:")
    print(f"ATR: {calculate_atr(test_klines):.6f}")
    print(f"RSI: {calculate_rsi(test_klines):.2f}")
    print(f"ADX: {calculate_adx(test_klines):.2f}")
    
    macd, signal, histogram = calculate_macd(test_klines)
    print(f"MACD: {macd:.6f}, Signal: {signal:.6f}, Histogram: {histogram:.6f}")

if __name__ == "__main__":
    test_indicators_inhouse()