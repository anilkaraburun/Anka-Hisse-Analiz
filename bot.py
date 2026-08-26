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
# 🦅 ANKA YATIRIM ANALİZ V10
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
# YARDIMCI FONKSİYON
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
    period="1y",
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
                "%s için veri boş.",
                symbol
            )

            return None


        # ----------------------------------------------------
        # MultiIndex güvenliği
        # ----------------------------------------------------

        if isinstance(data.columns, pd.MultiIndex):

            data.columns = data.columns.get_level_values(0)


        # ----------------------------------------------------
        # Sütun kontrolü
        # ----------------------------------------------------

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close"
        ]

        for column in required_columns:

            if column not in data.columns:

                logger.error(
                    "%s için %s sütunu bulunamadı.",
                    symbol,
                    column
                )

                return None


        # ----------------------------------------------------
        # Sayısal dönüşüm
        # ----------------------------------------------------

        for column in data.columns:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )


        # ----------------------------------------------------
        # Close temizliği
        # ----------------------------------------------------

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
# STOCHASTIC
# ============================================================

def calculate_stochastic(
    data,
    period=14
):

    low_min = data["Low"].rolling(
        period
    ).min()

    high_max = data["High"].rolling(
        period
    ).max()

    denominator = (
        high_max - low_min
    )

    denominator = denominator.replace(
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
        3
    ).mean()

    return (
        k,
        d
    )


# ============================================================
# HACİM ORANI
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

    if volume.dropna().empty:

        return None

    average = volume.rolling(
        period
    ).mean()

    current = volume.iloc[-1]

    average_current = average.iloc[-1]

    if (
        pd.isna(current)
        or pd.isna(average_current)
        or average_current == 0
    ):

        return None

    return float(
        current / average_current
    )


# ============================================================
# DESTEK / DİRENÇ
# ============================================================

def calculate_support_resistance(
    data
):

    recent = data.tail(60)

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

    if (
        len(high) < 10
        or len(low) < 10
        or len(close) < 10
    ):

        return (
            None,
            None
        )

    current = float(
        close.iloc[-1]
    )


    # --------------------------------------------------------
    # Fiyatın altındaki en yakın destek
    # --------------------------------------------------------

    supports = sorted(
        set(
            float(x)
            for x in low
            if float(x) < current
        ),
        reverse=True
    )


    if supports:

        support = supports[0]

    else:

        support = float(
            low.min()
        )


    # --------------------------------------------------------
    # Fiyatın üzerindeki en yakın direnç
    # --------------------------------------------------------

    resistances = sorted(
        set(
            float(x)
            for x in high
            if float(x) > current
        )
    )


    if resistances:

        resistance = resistances[0]

    else:

        resistance = float(
            high.max()
        )


    return (
        support,
        resistance
    )


# ============================================================
# KIRILIM
# ============================================================

def calculate_breakout(
    price,
    support,
    resistance
):

    if support is None or resistance is None:

        return "➡️ Kırılım yok"

    if price > resistance:

        return "🚀 DİRENÇ KIRILDI"

    if price < support:

        return "🚨 DESTEK KIRILDI"

    return "➡️ Kırılım yok"


# ============================================================
# 🧠 ANKA SKOR MOTORU V10
#
# Toplam sistem:
#
# Başlangıç       : 50
#
# EMA20           : ±8
# EMA20/EMA50     : ±8
# RSI             : ±6
# MACD            : ±6
# Histogram       : ±3
# Bollinger       : ±4
# Stochastic      : ±3
# Hacim           : ±2
#
# Destek/direnç   : +4 / -3
#
# Böylece sistem
# gereksiz yere 0'a
# çakılmaz.
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

    volume_ratio,

    support,

    resistance

):

    score = 50

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

        score += 8

        reasons.append(
            "EMA20, EMA50 üzerinde"
        )

    else:

        score -= 8

        reasons.append(
            "EMA20, EMA50 altında"
        )


    # ========================================================
    # 3 — RSI
    # ========================================================

    if 55 <= rsi <= 65:

        score += 6

        reasons.append(
            "RSI pozitif bölgede"
        )

    elif 50 <= rsi < 55:

        score += 3

        reasons.append(
            "RSI hafif pozitif"
        )

    elif 45 <= rsi < 50:

        score -= 1

        reasons.append(
            "RSI nötr / hafif zayıf"
        )

    elif 40 <= rsi < 45:

        score -= 2

        reasons.append(
            "RSI hafif zayıf"
        )

    elif 30 <= rsi < 40:

        score -= 4

        reasons.append(
            "RSI zayıf bölgede"
        )

    elif rsi < 30:

        score -= 2

        reasons.append(
            "RSI aşırı satım bölgesinde"
        )

    elif 65 < rsi <= 70:

        score += 4

        reasons.append(
            "RSI güçlü bölgede"
        )

    else:

        # RSI > 70
        # Güçlü momentum vardır fakat aşırı alım riski de vardır.

        score += 2

        reasons.append(
            "RSI yüksek / aşırı alım bölgesi"
        )


    # ========================================================
    # 4 — MACD
    # ========================================================

    if macd > signal:

        score += 6

        reasons.append(
            "MACD Signal üzerinde"
        )

    else:

        score -= 6

        reasons.append(
            "MACD Signal altında"
        )


    # ========================================================
    # 5 — HISTOGRAM
    # ========================================================

    if histogram > 0:

        score += 3

        reasons.append(
            "MACD histogram pozitif"
        )

    else:

        score -= 3

        reasons.append(
            "MACD histogram negatif"
        )


    # ========================================================
    # 6 — BOLLINGER
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
    # 7 — STOCHASTIC
    # ========================================================

    if (
        stoch_k is not None
        and stoch_d is not None
    ):

        if stoch_k > stoch_d and stoch_k < 80:

            score += 3

            reasons.append(
                "Stochastic pozitif"
            )

        elif stoch_k < stoch_d:

            score -= 3

            reasons.append(
                "Stochastic negatif"
            )


    # ========================================================
    # 8 — HACİM
    # ========================================================

    if volume_ratio is not None:

        if volume_ratio >= 1.5:

            if price > ema20:

                score += 2

                reasons.append(
                    "Yüksek hacim yükselişi destekliyor"
                )

            else:

                score -= 1

                reasons.append(
                    "Yüksek hacim satış baskısını artırıyor"
                )

        elif volume_ratio < 0.7:

            reasons.append(
                "Hacim düşük"
            )


    # ========================================================
    # 9 — DESTEK / DİRENÇ
    # ========================================================

    if (
        support is not None
        and resistance is not None
    ):

        distance_support = abs(
            price - support
        ) / price

        distance_resistance = abs(
            resistance - price
        ) / price


        # Desteğe çok yakınsa
        if distance_support <= 0.02:

            score += 4

            reasons.append(
                "Fiyat destek bölgesine yakın"
            )


        # Dirence çok yakınsa
        elif distance_resistance <= 0.02:

            score -= 3

            reasons.append(
                "Fiyat direnç bölgesine yakın"
            )


        else:

            reasons.append(
                "Fiyat destek/direnç arasında"
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


    if score >= 65:

        return "🟢 AL"


    if score >= 45:

        return "🟡 TUT"


    if score >= 30:

        return "🟠 ZAYIF"


    return "🔴 SAT"


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

        price = safe_float(
            close.iloc[-1]
        )


        if price is None:

            return None


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

        rsi_values = rsi_series.dropna()


        if rsi_values.empty:

            return None


        rsi = safe_float(
            rsi_values.iloc[-1]
        )


        # ====================================================
        # MACD
        # ====================================================

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


        # ====================================================
        # BOLLINGER
        # ====================================================

        (
            bb_middle_series,
            bb_upper_series,
            bb_lower_series
        ) = calculate_bollinger(
            close
        )


        bb_middle_values = (
            bb_middle_series.dropna()
        )

        bb_upper_values = (
            bb_upper_series.dropna()
        )

        bb_lower_values = (
            bb_lower_series.dropna()
        )


        if (
            bb_middle_values.empty
            or bb_upper_values.empty
            or bb_lower_values.empty
        ):

            return None


        bb_middle = safe_float(
            bb_middle_values.iloc[-1]
        )

        bb_upper = safe_float(
            bb_upper_values.iloc[-1]
        )

        bb_lower = safe_float(
            bb_lower_values.iloc[-1]
        )


        # ====================================================
        # ATR
        # ====================================================

        atr_series = calculate_atr(
            data,
            14
        )

        atr_values = atr_series.dropna()


        atr = (
            safe_float(
                atr_values.iloc[-1]
            )
            if not atr_values.empty
            else None
        )


        # ====================================================
        # STOCHASTIC
        # ====================================================

        stoch_k_series, stoch_d_series = (
            calculate_stochastic(
                data
            )
        )


        stoch_k_values = (
            stoch_k_series.dropna()
        )

        stoch_d_values = (
            stoch_d_series.dropna()
        )


        stoch_k = (
            safe_float(
                stoch_k_values.iloc[-1]
            )
            if not stoch_k_values.empty
            else None
        )


        stoch_d = (
            safe_float(
                stoch_d_values.iloc[-1]
            )
            if not stoch_d_values.empty
            else None
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
        # KIRILIM
        # ====================================================

        breakout = calculate_breakout(
            price,
            support,
            resistance
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

            volume_ratio=volume_ratio,

            support=support,

            resistance=resistance
        )


        # ====================================================
        # SİNYAL
        # ====================================================

        signal_text = calculate_signal(
            score
        )


        # ====================================================
        # MACD DURUM
        # ====================================================

        if macd > macd_signal:

            macd_status = "🟢 Pozitif"

        else:

            macd_status = "🔴 Negatif"


        # ====================================================
        # BOLLINGER DURUM
        # ====================================================

        if price > bb_upper:

            bollinger_status = (
                "🔥 Üst bandın üzerinde"
            )

        elif price < bb_lower:

            bollinger_status = (
                "🚨 Alt bandın altında"
            )

        elif price > bb_middle:

            bollinger_status = (
                "🟢 Orta bandın üzerinde"
            )

        else:

            bollinger_status = (
                "🟡 Orta bandın altında"
            )


        # ====================================================
        # RSI DURUM
        # ====================================================

        if rsi >= 70:

            rsi_status = "🔥 Aşırı alım"

        elif rsi >= 60:

            rsi_status = "🟢 Güçlü"

        elif rsi >= 50:

            rsi_status = "🟢 Pozitif"

        elif rsi >= 40:

            rsi_status = "🟡 Hafif zayıf"

        elif rsi >= 30:

            rsi_status = "🔴 Zayıf"

        else:

            rsi_status = "🚨 Aşırı satım"


        # ====================================================
        # STOCHASTIC DURUM
        # ====================================================

        if (
            stoch_k is not None
            and stoch_d is not None
        ):

            if stoch_k > stoch_d:

                stochastic_status = "🟢 Pozitif"

            else:

                stochastic_status = "🔴 Negatif"

        else:

            stochastic_status = "⚪ Hesaplanamadı"


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

            "bollinger_status": bollinger_status,

            "atr": atr,

            "stoch_k": stoch_k,

            "stoch_d": stoch_d,

            "stochastic_status": stochastic_status,

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
/analiz GUMUS
/analiz BAKIR

/metaller

/firsatlar

/takip THYAO
/takiplerim

/hakkinda

/test

━━━━━━━━━━━━━━━━━━

🧠 ANKA TEKNİK ANALİZ V10

EMA20 • EMA50
RSI • MACD
Bollinger
Stochastic
ATR
Hacim
Destek / Direnç

⭐ ANKA SKORU
0 - 100

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

        "🧠 Teknik analiz motoru V10 aktif."

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


        if current is None:

            await update.message.reply_text(
                "❌ Güncel fiyat alınamadı."
            )

            return


        if previous:

            change = (
                (
                    current - previous
                )
                / previous
                * 100
            )

        else:

            change = 0


        if "High" in data.columns:

            high = safe_float(
                data["High"].dropna().iloc[-1],
                current
            )

        else:

            high = current


        if "Low" in data.columns:

            low = safe_float(
                data["Low"].dropna().iloc[-1],
                current
            )

        else:

            low = current


        if change > 0:

            direction = "🟢"

        elif change < 0:

            direction = "🔴"

        else:

            direction = "🟡"


        mesaj = (

            "🦅 ANKA YATIRIM ANALİZ\n\n"

            f"📊 {asset}\n\n"

            f"{info['name']}\n\n"

            "━━━━━━━━━━━━━━━━\n\n"

            f"💰 Fiyat: {current:.4f}\n\n"

            f"{direction} Günlük değişim: "
            f"{change:+.2f}%\n\n"

            f"🔺 Gün içi yüksek: "
            f"{high:.4f}\n\n"

            f"🔻 Gün içi düşük: "
            f"{low:.4f}\n\n"

            "━━━━━━━━━━━━━━━━\n\n"

            "📌 Veri kaynağı: Yahoo Finance\n\n"

            "🧠 Teknik analiz:\n"

            f"/analiz {asset}"

        )


        await update.message.reply_text(
            mesaj
        )


    except Exception as e:

        logger.exception(
            "Fiyat hatası: %s",
            e
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

        f"🔎 {asset} teknik olarak analiz ediliyor...\n\n"
        "🧠 ANKA V10 motoru çalışıyor."

    )


    result = technical_analysis(
        info["symbol"]
    )


    if result is None:

        await update.message.reply_text(

            "❌ Teknik analiz için yeterli "
            "veya geçerli veri alınamadı.\n\n"

            "Yahoo Finance veri akışı kontrol edilemiyor."

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


    atr_text = (

        f"{result['atr']:.4f}"

        if result["atr"] is not None

        else "Hesaplanamadı"

    )


    stoch_k_text = (

        f"{result['stoch_k']:.2f}"

        if result["stoch_k"] is not None

        else "N/A"

    )


    stoch_d_text = (

        f"{result['stoch_d']:.2f}"

        if result["stoch_d"] is not None

        else "N/A"

    )


    volume_text = (

        f"{result['volume_ratio']:.2f}x"

        if result["volume_ratio"] is not None

        else "N/A"

    )


    mesaj = (

        "🦅 ANKA YATIRIM ANALİZ\n\n"

        f"📊 {asset}\n\n"

        f"{info['name']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🧠 ANKA TEKNİK ANALİZ V10\n\n"

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
        f"{result['histogram']:.4f}\n\n"

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
        f"{result['bollinger_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📉 STOCHASTIC\n\n"

        f"%K: {stoch_k_text}\n"

        f"%D: {stoch_d_text}\n\n"

        f"Durum: "
        f"{result['stochastic_status']}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "📊 VOLATİLİTE / HACİM\n\n"

        f"ATR(14): {atr_text}\n"

        f"Hacim / Ortalama: {volume_text}\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🎯 DESTEK / DİRENÇ\n\n"

        f"🟢 Destek: "
        f"{support_text}\n"

        f"🔴 Direnç: "
        f"{resistance_text}\n\n"

        "🚨 Durum:\n"

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

        "🥇🥈🟠 Altın-Gümüş-Bakır analiz ediliyor...\n\n"
        "🧠 ANKA V10 motoru çalışıyor."

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

        "🔥 Anka fırsat taraması yapıyor...\n\n"
        "📊 Tüm varlıklar taranıyor."

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

        +

        "\n\n━━━━━━━━━━━━━━\n\n"

        "⚠️ Liste yalnızca teknik göstergelere "
        "göre oluşturulmuştur."

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
# /TAKİPLERİM
# ============================================================

async def takiplerim(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not WATCHLIST:

        await update.message.reply_text(

            "📋 Takip listen boş.\n\n"

            "Örnek:\n"
            "/takip THYAO"

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

        "Otomatik teknik analiz sistemi.\n\n"

        "🧠 ANKA V10 MOTORU\n\n"

        "EMA20\n"
        "EMA50\n"
        "RSI(14)\n"
        "MACD\n"
        "Bollinger Bandı\n"
        "Stochastic\n"
        "ATR\n"
        "Hacim\n"
        "Destek / Direnç\n\n"

        "⭐ Anka Skoru: 0-100\n\n"

        "🤖 Sinyaller:\n"

        "🔥 GÜÇLÜ AL\n"
        "🟢 AL\n"
        "🟡 TUT\n"
        "🟠 ZAYIF\n"
        "🔴 SAT\n\n"

        "⚠️ Yatırım tavsiyesi değildir."

    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.exception(
        "Telegram bot hatası:",
        exc_info=context.error
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
        "🦅 ANKA YATIRIM ANALİZ V10 BAŞLATILIYOR..."
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
        "🦅 ANKA YATIRIM ANALİZ V10 AKTİF"
    )


    app.run_polling()


# ============================================================
# BAŞLAT
# ============================================================

if __name__ == "__main__":

    main()
