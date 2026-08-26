import os
import logging
import yfinance as yf

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


# ============================================================
# AYARLAR
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ============================================================
# VARLIKLAR
# ============================================================

ASSETS = {
    "THYAO": {
        "symbol": "THYAO.IS",
        "name": "Türk Hava Yolları"
    },

    "ALTIN": {
        "symbol": "GC=F",
        "name": "Altın"
    },

    "GUMUS": {
        "symbol": "SI=F",
        "name": "Gümüş"
    },

    "BAKIR": {
        "symbol": "HG=F",
        "name": "Bakır"
    },

    "USDTRY": {
        "symbol": "TRY=X",
        "name": "Dolar/TL"
    },

    "BTC": {
        "symbol": "BTC-USD",
        "name": "Bitcoin"
    }
}


# ============================================================
# START
# ============================================================

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
/fiyat GUMUS
/fiyat BAKIR
/fiyat USDTRY
/fiyat BTC

/test

━━━━━━━━━━━━━━━━━━

🚀 Teknik analiz sistemi
sonraki aşamada eklenecek.
"""

    await update.message.reply_text(mesaj)


# ============================================================
# ANKA
# ============================================================

async def anka(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await start(update, context)


# ============================================================
# TEST
# ============================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "✅ ANKA YATIRIM ANALİZ çalışıyor!\n\n"
        "Telegram bağlantısı başarılı. 🦅"
    )


# ============================================================
# VERİ AL
# ============================================================

def get_price_data(symbol):

    try:

        data = yf.download(
            symbol,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False
        )

        if data is None or data.empty:
            return None

        return data

    except Exception as e:

        logger.error(
            "Yahoo Finance veri hatası: %s",
            e
        )

        return None


# ============================================================
# FİYAT
# ============================================================

async def fiyat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "❌ Varlık belirtmelisin.\n\n"
            "Örnek:\n"
            "/fiyat THYAO\n"
            "/fiyat ALTIN\n"
            "/fiyat USDTRY\n"
            "/fiyat BTC"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Bu varlık sistemde bulunamadı.\n\n"
            "Örnekler:\n"
            "THYAO\n"
            "ALTIN\n"
            "GUMUS\n"
            "BAKIR\n"
            "USDTRY\n"
            "BTC"
        )

        return


    info = ASSETS[asset]


    await update.message.reply_text(
        f"🔎 {info['name']} verisi alınıyor..."
    )


    data = get_price_data(
        info["symbol"]
    )


    if data is None:

        await update.message.reply_text(
            "❌ Yahoo Finance'den veri alınamadı."
        )

        return


    try:

        # ====================================================
        # YAHOO FINANCE BAZEN MULTIINDEX DÖNDÜRÜYOR.
        # BU NEDENLE Close / High / Low DEĞERLERİNİ
        # GÜVENLİ ŞEKİLDE ALIYORUZ.
        # ====================================================

        close_data = data["Close"]

        high_data = data["High"]

        low_data = data["Low"]


        # Eğer DataFrame geldiyse ilk sütunu al

        if hasattr(close_data, "columns"):

            close_data = close_data.iloc[:, 0]

        if hasattr(high_data, "columns"):

            high_data = high_data.iloc[:, 0]

        if hasattr(low_data, "columns"):

            low_data = low_data.iloc[:, 0]


        # NaN değerleri temizle

        close_data = close_data.dropna()

        high_data = high_data.dropna()

        low_data = low_data.dropna()


        # Yeterli veri yoksa

        if len(close_data) == 0:

            await update.message.reply_text(
                "❌ Fiyat verisi boş geldi."
            )

            return


        # Güncel fiyat

        current = float(
            close_data.iloc[-1]
        )


        # Önceki kapanış

        if len(close_data) >= 2:

            previous = float(
                close_data.iloc[-2]
            )

        else:

            previous = current


        # Günlük değişim

        if previous != 0:

            change = (
                (current - previous)
                / previous
                * 100
            )

        else:

            change = 0


        # Gün içi yüksek

        high = float(
            high_data.iloc[-1]
        )


        # Gün içi düşük

        low = float(
            low_data.iloc[-1]
        )


        # Yön

        if change > 0:

            direction = "🟢"

        elif change < 0:

            direction = "🔴"

        else:

            direction = "🟡"


        # ====================================================
        # SONUÇ
        # ====================================================

        mesaj = (

            "🦅 ANKA YATIRIM ANALİZ\n\n"

            f"📊 {asset}\n\n"

            f"💰 Fiyat: {current:.4f}\n\n"

            f"{direction} Günlük değişim: "
            f"{change:+.2f}%\n\n"

            f"🔺 Gün içi yüksek: "
            f"{high:.4f}\n\n"

            f"🔻 Gün içi düşük: "
            f"{low:.4f}\n\n"

            "━━━━━━━━━━━━━━━━\n\n"

            "📌 Veri kaynağı: Yahoo Finance\n\n"

            "⚠️ Bu aşamada yalnızca fiyat "
            "verisi gösterilmektedir.\n\n"

            "🚀 Teknik analiz motoru "
            "sonraki aşamada eklenecek."
        )


        await update.message.reply_text(
            mesaj
        )


    except Exception as e:

        logger.error(
            "Fiyat hesaplama hatası: %s",
            e
        )


        await update.message.reply_text(
            "❌ Fiyat verisi işlenirken "
            "bir hata oluştu.\n\n"
            "Railway loglarını kontrol ediyoruz."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TELEGRAM_TOKEN:

        print(
            "❌ TELEGRAM_TOKEN bulunamadı."
        )

        return


    app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )


    # Komutlar

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


    print(
        "🦅 ANKA YATIRIM ANALİZ BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
