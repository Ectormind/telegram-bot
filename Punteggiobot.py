from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Token del bot
TOKEN = "IL_TUO_TOKEN"

# Dizionario per memorizzare la classifica degli utenti
classifica = {}

# Dizionario con le parole e i relativi punteggi
parole_punteggio = {
    "#bilancia": 5,
    "#salute": 3,
    "#felicità": 2
}

### --- FUNZIONI DEL BOT --- ###

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messaggio di benvenuto"""
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")

async def punteggio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la classifica attuale"""
    if not classifica:
        await update.message.reply_text("La classifica è vuota!")
        return

    messaggio = "🏆 Classifica attuale:\n"
    for utente, punti in sorted(classifica.items(), key=lambda x: x[1], reverse=True):
        messaggio += f"{utente}: {punti} punti\n"
    
    await update.message.reply_text(messaggio)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resetta la classifica"""
    classifica.clear()
    await update.message.reply_text("Classifica resettata con successo!")

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiunge punti agli utenti in base agli hashtag nei messaggi"""
    messaggio = update.message.text
    utente = update.message.from_user.username or update.message.from_user.first_name

    if not utente:
        return  # Se l'utente non ha un username, ignora

    punti_totali = 0
    for parola, punti in parole_punteggio.items():
        if parola in messaggio:
            punti_totali += punti

    if punti_totali > 0:
        classifica[utente] = classifica.get(utente, 0) + punti_totali
        await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! 🎉")

### --- MAIN --- ###
def main():
    """Avvia il bot"""
    application = Application.builder().token(TOKEN).build()

    # Aggiungi i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("punteggio", punteggio))
    application.add_handler(CommandHandler("reset", reset))

    # Aggiungi un handler per i messaggi normali
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gestisci_messaggi))

    # Avvia il bot
    application.run_polling()

if __name__ == "__main__":
    main()

