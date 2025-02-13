import pytest
from fastapi.testclient import TestClient
from app import app, ChatRequest, ChatResponse
from load_tester import LoadTestConfig, WebsiteUser
import os
import json
from unittest.mock import patch, MagicMock

# Create test client
client = TestClient(app)

# Test data
TEST_MESSAGE = "Hello, how are you?"
MOCK_LLM_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": "I'm doing well, thank you for asking!"
            }
        }
    ]
}

@pytest.fixture
def mock_env_vars():
    """Fixture to set up environment variables"""
    os.environ["DATABRICKS_TOKEN"] = "test-token"
    os.environ["DATABRICKS_HOST"] = "test-host"
    os.environ["SERVING_ENDPOINT_NAME"] = "test-endpoint"
    yield
    del os.environ["DATABRICKS_TOKEN"]
    del os.environ["DATABRICKS_HOST"]
    del os.environ["SERVING_ENDPOINT_NAME"]

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/api/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

@pytest.mark.asyncio
async def test_chat_endpoint_success(mock_env_vars):
    """Test successful chat endpoint response"""
    with patch('httpx.AsyncClient.post') as mock_post:
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_LLM_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Make request
        response = client.post(
            "/api/chat",
            json={"message": TEST_MESSAGE}
        )

        # Assertions
        assert response.status_code == 200
        assert response.json() == {
            "content": "I'm doing well, thank you for asking!"
        }

@pytest.mark.asyncio
async def test_chat_endpoint_error(mock_env_vars):
    """Test chat endpoint error handling"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = Exception("API Error")
        
        response = client.post(
            "/api/chat",
            json={"message": TEST_MESSAGE}
        )
        
        assert response.status_code == 500
        assert "API Error" in response.json()["detail"]

@pytest.mark.asyncio
async def test_load_test_endpoint():
    """Test load testing endpoint"""
    test_params = {
        "users": 2,
        "spawn_rate": 1,
        "test_time": 2
    }
    
    response = client.get("/api/load-test", params=test_params)
    
    assert response.status_code == 200
    result = response.json()
    
    # Verify response structure
    assert "test_duration" in result
    assert "total_requests" in result
    assert "successful_requests" in result
    assert "failed_requests" in result
    assert "requests_per_second" in result
    assert "response_time" in result
    assert "errors" in result

def test_load_test_config_validation():
    """Test LoadTestConfig validation"""
    # Valid config
    config = LoadTestConfig(users=10, spawn_rate=2, test_time=30)
    assert config.users == 10
    assert config.spawn_rate == 2
    assert config.test_time == 30

    # Invalid config should raise validation error
    with pytest.raises(ValueError):
        LoadTestConfig(users=-1, spawn_rate=2, test_time=30)

@pytest.mark.asyncio
async def test_website_user():
    """Test WebsiteUser class"""
    user = WebsiteUser(environment=MagicMock())
    
    # Mock the client get method
    user.client = MagicMock()
    user.client.get.return_value = MagicMock(status_code=200)
    
    # Test the get_endpoint task
    user.get_endpoint()
    user.client.get.assert_called_once_with("/api/")

def test_invalid_chat_request():
    """Test invalid chat request handling"""
    response = client.post(
        "/api/chat",
        json={"invalid_field": "test"}
    )
    assert response.status_code == 422  # Validation error

def test_load_test_invalid_params():
    """Test load test endpoint with invalid parameters"""
    test_params = {
        "users": -1,  # Invalid value
        "spawn_rate": 1,
        "test_time": 2
    }
    
    response = client.get("/api/load-test", params=test_params)
    assert response.status_code == 422  # Validation error
