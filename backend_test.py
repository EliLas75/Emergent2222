import requests
import sys
import io
import csv
from datetime import datetime

class FinancialAPITester:
    def __init__(self, base_url="https://24cba78b-7653-49b3-a6cb-b5003d39b8bb.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.uploaded_data_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {}
        if not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    print(f"   Response: {response.text}")
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def create_sample_csv(self):
        """Create a sample financial CSV for testing"""
        csv_data = [
            ['Date', 'Revenus', 'Charges', 'EBITDA', 'Resultat_Net', 'Cash_Flow', 'Investissements'],
            ['2024-01', '100000', '60000', '45000', '25000', '30000', '5000'],
            ['2024-02', '120000', '70000', '55000', '30000', '35000', '8000'],
            ['2024-03', '110000', '65000', '50000', '28000', '32000', '6000'],
            ['2024-04', '130000', '75000', '60000', '35000', '40000', '10000'],
            ['2024-05', '125000', '72000', '58000', '33000', '38000', '7000']
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        csv_content = output.getvalue()
        output.close()
        
        return csv_content

    def test_api_root(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "",
            200
        )
        return success and "Financial Analytics API" in str(response)

    def test_csv_upload(self):
        """Test CSV file upload"""
        csv_content = self.create_sample_csv()
        
        files = {
            'file': ('test_financial_data.csv', csv_content, 'text/csv')
        }
        
        success, response = self.run_test(
            "CSV Upload",
            "POST",
            "upload-csv",
            200,
            files=files
        )
        
        if success and isinstance(response, dict):
            # Verify response structure
            required_keys = ['id', 'filename', 'detected_columns', 'kpis', 'data_preview']
            has_all_keys = all(key in response for key in required_keys)
            
            if has_all_keys:
                self.uploaded_data_id = response['id']
                print(f"   ✅ Response has all required keys")
                print(f"   📊 KPIs calculated: {response['kpis']}")
                print(f"   🔍 Detected columns: {response['detected_columns']}")
                return True
            else:
                print(f"   ❌ Missing required keys in response")
                return False
        
        return success

    def test_invalid_file_upload(self):
        """Test uploading non-CSV file"""
        files = {
            'file': ('test.txt', 'This is not a CSV file', 'text/plain')
        }
        
        success, response = self.run_test(
            "Invalid File Upload",
            "POST",
            "upload-csv",
            400,
            files=files
        )
        return success

    def test_get_financial_data_by_id(self):
        """Test getting financial data by ID"""
        if not self.uploaded_data_id:
            print("❌ Skipping - No uploaded data ID available")
            return False
            
        success, response = self.run_test(
            "Get Financial Data by ID",
            "GET",
            f"financial-data/{self.uploaded_data_id}",
            200
        )
        return success

    def test_get_all_financial_data(self):
        """Test getting all financial data"""
        success, response = self.run_test(
            "Get All Financial Data",
            "GET",
            "financial-data",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   📊 Found {len(response)} financial data records")
            return True
        
        return success

    def test_get_nonexistent_data(self):
        """Test getting non-existent financial data"""
        success, response = self.run_test(
            "Get Non-existent Data",
            "GET",
            "financial-data/nonexistent-id",
            404
        )
        return success

def main():
    print("🚀 Starting Financial Analytics API Tests")
    print("=" * 50)
    
    tester = FinancialAPITester()
    
    # Test sequence
    tests = [
        ("API Root Endpoint", tester.test_api_root),
        ("CSV Upload", tester.test_csv_upload),
        ("Invalid File Upload", tester.test_invalid_file_upload),
        ("Get Financial Data by ID", tester.test_get_financial_data_by_id),
        ("Get All Financial Data", tester.test_get_all_financial_data),
        ("Get Non-existent Data", tester.test_get_nonexistent_data),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*50}")
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())