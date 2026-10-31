# Olist E-Commerce Dashboard

 Streamlit dashboard for analyzing sales data from Olist, a Brazilian e-commerce marketplace. The dashboard covers GMV, transaction trends, product categories, geographic distribution, and customer segmentation using RFM analysis.

Dashboard: https://olist-e-commerce-dashboard-app-g5f9nfvsqeybq2hzu9nqfz.streamlit.app/

## Project Structure

```text
├── dashboard/
│   ├── dashboard.py
│   ├── all_data.csv
│   └── brazil_states.geojson
├── data/                                   # raw CSV data
├── Proyek_Analisis_Data_E-Commerce.ipynb   # data analysis workflow
├── requirements.txt                        # list of required libraries
└── README.md                               # project documentation
```

## Setup Environment - Anaconda

Python 3.12 or newer is required.

```shell
git clone https://github.com/thcos/olist-e-commerce-dashboard-streamlit.git
cd olist-e-commerce-dashboard-streamlit

conda create --name main-ds python=3.12
conda activate main-ds
pip install -r requirements.txt
```

## Setup Environment - Shell/Terminal

Python 3.12 or newer is required.

```shell
git clone https://github.com/thcos/olist-e-commerce-dashboard-streamlit.git
cd olist-e-commerce-dashboard-streamlit

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run Streamlit App

Run the command below from the project root folder (the folder that contains `requirements.txt`):

```shell
streamlit run dashboard/dashboard.py
```

Press `Ctrl + C` in the terminal to stop it.

The dashboard only needs the files inside the `dashboard/` folder (`all_data.csv` and `brazil_states.geojson`). The `data/` folder and the notebook are only needed to reproduce the analysis.

## Data Source

Brazilian E-Commerce Public Dataset by Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce/data

The following tables are used: orders, order items, products, product category name translation, customers, and sellers.

## Methodology Notes

- Only orders with a `delivered` status are included in the analysis.
- GMV is calculated as the sum of item prices (`price`).
- The number of transactions is calculated using unique order IDs (`order_id`).
- Customers are identified using `customer_unique_id`, since `customer_id` changes with each order.
- RFM scores range from 1 to 5, where 5 represents the best score. Recency and Monetary are scored using quantiles, while Frequency uses manually defined thresholds because most customers have a frequency value of 1.
