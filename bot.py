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

    girilen = context.args[0].upper().strip()
    sembol = girilen

    # Kolay kullanım kısayolları
    if girilen in ["ALTIN", "GOLD"]:
        sembol = "GC=F"
    elif girilen in ["DOLAR", "USD"]:
        sembol = "USDTRY=X"
    elif girilen in ["EURO", "EUR"]:
        sembol = "EURTRY=X"
    elif girilen in ["GUMUS", "SILVER"]:
        sembol = "SI=F"
    # Sadece BIST gibi görünen kısa sembollere .IS ekle
    # ABD hisseleri (AAPL, TSLA, MSFT vb.) ve zaten nokta içerenler hariç
    elif (len(girilen) <= 5 
          and not any(x in girilen for x in [".", "=", "-"])
          and girilen not in ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "NFLX"]):
        sembol = f"{girilen}.IS"

    try:
        ticker = yf.Ticker(sembol)
        hist = ticker.history(period="5d")

        if hist.empty:
            await update.message.reply_text(
                f"❌ {sembol} için veri bulunamadı.\n"
                "Sembolü kontrol et."
            )
            return

        # NaN kontrolü
        son_kapanis = hist["Close"].iloc[-1]
        if pd.isna(son_kapanis):
            await update.message.reply_text(
                f"❌ {sembol} için güncel fiyat alınamadı.\n"
                "Piyasa kapalı olabilir veya veri geçici olarak gelmiyor."
            )
            return

        fiyat = float(son_kapanis)

        # Günlük değişim
        degisim_yazi = ""
        if len(hist) >= 2:
            onceki = hist["Close"].iloc[-2]
            if not pd.isna(onceki) and onceki != 0:
                degisim = ((fiyat - float(onceki)) / float(onceki)) * 100
                isaret = "📈" if degisim >= 0 else "📉"
                degisim_yazi = f"\n{isaret} Günlük: %{degisim:.2f}"

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
