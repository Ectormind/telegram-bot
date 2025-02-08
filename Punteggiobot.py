from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import json

TOKEN = "7996696893:AAHXsH0ZVisRxclXxSVbmlR8FdUaprnwnRA"


punti = {}
parole_punti = {
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
	"#fotofinale": 10
}

def salva_punti():
    with open("punti.json", "w") as f:
        json.dump(punti, f)

def carica_punti():
    global punti
    try:
        with open("punti.json", "r") as f:
            punti = json.load(f)
    except FileNotFoundError:
        punti = {}

# 🔹 AGGIORNATO: Aggiunto 'async'
async def gestisci_messaggio(update: Update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    testo = update.message.text.lower()
    punti_assegnati = 0  # 🔹 Tiene traccia dei punti guadagnati con il messaggio

    if user_id not in punti:
        punti[user_id] = {"username": username, "score": 0}

    # 🔹 Controlla se il messaggio contiene parole chiave
    for parola, valore in parole_punti.items():
        if parola in testo:
            punti[user_id]["score"] += valore
            punti_assegnati += valore  # 🔹 Aggiunge i punti ottenuti in questo messaggio

    salva_punti()

    # 🔹 Se il messaggio ha guadagnato punti, invia una risposta
    if punti_assegnati > 0:
        await update.message.reply_text(
            f"🎉 {username}, hai guadagnato {punti_assegnati} punti!\n"
            f"🔢 Totale: {punti[user_id]['score']} punti."
        )

# 🔹 AGGIORNATO: Aggiunto 'async'
async def mostra_classifica(update: Update, context):
    # Ordina la classifica per punteggio decrescente
    classifica = sorted(punti.values(), key=lambda x: x["score"], reverse=True)
    
    # Costruisce il testo della classifica
    testo = "🏆 *Classifica Punti* 🏆\n\n"
    for i, data in enumerate(classifica):
        testo += f"{i+1}. {data['username']} - {data['score']} punti\n"

    await update.message.reply_text(testo, parse_mode="Markdown")

def main():
    carica_punti()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gestisci_messaggio))
    app.add_handler(CommandHandler("classifica", mostra_classifica))

    app.run_polling()

if __name__ == "__main__":
    main()
