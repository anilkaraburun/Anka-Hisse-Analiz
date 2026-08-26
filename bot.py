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

/analiz THYAO
/analiz ALTIN
/analiz GUMUS
/analiz BAKIR
/analiz USDTRY
/analiz BTC

/test

━━━━━━━━━━━━━━━━━━

🧠 Teknik analiz V2 aktif.

RSI + EMA20 + EMA50
MACD + Bollinger Bandı
ile teknik görünüm hesaplanmaktadır.
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

def get_data(
    symbol,
    period="6mo",
    interval="1d"
):

    try:

        data = yf.download(
            symbol,
            period=period,
            interval=interval,
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
# CLOSE SERİSİ
# ============================================================

def get_close_series(data):

    try:

        close = data["Close"]

        if hasattr(
            close,
            "columns"
        ):

            close = close.iloc[:, 0]

        close = close.dropna()

        return close

    except Exception as e:

        logger.error(
            "Close verisi alınamadı: %s",
            e
        )

        return None


# ============================================================
# EMA
# ============================================================

def calculate_ema(
    series,
    period
):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    series,
    period=14
):

    delta = series.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    average_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = (
        average_gain
        / average_loss
    )

    rsi = (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )

    return rsi


# ============================================================
# MACD
# ============================================================

def calculate_macd(
    series
):

    ema12 = calculate_ema(
        series,
        12
    )

    ema26 = calculate_ema(
        series,
        26
    )

    macd = ema12 - ema26

    signal = calculate_ema(
        macd,
        9
    )

    histogram = (
        macd
        - signal
    )

    return (
        macd,
        signal,
        histogram
    )


# ============================================================
# BOLLINGER BANDI
# ============================================================

def calculate_bollinger(
    series,
    period=20
):

    middle = series.rolling(
        period
    ).mean()

    std = series.rolling(
        period
    ).std()

    upper = (
        middle
        + (std * 2)
    )

    lower = (
        middle
        - (std * 2)
    )

    return (
        middle,
        upper,
        lower
    )


# ============================================================
# TEKNİK ANALİZ V2
# ============================================================

def technical_analysis(
    symbol
):

    data = get_data(
        symbol,
        period="6mo",
        interval="1d"
    )

    if data is None:

        return None


    close = get_close_series(
        data
    )

    if close is None:

        return None


    if len(close) < 50:

        return None


    # ========================================================
    # FİYAT
    # ========================================================

    current_price = float(
        close.iloc[-1]
    )


    # ========================================================
    # EMA
    # ========================================================

    ema20_series = calculate_ema(
        close,
        20
    )

    ema50_series = calculate_ema(
        close,
        50
    )


    ema20 = float(
        ema20_series.iloc[-1]
    )

    ema50 = float(
        ema50_series.iloc[-1]
    )


    # ========================================================
    # RSI
    # ========================================================

    rsi_series = calculate_rsi(
        close,
        14
    )

    rsi = float(
        rsi_series.iloc[-1]
    )


    # ========================================================
    # MACD
    # ========================================================

    macd_series, signal_series, histogram_series = (
        calculate_macd(close)
    )

    macd = float(
        macd_series.iloc[-1]
    )

    macd_signal = float(
        signal_series.iloc[-1]
    )

    macd_histogram = float(
        histogram_series.iloc[-1]
    )


    # ========================================================
    # BOLLINGER
    # ========================================================

    bb_middle_series, bb_upper_series, bb_lower_series = (
        calculate_bollinger(close)
    )

    bb_middle = float(
        bb_middle_series.iloc[-1]
    )

    bb_upper = float(
        bb_upper_series.iloc[-1]
    )

    bb_lower = float(
        bb_lower_series.iloc[-1]
    )


    # ========================================================
    # ANKA SKORU
    # ========================================================

    score = 50

    reasons = []


    # --------------------------------------------------------
    # FİYAT - EMA20
    # --------------------------------------------------------

    if current_price > ema20:

        score += 10

        reasons.append(
            "Fiyat EMA20 üzerinde"
        )

    else:

        score -= 10

        reasons.append(
            "Fiyat EMA20 altında"
        )


    # --------------------------------------------------------
    # EMA20 - EMA50
    # --------------------------------------------------------

    if ema20 > ema50:

        score += 15

        reasons.append(
            "EMA20, EMA50 üzerinde"
        )

    else:

        score -= 15

        reasons.append(
            "EMA20, EMA50 altında"
        )


    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if 50 <= rsi < 70:

        score += 10

        reasons.append(
            "RSI pozitif bölgede"
        )

    elif rsi >= 70:

        score += 5

        reasons.append(
            "RSI yüksek / aşırı alım bölgesi"
        )

    elif 30 < rsi < 50:

        score -= 5

        reasons.append(
            "RSI zayıf bölgede"
        )

    else:

        score -= 10

        reasons.append(
            "RSI aşırı satım bölgesinde"
        )


    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if macd > macd_signal:

        score += 10

        reasons.append(
            "MACD pozitif"
        )

    else:

        score -= 10

        reasons.append(
            "MACD negatif"
        )


    # --------------------------------------------------------
    # MACD HISTOGRAM
    # --------------------------------------------------------

    if macd_histogram > 0:

        score += 5

        reasons.append(
            "MACD histogram pozitif"
        )

    else:

        score -= 5

        reasons.append(
            "MACD histogram negatif"
        )


    # --------------------------------------------------------
    # BOLLINGER
    # --------------------------------------------------------

    if current_price > bb_middle:

        score += 5

        reasons.append(
            "Fiyat Bollinger orta bandının üzerinde"
        )

    else:

        score -= 5

        reasons.append(
            "Fiyat Bollinger orta bandının altında"
        )


    # ========================================================
    # SKOR SINIRI
    # ========================================================

    score = max(
        0,
        min(
            100,
            score
        )
    )


    # ========================================================
    # SİNYAL
    # ========================================================

    if score >= 80:

        signal = "🔥 GÜÇLÜ AL"

    elif score >= 60:

        signal = "🟢 AL"

    elif score >= 40:

        signal = "🟡 TUT"

    else:

        signal = "🔴 SAT"


    # ========================================================
    # TREND
    # ========================================================

    if (
        current_price > ema20
        and ema20 > ema50
    ):

        trend = "📈 GÜÇLÜ YÜKSELİŞ"

    elif current_price > ema20:

        trend = "📈 YÜKSELİŞ"

    elif (
        current_price < ema20
        and ema20 < ema50
    ):

        trend = "📉 GÜÇLÜ DÜŞÜŞ"

    else:

        trend = "➡️ YATAY / KARARSIZ"


    # ========================================================
    # BOLLINGER DURUMU
    # ========================================================

    if current_price >= bb_upper:

        bollinger_status = (
            "🔴 Üst banda çok yakın / üzerinde"
        )

    elif current_price <= bb_lower:

        bollinger_status = (
            "🟢 Alt banda çok yakın / altında"
        )

    else:

        bollinger_status = (
            "🟡 Bantlar arasında"
        )


    # ========================================================
    # MACD DURUMU
    # ========================================================

    if macd > macd_signal:

        macd_status = "🟢 Pozitif"

    else:

        macd_status = "🔴 Negatif"


    # ========================================================
    # SONUÇ
    # ========================================================

    return {

        "price": current_price,

        "ema20": ema20,

        "ema50": ema50,

        "rsi": rsi,

        "macd": macd,

        "macd_signal": macd_signal,

        "macd_histogram": macd_histogram,

        "bb_middle": bb_middle,

        "bb_upper": bb_upper,

        "bb_lower": bb_lower,

        "bollinger_status": bollinger_status,

        "macd_status": macd_status,

        "score": score,

        "signal": signal,

        "trend": trend,

        "reasons": reasons

    }


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
            "/fiyat THYAO"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Bu varlık sistemde bulunamadı."
        )

        return


    info = ASSETS[asset]


    await update.message.reply_text(
        f"🔎 {info['name']} verisi alınıyor..."
    )


    data = get_data(
        info["symbol"],
        period="5d",
        interval="1d"
    )


    if data is None:

        await update.message.reply_text(
            "❌ Yahoo Finance'den veri alınamadı."
        )

        return


    try:

        close_data = data["Close"]

        high_data = data["High"]

        low_data = data["Low"]


        if hasattr(
            close_data,
            "columns"
        ):

            close_data = close_data.iloc[:, 0]


        if hasattr(
            high_data,
            "columns"
        ):

            high_data = high_data.iloc[:, 0]


        if hasattr(
            low_data,
            "columns"
        ):

            low_data = low_data.iloc[:, 0]


        close_data = close_data.dropna()

        high_data = high_data.dropna()

        low_data = low_data.dropna()


        if len(close_data) == 0:

            await update.message.reply_text(
                "❌ Fiyat verisi boş geldi."
            )

            return


        current = float(
            close_data.iloc[-1]
        )


        if len(close_data) >= 2:

            previous = float(
                close_data.iloc[-2]
            )

        else:

            previous = current


        if previous != 0:

            change = (
                (
                    current
                    - previous
                )
                / previous
                * 100
            )

        else:

            change = 0


        high = float(
            high_data.iloc[-1]
        )

        low = float(
            low_data.iloc[-1]
        )


        if change > 0:

            direction = "🟢"

        elif change < 0:

            direction = "🔴"

        else:

            direction = "🟡"


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

            "🧠 Teknik analiz için:\n"
            f"/analiz {asset}"

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
            "bir hata oluştu."
        )


# ============================================================
# ANALİZ
# ============================================================

async def analiz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "❌ Varlık belirtmelisin.\n\n"
            "Örnek:\n"
            "/analiz THYAO"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Bu varlık sistemde bulunamadı."
        )

        return


    info = ASSETS[asset]


    await update.message.reply_text(
        f"🧠 {info['name']} V2 analiz ediliyor..."
    )


    result = technical_analysis(
        info["symbol"]
    )


    if result is None:

        await update.message.reply_text(
            "❌ Teknik analiz için yeterli "
            "veri alınamadı."
        )

        return


    reasons_text = "\n".join(
        f"• {reason}"
        for reason in result["reasons"]
    )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        f"📊 {asset}\n"
        f"{info['name']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🧠 ANKA TEKNİK ANALİZ V2\n\n"

        f"💰 Fiyat: "
        f"{result['price']:.4f}\n\n"

        f"📐 EMA20: "
        f"{result['ema20']:.4f}\n"

        f"📐 EMA50: "
        f"{result['ema50']:.4f}\n\n"

        f"📊 RSI(14): "
        f"{result['rsi']:.2f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📈 MACD\n\n"

        f"MACD: "
        f"{result['macd']:.4f}\n"

        f"Signal: "
        f"{result['macd_signal']:.4f}\n"

        f"Histogram: "
        f"{result['macd_histogram']:.4f}\n"

        f"Durum: "
        f"{result['macd_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 BOLLINGER BANDI\n\n"

        f"Üst bant: "
        f"{result['bb_upper']:.4f}\n"

        f"Orta bant: "
        f"{result['bb_middle']:.4f}\n"

        f"Alt bant: "
        f"{result['bb_lower']:.4f}\n\n"

        f"Durum: "
        f"{result['bollinger_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        f"📈 Trend:\n"
        f"{result['trend']}\n\n"

        "⭐ ANKA SKORU:\n"

        f"{result['score']}/100\n\n"

        "🤖 SİNYAL:\n"

        f"{result['signal']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🔍 GÖSTERGE DEĞERLENDİRMESİ\n\n"

        f"{reasons_text}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "⚠️ Bu sistem yatırım tavsiyesi "
        "değildir. Teknik göstergelere dayalı "
        "otomatik analizdir."

    )


    await update.message.reply_text(
        mesaj
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
            "analiz",
            analiz
        )
    )


    print(
        "🦅 ANKA YATIRIM ANALİZ V2 BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
