import os
import logging
import pandas as pd
import yfinance as yf

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


# ============================================================
# 🦅 ANKA YATIRIM ANALİZ V8
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

    # 🇹🇷 BIST
    "THYAO": {
        "symbol": "THYAO.IS",
        "name": "Türk Hava Yolları"
    },

    "ASELS": {
        "symbol": "ASELS.IS",
        "name": "Aselsan"
    },

    "TUPRS": {
        "symbol": "TUPRS.IS",
        "name": "Tüpraş"
    },

    "BIMAS": {
        "symbol": "BIMAS.IS",
        "name": "BİM"
    },

    "EREGL": {
        "symbol": "EREGL.IS",
        "name": "Ereğli Demir Çelik"
    },

    "GARAN": {
        "symbol": "GARAN.IS",
        "name": "Garanti BBVA"
    },

    "AKBNK": {
        "symbol": "AKBNK.IS",
        "name": "Akbank"
    },

    "YKBNK": {
        "symbol": "YKBNK.IS",
        "name": "Yapı Kredi"
    },

    "SISE": {
        "symbol": "SISE.IS",
        "name": "Şişecam"
    },

    "KCHOL": {
        "symbol": "KCHOL.IS",
        "name": "Koç Holding"
    },

    # 🥇 ALTIN
    "ALTIN": {
        "symbol": "GC=F",
        "name": "Altın"
    },

    # 🥈 GÜMÜŞ
    "GUMUS": {
        "symbol": "SI=F",
        "name": "Gümüş"
    },

    # 🟠 BAKIR
    "BAKIR": {
        "symbol": "HG=F",
        "name": "Bakır"
    },

    # 💵 DÖVİZ
    "USDTRY": {
        "symbol": "TRY=X",
        "name": "Dolar/TL"
    },

    "EURTRY": {
        "symbol": "EURTRY=X",
        "name": "Euro/TL"
    },

    # 🇺🇸 ABD
    "AAPL": {
        "symbol": "AAPL",
        "name": "Apple"
    },

    "NVDA": {
        "symbol": "NVDA",
        "name": "Nvidia"
    },

    "TSLA": {
        "symbol": "TSLA",
        "name": "Tesla"
    },

    # ₿ KRİPTO
    "BTC": {
        "symbol": "BTC-USD",
        "name": "Bitcoin"
    },

    "ETH": {
        "symbol": "ETH-USD",
        "name": "Ethereum"
    }
}


# ============================================================
# TAKİP LİSTESİ
# ============================================================

WATCHLIST = set()


# ============================================================
# VERİ ÇEKME
# ============================================================

def get_data(symbol, period="6mo", interval="1d"):

    try:

        data = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            multi_level_index=False
        )

        if data is None or data.empty:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        if "Close" not in data.columns:
            logger.error(
                "%s için Close sütunu bulunamadı.",
                symbol
            )
            return None

        close = data["Close"]

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = pd.to_numeric(
            close,
            errors="coerce"
        )

        data["Close"] = close

        data = data.dropna(
            subset=["Close"]
        )

        if data.empty:
            return None

        return data

    except Exception as e:

        logger.error(
            "Veri alınamadı %s: %s",
            symbol,
            e
        )

        return None


# ============================================================
# EMA
# ============================================================

def calculate_ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# ============================================================
# RSI
# ============================================================

def calculate_rsi(series, period=14):

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

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


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

    upper = middle + (
        std * 2
    )

    lower = middle - (
        std * 2
    )

    return (
        middle,
        upper,
        lower
    )


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(data):

    recent = data.tail(20)

    high = pd.to_numeric(
        recent["High"],
        errors="coerce"
    ).dropna()

    low = pd.to_numeric(
        recent["Low"],
        errors="coerce"
    ).dropna()

    close = pd.to_numeric(
        recent["Close"],
        errors="coerce"
    ).dropna()

    if len(high) < 5 or len(low) < 5:
        return None, None

    current = float(
        close.iloc[-1]
    )

    resistance = float(
        high.max()
    )

    support = float(
        low.min()
    )

    previous_highs = sorted(
        set(
            float(x)
            for x in high
            if float(x) > current
        )
    )

    if previous_highs:
        resistance = previous_highs[0]

    previous_lows = sorted(
        set(
            float(x)
            for x in low
            if float(x) < current
        ),
        reverse=True
    )

    if previous_lows:
        support = previous_lows[0]

    # Destek ve direnç birbirine aşırı yakınsa
    # son 20 günün gerçek aralığını kullan

    if resistance <= support:
        resistance = float(high.max())
        support = float(low.min())

    if current > 0:

        range_percent = (
            (resistance - support)
            / current
            * 100
        )

        if range_percent < 0.5:

            support = float(low.min())
            resistance = float(high.max())

    return (
        support,
        resistance
    )


# ============================================================
# 🧠 ANKA SKOR MOTORU V8
# ============================================================

def calculate_anka_score(
    price,
    ema20,
    ema50,
    rsi,
    macd,
    signal,
    histogram,
    bb_middle,
    support,
    resistance
):

    # --------------------------------------------------------
    # NÖTR BAŞLANGIÇ
    # --------------------------------------------------------

    score = 50.0

    reasons = []


    # ========================================================
    # 1 — FİYAT / EMA20
    # ========================================================

    if price > ema20:

        score += 8

        reasons.append(
            "Fiyat EMA20 üzerinde"
        )

    else:

        score -= 8

        reasons.append(
            "Fiyat EMA20 altında"
        )


    # ========================================================
    # 2 — EMA20 / EMA50
    # ========================================================

    if ema20 > ema50:

        score += 10

        reasons.append(
            "EMA20, EMA50 üzerinde"
        )

    else:

        score -= 10

        reasons.append(
            "EMA20, EMA50 altında"
        )


    # ========================================================
    # 3 — RSI
    # ========================================================

    if rsi >= 70:

        score += 3

        reasons.append(
            "RSI yüksek / güçlü momentum"
        )

    elif rsi >= 60:

        score += 7

        reasons.append(
            "RSI güçlü bölgede"
        )

    elif rsi >= 50:

        score += 4

        reasons.append(
            "RSI pozitif bölgede"
        )

    elif rsi >= 40:

        score -= 2

        reasons.append(
            "RSI hafif zayıf bölgede"
        )

    elif rsi >= 30:

        score -= 5

        reasons.append(
            "RSI zayıf bölgede"
        )

    else:

        # Aşırı satım aynı zamanda tepki ihtimali
        # taşıdığı için ağır ceza vermiyoruz.

        score -= 2

        reasons.append(
            "RSI aşırı satım bölgesinde"
        )


    # ========================================================
    # 4 — MACD / SIGNAL
    # ========================================================

    if macd > signal:

        score += 7

        reasons.append(
            "MACD Signal üzerinde"
        )

    else:

        score -= 7

        reasons.append(
            "MACD Signal altında"
        )


    # ========================================================
    # 5 — MACD HISTOGRAM
    # ========================================================

    if histogram > 0:

        score += 4

        reasons.append(
            "MACD histogram pozitif"
        )

    else:

        score -= 4

        reasons.append(
            "MACD histogram negatif"
        )


    # ========================================================
    # 6 — BOLLINGER ORTA BANT
    # ========================================================

    if price > bb_middle:

        score += 4

        reasons.append(
            "Fiyat Bollinger orta bandının üzerinde"
        )

    else:

        score -= 4

        reasons.append(
            "Fiyat Bollinger orta bandının altında"
        )


    # ========================================================
    # 7 — DESTEK / DİRENÇ KONUMU
    # ========================================================

    if (
        support is not None
        and resistance is not None
        and resistance > support
        and price > 0
    ):

        range_value = resistance - support

        position = (
            price - support
        ) / range_value

        # Pozisyonu güvenli aralıkta tut
        position = max(
            0,
            min(
                1,
                position
            )
        )


        # Desteğe yakınsa tepki potansiyeli

        if position <= 0.20:

            score += 6

            reasons.append(
                "Fiyat güçlü destek bölgesine yakın"
            )

        elif position <= 0.40:

            score += 3

            reasons.append(
                "Fiyat destek bölgesine yakın"
            )

        elif position >= 0.85:

            score -= 2

            reasons.append(
                "Fiyat direnç bölgesine yakın"
            )

        else:

            reasons.append(
                "Fiyat destek/direnç arasında"
            )


    # ========================================================
    # 8 — GENEL TREND DENGELEME
    # ========================================================

    # Güçlü yükseliş
    if (
        price > ema20
        and ema20 > ema50
    ):

        score += 5

        reasons.append(
            "Genel trend pozitif"
        )

    # Güçlü düşüş
    elif (
        price < ema20
        and ema20 < ema50
    ):

        score -= 5

        reasons.append(
            "Genel trend negatif"
        )


    # ========================================================
    # 9 — SON SINIRLAMA
    # ========================================================

    score = max(
        5,
        min(
            95,
            score
        )
    )


    return (
        int(round(score)),
        reasons
    )


# ============================================================
# TEKNİK ANALİZ
# ============================================================

def technical_analysis(symbol):

    data = get_data(
        symbol,
        period="6mo",
        interval="1d"
    )

    if data is None:
        return None

    try:

        close = pd.to_numeric(
            data["Close"],
            errors="coerce"
        ).dropna()

        if len(close) < 60:

            logger.warning(
                "%s için yeterli veri yok. Veri sayısı: %s",
                symbol,
                len(close)
            )

            return None


        # ----------------------------------------------------
        # FİYAT
        # ----------------------------------------------------

        price = float(
            close.iloc[-1]
        )


        # ----------------------------------------------------
        # EMA
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # RSI
        # ----------------------------------------------------

        rsi_series = calculate_rsi(
            close,
            14
        )

        rsi_clean = rsi_series.dropna()

        if rsi_clean.empty:
            return None

        rsi = float(
            rsi_clean.iloc[-1]
        )


        # ----------------------------------------------------
        # MACD
        # ----------------------------------------------------

        macd_series, signal_series, histogram_series = (
            calculate_macd(close)
        )

        macd = float(
            macd_series.iloc[-1]
        )

        signal = float(
            signal_series.iloc[-1]
        )

        histogram = float(
            histogram_series.iloc[-1]
        )


        # ----------------------------------------------------
        # BOLLINGER
        # ----------------------------------------------------

        (
            bb_middle_series,
            bb_upper_series,
            bb_lower_series
        ) = calculate_bollinger(
            close
        )

        bb_middle_clean = bb_middle_series.dropna()
        bb_upper_clean = bb_upper_series.dropna()
        bb_lower_clean = bb_lower_series.dropna()

        if (
            bb_middle_clean.empty
            or bb_upper_clean.empty
            or bb_lower_clean.empty
        ):
            return None

        bb_middle = float(
            bb_middle_clean.iloc[-1]
        )

        bb_upper = float(
            bb_upper_clean.iloc[-1]
        )

        bb_lower = float(
            bb_lower_clean.iloc[-1]
        )


        # ----------------------------------------------------
        # DESTEK / DİRENÇ
        # ----------------------------------------------------

        support, resistance = (
            calculate_support_resistance(
                data
            )
        )


        # ----------------------------------------------------
        # SKOR
        # ----------------------------------------------------

        score, reasons = calculate_anka_score(

            price=price,

            ema20=ema20,

            ema50=ema50,

            rsi=rsi,

            macd=macd,

            signal=signal,

            histogram=histogram,

            bb_middle=bb_middle,

            support=support,

            resistance=resistance
        )


        # ----------------------------------------------------
        # TREND
        # ----------------------------------------------------

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

        elif price < ema20:

            trend = "📉 DÜŞÜŞ"

        else:

            trend = "➡️ YATAY"


        # ----------------------------------------------------
        # SİNYAL
        # ----------------------------------------------------

        if score >= 75:

            signal_text = "🔥 GÜÇLÜ AL"

        elif score >= 60:

            signal_text = "🟢 AL"

        elif score >= 45:

            signal_text = "🟡 TUT"

        elif score >= 30:

            signal_text = "🟠 ZAYIF"

        else:

            signal_text = "🔴 SAT"


        # ----------------------------------------------------
        # KIRILIM
        # ----------------------------------------------------

        breakout = "➡️ Kırılım yok"

        if (
            resistance is not None
            and price > resistance
        ):

            breakout = (
                "🚀 DİRENÇ KIRILDI"
            )

        elif (
            support is not None
            and price < support
        ):

            breakout = (
                "🚨 DESTEK KIRILDI"
            )


        return {

            "price": price,

            "ema20": ema20,

            "ema50": ema50,

            "rsi": rsi,

            "macd": macd,

            "signal": signal,

            "histogram": histogram,

            "bb_upper": bb_upper,

            "bb_middle": bb_middle,

            "bb_lower": bb_lower,

            "support": support,

            "resistance": resistance,

            "trend": trend,

            "score": score,

            "signal_text": signal_text,

            "breakout": breakout,

            "reasons": reasons

        }


    except Exception as e:

        logger.exception(
            "Teknik analiz hatası %s: %s",
            symbol,
            e
        )

        return None


# ============================================================
# /START
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
/fiyat USDTRY
/fiyat BTC

/analiz THYAO
/analiz ALTIN

/metaller

/firsatlar

/takip THYAO
/takiplerim

/test

━━━━━━━━━━━━━━━━━━

🧠 ANKA TEKNİK ANALİZ V8

EMA20 • EMA50
RSI • MACD
Bollinger
Destek / Direnç
Anka Skoru

⚠️ Bu sistem yatırım tavsiyesi değildir.
"""

    await update.message.reply_text(
        mesaj
    )


# ============================================================
# /ANKA
# ============================================================

async def anka(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await start(
        update,
        context
    )


# ============================================================
# /TEST
# ============================================================

async def test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "✅ ANKA YATIRIM ANALİZ çalışıyor!\n\n"
        "🦅 Telegram bağlantısı başarılı."
    )


# ============================================================
# /FIYAT
# ============================================================

async def fiyat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n\n"
            "/fiyat THYAO\n"
            "/fiyat ALTIN\n"
            "/fiyat USDTRY\n"
            "/fiyat BTC"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Varlık bulunamadı."
        )

        return


    info = ASSETS[asset]


    data = get_data(
        info["symbol"],
        period="5d",
        interval="1d"
    )


    if data is None:

        await update.message.reply_text(
            "❌ Veri alınamadı."
        )

        return


    try:

        close = pd.to_numeric(
            data["Close"],
            errors="coerce"
        ).dropna()

        if close.empty:

            await update.message.reply_text(
                "❌ Fiyat verisi bulunamadı."
            )

            return


        current = float(
            close.iloc[-1]
        )

        previous = (
            float(close.iloc[-2])
            if len(close) > 1
            else current
        )

        change = (
            (current - previous)
            / previous
            * 100
        ) if previous != 0 else 0


        high_series = pd.to_numeric(
            data["High"],
            errors="coerce"
        ).dropna()

        low_series = pd.to_numeric(
            data["Low"],
            errors="coerce"
        ).dropna()

        high = (
            float(high_series.iloc[-1])
            if not high_series.empty
            else current
        )

        low = (
            float(low_series.iloc[-1])
            if not low_series.empty
            else current
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


    except Exception:

        logger.exception(
            "Fiyat hatası"
        )

        await update.message.reply_text(
            "❌ Fiyat hesaplanırken hata oluştu."
        )


# ============================================================
# /ANALIZ
# ============================================================

async def analiz(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n\n"
            "/analiz THYAO\n"
            "/analiz ALTIN\n"
            "/analiz GUMUS\n"
            "/analiz BAKIR"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Varlık bulunamadı."
        )

        return


    info = ASSETS[asset]


    await update.message.reply_text(
        f"🔎 {asset} teknik olarak analiz ediliyor..."
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
        f"• {x}"
        for x in result["reasons"]
    )


    support_text = (
        f"{result['support']:.4f}"
        if result["support"] is not None
        else "Hesaplanamadı"
    )


    resistance_text = (
        f"{result['resistance']:.4f}"
        if result["resistance"] is not None
        else "Hesaplanamadı"
    )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        f"📊 {asset}\n\n"

        f"{info['name']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🧠 ANKA TEKNİK ANALİZ V8\n\n"

        f"💰 Fiyat: {result['price']:.4f}\n\n"

        f"📐 EMA20: {result['ema20']:.4f}\n\n"

        f"📐 EMA50: {result['ema50']:.4f}\n\n"

        f"📊 RSI(14): {result['rsi']:.2f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📈 MACD\n\n"

        f"MACD: {result['macd']:.4f}\n"

        f"Signal: {result['signal']:.4f}\n"

        f"Histogram: {result['histogram']:.4f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 BOLLINGER BANDI\n\n"

        f"Üst: {result['bb_upper']:.4f}\n"

        f"Orta: {result['bb_middle']:.4f}\n"

        f"Alt: {result['bb_lower']:.4f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🎯 DESTEK / DİRENÇ\n\n"

        f"🟢 Destek: {support_text}\n"

        f"🔴 Direnç: {resistance_text}\n\n"

        "🚨 Durum:\n\n"

        f"{result['breakout']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📈 Trend:\n\n"

        f"{result['trend']}\n\n"

        "⭐ ANKA SKORU:\n\n"

        f"{result['score']}/100\n\n"

        "🤖 SİNYAL:\n\n"

        f"{result['signal_text']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🔍 GÖSTERGE DEĞERLENDİRMESİ\n\n"

        f"{reasons_text}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "⚠️ Bu sistem yatırım tavsiyesi değildir.\n"
        "Teknik göstergelere dayalı otomatik analizdir."
    )


    await update.message.reply_text(
        mesaj
    )


# ============================================================
# /METALLER
# ============================================================

async def metaller(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🥇🥈🟠 Altın-Gümüş-Bakır analiz ediliyor..."
    )


    assets = [
        ("ALTIN", "🥇"),
        ("GUMUS", "🥈"),
        ("BAKIR", "🟠")
    ]


    mesajlar = []


    for asset, emoji in assets:

        result = technical_analysis(
            ASSETS[asset]["symbol"]
        )


        if result is None:

            mesajlar.append(
                f"{emoji} {asset}\n"
                "❌ Veri alınamadı."
            )

            continue


        mesajlar.append(

            f"{emoji} {asset}\n\n"

            f"💰 Fiyat: {result['price']:.4f}\n"

            f"📈 Trend: {result['trend']}\n"

            f"📊 RSI: {result['rsi']:.2f}\n"

            f"⭐ Anka Skoru: {result['score']}/100\n"

            f"🤖 {result['signal_text']}"
        )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        "🔥 ÜÇLÜ METAL RAPORU\n\n"

        +

        "\n\n━━━━━━━━━━━━━━━━\n\n".join(
            mesajlar
        )
    )


    await update.message.reply_text(
        mesaj
    )


# ============================================================
# /FIRSATLAR
# ============================================================

async def firsatlar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔥 Anka fırsat taraması yapıyor..."
    )


    results = []


    for asset, info in ASSETS.items():

        result = technical_analysis(
            info["symbol"]
        )


        if result is None:
            continue


        results.append(
            (
                result["score"],
                asset,
                result
            )
        )


    results.sort(
        key=lambda x: x[0],
        reverse=True
    )


    top = results[:10]


    if not top:

        await update.message.reply_text(
            "❌ Fırsat taraması yapılamadı."
        )

        return


    mesajlar = []


    for i, (
        score,
        asset,
        result
    ) in enumerate(
        top,
        1
    ):

        mesajlar.append(

            f"{i}. {asset}\n\n"

            f"⭐ {score}/100\n"

            f"{result['signal_text']}\n"

            f"{result['trend']}"
        )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        "🔥 EN GÜÇLÜ TEKNİK GÖRÜNÜMLER\n\n"

        +

        "\n\n━━━━━━━━━━━━━━\n\n".join(
            mesajlar
        )
    )


    await update.message.reply_text(
        mesaj
    )


# ============================================================
# /TAKIP
# ============================================================

async def takip(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n\n"
            "/takip THYAO"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Varlık bulunamadı."
        )

        return


    WATCHLIST.add(
        asset
    )


    await update.message.reply_text(

        f"✅ {asset} takip listesine eklendi.\n\n"

        "🦅 Anka takip sistemine aldı."
    )


# ============================================================
# /TAKIPLERIM
# ============================================================

async def takiplerim(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not WATCHLIST:

        await update.message.reply_text(
            "📋 Takip listen boş."
        )

        return


    liste = "\n".join(
        f"• {x}"
        for x in sorted(WATCHLIST)
    )


    await update.message.reply_text(

        "🦅 ANKA TAKİP LİSTESİ\n\n"

        + liste
    )


# ============================================================
# /HAKKINDA
# ============================================================

async def hakkinda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        "Teknik göstergeleri kullanarak "
        "otomatik piyasa analizi yapan "
        "bir finans botudur.\n\n"

        "🧠 V8 MOTORU\n\n"

        "EMA20\n"
        "EMA50\n"
        "RSI(14)\n"
        "MACD\n"
        "Bollinger Bandı\n"
        "Destek / Direnç\n\n"

        "⭐ Anka Skoru: 5-95\n\n"

        "⚠️ Yatırım tavsiyesi değildir."
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
        .token(
            TELEGRAM_TOKEN
        )
        .build()
    )


    # --------------------------------------------------------
    # KOMUTLAR
    # --------------------------------------------------------

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

    app.add_handler(
        CommandHandler(
            "metaller",
            metaller
        )
    )

    app.add_handler(
        CommandHandler(
            "firsatlar",
            firsatlar
        )
    )

    app.add_handler(
        CommandHandler(
            "takip",
            takip
        )
    )

    app.add_handler(
        CommandHandler(
            "takiplerim",
            takiplerim
        )
    )

    app.add_handler(
        CommandHandler(
            "hakkinda",
            hakkinda
        )
    )


    print(
        "🦅 ANKA YATIRIM ANALİZ V8 BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
