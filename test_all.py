#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

async def run_tests():
    """Run comprehensive tests to verify fixes"""
    print("🔍 Running VisionVend tests...")
    
    # Test 1: Check config file
    config_path = Path("src/config/config.yaml")
    if not config_path.exists():
        print("❌ Config file missing")
        return False
    
    # Test 2: Check Python syntax
    try:
        import src.server.app
        import src.object_detection.product_tracker
        print("✅ All modules import successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test 3: Check database
    try:
        from src.server.test_database import test_database
        await test_database()
        print("✅ Database tests passed")
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    print("🎉 All tests passed!")
    return True

if __name__ == "__main__":
    asyncio.run(run_tests())