import datetime
import asyncio
import os
import logging
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from waitress import serve
import httpx
import time
import threading

#  Configurazione Logging
logging.basicConfig(level=logging.INFO)

#  Lettura delle variabili d'ambiente
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CHAT_ID = os.getenv("CHAT_ID")  # ID della chat dove inviare la classifica giornaliera

#  Inizializza Flask e il bot Telegram
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

#  Dizionario con le parole e i relativi punteggi
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

#  Connessione al database PostgreSQL con retry
def connessione_db():
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=DictCursor)
        except psycopg2.OperationalError as e:
            logging.error(f"❌ Errore di connessione al database (tentativo {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

#  Creazione della tabella classifica
def crea_tabella_classifica():
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS classifica (
                    utente TEXT PRIMARY KEY,
                    punti INTEGER NOT NULL
                );
            """)
            conn.commit()
            logging.info(" Tabella classifica pronta!")

#  Caricamento classifica dal database (eseguito in un thread separato)
def carica_classifica_thread():
    try:
        with connessione_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT utente, punti FROM classifica ORDER BY punti DESC;")
                return dict(cur.fetchall())
    except Exception as e:
        logging.error(f"❌ Errore durante il caricamento della classifica: {e}")
        return {}

#  Aggiornamento punteggio nel database
def aggiorna_punteggio(utente, punti):
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO classifica (utente, punti) 
                VALUES (%s, %s)
                ON CONFLICT (utente) DO UPDATE 
                SET punti = classifica.punti + EXCLUDED.punti;
            """, (utente, punti))
            conn.commit()

#  Reset della classifica
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM classifica;")
            conn.commit()
    await update.message.reply_text(" Classifica resettata con successo!")

#  Messaggio di benvenuto
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")

#  Comando per visualizzare la classifica
async def classifica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Esegui carica_classifica_thread in un thread separato
        loop = asyncio.get_running_loop()
        classifica = await loop.run_in_executor(None, carica_classifica_thread)

        if not classifica:
            await update.message.reply_text(" La classifica è vuota!")
            return
        messaggio = " Classifica attuale:\n" + "\n".join(f"{u}: {p} punti" for u, p in classifica.items())
        await update.message.reply_text(messaggio)
    except Exception as e:
        logging.error(f"❌ Errore durante l'esecuzione di /classifica: {e}")
        await update.message.reply_text("❌ Si è verificato un errore durante la visualizzazione della classifica.")

#  Gestione dei messaggi per assegnare punti
async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi e assegna punti in base agli hashtag"""
    messaggio = update.message.text or update.message.caption
    if not messaggio:
        return
    utente = update.message.from_user.username or update.message.from_user.first_name
    if not utente:
        return
    punti_totali = sum(punti for parola, punti in parole_punteggio.items() if parola in messaggio)
    if punti_totali > 0:
        aggiorna_punteggio(utente, punti_totali)
        try:
            await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! ")
        except Exception as e:
            logging.error(f"❌ Errore nell'invio del messaggio: {e}")

#  Webhook Telegram (CORRETTO)
@app.route("/webhook", methods=["POST"])
async def webhook():
    """Gestisce le richieste Webhook di Telegram."""
    try:
        data = request.get_json(silent=True)
        if not data:
            logging.error("❌ Nessun dato JSON valido ricevuto!")
            return jsonify({"error": "Bad Request"}), 400
        update = Update.de_json(data, application.bot)
        logging.info(f" Ricevuto update: {update}")
        await application.process_update(update)
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        logging.error(f"❌ Errore Webhook: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

#  Invio automatico della classifica a mezzanotte
async def invia_classifica_giornaliera():
    """Invia automaticamente la classifica alle 00:00 una sola volta"""
    while True:
        ora_corrente = datetime.datetime.now()
        if ora_corrente.hour == 0 and ora_corrente.minute < 5:
            try:
                loop = asyncio.get_running_loop()
                classifica = await loop.run_in_executor(None, carica_classifica_thread)
                if classifica:
                    messaggio = " Classifica giornaliera \n" + "\n".join(f"{u}: {p} punti" for u, p in classifica.items())
                    await application.bot.send_message(chat_id=CHAT_ID, text=messaggio)
                    logging.info("✅ Classifica inviata con successo!")
            except Exception as e:
                logging.error(f"❌ Errore nell'invio della classifica: {e}")
            await asyncio.sleep(300)
        else:
            await asyncio.sleep(30)

#  Avvio del bot
async def main():
    logging.info("⚡ Il bot è avviato!")
    crea_tabella_classifica()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("classifica", classifica_bot))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestisci_messaggi))





