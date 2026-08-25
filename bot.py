import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mesaj = (
        "🦅 ANKA YATIRIM ANALİZ\n\n"
        "Finansal piyasa analiz botuna hoş geldin.\n\n"
        "📊 Yakında takip edilecek piyasalar:\n"
        "🇹🇷 BIST\n"
        "🇺🇸 ABD Hisseleri\n"
        "🥇 Altın\n"
        "🥈 Gümüş\n"
        "🟠 Bakır\n"
        "💵 Döviz\n"
        "₿ Kripto\n\n"
        "🚀 Sistem hazırlanıyor..."
    )

    await update.message.reply_text(mesaj)


async def anka(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mesaj = (
        "🦅 ANKA YATIRIM ANALİZ\n\n"
        "Ana menü\n\n"
        "/anka - Ana menü\n"
        "/test - Bot bağlantı testi\n"
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

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("anka", anka)
    )

    app.add_handler(
        CommandHandler("test", test)
    )

    app.add_handler(
        CommandHandler("hakkinda", hakkinda)
    )

    print("🦅 Anka Yatırım Analiz başlatıldı.")

    app.run_polling()


if __name__ == "__main__":
    main()
