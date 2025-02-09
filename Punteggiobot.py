from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime

# Token del bot
TOKEN = "7996696893:AAHXsH0ZVisRxclXxSVbmlR8FdUaprnwnRA"

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

### --- FUNZIONI DEL BOT --- ###

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Messaggio di benvenuto"""
    await update.message.reply_text("Ciao! Invia un messaggio con un hashtag per accumulare punti!")


async def classifica_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra la classifica attuale"""
    if not classifica:
        await update.message.reply_text("🏆 La classifica è vuota!")
        return

    messaggio = "🏆 Classifica attuale:\n"
    for utente, punti in sorted(classifica.items(), key=lambda x: x[1], reverse=True):
        messaggio += f"{utente}: {punti} punti\n"

    await update.message.reply_text(messaggio)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resetta la classifica e il registro degli hashtag usati"""
    classifica.clear()
    hashtag_usati.clear()  # Ora cancella anche il registro degli hashtag usati
    await update.message.reply_text("🔄 Classifica e limitazioni resettate con successo! Tutti possono ripartire da zero.")


async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aggiunge punti agli utenti in base agli hashtag nei messaggi, evitando ripetizioni giornaliere"""
    messaggio = update.message.text
    utente = update.message.from_user.username or update.message.from_user.first_name

    if not utente:
        return  # Se l'utente non ha un username, ignora

    oggi = datetime.date.today()
    if utente not in hashtag_usati:
        hashtag_usati[utente] = {}

    punti_totali = 0
    for parola, punti in parole_punteggio.items():
        if parola in messaggio:
            # Controlla se l'utente ha già guadagnato punti per questa parola oggi
            if parola not in hashtag_usati[utente] or hashtag_usati[utente][parola] != oggi:
                punti_totali += punti
                hashtag_usati[utente][parola] = oggi  # Segna la parola come usata oggi

    if punti_totali > 0:
        classifica[utente] = classifica.get(utente, 0) + punti_totali
        await update.message.reply_text(f"{utente} ha guadagnato {punti_totali} punti! 🎉")
    else:
        await update.message.reply_text(f"{utente}, hai già usato questi hashtag oggi. ⏳ Prova domani!")


### --- MAIN --- ###
def main():
    """Avvia il bot"""
    application = Application.builder().token(TOKEN).build()

    # Aggiungi i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("classifica", classifica_bot))
    application.add_handler(CommandHandler("reset", reset))

    # Aggiungi un handler per i messaggi normali
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gestisci_messaggi))

    # Avvia il bot
    application.run_polling()

if __name__ == "__main__":
    main()
