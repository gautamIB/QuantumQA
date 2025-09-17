# QuantumQA API - Quick Start Guide

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install fastapi uvicorn python-multipart cryptography PyYAML
```

### 2. Start the API Server
```bash
python api_complete.py
```

The server will be available at:
- **API Base URL**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs`
- **Alternative Docs**: `http://localhost:8000/redoc`

### 3. Verify Server is Running
```bash
curl http://localhost:8000/
```

---

## 📋 Common Operations

### Create a UI Test
```bash
curl -X POST "http://localhost:8000/test-configurations" \
  -F "test_name=my_first_test" \
  -F "test_type=UI" \
  -F "instruction=Navigate to https://google.com
Click on search box
Type hello world
Verify page loads successfully"
```

### Create an API Test
```bash
curl -X POST "http://localhost:8000/test-configurations" \
  -F "test_name=my_api_test" \
  -F "test_type=API" \
  -F "apis_documentation=name: Sample API Test
base_url: https://jsonplaceholder.typicode.com
tests:
  - name: Get Posts
    method: GET
    endpoint: /posts
    expected_status: 200"
```

### List All Tests
```bash
curl http://localhost:8000/test-configurations
```

### Execute a Test
```bash
curl -X POST "http://localhost:8000/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "env": "https://google.com",
    "credentials": {
      "username": "testuser",
      "password": "testpass"
    },
    "test_file_path": "Test/UI/my_first_test.txt",
    "test_type": "UI",
    "run_name": "test_run_1"
  }'
```

### Check Test Status
```bash
curl http://localhost:8000/runs/test_run_1
```

### Get All Runs
```bash
curl http://localhost:8000/runs
```

### Create Encrypted Credentials
```bash
# UI Credentials
curl -X POST "http://localhost:8000/credentials" \
  -H "Content-Type: application/json" \
  -d '{
    "credential_name": "my_ui_creds",
    "type": "UI",
    "environment": "staging",
    "description": "UI test credentials",
    "data": {
      "username": "testuser",
      "password": "testpass123"
    }
  }'

# API Credentials  
curl -X POST "http://localhost:8000/credentials" \
  -H "Content-Type: application/json" \
  -d '{
    "credential_name": "my_api_creds", 
    "type": "API",
    "environment": "production",
    "data": {
      "api_key": "sk-1234567890abcdef"
    }
  }'
```

### List Stored Credentials
```bash
curl http://localhost:8000/credentials
```

### Use Stored Credentials in Test
```bash
curl -X POST "http://localhost:8000/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "env": "https://app.example.com",
    "credential_id": "your-credential-id-here",
    "test_file_path": "Test/UI/my_first_test.txt",
    "test_type": "UI",
    "run_name": "secure_test_run"
  }'
```

---

## 📁 File Structure Created

When you start using the API, it will automatically create:

```
QuantumQA/
├── Test/
│   ├── UI/           # UI test files (.txt)
│   └── API/          # API test files (.yml)
├── logs/             # Test execution logs
├── reports/          # Test execution reports
└── credentials/      # Encrypted credentials storage
    ├── encryption.key    # Fernet encryption key
    └── *.json           # Individual credential files (encrypted)
```

---

## 🔧 Integration Tips

### For Frontend Developers

1. **Use Form Data for File Uploads**:
   ```javascript
   const formData = new FormData();
   formData.append('test_name', 'my_test');
   formData.append('test_type', 'UI');
   formData.append('instruction', testContent);
   ```

2. **Poll for Test Results**:
   ```javascript
   const pollResults = async (runName) => {
     const response = await fetch(`/runs/${runName}`);
     const data = await response.json();
     
     if (data.status === 'RUNNING') {
       setTimeout(() => pollResults(runName), 5000);
     }
     return data;
   };
   ```

3. **Handle Validation Errors**:
   ```javascript
   if (response.status === 400) {
     const error = await response.json();
     console.log('Validation errors:', error.validation.errors);
   }
   ```

### For Backend Developers

1. **Environment Variables**: Set up proper environment variables for production
2. **Authentication**: Add API key authentication for production use
3. **Monitoring**: Implement proper logging and monitoring
4. **Rate Limiting**: Add rate limiting for production deployment

---

## 🐛 Troubleshooting

### Server Won't Start
- Check if port 8000 is available
- Ensure all dependencies are installed
- Check Python version compatibility

### Tests Not Executing
- Verify test file exists at specified path
- Check credentials are provided for test type
- Review test validation status

### File Not Found Errors
- Ensure test was created successfully
- Check test name spelling
- Verify test type matches file location

---

## 📚 Next Steps

1. Review the full [API Documentation](./API_DOCUMENTATION.md)
2. Explore the interactive docs at `/docs`
3. Test the validation features with various test formats
4. Set up proper environment configuration for your deployment

Happy testing! 🎉
