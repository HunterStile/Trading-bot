from trading_functions import *
import webbrowser

#MENU
categoria = 'linear'
symbol = input('inserisci la moneta: ')
prezzo_allert = input('inserisci prezzo allert: ')
print('Ti avviserò non appena la moneta arrivarà al prezzo indicato')
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
        print("il prezzo è arrivato a target!")
        webbrowser.open_new('https://www.bybit.com/trade/usdt/'+symbol)
        break
    else:
        print("il prezzo NON è arrivato a target...")
        print('prezzo attuale: ', prezzo_attuale)
        print('prezzo allert: ', prezzo_allert)
        time.sleep(10)
        prezzo_attuale = vedi_prezzo_moneta(categoria, symbol)

while tipo == False:
    if prezzo_attuale >= prezzo_allert:
        print("il prezzo è arrivato a target!")
        webbrowser.open_new('https://www.bybit.com/trade/usdt/'+symbol)
        break
    else:
        print("il prezzo NON è arrivato a target...")
        print('prezzo attuale: ', prezzo_attuale)
        print('prezzo allert: ', prezzo_allert)
        time.sleep(10)
        prezzo_attuale = vedi_prezzo_moneta(categoria, symbol)



print("fine")