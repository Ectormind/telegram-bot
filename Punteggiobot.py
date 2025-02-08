import json
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext

# Nome del file dei punteggi
PUNTEGGI_FILE = "punti.json"

# Funzione per caricare i punteggi
def carica_punteggi():
    try:
        with open(PUNTEGGI_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Se il file non esiste o è corrotto, inizializza con un dizionario vuoto

# **Reset automatico all'avvio del bot**
punteggi = {}

# Salva subito il reset nel file
with open(PUNTEGGI_FILE, "w") as file:
    json.dump(punteggi, file, indent=4)

# **Funzione per gestire i messaggi**
def gestione_messaggio(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = str(user.id)
    user_name = user.first_name

    # Aggiungere punti solo se il messaggio contiene parole specifiche
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
	"#spuntino1 altri": 8, 
	"#spuntino2 altri": 8,
	"#integrazione1": 8, 
	"#integrazione2": 8,
	"#workout": 10,
	"#pastosostitutivo": 10,
	"#sensazioni": 10, 
	"#kitnewenergy": 10,
	"#fotoiniziale": 10,
	"#fotofinale": 10}
    punti_da_aggiungere = 0

    for parola, punti in parole_punteggio.items():
        if parola in update.message.text.lower():
            punti_da_aggiungere += punti

    if punti_da_aggiungere > 0:
        # Aggiorna il punteggio dell'utente
        if user_id in punteggi:
            punteggi[user_id]["punti"] += punti_da_aggiungere
        else:
            punteggi[user_id] = {"nome": user_name, "punti": punti_da_aggiungere}

        # Salva i punteggi
        with open(PUNTEGGI_FILE, "w") as file:
            json.dump(punteggi, file, indent=4)

        # Risponde con il punteggio aggiornato
        update.message.reply_text(f"⭐ {user_name}, hai guadagnato {punti_da_aggiungere} punti! Totale: {punteggi[user_id]['punti']} punti.")

# **Funzione per mostrare la classifica**
def classifica(update: Update, context: CallbackContext):
    if not punteggi:
        update.message.reply_text("🏆 Nessun punteggio registrato ancora!")
        return

    classifica_ordinata = sorted(punteggi.items(), key=lambda x: x[1]["punti"], reverse=True)
    messaggio = "🏆 *Classifica Punti* 🏆\n\n"

    for i, (user_id, dati) in enumerate(classifica_ordinata, 1):
        messaggio += f"{i}. {dati['nome']} - {dati['punti']} punti\n"

    update.message.reply_text(messaggio, parse_mode="Markdown")

# **Funzione per resettare la classifica con il comando /reset**
def reset_classifica(update: Update, context: CallbackContext):
    global punteggi
    punteggi = {}  # Svuota il dizionario
    with open(PUNTEGGI_FILE, "w") as file:
        json.dump(punteggi, file, indent=4)  # Salva il reset
    update.message.reply_text("🔄 Classifica resettata con successo!")

# **Setup del bot**
def main():
    TOKEN = "7996696893:AAHXsH0ZVisRxclXxSVbmlR8FdUaprnwnRA"
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Comandi del bot
    dispatcher.add_handler(CommandHandler("classifica", classifica))
    dispatcher.add_handler(CommandHandler("reset", reset_classifica))

    # Gestione messaggi
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, gestione_messaggio))

    # Avvia il bot
    updater.start_polling()
    updater.idle()

# **Eseguire il bot**
if __name__ == "__main__":
    main()
