from typing import Any, Dict, List, Optional

import pandas as pd


SUPPORTED_MARKET_TICKERS = {
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
}


def _import_yfinance():
    try:
        import yfinance as yf

        return yf
    except ImportError:
        return None


def _format_date(value: Any) -> str:
    parsed_date = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed_date):
        return str(value)[:10]

    return parsed_date.strftime("%Y-%m-%d")


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, pd.Series):
        if value.empty:
            return None
        value = value.iloc[0]

    if pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_series(data: pd.DataFrame, column_name: str) -> Optional[pd.Series]:
    if data.empty:
        return None

    if column_name in data.columns:
        selected = data[column_name]

        if isinstance(selected, pd.DataFrame):
            return selected.iloc[:, 0]

        return selected

    if isinstance(data.columns, pd.MultiIndex):
        if column_name in data.columns.get_level_values(0):
            selected = data.xs(column_name, axis=1, level=0)

            if isinstance(selected, pd.DataFrame):
                return selected.iloc[:, 0]

            return selected

        for column in data.columns:
            column_parts = [str(part) for part in column]

            if column_name in column_parts:
                selected = data[column]

                if isinstance(selected, pd.DataFrame):
                    return selected.iloc[:, 0]

                return selected

    return None


def _clean_price_history(data: pd.DataFrame) -> List[Dict[str, Any]]:
    close_series = _get_series(data, "Close")

    if close_series is None:
        close_series = _get_series(data, "Adj Close")

    if close_series is None:
        return []

    close_series = close_series.dropna()

    history = []

    for date_value, close_price_value in close_series.items():
        close_price = _to_float(close_price_value)

        if close_price is None:
            continue

        history.append(
            {
                "date": _format_date(date_value),
                "close": round(close_price, 4),
            }
        )

    return history


def get_market_snapshot(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
) -> Dict[str, Any]:
    """
    Seçilen ticker için basit piyasa görünümü döndürür.

    Bu modül RAG cevabına veri enjekte etmez.
    Sadece Streamlit arayüzünde bağlamsal finansal gösterim için kullanılır.
    """
    ticker = ticker.upper().strip()

    if ticker not in SUPPORTED_MARKET_TICKERS:
        return {
            "ok": False,
            "ticker": ticker,
            "error": "Desteklenmeyen ticker.",
            "history": [],
        }

    yf = _import_yfinance()

    if yf is None:
        return {
            "ok": False,
            "ticker": ticker,
            "error": "yfinance paketi kurulu değil.",
            "history": [],
        }

    try:
        data = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if data is None or data.empty:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "Piyasa verisi bulunamadı.",
                "history": [],
            }

        history = _clean_price_history(data)

        if not history:
            return {
                "ok": False,
                "ticker": ticker,
                "error": "Kapanış fiyatı verisi okunamadı.",
                "history": [],
            }

        last_item = history[-1]
        previous_item = history[-2] if len(history) >= 2 else None

        last_close = float(last_item["close"])
        previous_close = float(previous_item["close"]) if previous_item else None

        if previous_close and previous_close != 0:
            daily_change = last_close - previous_close
            daily_change_percent = (daily_change / previous_close) * 100
        else:
            daily_change = 0.0
            daily_change_percent = 0.0

        return {
            "ok": True,
            "ticker": ticker,
            "currency": "USD",
            "last_close": round(last_close, 4),
            "previous_close": round(previous_close, 4) if previous_close else None,
            "daily_change": round(daily_change, 4),
            "daily_change_percent": round(daily_change_percent, 4),
            "price_date": last_item["date"],
            "period": period,
            "interval": interval,
            "history": history,
            "data_provider": "Yahoo Finance via yfinance",
            "disclaimer": (
                "Piyasa verisi yalnızca bağlamsal gösterim amaçlıdır. "
                "RAG cevabı SEC 10-K kaynaklarına dayanır ve yatırım tavsiyesi değildir."
            ),
        }

    except Exception as error:
        return {
            "ok": False,
            "ticker": ticker,
            "error": str(error),
            "history": [],
        }


def print_market_snapshot(ticker: str) -> None:
    snapshot = get_market_snapshot(ticker)

    if not snapshot.get("ok"):
        print(f"{ticker} için piyasa verisi alınamadı: {snapshot.get('error')}")
        return

    print(f"Ticker: {snapshot['ticker']}")
    print(f"Last Close: {snapshot['last_close']} {snapshot['currency']}")
    print(
        f"Daily Change: {snapshot['daily_change']} "
        f"({snapshot['daily_change_percent']}%)"
    )
    print(f"Price Date: {snapshot['price_date']}")
    print(f"History Count: {len(snapshot['history'])}")


def main() -> None:
    print_market_snapshot("AAPL")


if __name__ == "__main__":
    main()