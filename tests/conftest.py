"""
conftest.py - Pytest configuration and fixtures for VisionVend

This module provides fixtures for testing the VisionVend system:
- Mock MQTT client and broker
- Test database setup and teardown
- Mock Stripe API
- Test configuration
- FastAPI test client
- Sample transaction data
- Utility functions for testing
"""

import asyncio
import json
import os
import random
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Generator, AsyncGenerator, Optional

import pytest
import yaml
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from paho.mqtt import client as mqtt_client
from pytest_mock import MockFixture
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import the application and models
# These imports will be adjusted based on your actual project structure
try:
    from VisionVend.server.app import app as fastapi_app
    from VisionVend.utils.security import generate_hmac
except ImportError:
    # For tests that run without the full application installed
    fastapi_app = None


# ----------------------
# Path and Environment Fixtures
# ----------------------

@pytest.fixture(scope="session")
def test_dir() -> Path:
    """Return the directory containing the tests."""
    return Path(__file__).parent


@pytest.fixture(scope="session")
def temp_dir(tmp_path_factory) -> Path:
    """Create and return a temporary directory for test artifacts."""
    temp = tmp_path_factory.mktemp("visionvend_test")
    yield temp
    # Clean up temp directory after tests
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture(scope="session")
def env_setup() -> Generator[None, None, None]:
    """Set up environment variables for testing."""
    # Store original environment variables
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["STRIPE_API_KEY"] = "sk_test_example"
    os.environ["HMAC_SECRET"] = "test_hmac_secret"
    os.environ["JWT_SECRET_KEY"] = "test_jwt_secret"
    os.environ["CONFIG_PATH"] = "tests/fixtures/test_config.yaml"
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)


# ----------------------
# Configuration Fixtures
# ----------------------

@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Load test configuration from YAML file."""
    config_path = Path("tests/fixtures/test_config.yaml")
    if not config_path.exists():
        # Create a default test config if it doesn't exist
        config = {
            "mqtt": {
                "broker": "localhost",
                "port": 1883,
                "client_id": "test_client",
                "unlock_topic": "test/unlock",
                "status_topic": "test/status",
                "door_topic": "test/door",
                "hmac_secret": "test_hmac_secret"
            },
            "stripe": {
                "api_key": "sk_test_example"
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "url": "http://localhost:8000"
            },
            "inventory": {
                "test_cola": {"price": 2.00, "weight": 355, "tolerance": 5},
                "test_chips": {"price": 1.50, "weight": 70, "tolerance": 4}
            }
        }
        
        # Ensure the fixtures directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the config to file
        with open(config_path, "w") as f:
            yaml.dump(config, f)
    else:
        # Load existing config
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    
    return config


@pytest.fixture
def override_config(test_config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    """Create a copy of the test config that can be modified for specific tests."""
    config_copy = json.loads(json.dumps(test_config))  # Deep copy
    yield config_copy


# ----------------------
# Database Fixtures
# ----------------------

@pytest.fixture(scope="session")
def db_path(temp_dir: Path) -> Path:
    """Return the path to the test database."""
    return temp_dir / "test.db"


@pytest.fixture
def db_engine(db_path: Path):
    """Create a SQLAlchemy engine for the test database."""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Import and create tables if models are available
    try:
        from VisionVend.models import Base
        Base.metadata.create_all(engine)
    except ImportError:
        pass  # Skip if models are not available
    
    yield engine
    
    # Close engine connections
    engine.dispose()


@pytest.fixture
async def async_db_engine(db_path: Path):
    """Create an async SQLAlchemy engine for the test database."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    
    # Import and create tables if models are available
    try:
        from VisionVend.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ImportError:
        pass  # Skip if models are not available
    
    yield engine
    
    # Close engine connections
    await engine.dispose()


@pytest.fixture
async def db_session(async_db_engine):
    """Create a SQLAlchemy async session for database operations."""
    async_session = sessionmaker(
        async_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        # Rollback any changes made during the test
        await session.rollback()


# ----------------------
# MQTT Fixtures
# ----------------------

class MockMQTTClient:
    """Mock MQTT client for testing."""
    
    def __init__(self, client_id: str = "test_client"):
        self.client_id = client_id
        self.connected = False
        self.subscribed_topics = set()
        self.published_messages = []
        self.received_messages = []
        self.callbacks = {
            "on_connect": None,
            "on_message": None,
            "on_disconnect": None,
            "on_subscribe": None,
            "on_publish": None
        }
    
    def connect(self, broker: str, port: int):
        """Mock connect method."""
        self.connected = True
        if self.callbacks["on_connect"]:
            self.callbacks["on_connect"](self, None, None, 0)
        return 0
    
    def disconnect(self):
        """Mock disconnect method."""
        self.connected = False
        if self.callbacks["on_disconnect"]:
            self.callbacks["on_disconnect"](self, None, 0)
        return 0
    
    def subscribe(self, topic: str):
        """Mock subscribe method."""
        self.subscribed_topics.add(topic)
        if self.callbacks["on_subscribe"]:
            self.callbacks["on_subscribe"](self, None, None, 0)
        return (0, 0)
    
    def publish(self, topic: str, payload: str):
        """Mock publish method."""
        message = {"topic": topic, "payload": payload, "timestamp": time.time()}
        self.published_messages.append(message)
        if self.callbacks["on_publish"]:
            self.callbacks["on_publish"](self, None, None)
        
        # Create a result object with rc attribute
        class Result:
            rc = 0
        
        return Result()
    
    def loop_start(self):
        """Mock loop_start method."""
        pass
    
    def loop_stop(self):
        """Mock loop_stop method."""
        pass
    
    def is_connected(self):
        """Mock is_connected method."""
        return self.connected
    
    def simulate_message(self, topic: str, payload: str):
        """Simulate receiving a message."""
        if topic in self.subscribed_topics and self.callbacks["on_message"]:
            # Create a mock message object
            class Message:
                def __init__(self, topic, payload):
                    self.topic = topic
                    self.payload = payload.encode() if isinstance(payload, str) else payload
                
                def decode(self):
                    return self.payload.decode() if isinstance(self.payload, bytes) else self.payload
            
            msg = Message(topic, payload)
            self.received_messages.append({"topic": topic, "payload": payload, "timestamp": time.time()})
            self.callbacks["on_message"](self, None, msg)


@pytest.fixture
def mock_mqtt_client(monkeypatch: pytest.MonkeyPatch, test_config: Dict[str, Any]):
    """Create a mock MQTT client for testing."""
    client = MockMQTTClient()
    
    # Monkeypatch the mqtt_client.Client to return our mock
    def mock_client(*args, **kwargs):
        return client
    
    # Apply the monkeypatch if mqtt_client is available
    try:
        import paho.mqtt.client
        monkeypatch.setattr(paho.mqtt.client, "Client", mock_client)
    except ImportError:
        pass
    
    return client


@pytest.fixture
def mqtt_message_factory(mock_mqtt_client: MockMQTTClient, test_config: Dict[str, Any]):
    """Create a factory function for generating MQTT messages."""
    
    def create_message(topic: str, payload: Dict[str, Any], use_hmac: bool = True):
        """Create and send a mock MQTT message."""
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)
        
        if use_hmac and "hmac_secret" in test_config.get("mqtt", {}):
            hmac_secret = test_config["mqtt"]["hmac_secret"]
            hmac_val = generate_hmac(payload_str.encode(), hmac_secret)
            full_payload = f"{payload_str}|{hmac_val}"
        else:
            full_payload = payload_str
        
        mock_mqtt_client.simulate_message(topic, full_payload)
        return {"topic": topic, "payload": full_payload}
    
    return create_message


# ----------------------
# Stripe Mock Fixtures
# ----------------------

@pytest.fixture
def mock_stripe(monkeypatch: pytest.MonkeyPatch):
    """Mock the Stripe API for testing."""
    
    class MockStripePaymentIntent:
        """Mock Stripe PaymentIntent class."""
        
        @staticmethod
        def create(**kwargs):
            """Mock create method."""
            intent_id = f"pi_{random.randint(100000, 999999)}"
            return type("PaymentIntent", (), {
                "id": intent_id,
                "client_secret": f"{intent_id}_secret",
                "amount": kwargs.get("amount", 0),
                "currency": kwargs.get("currency", "usd"),
                "status": "requires_confirmation"
            })
        
        @staticmethod
        def modify(intent_id, **kwargs):
            """Mock modify method."""
            return type("PaymentIntent", (), {
                "id": intent_id,
                "amount": kwargs.get("amount", 0),
                "status": "requires_capture"
            })
        
        @staticmethod
        def capture(intent_id):
            """Mock capture method."""
            return type("PaymentIntent", (), {
                "id": intent_id,
                "status": "succeeded"
            })
        
        @staticmethod
        def cancel(intent_id):
            """Mock cancel method."""
            return type("PaymentIntent", (), {
                "id": intent_id,
                "status": "canceled"
            })
    
    class MockStripeCustomer:
        """Mock Stripe Customer class."""
        
        @staticmethod
        def create(**kwargs):
            """Mock create method."""
            customer_id = f"cus_{random.randint(100000, 999999)}"
            return type("Customer", (), {
                "id": customer_id,
                "email": kwargs.get("email", "test@example.com")
            })
        
        @staticmethod
        def modify(customer_id, **kwargs):
            """Mock modify method."""
            return type("Customer", (), {
                "id": customer_id
            })
    
    class MockStripePaymentMethod:
        """Mock Stripe PaymentMethod class."""
        
        @staticmethod
        def attach(payment_method_id, **kwargs):
            """Mock attach method."""
            return type("PaymentMethod", (), {
                "id": payment_method_id,
                "customer": kwargs.get("customer")
            })
    
    class MockStripeBalance:
        """Mock Stripe Balance class."""
        
        @staticmethod
        def retrieve():
            """Mock retrieve method."""
            return type("Balance", (), {
                "available": [{"amount": 10000, "currency": "usd"}],
                "pending": [{"amount": 0, "currency": "usd"}]
            })
    
    # Create a mock Stripe module
    mock_stripe_module = type("stripe", (), {
        "PaymentIntent": MockStripePaymentIntent,
        "Customer": MockStripeCustomer,
        "PaymentMethod": MockStripePaymentMethod,
        "Balance": MockStripeBalance,
        "api_key": "sk_test_example",
        "error": type("error", (), {
            "StripeError": Exception,
            "CardError": Exception,
            "InvalidRequestError": Exception
        })
    })
    
    # Apply the monkeypatch if stripe is available
    try:
        import stripe
        for attr in dir(mock_stripe_module):
            if not attr.startswith("__"):
                monkeypatch.setattr(stripe, attr, getattr(mock_stripe_module, attr))
    except ImportError:
        pass
    
    return mock_stripe_module


# ----------------------
# FastAPI Test Client Fixtures
# ----------------------

@pytest.fixture
def app() -> FastAPI:
    """Return the FastAPI application for testing."""
    if fastapi_app is None:
        pytest.skip("FastAPI app not available")
    return fastapi_app


@pytest.fixture
def test_client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient for testing."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async client for testing FastAPI endpoints."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        async with LifespanManager(app):
            yield client


# ----------------------
# Sample Data Fixtures
# ----------------------

@pytest.fixture
def sample_transaction_data() -> Dict[str, Any]:
    """Generate sample transaction data for testing."""
    transaction_id = f"txn_{random.randint(100000, 999999)}"
    return {
        "transaction_id": transaction_id,
        "items": [
            {"sku": "test_cola", "qty": 1},
            {"sku": "test_chips", "qty": 2}
        ],
        "payment_intent_id": f"pi_{random.randint(100000, 999999)}",
        "total": 5.00,  # $2.00 for cola + $1.50 x 2 for chips
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_unlock_request() -> Dict[str, Any]:
    """Generate a sample unlock request for testing."""
    return {
        "id": f"txn_{random.randint(100000, 999999)}"
    }


@pytest.fixture
def sample_payment_request() -> Dict[str, Any]:
    """Generate a sample payment method request for testing."""
    return {
        "payment_method_id": f"pm_{random.randint(100000, 999999)}",
        "customer_email": "test@example.com"
    }


@pytest.fixture
def sample_door_event(test_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a sample door event for testing."""
    transaction_id = f"txn_{random.randint(100000, 999999)}"
    items = ["test_cola", "test_chips"]
    delta_mass = 425.0  # 355g for cola + 70g for chips
    
    return {
        "transaction_id": transaction_id,
        "items": items,
        "delta_mass": delta_mass,
        "payload": f"{transaction_id}:{','.join(items)}:{delta_mass}"
    }


# ----------------------
# Utility Fixtures
# ----------------------

@pytest.fixture
def mock_file_system(tmp_path: Path) -> Path:
    """Create a mock file system for testing file operations."""
    # Create directories
    (tmp_path / "config").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "data").mkdir()
    
    # Create sample files
    with open(tmp_path / "config" / "test_config.yaml", "w") as f:
        yaml.dump({
            "test": True,
            "inventory": {
                "test_cola": {"price": 2.00, "weight": 355}
            }
        }, f)
    
    return tmp_path


@pytest.fixture
def mock_logger(mocker: MockFixture):
    """Mock the logger for testing."""
    return mocker.patch("VisionVend.utils.logging_config.get_logger", autospec=True)


@pytest.fixture
def capture_logs():
    """Capture logs during a test."""
    import logging
    
    # Create a handler that captures logs
    class LogCapture(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []
        
        def emit(self, record):
            self.records.append(record)
    
    # Create and add the capture handler
    capture_handler = LogCapture()
    root_logger = logging.getLogger()
    root_logger.addHandler(capture_handler)
    
    # Store the original level and set to DEBUG for tests
    original_level = root_logger.level
    root_logger.setLevel(logging.DEBUG)
    
    yield capture_handler.records
    
    # Restore original level and remove the handler
    root_logger.setLevel(original_level)
    root_logger.removeHandler(capture_handler)


@pytest.fixture
def mock_time(monkeypatch: pytest.MonkeyPatch):
    """Mock time.time() for predictable timestamps."""
    start_time = time.time()
    
    class MockTime:
        current_time = start_time
        
        @classmethod
        def time(cls):
            return cls.current_time
        
        @classmethod
        def sleep(cls, seconds):
            cls.current_time += seconds
    
    monkeypatch.setattr(time, "time", MockTime.time)
    monkeypatch.setattr(time, "sleep", MockTime.sleep)
    
    return MockTime


# ----------------------
# Pytest Configuration
# ----------------------

def pytest_configure(config):
    """Configure pytest for VisionVend tests."""
    # Register custom markers
    config.addinivalue_line("markers", "mqtt: mark tests that use MQTT")
    config.addinivalue_line("markers", "stripe: mark tests that use Stripe")
    config.addinivalue_line("markers", "hardware: mark tests that interact with hardware")
    config.addinivalue_line("markers", "integration: mark integration tests")
    config.addinivalue_line("markers", "slow: mark tests that are slow")


@pytest.fixture(autouse=True)
def setup_test_env():
    """Automatically set up the test environment for all tests."""
    # Set test environment variables
    os.environ["TESTING"] = "1"
    
    yield
    
    # Clean up any test-specific environment variables
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
