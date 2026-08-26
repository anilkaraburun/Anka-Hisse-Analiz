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

🧠 ANKA Teknik Analiz V3

RSI
EMA20 / EMA50
MACD
Bollinger
Destek / Direnç
Kırılım teyidi
Anka Skoru
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
# CLOSE
# ============================================================

def get_close_series(data):

    try:

        close = data["Close"]

        if hasattr(
            close,
            "columns"
        ):

            close = close.iloc[:, 0]

        return close.dropna()

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

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss

    return (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )


# ============================================================
# MACD
# ============================================================

def calculate_macd(series):

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

    histogram = macd - signal

    return (
        macd,
        signal,
        histogram
    )


# ============================================================
# BOLLINGER
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
        + 2 * std
    )

    lower = (
        middle
        - 2 * std
    )

    return (
        middle,
        upper,
        lower
    )


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(
    data,
    lookback=20
):

    try:

        high = data["High"]

        low = data["Low"]


        if hasattr(
            high,
            "columns"
        ):

            high = high.iloc[:, 0]


        if hasattr(
            low,
            "columns"
        ):

            low = low.iloc[:, 0]


        high = high.dropna()

        low = low.dropna()


        if len(high) < lookback:

            return None, None


        recent_high = high.iloc[
            -lookback:
        ]

        recent_low = low.iloc[
            -lookback:
        ]


        resistance = float(
            recent_high.max()
        )

        support = float(
            recent_low.min()
        )


        return (
            support,
            resistance
        )


    except Exception as e:

        logger.error(
            "Destek direnç hatası: %s",
            e
        )

        return None, None


# ============================================================
# KIRILIM KONTROLÜ
# ============================================================

def check_breakout(
    data,
    price,
    support,
    resistance
):

    if support is None or resistance is None:

        return "➡️ Kırılım yok"


    try:

        close = get_close_series(
            data
        )

        if close is None or len(close) < 3:

            return "➡️ Kırılım yok"


        previous_price = float(
            close.iloc[-2]
        )


        # ----------------------------------------------------
        # DİRENÇ KIRILIMI
        # ----------------------------------------------------

        if (
            previous_price <= resistance
            and price > resistance
        ):

            return "🚀 DİRENÇ KIRILDI"


        # ----------------------------------------------------
        # DESTEK KIRILIMI
        # ----------------------------------------------------

        if (
            previous_price >= support
            and price < support
        ):

            return "🔻 DESTEK KIRILDI"


        # ----------------------------------------------------
        # DİRENCE YAKIN
        # ----------------------------------------------------

        resistance_distance = (
            (resistance - price)
            / price
            * 100
        )


        if (
            resistance_distance >= 0
            and resistance_distance <= 1
        ):

            return "⚠️ DİRENCE YAKIN"


        # ----------------------------------------------------
        # DESTEĞE YAKIN
        # ----------------------------------------------------

        support_distance = (
            (price - support)
            / price
            * 100
        )


        if (
            support_distance >= 0
            and support_distance <= 1
        ):

            return "🟢 DESTEĞE YAKIN"


        return "➡️ Kırılım yok"


    except Exception:

        return "➡️ Kırılım yok"


# ============================================================
# TEKNİK ANALİZ V3
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

    price = float(
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
        close
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

    histogram = float(
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
    # DESTEK / DİRENÇ
    # ========================================================

    support, resistance = (
        calculate_support_resistance(
            data,
            20
        )
    )


    # ========================================================
    # KIRILIM
    # ========================================================

    breakout = check_breakout(
        data,
        price,
        support,
        resistance
    )


    # ========================================================
    # ANKA SKORU
    #
    # 50 = NÖTR
    #
    # Trend       ±25
    # RSI         ±15
    # MACD        ±20
    # Bollinger   ±10
    # Kırılım     ±30
    #
    # Daha sonra ağırlıkları
    # backtest ile optimize edeceğiz.
    # ========================================================

    score = 50

    reasons = []


    # ========================================================
    # TREND
    # ========================================================

    if (
        price > ema20
        and ema20 > ema50
    ):

        score += 25

        reasons.append(
            "Güçlü yükseliş trendi"
        )

    elif (
        price < ema20
        and ema20 < ema50
    ):

        score -= 25

        reasons.append(
            "Güçlü düşüş trendi"
        )

    elif price > ema20:

        score += 12

        reasons.append(
            "Fiyat EMA20 üzerinde"
        )

    else:

        score -= 12

        reasons.append(
            "Fiyat EMA20 altında"
        )


    # ========================================================
    # RSI
    # ========================================================

    if 50 <= rsi < 70:

        score += 15

        reasons.append(
            "RSI pozitif"
        )

    elif 70 <= rsi:

        score += 5

        reasons.append(
            "RSI yüksek / aşırı alım"
        )

    elif 30 < rsi < 50:

        score -= 7

        reasons.append(
            "RSI zayıf"
        )

    else:

        score -= 10

        reasons.append(
            "RSI aşırı satım"
        )


    # ========================================================
    # MACD
    # ========================================================

    if macd > macd_signal:

        score += 15

        reasons.append(
            "MACD pozitif"
        )

    else:

        score -= 15

        reasons.append(
            "MACD negatif"
        )


    # ========================================================
    # MACD HISTOGRAM
    # ========================================================

    if histogram > 0:

        score += 5

        reasons.append(
            "MACD histogram pozitif"
        )

    else:

        score -= 5

        reasons.append(
            "MACD histogram negatif"
        )


    # ========================================================
    # BOLLINGER
    # ========================================================

    if (
        price > bb_middle
        and price < bb_upper
    ):

        score += 5

        reasons.append(
            "Fiyat Bollinger orta bandı üzerinde"
        )

    elif price < bb_middle:

        score -= 5

        reasons.append(
            "Fiyat Bollinger orta bandı altında"
        )


    # ========================================================
    # KIRILIM
    # ========================================================

    if breakout == "🚀 DİRENÇ KIRILDI":

        score += 30

        reasons.append(
            "Direnç yukarı kırıldı"
        )

    elif breakout == "🔻 DESTEK KIRILDI":

        score -= 30

        reasons.append(
            "Destek aşağı kırıldı"
        )

    elif breakout == "⚠️ DİRENCE YAKIN":

        score += 3

        reasons.append(
            "Fiyat dirence yaklaşıyor"
        )

    elif breakout == "🟢 DESTEĞE YAKIN":

        score += 3

        reasons.append(
            "Fiyat desteğe yaklaşıyor"
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
    # TREND METNİ
    # ========================================================

    if (
        price > ema20
        and ema20 > ema50
    ):

        trend = "📈 GÜÇLÜ YÜKSELİŞ"

    elif price > ema20:

        trend = "📈 YÜKSELİŞ"

    elif (
        price < ema20
        and ema20 < ema50
    ):

        trend = "📉 GÜÇLÜ DÜŞÜŞ"

    else:

        trend = "➡️ YATAY / KARARSIZ"


    # ========================================================
    # SONUÇ
    # ========================================================

    return {

        "price": price,

        "ema20": ema20,

        "ema50": ema50,

        "rsi": rsi,

        "macd": macd,

        "macd_signal": macd_signal,

        "histogram": histogram,

        "bb_middle": bb_middle,

        "bb_upper": bb_upper,

        "bb_lower": bb_lower,

        "support": support,

        "resistance": resistance,

        "breakout": breakout,

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

        close = data["Close"]

        high = data["High"]

        low = data["Low"]


        if hasattr(
            close,
            "columns"
        ):

            close = close.iloc[:, 0]


        if hasattr(
            high,
            "columns"
        ):

            high = high.iloc[:, 0]


        if hasattr(
            low,
            "columns"
        ):

            low = low.iloc[:, 0]


        close = close.dropna()

        high = high.dropna()

        low = low.dropna()


        current = float(
            close.iloc[-1]
        )


        if len(close) >= 2:

            previous = float(
                close.iloc[-2]
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


        high_value = float(
            high.iloc[-1]
        )

        low_value = float(
            low.iloc[-1]
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

            f"💰 Fiyat: "
            f"{current:.4f}\n\n"

            f"{direction} Günlük değişim: "
            f"{change:+.2f}%\n\n"

            f"🔺 Gün içi yüksek: "
            f"{high_value:.4f}\n\n"

            f"🔻 Gün içi düşük: "
            f"{low_value:.4f}\n\n"

            "━━━━━━━━━━━━━━━━\n\n"

            "📌 Veri kaynağı: Yahoo Finance\n\n"

            f"🧠 Teknik analiz:\n"
            f"/analiz {asset}"

        )


        await update.message.reply_text(
            mesaj
        )


    except Exception as e:

        logger.error(
            "Fiyat hatası: %s",
            e
        )

        await update.message.reply_text(
            "❌ Fiyat verisi işlenirken hata oluştu."
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
        f"🧠 {info['name']} V3 analiz ediliyor..."
    )


    result = technical_analysis(
        info["symbol"]
    )


    if result is None:

        await update.message.reply_text(
            "❌ Teknik analiz için yeterli veri alınamadı."
        )

        return


    reasons_text = "\n".join(
        f"• {reason}"
        for reason in result["reasons"]
    )


    if result["support"] is not None:

        support_text = (
            f"{result['support']:.4f}"
        )

    else:

        support_text = "Hesaplanamadı"


    if result["resistance"] is not None:

        resistance_text = (
            f"{result['resistance']:.4f}"
        )

    else:

        resistance_text = "Hesaplanamadı"


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        f"📊 {asset}\n"
        f"{info['name']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🧠 ANKA TEKNİK ANALİZ V3\n\n"

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
        f"{result['histogram']:.4f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 BOLLINGER BANDI\n\n"

        f"Üst: "
        f"{result['bb_upper']:.4f}\n"

        f"Orta: "
        f"{result['bb_middle']:.4f}\n"

        f"Alt: "
        f"{result['bb_lower']:.4f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🎯 DESTEK / DİRENÇ\n\n"

        f"🟢 Destek: "
        f"{support_text}\n"

        f"🔴 Direnç: "
        f"{resistance_text}\n\n"

        f"🚨 Durum:\n"
        f"{result['breakout']}\n\n"

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
        "🦅 ANKA YATIRIM ANALİZ V3 BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
