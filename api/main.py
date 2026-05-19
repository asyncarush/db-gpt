from agent.graph import agent


sample_tables_metadata = [
    {
        "table_name": "users",
        "description": "Stores user account information including profile details, authentication data, and account status."
    },
    {
        "table_name": "orders",
        "description": "Contains customer purchase orders, order status, total amount, and order timestamps."
    },
    {
        "table_name": "products",
        "description": "Maintains product catalog information such as product name, category, pricing, and inventory."
    },
    {
        "table_name": "payments",
        "description": "Tracks payment transactions, payment methods, transaction status, and billing details."
    },
    {
        "table_name": "employees",
        "description": "Stores employee records including department, designation, salary, and joining date."
    },
    {
        "table_name": "customers",
        "description": "Contains customer personal details, contact information, and customer activity data."
    },
    {
        "table_name": "support_tickets",
        "description": "Manages customer support tickets, issue categories, resolution status, and assigned agents."
    },
    {
        "table_name": "inventory",
        "description": "Tracks warehouse inventory levels, stock movements, supplier information, and reorder thresholds."
    },
    {
        "table_name": "shipments",
        "description": "Stores shipment tracking details, delivery status, courier information, and shipment timelines."
    },
    {
        "table_name": "audit_logs",
        "description": "Maintains system audit logs including user activities, security events, and data access history."
    }
]

fake_table_schemas = [
    {
        "table_name": "users",
        "schema": """
        users (
            id INTEGER,
            full_name TEXT,
            email TEXT,
            phone_number TEXT,
            city TEXT,
            created_at TIMESTAMP,
            account_status TEXT
        )
        """
    },
    {
        "table_name": "customers",
        "schema": """
        customers (
            id INTEGER,
            customer_name TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP
        )
        """
    },
    {
        "table_name": "employees",
        "schema": """
        employees (
            id INTEGER,
            employee_name TEXT,
            department TEXT,
            designation TEXT,
            salary NUMERIC,
            joining_date DATE
        )
        """
    },
    {
        "table_name": "products",
        "schema": """
        products (
            id INTEGER,
            product_name TEXT,
            category TEXT,
            price NUMERIC,
            stock_quantity INTEGER,
            created_at TIMESTAMP
        )
        """
    },
    {
        "table_name": "inventory",
        "schema": """
        inventory (
            id INTEGER,
            product_id INTEGER,
            warehouse_location TEXT,
            available_stock INTEGER,
            reorder_level INTEGER,
            last_updated TIMESTAMP
        )
        """
    },
    {
        "table_name": "orders",
        "schema": """
        orders (
            id INTEGER,
            customer_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total_amount NUMERIC,
            order_status TEXT,
            order_date TIMESTAMP
        )
        """
    },
    {
        "table_name": "payments",
        "schema": """
        payments (
            id INTEGER,
            order_id INTEGER,
            payment_method TEXT,
            payment_status TEXT,
            transaction_amount NUMERIC,
            transaction_date TIMESTAMP
        )
        """
    },
    {
        "table_name": "shipments",
        "schema": """
        shipments (
            id INTEGER,
            order_id INTEGER,
            courier_name TEXT,
            tracking_number TEXT,
            shipment_status TEXT,
            shipped_at TIMESTAMP,
            delivered_at TIMESTAMP
        )
        """
    },
    {
        "table_name": "support_tickets",
        "schema": """
        support_tickets (
            id INTEGER,
            customer_id INTEGER,
            assigned_employee_id INTEGER,
            issue_category TEXT,
            ticket_status TEXT,
            created_at TIMESTAMP,
            resolved_at TIMESTAMP
        )
        """
    },
    {
        "table_name": "audit_logs",
        "schema": """
        audit_logs (
            id INTEGER,
            user_id INTEGER,
            action_type TEXT,
            entity_name TEXT,
            ip_address TEXT,
            created_at TIMESTAMP
        )
        """
    }
]


def main():
    agent.invoke({ 
        "available_tables": [], 
        "messages": [
            { 
                "role": "user", 
                "content": "Find products generating more revenue than average product revenue"
            }
        ], 
        "table_metadata": sample_tables_metadata,
        "fake_table_schemas": fake_table_schemas
    })


if __name__ == "__main__":
    main()