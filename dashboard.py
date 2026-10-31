import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns 
import streamlit as st
from babel.numbers import format_currency
import geopandas as gdp

sns.set(style='dark')
st.set_page_config(page_title="Olist Dashboard", layout="wide")

# formatter
fmt_num = ticker.FuncFormatter(lambda x, pos: f"{x:,.0f}")
fmt_gmv = ticker.FuncFormatter(lambda x, pos:f"{x / 1e6:,.1f}M" if x >= 1e6 else f"{x / 1e3:,.0f}K" )

# format untuk menyingkat label di visualisasi (misal: 1.2M/350K, dst)
def short_label(v):
    return f"{v/1e6:,.2f}M" if v >= 1e6 else f"{v/1e3:,.0f}K"
def brl(value):
    return format_currency(value, "BRL", locale="pt_BR")

# MENYIAPKAN DATAFRAME

# GMV dan jumlah order unik per bulan (Pertanyaan 1 dan 3)
def create_monthly_df(df):
    monthly_df = df.resample(rule="MS", on="order_purchase_timestamp").agg({
        "order_id":"nunique",
        "price":"sum"
    }).reset_index()
    monthly_df.rename(columns={
        "order_id":"order_count",
        "price":"gmv"
    }, inplace=True)
    monthly_df["month"] = monthly_df["order_purchase_timestamp"].dt.strftime("%Y-%m")
    monthly_df["gmv_per_order"] = monthly_df["gmv"] / monthly_df["order_count"]
    monthly_df["mom_growth"] = monthly_df["order_count"].pct_change() * 100
    return monthly_df

# Jumlah item terjual, jumlah order, dan GMV per kategori (Pertanyaan 2)
def create_category_df(df):
    category_df = df.groupby(by="product_category_eng").agg(
        total_items=("order_id", "count"),
        total_orders=("order_id", "nunique"),
        gmv=("price", "sum")
    ).reset_index()
    return category_df

# Customer, seller, transaksi, dan GMV per state (Pertanyaan 4)
def create_region_df(df):
    cust_state = df.groupby("customer_state").agg(
        total_customers=("customer_unique_id", "nunique"),
        total_orders=("order_id", "nunique"),
        gmv=("price", "sum")
    ).reset_index().rename(columns={"customer_state":"abbrev_state"})

    seller_state = df.groupby("seller_state").agg(
        total_sellers=("seller_id","nunique"),
    ).reset_index().rename(columns={"seller_state":"abbrev_state"})

    region_df = cust_state.merge(seller_state, on="abbrev_state", how="outer").fillna(0)
    region_df[["total_customers", "total_orders", "total_sellers"]] = (
        region_df[["total_customers", "total_orders", "total_sellers"]].astype(int)
    )
    region_df["persen_customer"] = (region_df["total_customers"]/region_df["total_customers"].sum()*100).round(1)
    region_df["persen_seller"] = (region_df["total_sellers"]/region_df["total_sellers"].sum()*100).round(1)
    region_df["customer_per_seller"] = (
        region_df["total_customers"] / region_df["total_sellers"].replace(0, np.nan)
    ).round(1)
    return region_df

def create_rfm_df(df):
    rfm_df = df.groupby(by="customer_unique_id", as_index=False).agg(
        last_order_timestamp=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("price","sum")
    )
    # tangal acuan = sehari setelah transaksi terakhir di data
    recent_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    rfm_df["recency"] = (recent_date-rfm_df["last_order_timestamp"]).dt.days
    rfm_df.drop("last_order_timestamp", axis=1, inplace=True)
    # scoring rfm
    if len(rfm_df) >= 5:
        labels = [1, 2, 3, 4, 5]
        rfm_df["r_score"] = pd.qcut(
            rfm_df["recency"].rank(method="first"), 5, labels=labels[::-1]
        ).astype(int)
        rfm_df["m_score"] = pd.qcut(
            rfm_df["monetary"].rank(method="first"), 5, labels=labels
        ).astype(int)
        rfm_df["f_score"] = pd.cut(
            rfm_df["frequency"], bins=[0, 1, 2, 3, 4, np.inf], labels=labels
        ).astype(int)

        rfm_df["rfm_score"] = (rfm_df["r_score"].astype(str) + rfm_df["f_score"].astype(str) + rfm_df["m_score"].astype(str))
        rfm_df["rfm_total"] = rfm_df["r_score"] + rfm_df["f_score"] + rfm_df["m_score"]
        r, f, m = rfm_df["r_score"], rfm_df["f_score"], rfm_df["m_score"]
        conditions = [
            (r >= 4) & (m >= 4),
            f >= 2,
            r >= 4,
            (r <= 2) & (m >= 4),
            (r <= 2) & (m <= 2),
        ]
        choices = [
            "Top Customers",
            "Repeat Customers",
            "Recent / New Customers",
            "Big Spenders at Risk",
            "Lost Customers",
        ]
        rfm_df["segment"] = np.select(conditions, choices, default="Need Attention")
    return rfm_df

# LOAD DATA

def load_data(path):
    df = pd.read_csv(path)
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    df.sort_values(by="order_purchase_timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def load_states(path):
    return gdp.read_file(path)

all_df = load_data("all_data.csv")
brazil_states = load_states("brazil_states.geojson")

# Komponen Filter Data
min_date = all_df["order_purchase_timestamp"].min().date()
max_date = all_df["order_purchase_timestamp"].max().date()

with st.sidebar:
    st.header("Olist Dashboard")
    st.caption("Analisis penjualan marketplace e-commerce Brazil (order berstatus delivered)")

    date_range = st.date_input(
        label="Rentang Waktu",
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )
if len(date_range) != 2:
    st.info("Pilih tanggal awal dan akhir pada filter di sidebar.")
    st.stop()

start_date, end_date = date_range
main_df = all_df[
    (all_df["order_purchase_timestamp"] >= pd.Timestamp(start_date)) &
    (all_df["order_purchase_timestamp"] < pd.Timestamp(end_date) + pd.Timedelta(days=1))
]
if main_df.empty:
    st.warning("Tidak ditemukan data pada rentang waktu yang dipilih.")
    st.stop()

# menyiapkan berbagai dataframe
monthly_df = create_monthly_df(main_df)
category_df = create_category_df(main_df)
region_df = create_region_df(main_df)
rfm_df = create_rfm_df(main_df)

# Melengkapi Dashboard dengan Visualisasi Data
st.header("Olist E-Commerce Dashboard :sparkles:")

# ---- Ringkasan ----
col1, col2, = st.columns(2)
with col1:
    tot_orders = f"{main_df["order_id"].nunique():,}"
    st.metric("Total Orders", value=tot_orders)
with col2:
    tot_gmv = brl(main_df["price"].sum())
    st.metric("Total GMV", value=tot_gmv)
col3, col4 = st.columns(2)
with col3:
    tot_cust = f"{main_df["customer_unique_id"].nunique():,}"
    st.metric("Total Customers", value=tot_cust)
with col4:
    tot_selr = f"{main_df["seller_id"].nunique():,}"
    st.metric("Total Sellers", value=tot_selr)

# --- Pertanyaan 1: Tren Jumlah Transaksi
st.subheader("Monthly Orders Trend")
fig, ax = plt.subplots(figsize=(16, 6))
ax.plot(monthly_df["month"], monthly_df["order_count"], marker="o", linewidth=2, color="#2440a3")

idx_max = monthly_df["order_count"].idxmax()
ax.annotate(f"Tertinggi : {monthly_df.loc[idx_max, 'order_count']:,}",
            xy=(
                monthly_df.loc[idx_max, "month"],
                monthly_df.loc[idx_max, "order_count"]),
                xytext=(0,15),
                textcoords="offset points",
                ha="center", 
                fontsize=12,
                arrowprops=dict(arrowstyle="->"))
ax.yaxis.set_major_formatter(fmt_num)
ax.set_ylabel("Total Orders", fontsize=14)
ax.tick_params(axis="y", labelsize=14)
ax.tick_params(axis="x", labelsize=12, rotation=45)
ax.grid(True)
st.pyplot(fig)
plt.close(fig)

with st.expander("Lihat pertumbuhan jumlah transaksi dari bulan ke bulan (MoM)"):
    mom_df = monthly_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["mom_growth"])
    mom_df = mom_df[mom_df["order_purchase_timestamp"] >= "2017-02-01"]
    if mom_df.empty:
        st.write("Data tidak cukup untuk menghitung pertumbuhan MoM pada rentang ini")
    else:
        fig, ax = plt.subplots(figsize=(16, 5))
        bar_colors = ["#2440a3" if v >= 0 else "#E67E22" for v in mom_df["mom_growth"]]
        ax.bar(mom_df["month"], mom_df["mom_growth"], color=bar_colors)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f"{x:.0f}%"))
        ax.set_ylabel("Pertumbuhan (%)", fontsize=12)
        ax.tick_params(axis="x", labelsize=11, rotation=45)
        ax.grid(True)
        st.pyplot(fig)
        plt.close(fig)

# ---- Pertanyaan 1 : GMV
st.subheader("Monthly Gross Merchandise Value (GMV)")
fig, ax = plt.subplots(figsize=(16, 6))
ax.plot(monthly_df["month"], monthly_df["gmv"], marker="o", linewidth=2, color="#2440a3")

idx_max = monthly_df["gmv"].idxmax()
ax.annotate(f"Tertinggi: {monthly_df.loc[idx_max, 'gmv']:,.0f}",
            xy=(
                monthly_df.loc[idx_max, "month"], 
                monthly_df.loc[idx_max, "gmv"]),
            xytext=(0, 15), 
            textcoords="offset points", 
            ha="center",
            fontsize=12,
            arrowprops=dict(arrowstyle="->"))
ax.yaxis.set_major_formatter(fmt_gmv)
ax.set_ylabel("GMV (BRL)", fontsize=14)
ax.tick_params(axis="y", labelsize=14)
ax.tick_params(axis="x", labelsize=12, rotation=45)
ax.grid(True)
st.pyplot(fig)
plt.close(fig)

# GMV vs Total Transaksi
sns.set_theme(style="whitegrid")
st.subheader("GMV vs Total Orders")
fig, ax1 = plt.subplots(figsize=(16,6))
# Grafik 1: Tren GMV (Sumbu Y Kiri)
color = "#2440a3"
ax1.set_xlabel("Bulan (Tahun-Bulan)", fontsize=12)
ax1.set_ylabel("Total GMV (R$)", color=color, fontsize=12, fontweight="bold")

line1, = ax1.plot(
    monthly_df["month"],
    monthly_df["gmv"],
    marker="o",
    linewidth=2,
    color=color,
    label="GMV"
)
ax1.yaxis.set_major_formatter(fmt_gmv)
ax1.tick_params(axis="y", labelcolor=color, labelsize=12)
ax1.tick_params(axis="x", labelsize=11, rotation=45)
plt.setp(ax1.get_xticklabels(), ha="right")
ax1.grid(True)

# Grafik 2: Total Orders (Sumbu Y kanan)
ax2 = ax1.twinx()
color2 = "#E67E22"
ax2.set_ylabel("Total Orders", color=color, fontsize=12, fontweight="bold")

line2, = ax2.plot(
    monthly_df["month"],
    monthly_df["order_count"],
    marker="s",
    linewidth=2,
    linestyle="--",
    color=color2,
    label="Total Orders"
)
ax2.yaxis.set_major_formatter(fmt_num)
ax2.tick_params(axis="y", labelcolor=color2, labelsize=12)

ax1.legend(
    handles=[line1, line2],
    labels=["GMV", "Total Orders"],
    loc="upper left",
    fontsize=11
)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

# Indeks: GMV, Total Orders, GMV per Order
st.subheader("Indeks Pertumbuhan Bulanan: GMV, Total Orders, dan GMV per Order")
base_label = monthly_df["month"].iloc[0]
st.caption(f"Tiap metrik dibagi nilainya pada bulan pertama ({base_label}) lalu dikali 100, sehingga bulan pertama = 100.")
COLOR_GMV, COLOR_ORDERS, COLOR_AOV = "#2440a3", "#E67E22", "#6b6b6b"

index_cols = {"gmv": "GMV", "order_count": "Total Orders", "gmv_per_order": "GMV per Order"}
idx_df = monthly_df.set_index("month")[list(index_cols)]
idx_df = (idx_df / idx_df.iloc[0] * 100).rename(columns=index_cols)
 
fig, ax = plt.subplots(figsize=(14, 6))
for nama, warna in [("GMV", COLOR_GMV), ("Total Orders", COLOR_ORDERS), ("GMV per Order", COLOR_AOV)]:
    ax.plot(idx_df.index, idx_df[nama], marker="o", markersize=4, linewidth=2, color=warna, label=nama)
    ax.annotate(
        f"{idx_df[nama].iloc[-1]:,.0f}",
        xy=(idx_df.index[-1], idx_df[nama].iloc[-1]),
        xytext=(8, 0), textcoords="offset points",
        va="center", fontsize=10, color=warna, fontweight="bold",
    )
 
ax.axhline(100, color="black", linewidth=0.8, linestyle=":")
ax.set_xlabel("Bulan (Tahun-Bulan)", fontsize=12)
ax.set_ylabel("Indeks", fontsize=12)
ax.yaxis.set_major_formatter(fmt_num)
ax.tick_params(axis="x", rotation=45)
plt.setp(ax.get_xticklabels(), ha="right")
ax.grid(True, axis="y", linestyle="--", alpha=0.5)
ax.legend(loc="upper left", fontsize=11)
ax.margins(x=0.06)
plt.tight_layout()
st.pyplot(fig)
plt.close(fig)
 

# ---- Pertanyaan 3: Kategori Produk
st.subheader("Best & Worst Performing Product Category")
color1= "#2440a3"
color2= "#E67E22"
color3= "#c5cdeb"

category_config = [
    ("total_items", "Most Sold Categories", "Least Sold Categories", "Items Sold", fmt_num),
    ("gmv", "Highest GMV Categories", "Lowest GMV Categories", "GMV (BRL)", fmt_gmv),
]
for value_col, title_best, title_worst, xlabel, formatter in category_config:
    best = category_df.nlargest(5, value_col)
    worst = category_df.nsmallest(5, value_col)

    fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(16, 5))
    for a, data, title, first_color in [(ax[0], best, title_best, color1), (ax[1], worst, title_worst, color2)]:
        colors = [first_color] + [color3] * (len(data)-1)
        sns.barplot(
            x=value_col,
            y="product_category_eng",
            data=data,
            hue="product_category_eng",
            palette=colors,
            legend=False,
            ax=a
            )
        for p in a.patches:
            a.annotate(
                f"{p.get_width():,.0f}", 
                xy=(p.get_width(), p.get_y() + p.get_height() / 2),
                xytext=(4, 0), 
                textcoords="offset points",
                va="center", fontsize=10
                )
        a.set_ylabel(None)
        a.set_xlabel(xlabel, fontsize=12)
        a.xaxis.set_major_formatter(formatter)
        a.set_title(title, loc="center", fontsize=15)
        a.tick_params(axis="y", labelsize=11)
        a.margins(x=0.15)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# ---- Pertanyaan 4: Geospasial Analiysis
st.subheader("Customer & Seller Distribution")

cmap_blue = LinearSegmentedColormap.from_list("custom_blue", [color3, color1])
cmap_orange = LinearSegmentedColormap.from_list("custom_orange", ["#FBE3CF", color2])

map_df = brazil_states.merge(region_df, on="abbrev_state", how="left")
num_cols = ["total_customers", "total_orders", "gmv", "total_sellers", "persen_customer", "persen_seller"]
map_df[num_cols] = map_df[num_cols].fillna(0)

map_figures = [
    ("Distribution of Customers and Sellers across States", [
        ("total_customers", cmap_blue, "Customers based on State", lambda v: f"{v:,.0f}", "Total Customers"),
        ("total_sellers", cmap_blue, "Sellers based on State", lambda v: f"{v:,.0f}", "Total Sellers"),
    ]),
    ("Distribution of Transactions and GMV across States", [
        ("total_orders", cmap_blue, "Transactions based on State", lambda v: f"{v:,.0f}", "Total Orders"),
        ("gmv", cmap_blue, "GMV based on State", short_label, "GMV (BRL)"),
    ]),
]

for suptitle, panels in map_figures:
    fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(18,8))
    for a, (column, cmap, title, value_fmt, cbar_label) in zip(ax, panels):
         # transformasi logaritmik
        log_values = np.log10(map_df[column]+1)
        map_df.plot(column=log_values, cmap=cmap, edgecolor=color3, linewidth=0.6, ax=a,
                    legend=True, legend_kwds={"label":cbar_label, "shrink":0.7, "pad":0.1})
        max_power = int(np.log10(map_df[column].max()+1))
        tick_value = [10 ** i for i in range(1, max_power + 1)]
        if tick_value:
            cbar_ax = a.figure.axes[-1]
            cbar_ax.set_yticks([np.log10(v+1) for v in tick_value])
            cbar_ax.set_yticklabels([f"{v:,}" for v in tick_value])
        # label: singkatan state + nilai asli
        for _, row in map_df.iterrows():
            p = row.geometry.representative_point()
            a.text(p.x, p.y, f"{row['abbrev_state']}\n{value_fmt(row[column])}",
                   ha="center", va="center", fontsize=6.5, color="black",
                   path_effects=[pe.withStroke(linewidth=2, foreground="white")])
        
        a.set_title(title, fontsize=14)
        a.axis("off")

    plt.suptitle(suptitle, fontsize=16)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# melihat ketimpangan seller vs customer
with st.expander("Lihat Ketimpangan/perbandingan Customer vs Seller per State"):
    tabel = region_df[["abbrev_state", "total_customers", "persen_customer",
                       "total_sellers", "persen_seller", "customer_per_seller"]] \
        .sort_values("total_customers", ascending=False).reset_index(drop=True)
    st.dataframe(tabel)

    no_seller = region_df[(region_df["total_sellers"]==0) & (region_df["total_customers"] > 0)]["abbrev_state"].tolist()
    if no_seller:
        st.write("State yang punya customer tetapi tidak punya seller: " + ", ".join(sorted(no_seller)))

# RFM Analysis
st.subheader("Best Customer Based on RFM Parameters")
col1, col2, col3 = st.columns(3)

with col1:
    avg_recency = round(rfm_df.recency.mean(), 1)
    st.metric("Average Recency (days)", value=avg_recency)

with col2:
    avg_frequency = round(rfm_df.frequency.mean(), 2)
    st.metric("Average Frequency", value=avg_frequency)

with col3:
    avg_monetary = brl(rfm_df.monetary.mean())
    st.metric("Average Monetary", value=avg_monetary)

# top 5 customer masing-masing parameter
fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(35, 15))
colors = ["#2440a3", "#2440a3", "#2440a3", "#2440a3", "#2440a3"]

rfm_config = [
    (ax[0], "recency", True, "By Recency (days)"),
    (ax[1], "frequency", False, "By Frequency"),
    (ax[2], "monetary", False, "By Monetary")
]

for a, column, ascending, title in rfm_config:
    top = rfm_df.sort_values(by=column, ascending=ascending).head(5).copy()
    top["customer_short"] = top["customer_unique_id"].str[:8]
    sns.barplot(y=column, x="customer_short", data=top, hue="customer_short", palette=colors, legend=False, ax=a)
    a.set_ylabel(None)
    a.set_xlabel("customer_unique_id", fontsize=30)
    a.set_title(title, loc="center", fontsize=30)
    a.tick_params(axis="y", labelsize=30)
    a.tick_params(axis="x", labelsize=30, rotation=45)

plt.tight_layout()
st.pyplot(fig)
plt.close(fig)

if "rfm_total" in rfm_df.columns:
    st.subheader("Customer Segmentation (RFM)")
    segment_df = (
        rfm_df.groupby("segment").agg(
            total_customers=("customer_unique_id", "nunique"),
            avg_recency=("recency", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
        ).round(1).sort_values("total_customers", ascending=False).reset_index()
    )
    segment_df["persen_%"] = (
        segment_df["total_customers"] / segment_df["total_customers"].sum() * 100
    ).round(1)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(segment_df["segment"], segment_df["total_customers"], color="#2440a3")
    ax.invert_yaxis()  

    for bar, pct in zip(bars, segment_df["persen_%"]):
        ax.annotate(
            f"{bar.get_width():,.0f} ({pct:.1f}%)",
            xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(6, 0), textcoords="offset points",
            va="center", fontsize=11,
        )

    ax.xaxis.set_major_formatter(fmt_num)
    ax.set_xlim(0, segment_df["total_customers"].max() * 1.25)  
    ax.set_title("Distribusi Segmen Customer (RFM)", fontsize=16)
    ax.set_xlabel("Jumlah Customer", fontsize=12)
    ax.set_ylabel(None)
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

else:
    st.info("Data terlalu sedikit (kurang dari 5 pelanggan) untuk menghitung segmentasi RFM.")
plt.tight_layout()
st.pyplot(fig)
plt.close(fig)

st.caption("Olist E-Commerce Dashboard")