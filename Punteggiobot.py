import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Nome del file dei punteggi
PUNTEGGI_FILE = "punti.json"

# Funzione per caricare i punteggi
def carica_punteggi():
    try:
        with open(PUNTEGGI_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Se il file non esiste o è corrotto, inizializza con un dizionario vuoto

# Carica i punteggi all'avvio
punteggi = carica_punteggi()

# Funzione per gestire i messaggi
async def gestione_messaggio(update: Update, context: CallbackContext):  # Aggiunto async
    user = update.message.from_user
    user_id = str(user.id)
    user_name = user.first_name

    # Parole chiave e relativi punteggi
    parole_punteggio = {
        "#bilancia": 5,
        # ... (aggiungi qui le altre parole chiave)
    }
    punti_da_aggiungere = 0

    # Controlla se il messaggio contiene parole chiave (case-insensitive)
    for parola, punti in parole_punteggio.items():
        if parola in update.message.text.lower():
            punti_da_aggiungere += punti

    if punti_da_aggiungere > 0:
        # Inizializza 'nome' e 'punti' se l'utente è nuovo
        if user_id not in punteggi:
            punteggi[user_id] = {"nome": user_name, "punti": 0}  # Inizializzazione COMPLETA

        punteggi[user_id]["punti"] += punti_da_aggiungere

        # Salva i punteggi
        try:
            with open(PUNTEGGI_FILE, "w") as file:
                json.dump(punteggi, file, indent=4)
        except Exception as e:
            print(f"Errore nel salvataggio dei punteggi: {e}")  # Stampa l'errore nei log

        # Risponde con il punteggio aggiornato (await aggiunto)
        await update.message.reply_text(f"⭐ {user.mention_html()}, hai guadagnato {punti_da_aggiungere} punti! Totale: {punteggi[user_id]['punti']} punti.", parse_mode="HTML")

# Funzione per mostrare la classifica
async def classifica(update: Update, context: CallbackContext):  # Aggiunto async
    if not punteggi:
        await update.message.reply_text(" Nessun punteggio registrato ancora!")  # await aggiunto
        return

    classifica_ordinata = sorted(punteggi.items(), key=lambda item: item[1].get("punti", 0), reverse=True)

    messaggio = " *Classifica Punti* \n\n"

    for i, (user_id, dati) in enumerate(classifica_ordinata, 1):
        messaggio += f"{i}. {dati.get('nome', 'Sconosciuto')} - {dati.get('punti', 0)} punti\n"

    await update.message.reply_text(messaggio, parse_mode="Markdown")  # await aggiunto

# Funzione per resettare la classifica (con conferma)
async def reset_classifica(update: Update, context: CallbackContext):  # Aggiunto async
    await update.message.reply_text("Sei sicuro di voler resettare la classifica? /conferma_reset per confermare.")  # await aggiunto

# Funzione per confermare il reset
async def conferma_reset(update: Update, context: CallbackContext):  # Aggiunto async
    global punteggi
    punteggi = {}  # Svuota il dizionario
    try:
        with open(PUNTEGGI_FILE, "w") as file:
            json.dump(punteggi, file, indent=4)  # Salva il reset
    except Exception as e:
        print(f"Errore nel reset della classifica: {e}")  # Stampa l'errore nei log

    await update.message.reply_text(" Classifica resettata con successo!")  # await aggiunto

# Funzione principale (avvia il bot)
async def main():  # Aggiunto async
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # Ottieni il token da una variabile d'ambiente (Railway)
    if not TOKEN:
        print("Errore: variabile d'ambiente TELEGRAM_BOT_TOKEN non impostata.")
        return  # Esce se il token non è presente

    application = Application.builder().token(TOKEN).build()

    # Comandi del bot
    application.add_handler(CommandHandler("classifica", classifica))
    application.add_handler(CommandHandler("reset", reset_classifica))
    application.add_handler(CommandHandler("conferma_reset", conferma_reset))  # Handler per la conferma

    # Gestione messaggi
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gestione_messaggio))

    # Avvia il bot (con gestione errori)
    try:
        application.run_polling()  # Chiamata diretta, *senza* await
    except Exception as e:
        print(f"Errore durante l'avvio del bot: {e}")  # Stampa l'errore nei log

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # Necessario per avviare la funzione asincrona main()