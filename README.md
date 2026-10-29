# Olist E-Commerce Dashboard

An interactive Streamlit dashboard for analyzing sales data from Olist, a Brazilian e-commerce marketplace. The dashboard covers GMV, transaction trends, product categories, geographic distribution, and customer segmentation using RFM analysis.

Dashboard: https://olist-e-commerce-dashboard-app-g5f9nfvsqeybq2hzu9nqfz.streamlit.app/

## Project Structure

```text
├── dashboard.py
├── all_data.csv
├── brazil_states.geojson
├── requirements.txt     : List of required libraries
├── README.md            : Project documentation
```

## Data Source

Brazilian E-Commerce Public Dataset by Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data

The following tables are used: orders, order items, products, product category name translation, customers, and sellers.

## Methodology Notes

- Only orders with a `delivered` status are included in the analysis.
- GMV is calculated as the sum of item prices (`price`).
- The number of transactions is calculated using unique order IDs (`order_id`).
- Customers are identified using `customer_unique_id`, since `customer_id` changes with each order.
- RFM scores range from 1 to 5, where 5 represents the best score. Recency and Monetary are scored using quantiles, while Frequency uses manually defined thresholds because most customers have a frequency value of 1.
