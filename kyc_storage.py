# import json
# import os
# from datetime import datetime
# from typing import Dict, List, Optional
# from minio import Minio
# from minio.error import S3Error
# import uuid
#
#
# class KYCMinIOStorage:
#     """Enhanced MinIO storage for KYC verification data with admin panel support"""
#
#     def __init__(self):
#         self.client = Minio(
#             "objectstorageapi.nugenesisou.com",
#             access_key="QzSM21wSjuOrX19BFNbd",
#             secret_key="uGxkxm6chB0XK6GiU8vJT5va76BGjuAk0vS0PFnf",
#             secure=True
#         )
#
#         # Bucket names for different types of data
#         self.kyc_bucket = "kyc-verifications"
#         self.admin_bucket = "kyc-admin-data"
#
#         # Create buckets if they don't exist
#         self._create_buckets()
#
#     def _create_buckets(self):
#         """Create necessary buckets for KYC storage"""
#         buckets = [self.kyc_bucket, self.admin_bucket]
#         for bucket in buckets:
#             try:
#                 if not self.client.bucket_exists(bucket):
#                     self.client.make_bucket(bucket)
#                     print(f"✅ Created bucket: {bucket}")
#             except S3Error as e:
#                 print(f"❌ Error creating bucket {bucket}: {e}")
#
#     def save_kyc_verification(self,
#                               verification_id: str,
#                               email: str,
#                               id_image_path: str,
#                               video_path: str,
#                               status: str,  # "pass" or "fail"
#                               confidence_score: float,
#                               id_details: dict,
#                               error_message: str = None) -> Dict:
#         """
#         Save complete KYC verification data to MinIO
#         Returns the storage summary
#         """
#         try:
#             timestamp = datetime.now()
#             date_folder = timestamp.strftime("%Y/%m/%d")
#
#             # Create organized folder structure: kyc-verifications/2024/06/30/email@domain.com/verification_id/
#             base_path = f"{date_folder}/{email}/{verification_id}"
#
#             # 1. Save ID card image
#             id_image_name = f"{base_path}/id_card.jpg"
#             id_result = self._upload_with_metadata(
#                 self.kyc_bucket,
#                 id_image_name,
#                 id_image_path,
#                 {
#                     "verification-id": verification_id,
#                     "email": email,
#                     "file-type": "id-card",
#                     "timestamp": timestamp.isoformat(),
#                     "status": status
#                 }
#             )
#
#             # 2. Save selfie video
#             video_ext = os.path.splitext(video_path)[1]
#             video_name = f"{base_path}/selfie_video{video_ext}"
#             video_result = self._upload_with_metadata(
#                 self.kyc_bucket,
#                 video_name,
#                 video_path,
#                 {
#                     "verification-id": verification_id,
#                     "email": email,
#                     "file-type": "selfie-video",
#                     "timestamp": timestamp.isoformat(),
#                     "status": status
#                 }
#             )
#
#             # 3. Create comprehensive metadata JSON
#             metadata = {
#                 "verification_id": verification_id,
#                 "email": email,
#                 "timestamp": timestamp.isoformat(),
#                 "status": status,
#                 "confidence_score": confidence_score,
#                 "files": {
#                     "id_card": id_image_name,
#                     "selfie_video": video_name
#                 },
#                 "id_details": id_details,
#                 "error_message": error_message,
#                 "processing_info": {
#                     "date": timestamp.strftime("%Y-%m-%d"),
#                     "time": timestamp.strftime("%H:%M:%S"),
#                     "month": timestamp.strftime("%Y-%m"),
#                     "year": timestamp.strftime("%Y")
#                 }
#             }
#
#             # 4. Save metadata JSON file
#             metadata_name = f"{base_path}/metadata.json"
#             metadata_result = self._upload_json_data(
#                 self.kyc_bucket,
#                 metadata_name,
#                 metadata,
#                 {
#                     "verification-id": verification_id,
#                     "email": email,
#                     "file-type": "metadata",
#                     "timestamp": timestamp.isoformat(),
#                     "status": status
#                 }
#             )
#
#             # 5. Save to admin index for quick querying
#             self._update_admin_index(email, verification_id, status, timestamp, metadata)
#
#             # 6. Save daily summary
#             self._update_daily_summary(timestamp.strftime("%Y-%m-%d"), status, email)
#
#             return {
#                 "success": True,
#                 "verification_id": verification_id,
#                 "base_path": base_path,
#                 "files_saved": {
#                     "id_card": id_result,
#                     "video": video_result,
#                     "metadata": metadata_result
#                 },
#                 "metadata": metadata
#             }
#
#         except Exception as e:
#             print(f"❌ Error saving KYC verification: {e}")
#             return {"success": False, "error": str(e)}
#
#     def _upload_with_metadata(self, bucket: str, object_name: str, file_path: str, metadata: Dict) -> bool:
#         """Upload file with custom metadata"""
#         try:
#             # Convert metadata to string format (MinIO requirement)
#             string_metadata = {f"x-amz-meta-{k}": str(v) for k, v in metadata.items()}
#
#             self.client.fput_object(
#                 bucket,
#                 object_name,
#                 file_path,
#                 metadata=string_metadata
#             )
#             print(f"✅ Uploaded: {object_name}")
#             return True
#         except Exception as e:
#             print(f"❌ Upload failed for {object_name}: {e}")
#             return False
#
#     def _upload_json_data(self, bucket: str, object_name: str, data: Dict, metadata: Dict = None) -> bool:
#         """Upload JSON data as object"""
#         try:
#             import io
#             json_data = json.dumps(data, indent=2)
#             json_bytes = io.BytesIO(json_data.encode('utf-8'))
#
#             upload_metadata = {"content-type": "application/json"}
#             if metadata:
#                 upload_metadata.update({f"x-amz-meta-{k}": str(v) for k, v in metadata.items()})
#
#             self.client.put_object(
#                 bucket,
#                 object_name,
#                 json_bytes,
#                 length=len(json_data),
#                 content_type="application/json",
#                 metadata=upload_metadata
#             )
#             print(f"✅ Uploaded JSON: {object_name}")
#             return True
#         except Exception as e:
#             print(f"❌ JSON upload failed for {object_name}: {e}")
#             return False
#
#     def _update_admin_index(self, email: str, verification_id: str, status: str, timestamp: datetime, metadata: Dict):
#         """Update admin index for quick querying"""
#         try:
#             # Create monthly index entry
#             month_key = timestamp.strftime("%Y-%m")
#             index_path = f"admin/monthly_index/{month_key}.json"
#
#             # Try to get existing index
#             try:
#                 response = self.client.get_object(self.admin_bucket, index_path)
#                 existing_index = json.loads(response.read().decode('utf-8'))
#             except:
#                 existing_index = {"month": month_key, "verifications": []}
#
#             # Add new verification
#             verification_summary = {
#                 "verification_id": verification_id,
#                 "email": email,
#                 "status": status,
#                 "timestamp": timestamp.isoformat(),
#                 "confidence_score": metadata.get("confidence_score", 0),
#                 "id_name": metadata.get("id_details", {}).get("name", "N/A")
#             }
#
#             existing_index["verifications"].append(verification_summary)
#
#             # Save updated index
#             self._upload_json_data(self.admin_bucket, index_path, existing_index)
#
#         except Exception as e:
#             print(f"⚠️ Warning: Could not update admin index: {e}")
#
#     def _update_daily_summary(self, date: str, status: str, email: str):
#         """Update daily summary statistics"""
#         try:
#             summary_path = f"admin/daily_summaries/{date}.json"
#
#             # Try to get existing summary
#             try:
#                 response = self.client.get_object(self.admin_bucket, summary_path)
#                 summary = json.loads(response.read().decode('utf-8'))
#             except:
#                 summary = {
#                     "date": date,
#                     "total_verifications": 0,
#                     "passed": 0,
#                     "failed": 0,
#                     "unique_emails": set()
#                 }
#
#             # Update summary
#             summary["total_verifications"] += 1
#             if status == "pass":
#                 summary["passed"] += 1
#             else:
#                 summary["failed"] += 1
#
#             summary["unique_emails"].add(email)
#
#             # Convert set to list for JSON serialization
#             summary_json = {
#                 **summary,
#                 "unique_emails": list(summary["unique_emails"]),
#                 "unique_users_count": len(summary["unique_emails"])
#             }
#
#             # Save updated summary
#             self._upload_json_data(self.admin_bucket, summary_path, summary_json)
#
#         except Exception as e:
#             print(f"⚠️ Warning: Could not update daily summary: {e}")
#
#
# # Admin Panel Query Functions
# class KYCAdminQueries:
#     """Query functions for KYC admin panel"""
#
#     def __init__(self, storage: KYCMinIOStorage):
#         self.storage = storage
#         self.client = storage.client
#         self.kyc_bucket = storage.kyc_bucket
#         self.admin_bucket = storage.admin_bucket
#
#     def get_verification_by_id(self, verification_id: str) -> Optional[Dict]:
#         """Get verification data by verification ID"""
#         try:
#             # List all objects and find the one with matching verification ID
#             objects = self.client.list_objects(self.kyc_bucket, recursive=True)
#
#             for obj in objects:
#                 if verification_id in obj.object_name and obj.object_name.endswith('metadata.json'):
#                     response = self.client.get_object(self.kyc_bucket, obj.object_name)
#                     metadata = json.loads(response.read().decode('utf-8'))
#
#                     # Add download URLs
#                     metadata['download_urls'] = {
#                         'id_card': self.client.presigned_get_object(self.kyc_bucket, metadata['files']['id_card']),
#                         'selfie_video': self.client.presigned_get_object(self.kyc_bucket,
#                                                                          metadata['files']['selfie_video']),
#                         'metadata': self.client.presigned_get_object(self.kyc_bucket, obj.object_name)
#                     }
#
#                     return metadata
#
#             return None
#         except Exception as e:
#             print(f"❌ Error getting verification by ID: {e}")
#             return None
#
#     def get_verifications_by_email(self, email: str, limit: int = 100) -> List[Dict]:
#         """Get all verifications for a specific email"""
#         try:
#             verifications = []
#             # List objects with email prefix
#             objects = self.client.list_objects(
#                 self.kyc_bucket,
#                 prefix=f"",  # Search all
#                 recursive=True
#             )
#
#             for obj in objects:
#                 if email in obj.object_name and obj.object_name.endswith('metadata.json'):
#                     response = self.client.get_object(self.kyc_bucket, obj.object_name)
#                     metadata = json.loads(response.read().decode('utf-8'))
#                     verifications.append(metadata)
#
#                     if len(verifications) >= limit:
#                         break
#
#             return sorted(verifications, key=lambda x: x['timestamp'], reverse=True)
#         except Exception as e:
#             print(f"❌ Error getting verifications by email: {e}")
#             return []
#
#     def get_daily_summary(self, date: str) -> Optional[Dict]:
#         """Get daily summary statistics"""
#         try:
#             summary_path = f"admin/daily_summaries/{date}.json"
#             response = self.client.get_object(self.admin_bucket, summary_path)
#             return json.loads(response.read().decode('utf-8'))
#         except Exception as e:
#             print(f"❌ Error getting daily summary: {e}")
#             return None
#
#     def get_monthly_index(self, month: str) -> Optional[Dict]:
#         """Get monthly verification index (YYYY-MM format)"""
#         try:
#             index_path = f"admin/monthly_index/{month}.json"
#             response = self.client.get_object(self.admin_bucket, index_path)
#             return json.loads(response.read().decode('utf-8'))
#         except Exception as e:
#             print(f"❌ Error getting monthly index: {e}")
#             return None
#
#     def search_verifications(self,
#                              start_date: str = None,
#                              end_date: str = None,
#                              status: str = None,
#                              email_filter: str = None) -> List[Dict]:
#         """Search verifications with filters"""
#         try:
#             results = []
#
#             # If date range provided, search monthly indices
#             if start_date and end_date:
#                 from datetime import datetime, timedelta
#                 start = datetime.strptime(start_date, "%Y-%m-%d")
#                 end = datetime.strptime(end_date, "%Y-%m-%d")
#
#                 current = start.replace(day=1)  # Start of month
#                 while current <= end:
#                     month_key = current.strftime("%Y-%m")
#                     monthly_data = self.get_monthly_index(month_key)
#
#                     if monthly_data:
#                         for verification in monthly_data['verifications']:
#                             # Apply filters
#                             if status and verification['status'] != status:
#                                 continue
#                             if email_filter and email_filter.lower() not in verification['email'].lower():
#                                 continue
#
#                             results.append(verification)
#
#                     # Move to next month
#                     if current.month == 12:
#                         current = current.replace(year=current.year + 1, month=1)
#                     else:
#                         current = current.replace(month=current.month + 1)
#
#             return sorted(results, key=lambda x: x['timestamp'], reverse=True)
#         except Exception as e:
#             print(f"❌ Error searching verifications: {e}")
#             return []
#
#
# # Integration with existing KYC API
# def integrate_with_existing_kyc_api():
#     """
#     Example of how to integrate this with your existing process_verification function
#     """
#
#     # Add this to your existing code after the verification is complete
#     def enhanced_process_verification(id_image_path, video_path, verification_id, user_id=None, session_id=None):
#         """Enhanced version of your process_verification function"""
#
#         # ... your existing verification logic ...
#
#         # After verification is complete, save to MinIO
#         try:
#             storage = KYCMinIOStorage()
#
#             # Determine status
#             status = "pass" if final_match else "fail"
#
#             # Save to MinIO
#             storage_result = storage.save_kyc_verification(
#                 verification_id=verification_id,
#                 email=user_id if is_email(user_id) else "unknown@domain.com",
#                 id_image_path=id_image_path,
#                 video_path=video_path,
#                 status=status,
#                 confidence_score=final_score,
#                 id_details=id_details.dict() if id_details else {},
#                 error_message=None if final_match else "Face verification failed"
#             )
#
#             if storage_result["success"]:
#                 logger.info(f"✅ KYC data saved to MinIO: {verification_id}")
#             else:
#                 logger.error(f"❌ Failed to save KYC data to MinIO: {storage_result.get('error')}")
#
#         except Exception as e:
#             logger.error(f"❌ Error saving to MinIO: {e}")
#
#         # ... rest of your existing logic ...
#
#
# # Example usage for admin panel
# def admin_panel_examples():
#     """Examples of how to use this for an admin panel"""
#
#     storage = KYCMinIOStorage()
#     admin = KYCAdminQueries(storage)
#
#     # Example 1: Get specific verification
#     verification = admin.get_verification_by_id("some-uuid-here")
#     if verification:
#         print(f"Found verification for {verification['email']}")
#         print(f"Status: {verification['status']}")
#         print(f"Download ID card: {verification['download_urls']['id_card']}")
#
#     # Example 2: Get daily summary
#     today = datetime.now().strftime("%Y-%m-%d")
#     daily_stats = admin.get_daily_summary(today)
#     if daily_stats:
#         print(f"Today: {daily_stats['passed']} passed, {daily_stats['failed']} failed")
#
#     # Example 3: Search with filters
#     recent_failures = admin.search_verifications(
#         start_date="2024-06-01",
#         end_date="2024-06-30",
#         status="fail"
#     )
#     print(f"Found {len(recent_failures)} failed verifications this month")
#
#
# if __name__ == "__main__":
#     # Test the storage system
#     storage = KYCMinIOStorage()
#     print("✅ KYC MinIO Storage system initialized")


import json
import os
import tempfile
import logging
from datetime import datetime
from typing import Dict, List, Optional
from minio import Minio
from minio.error import S3Error


class KYCMinIOStorage:
    """Enhanced MinIO storage for KYC verification data with admin panel support"""

    def __init__(self):
        # Initialize logger for this class
        self.logger = logging.getLogger(f"{__name__}.KYCMinIOStorage")

        self.client = Minio(
            "objectstorageapi.nugenesisou.com",
            access_key="QzSM21wSjuOrX19BFNbd",
            secret_key="uGxkxm6chB0XK6GiU8vJT5va76BGjuAk0vS0PFnf",
            secure=True
        )

        # Bucket names for different types of data
        self.kyc_bucket = "kyc-verifications"
        self.admin_bucket = "kyc-admin-data"

        # Create buckets if they don't exist
        self._create_buckets()

    def _create_buckets(self):
        """Create necessary buckets for KYC storage"""
        buckets = [self.kyc_bucket, self.admin_bucket]
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    self.logger.info(f"✅ Created MinIO bucket: {bucket}")
            except S3Error as e:
                self.logger.error(f"❌ Error creating bucket {bucket}: {e}")

    def save_kyc_verification(self,
                              verification_id: str,
                              email: str,
                              id_image_path: str,
                              video_path: str,
                              status: str,  # "pass" or "fail"
                              confidence_score: float,
                              id_details: dict,
                              error_message: str = None) -> Dict:
        """
        Save complete KYC verification data to MinIO
        Returns the storage summary
        """
        try:
            timestamp = datetime.now()
            date_folder = timestamp.strftime("%Y/%m/%d")

            # Create organized folder structure: kyc-verifications/2024/06/30/email@domain.com/verification_id/
            base_path = f"{date_folder}/{email}/{verification_id}"

            # 1. Save ID card image
            id_image_name = f"{base_path}/id_card.jpg"
            id_result = self._upload_with_metadata(
                self.kyc_bucket,
                id_image_name,
                id_image_path,
                {
                    "verification-id": verification_id,
                    "email": email,
                    "file-type": "id-card",
                    "timestamp": timestamp.isoformat(),
                    "status": status
                }
            )

            # 2. Save selfie video
            video_ext = os.path.splitext(video_path)[1]
            video_name = f"{base_path}/selfie_video{video_ext}"
            video_result = self._upload_with_metadata(
                self.kyc_bucket,
                video_name,
                video_path,
                {
                    "verification-id": verification_id,
                    "email": email,
                    "file-type": "selfie-video",
                    "timestamp": timestamp.isoformat(),
                    "status": status
                }
            )

            # 3. Create comprehensive metadata JSON
            metadata = {
                "verification_id": verification_id,
                "email": email,
                "timestamp": timestamp.isoformat(),
                "status": status,
                "confidence_score": confidence_score,
                "files": {
                    "id_card": id_image_name,
                    "selfie_video": video_name
                },
                "id_details": id_details,
                "error_message": error_message,
                "processing_info": {
                    "date": timestamp.strftime("%Y-%m-%d"),
                    "time": timestamp.strftime("%H:%M:%S"),
                    "month": timestamp.strftime("%Y-%m"),
                    "year": timestamp.strftime("%Y")
                }
            }

            # 4. Save metadata JSON file
            metadata_name = f"{base_path}/metadata.json"
            metadata_result = self._upload_json_data(
                self.kyc_bucket,
                metadata_name,
                metadata,
                {
                    "verification-id": verification_id,
                    "email": email,
                    "file-type": "metadata",
                    "timestamp": timestamp.isoformat(),
                    "status": status
                }
            )

            # 5. Save to admin index for quick querying
            self._update_admin_index(email, verification_id, status, timestamp, metadata)

            # 6. Save daily summary
            self._update_daily_summary(timestamp.strftime("%Y-%m-%d"), status, email)

            return {
                "success": True,
                "verification_id": verification_id,
                "base_path": base_path,
                "files_saved": {
                    "id_card": id_result,
                    "video": video_result,
                    "metadata": metadata_result
                },
                "metadata": metadata
            }

        except Exception as e:
            self.logger.error(f"❌ Error saving KYC verification to MinIO: {e}")
            return {"success": False, "error": str(e)}

    def _upload_with_metadata(self, bucket: str, object_name: str, file_path: str, metadata: Dict) -> bool:
        """Upload file with custom metadata"""
        try:
            # Convert metadata to string format (MinIO requirement)
            string_metadata = {f"x-amz-meta-{k}": str(v) for k, v in metadata.items()}

            self.client.fput_object(
                bucket,
                object_name,
                file_path,
                metadata=string_metadata
            )
            self.logger.debug(f"✅ Uploaded to MinIO: {object_name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ MinIO upload failed for {object_name}: {e}")
            return False

    def _upload_json_data(self, bucket: str, object_name: str, data: Dict, metadata: Dict = None) -> bool:
        """Upload JSON data as object using temporary file approach"""
        try:
            # Create temporary file for JSON data
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                json.dump(data, temp_file, indent=2)
                temp_file_path = temp_file.name

            try:
                # Prepare metadata for fput_object (same format as other uploads)
                upload_metadata = {}
                if metadata:
                    upload_metadata.update({f"x-amz-meta-{k}": str(v) for k, v in metadata.items()})

                # Use fput_object instead of put_object for consistency
                self.client.fput_object(
                    bucket,
                    object_name,
                    temp_file_path,
                    content_type="application/json",
                    metadata=upload_metadata
                )
                self.logger.debug(f"✅ Uploaded JSON to MinIO: {object_name}")
                return True

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        except Exception as e:
            self.logger.error(f"❌ MinIO JSON upload failed for {object_name}: {e}")
            return False

    def _update_admin_index(self, email: str, verification_id: str, status: str, timestamp: datetime, metadata: Dict):
        """Update admin index for quick querying"""
        try:
            # Create monthly index entry
            month_key = timestamp.strftime("%Y-%m")
            index_path = f"admin/monthly_index/{month_key}.json"

            # Try to get existing index
            try:
                response = self.client.get_object(self.admin_bucket, index_path)
                existing_index = json.loads(response.read().decode('utf-8'))
            except:
                existing_index = {"month": month_key, "verifications": []}

            # Add new verification
            verification_summary = {
                "verification_id": verification_id,
                "email": email,
                "status": status,
                "timestamp": timestamp.isoformat(),
                "confidence_score": metadata.get("confidence_score", 0),
                "id_name": metadata.get("id_details", {}).get("name", "N/A")
            }

            existing_index["verifications"].append(verification_summary)

            # Save updated index
            self._upload_json_data(self.admin_bucket, index_path, existing_index)

        except Exception as e:
            self.logger.warning(f"⚠️ Could not update admin index: {e}")

    def _update_daily_summary(self, date: str, status: str, email: str):
        """Update daily summary statistics"""
        try:
            summary_path = f"admin/daily_summaries/{date}.json"

            # Try to get existing summary
            try:
                response = self.client.get_object(self.admin_bucket, summary_path)
                summary = json.loads(response.read().decode('utf-8'))
                # Convert unique_emails back to set for processing
                summary["unique_emails"] = set(summary.get("unique_emails", []))
            except:
                summary = {
                    "date": date,
                    "total_verifications": 0,
                    "passed": 0,
                    "failed": 0,
                    "unique_emails": set()
                }

            # Update summary
            summary["total_verifications"] += 1
            if status == "pass":
                summary["passed"] += 1
            else:
                summary["failed"] += 1

            summary["unique_emails"].add(email)

            # Convert set to list for JSON serialization
            summary_json = {
                **summary,
                "unique_emails": list(summary["unique_emails"]),
                "unique_users_count": len(summary["unique_emails"])
            }

            # Save updated summary
            self._upload_json_data(self.admin_bucket, summary_path, summary_json)

        except Exception as e:
            self.logger.warning(f"⚠️ Could not update daily summary: {e}")


# Admin Panel Query Functions
class KYCAdminQueries:
    """Query functions for KYC admin panel"""

    def __init__(self, storage: KYCMinIOStorage):
        self.logger = logging.getLogger(f"{__name__}.KYCAdminQueries")
        self.storage = storage
        self.client = storage.client
        self.kyc_bucket = storage.kyc_bucket
        self.admin_bucket = storage.admin_bucket

    def get_verification_by_id(self, verification_id: str) -> Optional[Dict]:
        """Get verification data by verification ID"""
        try:
            # List all objects and find the one with matching verification ID
            objects = self.client.list_objects(self.kyc_bucket, recursive=True)

            for obj in objects:
                if verification_id in obj.object_name and obj.object_name.endswith('metadata.json'):
                    response = self.client.get_object(self.kyc_bucket, obj.object_name)
                    metadata = json.loads(response.read().decode('utf-8'))

                    # Add download URLs
                    metadata['download_urls'] = {
                        'id_card': self.client.presigned_get_object(self.kyc_bucket, metadata['files']['id_card']),
                        'selfie_video': self.client.presigned_get_object(self.kyc_bucket,
                                                                         metadata['files']['selfie_video']),
                        'metadata': self.client.presigned_get_object(self.kyc_bucket, obj.object_name)
                    }

                    return metadata

            return None
        except Exception as e:
            self.logger.error(f"❌ Error getting verification by ID: {e}")
            return None

    def get_verifications_by_email(self, email: str, limit: int = 100) -> List[Dict]:
        """Get all verifications for a specific email"""
        try:
            verifications = []
            # List objects with email prefix
            objects = self.client.list_objects(
                self.kyc_bucket,
                prefix=f"",  # Search all
                recursive=True
            )

            for obj in objects:
                if email in obj.object_name and obj.object_name.endswith('metadata.json'):
                    response = self.client.get_object(self.kyc_bucket, obj.object_name)
                    metadata = json.loads(response.read().decode('utf-8'))
                    verifications.append(metadata)

                    if len(verifications) >= limit:
                        break

            return sorted(verifications, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            self.logger.error(f"❌ Error getting verifications by email: {e}")
            return []

    def get_daily_summary(self, date: str) -> Optional[Dict]:
        """Get daily summary statistics"""
        try:
            summary_path = f"admin/daily_summaries/{date}.json"
            response = self.client.get_object(self.admin_bucket, summary_path)
            return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.logger.error(f"❌ Error getting daily summary: {e}")
            return None

    def get_monthly_index(self, month: str) -> Optional[Dict]:
        """Get monthly verification index (YYYY-MM format)"""
        try:
            index_path = f"admin/monthly_index/{month}.json"
            response = self.client.get_object(self.admin_bucket, index_path)
            return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.logger.error(f"❌ Error getting monthly index: {e}")
            return None

    def search_verifications(self,
                             start_date: str = None,
                             end_date: str = None,
                             status: str = None,
                             email_filter: str = None) -> List[Dict]:
        """Search verifications with filters"""
        try:
            results = []

            # If date range provided, search monthly indices
            if start_date and end_date:
                from datetime import datetime, timedelta
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                current = start.replace(day=1)  # Start of month
                while current <= end:
                    month_key = current.strftime("%Y-%m")
                    monthly_data = self.get_monthly_index(month_key)

                    if monthly_data:
                        for verification in monthly_data['verifications']:
                            # Apply filters
                            if status and verification['status'] != status:
                                continue
                            if email_filter and email_filter.lower() not in verification['email'].lower():
                                continue

                            results.append(verification)

                    # Move to next month
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)

            return sorted(results, key=lambda x: x['timestamp'], reverse=True)
        except Exception as e:
            self.logger.error(f"❌ Error searching verifications: {e}")
            return []


if __name__ == "__main__":
    # Test the storage system
    storage = KYCMinIOStorage()
    print("✅ KYC MinIO Storage system initialized")