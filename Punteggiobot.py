from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime
import os
import logging
import asyncio
import json
from waitress import serve

# Configurazione Logging
logging.basicConfig(level=logging.INFO)

# Token del bot (da Railway)
TOKEN = os.getenv("TOKEN")

# Webhook URL - Sostituiscilo con il dominio Railway generato
WEBHOOK_URL = "https://telegram-bot-production-2303.up.railway.app"

# Variabili globali
ultimo_chat_id = None  # Memorizza l'ultima chat che ha richiesto la classifica
ultima_data_invio = None  # Memorizza l'ultima data in cui è stata inviata la classifica

# Dizionario per memorizzare la classifica degli utenti
classifica = {}

# Dizionario per memorizzare gli hashtag già usati dagli utenti oggi
hashtag_usati = {}

# Dizionario con le parole e i relativi punteggi
parole_punteggio = {
    "#bilancia": 5, "#colazioneequilibrata": 5, "#collagene": 5, "#bombetta": 5,
    "#ricostruttore": 5, "#idratazionespecifica": 5, "#phytocomplete": 5, "#pranzobilanciato": 8,
    "#cenabilanciata": 8, "#spuntino1": 8, "#spuntino2": 8, "#integrazione1": 8,
    "#integrazione2": 8, "#workout": 10, "#pastosostitutivo": 10, "#sensazioni": 10,
    "#kitnewenergy": 10, "#fotoiniziale": 10, "#fotofinale": 10
}

# Inizializza Flask
app = Flask(__name__)

# Inizializza il bot
application = Application.builder().token(TOKEN).build()

### --- FUNZIONI PER GESTIRE IL SALVATAGGIO DELLA CLASSIFICA --- ###

def salva_classifica():
    """Salva la classifica in un file JSON."""
    with open("classifica.json", "w") as f:
        json.dump(classifica, f)

def carica_classifica():
    """Carica la classifica da un file JSON, se esiste."""
    global classifica
    try:
        with open("classifica.json", "r") as f:
            classifica = json.load(f)
            logging.info("✅ Classifica caricata con successo.")
    except FileNotFoundError:
        logging.info("⚠️ Nessuna classifica trovata, si parte da zero.")
        classifica = {}

### --- FUNZIONI DEL BOT --- ###

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messaggio di benvenuto"""
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")

async def classifica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la classifica attuale e salva l'ID della chat"""
    global ultimo_chat_id
    ultimo_chat_id = update.message.chat_id  # Memorizza l'ultima chat

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
    salva_classifica()  # 🔹 Cancella i dati salvati
    await update.message.reply_text("🔄 Classifica e limitazioni resettate con successo! Tutti possono ripartire da zero.")

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiunge punti agli utenti in base agli hashtag nei messaggi o nelle didascalie delle foto"""
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
        salva_classifica()  # 🔹 Salva la classifica aggiornata
        await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! 🎉 Ora ha {classifica[utente]} punti totali.")
    elif not parole_trovate:
        return  
    else:
        await update.message.reply_text(f"{utente}, hai già usato questi hashtag oggi. ⏳ Prova domani!")

### --- INVIO AUTOMATICO DELLA CLASSIFICA A MEZZANOTTE --- ###

async def invia_classifica_giornaliera():
    """Invia automaticamente la classifica alle 00:00, ma solo una volta al giorno"""
    global ultimo_chat_id, ultima_data_invio
    while True:
        ora_corrente = datetime.datetime.now()
        
        if ora_corrente.hour == 0 and ora_corrente.minute < 5:
            if classifica and ultimo_chat_id and (ultima_data_invio != ora_corrente.date()):
                classifica_ordinata = sorted(classifica.items(), key=lambda x: x[1], reverse=True)
                messaggio = "🏆 Classifica giornaliera 🏆\n"
                for utente, punti in classifica_ordinata:
                    messaggio += f"{utente}: {punti} punti\n"

                try:
                    await application.bot.send_message(chat_id=ultimo_chat_id, text=messaggio)
                    logging.info(f"✅ Classifica inviata alla chat {ultimo_chat_id}")
                    ultima_data_invio = ora_corrente.date()
                except Exception as e:
                    logging.error(f"❌ Errore nell'invio della classifica: {e}")

            await asyncio.sleep(300)  
        else:
            await asyncio.sleep(30)  

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Gestisce le richieste in arrivo dal Webhook di Telegram."""
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return "OK", 200

def set_webhook():
    """Imposta il Webhook di Telegram."""
    url = f"{WEBHOOK_URL}/webhook"
    application.bot.set_webhook(url)
    logging.info(f"✅ Webhook impostato su {url}")

if __name__ == "__main__":
    logging.info("⚡ Il bot è avviato e in ascolto su Railway...")

    carica_classifica()
    set_webhook()

    # Avvia il server Flask
    serve(app, host="0.0.0.0", port=8080)


