from trading_functions import *
import webbrowser
import telegram
import asyncio


bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Definisci una funzione asincrona per monitorare il prezzo
async def monitor_price():
    # MENU
    tempo_controllo = 10
    categoria = 'linear'
    symbol = input('inserisci la moneta: ')
    prezzo_allert = input('inserisci prezzo allert: ')
    print('Ti avviserò non appena la moneta arriverà al prezzo indicato')
    print('PAIR=',symbol)
    print('ALLERT=',prezzo_allert)

    prezzo_attuale = vedi_prezzo_moneta(categoria, symbol)
    prezzo_allert = float(prezzo_allert)

    if prezzo_allert <= prezzo_attuale:
        tipo = True
    else:
        tipo = False 

    while tipo == True:
        if prezzo_attuale <= prezzo_allert:
            messaggio = f"Il prezzo di {symbol} è arrivato a {prezzo_allert}!"
            print(messaggio)
            webbrowser.open_new('https://www.bybit.com/trade/usdt/'+symbol)
            await bot.send_message(chat_id=CHAT_ID, text=messaggio)
            break
        else:
            print(f"Il prezzo di {symbol} NON è arrivato a target...")
            print('Prezzo attuale: ', prezzo_attuale)
            print('Prezzo allert: ', prezzo_allert)
            time.sleep(10)
            prezzo_attuale = vedi_prezzo_moneta(categoria, symbol)

    while tipo == False:
        if prezzo_attuale >= prezzo_allert:
            messaggio = f"Il prezzo di {symbol} è arrivato a {prezzo_allert}!"
            print(messaggio)
            webbrowser.open_new('https://www.bybit.com/trade/usdt/'+symbol)
            await bot.send_message(chat_id=CHAT_ID, text=messaggio)
            break
        else:
            print(f"Il prezzo di {symbol} NON è arrivato a target...")
            print('Prezzo attuale: ', prezzo_attuale)
            print('Prezzo allert: ', prezzo_allert)
            time.sleep(60)
            prezzo_attuale = vedi_prezzo_moneta(categoria, symbol)

    print("Fine")

# Esegui l'evento principale
asyncio.run(monitor_price())