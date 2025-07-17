#!/usr/bin/env python3
"""Test script to verify database setup works correctly"""

import asyncio
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

async def test_database():
    try:
        print("Testing database setup...")
        
        # Import after path setup
        from database import create_tables, async_session_maker
        from models import Device, Product, Transaction, TransactionStatus
        
        print("✓ Imports successful")
        
        # Create tables
        await create_tables()
        print("✓ Tables created")
        
        # Test basic database operations
        async with async_session_maker() as session:
            # Create a test device
            device = Device(
                device_id="test_device",
                name="Test Vending Machine", 
                location="Test Location"
            )
            session.add(device)
            await session.commit()
            await session.refresh(device)
            print(f"✓ Device created with ID: {device.id}")
            
            # Create a test product
            product = Product(
                name="Test Product",
                price=1.50,
                sku="TEST001"
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)
            print(f"✓ Product created with ID: {product.id}")
            
            # Create a test transaction
            transaction = Transaction(
                transaction_id="test_tx_001",
                device_id=device.id,
                payment_intent_id="pi_test_123",
                status=TransactionStatus.PENDING_ITEMS,
                total_amount=1.50
            )
            session.add(transaction)
            await session.commit()
            print(f"✓ Transaction created with ID: {transaction.id}")
            
        print("\n🎉 Database setup test completed successfully!")
        print("Ready to start the FastAPI server.")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database())