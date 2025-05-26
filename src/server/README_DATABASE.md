# VisionVend Database Setup

## Overview
The VisionVend database has been upgraded from simple SQLite to a proper SQLAlchemy ORM with async support, migrations, and structured relationships.

## Database Schema

### Tables
- **devices** - Vending machine devices
- **products** - Product catalog with pricing
- **device_inventory** - Inventory levels per device/product
- **transactions** - Payment and transaction records
- **transaction_items** - Individual items in transactions
- **users** - Customer records
- **audit_logs** - Change tracking

### Key Relationships
- Device → Transactions (one-to-many)
- Device → Inventory (one-to-many)
- Product → Inventory (one-to-many)
- Transaction → TransactionItems (one-to-many)

## Setup Instructions

1. **Create Virtual Environment**:
   ```bash
   ./setup_venv.sh
   ```

2. **Manual Setup** (if script fails):
   ```bash
   cd /mnt/c/Users/david/Documents/Artificial-Me-Org/VisionVend
   python3 -m venv venv
   source venv/bin/activate
   cd src/server
   pip install -r requirements.txt
   pip install aiosqlite
   ```

3. **Test Database**:
   ```bash
   python test_database.py
   ```

4. **Migrate Existing Data** (if you have old transactions.db):
   ```bash
   python migrate.py
   ```

## Running the Server

```bash
source venv/bin/activate
cd src/server
uvicorn app:app --reload
```

## Database Files
- `visionvend.db` - Main SQLite database
- `alembic/` - Migration system
- `models.py` - Database schema definitions
- `database.py` - Connection management

## Migration Commands

Generate new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

## Changes from Old System

### Before
- Raw SQLite with `aiosqlite`
- Single `transactions` table
- Items stored as JSON strings
- Manual SQL queries

### After
- SQLAlchemy ORM with async support
- Proper normalized schema
- Foreign key relationships
- Type-safe model operations
- Migration system with Alembic

## API Changes

The `/unlock` endpoint now:
- Uses dependency injection for database sessions
- Creates proper Transaction model instances
- Links to default Device automatically
- Maintains backward compatibility