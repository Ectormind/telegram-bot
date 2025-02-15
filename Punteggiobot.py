import datetime
import asyncio
import json
import os
import logging
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from waitress import serve

# Configurazione Logging
logging.basicConfig(level=logging.INFO)

# Token del bot (da Railway)
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = "https://telegram-bot-production-2303.up.railway.app"

# Variabili globali
ultimo_chat_id = None  
ultima_data_invio = None  
classifica = {}
hashtag_usati = {}

# Dizionario con le parole e i relativi punteggi
parole_punteggio = {
    "#bilancia": 5,
    "#colazioneequilibrata": 5,
    "#collagene": 5,
    "#bombetta": 5,
    "#ricostruttore": 5,
    "#idratazionespecifica": 5,
    "#phytocomplete": 5,
    "#pranzobilanciato": 8,
    "#cenabilanciata": 8,
    "#spuntino1": 8,
    "#spuntino2": 8,
    "#integrazione1": 8,
    "#integrazione2": 8,
    "#workout": 10,
    "#pastosostitutivo": 10,
    "#sensazioni": 10,
    "#kitnewenergy": 10,
    "#fotoiniziale": 10,
    "#fotofinale": 10
}

# Inizializza Flask e il bot
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Carica la classifica dal file JSON
def carica_classifica():
    global classifica
    try:
        with open("classifica.json", "r") as f:
            classifica = json.load(f)
            logging.info("✅ Classifica caricata.")
    except FileNotFoundError:
        classifica = {}

# Salva la classifica nel file JSON
def salva_classifica():
    with open("classifica.json", "w") as f:
        json.dump(classifica, f)
    logging.info("💾 Classifica salvata.")

# Funzioni bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")

async def classifica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ultimo_chat_id
    ultimo_chat_id = update.message.chat_id  

    if not classifica:
        await update.message.reply_text("🏆 La classifica è vuota!")
        return

    classifica_ordinata = sorted(classifica.items(), key=lambda x: x[1], reverse=True)
    messaggio = "🏆 Classifica attuale:\n" + "\n".join(f"{u}: {p} punti" for u, p in classifica_ordinata)
    await update.message.reply_text(messaggio)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resetta la classifica e il registro degli hashtag usati"""
    classifica.clear()
    hashtag_usati.clear()
    salva_classifica()
    await update.message.reply_text("🔄 Classifica e limitazioni resettate con successo!")

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi e assegna punti in base agli hashtag"""
    messaggio = update.message.text or update.message.caption
    if not messaggio:
        return  

    utente = update.message.from_user.username or update.message.from_user.first_name
    if not utente:
        return  

    oggi = datetime.date.today()
    if utente not in hashtag_usati:
        hashtag_usati[utente] = {}

    punti_totali = 0
    parole_trovate = []

    for parola, punti in parole_punteggio.items():
        if parola in messaggio:
            parole_trovate.append(parola)
            if parola not in hashtag_usati[utente] or hashtag_usati[utente][parola] != oggi:
                punti_totali += punti
                hashtag_usati[utente][parola] = oggi  

    if punti_totali > 0:
        classifica[utente] = classifica.get(utente, 0) + punti_totali
        salva_classifica()  
        await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! 🎉 Ora ha {classifica[utente]} punti totali.")
    elif not parole_trovate:
        return  
    else:
        await update.message.reply_text(f"{utente}, hai già usato questi hashtag oggi. ⏳ Prova domani!")

# Webhook Telegram
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, application.bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.process_update(update))
    return "OK", 200

# Invio classifica giornaliera
async def invia_classifica_giornaliera():
    global ultima_data_invio
    while True:
        ora_corrente = datetime.datetime.now()
        if ora_corrente.hour == 0 and ora_corrente.minute < 5:  
            if classifica and ultimo_chat_id and (ultima_data_invio != ora_corrente.date()):
                classifica_ordinata = sorted(classifica.items(), key=lambda x: x[1], reverse=True)
                messaggio = "🏆 Classifica giornaliera 🏆\n" + "\n".join(f"{u}: {p} punti" for u, p in classifica_ordinata)

                try:
                    await application.bot.send_message(chat_id=ultimo_chat_id, text=messaggio)
                    logging.info(f"✅ Classifica inviata alla chat {ultimo_chat_id}")
                    ultima_data_invio = ora_corrente.date()
                except Exception as e:
                    logging.error(f"❌ Errore nell'invio della classifica: {e}")

            await asyncio.sleep(300)  
        else:
            await asyncio.sleep(30)  

def avvia_classifica_thread():
    """Avvia il loop per inviare la classifica giornaliera in un thread separato"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(invia_classifica_giornaliera())

# Avvio del bot
if __name__ == "__main__":
    logging.info("⚡ Il bot è avviato!")
    carica_classifica()

    # Aggiunta comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("classifica", classifica_bot))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestisci_messaggi))

    # Avvia il thread per la classifica
    threading.Thread(target=avvia_classifica_thread, daemon=True).start()

    # Avvia il server Flask con Waitress
    serve(app, host="0.0.0.0", port=8080)






