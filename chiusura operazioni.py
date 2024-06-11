from config import *
from trading_functions import *

#SCELTA DELLA MONETA
simbolo = "AVAXUSDT"              #Simbolo della moneta
operazione = True                 #True = Long, False = Short
quantita=300                      #Quantità di contratti#
categoria = "linear"              #spot, linear(Futures), inverse   

#VARIABILI PER LA STRATEGIA
intervallo = 1                      #Intervallo in minuti del gragico
periodo_ema = 10                    #Periodo della media mobile
candele_open = 3                    #Numero di candele per l'apertura della posizione
candele_stop = 3                    #Numero di candele per il trailing stop
lunghezza = 1                       #Distanza in percentuale tra il prezzo di apertura e la media mobile


print("Ciao, stai per aprire un bot per fare trailing stop ad una tua operazione.")
risultati = scelta_moneta_operazione()  
simbolo = risultati[0]
token = risultati[1]
operazione = risultati[2]


bot_trailing_stop(categoria,simbolo,periodo_ema,intervallo,token,candele_stop,operazione)