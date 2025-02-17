import datetime
import asyncio
import os
import logging
import threading
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from waitress import serve

# Configurazione Logging
logging.basicConfig(level=logging.INFO)

# Ottieni il TOKEN e il DATABASE_URL dalle variabili d'ambiente
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = "https://telegram-bot-production-2303.up.railway.app"

# Variabili globali
ultimo_chat_id = None  
ultima_data_invio = None  

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

### --- CONNESSIONE AL DATABASE --- ###
def connessione_db():
    """Crea una connessione al database PostgreSQL."""
    return psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=DictCursor)

def crea_tabella_classifica():
    """Crea la tabella della classifica se non esiste."""
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS classifica (
                    id SERIAL PRIMARY KEY,
                    utente TEXT UNIQUE NOT NULL,
                    punti INTEGER NOT NULL DEFAULT 0
                );
            """)
            conn.commit()
    logging.info("📌 Tabella classifica pronta!")

### --- GESTIONE CLASSIFICA --- ###
def salva_classifica(utente, punti):
    """Aggiorna la classifica nel database PostgreSQL."""
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO classifica (utente, punti)
                VALUES (%s, %s)
                ON CONFLICT (utente) DO UPDATE SET punti = classifica.punti + EXCLUDED.punti;
            """, (utente, punti))
            conn.commit()
    logging.info(f"✅ Classifica aggiornata: {utente} ha ora {punti} punti")

def carica_classifica():
    """Carica la classifica dal database."""
    global classifica
    classifica = {}
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT utente, punti FROM classifica ORDER BY punti DESC;")
            for row in cur.fetchall():
                classifica[row["utente"]] = row["punti"]
    logging.info("📌 Classifica caricata dal database!")

def reset_classifica():
    """Resetta la classifica nel database."""
    with connessione_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM classifica;")
            conn.commit()
    logging.info("🔄 Classifica resettata!")

### --- FUNZIONI DEL BOT --- ###
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messaggio di benvenuto"""
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")

async def classifica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la classifica attuale."""
    global ultimo_chat_id
    ultimo_chat_id = update.message.chat_id  

    carica_classifica()  # Carica sempre l'ultima classifica aggiornata

    if not classifica:
        await update.message.reply_text("🏆 La classifica è vuota!")
        return

    classifica_ordinata = sorted(classifica.items(), key=lambda x: x[1], reverse=True)
    messaggio = "🏆 Classifica attuale:\n" + "\n".join(f"{u}: {p} punti" for u, p in classifica_ordinata)
    await update.message.reply_text(messaggio)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resetta la classifica nel database"""
    reset_classifica()
    await update.message.reply_text("🔄 Classifica e limitazioni resettate con successo!")

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiunge punti agli utenti in base agli hashtag nei messaggi."""
    messaggio = update.message.text or update.message.caption
    if not messaggio:
        return  

    utente = update.message.from_user.username or update.message.from_user.first_name
    if not utente:
        return  

    oggi = datetime.date.today()
    punti_totali = 0

    for parola, punti in parole_punteggio.items():
        if parola in messaggio:
            punti_totali += punti

    if punti_totali > 0:
        salva_classifica(utente, punti_totali)  # Salva direttamente nel DB
        await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! 🎉")

### --- WEBHOOK TELEGRAM --- ###
@app.route("/webhook", methods=["POST"])
def webhook():
    """Gestisce le richieste Webhook di Telegram"""
    try:
        data = request.get_json()
        if not data:
            return "Bad Request", 400

        update = Update.de_json(data, application.bot)
        logging.info(f"📩 Ricevuto update: {update}")

        # Esegui il processamento dell'update in modo asincrono
        asyncio.run(application.process_update(update))

        return "OK", 200
    except Exception as e:
        logging.error(f"❌ Errore Webhook: {e}")
        return "Internal Server Error", 500


### --- AVVIO DEL BOT --- ###
if __name__ == "__main__":
    logging.info("⚡ Il bot è avviato!")
    
    # Crea la tabella se non esiste
    crea_tabella_classifica()

    # Aggiunta comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("classifica", classifica_bot))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestisci_messaggi))

    # Avvia il server Flask con Waitress
    serve(app, host="0.0.0.0", port=8080)
