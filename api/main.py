from agent.graph import agent

tables_metadata = [
    {
        "table_name": "olist_orders_dataset",
        "description": "Core transactional fact table containing one record per customer order placed on the Olist marketplace. This table represents the complete order lifecycle from purchase to delivery. Includes order identifiers, customer identifiers, order status, purchase timestamp, payment approval timestamp, carrier delivery timestamp, customer delivery timestamp, and estimated delivery timestamp. This table acts as the central hub connecting customers, payments, reviews, products, sellers, and logistics data. Commonly used for revenue analysis, order trend analysis, delivery performance tracking, operational KPIs, fulfillment analytics, cancellation analysis, and customer behavior analysis. Frequently joined with olist_customers_dataset using customer_id, olist_order_items_dataset using order_id, olist_order_payments_dataset using order_id, and olist_order_reviews_dataset using order_id."
    },
    {
        "table_name": "olist_customers_dataset",
        "description": "Dimension table containing customer identity and delivery location information. Stores customer_id, customer_unique_id, zip code prefix, city, and state. customer_id is unique per order, meaning the same real-world customer may have multiple customer_id values across multiple purchases. customer_unique_id should be used to identify repeat customers and customer retention behavior across orders. Frequently used for customer segmentation, cohort analysis, repeat purchase analysis, geographic sales analysis, regional demand analysis, and customer lifetime value calculations. Common joins include joining with olist_orders_dataset using customer_id and joining with olist_geolocation_dataset using zip code prefixes for geospatial analysis."
    },
    {
        "table_name": "olist_order_items_dataset",
        "description": "Transactional line-item table containing product-level details for each order. Each row represents a single product item purchased within an order. Includes order_id, order_item_id, product_id, seller_id, shipping_limit_date, item price, and freight value. Orders may contain multiple products and multiple sellers. Freight values are calculated at the item level and should be aggregated to compute total shipping cost per order. Used extensively for revenue calculations, product sales analysis, seller performance analysis, shipping cost analysis, inventory demand analysis, and marketplace basket analysis. Frequently joined with olist_orders_dataset using order_id, olist_products_dataset using product_id, and olist_sellers_dataset using seller_id."
    },
    {
        "table_name": "olist_order_payments_dataset",
        "description": "Fact table containing payment transaction details associated with customer orders. Includes order_id, payment sequential number, payment type, payment installments, and payment value. Orders may have multiple payment records due to split payments or multiple payment methods. Payment types include credit card, boleto, voucher, debit card, and others. Commonly used for financial reporting, payment behavior analysis, installment analysis, fraud detection patterns, payment method popularity analysis, and average order value calculations. Frequently joined with olist_orders_dataset using order_id."
    },
    {
        "table_name": "olist_order_reviews_dataset",
        "description": "Customer feedback and satisfaction table containing review information associated with completed orders. Includes review identifiers, order_id, review score, review title, review message, review creation timestamp, and review response timestamp. Review scores typically range from 1 to 5 and are widely used as customer satisfaction KPIs. Reviews are generally submitted after order delivery or estimated delivery date expiration. Commonly used for customer sentiment analysis, seller quality evaluation, product satisfaction analysis, operational issue detection, delayed delivery impact analysis, and review trend analysis. Frequently joined with olist_orders_dataset using order_id and indirectly linked to products and sellers through order items."
    },
    {
        "table_name": "olist_products_dataset",
        "description": "Product dimension table containing catalog metadata for products sold on the Olist marketplace. Includes product_id, product category name, product name length, product description length, product photo quantity, product weight in grams, product length, product height, and product width. Used for product catalog analysis, inventory intelligence, product performance analysis, logistics optimization, shipping cost estimation, category-level analytics, and product recommendation analysis. Product dimensions and weight are particularly important for freight cost analysis and warehouse optimization scenarios. Frequently joined with olist_order_items_dataset using product_id and product_category_name_translation using product_category_name."
    },
    {
        "table_name": "olist_sellers_dataset",
        "description": "Seller dimension table containing marketplace seller information including seller identifiers, zip code prefix, city, and state. Represents merchants or vendors fulfilling customer orders on the marketplace platform. Used for seller performance evaluation, regional seller analysis, fulfillment efficiency tracking, logistics analysis, marketplace concentration analysis, and operational benchmarking. Frequently joined with olist_order_items_dataset using seller_id and optionally joined with olist_geolocation_dataset using zip code prefixes for geographic and distance-based logistics analysis."
    },
    {
        "table_name": "olist_geolocation_dataset",
        "description": "Reference geospatial table containing Brazilian zip code geolocation data including zip code prefix, latitude, longitude, city, and state. Used primarily for geographic analysis, logistics optimization, route estimation, seller-customer distance calculations, regional clustering, geospatial visualization, and mapping use cases. Multiple records may exist for the same zip code prefix due to geographic granularity variations. Frequently joined with customer and seller datasets using zip code prefixes for delivery distance and regional analytics."
    },
    {
        "table_name": "product_category_name_translation",
        "description": "Lookup table used for translating Portuguese product category names into English-readable category labels. Contains original Portuguese product_category_name and corresponding English translation. Useful for international reporting, dashboard readability, multilingual analytics, and natural language query interpretation. Frequently joined with olist_products_dataset using product_category_name."
    }
]

def main():
   response = agent.invoke({ 
        "messages": [
            { 
                "role": "user", 
                "content": "What were the top 10 product categories by revenue in Q4 2017, and how did they compare to Q3?"
            }
        ], 
        "table_metadata": tables_metadata
    })

if __name__ == "__main__":
    main()




#What were the top 10 product categories by revenue in Q4 2017, and how did they compare to Q3?