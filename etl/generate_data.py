"""
generate_data.py — Generates realistic synthetic data for the warehouse project.

Produces 5 CSV/JSON files in data/raw/:
  - customers.csv       500 customers with demographics
  - products.csv         50 products across 5 categories
  - orders.csv         5000 sales orders (2022–2024)
  - order_items.csv    line items for every order
  - campaigns.json      20 marketing campaigns with spend + impressions
"""

import json
import random
import numpy as np
import pandas as pd
from faker import Faker
from pathlib import Path
from datetime import datetime, timedelta

from config import RAW_DATA_DIR, NUM_CUSTOMERS, NUM_PRODUCTS, NUM_ORDERS, NUM_CAMPAIGNS, START_DATE, END_DATE
from logger import get_logger

log = get_logger("generate_data")
fake = Faker("en_IN")   # Indian locale for names; prices in USD still
random.seed(42)
np.random.seed(42)
Faker.seed(42)

START = datetime.strptime(START_DATE, "%Y-%m-%d")
END   = datetime.strptime(END_DATE,   "%Y-%m-%d")
DAYS  = (END - START).days


# ─── Helper ───────────────────────────────────────────────────────────────────

def rand_date(start=START, days=DAYS) -> datetime:
    return start + timedelta(days=random.randint(0, days))


# ─── Customers ────────────────────────────────────────────────────────────────

SEGMENTS   = ["Enterprise", "SMB", "Startup", "Consumer"]
SEG_WEIGHT = [0.15, 0.30, 0.25, 0.30]

REGIONS = {
    "North": ["Delhi", "Chandigarh", "Lucknow", "Jaipur"],
    "South": ["Bengaluru", "Chennai", "Hyderabad", "Kochi"],
    "East":  ["Kolkata", "Bhubaneswar", "Patna", "Guwahati"],
    "West":  ["Mumbai", "Pune", "Ahmedabad", "Surat"],
}


def generate_customers(n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        region  = random.choice(list(REGIONS.keys()))
        city    = random.choice(REGIONS[region])
        segment = random.choices(SEGMENTS, SEG_WEIGHT)[0]
        joined  = rand_date(START - timedelta(days=730), 730 + DAYS)
        rows.append({
            "customer_id":   f"CUST{i:05d}",
            "name":          fake.name(),
            "email":         fake.email(),
            "phone":         fake.phone_number(),
            "city":          city,
            "region":        region,
            "country":       "India",
            "segment":       segment,
            "joined_date":   joined.strftime("%Y-%m-%d"),
            "is_active":     random.choices([1, 0], [0.85, 0.15])[0],
            "loyalty_score": round(random.uniform(1.0, 10.0), 1),
        })
    df = pd.DataFrame(rows)
    log.info(f"Generated {len(df)} customers across {df['region'].nunique()} regions")
    return df


# ─── Products ─────────────────────────────────────────────────────────────────

CATEGORIES = {
    "Electronics":  (5000, 80000),
    "Software":     (999,  25000),
    "Accessories":  (299,   5000),
    "Furniture":    (3000, 40000),
    "Stationery":   (50,    999),
}

PRODUCT_NAMES = {
    "Electronics":  ["Laptop Pro", "Wireless Headset", "Smart Monitor", "USB-C Hub",
                     "Webcam HD", "Keyboard Mech", "Mouse Ergonomic", "Tablet",
                     "SSD External", "Docking Station"],
    "Software":     ["CRM Suite", "Project Manager", "Analytics Tool", "Security Suite",
                     "Cloud Backup", "Design Studio", "Dev IDE Pro", "Collab Platform",
                     "Finance Tracker", "HR Module"],
    "Accessories":  ["Cable HDMI 2m", "Screen Cleaner Kit", "Laptop Stand", "Bag",
                     "Power Bank", "Wireless Charger", "Stylus Pen", "Mouse Pad XL",
                     "Webcam Cover", "Cable Organiser"],
    "Furniture":    ["Standing Desk", "Ergonomic Chair", "Monitor Arm", "Drawer Cabinet",
                     "Bookshelf", "Meeting Table", "Locker Unit", "Whiteboard Foldable",
                     "Visitor Chair", "Footrest"],
    "Stationery":   ["Notebook Premium", "Pen Set", "Sticky Notes Pack", "Highlighters",
                     "Binder A4", "Stapler Heavy", "Paper Ream", "Marker Board",
                     "File Folder", "Label Printer"],
}


def generate_products(n: int) -> pd.DataFrame:
    rows = []
    pid  = 1
    per_cat = n // len(CATEGORIES)
    for cat, (lo, hi) in CATEGORIES.items():
        names = PRODUCT_NAMES[cat]
        for j in range(per_cat):
            name = names[j % len(names)]
            cost = round(random.uniform(lo * 0.4, hi * 0.6), 2)
            price = round(cost * random.uniform(1.4, 2.2), 2)
            rows.append({
                "product_id":   f"PROD{pid:04d}",
                "name":         name,
                "category":     cat,
                "sub_category": cat,
                "unit_cost":    cost,
                "unit_price":   price,
                "margin_pct":   round((price - cost) / price * 100, 1),
                "stock_qty":    random.randint(0, 500),
                "is_active":    random.choices([1, 0], [0.90, 0.10])[0],
                "launch_date":  rand_date(START - timedelta(days=1000), 1000).strftime("%Y-%m-%d"),
            })
            pid += 1
    df = pd.DataFrame(rows)
    log.info(f"Generated {len(df)} products across {df['category'].nunique()} categories")
    return df


# ─── Orders + Order Items ─────────────────────────────────────────────────────

CHANNELS  = ["Online", "Sales Rep", "Partner", "Direct"]
STATUSES  = ["Completed", "Completed", "Completed", "Returned", "Cancelled"]
PAYMENT   = ["Credit Card", "UPI", "Net Banking", "Cheque", "Cash"]


def generate_orders_and_items(
    n: int,
    customers: pd.DataFrame,
    products: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    customer_ids = customers["customer_id"].tolist()
    product_ids  = products["product_id"].tolist()

    # Weight products so Electronics & Software sell more
    cat_map = products.set_index("product_id")["category"]
    weights = products["product_id"].map(
        lambda p: 3 if cat_map[p] in ("Electronics", "Software") else 1
    ).tolist()
    total_w = sum(weights)
    prod_probs = [w / total_w for w in weights]

    orders, items = [], []
    item_id = 1

    # Seasonal multiplier helper
    def seasonal(dt: datetime) -> float:
        m = dt.month
        if m in (11, 12): return 1.6   # festive / year-end
        if m in (3, 4):   return 1.3   # fiscal year-end
        if m in (6, 7):   return 0.8   # lean months
        return 1.0

    for i in range(1, n + 1):
        order_date = rand_date()
        # Bias toward higher order count in later years (growth trend)
        year_factor = 1 + (order_date.year - START.year) * 0.15
        if random.random() > (0.7 * year_factor * seasonal(order_date)):
            order_date = rand_date()   # resample; soft retry

        num_items  = random.choices([1, 2, 3, 4, 5], [0.40, 0.30, 0.15, 0.10, 0.05])[0]
        prods      = np.random.choice(product_ids, size=num_items, replace=False, p=prod_probs)
        cust_id    = random.choice(customer_ids)
        status     = random.choice(STATUSES)
        channel    = random.choice(CHANNELS)
        payment    = random.choice(PAYMENT)

        order_total  = 0.0
        order_profit = 0.0

        for prod_id in prods:
            prod_row  = products[products["product_id"] == prod_id].iloc[0]
            qty       = random.randint(1, 5)
            unit_p    = prod_row["unit_price"]
            unit_c    = prod_row["unit_cost"]
            disc_pct  = random.choices([0, 5, 10, 15, 20], [0.50, 0.20, 0.15, 0.10, 0.05])[0]
            disc_amt  = round(unit_p * disc_pct / 100, 2)
            final_p   = round((unit_p - disc_amt) * qty, 2)
            profit    = round((unit_p - disc_amt - unit_c) * qty, 2)
            order_total  += final_p
            order_profit += profit
            items.append({
                "item_id":       f"ITEM{item_id:07d}",
                "order_id":      f"ORD{i:07d}",
                "product_id":    prod_id,
                "quantity":      qty,
                "unit_price":    unit_p,
                "discount_pct":  disc_pct,
                "discount_amt":  disc_amt,
                "line_total":    final_p,
                "line_profit":   profit,
            })
            item_id += 1

        # Nullify revenue for cancelled/returned
        if status in ("Cancelled", "Returned"):
            order_total  = 0.0
            order_profit = 0.0

        ship_days   = random.randint(1, 7)
        shipped_at  = None if status == "Cancelled" else (
            order_date + timedelta(days=ship_days)
        ).strftime("%Y-%m-%d")

        orders.append({
            "order_id":      f"ORD{i:07d}",
            "customer_id":   cust_id,
            "order_date":    order_date.strftime("%Y-%m-%d"),
            "shipped_date":  shipped_at,
            "status":        status,
            "channel":       channel,
            "payment_method": payment,
            "order_total":   round(order_total, 2),
            "order_profit":  round(order_profit, 2),
            "num_items":     num_items,
        })

    orders_df = pd.DataFrame(orders)
    items_df  = pd.DataFrame(items)
    log.info(f"Generated {len(orders_df)} orders, {len(items_df)} line items")
    log.info(f"Order statuses: {orders_df['status'].value_counts().to_dict()}")
    return orders_df, items_df


# ─── Marketing Campaigns ──────────────────────────────────────────────────────

CAMPAIGN_TYPES = ["Email", "Social Media", "Search Ads", "Display", "Influencer", "Event"]
CAMPAIGN_GOALS = ["Awareness", "Lead Gen", "Conversion", "Retention"]


def generate_campaigns(n: int) -> list[dict]:
    campaigns = []
    for i in range(1, n + 1):
        start = rand_date(START, DAYS - 60)
        dur   = random.randint(14, 90)
        end   = start + timedelta(days=dur)
        budget     = round(random.uniform(5000, 200000), 2)
        spend      = round(budget * random.uniform(0.75, 1.05), 2)
        impressions = random.randint(10000, 2000000)
        clicks      = int(impressions * random.uniform(0.01, 0.08))
        conversions = int(clicks * random.uniform(0.02, 0.15))
        revenue_gen = round(conversions * random.uniform(500, 5000), 2)

        campaigns.append({
            "campaign_id":    f"CAMP{i:04d}",
            "name":           f"{random.choice(CAMPAIGN_TYPES)} Campaign {i:02d}",
            "type":           random.choice(CAMPAIGN_TYPES),
            "goal":           random.choice(CAMPAIGN_GOALS),
            "start_date":     start.strftime("%Y-%m-%d"),
            "end_date":       end.strftime("%Y-%m-%d"),
            "budget":         budget,
            "spend":          spend,
            "impressions":    impressions,
            "clicks":         clicks,
            "conversions":    conversions,
            "revenue_generated": revenue_gen,
            "ctr":            round(clicks / impressions * 100, 3),
            "conversion_rate": round(conversions / clicks * 100, 3) if clicks else 0,
            "roi":            round((revenue_gen - spend) / spend * 100, 2) if spend else 0,
            "status":         "Active" if end > datetime.now() else "Completed",
        })

    log.info(f"Generated {len(campaigns)} marketing campaigns")
    return campaigns


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Starting synthetic data generation")
    log.info("=" * 60)

    # Customers
    customers = generate_customers(NUM_CUSTOMERS)
    customers.to_csv(RAW_DATA_DIR / "customers.csv", index=False)
    log.info(f"Saved customers.csv  ({len(customers)} rows)")

    # Products
    products = generate_products(NUM_PRODUCTS)
    products.to_csv(RAW_DATA_DIR / "products.csv", index=False)
    log.info(f"Saved products.csv   ({len(products)} rows)")

    # Orders + Items
    orders, items = generate_orders_and_items(NUM_ORDERS, customers, products)
    orders.to_csv(RAW_DATA_DIR / "orders.csv",      index=False)
    items.to_csv( RAW_DATA_DIR / "order_items.csv", index=False)
    log.info(f"Saved orders.csv     ({len(orders)} rows)")
    log.info(f"Saved order_items.csv ({len(items)} rows)")

    # Campaigns — saved as JSON to show mixed format handling
    campaigns = generate_campaigns(NUM_CAMPAIGNS)
    with open(RAW_DATA_DIR / "campaigns.json", "w") as f:
        json.dump(campaigns, f, indent=2)
    log.info(f"Saved campaigns.json ({len(campaigns)} records)")

    log.info("=" * 60)
    log.info("Data generation complete")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
