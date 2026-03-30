"""
Precios de Gasolina y Diesel en España a lo largo del tiempo.
Fuente oficial: API REST del Ministerio para la Transición Ecológica y el Reto Demográfico (MITERD)
URL: https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/
"""

import requests
import json
import datetime
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

BASE_URL = (
    "https://sedeaplicaciones.minetur.gob.es"
    "/ServiciosRESTCarburantes/PreciosCarburantes"
)

HEADERS = {"Accept": "application/json"}

# Campos de precio en la respuesta de la API
GASOLINA_95_KEY = "Precio Gasolina 95 E5"
DIESEL_KEY = "Precio Gasoil A"


def fetch_prices_for_date(date: datetime.date) -> dict | None:
    """Descarga el listado de estaciones para una fecha y calcula la media nacional."""
    date_str = date.strftime("%d-%m-%Y")
    url = f"{BASE_URL}/EstacionesTerrestresHist/{date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  [AVISO] {date_str}: {exc}")
        return None

    stations = data.get("ListaEESSPrecio", [])
    if not stations:
        return None

    g95_prices = []
    diesel_prices = []

    for station in stations:
        g95_raw = station.get(GASOLINA_95_KEY, "").replace(",", ".").strip()
        diesel_raw = station.get(DIESEL_KEY, "").replace(",", ".").strip()
        try:
            if g95_raw:
                g95_prices.append(float(g95_raw))
        except ValueError:
            pass
        try:
            if diesel_raw:
                diesel_prices.append(float(diesel_raw))
        except ValueError:
            pass

    result = {}
    if g95_prices:
        result["gasolina_95"] = statistics.mean(g95_prices)
    if diesel_prices:
        result["diesel"] = statistics.mean(diesel_prices)

    return result if result else None


def build_date_range(months_back: int = 24) -> list[datetime.date]:
    """Genera una lista de fechas, una por semana, desde hace `months_back` meses."""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=months_back * 30)
    dates = []
    current = start
    while current <= today:
        # Solo días laborables (lunes a viernes)
        if current.weekday() < 5:
            dates.append(current)
        current += datetime.timedelta(days=7)
    return dates


def collect_data(months_back: int = 24) -> tuple[list, list, list]:
    dates_to_query = build_date_range(months_back)
    print(f"Consultando {len(dates_to_query)} fechas (API MITERD)...\n")

    x_dates, y_g95, y_diesel = [], [], []

    for i, d in enumerate(dates_to_query, 1):
        print(f"  [{i:3d}/{len(dates_to_query)}] {d.strftime('%d-%m-%Y')}", end=" ")
        result = fetch_prices_for_date(d)
        if result:
            x_dates.append(d)
            y_g95.append(result.get("gasolina_95"))
            y_diesel.append(result.get("diesel"))
            g95_str = f"{result['gasolina_95']:.3f}" if result.get("gasolina_95") else "N/A"
            diesel_str = f"{result['diesel']:.3f}" if result.get("diesel") else "N/A"
            print(f"-> Gasolina 95: {g95_str} €/L  |  Diesel: {diesel_str} €/L")
        else:
            print("-> sin datos")

    return x_dates, y_g95, y_diesel


def plot(x_dates, y_g95, y_diesel, output_path: str = "precios_carburantes_espana.png"):
    # Filtrar None
    dates_g95 = [d for d, v in zip(x_dates, y_g95) if v is not None]
    vals_g95  = [v for v in y_g95  if v is not None]
    dates_d   = [d for d, v in zip(x_dates, y_diesel) if v is not None]
    vals_d    = [v for v in y_diesel if v is not None]

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("#F7F9FC")
    ax.set_facecolor("#F7F9FC")

    ax.plot(dates_g95, vals_g95,
            color="#E8412A", linewidth=2, marker="o", markersize=3,
            label="Gasolina 95 E5 (media nacional)")
    ax.plot(dates_d, vals_d,
            color="#1A6EBD", linewidth=2, marker="s", markersize=3,
            label="Gasóleo A (media nacional)")

    # Sombreado entre curvas
    if dates_g95 and dates_d:
        from matplotlib.dates import date2num
        import numpy as np
        all_dates = sorted(set(dates_g95) | set(dates_d))
        g95_dict = dict(zip(dates_g95, vals_g95))
        d_dict   = dict(zip(dates_d,   vals_d))
        common   = [d for d in all_dates if d in g95_dict and d in d_dict]
        if common:
            ax.fill_between(common,
                            [g95_dict[d] for d in common],
                            [d_dict[d]   for d in common],
                            alpha=0.10, color="#888888")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f €"))

    ax.set_title(
        "Evolución del Precio de Carburantes en España\n"
        "(Media nacional · Fuente: MITERD — API REST Carburantes)",
        fontsize=14, fontweight="bold", pad=14
    )
    ax.set_xlabel("Fecha", fontsize=11)
    ax.set_ylabel("Precio medio (€/litro)", fontsize=11)
    ax.legend(fontsize=11, loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.grid(axis="x", linestyle=":", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\nGráfico guardado en: {output_path}")


if __name__ == "__main__":
    x, g95, diesel = collect_data(months_back=24)
    if x:
        plot(x, g95, diesel)
    else:
        print("No se obtuvieron datos. Revisa la conexión o la API.")
