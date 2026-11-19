from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
    text,
)


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("email", String(320), nullable=False),
    Column("role", String(20), nullable=False, server_default=text("'user'")),
    Column("password_hash", String(255), nullable=False),
    UniqueConstraint("email", name="uq_users_email"),
    CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
)

products = Table(
    "products",
    metadata,
    Column("product_id", BigInteger, primary_key=True),
    Column("product_name", String(255), nullable=False),
    Column("stock_quantity", Integer, nullable=False),
    Column("price", Numeric(12, 2), nullable=False),
    Column("category", String(100), nullable=False),
    Column("last_update", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("stock_quantity >= 0", name="ck_products_stock_nonnegative"),
    CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
)

# Current store-credit balance. Consider adding a transaction ledger before
# using this for real payments or auditable account history.
account = Table(
    "account",
    metadata,
    Column("user_id", BigInteger, ForeignKey("users.id"), primary_key=True),
    Column("balance", Numeric(12, 2), nullable=False, server_default=text("0.00")),
    CheckConstraint("balance >= 0", name="ck_account_balance_nonnegative"),
)

orders = Table(
    "orders",
    metadata,
    Column("order_id", BigInteger, primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("status", String(20), nullable=False, server_default=text("'pending'")),
    Column("last_update", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

order_items = Table(
    "order_items",
    metadata,
    Column("order_item_id", BigInteger, primary_key=True),
    Column("order_id", BigInteger, ForeignKey("orders.order_id"), nullable=False),
    Column("product_id", BigInteger, ForeignKey("products.product_id"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(12, 2), nullable=False),
    CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_nonnegative"),
)