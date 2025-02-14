from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime
import os
import logging
import asyncio
import threading
from waitress import serve

# Configurazione Logging
logging.basicConfig(level=logging.INFO)

# Token del bot (da Railway)
TOKEN = os.getenv("TOKEN")

# Webhook URL - sostituiscilo con il dominio Railway generato
WEBHOOK_URL = "https://telegram-bot-production-2303.up.railway.app"

# Dizionario per memorizzare la classifica degli utenti
classifica = {}

# Dizionario per memorizzare gli hashtag già usati dagli utenti oggi
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

# Inizializza Flask
app = Flask(__name__)

# Inizializza il bot
application = Application.builder().token(TOKEN).build()

### --- FUNZIONI DEL BOT --- ###

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messaggio di benvenuto"""
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")

async def classifica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la classifica attuale"""
    if not classifica:
        await update.message.reply_text("🏆 La classifica è vuota!")
        return

    classifica_ordinata = sorted(classifica.items(), key=lambda x: x[1], reverse=True)
    
    messaggio = "🏆 Classifica attuale:\n"
    for utente, punti in classifica_ordinata:
        messaggio += f"{utente}: {punti} punti\n"

    await update.message.reply_text(messaggio)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resetta la classifica e il registro degli hashtag usati"""
    classifica.clear()
    hashtag_usati.clear()
    await update.message.reply_text("🔄 Classifica e limitazioni resettate con successo! Tutti possono ripartire da zero.")

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiunge punti agli utenti in base agli hashtag nei messaggi o nelle didascalie delle foto"""
    messaggio = update.message.text or update.message.caption  # ✅ Supporta sia testo che didascalie
    if not messaggio:
        return  # Se il messaggio non ha né testo né didascalia, ignoralo

    utente = update.message.from_user.username or update.message.from_user.first_name
    if not utente:
        return  # Se l'utente non ha un username, ignora

    oggi = datetime.date.today()
    if utente not in hashtag_usati:
        hashtag_usati[utente] = {}

    punti_totali = 0
    parole_trovate = []

    # Controlla se il messaggio contiene parole chiave
    for parola, punti in parole_punteggio.items():
        if parola in messaggio:
            parole_trovate.append(parola)
            if parola not in hashtag_usati[utente] or hashtag_usati[utente][parola] != oggi:
                punti_totali += punti
                hashtag_usati[utente][parola] = oggi  

    if punti_totali > 0:
        classifica[utente] = classifica.get(utente, 0) + punti_totali
        await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! 🎉 Ora ha {classifica[utente]} punti totali.")
    elif not parole_trovate:
        return  # 🔴 Non risponde se nessuna parola chiave è trovata
    else:
        await update.message.reply_text(f"{utente}, hai già usato questi hashtag oggi. ⏳ Prova domani!")

# Aggiunta comandi al bot
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("classifica", classifica_bot))
application.add_handler(CommandHandler("reset", reset))
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestisci_messaggi))

### --- WEBHOOK CON FLASK (Corretto `process_update()`) --- ###

async def process_update_async(update):
    """Inizializza il bot e processa gli aggiornamenti"""
    await application.initialize()
    await application.process_update(update)

@app.route("/", methods=["POST"])
def webhook():
    """Gestisce le richieste Webhook di Telegram"""
    update = Update.de_json(request.get_json(), application.bot)
    logging.info(f"Ricevuto update: {update}")
    
    # Esegui la funzione async in un nuovo event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(process_update_async(update))
    
    return "OK", 200

### --- AVVIO DEL SERVER CON KEEP-ALIVE --- ###
def keep_alive():
    """Ping ogni 5 minuti per mantenere attivo Railway"""
    import time
    import requests
    while True:
        time.sleep(300)
        try:
            requests.get(WEBHOOK_URL)
            logging.info("🔄 Ping inviato per mantenere Railway attivo")
        except Exception as e:
            logging.error(f"⚠️ Errore nel ping: {e}")

if __name__ == "__main__":
    logging.info("⚡ Il bot è avviato e in ascolto su Railway...")
    
    # Avvia il ping per evitare che Railway chiuda il bot
    threading.Thread(target=keep_alive, daemon=True).start()

    # Avvia il server Flask con Waitress
    serve(app, host="0.0.0.0", port=8080)

