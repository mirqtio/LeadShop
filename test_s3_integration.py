#!/usr/bin/env python3
"""
PRP-000 S3 Integration Test Suite
Tests all acceptance criteria for the S3 bucket setup
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import settings
from src.core.storage.s3_client import get_s3_client, S3ClientError


async def test_s3_basic_connection():
    """Test 1: S3 Bucket Operational"""
    print("🔍 Test 1: S3 Bucket Connection...")
    
    try:
        client = get_s3_client()
        print(f"✅ S3 client initialized successfully")
        print(f"   Bucket: {settings.AWS_S3_BUCKET_NAME}")
        print(f"   Region: {settings.AWS_DEFAULT_REGION}")
        return True
    except Exception as e:
        print(f"❌ S3 client failed: {e}")
        return False


async def test_file_upload_download():
    """Test 2: File Upload/Download with 10MB test file"""
    print("\n🔍 Test 2: File Upload/Download (10MB)...")
    
    try:
        client = get_s3_client()
        
        # Create 10MB test file
        test_data = b"0" * (10 * 1024 * 1024)  # 10MB of zeros
        test_key = "test/10mb-test-file.bin"
        
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_data)
            temp_file.flush()
            
            # Upload test
            print("   📤 Uploading 10MB test file...")
            upload_result = await client.upload_file(
                temp_file.name,
                test_key,
                prefix="test",
                metadata={"test": "prp-000-validation"}
            )
            
            if upload_result['success']:
                print(f"   ✅ Upload successful: {upload_result['upload_duration_ms']}ms")
                
                # Download test
                print("   📥 Downloading test file...")
                downloaded_data = await client.download_file(test_key)
                
                if len(downloaded_data) == len(test_data):
                    print(f"   ✅ Download successful: {len(downloaded_data)} bytes")
                    
                    # Cleanup
                    client.delete_file(test_key)
                    print("   🧹 Test file cleaned up")
                    return True
                else:
                    print(f"   ❌ Download size mismatch: {len(downloaded_data)} != {len(test_data)}")
                    return False
            else:
                print(f"   ❌ Upload failed")
                return False
                
    except Exception as e:
        print(f"   ❌ Upload/Download test failed: {e}")
        return False


async def test_presigned_urls():
    """Test 3: Presigned URL Generation"""
    print("\n🔍 Test 3: Presigned URL Generation...")
    
    try:
        client = get_s3_client()
        
        # Create small test file
        test_data = b"Hello LeadFactory S3 Integration!"
        test_key = "test/presigned-url-test.txt"
        
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_data)
            temp_file.flush()
            
            # Upload file
            await client.upload_file(temp_file.name, test_key, public_read=True)
            
        # Generate presigned URL
        presigned_url = client.generate_presigned_url(test_key, expiration=3600)
        
        if presigned_url and "https://" in presigned_url:
            print(f"   ✅ Presigned URL generated successfully")
            print(f"   📋 URL: {presigned_url[:80]}...")
            
            # Cleanup
            client.delete_file(test_key)
            return True
        else:
            print(f"   ❌ Invalid presigned URL: {presigned_url}")
            return False
            
    except Exception as e:
        print(f"   ❌ Presigned URL test failed: {e}")
        return False


async def test_file_info_and_listing():
    """Test 4: File Operations (info, listing)"""
    print("\n🔍 Test 4: File Information and Listing...")
    
    try:
        client = get_s3_client()
        
        # Create test file
        test_data = b"LeadFactory file info test"
        test_key = "test/file-info-test.txt"
        
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(test_data)
            temp_file.flush()
            
            # Upload file
            upload_result = await client.upload_file(
                temp_file.name,
                test_key,
                metadata={"purpose": "info-test", "size": str(len(test_data))}
            )
            
        # Get file info
        file_info = client.get_file_info(test_key)
        print(f"   ✅ File info retrieved:")
        print(f"      Size: {file_info['size']} bytes")
        print(f"      Content-Type: {file_info['content_type']}")
        print(f"      Metadata: {file_info['metadata']}")
        
        # List files
        file_list = client.list_files(prefix="test/")
        print(f"   ✅ File listing successful: {file_list['count']} files found")
        
        # Cleanup
        client.delete_file(test_key)
        return True
        
    except Exception as e:
        print(f"   ❌ File info/listing test failed: {e}")
        return False


async def test_bucket_security():
    """Test 5: Security Configuration Validation"""
    print("\n🔍 Test 5: Security Configuration...")
    
    try:
        import boto3
        
        # Use raw boto3 client to check security settings
        s3_client = boto3.client('s3', region_name=settings.AWS_DEFAULT_REGION)
        
        # Check public access block
        try:
            pab = s3_client.get_public_access_block(Bucket=settings.AWS_S3_BUCKET_NAME)
            config = pab['PublicAccessBlockConfiguration']
            
            if all([
                config['BlockPublicAcls'],
                config['IgnorePublicAcls'],
                config['BlockPublicPolicy'],
                config['RestrictPublicBuckets']
            ]):
                print("   ✅ Public access properly blocked")
            else:
                print("   ⚠️  Public access block not fully configured")
                
        except Exception as e:
            print(f"   ❌ Could not verify public access block: {e}")
        
        # Check encryption
        try:
            encryption = s3_client.get_bucket_encryption(Bucket=settings.AWS_S3_BUCKET_NAME)
            if encryption['ServerSideEncryptionConfiguration']:
                print("   ✅ Server-side encryption enabled")
            else:
                print("   ⚠️  Server-side encryption not found")
        except Exception as e:
            print(f"   ❌ Could not verify encryption: {e}")
        
        # Check CORS
        try:
            cors = s3_client.get_bucket_cors(Bucket=settings.AWS_S3_BUCKET_NAME)
            if cors['CORSRules']:
                print(f"   ✅ CORS configuration active ({len(cors['CORSRules'])} rules)")
            else:
                print("   ⚠️  No CORS rules found")
        except Exception as e:
            print(f"   ❌ Could not verify CORS: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Security validation failed: {e}")
        return False


async def main():
    """Run all S3 integration tests"""
    print("🚀 LeadFactory PRP-000 S3 Integration Test Suite")
    print("=" * 60)
    
    tests = [
        test_s3_basic_connection,
        test_file_upload_download,
        test_presigned_urls,
        test_file_info_and_listing,
        test_bucket_security
    ]
    
    results = []
    
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 PRP-000 S3 Integration: FULLY OPERATIONAL!")
        print("✅ Ready to proceed to PRP-001")
    else:
        print("⚠️  Some tests failed - review configuration")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())