import os
import yfinance as yf

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


# =========================================================
# AYARLAR
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# =========================================================
# VARLIK KODLARI
# =========================================================

ASSETS = {

    # 🇹🇷 BIST
    "THYAO": "THYAO.IS",
    "ASELS": "ASELS.IS",
    "TUPRS": "TUPRS.IS",
    "BIMAS": "BIMAS.IS",
    "EREGL": "EREGL.IS",
    "GARAN": "GARAN.IS",
    "AKBNK": "AKBNK.IS",
    "YKBNK": "YKBNK.IS",
    "SISE": "SISE.IS",
    "KCHOL": "KCHOL.IS",

    # 🇺🇸 ABD
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    "MSFT": "MSFT",
    "AMZN": "AMZN",
    "GOOGL": "GOOGL",

    # 🥇 EMTİA
    "ALTIN": "GC=F",
    "GUMUS": "SI=F",
    "BAKIR": "HG=F",
    "PETROL": "CL=F",

    # 💵 DÖVİZ
    "USDTRY": "TRY=X",
    "EURTRY": "EURTRY=X",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",

    # ₿ KRİPTO
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
}


# =========================================================
# ANA MENÜ
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mesaj = """
🦅 ANKA YATIRIM ANALİZ

Finansal piyasaları analiz eden
yeni nesil analiz botu.

📊 Piyasalar:

🇹🇷 BIST
🇺🇸 ABD Hisseleri
🥇 Altın
🥈 Gümüş
🟠 Bakır
💵 Döviz
₿ Kripto

━━━━━━━━━━━━━━━━━━

📌 KOMUTLAR

/anka
/fiyat THYAO
/fiyat ALTIN
/fiyat USDTRY
/fiyat BTC

/test

━━━━━━━━━━━━━━━━━━

🚀 Teknik analiz sistemi
yakında eklenecek.
"""

    await update.message.reply_text(mesaj)


# =========================================================
# ANKA MENÜ
# =========================================================

async def anka(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mesaj = """
🦅 ANKA YATIRIM ANALİZ

📊 Fiyat sorgulama:

/fiyat THYAO
/fiyat ASELS
/fiyat ALTIN
/fiyat GUMUS
/fiyat USDTRY
/fiyat EURTRY
/fiyat BTC

━━━━━━━━━━━━━━━━━━

🔜 Yakında:

📈 RSI
📊 MACD
📉 EMA
🎯 Destek / Direnç
🟢 AL
🟡 TUT
🔴 SAT
🔥 Fırsat taraması
🚨 Alarm sistemi
"""

    await update.message.reply_text(mesaj)


# =========================================================
# TEST
# =========================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "✅ ANKA YATIRIM ANALİZ çalışıyor!\n\n"
        "Telegram bağlantısı başarılı."
    )


# =========================================================
# FİYAT
# =========================================================

async def fiyat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "❗ Kullanım:\n\n"
            "/fiyat THYAO\n"
            "/fiyat ALTIN\n"
            "/fiyat USDTRY\n"
            "/fiyat BTC"
        )

        return


    symbol = context.args[0].upper()

    if symbol not in ASSETS:

        await update.message.reply_text(

            "❌ Bu varlık henüz tanımlı değil.\n\n"

            "Örnek:\n"
            "/fiyat THYAO\n"
            "/fiyat ALTIN\n"
            "/fiyat GUMUS\n"
            "/fiyat USDTRY\n"
            "/fiyat BTC"

        )

        return


    yahoo_symbol = ASSETS[symbol]


    await update.message.reply_text(
        f"🔍 {symbol} verisi alınıyor..."
    )


    try:

        ticker = yf.Ticker(yahoo_symbol)

        data = ticker.history(
            period="5d",
            interval="1d"
        )


        if data.empty:

            await update.message.reply_text(
                f"❌ {symbol} için veri bulunamadı."
            )

            return


        last = data.iloc[-1]


        close = float(last["Close"])

        open_price = float(last["Open"])

        high = float(last["High"])

        low = float(last["Low"])


        change = (
            (close - open_price)
            / open_price
            * 100
        )


        if change > 0:

            direction = "🟢"

        elif change < 0:

            direction = "🔴"

        else:

            direction = "🟡"


        mesaj = (

            f"🦅 ANKA YATIRIM ANALİZ\n\n"

            f"📊 {symbol}\n"

            f"💰 Fiyat: {close:.4f}\n\n"

            f"{direction} Günlük değişim: "
            f"{change:+.2f}%\n\n"

            f"🔺 Gün içi yüksek: {high:.4f}\n"

            f"🔻 Gün içi düşük: {low:.4f}\n\n"

            f"━━━━━━━━━━━━━━━━\n\n"

            f"📌 Veri kaynağı: Yahoo Finance\n\n"

            f"⚠️ Bu aşamada yalnızca fiyat "
            f"verisi gösterilmektedir.\n"

            f"Teknik analiz motoru sonraki "
            f"aşamada eklenecek."

        )


        await update.message.reply_text(
            mesaj
        )


    except Exception as e:

        await update.message.reply_text(

            "❌ Veri alınırken hata oluştu.\n\n"

            f"Hata: {str(e)}"

        )


# =========================================================
# HAKKINDA
# =========================================================

async def hakkinda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mesaj = """
🦅 ANKA YATIRIM ANALİZ

Amaç:

Finansal piyasalardaki varlıkları
veriye dayalı olarak analiz etmek.

📊 BIST
🇺🇸 ABD hisseleri
🥇 Altın
🥈 Gümüş
🟠 Bakır
💵 Döviz
₿ Kripto

Sistem aşamalı olarak
geliştirilecektir.

⚠️ Anka Yatırım Analiz yatırım
danışmanlığı yapmaz.
Sinyaller yalnızca analiz amaçlıdır.
"""

    await update.message.reply_text(mesaj)


# =========================================================
# BOTU BAŞLAT
# =========================================================

def main():

    if not TELEGRAM_TOKEN:

        print(
            "❌ TELEGRAM_TOKEN bulunamadı."
        )

        print(
            "Railway üzerinde daha sonra "
            "TELEGRAM_TOKEN değişkeni eklenmelidir."
        )

        return


    app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        CommandHandler(
            "anka",
            anka
        )
    )


    app.add_handler(
        CommandHandler(
            "test",
            test
        )
    )


    app.add_handler(
        CommandHandler(
            "fiyat",
            fiyat
        )
    )


    app.add_handler(
        CommandHandler(
            "hakkinda",
            hakkinda
        )
    )


    print(
        "🦅 ANKA YATIRIM ANALİZ BAŞLATILDI"
    )


    app.run_polling()


# =========================================================
# ÇALIŞTIR
# =========================================================

if __name__ == "__main__":

    main()
