#!/bin/bash

# Phoenix Widget Backend Deployment Test Script
# Usage: ./test_deployment.sh

API_URL="https://phoenix-widget-backend-production-f686.up.railway.app"

echo "🚀 Testing Phoenix Widget Backend Deployment"
echo "URL: $API_URL"
echo "================================="

# Test 1: Health Check
echo "1. Testing Health Endpoint..."
health_response=$(curl -s "$API_URL/health")
if [[ $health_response == *"\"status\":\"ok\""* ]]; then
    echo "   ✅ Health check PASSED: $health_response"
else
    echo "   ❌ Health check FAILED: $health_response"
    exit 1
fi

echo ""

# Test 2: Basic Chat
echo "2. Testing Chat Endpoint..."
chat_response=$(curl -s -X POST "$API_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "What is Phoenix Technologies?"}')

if [[ $chat_response == *"\"response\":"* ]]; then
    echo "   ✅ Chat endpoint PASSED"
    echo "   Response preview: $(echo $chat_response | jq -r '.response' | head -c 100)..."
else
    echo "   ❌ Chat endpoint FAILED: $chat_response"
    exit 1
fi

echo ""

# Test 3: Error Handling
echo "3. Testing Error Handling..."
error_response=$(curl -s -X POST "$API_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": ""}')

if [[ $error_response == *"Error: Please provide a valid message"* ]]; then
    echo "   ✅ Error handling PASSED"
else
    echo "   ❌ Error handling FAILED: $error_response"
fi

echo ""
echo "🎉 All tests completed successfully!"
echo "Your Phoenix Widget Backend deployment is healthy and ready to use."

