import os
import yfinance as yf
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
        "Kullanılabilir komutlar:\n"
        "/fiyat THYAO\n"
        "/fiyat AAPL\n"
        "/fiyat altın\n"
        "/fiyat dolar\n"
        "/test\n"
        "/anka\n"
        "/hakkinda"
    )
    await update.message.reply_text(mesaj)


async def anka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "🦅 ANKA YATIRIM ANALİZ\n\n"
        "Ana menü\n\n"
        "/fiyat [sembol] - Fiyat sorgula\n"
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
            "Lütfen sembol gir.\n\n"
            "Örnekler:\n"
            "/fiyat THYAO\n"
            "/fiyat AAPL\n"
            "/fiyat altın\n"
            "/fiyat dolar"
        )
        return

    sembol = context.args[0].upper().strip()

    # Kolay kullanım kısayolları
    if sembol in ["ALTIN", "GOLD"]:
        sembol = "GC=F"
    elif sembol in ["DOLAR", "USD"]:
        sembol = "USDTRY=X"
    elif sembol in ["EURO", "EUR"]:
        sembol = "EURTRY=X"
    elif sembol in ["GUMUS", "SILVER"]:
        sembol = "SI=F"
    # BIST hisseleri için .IS ekle
    elif len(sembol) <= 5 and not any(x in sembol for x in [".", "=", "-"]):
        sembol = f"{sembol}.IS"

    try:
        ticker = yf.Ticker(sembol)
        hist = ticker.history(period="5d")

        if hist.empty:
            await update.message.reply_text(
                f"❌ {sembol} için veri bulunamadı.\n"
                "Sembolü kontrol et."
            )
            return

        fiyat = float(hist["Close"].iloc[-1])

        # Günlük değişim
        if len(hist) >= 2:
            onceki = float(hist["Close"].iloc[-2])
            degisim = ((fiyat - onceki) / onceki) * 100
            isaret = "📈" if degisim >= 0 else "📉"
            degisim_yazi = f"\n{isaret} Günlük: %{degisim:.2f}"
        else:
            degisim_yazi = ""

        mesaj = (
            f"🦅 ANKA YATIRIM ANALİZ\n\n"
            f"{sembol}\n"
            f"💰 Fiyat: {fiyat:,.2f}\n"
            f"{degisim_yazi}"
        )
        await update.message.reply_text(mesaj)

    except Exception as e:
        await update.message.reply_text(
            f"❌ Hata oluştu.\n"
            f"Sembol: {sembol}\n"
            f"Detay: {str(e)[:300]}"
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
