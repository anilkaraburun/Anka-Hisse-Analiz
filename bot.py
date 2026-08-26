import os
import logging
import math

import yfinance as yf

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


# ============================================================
# 🦅 ANKA YATIRIM ANALİZ V4
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
# SON ALARM
# ============================================================

LAST_ALERT = {}


# ============================================================
# YARDIMCI
# ============================================================

def safe_float(value, default=0.0):

    try:

        result = float(value)

        if math.isnan(result) or math.isinf(result):
            return default

        return result

    except Exception:

        return default


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
            progress=False
        )

        if data is None or data.empty:
            return None


        # yfinance MultiIndex düzeltmesi
        if hasattr(data.columns, "levels"):

            try:

                close = data["Close"]

                if hasattr(close, "columns"):

                    close = close.iloc[:, 0]

                data["Close"] = close

            except Exception:

                pass


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

    avg_gain = gain.rolling(
        period
    ).mean()

    avg_loss = loss.rolling(
        period
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        float("nan")
    )

    rsi = 100 - (
        100 / (1 + rs)
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
# V4 SKOR SİSTEMİ
# ============================================================

def calculate_anka_score(
    price,
    ema20,
    ema50,
    rsi,
    macd,
    macd_signal,
    histogram,
    bb_middle,
    daily_change
):

    # --------------------------------------------------------
    # 1. EMA20
    # --------------------------------------------------------

    if price > ema20:

        ema20_score = 100

    else:

        # Fiyat EMA20'den ne kadar uzak?
        distance = (
            (ema20 - price)
            / ema20
            * 100
        )

        if distance <= 1:
            ema20_score = 45

        elif distance <= 3:
            ema20_score = 30

        elif distance <= 5:
            ema20_score = 20

        else:
            ema20_score = 10


    # --------------------------------------------------------
    # 2. EMA50
    # --------------------------------------------------------

    if price > ema50:

        ema50_score = 100

    else:

        distance = (
            (ema50 - price)
            / ema50
            * 100
        )

        if distance <= 1:
            ema50_score = 45

        elif distance <= 3:
            ema50_score = 30

        elif distance <= 5:
            ema50_score = 20

        else:
            ema50_score = 10


    # --------------------------------------------------------
    # 3. RSI
    # --------------------------------------------------------

    if rsi >= 70:

        # Güçlü ama aşırı alım
        rsi_score = 70

    elif rsi >= 60:

        rsi_score = 90

    elif rsi >= 50:

        rsi_score = 75

    elif rsi >= 45:

        rsi_score = 55

    elif rsi >= 40:

        rsi_score = 40

    elif rsi >= 30:

        rsi_score = 25

    else:

        rsi_score = 15


    # --------------------------------------------------------
    # 4. MACD
    # --------------------------------------------------------

    if macd > macd_signal:

        macd_score = 100

    else:

        difference = abs(
            macd - macd_signal
        )

        if difference < 0.2:

            macd_score = 45

        elif difference < 1:

            macd_score = 30

        else:

            macd_score = 15


    # --------------------------------------------------------
    # 5. MACD HISTOGRAM
    # --------------------------------------------------------

    if histogram > 0:

        histogram_score = 100

    else:

        if abs(histogram) < 0.2:

            histogram_score = 45

        elif abs(histogram) < 1:

            histogram_score = 30

        else:

            histogram_score = 15


    # --------------------------------------------------------
    # 6. BOLLINGER
    # --------------------------------------------------------

    if price > bb_middle:

        bb_score = 85

    else:

        distance = (
            (bb_middle - price)
            / bb_middle
            * 100
        )

        if distance <= 1:

            bb_score = 45

        elif distance <= 3:

            bb_score = 30

        else:

            bb_score = 15


    # --------------------------------------------------------
    # 7. MOMENTUM
    # --------------------------------------------------------

    if daily_change >= 2:

        momentum_score = 100

    elif daily_change >= 1:

        momentum_score = 85

    elif daily_change >= 0:

        momentum_score = 60

    elif daily_change >= -1:

        momentum_score = 40

    elif daily_change >= -2:

        momentum_score = 25

    else:

        momentum_score = 10


    # ========================================================
    # AĞIRLIKLI SKOR
    # ========================================================

    score = (

        ema20_score * 0.20 +

        ema50_score * 0.15 +

        rsi_score * 0.15 +

        macd_score * 0.15 +

        histogram_score * 0.10 +

        bb_score * 0.10 +

        momentum_score * 0.15

    )


    score = round(
        score
    )


    # Güvenli sınır

    score = max(
        0,
        min(
            100,
            score
        )
    )


    return score


# ============================================================
# SİNYAL
# ============================================================

def get_signal(score):

    if score >= 90:

        return "🚀 ÇOK GÜÇLÜ AL"

    elif score >= 75:

        return "🔥 GÜÇLÜ AL"

    elif score >= 60:

        return "🟢 AL"

    elif score >= 50:

        return "🟡 TUT"

    elif score >= 35:

        return "🟠 ZAYIF"

    elif score >= 20:

        return "🔴 SAT"

    else:

        return "🔴 ÇOK GÜÇLÜ SAT"


# ============================================================
# TEKNİK ANALİZ
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


    try:

        close = data["Close"].dropna()


        if len(close) < 50:

            return None


        price = safe_float(
            close.iloc[-1]
        )

        previous = safe_float(
            close.iloc[-2]
        )


        if previous == 0:

            return None


        daily_change = (
            (price - previous)
            / previous
            * 100
        )


        # EMA

        ema20 = safe_float(
            calculate_ema(
                close,
                20
            ).iloc[-1]
        )

        ema50 = safe_float(
            calculate_ema(
                close,
                50
            ).iloc[-1]
        )


        # RSI

        rsi_series = calculate_rsi(
            close
        )

        rsi = safe_float(
            rsi_series.iloc[-1],
            50
        )


        # MACD

        macd_series, signal_series, histogram_series = (
            calculate_macd(
                close
            )
        )


        macd = safe_float(
            macd_series.iloc[-1]
        )

        macd_signal = safe_float(
            signal_series.iloc[-1]
        )

        histogram = safe_float(
            histogram_series.iloc[-1]
        )


        # Bollinger

        bb_middle_series, bb_upper_series, bb_lower_series = (
            calculate_bollinger(
                close
            )
        )


        bb_middle = safe_float(
            bb_middle_series.iloc[-1]
        )

        bb_upper = safe_float(
            bb_upper_series.iloc[-1]
        )

        bb_lower = safe_float(
            bb_lower_series.iloc[-1]
        )


        # ====================================================
        # TREND
        # ====================================================

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


        # ====================================================
        # V4 SKOR
        # ====================================================

        score = calculate_anka_score(

            price=price,

            ema20=ema20,

            ema50=ema50,

            rsi=rsi,

            macd=macd,

            macd_signal=macd_signal,

            histogram=histogram,

            bb_middle=bb_middle,

            daily_change=daily_change

        )


        signal = get_signal(
            score
        )


        # ====================================================
        # DEĞERLENDİRMELER
        # ====================================================

        reasons = []


        if price > ema20:

            reasons.append(
                "• Fiyat EMA20 üzerinde"
            )

        else:

            reasons.append(
                "• Fiyat EMA20 altında"
            )


        if ema20 > ema50:

            reasons.append(
                "• EMA20, EMA50 üzerinde"
            )

        else:

            reasons.append(
                "• EMA20, EMA50 altında"
            )


        if rsi >= 70:

            reasons.append(
                "• RSI yüksek / aşırı alım bölgesi"
            )

        elif rsi >= 50:

            reasons.append(
                "• RSI pozitif bölgede"
            )

        elif rsi >= 40:

            reasons.append(
                "• RSI zayıf bölgede"
            )

        else:

            reasons.append(
                "• RSI aşırı zayıf bölgede"
            )


        if macd > macd_signal:

            reasons.append(
                "• MACD pozitif"
            )

        else:

            reasons.append(
                "• MACD negatif"
            )


        if histogram > 0:

            reasons.append(
                "• MACD histogram pozitif"
            )

        else:

            reasons.append(
                "• MACD histogram negatif"
            )


        if price > bb_middle:

            reasons.append(
                "• Fiyat Bollinger orta bandının üzerinde"
            )

        else:

            reasons.append(
                "• Fiyat Bollinger orta bandının altında"
            )


        return {

            "price": price,

            "daily_change": daily_change,

            "ema20": ema20,

            "ema50": ema50,

            "rsi": rsi,

            "macd": macd,

            "macd_signal": macd_signal,

            "histogram": histogram,

            "bb_upper": bb_upper,

            "bb_middle": bb_middle,

            "bb_lower": bb_lower,

            "trend": trend,

            "score": score,

            "signal": signal,

            "reasons": reasons

        }


    except Exception as e:

        logger.error(
            "Teknik analiz hatası %s: %s",
            symbol,
            e
        )

        return None


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
/fiyat USDTRY
/fiyat BTC

/analiz THYAO
/analiz ALTIN
/analiz GUMUS
/analiz BAKIR

/metaller

/firsatlar

/test

━━━━━━━━━━━━━━━━━━

🚀 ANKA TEKNİK ANALİZ V4

EMA20 • EMA50
RSI • MACD
Bollinger • Momentum

⭐ 0–100 ANKA SKORU
"""

    await update.message.reply_text(
        mesaj
    )


# ============================================================
# ANKA
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
# FİYAT
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
            "/fiyat GUMUS\n"
            "/fiyat BAKIR\n"
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

        close = data["Close"].dropna()


        if len(close) < 2:

            await update.message.reply_text(
                "❌ Yeterli veri yok."
            )

            return


        price = safe_float(
            close.iloc[-1]
        )

        previous = safe_float(
            close.iloc[-2]
        )


        if previous == 0:

            change = 0

        else:

            change = (
                (price - previous)
                / previous
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

            f"📊 {asset}\n\n"

            f"💰 Fiyat: "
            f"{price:.4f}\n\n"

            f"{direction} Günlük değişim: "
            f"{change:+.2f}%\n\n"

            f"━━━━━━━━━━━━━━━━\n\n"

            f"📌 Veri kaynağı: "
            f"Yahoo Finance\n\n"

            f"⚠️ Bu aşamada yalnızca "
            f"fiyat verisi gösterilmektedir."

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
            "❌ Fiyat alınırken hata oluştu."
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


    reasons = "\n".join(
        result["reasons"]
    )


    mesaj = (

        f"🦅 ANKA YATIRIM ANALİZ\n\n"

        f"📊 {asset}\n\n"

        f"{info['name']}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"🧠 ANKA TEKNİK ANALİZ V4\n\n"

        f"💰 Fiyat: "
        f"{result['price']:.4f}\n\n"

        f"📐 EMA20: "
        f"{result['ema20']:.4f}\n\n"

        f"📐 EMA50: "
        f"{result['ema50']:.4f}\n\n"

        f"📊 RSI(14): "
        f"{result['rsi']:.2f}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"📈 MACD\n\n"

        f"MACD: "
        f"{result['macd']:.4f}\n"

        f"Signal: "
        f"{result['macd_signal']:.4f}\n"

        f"Histogram: "
        f"{result['histogram']:.4f}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"📊 BOLLINGER BANDI\n\n"

        f"Üst: "
        f"{result['bb_upper']:.4f}\n"

        f"Orta: "
        f"{result['bb_middle']:.4f}\n"

        f"Alt: "
        f"{result['bb_lower']:.4f}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"📈 Trend:\n\n"

        f"{result['trend']}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"⭐ ANKA SKORU:\n\n"

        f"🔥 {result['score']}/100\n\n"

        f"🤖 SİNYAL:\n\n"

        f"{result['signal']}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"🔍 GÖSTERGE DEĞERLENDİRMESİ\n\n"

        f"{reasons}\n\n"

        f"━━━━━━━━━━━━━━━━\n\n"

        f"⚠️ Bu sistem yatırım tavsiyesi değildir. "
        f"Teknik göstergelere dayalı otomatik analizdir."

    )


    await update.message.reply_text(
        mesaj
    )


# ============================================================
# METALLER
# ============================================================

async def metaller(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🥇🥈🟠 Altın-Gümüş-Bakır analiz ediliyor..."
    )


    metal_list = [
        ("ALTIN", "🥇"),
        ("GUMUS", "🥈"),
        ("BAKIR", "🟠")
    ]


    reports = []


    for asset, emoji in metal_list:

        info = ASSETS[asset]

        result = technical_analysis(
            info["symbol"]
        )


        if result is None:

            reports.append(
                f"{emoji} {asset}\n"
                f"❌ Veri alınamadı."
            )

            continue


        reports.append(

            f"{emoji} {asset}\n\n"

            f"💰 Fiyat: "
            f"{result['price']:.4f}\n"

            f"📈 Günlük: "
            f"{result['daily_change']:+.2f}%\n"

            f"📊 RSI: "
            f"{result['rsi']:.2f}\n"

            f"📈 Trend: "
            f"{result['trend']}\n"

            f"⭐ Skor: "
            f"{result['score']}/100\n"

            f"🤖 {result['signal']}"

        )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        "🔥 ÜÇLÜ METAL ANALİZİ\n\n"

        +
        "\n\n━━━━━━━━━━━━━━━━\n\n".join(
            reports
        )

        +

        "\n\n⚠️ Teknik göstergelere dayalı "
        "otomatik analizdir."

    )


    await update.message.reply_text(
        mesaj
    )


# ============================================================
# FIRSATLAR
# ============================================================

async def firsatlar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔥 Anka fırsat taraması başladı..."
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
            "❌ Fırsat taraması için veri bulunamadı."
        )

        return


    reports = []


    for index, (
        score,
        asset,
        result
    ) in enumerate(
        top,
        1
    ):

        reports.append(

            f"{index}. {asset}\n"

            f"⭐ {score}/100\n"

            f"{result['signal']}\n"

            f"{result['trend']}"

        )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        "🔥 EN YÜKSEK SKORLU VARLIKLAR\n\n"

        +
        "\n\n".join(
            reports
        )

        +

        "\n\n━━━━━━━━━━━━━━━━\n\n"

        "⚠️ Bu sıralama teknik göstergelere "
        "göre oluşturulmuştur."

    )


    await update.message.reply_text(
        mesaj
    )


# ============================================================
# TAKİP
# ============================================================

async def takip(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Kullanım:\n\n"
            "/takip THYAO\n"
            "/takip ALTIN\n"
            "/takip GUMUS"
        )

        return


    asset = context.args[0].upper()


    if asset not in ASSETS:

        await update.message.reply_text(
            "❌ Böyle bir varlık yok."
        )

        return


    WATCHLIST.add(
        asset
    )


    await update.message.reply_text(

        f"✅ {asset} takip listesine eklendi.\n\n"

        f"🦅 Anka artık {asset} için "
        f"teknik hareketleri takip edecek."

    )


# ============================================================
# TAKİPLERİM
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
        f"• {asset}"
        for asset in WATCHLIST
    )


    await update.message.reply_text(

        "🦅 ANKA TAKİP LİSTESİ\n\n"
        +
        liste

    )


# ============================================================
# HAKKINDA
# ============================================================

async def hakkinda(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mesaj = """
🦅 ANKA YATIRIM ANALİZ

Teknik göstergeleri kullanarak
finansal varlıkları analiz eder.

📊 BIST
🇺🇸 ABD
🥇 Altın
🥈 Gümüş
🟠 Bakır
💵 Döviz
₿ Kripto

🧠 ANKA V4

EMA20
EMA50
RSI
MACD
Bollinger
Momentum

⭐ 0–100 ANKA SKORU

⚠️ Yatırım tavsiyesi değildir.
"""

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
        "🦅 ANKA YATIRIM ANALİZ V4 BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == "__main__":

    main()
