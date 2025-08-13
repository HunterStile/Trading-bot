from config import *
import threading
from selenium.webdriver import Chrome
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from time import sleep
import time
from pybit.unified_trading import HTTP
from random import randint
from bs4 import BeautifulSoup
from enum import Enum
from datetime import datetime
import requests

#Variabili 
a = 1
b = 2
attesa = 60

#CONFIGURAZIONE BROWSER#
def configurazione_browser():
    chrome_driver_path = leggi_txt(path)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = leggi_txt(chrome_scelto)
    driver =Chrome(service=Service(chrome_driver_path),options=chrome_options)
    sleep(randint(a,b))
    return driver

def leggi_txt(nome_file):
    try:
        with open(nome_file, 'r') as file:
            prima_riga = file.readline().strip()  # Legge la prima riga e rimuove eventuali spazi bianchi iniziali/finali
            return prima_riga
    except FileNotFoundError:
        print(f"Errore: Il file '{nome_file}' non è stato trovato.")
        return None
    except Exception as e:
        print(f"Errore durante la lettura del file '{nome_file}': {e}")
        return None

#FUNZIONI SCRAPING#
def Scraping_binance(query,driver):
    trovato=False

    url = 'https://www.binance.com/en/support/announcement/new-cryptocurrency-listing?c=48&navId=48'
    driver.get(url)

    # Recupera i link degli annunci
    link_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/en/support/announcement"]')
    links = [link_element.get_attribute('href') for link_element in link_elements]

    # Salva i link in un file txt
    with open('announcements.txt', 'r+') as file:
        for link in links:
            # Leggi il contenuto del file e controlla se il link è già presente
            file.seek(0)
            if link in file.read():
                continue
            # Scrivi il link nel file e stampalo
            trovato=True
            file.write(link + '\n')
            print("Nuovo annuncio trovato!, Verifico la Query!")
            # Controllo la query
            check = is_name_in_string(query,link)
            if check==True:
                print("La Query è stata trovata!")
                print("Sto effettuando l'operazione...")
                return True
            else:
                print("La Query non è stata trovata!")
           
    if trovato == False:
        print("Nessun annuncio trovato, riprovo...")
    
    else:
        print("Nuovi Annunci inseriti!")
    driver.quit()

def scrape_cryptopanic():
    url = "https://cryptopanic.com/"

   
    driver = configurazione_browser()

    try:
        driver.get(url)
        #WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "news-row-link")))
        driver.implicitly_wait(10)
        #croll_to_bottom(driver)
    except Exception as e:
        print(f"Error during loading the page: {e}")
        driver.quit()
        return

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    news_items = soup.select(".news-row-link")

    return news_items

def save_to_txt(news_items, file_path, query_keywords=None, max_articles=10):
    if query_keywords is None:
        query_keywords = []  # Se la lista delle parole chiave non è fornita, impostala come lista vuota

    with open(file_path, "a") as file:
        for idx, item in enumerate(news_items[:max_articles], 1):
            title = item.select_one(".nc-title span span").get_text()
            source = item.select_one(".si-source-domain").get_text()
            link = "https://cryptopanic.com" + item.select_one(".nc-title")["href"]

            news = f"Title: {title}\nSource: {source}\nLink: {link}\n"

            if not is_duplicate_title(file_path, title):
                file.write(news)
                file.write("-" * 30 + "\n")
                print("Nuova Notizia!")
                print("Controllo la query...")

                for keyword in query_keywords:
                    if is_string_in_title(title, keyword):
                        # Esegui l'azione desiderata quando trovi una corrispondenza
                        print(f"Parola chiave '{keyword}' trovata! Esegui azione...")
                        
                        print(f"{keyword} trovato la query! Esegui l'operazione...")
                        return True

                else:
                    print("Nessuna corrispondenza con le parole chiave nella query!")

            else:
                print("Nessuna nuova notizia, riprovo.")

            if idx == max_articles:
                return False

#FUNZIONI SECONDARIE#
def save_list_to_file(lst, filename):
    with open(filename, 'w') as f:
        for item in lst:
            f.write("%s\n" % item)

def is_name_in_string(name, string):
    #Restituisce True se il nome è presente nella stringa, False altrimenti.
    return name.lower() in string.lower()

def is_duplicate_title(file_path, title):
    with open(file_path, "r") as file:
        content = file.read()
        return title in content

def scroll_to_bottom(driver):
    # Simulate scroll to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Add a small delay to let the content load

def is_string_in_title(title, query):
    return query.lower() in title.lower()

def leggi_simboli_da_file(nome_file):
    with open(nome_file, 'r') as file:
        simboli = file.readlines()
        # Rimuovi eventuali spazi bianchi e newline all'inizio e alla fine di ciascuna riga
        simboli = [simbolo.strip() for simbolo in simboli]
    return simboli

def execute_thread(func, args):
    thread = threading.Thread(target=func, args=args)
    thread.start()
    return thread
#FUNZIONI BYBIT#
def get_server_time():
    try:
        # Usa il nuovo endpoint v5 per il server time
        response = requests.get("https://api.bybit.com/v5/market/time")
        if response.status_code == 200:
            data = response.json()
            if data['retCode'] == 0:
                # Il tempo è in millisecondi, convertiamo in secondi
                server_time = int(data['result']['timeSecond'])
                return float(server_time)
            else:
                print(f"Errore API Bybit: {data['retMsg']}")
                return None
        else:
            print(f"Errore HTTP: {response.status_code}")
            return None
    except Exception as e:
        print(f"Errore durante il recupero del tempo del server di Bybit: {e}")
        return None
    
def check_timestamp(recv_window, timestamp):
    server_time = get_server_time() * 1000  # Converti il tempo Unix in millisecondi
    if server_time is not None:
        lower_bound = server_time - recv_window
        upper_bound = server_time + 1000
        print("Lower Bound:", lower_bound)
        print("Upper Bound:", upper_bound)
        print("Timestamp:", timestamp)
        return lower_bound <= timestamp < upper_bound
    else:
        return False

def compra_moneta_bybit2(categoria, pair, quantita):
    session = HTTP(
        testnet=False,
        api_key=api,
        api_secret=api_sec,
    )
    
    # Ottieni il timestamp attuale
    timestamp = int(time.time() * 1000)
    
    # Verifica che il timestamp soddisfi le regole
    recv_window = 5000  # Puoi impostare questo valore in base alle raccomandazioni di Bybit
    if not check_timestamp(recv_window, timestamp):
        print("Errore: Il timestamp non soddisfa le regole.")
        return None
    
    # Ottieni il prezzo della moneta
    prezzo = vedi_prezzo_moneta(categoria, pair)
    if prezzo is None:
        print("Errore: Impossibile ottenere il prezzo della moneta.")
        return None
    
    # Calcola il numero di token da acquistare
    token = int(quantita / prezzo)
    
    # Effettua l'ordine di acquisto di mercato
    response = session.place_order(
        category=categoria,
        symbol=pair,
        side="Buy",
        orderType="Market",
        qty=token
    )
    
    if 'order_id' in response:
        print("Ordine di acquisto effettuato con successo.")
        return token
    else:
        print("Errore durante l'ordine di acquisto:", response)
        return None

def compra_moneta_bybit_by_quantita(categoria,pair,quantita):
    prezzo = vedi_prezzo_moneta(categoria,pair)
    token = int(quantita/prezzo)

    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    
    print(session.place_order(
    category=categoria,
    symbol=pair,
    side="Buy",
    orderType="Market",
    qty=token,
))
    return token

def compra_moneta_bybit_by_token(categoria,pair,token):
    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    
    print(session.place_order(
    category=categoria,
    symbol=pair,
    side="Buy",
    orderType="Market",
    qty=token,
))
    return token

def vendi_moneta_bybit_by_quantita(categoria,pair,quantita):
    prezzo = vedi_prezzo_moneta(categoria,pair)
    token = int(quantita/prezzo)

    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    
    
    print(session.place_order(
    category=categoria,
    symbol=pair,
    side="Sell",
    orderType="Market",
    qty=token,
))
    return token

def vendi_moneta_bybit_by_token(categoria,pair,token):
    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    
    print(session.place_order(
    category=categoria,
    symbol=pair,
    side="Sell",
    orderType="Market",
    qty=token,
))
    return token

def chiudi_operazione_long(categoria,pair,token):
    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    
    print(session.place_order(
    category=categoria,
    symbol=pair,
    side="Sell",
    orderType="Market",
    qty=token
    ))

def chiudi_operazione_short(categoria,pair,token):
    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    
    print(session.place_order(
    category=categoria,
    symbol=pair,
    side="Buy",
    orderType="Market",
    qty=token
    ))
    
def vedi_prezzo_moneta(categoria,pair):
    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    response = session.get_orderbook(category=categoria, symbol=pair)
    b_values = response['result']['b']

    # Il valore in prima posizione della lista è il prezzo più basso
    lowest_price = float(b_values[0][0])
    return (lowest_price)

def mostra_saldo():
    # Get wallet balance of the Unified Trading Account
    session = HTTP(
    testnet=False,
    api_key=api,
    api_secret=api_sec,
    )
    response = session.get_wallet_balance(accountType="UNIFIED")
    response_data = response['result']['list'][0]  # Accedi alla parte del dizionario che contiene i dati dell'account
    total_equity = response_data['totalEquity']  # Estrai il valore di 'totalEquity'

    # Stampa o fai ciò che vuoi con 'total_equity'
    print(f'Total Equity: {total_equity}')

    from datetime import datetime, timedelta

def ottieni_prezzi(categoria,simbolo):
    session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
    print(session.get_orderbook(category=categoria, symbol=simbolo))

def get_kline_printato(categoria, simbolo, intervallo, limit):
    # Inizializza la sessione HTTP con le tue chiavi API
    session = HTTP(testnet=False, api_key=api, api_secret=api_sec)

    # Ottieni i dati Kline per il simbolo specifico con il limite specificato
    kline_data = session.get_kline(
        category=categoria,
        symbol=simbolo,
        interval=intervallo,
        limit=limit
    )["result"]

    # Verifica se ci sono dati disponibili
    if "list" in kline_data and kline_data["list"]:
        # Inverti l'ordine della lista dei dati Kline
        reversed_klines = reversed(kline_data["list"])
        # Itera sul numero di candele nella lista
        for i, data_list in enumerate(reversed_klines):
            # Stampa i dati Kline
            print(f"\nCandela {i + 1}:")
            print(f"Open price: {data_list[1]}")
            print(f"High price: {data_list[2]}")
            print(f"Low price: {data_list[3]}")
            print(f"Close price: {data_list[4]}")
    else:
        print(f"Nessun dato Kline disponibile per il simbolo {simbolo}")

def get_kline_data(categoria, simbolo, intervallo, limit=200):
    # Inizializza la sessione HTTP con le tue chiavi API
    session = HTTP(testnet=False, api_key=api, api_secret=api_sec)

    # Ottieni i dati Kline per il simbolo specifico con il limite specificato
    kline_data = session.get_kline(
        category=categoria,
        symbol=simbolo,
        interval=intervallo,
        limit=limit
    )["result"]

    # Verifica se ci sono dati disponibili
    if "list" in kline_data and kline_data["list"]:
        # Restituisci la lista dei dati Kline
        return kline_data["list"]
    else:
        print(f"Nessun dato Kline disponibile per il simbolo {simbolo}")
        return []

def get_kline_data_with_dates(categoria, simbolo, intervallo, start_timestamp=None, end_timestamp=None, limit=200):
    """
    Ottieni dati Kline con date specifiche usando PyBit
    
    Args:
        categoria: Categoria del trading (linear, spot, etc.)
        simbolo: Simbolo da scaricare (es. BTCUSDT)
        intervallo: Timeframe (D, 240, 60, etc.)
        start_timestamp: Timestamp inizio in millisecondi (opzionale)
        end_timestamp: Timestamp fine in millisecondi (opzionale)
        limit: Numero massimo di candele da scaricare
        
    Returns:
        Lista di candele OHLCV
    """
    # Inizializza la sessione HTTP
    session = HTTP(testnet=False, api_key=api, api_secret=api_sec)
    
    # Prepara parametri per la richiesta
    params = {
        "category": categoria,
        "symbol": simbolo,
        "interval": intervallo,
        "limit": limit
    }
    
    # Aggiungi timestamp se forniti
    if start_timestamp:
        params["start"] = int(start_timestamp)
    if end_timestamp:
        params["end"] = int(end_timestamp)
    
    try:
        # Esegui richiesta
        kline_data = session.get_kline(**params)["result"]
        
        # Verifica se ci sono dati disponibili
        if "list" in kline_data and kline_data["list"]:
            return kline_data["list"]
        else:
            print(f"Nessun dato Kline disponibile per {simbolo} nel periodo richiesto")
            return []
            
    except Exception as e:
        print(f"Errore nel download dati per {simbolo}: {e}")
        return []

#FUNZIONI TRADING#
def totale_pnl(quantita_acquistata, prezzo_acquisto, prezzo_attuale):
    return (prezzo_attuale - prezzo_acquisto) * quantita_acquistata 

def calculate_simple_moving_average(prices, period):
    # Calcola la media mobile semplice
    sma = [sum(prices[i - period + 1:i + 1]) / period for i in range(period - 1, len(prices))]
    return sma

def media_esponenziale(prices, period):
    alpha = 2 / (period + 1)
    ema = [prices[0]]

    for i in range(1, len(prices)):
        ema_t = (prices[i] * alpha) + (ema[i - 1] * (1 - alpha))
        ema.append(ema_t)

    return ema

def candele_sopra_ema(categoria, simbolo, intervallo, periodo_ema,numero_candele):
    # Ottieni tutti i dati Kline (ultime 200 candele)
    kline_data_all = get_kline_data(categoria, simbolo, intervallo, limit=200)
    
    kline_data_last_5 = kline_data_all[:numero_candele]

    # Estrai le open prices dalle ultime x candele
    open_prices_last_5 = [float(data[4]) for data in kline_data_last_5]
    print(open_prices_last_5)

    # Cambia l'ordine dei dati per il calcolo dell'ema.
    reversed_klines = reversed(kline_data_all)
    # Estrai tutte le open prices per il calcolo dell'EMA
    open_prices_all = [float(data[4]) for data in reversed_klines]

    # Calcola l'EMA 
    ema= media_esponenziale(open_prices_all, periodo_ema)
    
    reversed_ema=list(reversed(ema))
    print(reversed_ema)
    # Verifica se tutte le open prices delle ultime 5 candele sono sopra l'EMA
    all_above_ema = all(open_price > reversed_ema[i] for i, open_price in enumerate(open_prices_last_5))

    return all_above_ema

def controlla_candele_sopra_ema(categoria, coppia, intervallo, periodo_ema):
        candele_sopra_ema = 0
        # Ottieni i dati Kline per la coppia corrente
        kline_data_all = get_kline_data(categoria, coppia, intervallo, limit=200)
        
        if kline_data_all:
            # Estrai il timestamp della prima candela nei nuovi dati Kline
            timespamp_totali = [float(data[0]) for data in kline_data_all]
            # Estrai il timestamp piu recente
            timestamp_attuale= timespamp_totali[-1]

            risultato = 0
            kline_data_last_200 = kline_data_all[:200]

            # Estrai le open prices dalle ultime x candele
            close_prices_200 = [float(data[4]) for data in kline_data_last_200]
            
            # Cambia l'ordine dei dati per il calcolo dell'ema.
            reversed_klines = reversed(kline_data_all)

            # Estrai tutte le open prices per il calcolo dell'EMA
            close_prices = [float(data[4]) for data in reversed_klines]
            # Estrai il prezzo di chiusura più recente
            prezzo_attuale = close_prices[-1]

            # Calcola l'EMA 
            ema = media_esponenziale(close_prices, periodo_ema)
            reversed_ema=list(reversed(ema))

            # Calcola la differenza in percentuale tra il prezzo attuale e l'EMA
            differenza_percentuale = ((prezzo_attuale - ema[-1]) / ema[-1]) * 100
            
            
            # Verifica quanti periodi consecutivi la coppia ha chiuso sopra l'EMA
            for i, close_price in enumerate(close_prices_200):
                if close_price < reversed_ema[i]:
                    break  # Fermati non appena una candela si trova sotto l'EMA
                else:
                    candele_sopra_ema += 1
            if candele_sopra_ema > 0:      
                risultato = candele_sopra_ema 

        return risultato,prezzo_attuale,differenza_percentuale,timestamp_attuale

def controlla_candele_sotto_ema(categoria, coppia, intervallo, periodo_ema):
        candele_sopra_ema = 0
        # Ottieni i dati Kline per la coppia corrente
        kline_data_all = get_kline_data(categoria, coppia, intervallo, limit=200)
        
        if kline_data_all:
            # Estrai il timestamp della prima candela nei nuovi dati Kline
            timespamp_totali = [float(data[0]) for data in kline_data_all]
            # Estrai il timestamp piu recente
            timestamp_attuale= timespamp_totali[-1]

            risultato = 0
            kline_data_last_200 = kline_data_all[:200]

            # Estrai le open prices dalle ultime x candele
            close_prices_200 = [float(data[4]) for data in kline_data_last_200]
            
            # Cambia l'ordine dei dati per il calcolo dell'ema.
            reversed_klines = reversed(kline_data_all)

            # Estrai tutte le open prices per il calcolo dell'EMA
            close_prices = [float(data[4]) for data in reversed_klines]
            # Estrai il prezzo di chiusura più recente
            prezzo_attuale = close_prices[-1]

            # Calcola l'EMA 
            ema = media_esponenziale(close_prices, periodo_ema)
            reversed_ema=list(reversed(ema))

            # Calcola la differenza in percentuale tra il prezzo attuale e l'EMA
            differenza_percentuale = ((prezzo_attuale - ema[-1]) / ema[-1]) * 100
            
            
            # Verifica quanti periodi consecutivi la coppia ha chiuso sopra l'EMA
            for i, close_price in enumerate(close_prices_200):
                if close_price > reversed_ema[i]:
                    break  # Fermati non appena una candela si trova sotto l'EMA
                else:
                    candele_sopra_ema += 1
            if candele_sopra_ema > 0:      
                risultato = candele_sopra_ema 

        return risultato,prezzo_attuale,differenza_percentuale,timestamp_attuale

def analizza_prezzo_sopra_media(categoria, simbolo, intervallo, periodo_ema):
        # Ottieni i dati Kline per la coppia corrente
        kline_data_all = get_kline_data(categoria, simbolo, intervallo, limit=200)
        
        if kline_data_all:
            # Estrai il timestamp della prima candela nei nuovi dati Kline
            timespamp_totali = [float(data[0]) for data in kline_data_all]
            # Estrai il timestamp piu recente
            timestamp_attuale= timespamp_totali[-1]
         
            # Cambia l'ordine dei dati per il calcolo dell'ema.
            reversed_klines = reversed(kline_data_all)

            # Estrai tutte le close prices per il calcolo dell'EMA
            close_prices = [float(data[4]) for data in reversed_klines]

            # Calcola l'EMA 
            ema = media_esponenziale(close_prices, periodo_ema)
            reversed_ema=list(reversed(ema))

            # Estrai il prezzo di chiusura più recente
            prezzo_attuale = close_prices[-1]
            # Calcola la differenza in percentuale tra il prezzo attuale e l'EMA
            differenza_percentuale = ((prezzo_attuale - ema[-1]) / ema[-1]) * 100
            
            # Controlla se il prezzo di chiusura più recente è sopra la EMA
            
            sopra_ema = prezzo_attuale > reversed_ema[-1]

        return sopra_ema, differenza_percentuale,prezzo_attuale,timestamp_attuale

def bot_analisi(categoria,periodo_ema):
    
    menu = input("MENU\n1-Analizza coppia \n2-Scraping allert\n3-Visualizza tutti gli Allert\n4-Elimina un allert\nInserisci un valore: ")

    if menu == ('1'):
        print("\nBenvenuto nel bot di analisi di Hunterstile!")
        simbolo = input("\nScegli un coppia: ")
        print(f"\nHai scelto: {simbolo} "
            f"\nEma utilizzata:{periodo_ema}"
            )
        print(f"\nAnalizzo il grafico mensile:")
        analisi = analizza_prezzo_sopra_media(categoria, simbolo, "M", periodo_ema)
        sopra_ema = analisi[0]
        differenza_percentuale = analisi[1]
        if sopra_ema == True:
            analisi = controlla_candele_sopra_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sopra l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")
            

        else:
            analisi = controlla_candele_sotto_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sotto l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")

        print(f"\nAnalizzo il grafico Settimanale:")
        analisi = analizza_prezzo_sopra_media(categoria, simbolo, "W", periodo_ema)
        sopra_ema = analisi[0]
        differenza_percentuale = analisi[1]
        if sopra_ema == True:
            analisi = controlla_candele_sopra_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sopra l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")
            
        else:
            analisi = controlla_candele_sotto_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sotto l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")
        
        print(f"\nAnalizzo il grafico Giornaliero:")
        analisi = analizza_prezzo_sopra_media(categoria, simbolo, "D", periodo_ema)
        sopra_ema = analisi[0]
        differenza_percentuale = analisi[1]
        if sopra_ema == True:
            analisi = controlla_candele_sopra_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sopra l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")
        else:
            analisi = controlla_candele_sotto_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sotto l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")

        
        print(f"\nAnalizzo il grafico 4 ore:")
        analisi = analizza_prezzo_sopra_media(categoria, simbolo, "240", periodo_ema)
        sopra_ema = analisi[0]
        differenza_percentuale = analisi[1]
        if sopra_ema == True:
            analisi = controlla_candele_sopra_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sopra l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")
        else:
            analisi = controlla_candele_sotto_ema(categoria, simbolo,"M", periodo_ema)
            risultato = analisi[0]
            print(f"la coppia: {simbolo} si trova sotto l'ema {periodo_ema} del {differenza_percentuale:.2f}%. da {risultato} candele")


        input("\nPremere Enter per tornare indietro...")
        return bot_analisi(categoria,periodo_ema)
    
    elif menu ==('2'):
        print("\nPagina in costruzione...")

        input("\nPremere Enter per tornare indietro...")
        return bot_analisi(categoria,periodo_ema)

def nuova_candela(kline_data, ultimo_timestamp_precedente):

    # Estrai il timestamp della prima candela nei nuovi dati Kline
    timespamp_totali = [float(data[0]) for data in kline_data]

    # Estrai il timestamp piu recente
    nuovo_timestamp = timespamp_totali[-1]
    print(nuovo_timestamp)

    # Confronta il timestamp della prima candela nei nuovi dati Kline con il timestamp precedente
    return nuovo_timestamp != ultimo_timestamp_precedente

def estrai_ultimo_timestamp(kline_data):
    # Estrai il timestamp della prima candela nei nuovi dati Kline
    timespamp_totali = [float(data[0]) for data in kline_data]
    # Estrai il timestamp piu recente
    timestamp_attuale= timespamp_totali[-1]
    return timestamp_attuale

def estrai_prezzo_ultima_candela(kline_data):
    close_prices = [float(data[4]) for data in kline_data]
    last_price = close_prices[-1]
    return last_price

def bot_trailing_stop(categoria,simbolo,periodo_ema,intervallo,token,candele,operazione):
    chiudi_operazione = True
    timestamp_precedente = 0
    while chiudi_operazione == True:
        #ESTRAZIONE GRAFICO
        
        kline_data_all = get_kline_data(categoria, simbolo, intervallo, limit=200)
        timestamp_attuale = estrai_ultimo_timestamp(kline_data_all)
        if timestamp_attuale != timestamp_precedente:
            print("Nuova Candela")
            print(f"\nAnalizzo il grafico con Ema {periodo_ema}")
            #ANALISI DEL GRAFICO
            if operazione == True:
                analisi = controlla_candele_sotto_ema(categoria, simbolo, intervallo, periodo_ema)
            else:
                analisi = controlla_candele_sopra_ema(categoria, simbolo, intervallo, periodo_ema)
            risultato = analisi[0]
            prezzo = analisi[1]
            differenza_percentuale = analisi[2]
            timestamp_attuale = analisi[3]
            timestamp_precedente = timestamp_attuale
            
            if risultato < candele:
                print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema del {(differenza_percentuale):.2f}% da {risultato} candele  ")
                print(f"Candele non raggiunte...")
                
            else:
                print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema del {(differenza_percentuale):.2f}% da {risultato} candele ")
                print(f"Candele raggiunte, chiudo l'operazione...")
                if operazione == True:
                    token = chiudi_operazione_long(categoria,simbolo,token)
                else:
                    token = chiudi_operazione_short(categoria,simbolo,token)
                chiudi_operazione = False
                
        else:
            print("Aspetto nuova candela...") 
            sleep(attesa)

    return 

def bot_open_position(categoria,simbolo,periodo_ema,intervallo,quantita,candele,lunghezza,operazione):
    print(f"\nMoneta da scambiare: {simbolo} ")
    print(f"\nEma utilizzata:{periodo_ema}")
    print(f"\nIntervallo utilizzato:{intervallo}")
    print(f"\nCandele di riferimento scelte.:{candele}")
    if operazione == True:
        print(f"\nTipo di operazione.: LONG")
    else:
        print(f"\nTipo di operazione.: SHORT")
    sleep(3)
    timestamp_precedente = 0
    cerca_operazione = True
    while cerca_operazione == True:
        #ESTRAZIONE GRAFICO
        kline_data_all = get_kline_data(categoria, simbolo, intervallo, limit=200)
        timestamp_attuale = estrai_ultimo_timestamp(kline_data_all)
        if timestamp_attuale != timestamp_precedente:
            print("Nuova Candela")
            print(f"Analizzo il grafico di  {simbolo} con Ema {periodo_ema}")
            #ANALISI DEL GRAFICO
            if operazione == True:
                analisi = controlla_candele_sopra_ema(categoria, simbolo, intervallo, periodo_ema)
            else:
                analisi = controlla_candele_sotto_ema(categoria, simbolo, intervallo, periodo_ema)
            risultato = analisi[0]
            prezzo = analisi[1]
            differenza_percentuale = analisi[2]
            timestamp_attuale = analisi[3]
            timestamp_precedente = timestamp_attuale    
            if  risultato < candele:
                print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema del {(differenza_percentuale):.2f}% da {risultato} candele ")
                print(f"Candele non raggiunte...")
                trend_4_ore = False
            else:
                print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema del {(differenza_percentuale):.2f}% da {risultato} candele ")
                print(f"Candele raggiunte!")
                trend_4_ore = True
                if differenza_percentuale > lunghezza:
                    print(f"Prezzo troppo per alto per la media, aspetto prossima candela...")
                else:

                    #Analisi sul grafico sul minuto
                    if operazione == True:
                        analisi = controlla_candele_sopra_ema(categoria, simbolo, 1, periodo_ema)
                    else:
                        analisi = controlla_candele_sotto_ema(categoria, simbolo, 1, periodo_ema)

                    risultato = analisi[0]
                    prezzo = analisi[1]
                    differenza_percentuale = analisi[2]
                    timestamp_attuale = analisi[3]
                    timestamp_precedente = timestamp_attuale
                    candele_minuto = 2
                    if risultato <= candele_minuto:
                        print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema sul minuto del {(differenza_percentuale):.2f}% da {risultato} candele ")
                        print(f"Candele non raggiunte...")
                    else:
                        print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema sul minuto del {(differenza_percentuale):.2f}% da {risultato} candele ")
                        print(f"Candele raggiunte!")
                        if operazione == True:
                            token = compra_moneta_bybit_by_quantita(categoria,simbolo,quantita)
                        else:
                            token = vendi_moneta_bybit_by_quantita(categoria,simbolo,quantita)
                        print(f"Ho comprato: {token} {simbolo} a {prezzo} ")
                        cerca_operazione = False
                        sleep(attesa)
                        
        else:
            if trend_4_ore == False:
                print("Aspetto la nuova candela...")
                sleep(attesa)
            else:
                print("Aspetto la nuova candela...")
                #ANALISI DEL GRAFICO
                if operazione == True:
                    analisi = controlla_candele_sopra_ema(categoria, simbolo, intervallo, periodo_ema)
                else:
                    analisi = controlla_candele_sotto_ema(categoria, simbolo, intervallo, periodo_ema)
                risultato = analisi[0]
                prezzo = analisi[1]
                differenza_percentuale = analisi[2]
                timestamp_attuale = analisi[3]
                timestamp_precedente = timestamp_attuale  
                print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema del {(differenza_percentuale):.2f}% da {risultato} candele  ")
                if differenza_percentuale > lunghezza:
                    print(f"Prezzo troppo per alto per la media, aspetto prossima candela...")
                else:
                    #Analisi sul grafico sul minuto
                    if operazione == True:
                        analisi = controlla_candele_sopra_ema(categoria, simbolo, 1, periodo_ema)
                    else:
                        analisi = controlla_candele_sotto_ema(categoria, simbolo, 1, periodo_ema)

                    risultato = analisi[0]
                    prezzo = analisi[1]
                    differenza_percentuale = analisi[2]
                    timestamp_attuale = analisi[3]
                    timestamp_precedente = timestamp_attuale
                    candele_minuto = 2
                    if risultato < candele_minuto:
                        print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema sul minuto del {(differenza_percentuale):.2f}% da {risultato} candele ")
                        print(f"Candele non raggiunte...")
                    else:
                        print(f"la coppia: {simbolo} si trova a {prezzo} con differenza dall'ema sul minuto del {(differenza_percentuale):.2f}% da {risultato} candele ")
                        print(f"Candele raggiunte!")
                        if operazione == True:
                            token = compra_moneta_bybit_by_quantita(categoria,simbolo,quantita)
                        else:
                            token = vendi_moneta_bybit_by_quantita(categoria,simbolo,quantita)
                        print(f"Ho comprato: {token} {simbolo} a {prezzo} ")
                        cerca_operazione = False
                sleep(attesa)

    return token
    
def scelta_moneta_operazione(): 
    simbolo = input("Inserisci il simbolo della moneta: ")
    quantita = int(input("Inserisci la quantità(se è per traling stop, inserire token): "))
    tipo_operazione = input("Inserisci il tipo di operazione: ")
    tipo_operazione = tipo_operazione.lower()
    if tipo_operazione == "buy":
        tipo_operazione = True
    elif tipo_operazione == "sell":
        tipo_operazione = False
    else:
        print("Tipo di operazione non valido.")
    
    print(f"Simbolo: {simbolo}")
    print(f"Quantità: {quantita}")
    print(f"Tipo operazione(Buy/Sell): {tipo_operazione}")
    

    conferma = input("Sei sicuro di voler procedere? S/N: ")
    if conferma.lower() == "s":
        print("Operazione confermata, procedo...")
        sleep(3)
    else:
        print("Operazione annullata.")
        scelta_moneta_operazione()
        return  # Exit the function if the operation is canceled

    return simbolo, quantita, tipo_operazione