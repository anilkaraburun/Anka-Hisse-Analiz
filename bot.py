import os
import logging
import math

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
# FINAL TEKNİK ANALİZ MOTORU
# ============================================================

VERSION = "FINAL"

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

    # 🥇 EMTİA

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

    "MSFT": {
        "symbol": "MSFT",
        "name": "Microsoft"
    },

    "AMZN": {
        "symbol": "AMZN",
        "name": "Amazon"
    },

    "META": {
        "symbol": "META",
        "name": "Meta"
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
# YARDIMCI
# ============================================================

def safe_float(value, default=None):

    try:

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except Exception:

        return default


# ============================================================
# VERİ ÇEKME
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
            multi_level_index=False
        )

        if data is None or data.empty:

            logger.warning(
                "Boş veri: %s",
                symbol
            )

            return None


        # ----------------------------------------------------
        # MultiIndex düzeltme
        # ----------------------------------------------------

        if isinstance(
            data.columns,
            pd.MultiIndex
        ):

            data.columns = [
                column[0]
                if isinstance(column, tuple)
                else column
                for column in data.columns
            ]


        # ----------------------------------------------------
        # Gerekli sütunlar
        # ----------------------------------------------------

        required = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        for column in required:

            if column not in data.columns:

                logger.warning(
                    "%s sütunu yok: %s",
                    column,
                    symbol
                )

                return None


        # ----------------------------------------------------
        # Sayısal dönüşüm
        # ----------------------------------------------------

        for column in [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]:

            if column in data.columns:

                data[column] = pd.to_numeric(
                    data[column],
                    errors="coerce"
                )


        # ----------------------------------------------------
        # Close temizle
        # ----------------------------------------------------

        data = data.dropna(
            subset=[
                "Close",
                "High",
                "Low"
            ]
        )


        if data.empty:

            return None


        return data


    except Exception as e:

        logger.exception(
            "Veri alınamadı %s: %s",
            symbol
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
# STOCHASTIC
# ============================================================

def calculate_stochastic(
    data,
    period=14,
    smooth=3
):

    low_min = data["Low"].rolling(
        period
    ).min()

    high_max = data["High"].rolling(
        period
    ).max()

    denominator = (
        high_max - low_min
    ).replace(
        0,
        float("nan")
    )

    k = (
        (
            data["Close"] - low_min
        )
        / denominator
    ) * 100

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

    previous_close = data["Close"].shift(1)

    tr1 = (
        data["High"] - data["Low"]
    )

    tr2 = (
        data["High"] - previous_close
    ).abs()

    tr3 = (
        data["Low"] - previous_close
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
# HACİM
# ============================================================

def calculate_volume_ratio(
    data,
    period=20
):

    if "Volume" not in data.columns:

        return None

    volume = pd.to_numeric(
        data["Volume"],
        errors="coerce"
    )

    average = volume.rolling(
        period
    ).mean()

    if average.empty:

        return None

    current = safe_float(
        volume.iloc[-1]
    )

    avg = safe_float(
        average.iloc[-1]
    )

    if current is None or avg is None or avg == 0:

        return None

    return current / avg


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(
    data
):

    recent = data.tail(30).copy()

    if len(recent) < 10:

        return None, None


    current = safe_float(
        recent["Close"].iloc[-1]
    )

    if current is None:

        return None, None


    highs = pd.to_numeric(
        recent["High"],
        errors="coerce"
    ).dropna()

    lows = pd.to_numeric(
        recent["Low"],
        errors="coerce"
    ).dropna()


    # --------------------------------------------------------
    # Fiyatın altında kalan anlamlı dipler
    # --------------------------------------------------------

    supports = sorted(
        [
            float(x)
            for x in lows
            if float(x) < current
        ],
        reverse=True
    )


    # --------------------------------------------------------
    # Fiyatın üstünde kalan anlamlı tepeler
    # --------------------------------------------------------

    resistances = sorted(
        [
            float(x)
            for x in highs
            if float(x) > current
        ]
    )


    # --------------------------------------------------------
    # Destek
    # --------------------------------------------------------

    support = None

    if supports:

        support = supports[0]

    else:

        support = safe_float(
            lows.min()
        )


    # --------------------------------------------------------
    # Direnç
    # --------------------------------------------------------

    resistance = None

    if resistances:

        resistance = resistances[0]

    else:

        resistance = safe_float(
            highs.max()
        )


    # --------------------------------------------------------
    # Çok yakın / anlamsız seviyeleri filtrele
    # --------------------------------------------------------

    if support is not None:

        if support >= current:

            support = None


    if resistance is not None:

        if resistance <= current:

            resistance = None


    return (
        support,
        resistance
    )


# ============================================================
# SKOR MOTORU
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

    bb_upper,

    bb_lower,

    stochastic_k,

    stochastic_d,

    volume_ratio,

    support,

    resistance

):

    # ========================================================
    # BAŞLANGIÇ
    # ========================================================

    score = 50

    reasons = []


    # ========================================================
    # 1 - FİYAT / EMA20
    # Ağırlık: 12
    # ========================================================

    if price > ema20:

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
    # 2 - EMA20 / EMA50
    # Ağırlık: 12
    # ========================================================

    if ema20 > ema50:

        score += 12

        reasons.append(
            "EMA20, EMA50 üzerinde"
        )

    else:

        score -= 12

        reasons.append(
            "EMA20, EMA50 altında"
        )


    # ========================================================
    # 3 - RSI
    # Ağırlık: 12
    # ========================================================

    if rsi >= 70:

        score += 4

        reasons.append(
            "RSI yüksek / aşırı alım bölgesi"
        )

    elif rsi >= 60:

        score += 10

        reasons.append(
            "RSI güçlü bölgede"
        )

    elif rsi >= 50:

        score += 6

        reasons.append(
            "RSI pozitif bölgede"
        )

    elif rsi >= 40:

        score -= 3

        reasons.append(
            "RSI hafif zayıf"
        )

    elif rsi >= 30:

        score -= 7

        reasons.append(
            "RSI zayıf bölgede"
        )

    else:

        score -= 2

        reasons.append(
            "RSI aşırı satım bölgesinde"
        )


    # ========================================================
    # 4 - MACD
    # Ağırlık: 10
    # ========================================================

    if macd > macd_signal:

        score += 10

        reasons.append(
            "MACD Signal üzerinde"
        )

    else:

        score -= 10

        reasons.append(
            "MACD Signal altında"
        )


    # ========================================================
    # 5 - HISTOGRAM
    # Ağırlık: 5
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
    # 6 - BOLLINGER
    # Ağırlık: 8
    # ========================================================

    if price > bb_middle:

        score += 8

        reasons.append(
            "Fiyat Bollinger orta bandının üzerinde"
        )

    else:

        score -= 8

        reasons.append(
            "Fiyat Bollinger orta bandının altında"
        )


    # ========================================================
    # 7 - STOCHASTIC
    # Ağırlık: 5
    # ========================================================

    if stochastic_k > stochastic_d:

        score += 5

        reasons.append(
            "Stochastic pozitif"
        )

    else:

        score -= 3

        reasons.append(
            "Stochastic negatif"
        )


    # ========================================================
    # 8 - HACİM
    # Ağırlık: 3
    # ========================================================

    if volume_ratio is not None:

        if volume_ratio >= 1.5:

            score += 3

            reasons.append(
                "Hacim ortalamanın üzerinde"
            )

        elif volume_ratio >= 1.0:

            score += 1

        elif volume_ratio < 0.7:

            score -= 1

            reasons.append(
                "Hacim zayıf"
            )


    # ========================================================
    # 9 - DESTEK / DİRENÇ
    # Ağırlık: 5
    # ========================================================

    if (
        support is not None
        and resistance is not None
        and resistance > support
    ):

        total_range = (
            resistance - support
        )

        position = (
            price - support
        ) / total_range


        # Desteğe yakın
        if position <= 0.20:

            score += 5

            reasons.append(
                "Fiyat destek bölgesine yakın"
            )

        # Orta alan
        elif position <= 0.60:

            reasons.append(
                "Fiyat destek/direnç arasında"
            )

        # Dirence yakın
        elif position >= 0.80:

            score += 2

            reasons.append(
                "Fiyat direnç bölgesine yakın"
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


    return (
        int(round(score)),
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


    if (
        price > ema20
        and ema20 <= ema50
    ):

        return "📈 YÜKSELİŞ"


    if (
        price < ema20
        and ema20 < ema50
    ):

        return "📉 GÜÇLÜ DÜŞÜŞ"


    if price < ema20:

        return "📉 DÜŞÜŞ"


    return "➡️ YATAY"


# ============================================================
# SİNYAL
# ============================================================

def calculate_signal(
    score
):

    if score >= 80:

        return "🔥 GÜÇLÜ AL"

    elif score >= 65:

        return "🟢 AL"

    elif score >= 45:

        return "🟡 TUT"

    elif score >= 30:

        return "🟠 ZAYIF"

    else:

        return "🔴 SAT"


# ============================================================
# BREAKOUT
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
                "%s için yeterli veri yok: %s",
                symbol,
                len(close)
            )

            return None


        # ====================================================
        # FİYAT
        # ====================================================

        price = safe_float(
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


        ema20 = safe_float(
            ema20_series.iloc[-1]
        )

        ema50 = safe_float(
            ema50_series.iloc[-1]
        )


        # ====================================================
        # RSI
        # ====================================================

        rsi_series = calculate_rsi(
            close,
            14
        )

        rsi_clean = rsi_series.dropna()


        if rsi_clean.empty:

            return None


        rsi = safe_float(
            rsi_clean.iloc[-1]
        )


        # ====================================================
        # MACD
        # ====================================================

        macd_series, macd_signal_series, histogram_series = (
            calculate_macd(close)
        )


        macd = safe_float(
            macd_series.iloc[-1]
        )

        macd_signal = safe_float(
            macd_signal_series.iloc[-1]
        )

        histogram = safe_float(
            histogram_series.iloc[-1]
        )


        # ====================================================
        # BOLLINGER
        # ====================================================

        bb_middle_series, bb_upper_series, bb_lower_series = (
            calculate_bollinger(close)
        )


        bb_middle_clean = (
            bb_middle_series.dropna()
        )

        bb_upper_clean = (
            bb_upper_series.dropna()
        )

        bb_lower_clean = (
            bb_lower_series.dropna()
        )


        if (
            bb_middle_clean.empty
            or bb_upper_clean.empty
            or bb_lower_clean.empty
        ):

            return None


        bb_middle = safe_float(
            bb_middle_clean.iloc[-1]
        )

        bb_upper = safe_float(
            bb_upper_clean.iloc[-1]
        )

        bb_lower = safe_float(
            bb_lower_clean.iloc[-1]
        )


        # ====================================================
        # STOCHASTIC
        # ====================================================

        stochastic_k_series, stochastic_d_series = (
            calculate_stochastic(
                data
            )
        )


        stochastic_k_clean = (
            stochastic_k_series.dropna()
        )

        stochastic_d_clean = (
            stochastic_d_series.dropna()
        )


        if (
            stochastic_k_clean.empty
            or stochastic_d_clean.empty
        ):

            return None


        stochastic_k = safe_float(
            stochastic_k_clean.iloc[-1]
        )

        stochastic_d = safe_float(
            stochastic_d_clean.iloc[-1]
        )


        # ====================================================
        # ATR
        # ====================================================

        atr_series = calculate_atr(
            data,
            14
        )

        atr_clean = atr_series.dropna()


        if atr_clean.empty:

            return None


        atr = safe_float(
            atr_clean.iloc[-1]
        )


        # ====================================================
        # HACİM
        # ====================================================

        volume_ratio = calculate_volume_ratio(
            data,
            20
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

            macd_signal=macd_signal,

            histogram=histogram,

            bb_middle=bb_middle,

            bb_upper=bb_upper,

            bb_lower=bb_lower,

            stochastic_k=stochastic_k,

            stochastic_d=stochastic_d,

            volume_ratio=volume_ratio,

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
        # BREAKOUT
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

        elif rsi >= 60:

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

        if macd > macd_signal:

            macd_status = "🟢 Pozitif"

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

        if stochastic_k > stochastic_d:

            stochastic_status = "🟢 Pozitif"

        else:

            stochastic_status = "🔴 Negatif"


        # ====================================================
        # HACİM METNİ
        # ====================================================

        if volume_ratio is None:

            volume_text = "Hesaplanamadı"

        else:

            volume_text = (
                f"{volume_ratio:.2f}x"
            )


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

            "stochastic_k": stochastic_k,

            "stochastic_d": stochastic_d,

            "stochastic_status": stochastic_status,

            "atr": atr,

            "volume_ratio": volume_ratio,

            "volume_text": volume_text,

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
yeni nesil teknik analiz botu.

📊 PİYASALAR

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
/analiz BTC

/metaller

/firsatlar

/takip THYAO
/takiplerim

/hakkinda

/test

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

━━━━━━━━━━━━━━━━━━

⚠️ Bu sistem yatırım tavsiyesi değildir.
Teknik göstergelere dayalı otomatik analizdir.

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
        "🦅 Telegram bağlantısı başarılı.\n"
        "📊 Teknik analiz motoru aktif.\n"
        "⭐ Skor motoru aktif."

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


        current = safe_float(
            close.iloc[-1]
        )


        previous = (

            safe_float(
                close.iloc[-2]
            )

            if len(close) > 1

            else current

        )


        if (
            current is None
            or previous is None
        ):

            await update.message.reply_text(
                "❌ Fiyat hesaplanamadı."
            )

            return


        change = (

            (
                current - previous
            )
            / previous
            * 100

            if previous != 0

            else 0

        )


        high = safe_float(
            data["High"].iloc[-1]
        )


        low = safe_float(
            data["Low"].iloc[-1]
        )


        if high is None:

            high = current


        if low is None:

            low = current


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

        f"🔎 {asset} teknik olarak analiz ediliyor...\n"
        "📊 Göstergeler hesaplanıyor..."

    )


    result = technical_analysis(
        info["symbol"]
    )


    if result is None:

        await update.message.reply_text(

            "❌ Teknik analiz için yeterli "
            "veri alınamadı.\n\n"
            "Yahoo Finance verisi geçici olarak "
            "ulaşılamıyor olabilir."

        )

        return


    reasons_text = "\n".join(

        f"• {reason}"

        for reason in result["reasons"]

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
        f"{result['bb_lower']:.4f}\n\n"

        f"Durum: "
        f"{result['bb_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📉 STOCHASTIC\n\n"

        f"%K: "
        f"{result['stochastic_k']:.2f}\n"

        f"%D: "
        f"{result['stochastic_d']:.2f}\n"

        f"Durum: "
        f"{result['stochastic_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 VOLATİLİTE / HACİM\n\n"

        f"ATR(14): "
        f"{result['atr']:.4f}\n\n"

        f"Hacim / Ortalama: "
        f"{result['volume_text']}\n\n"

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
        "🥇🥈🟠 Metal piyasaları analiz ediliyor..."
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

        "🔥 METAL RAPORU\n\n"

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

        "🔥 Anka fırsat taraması yapıyor...\n\n"
        "📊 Tüm varlıklar analiz ediliyor."

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

        key=lambda item: item[0],
        reverse=True

    )


    if not results:

        await update.message.reply_text(

            "❌ Fırsat taraması yapılamadı."

        )

        return


    top = results[:10]


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

        +

        "\n\n━━━━━━━━━━━━━━\n\n"

        "📌 Skor; trend, momentum, "
        "hareketli ortalamalar, volatilite "
        "ve hacim göstergelerinin birleşimidir."

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

        f"• {asset}"

        for asset in sorted(
            WATCHLIST
        )

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

        "Otomatik teknik piyasa analiz "
        "sistemi.\n\n"

        "🧠 TEKNİK MOTOR\n\n"

        "EMA20\n"
        "EMA50\n"
        "RSI(14)\n"
        "MACD\n"
        "MACD Histogram\n"
        "Bollinger Bandı\n"
        "Stochastic\n"
        "ATR(14)\n"
        "Hacim\n"
        "Destek / Direnç\n\n"

        "⭐ ANKA SKORU\n"
        "0 - 100\n\n"

        "🤖 SİNYALLER\n"
        "🔥 GÜÇLÜ AL\n"
        "🟢 AL\n"
        "🟡 TUT\n"
        "🟠 ZAYIF\n"
        "🔴 SAT\n\n"

        "📌 Veri kaynağı: Yahoo Finance\n\n"

        "⚠️ Yatırım tavsiyesi değildir."

    )


# ============================================================
# HATA YAKALAMA
# ============================================================

async def error_handler(
    update,
    context
):

    logger.exception(
        "Telegram hatası: %s",
        context.error
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


    print(
        "🦅 ANKA YATIRIM ANALİZ BAŞLATILIYOR..."
    )


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


    app.add_error_handler(
        error_handler
    )


    print(
        "🦅 ANKA YATIRIM ANALİZ FINAL BAŞLATILDI"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
