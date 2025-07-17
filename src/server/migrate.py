import asyncio
import sqlite3
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session_maker, create_tables
from models import Transaction, Device, Product, TransactionItem

async def migrate_existing_data():
    """Migrate data from old SQLite schema to new schema"""
    
    # Create tables first
    await create_tables()
    
    # Connect to old database
    old_db = sqlite3.connect('transactions.db')
    old_cursor = old_db.cursor()
    
    async with async_session_maker() as session:
        try:
            # Create default device if not exists
            device = Device(
                device_id="default",
                name="Main Vending Machine",
                location="Default Location"
            )
            session.add(device)
            await session.flush()
            
            # Migrate transactions
            old_cursor.execute("SELECT * FROM transactions")
            old_transactions = old_cursor.fetchall()
            
            for old_tx in old_transactions:
                transaction_id, payment_intent_id, items_json, status, created_at, updated_at = old_tx
                
                # Parse items JSON
                items = json.loads(items_json) if items_json else []
                
                # Create new transaction
                new_tx = Transaction(
                    transaction_id=transaction_id,
                    device_id=device.id,
                    payment_intent_id=payment_intent_id,
                    status=status,
                    created_at=datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else datetime.now(),
                    updated_at=datetime.fromisoformat(updated_at.replace('Z', '+00:00')) if updated_at else datetime.now()
                )
                session.add(new_tx)
                await session.flush()
                
                # Create products and transaction items
                total_amount = 0
                for item in items:
                    # Create product if not exists
                    product = Product(
                        name=item.get('name', 'Unknown Product'),
                        price=float(item.get('price', 0)),
                        sku=item.get('id', f"product_{item.get('name', 'unknown')}")
                    )
                    session.add(product)
                    await session.flush()
                    
                    # Create transaction item
                    quantity = int(item.get('quantity', 1))
                    unit_price = float(item.get('price', 0))
                    subtotal = quantity * unit_price
                    total_amount += subtotal
                    
                    tx_item = TransactionItem(
                        transaction_id=new_tx.id,
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=subtotal
                    )
                    session.add(tx_item)
                
                # Update transaction total
                new_tx.total_amount = total_amount
            
            await session.commit()
            print(f"Migrated {len(old_transactions)} transactions")
            
        except Exception as e:
            await session.rollback()
            print(f"Migration failed: {e}")
            raise
    
    old_db.close()

if __name__ == "__main__":
    asyncio.run(migrate_existing_data())