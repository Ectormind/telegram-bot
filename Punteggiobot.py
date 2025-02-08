import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Nome del file dei punteggi (meglio usare una variabile per evitare errori di battitura)
PUNTEGGI_FILE = "punti.json"



# Funzione per caricare i punteggi (con gestione errori)
def carica_punteggi():
    try:
        with open(PUNTEGGI_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Inizializza con un dizionario vuoto se il file non esiste o è corrotto

# Reset automatico all'avvio del bot (e salva subito il reset nel file)
punteggi = carica_punteggi() #carica i punteggi all'avvio del bot, se non presenti li inizializza vuoti
# punteggi = {}  # Resetta i punteggi ad ogni avvio (commenta questa riga se non vuoi resettare)
# with open(PUNTEGGI_FILE, "w") as file:
#     json.dump(punteggi, file, indent=4)

# Funzione per gestire i messaggi
def gestione_messaggio(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = str(user.id)
    user_name = user.first_name

    # Parole chiave e relativi punteggi (usare un dizionario per chiarezza)
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
        "#spuntino1altri": 8,
        "#spuntino2altri": 8,
        "#integrazione1": 8,
        "#integrazione2": 8,
        "#workout": 10,
        "#pastosostitutivo": 10,
        "#sensazioni": 10,
        "#kitnewenergy": 10,
        "#fotoiniziale": 10,
        "#fotofinale": 10
    }
    punti_da_aggiungere = 0

    # Controlla se il messaggio contiene parole chiave (case-insensitive)
    for parola, punti in parole_punteggio.items():
        if parola in update.message.text.lower():
            punti_da_aggiungere += punti

    if punti_da_aggiungere > 0:
        # Aggiorna il punteggio dell'utente (usando .get per gestire utenti nuovi)
        punteggi[user_id] = punteggi.get(user_id, {"nome": user_name, "punti": 0})
        punteggi[user_id]["punti"] += punti_da_aggiungere

        # Salva i punteggi (con gestione errori)
        try:
            with open(PUNTEGGI_FILE, "w") as file:
                json.dump(punteggi, file, indent=4)
        except Exception as e:
            print(f"Errore nel salvataggio dei punteggi: {e}")  # Stampa l'errore nei log

        # Risponde con il punteggio aggiornato (menzione utente)
        update.message.reply_text(f"⭐ {user.mention_html()}, hai guadagnato {punti_da_aggiungere} punti! Totale: {punteggi[user_id]['punti']} punti.", parse_mode="HTML")

# Funzione per mostrare la classifica
def classifica(update: Update, context: CallbackContext):
    if not punteggi:
        update.message.reply_text(" Nessun punteggio registrato ancora!")
        return

    # Ordina i punteggi per punti (con lambda function)
    classifica_ordinata = sorted(punteggi.items(), key=lambda item: item[1]["punti"], reverse=True)
    messaggio = " *Classifica Punti* \n\n"

    # Formatta il messaggio con la classifica (usando enumerate per l'indice)
    for i, (user_id, dati) in enumerate(classifica_ordinata, 1):
        messaggio += f"{i}. {dati['nome']} - {dati['punti']} punti\n"

    update.message.reply_text(messaggio, parse_mode="Markdown")

# Funzione per resettare la classifica (con conferma)
def reset_classifica(update: Update, context: CallbackContext):
    # Chiedi conferma prima di resettare
    update.message.reply_text("Sei sicuro di voler resettare la classifica? /conferma_reset per confermare.")

# Funzione per confermare il reset
def conferma_reset(update: Update, context: CallbackContext):
    global punteggi
    punteggi = {}  # Svuota il dizionario
    try:
        with open(PUNTEGGI_FILE, "w") as file:
            json.dump(punteggi, file, indent=4)  # Salva il reset
    except Exception as e:
        print(f"Errore nel reset della classifica: {e}")  # Stampa l'errore nei log

    update.message.reply_text(" Classifica resettata con successo!")

# Funzione principale (avvia il bot)
def main():
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # Ottieni il token da una variabile d'ambiente (Railway)
    if not TOKEN:
        print("Errore: variabile d'ambiente TELEGRAM_BOT_TOKEN non impostata.")
        return  # Esce se il token non è presente

    application = Application.builder().token(TOKEN).build()
    # application = Application.builder().token(TOKEN).build() #corretto

    # Comandi del bot
    application.add_handler(CommandHandler("classifica", classifica))
    application.add_handler(CommandHandler("reset", reset_classifica))
    application.add_handler(CommandHandler("conferma_reset", conferma_reset))  # Handler per la conferma

    # Gestione messaggi
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gestione_messaggio))

    # Avvia il bot (con gestione errori)
    try:
        application.run_polling()
    except Exception as e:
        print(f"Errore durante l'avvio del bot: {e}")  # Stampa l'errore nei log


# Esegui il bot solo se il file viene eseguito direttamente (non importato)
if __name__ == "__main__":
    main()