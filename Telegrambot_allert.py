from config import *
import webbrowser
import telegram
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, JobQueue
import asyncio
from trading_functions import vedi_prezzo_moneta
import logging
import time


# Stati per la conversazione
SYMBOL, PRICE = range(2)

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def monitor_price(context: CallbackContext):
    job = context.job
    categoria = 'linear'
    symbol = job.context['symbol']
    prezzo_allert = job.context['prezzo_allert']
    chat_id = job.context['chat_id']
    
    prezzo_attuale = vedi_prezzo_moneta(categoria, symbol)

    if job.context['tipo']:  # Se tipo è True, controlliamo che il prezzo attuale sia minore o uguale al prezzo di alert
        if prezzo_attuale <= prezzo_allert:
            messaggio = f"Il prezzo di {symbol} è arrivato a {prezzo_allert}!"
            webbrowser.open_new('https://www.bybit.com/trade/usdt/'+symbol)
            context.bot.send_message(chat_id=chat_id, text=messaggio)
            job.schedule_removal()
    else:  # Se tipo è False, controlliamo che il prezzo attuale sia maggiore o uguale al prezzo di alert
        if prezzo_attuale >= prezzo_allert:
            messaggio = f"Il prezzo di {symbol} è arrivato a {prezzo_allert}!"
            webbrowser.open_new('https://www.bybit.com/trade/usdt/'+symbol)
            context.bot.send_message(chat_id=chat_id, text=messaggio)
            job.schedule_removal()

def start(update: Update, context: CallbackContext) -> int:
    """Inizia la conversazione e chiede all'utente di inserire il simbolo della moneta."""
    update.message.reply_text(
        'Benvenuto! Inserisci il simbolo della moneta che vuoi monitorare.'
    )
    return SYMBOL

def symbol(update: Update, context: CallbackContext) -> int:
    """Salva il simbolo della moneta e chiede il prezzo di alert."""
    context.user_data['symbol'] = update.message.text.upper()
    update.message.reply_text(
        f"Hai inserito {context.user_data['symbol']}. Ora inserisci il prezzo di alert."
    )
    return PRICE

def price(update: Update, context: CallbackContext) -> int:
    """Salva il prezzo di alert e avvia il monitoraggio."""
    context.user_data['prezzo_allert'] = float(update.message.text)
    symbol = context.user_data['symbol']
    prezzo_allert = context.user_data['prezzo_allert']
    
    update.message.reply_text(
        f"Monitorerò il prezzo di {symbol} e ti avviserò quando raggiungerà {prezzo_allert}."
    )

    prezzo_attuale = vedi_prezzo_moneta('linear', symbol)

    if prezzo_allert <= prezzo_attuale:
        tipo = True
    else:
        tipo = False

    context.job_queue.run_repeating(
        monitor_price,
        interval=60,
        first=0,
        context={'symbol': symbol, 'prezzo_allert': prezzo_allert, 'tipo': tipo, 'chat_id': update.message.chat_id}
    )

    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Annulla la conversazione."""
    update.message.reply_text('Conversazione annullata.')
    return ConversationHandler.END

def main():
    """Avvia il bot."""
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Gestori di conversazione
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SYMBOL: [MessageHandler(Filters.text & ~Filters.command, symbol)],
            PRICE: [MessageHandler(Filters.text & ~Filters.command, price)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher = updater.dispatcher
    dispatcher.add_handler(conv_handler)

    # Avvia il Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

