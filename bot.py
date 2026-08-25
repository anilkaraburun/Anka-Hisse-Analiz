import os
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
COLLECT_API_KEY = os.getenv("COLLECT_API_KEY")

HEADERS = {
    "authorization": f"apikey {COLLECT_API_KEY}",
    "content-type": "application/json"
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "🦅 ANKA YATIRIM ANALİZ\n\n"
        "Finansal piyasa analiz botuna hoş geldin.\n\n"
        "Kullanılabilir komutlar:\n"
        "/fiyat dolar\n"
        "/fiyat euro\n"
        "/fiyat altın\n"
        "/fiyat gümüş\n"
        "/test\n"
        "/anka\n"
        "/hakkinda"
    )
    await update.message.reply_text(mesaj)


async def anka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "🦅 ANKA YATIRIM ANALİZ\n\n"
        "Ana menü\n\n"
        "/fiyat [dolar/euro/altın/gümüş] - Fiyat sorgula\n"
        "/test - Bağlantı testi\n"
        "/hakkinda - Proje hakkında"
    )
    await update.message.reply_text(mesaj)


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ ANKA YATIRIM ANALİZ çalışıyor!\n\n"
        "Telegram bağlantısı başarılı."
    )


async def hakkinda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "🦅 ANKA YATIRIM ANALİZ\n\n"
        "Amaç:\n"
        "Finansal piyasalardaki varlıkları "
        "veriye dayalı olarak analiz etmek.\n\n"
        "Sistem aşamalı olarak geliştirilecektir."
    )
    await update.message.reply_text(mesaj)


async def fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Lütfen ne istediğini yaz.\n\n"
            "Örnekler:\n"
            "/fiyat dolar\n"
            "/fiyat euro\n"
            "/fiyat altın\n"
            "/fiyat gümüş"
        )
        return

    if not COLLECT_API_KEY:
        await update.message.reply_text("❌ COLLECT_API_KEY bulunamadı!")
        return

    istek = context.args[0].lower().strip()

    try:
        if istek in ["dolar", "usd"]:
            url = "https://api.collectapi.com/economy/singleCurrency?int=1&tag=USD"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()

            if data.get("success"):
                result = data["result"][0] if isinstance(data["result"], list) else data["result"]
                alis = result.get("buying") or result.get("alis")
                satis = result.get("selling") or result.get("satis")
                mesaj = (
                    f"🦅 ANKA YATIRIM ANALİZ\n\n"
                    f"💵 Dolar (USD/TRY)\n"
                    f"Alış: {alis}\n"
                    f"Satış: {satis}"
                )
            else:
                mesaj = "❌ Dolar verisi alınamadı."

        elif istek in ["euro", "eur"]:
            url = "https://api.collectapi.com/economy/singleCurrency?int=1&tag=EUR"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()

            if data.get("success"):
                result = data["result"][0] if isinstance(data["result"], list) else data["result"]
                alis = result.get("buying") or result.get("alis")
                satis = result.get("selling") or result.get("satis")
                mesaj = (
                    f"🦅 ANKA YATIRIM ANALİZ\n\n"
                    f"💶 Euro (EUR/TRY)\n"
                    f"Alış: {alis}\n"
                    f"Satış: {satis}"
                )
            else:
                mesaj = "❌ Euro verisi alınamadı."

        elif istek in ["altın", "altin", "gold"]:
            url = "https://api.collectapi.com/economy/goldPrice"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()

            if data.get("success"):
                # Gram altın genellikle listede "Gram Altın" olarak gelir
                gram = None
                for item in data["result"]:
                    name = item.get("name", "").lower()
                    if "gram" in name and "altın" in name:
                        gram = item
                        break
                if gram:
                    mesaj = (
                        f"🦅 ANKA YATIRIM ANALİZ\n\n"
                        f"🥇 Gram Altın\n"
                        f"Alış: {gram.get('buying') or gram.get('alis')}\n"
                        f"Satış: {gram.get('selling') or gram.get('satis')}"
                    )
                else:
                    mesaj = "❌ Gram altın verisi bulunamadı."
            else:
                mesaj = "❌ Altın verisi alınamadı."

        elif istek in ["gümüş", "gumus", "silver"]:
            url = "https://api.collectapi.com/economy/goldPrice"
            r = requests.get(url, headers=HEADERS, timeout=10)
            data = r.json()

            if data.get("success"):
                gumus = None
                for item in data["result"]:
                    name = item.get("name", "").lower()
                    if "gümüş" in name or "gumus" in name:
                        gumus = item
                        break
                if gumus:
                    mesaj = (
                        f"🦅 ANKA YATIRIM ANALİZ\n\n"
                        f"🥈 Gümüş\n"
                        f"Alış: {gumus.get('buying') or gumus.get('alis')}\n"
                        f"Satış: {gumus.get('selling') or gumus.get('satis')}"
                    )
                else:
                    mesaj = "❌ Gümüş verisi bulunamadı."
            else:
                mesaj = "❌ Gümüş verisi alınamadı."

        else:
            mesaj = (
                "Şu an sadece şunları destekliyorum:\n"
                "/fiyat dolar\n"
                "/fiyat euro\n"
                "/fiyat altın\n"
                "/fiyat gümüş\n\n"
                "BIST hisseleri yakında eklenecek."
            )

        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(
            f"❌ Hata oluştu.\n"
            f"Detay: {str(e)[:250]}"
        )


def main():
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN bulunamadı!")
        return

    app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("anka", anka))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("hakkinda", hakkinda))
    app.add_handler(CommandHandler("fiyat", fiyat))

    print("🦅 Anka Yatırım Analiz başlatıldı.")
    app.run_polling()


if __name__ == "__main__":
    main()
