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
# VERİ ÇEKME
# yfinance yeni MultiIndex yapısına uyumlu
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

        # ----------------------------------------------------
        # Güvenlik: MultiIndex gelirse düzleştir
        # ----------------------------------------------------

        if isinstance(data.columns, pd.MultiIndex):

            data.columns = data.columns.get_level_values(0)

        # ----------------------------------------------------
        # Gerekli sütun var mı?
        # ----------------------------------------------------

        if "Close" not in data.columns:

            logger.error(
                "%s için Close sütunu bulunamadı.",
                symbol
            )

            return None

        # ----------------------------------------------------
        # Close kesinlikle Series olsun
        # ----------------------------------------------------

        close = data["Close"]

        if isinstance(close, pd.DataFrame):

            close = close.iloc[:, 0]

        close = pd.to_numeric(
            close,
            errors="coerce"
        )

        data["Close"] = close

        # NaN temizle

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

def calculate_support_resistance(
    data
):

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

    # Son 20 günlük en yüksek/en düşük

    resistance = float(
        high.max()
    )

    support = float(
        low.min()
    )

    # Fiyatın hemen üstündeki direnç
    # için son yüksek değerlerden daha
    # anlamlı bir seviye seçmeye çalış

    previous_highs = sorted(
        set(
            float(x)
            for x in high
            if float(x) > current
        )
    )

    if previous_highs:

        resistance = previous_highs[0]

    # Fiyatın altındaki destek

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

    return (
        support,
        resistance
    )


# ============================================================
# 🧠 ANKA SKOR MOTORU V4
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

    score = 50

    reasons = []


    # ========================================================
    # 1 — EMA20
    # ========================================================

    if price > ema20:

        score += 10

        reasons.append(
            "Fiyat EMA20 üzerinde"
        )

    else:

        score -= 10

        reasons.append(
            "Fiyat EMA20 altında"
        )


    # ========================================================
    # 2 — EMA20 / EMA50 TREND
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

    if 50 <= rsi < 60:

        score += 5

        reasons.append(
            "RSI pozitif bölgede"
        )

    elif 60 <= rsi <= 70:

        score += 8

        reasons.append(
            "RSI güçlü bölgede"
        )

    elif rsi > 70:

        # Aşırı alım tamamen negatif değildir.
        # Trend güçlü ise puanı sadece biraz azaltıyoruz.

        score += 2

        reasons.append(
            "RSI yüksek / aşırı alım bölgesi"
        )

    elif 40 <= rsi < 50:

        score -= 3

        reasons.append(
            "RSI zayıf bölgede"
        )

    elif 30 <= rsi < 40:

        score -= 6

        reasons.append(
            "RSI düşük bölgede"
        )

    else:

        score -= 3

        reasons.append(
            "RSI aşırı satım bölgesinde"
        )


    # ========================================================
    # 4 — MACD
    # ========================================================

    if macd > signal:

        score += 8

        reasons.append(
            "MACD pozitif"
        )

    else:

        score -= 8

        reasons.append(
            "MACD negatif"
        )


    # ========================================================
    # 5 — MACD HISTOGRAM
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
    # 6 — BOLLINGER
    # ========================================================

    if price > bb_middle:

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
    # 7 — DESTEK / DİRENÇ
    # ========================================================

    if support is not None and resistance is not None:

        range_value = resistance - support

        if range_value > 0:

            position = (
                price - support
            ) / range_value

            # Desteğe yakın
            if position < 0.25:

                score += 3

                reasons.append(
                    "Fiyat desteğe yakın"
                )

            # Dirence yakın
            elif position > 0.75:

                score += 1

                reasons.append(
                    "Fiyat dirence yakın"
                )


    # ========================================================
    # SINIRLAMA
    # ========================================================

    score = max(
        0,
        min(
            100,
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

        close = pd.to_numeric(
            data["Close"],
            errors="coerce"
        ).dropna()

        if len(close) < 60:

            logger.warning(
                "%s için yeterli veri yok. "
                "Veri sayısı: %s",
                symbol,
                len(close)
            )

            return None


        # ====================================================
        # FİYAT
        # ====================================================

        price = float(
            close.iloc[-1]
        )


        # ====================================================
        # EMA
        # ====================================================

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


        # ====================================================
        # RSI
        # ====================================================

        rsi_series = calculate_rsi(
            close,
            14
        )

        rsi = float(
            rsi_series.dropna().iloc[-1]
        )


        # ====================================================
        # MACD
        # ====================================================

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


        # ====================================================
        # BOLLINGER
        # ====================================================

        bb_middle_series, bb_upper_series, bb_lower_series = (
            calculate_bollinger(close)
        )

        bb_middle = float(
            bb_middle_series.dropna().iloc[-1]
        )

        bb_upper = float(
            bb_upper_series.dropna().iloc[-1]
        )

        bb_lower = float(
            bb_lower_series.dropna().iloc[-1]
        )


        # ====================================================
        # DESTEK / DİRENÇ
        # ====================================================

        support, resistance = (
            calculate_support_resistance(
                data
            )
        )


        # ====================================================
        # SKOR
        # ====================================================

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

        elif price < ema20:

            trend = "📉 DÜŞÜŞ"

        else:

            trend = "➡️ YATAY"


        # ====================================================
        # SİNYAL
        # ====================================================

        if score >= 80:

            signal_text = "🔥 GÜÇLÜ AL"

        elif score >= 65:

            signal_text = "🟢 AL"

        elif score >= 45:

            signal_text = "🟡 TUT"

        elif score >= 30:

            signal_text = "🟠 ZAYIF"

        else:

            signal_text = "🔴 SAT"


        # ====================================================
        # KIRILIM
        # ====================================================

        breakout = "➡️ Kırılım yok"


        if resistance is not None:

            if price > resistance:

                breakout = (
                    "🚀 DİRENÇ KIRILDI"
                )


        if support is not None:

            if price < support:

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
            "Teknik analiz hatası: %s",
            symbol
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

/test

━━━━━━━━━━━━━━━━━━

🧠 ANKA TEKNİK ANALİZ V4

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


        previous = float(
            close.iloc[-2]
        ) if len(close) > 1 else current


        change = (
            (current - previous)
            / previous
            * 100
        ) if previous != 0 else 0


        high = float(
            data["High"].dropna().iloc[-1]
        ) if "High" in data.columns else current


        low = float(
            data["Low"].dropna().iloc[-1]
        ) if "Low" in data.columns else current


        direction = (
            "🟢"
            if change > 0
            else
            "🔴"
            if change < 0
            else
            "🟡"
        )


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

        "🧠 ANKA TEKNİK ANALİZ V4\n\n"

        f"💰 Fiyat: "
        f"{result['price']:.4f}\n\n"

        f"📐 EMA20: "
        f"{result['ema20']:.4f}\n\n"

        f"📐 EMA50: "
        f"{result['ema50']:.4f}\n\n"

        f"📊 RSI(14): "
        f"{result['rsi']:.2f}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📈 MACD\n\n"

        f"MACD: "
        f"{result['macd']:.4f}\n"

        f"Signal: "
        f"{result['signal']:.4f}\n"

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

        "🚨 Durum:\n"

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

            f"💰 Fiyat: "
            f"{result['price']:.4f}\n"

            f"📈 Trend: "
            f"{result['trend']}\n"

            f"📊 RSI: "
            f"{result['rsi']:.2f}\n"

            f"⭐ Anka Skoru: "
            f"{result['score']}/100\n"

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

            f"{i}. {asset}\n"

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
        for x in WATCHLIST
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

        "🧠 V4 MOTORU\n\n"

        "EMA20\n"
        "EMA50\n"
        "RSI(14)\n"
        "MACD\n"
        "Bollinger Bandı\n"
        "Destek / Direnç\n\n"

        "⭐ Anka Skoru: 0-100\n\n"

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
        "🦅 ANKA YATIRIM ANALİZ V4 BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
