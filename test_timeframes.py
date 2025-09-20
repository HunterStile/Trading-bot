from trading_functions import get_kline_data

# Test con formato attuale (1440)
print('🔍 Test 1440 minutes:')
try:
    data_1440 = get_kline_data('linear', 'BTCUSDT', 1440, limit=5)
    print(f'✅ 1440 funziona: {len(data_1440)} candele ricevute')
    if data_1440:
        print(f'   Prima candela: {data_1440[0][:6]}')
except Exception as e:
    print(f'❌ 1440 errore: {e}')

# Test con formato giornaliero Bybit (D)
print('\n🔍 Test D (daily):')
try:
    data_D = get_kline_data('linear', 'BTCUSDT', 'D', limit=5)
    print(f'✅ D funziona: {len(data_D)} candele ricevute')
    if data_D:
        print(f'   Prima candela: {data_D[0][:6]}')
except Exception as e:
    print(f'❌ D errore: {e}')

# Test con formato settimanale (W)
print('\n🔍 Test W (weekly):')
try:
    data_W = get_kline_data('linear', 'BTCUSDT', 'W', limit=5)
    print(f'✅ W funziona: {len(data_W)} candele ricevute')
    if data_W:
        print(f'   Prima candela: {data_W[0][:6]}')
except Exception as e:
    print(f'❌ W errore: {e}')

# Test con formato mensile (M)
print('\n🔍 Test M (monthly):')
try:
    data_M = get_kline_data('linear', 'BTCUSDT', 'M', limit=5)
    print(f'✅ M funziona: {len(data_M)} candele ricevute')
    if data_M:
        print(f'   Prima candela: {data_M[0][:6]}')
except Exception as e:
    print(f'❌ M errore: {e}')
