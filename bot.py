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
# 🦅 ANKA YATIRIM ANALİZ
# STABİL TEKNİK ANALİZ MOTORU
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

def get_data(symbol, period="1y", interval="1d"):

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
            logger.error("%s için veri boş.", symbol)
            return None

        # ----------------------------------------------------
        # MultiIndex güvenliği
        # ----------------------------------------------------

        if isinstance(data.columns, pd.MultiIndex):

            data.columns = data.columns.get_level_values(0)

        # ----------------------------------------------------
        # Gerekli kolonlar
        # ----------------------------------------------------

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for column in required_columns:

            if column not in data.columns:

                logger.error(
                    "%s için %s sütunu bulunamadı.",
                    symbol,
                    column
                )

                return None

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

        data = data.dropna(
            subset=["Close"]
        )

        if data.empty:
            return None

        return data

    except Exception as e:

        logger.exception(
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
# STOCHASTIC
# ============================================================

def calculate_stochastic(
    data,
    period=14,
    smooth=3
):

    high = data["High"]

    low = data["Low"]

    close = data["Close"]

    lowest_low = low.rolling(
        period
    ).min()

    highest_high = high.rolling(
        period
    ).max()

    denominator = (
        highest_high - lowest_low
    )

    denominator = denominator.replace(
        0,
        pd.NA
    )

    k = (
        (close - lowest_low)
        / denominator
        * 100
    )

    d = k.rolling(
        smooth
    ).mean()

    return (
        k,
        d
    )


# ============================================================
# ATR
# ============================================================

def calculate_atr(
    data,
    period=14
):

    high = data["High"]

    low = data["Low"]

    close = data["Close"]

    previous_close = close.shift(1)

    tr1 = high - low

    tr2 = (
        high - previous_close
    ).abs()

    tr3 = (
        low - previous_close
    ).abs()

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(
        axis=1
    )

    atr = true_range.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    return atr


# ============================================================
# HACİM ORANI
# ============================================================

def calculate_volume_ratio(
    data,
    period=20
):

    volume = pd.to_numeric(
        data["Volume"],
        errors="coerce"
    )

    average_volume = volume.rolling(
        period
    ).mean()

    current_volume = volume.iloc[-1]

    average = average_volume.iloc[-1]

    if pd.isna(average) or average == 0:

        return 1.0

    return float(
        current_volume / average
    )


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(
    data
):

    recent = data.tail(60)

    if len(recent) < 10:

        return None, None

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

    if len(high) < 10 or len(low) < 10:

        return None, None

    current = float(
        close.iloc[-1]
    )

    # --------------------------------------------------------
    # Fiyatın altında kalan en yakın destek
    # --------------------------------------------------------

    lows = sorted(
        set(
            round(float(x), 4)
            for x in low
            if float(x) < current
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # Fiyatın üstünde kalan en yakın direnç
    # --------------------------------------------------------

    highs = sorted(
        set(
            round(float(x), 4)
            for x in high
            if float(x) > current
        )
    )

    support = (
        lows[0]
        if lows
        else float(low.min())
    )

    resistance = (
        highs[0]
        if highs
        else float(high.max())
    )

    return (
        support,
        resistance
    )


# ============================================================
# 🧠 ANKA SKOR MOTORU
#
# TOPLAM = 100 PUAN
#
# EMA20       15
# EMA50       15
# RSI         15
# MACD        15
# Histogram   10
# Bollinger   10
# Stochastic  10
# Destek      10
#
# Toplam      100
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
    stoch_k,
    stoch_d,
    support,
    resistance
):

    score = 0

    reasons = []

    # ========================================================
    # 1 — FİYAT / EMA20
    # 15 PUAN
    # ========================================================

    if price > ema20:

        score += 15

        reasons.append(
            "• Fiyat EMA20 üzerinde"
        )

    else:

        reasons.append(
            "• Fiyat EMA20 altında"
        )


    # ========================================================
    # 2 — EMA20 / EMA50
    # 15 PUAN
    # ========================================================

    if ema20 > ema50:

        score += 15

        reasons.append(
            "• EMA20, EMA50 üzerinde"
        )

    else:

        reasons.append(
            "• EMA20, EMA50 altında"
        )


    # ========================================================
    # 3 — RSI
    # 15 PUAN
    # ========================================================

    if 55 <= rsi <= 65:

        score += 15

        reasons.append(
            "• RSI güçlü pozitif bölgede"
        )

    elif 50 <= rsi < 55:

        score += 11

        reasons.append(
            "• RSI pozitif bölgede"
        )

    elif 40 <= rsi < 50:

        score += 6

        reasons.append(
            "• RSI hafif zayıf"
        )

    elif 30 <= rsi < 40:

        score += 3

        reasons.append(
            "• RSI zayıf bölgede"
        )

    elif rsi > 65:

        score += 10

        reasons.append(
            "• RSI yüksek / aşırı alım bölgesi"
        )

    else:

        score += 5

        reasons.append(
            "• RSI aşırı satım bölgesinde"
        )


    # ========================================================
    # 4 — MACD
    # 15 PUAN
    # ========================================================

    if macd > signal and macd > 0:

        score += 15

        reasons.append(
            "• MACD pozitif"
        )

    elif macd > signal:

        score += 10

        reasons.append(
            "• MACD Signal üzerinde"
        )

    elif macd < signal and macd < 0:

        reasons.append(
            "• MACD Signal altında"
        )

    else:

        score += 4

        reasons.append(
            "• MACD zayıf"
        )


    # ========================================================
    # 5 — MACD HISTOGRAM
    # 10 PUAN
    # ========================================================

    if histogram > 0:

        score += 10

        reasons.append(
            "• MACD histogram pozitif"
        )

    else:

        reasons.append(
            "• MACD histogram negatif"
        )


    # ========================================================
    # 6 — BOLLINGER
    # 10 PUAN
    # ========================================================

    if price > bb_middle:

        score += 10

        reasons.append(
            "• Fiyat Bollinger orta bandının üzerinde"
        )

    else:

        reasons.append(
            "• Fiyat Bollinger orta bandının altında"
        )


    # ========================================================
    # 7 — STOCHASTIC
    # 10 PUAN
    # ========================================================

    if stoch_k > stoch_d:

        score += 10

        reasons.append(
            "• Stochastic pozitif"
        )

    else:

        reasons.append(
            "• Stochastic negatif"
        )


    # ========================================================
    # 8 — DESTEK / DİRENÇ
    # 10 PUAN
    # ========================================================

    if (
        support is not None
        and resistance is not None
        and resistance > support
    ):

        distance_to_support = abs(
            price - support
        )

        distance_to_resistance = abs(
            resistance - price
        )

        total_range = (
            resistance - support
        )

        # Desteğe çok yakınsa
        if (
            distance_to_support
            <= total_range * 0.15
        ):

            score += 10

            reasons.append(
                "• Fiyat destek bölgesine yakın"
            )

        # Dirence çok yakınsa
        elif (
            distance_to_resistance
            <= total_range * 0.15
        ):

            score += 5

            reasons.append(
                "• Fiyat direnç bölgesine yakın"
            )

        else:

            score += 3

            reasons.append(
                "• Fiyat destek/direnç arasında"
            )

    else:

        score += 3

        reasons.append(
            "• Destek/direnç hesaplandı"
        )


    # ========================================================
    # SKOR SINIRLAMA
    # ========================================================

    score = max(
        0,
        min(
            100,
            score
        )
    )

    return (
        int(score),
        reasons
    )


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    price,
    ema20,
    ema50
):

    if (
        price > ema20
        and ema20 > ema50
    ):

        return "📈 GÜÇLÜ YÜKSELİŞ"

    elif price > ema20:

        return "📈 YÜKSELİŞ"

    elif (
        price < ema20
        and ema20 < ema50
    ):

        return "📉 GÜÇLÜ DÜŞÜŞ"

    elif price < ema20:

        return "📉 DÜŞÜŞ"

    return "➡️ YATAY"


# ============================================================
# SİNYAL
# ============================================================

def calculate_signal(score):

    if score >= 80:

        return "🔥 GÜÇLÜ AL"

    elif score >= 65:

        return "🟢 AL"

    elif score >= 45:

        return "🟡 TUT"

    elif score >= 30:

        return "🟠 ZAYIF"

    return "🔴 SAT"


# ============================================================
# KIRILIM
# ============================================================

def calculate_breakout(
    price,
    support,
    resistance
):

    if resistance is not None:

        if price > resistance:

            return "🚀 DİRENÇ KIRILDI"

    if support is not None:

        if price < support:

            return "🚨 DESTEK KIRILDI"

    return "➡️ Kırılım yok"


# ============================================================
# TEKNİK ANALİZ
# ============================================================

def technical_analysis(
    symbol
):

    data = get_data(
        symbol,
        period="1y",
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
                "%s için yeterli veri yok: %s",
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

        rsi_clean = (
            rsi_series
            .dropna()
        )

        if rsi_clean.empty:

            return None

        rsi = float(
            rsi_clean.iloc[-1]
        )


        # ====================================================
        # MACD
        # ====================================================

        (
            macd_series,
            signal_series,
            histogram_series
        ) = calculate_macd(
            close
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


        # ====================================================
        # BOLLINGER
        # ====================================================

        (
            bb_middle_series,
            bb_upper_series,
            bb_lower_series
        ) = calculate_bollinger(
            close,
            20
        )

        bb_middle_clean = (
            bb_middle_series
            .dropna()
        )

        bb_upper_clean = (
            bb_upper_series
            .dropna()
        )

        bb_lower_clean = (
            bb_lower_series
            .dropna()
        )

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


        # ====================================================
        # STOCHASTIC
        # ====================================================

        stoch_k_series, stoch_d_series = (
            calculate_stochastic(
                data,
                14,
                3
            )
        )

        stoch_k_clean = (
            stoch_k_series
            .dropna()
        )

        stoch_d_clean = (
            stoch_d_series
            .dropna()
        )

        if (
            stoch_k_clean.empty
            or stoch_d_clean.empty
        ):

            return None

        stoch_k = float(
            stoch_k_clean.iloc[-1]
        )

        stoch_d = float(
            stoch_d_clean.iloc[-1]
        )


        # ====================================================
        # ATR
        # ====================================================

        atr_series = calculate_atr(
            data,
            14
        )

        atr_clean = (
            atr_series
            .dropna()
        )

        if atr_clean.empty:

            atr = 0.0

        else:

            atr = float(
                atr_clean.iloc[-1]
            )


        # ====================================================
        # HACİM
        # ====================================================

        volume_ratio = (
            calculate_volume_ratio(
                data,
                20
            )
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

            signal=macd_signal,

            histogram=histogram,

            bb_middle=bb_middle,

            stoch_k=stoch_k,

            stoch_d=stoch_d,

            support=support,

            resistance=resistance
        )


        # ====================================================
        # TREND
        # ====================================================

        trend = calculate_trend(
            price,
            ema20,
            ema50
        )


        # ====================================================
        # SİNYAL
        # ====================================================

        signal_text = calculate_signal(
            score
        )


        # ====================================================
        # KIRILIM
        # ====================================================

        breakout = calculate_breakout(
            price,
            support,
            resistance
        )


        # ====================================================
        # RSI DURUMU
        # ====================================================

        if rsi >= 70:

            rsi_status = "🔴 Aşırı alım"

        elif rsi >= 55:

            rsi_status = "🟢 Güçlü"

        elif rsi >= 50:

            rsi_status = "🟢 Pozitif"

        elif rsi >= 40:

            rsi_status = "🟡 Hafif zayıf"

        elif rsi >= 30:

            rsi_status = "🟠 Zayıf"

        else:

            rsi_status = "🔵 Aşırı satım"


        # ====================================================
        # MACD DURUMU
        # ====================================================

        if (
            macd > macd_signal
            and macd > 0
        ):

            macd_status = "🟢 Pozitif"

        elif macd > macd_signal:

            macd_status = "🟢 Signal üzerinde"

        else:

            macd_status = "🔴 Negatif"


        # ====================================================
        # BOLLINGER DURUMU
        # ====================================================

        if price > bb_upper:

            bb_status = "🔴 Üst bandın üzerinde"

        elif price > bb_middle:

            bb_status = "🟢 Orta bandın üzerinde"

        elif price > bb_lower:

            bb_status = "🟡 Orta bandın altında"

        else:

            bb_status = "🔵 Alt bandın altında"


        # ====================================================
        # STOCHASTIC DURUMU
        # ====================================================

        if stoch_k > stoch_d:

            stoch_status = "🟢 Pozitif"

        else:

            stoch_status = "🔴 Negatif"


        return {

            "price": price,

            "ema20": ema20,

            "ema50": ema50,

            "rsi": rsi,

            "rsi_status": rsi_status,

            "macd": macd,

            "macd_signal": macd_signal,

            "histogram": histogram,

            "macd_status": macd_status,

            "bb_upper": bb_upper,

            "bb_middle": bb_middle,

            "bb_lower": bb_lower,

            "bb_status": bb_status,

            "stoch_k": stoch_k,

            "stoch_d": stoch_d,

            "stoch_status": stoch_status,

            "atr": atr,

            "volume_ratio": volume_ratio,

            "support": support,

            "resistance": resistance,

            "breakout": breakout,

            "trend": trend,

            "score": score,

            "signal_text": signal_text,

            "reasons": reasons
        }


    except Exception as e:

        logger.exception(
            "Teknik analiz hatası %s",
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

/takip THYAO
/takiplerim

/test

/hakkinda

━━━━━━━━━━━━━━━━━━

🧠 ANKA TEKNİK ANALİZ

EMA20 • EMA50
RSI • MACD
Bollinger
Stochastic
ATR
Hacim
Destek / Direnç
Anka Skoru

⭐ Anka Skoru: 0-100

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
            (
                current - previous
            )
            / previous
            * 100
        ) if previous != 0 else 0


        high = (
            float(
                data["High"]
                .dropna()
                .iloc[-1]
            )
            if "High" in data.columns
            else current
        )


        low = (
            float(
                data["Low"]
                .dropna()
                .iloc[-1]
            )
            if "Low" in data.columns
            else current
        )


        direction = (

            "🟢"
            if change > 0

            else "🔴"
            if change < 0

            else "🟡"
        )


        mesaj = (

            "🦅 ANKA YATIRIM ANALİZ\n\n"

            f"📊 {asset}\n\n"

            f"{info['name']}\n\n"

            "━━━━━━━━━━━━━━━━\n\n"

            f"💰 Fiyat: "
            f"{current:.4f}\n\n"

            f"{direction} Günlük değişim: "
            f"{change:+.2f}%\n\n"

            f"🔺 Gün içi yüksek: "
            f"{high:.4f}\n\n"

            f"🔻 Gün içi düşük: "
            f"{low:.4f}\n\n"

            "━━━━━━━━━━━━━━━━\n\n"

            "📌 Veri kaynağı: Yahoo Finance\n\n"

            f"🧠 Teknik analiz:\n"
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
            "/analiz BAKIR\n"
            "/analiz BTC"
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
        result["reasons"]
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

        "🧠 ANKA TEKNİK ANALİZ\n\n"

        f"💰 Fiyat: "
        f"{result['price']:.4f}\n\n"

        f"📐 EMA20: "
        f"{result['ema20']:.4f}\n\n"

        f"📐 EMA50: "
        f"{result['ema50']:.4f}\n\n"

        f"📊 RSI(14): "
        f"{result['rsi']:.2f}\n"

        f"{result['rsi_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📈 MACD\n\n"

        f"MACD: "
        f"{result['macd']:.4f}\n"

        f"Signal: "
        f"{result['macd_signal']:.4f}\n"

        f"Histogram: "
        f"{result['histogram']:.4f}\n"

        f"Durum: "
        f"{result['macd_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 BOLLINGER BANDI\n\n"

        f"Üst: "
        f"{result['bb_upper']:.4f}\n"

        f"Orta: "
        f"{result['bb_middle']:.4f}\n"

        f"Alt: "
        f"{result['bb_lower']:.4f}\n"

        f"Durum: "
        f"{result['bb_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📉 STOCHASTIC\n\n"

        f"%K: "
        f"{result['stoch_k']:.2f}\n"

        f"%D: "
        f"{result['stoch_d']:.2f}\n"

        f"Durum: "
        f"{result['stoch_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 VOLATİLİTE / HACİM\n\n"

        f"ATR(14): "
        f"{result['atr']:.4f}\n\n"

        f"Hacim / Ortalama: "
        f"{result['volume_ratio']:.2f}x\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🎯 DESTEK / DİRENÇ\n\n"

        f"🟢 Destek: "
        f"{support_text}\n"

        f"🔴 Direnç: "
        f"{resistance_text}\n\n"

        "🚨 Durum:\n\n"

        f"{result['breakout']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📈 TREND\n\n"

        f"{result['trend']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "⭐ ANKA SKORU\n\n"

        f"{result['score']}/100\n\n"

        "🤖 SİNYAL\n\n"

        f"{result['signal_text']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🔍 GÖSTERGE DEĞERLENDİRMESİ\n\n"

        f"{reasons_text}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📌 Veri kaynağı: Yahoo Finance\n\n"

        "⚠️ Bu sistem yatırım tavsiyesi değildir.\n\n"

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

        + "\n\n━━━━━━━━━━━━━━━━\n\n".join(
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

        + "\n\n━━━━━━━━━━━━━━\n\n".join(
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

        "Otomatik teknik piyasa analiz botu.\n\n"

        "🧠 ANALİZ MOTORU\n\n"

        "EMA20\n"
        "EMA50\n"
        "RSI(14)\n"
        "MACD\n"
        "Bollinger Bandı\n"
        "Stochastic\n"
        "ATR\n"
        "Hacim\n"
        "Destek / Direnç\n\n"

        "⭐ ANKA SKORU: 0-100\n\n"

        "Skor sistemi sabit ağırlıklı olarak "
        "hesaplanmaktadır.\n\n"

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


    # ========================================================
    # KOMUTLAR
    # ========================================================

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
        "🦅 ANKA YATIRIM ANALİZ BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
