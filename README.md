# Olist E-Commerce Dashboard

Dashboard interaktif berbasis Streamlit untuk menganalisis penjualan marketplace e-commerce Brasil (Olist), mencakup GMV, tren transaksi, kategori produk, persebaran wilayah, dan segmentasi customer (RFM).

Dashboard: 

## Project Structure

```
dashboard/           : direktori berisi file untuk pembuatan dashboard
├── dashboard.py            
├── all_data.csv            
├── brazil_states.geojson   
data/                : direktori yang berisi data mentah csv
notebook.ipynb       : proses analisis pada notebook.ipynb
requirements.txt     : daftar library
README.md            : dokumentasi file

```

## Sumber Data

Brazilian E-Commerce Public Dataset by Olist: [https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data].Tabel yang dipakai: orders, order items, products, product category
name translation, customers, dan sellers.

## Catatan Metodologi

- Hanya order berstatus `delivered` yang dianalisis.
- GMV dihitung dari total harga barang (`price`).
- Jumlah transaksi dihitung dari order unik (`order_id`).
- Customer diidentifikasi dengan `customer_unique_id`, karena `customer_id` berubah di setiap order.
- Skor RFM berskala 1 sampai 5 (5 = terbaik). Recency dan Monetary memakai kuantil, Frequency memakai batas manual karena sebagian besar customer hanya memiliki nilai frequency 1.
