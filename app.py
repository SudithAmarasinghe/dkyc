import streamlit as st
import requests
import json
import time
import pandas as pd
from PIL import Image
import io
import os
from datetime import datetime, timedelta
import hashlib
from kyc_storage import KYCMinIOStorage, KYCAdminQueries

# IMPORTANT: set_page_config must be the first Streamlit command
st.set_page_config(
    page_title="Digital KYC",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import MinIO classes (make sure kyc_storage.py is in the same directory)
try:
    # from kyc_storage import KYCMinIOStorage, KYCAdminQueries

    ADMIN_AVAILABLE = True
    ADMIN_ERROR = None
except ImportError as e:
    ADMIN_AVAILABLE = False
    ADMIN_ERROR = f"Import Error: {str(e)}"
except Exception as e:
    ADMIN_AVAILABLE = False
    ADMIN_ERROR = f"General Error: {str(e)}"

# Configure the API base URL
API_BASE_URL = "https://digit-wings-beauty-anti.trycloudflare.com"  # Change this to your actual API URL

# Add API endpoint configuration
API_ENDPOINTS = {
    "health": "/api/v1/health",
    "verify": "/api/v1/kyc/verify",
    "status": "/api/v1/kyc/status/"  # Note: verification_id will be appended to this
}

# Admin credentials
ADMIN_USERNAME = "NugenAdmin"
ADMIN_PASSWORD = "Nugenesisou@123"

# Function to get the full API URL
def get_api_url(endpoint_key, param=None):
    base = API_BASE_URL.rstrip('/')
    endpoint = API_ENDPOINTS[endpoint_key].lstrip('/')
    if param:
        return f"{base}/{endpoint}{param}"
    return f"{base}/{endpoint}"

def hash_password(password):
    """Simple password hashing for session management"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_admin_credentials(username, password):
    """Check admin credentials"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def admin_login():
    """Admin login form"""
    st.markdown('<p class="sub-header">Admin Login</p>', unsafe_allow_html=True)
    
    with st.form("admin_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if check_admin_credentials(username, password):
                st.session_state.admin_authenticated = True
                st.session_state.admin_user = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

def admin_logout():
    """Admin logout"""
    if st.button("Logout"):
        st.session_state.admin_authenticated = False
        st.session_state.admin_user = None
        st.success("Logged out successfully!")
        st.rerun()

def get_admin_storage():
    """Get MinIO storage instance (no caching for network connections)"""
    if not ADMIN_AVAILABLE:
        return None, None
    try:
        storage = KYCMinIOStorage()
        admin_queries = KYCAdminQueries(storage)
        return storage, admin_queries
    except Exception as e:
        st.error(f"❌ Failed to connect to MinIO: {e}")
        st.info("**Possible solutions:**")
        st.code("""
1. Check MinIO server is running on objectstorageapi.nugenesisou.com
2. Verify MinIO credentials are correct
3. Test MinIO connection manually:
   from kyc_storage import KYCMinIOStorage
   storage = KYCMinIOStorage()
        """)
        return None, None

def display_verification_summary(verification):
    """Display a single verification in a nice format"""
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
    
    with col1:
        st.write(f"**{verification.get('email', 'N/A')}**")
        st.write(f"ID: {verification.get('verification_id', 'N/A')[:8]}...")
        
    with col2:
        status = verification.get('status', 'unknown')
        if status == 'pass':
            st.success(f"✅ {status.upper()}")
        else:
            st.error(f"❌ {status.upper()}")
            
    with col3:
        confidence = verification.get('confidence_score', 0)
        st.write(f"**Confidence:** {confidence:.3f}")
        
    with col4:
        timestamp = verification.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                st.write(f"**Date:** {dt.strftime('%Y-%m-%d')}")
                st.write(f"**Time:** {dt.strftime('%H:%M:%S')}")
            except:
                st.write(f"**Time:** {timestamp[:19]}")

def admin_panel():
    """Main admin panel interface"""
    if not ADMIN_AVAILABLE:
        st.error("❌ Admin panel requires MinIO connection.")
        st.error(f"**Error Details:** {ADMIN_ERROR}")
        st.info("**Troubleshooting:**")
        st.code("""
1. Make sure kyc_storage.py is in the same directory as this app
2. Check that kyc_storage.py has no syntax errors
3. Ensure all required packages are installed:
   pip install minio logging datetime
        """)
        
        # Show current working directory for debugging
        import os
        st.info(f"**Current directory:** {os.getcwd()}")
        st.info(f"**Files in directory:** {os.listdir('.')}")
        return
        
    # Admin header with logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<p class="sub-header">Admin Dashboard</p>', unsafe_allow_html=True)
        st.info(f"Logged in as: {st.session_state.get('admin_user', 'Unknown')}")
    with col2:
        admin_logout()
    
    # Get storage instance
    storage, admin_queries = get_admin_storage()
    if not storage or not admin_queries:
        st.error("❌ Failed to connect to MinIO storage")
        st.warning("This could be due to:")
        st.markdown("""
        - MinIO server is not accessible
        - Wrong credentials in kyc_storage.py
        - Network connectivity issues
        - MinIO bucket permissions
        """)
        return
    
    # Admin tabs
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "📊 Dashboard", 
        "🔍 Search Records", 
        "📁 View by Email", 
        "📈 Statistics"
    ])
    
    with admin_tab1:
        st.markdown("### Recent Verifications")
        
        # Get today's date for recent verifications
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        try:
            # Get daily summaries
            today_summary = admin_queries.get_daily_summary(today)
            yesterday_summary = admin_queries.get_daily_summary(yesterday)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                today_total = today_summary.get('total_verifications', 0) if today_summary else 0
                st.metric("Today's Verifications", today_total)
                
            with col2:
                today_passed = today_summary.get('passed', 0) if today_summary else 0
                st.metric("Today's Passed", today_passed)
                
            with col3:
                today_failed = today_summary.get('failed', 0) if today_summary else 0
                st.metric("Today's Failed", today_failed)
                
            with col4:
                today_users = today_summary.get('unique_users_count', 0) if today_summary else 0
                st.metric("Unique Users Today", today_users)
            
            # Show recent verifications from current month
            current_month = datetime.now().strftime("%Y-%m")
            monthly_data = admin_queries.get_monthly_index(current_month)
            
            if monthly_data and 'verifications' in monthly_data:
                # Get last 10 verifications
                recent_verifications = sorted(
                    monthly_data['verifications'], 
                    key=lambda x: x.get('timestamp', ''), 
                    reverse=True
                )[:10]
                
                st.markdown("### Last 10 Verifications")
                for verification in recent_verifications:
                    with st.container():
                        display_verification_summary(verification)
                        st.divider()
            else:
                st.info("No verification data found for this month")
                
        except Exception as e:
            st.error(f"Error loading dashboard data: {e}")
    
    with admin_tab2:
        st.markdown("### Search Verification Records")
        
        # Search form
        with st.form("search_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                start_date = st.date_input(
                    "Start Date", 
                    value=datetime.now() - timedelta(days=30),
                    max_value=datetime.now()
                )
                status_filter = st.selectbox(
                    "Status Filter", 
                    ["All", "pass", "fail"]
                )
                
            with col2:
                end_date = st.date_input(
                    "End Date", 
                    value=datetime.now(),
                    max_value=datetime.now()
                )
                email_filter = st.text_input("Email Filter (optional)")
            
            search_button = st.form_submit_button("Search")
            
        if search_button:
            try:
                with st.spinner("Searching verification records..."):
                    # Convert dates to strings
                    start_str = start_date.strftime("%Y-%m-%d")
                    end_str = end_date.strftime("%Y-%m-%d")
                    
                    # Apply filters
                    status_param = None if status_filter == "All" else status_filter
                    email_param = email_filter if email_filter.strip() else None
                    
                    # Search
                    results = admin_queries.search_verifications(
                        start_date=start_str,
                        end_date=end_str,
                        status=status_param,
                        email_filter=email_param
                    )
                    
                    if results:
                        st.success(f"Found {len(results)} verification(s)")
                        
                        # Display results
                        for i, result in enumerate(results):
                            with st.expander(f"Verification {i+1}: {result.get('email', 'N/A')} - {result.get('status', 'unknown').upper()}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Verification ID:** {result.get('verification_id', 'N/A')}")
                                    st.write(f"**Email:** {result.get('email', 'N/A')}")
                                    st.write(f"**Status:** {result.get('status', 'N/A')}")
                                    st.write(f"**Confidence:** {result.get('confidence_score', 0):.3f}")
                                    
                                with col2:
                                    timestamp = result.get('timestamp', '')
                                    if timestamp:
                                        try:
                                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                            st.write(f"**Date:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                        except:
                                            st.write(f"**Timestamp:** {timestamp}")
                                    
                                    st.write(f"**ID Name:** {result.get('id_name', 'N/A')}")
                    else:
                        st.info("No verification records found for the specified criteria")
                        
            except Exception as e:
                st.error(f"Error searching records: {e}")
    
    with admin_tab3:
        st.markdown("### View Verifications by Email")
        
        email_input = st.text_input("Enter email address")
        limit_input = st.number_input("Number of records to show", min_value=1, max_value=100, value=10)
        
        if st.button("Get Verifications") and email_input:
            try:
                with st.spinner(f"Loading verifications for {email_input}..."):
                    verifications = admin_queries.get_verifications_by_email(email_input, limit_input)
                    
                    if verifications:
                        st.success(f"Found {len(verifications)} verification(s) for {email_input}")
                        
                        for i, verification in enumerate(verifications):
                            verification_id = verification.get('verification_id', 'N/A')
                            
                            with st.expander(f"Verification {i+1} - {verification.get('status', 'unknown').upper()}"):
                                # Display verification details
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Verification ID:** {verification_id}")
                                    st.write(f"**Status:** {verification.get('status', 'N/A')}")
                                    st.write(f"**Confidence Score:** {verification.get('confidence_score', 0):.3f}")
                                    
                                    # Error message if failed
                                    error_msg = verification.get('error_message')
                                    if error_msg:
                                        st.error(f"**Error:** {error_msg}")
                                
                                with col2:
                                    timestamp = verification.get('timestamp', '')
                                    if timestamp:
                                        try:
                                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                            st.write(f"**Date:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                        except:
                                            st.write(f"**Timestamp:** {timestamp}")
                                
                                # ID Details
                                id_details = verification.get('id_details', {})
                                if id_details:
                                    st.markdown("**ID Card Details:**")
                                    id_df = pd.DataFrame([
                                        {"Field": "Name", "Value": id_details.get('name', 'N/A')},
                                        {"Field": "ID Number", "Value": id_details.get('id_number', 'N/A')},
                                        {"Field": "Type", "Value": id_details.get('type_of_id', 'N/A')},
                                        {"Field": "Country", "Value": id_details.get('country', 'N/A')},
                                        {"Field": "Date of Birth", "Value": id_details.get('date_of_birth', 'N/A')},
                                        {"Field": "Address", "Value": id_details.get('address', 'N/A')},
                                    ])
                                    st.dataframe(id_df, use_container_width=True)
                                
                                # Always load and display files directly
                                st.markdown("---")
                                st.markdown("### 📁 Verification Files")
                                
                                try:
                                    # Get full verification details with download URLs
                                    full_verification = admin_queries.get_verification_by_id(verification_id)
                                    
                                    if full_verification and 'download_urls' in full_verification:
                                        download_urls = full_verification['download_urls']
                                        
                                        # Create two columns for side-by-side display
                                        file_col1, file_col2 = st.columns(2)
                                        
                                        # Display ID Card Image
                                        with file_col1:
                                            st.markdown("**📷 ID Card Image:**")
                                            if 'id_card' in download_urls:
                                                try:
                                                    st.image(download_urls['id_card'], caption="ID Card Image", use_column_width=True)
                                                except Exception as img_error:
                                                    st.error(f"Could not load ID card image")
                                                    st.caption(f"Error: {str(img_error)[:100]}...")
                                                    # Show file path for debugging
                                                    files = verification.get('files', {})
                                                    if files.get('id_card'):
                                                        st.caption(f"File: {files['id_card']}")
                                            else:
                                                st.warning("ID card image not available")
                                        
                                        # Display Selfie Video
                                        with file_col2:
                                            st.markdown("**🎥 Selfie Video:**")
                                            if 'selfie_video' in download_urls:
                                                try:
                                                    st.video(download_urls['selfie_video'])
                                                except Exception as vid_error:
                                                    st.error(f"Could not load selfie video")
                                                    st.caption(f"Error: {str(vid_error)[:100]}...")
                                                    # Show file path for debugging
                                                    files = verification.get('files', {})
                                                    if files.get('selfie_video'):
                                                        st.caption(f"File: {files['selfie_video']}")
                                            else:
                                                st.warning("Selfie video not available")
                                        
                                        # Show metadata download link
                                        if 'metadata' in download_urls:
                                            st.markdown("**📄 Additional Info:**")
                                            col_meta1, col_meta2 = st.columns(2)
                                            with col_meta1:
                                                st.link_button("📥 Download Metadata", download_urls['metadata'], help="Download full verification details as JSON")
                                            with col_meta2:
                                                files = verification.get('files', {})
                                                st.caption(f"Files stored in MinIO bucket")
                                                
                                    else:
                                        st.error("Could not retrieve file download URLs")
                                        st.info("💡 **Possible reasons:**")
                                        st.write("• MinIO server connection issues")
                                        st.write("• File access permissions")
                                        st.write("• Files may have been moved or deleted")
                                        
                                        # Show file paths for debugging
                                        files = verification.get('files', {})
                                        if files:
                                            st.caption("**Expected file locations:**")
                                            st.caption(f"• ID Card: {files.get('id_card', 'N/A')}")
                                            st.caption(f"• Video: {files.get('selfie_video', 'N/A')}")
                                        
                                except Exception as e:
                                    st.error(f"Error loading verification files: {str(e)}")
                                    st.info("💡 **Troubleshooting:**")
                                    st.write("• Check MinIO server connection")
                                    st.write("• Verify bucket permissions")
                                    st.write("• Files may need time to be available")
                    else:
                        st.info(f"No verifications found for {email_input}")
                        
            except Exception as e:
                st.error(f"Error loading verifications: {e}")
    
    with admin_tab4:
        st.markdown("### Statistics & Analytics")
        
        # Date range for statistics
        col1, col2 = st.columns(2)
        with col1:
            stats_start_date = st.date_input(
                "Statistics Start Date", 
                value=datetime.now() - timedelta(days=7),
                key="stats_start"
            )
        with col2:
            stats_end_date = st.date_input(
                "Statistics End Date", 
                value=datetime.now(),
                key="stats_end"
            )
        
        if st.button("Generate Statistics"):
            try:
                with st.spinner("Generating statistics..."):
                    # Generate date range
                    current_date = stats_start_date
                    daily_stats = []
                    
                    while current_date <= stats_end_date:
                        date_str = current_date.strftime("%Y-%m-%d")
                        daily_summary = admin_queries.get_daily_summary(date_str)
                        
                        if daily_summary:
                            daily_stats.append({
                                'Date': date_str,
                                'Total': daily_summary.get('total_verifications', 0),
                                'Passed': daily_summary.get('passed', 0),
                                'Failed': daily_summary.get('failed', 0),
                                'Unique Users': daily_summary.get('unique_users_count', 0)
                            })
                        else:
                            daily_stats.append({
                                'Date': date_str,
                                'Total': 0,
                                'Passed': 0,
                                'Failed': 0,
                                'Unique Users': 0
                            })
                        
                        current_date += timedelta(days=1)
                    
                    if daily_stats:
                        df = pd.DataFrame(daily_stats)
                        
                        # Display summary metrics
                        total_verifications = df['Total'].sum()
                        total_passed = df['Passed'].sum()
                        total_failed = df['Failed'].sum()
                        total_unique_users = df['Unique Users'].sum()
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Verifications", total_verifications)
                        with col2:
                            st.metric("Total Passed", total_passed)
                        with col3:
                            st.metric("Total Failed", total_failed)
                        with col4:
                            st.metric("Pass Rate", f"{(total_passed/max(total_verifications,1)*100):.1f}%")
                        
                        # Display daily statistics table
                        st.markdown("### Daily Statistics")
                        st.dataframe(df, use_container_width=True)
                        
                        # Simple charts
                        if len(df) > 1:
                            st.markdown("### Daily Verification Trends")
                            st.line_chart(df.set_index('Date')[['Total', 'Passed', 'Failed']])
                    else:
                        st.info("No statistics available for the selected date range")
                        
            except Exception as e:
                st.error(f"Error generating statistics: {e}")

# Initialize session state
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'admin_user' not in st.session_state:
    st.session_state.admin_user = None
if 'last_request_url' not in st.session_state:
    st.session_state.last_request_url = ""
if 'last_verification_id' not in st.session_state:
    st.session_state.last_verification_id = ""
if 'last_verification_request' not in st.session_state:
    st.session_state.last_verification_request = None

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        font-weight: bold;
    }
    .success-text {
        color: #4CAF50;
        font-weight: bold;
    }
    .failure-text {
        color: #F44336;
        font-weight: bold;
    }
    .processing-text {
        color: #FF9800;
        font-weight: bold;
    }
    .info-text {
        color: #2196F3;
    }
    .border-box {
        border: 1px solid #E0E0E0;
        border-radius: 5px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #FAFAFA;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health():
    """Check if the API is running"""
    try:
        url = get_api_url("health")
        st.session_state.last_request_url = url  # Store for debugging

        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            error_msg = f"API returned status code {response.status_code}"
            try:
                error_details = response.json()
                error_msg += f": {error_details}"
            except:
                error_msg += f": {response.text}"
            return False, error_msg
    except requests.RequestException as e:
        return False, f"Connection error: {str(e)}"

def submit_verification(id_card_file, selfie_video_file, user_id):
    """Submit files for verification"""
    try:
        url = get_api_url("verify")
        st.session_state.last_request_url = url  # Store for debugging

        files = {
            'id_card': (id_card_file.name, id_card_file.getvalue(), 'image/jpeg'),
            'selfie_video': (selfie_video_file.name, selfie_video_file.getvalue(), 'video/mp4')
        }
        data = {
            'user_id': user_id
        }

        # Log the request
        st.session_state.last_verification_request = {
            'url': url,
            'user_id': user_id,
            'files': [id_card_file.name, selfie_video_file.name]
        }

        # Set a longer timeout for uploads
        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=60  # 60 second timeout for file uploads
        )

        if response.status_code == 200:
            try:
                return True, response.json()
            except json.JSONDecodeError:
                return False, f"Server returned success status but invalid JSON: {response.text[:100]}..."
        else:
            error_msg = f"API returned status code {response.status_code}"
            try:
                error_details = response.json()
                return False, error_details
            except json.JSONDecodeError:
                # If we can't parse the response as JSON, return the raw text
                return False, f"{error_msg}: {response.text[:200]}..."
    except requests.RequestException as e:
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def check_verification_status(verification_id):
    """Check the status of a verification process"""
    try:
        url = get_api_url("status", verification_id)
        st.session_state.last_request_url = url  # Store for debugging

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            try:
                return True, response.json()
            except json.JSONDecodeError:
                return False, f"Server returned success status but invalid JSON: {response.text[:100]}..."
        elif response.status_code == 404:
            return False, "Verification ID not found. Please make sure you entered the correct ID."
        else:
            error_msg = f"API returned status code {response.status_code}"
            try:
                error_details = response.json()
                return False, error_details
            except json.JSONDecodeError:
                # If we can't parse the response as JSON, return the raw text
                return False, f"{error_msg}: {response.text[:200]}..."
    except requests.RequestException as e:
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def display_verification_result(status_data):
    """Display verification results in a nice format"""
    status = status_data.get('status')

    if status == 'processing':
        st.markdown('<p class="processing-text">⏳ Processing...</p>', unsafe_allow_html=True)
        st.info("Your verification is still being processed. Please wait or check again later.")
        return False

    elif status == 'completed':
        details = status_data.get('details', {})
        id_details = status_data.get('id_details', {})

        match_result = details.get('match_result', False)
        confidence_score = details.get('confidence_score', 0.0)

        if match_result:
            st.markdown('<p class="success-text">✅ MATCH SUCCESSFUL</p>', unsafe_allow_html=True)
            st.success(f"Face verification passed with confidence score: {confidence_score:.2f}")
        else:
            st.markdown('<p class="failure-text">❌ MATCH FAILED</p>', unsafe_allow_html=True)
            st.error(f"Face verification failed with confidence score: {confidence_score:.2f}")

        st.markdown('<p class="sub-header">ID Card Details</p>', unsafe_allow_html=True)

        if id_details:
            # Convert ID details to DataFrame for better display
            id_data = {
                'Field': [
                    'ID Number', 'Type of ID', 'Country', 'Name',
                    'Sex', 'Address', 'Date of Birth', 'Issued Date', 'Expire Date'
                ],
                'Value': [
                    id_details.get('id_number', 'N/A'),
                    id_details.get('type_of_id', 'N/A'),
                    id_details.get('country', 'N/A'),
                    id_details.get('name', 'N/A'),
                    id_details.get('sex', 'N/A'),
                    id_details.get('address', 'N/A'),
                    id_details.get('date_of_birth', 'N/A'),
                    id_details.get('issued_date', 'N/A'),
                    id_details.get('expire_date', 'N/A')
                ]
            }

            df = pd.DataFrame(id_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No ID card details were extracted")

        return True

    elif status == 'failed':
        details = status_data.get('details', {})
        error = details.get('error', 'Unknown error')

        st.markdown('<p class="failure-text">❌ VERIFICATION FAILED</p>', unsafe_allow_html=True)
        st.error(f"Error: {error}")

        # Check if there are partial ID details despite the failure
        id_details = status_data.get('id_details', {})
        if id_details and any(id_details.values()):
            st.markdown('<p class="sub-header">Partial ID Card Details</p>', unsafe_allow_html=True)

            # Convert partial ID details to DataFrame
            id_data = {
                'Field': [
                    'ID Number', 'Type of ID', 'Country', 'Name',
                    'Sex', 'Address', 'Date of Birth', 'Issued Date', 'Expire Date'
                ],
                'Value': [
                    id_details.get('id_number', 'N/A'),
                    id_details.get('type_of_id', 'N/A'),
                    id_details.get('country', 'N/A'),
                    id_details.get('name', 'N/A'),
                    id_details.get('sex', 'N/A'),
                    id_details.get('address', 'N/A'),
                    id_details.get('date_of_birth', 'N/A'),
                    id_details.get('issued_date', 'N/A'),
                    id_details.get('expire_date', 'N/A')
                ]
            }

            df = pd.DataFrame(id_data)
            st.dataframe(df, use_container_width=True)

        return True

    else:
        st.warning(f"Unknown status: {status}")
        return False

# App layout
st.markdown('<p class="main-header">Digital KYC Verification</p>', unsafe_allow_html=True)
st.markdown("Verify your identity with face matching and ID card extraction")

# Instructions in the sidebar
with st.sidebar:
    st.markdown('<p class="sub-header">ID Card Photo Instructions</p>', unsafe_allow_html=True)
    st.markdown("""
    1. Place your ID card on a dark, solid-colored surface
    2. Make sure all four corners of the ID are visible
    3. Ensure there's good lighting without glare or shadows
    4. Keep the ID card straight (not tilted)
    5. Make sure your face on the ID is clearly visible
    6. Take the photo directly above the ID (not at an angle)
    7. Avoid including other objects in the frame
    """)

    st.markdown('<p class="sub-header">Selfie Video Instructions</p>', unsafe_allow_html=True)
    st.markdown("""
    1. Find a well-lit area (natural light is best)
    2. Hold your device at eye level, arm's length away
    3. Look directly at the camera
    4. Keep a neutral expression or slight smile
    5. Ensure your face is centered and fully visible
    6. Move your head slightly from side to side
    7. Keep your background simple and uncluttered
    8. Record for 3-5 seconds
    """)

    st.markdown('<p class="sub-header">Troubleshooting Common Errors</p>', unsafe_allow_html=True)
    st.markdown("""
    - **"No face detected in ID"**: Ensure your ID card shows a clear face and is well-lit
    - **"No face found in video"**: Make sure your face is clearly visible throughout the video
    - **"Unable to extract data"**: Check that your ID text is clearly visible and not blurry
    """)

# Create tabs for the app
tab1, tab2, tab3 = st.tabs(["Submit Verification", "Check Status", "Admin Panel"])

with tab1:
    st.markdown('<div class="border-box">', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Identity Verification</p>', unsafe_allow_html=True)

    # User ID input
    user_id = st.text_input("User ID", value="user@exampe.com", placeholder="Enter your user ID", help="Your unique identifier")

    # File uploaders
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="info-text">Upload ID Card Image</p>', unsafe_allow_html=True)
        st.markdown("""
        **Requirements:**
        - Good lighting without glare
        - All four corners visible
        - Face on ID clearly visible
        """)
        id_card_file = st.file_uploader("ID Card Image", type=["jpg", "jpeg", "png"])

        if id_card_file is not None:
            try:
                image = Image.open(id_card_file)
                img = image
                st.image(img, caption="Uploaded ID Card", use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
                st.warning("Please upload a valid image file")

    with col2:
        st.markdown('<p class="info-text">Upload Selfie Video</p>', unsafe_allow_html=True)
        st.markdown("""
        **Requirements:**
        - 3-5 seconds duration
        - Good lighting on your face
        - Look directly at camera
        - Slight natural head movement
        """)
        selfie_video_file = st.file_uploader("Selfie Video", type=["mp4", "mov", "avi"])

        if selfie_video_file is not None:
            try:
                # Save to a temporary file and display
                video_bytes = selfie_video_file.read()
                selfie_video_file.seek(0)  # Reset file position after reading
                st.video(video_bytes)
            except Exception as e:
                st.error(f"Error displaying video: {str(e)}")
                st.warning("Please upload a valid video file")

    # Check if both files are uploaded
    files_ready = id_card_file is not None and selfie_video_file is not None

    # Display a message if files are uploaded but button is still disabled
    if files_ready and not user_id:
        st.warning("Please enter your User ID to enable submission")

    submit_button = st.button("Submit for Verification", type="primary", disabled=not (files_ready and user_id))

    if submit_button:
        with st.spinner("Uploading files and submitting verification..."):
            try:
                # Reset the file position to the beginning (just to be safe)
                id_card_file.seek(0)
                selfie_video_file.seek(0)

                success, response = submit_verification(id_card_file, selfie_video_file, user_id)

                if success:
                    verification_id = response.get('verification_id')
                    st.session_state.last_verification_id = verification_id

                    st.success("Verification submitted successfully!")
                    st.info(f"Verification ID: {verification_id}")
                    st.info("Switch to the 'Check Status' tab to monitor the verification progress.")
                else:
                    st.error("Error submitting verification")

                    # Display the error in a more user-friendly way
                    if isinstance(response, dict):
                        st.json(response)
                    else:
                        st.error(str(response))

                    # Add troubleshooting info
                    st.warning("""
                    **Troubleshooting tips:**
                    - Check that your server is running
                    - Verify that your files are valid
                    - Try uploading smaller files
                    """)
            except Exception as e:
                st.error(f"Unexpected error during submission: {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="border-box">', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Verification Status</p>', unsafe_allow_html=True)

    # Get verification ID from user input or session state
    verification_id = st.text_input(
        "Verification ID",
        value=st.session_state.get("last_verification_id", ""),
        help="Enter the verification ID received after submission"
    )

    check_button = st.button("Check Status", type="primary", disabled=not verification_id)

    if check_button:
        with st.spinner("Checking verification status..."):
            success, response = check_verification_status(verification_id)

            if success:
                st.markdown('<p class="sub-header">Verification Result</p>', unsafe_allow_html=True)
                display_verification_result(response)
            else:
                st.error(f"Error checking verification status: {response}")

                # Show troubleshooting help
                st.markdown("### Need Help?")
                st.markdown("""
                If you're having trouble with verification:
                - Make sure you've entered the correct verification ID
                - Check that your ID photo followed the guidelines
                - Ensure your selfie video clearly shows your face
                - Try submitting a new verification with better lighting
                """)

    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="border-box">', unsafe_allow_html=True)
    
    # Check if admin is authenticated
    if not st.session_state.admin_authenticated:
        admin_login()
    else:
        admin_panel()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Add instructions in the sidebar
with st.sidebar:
    st.markdown('<p class="sub-header">How to Use</p>', unsafe_allow_html=True)
    st.markdown("""
    1. **Submit Tab**: Upload an ID card image and a selfie video
    2. **Check Status Tab**: Enter the verification ID to see results
    3. **Admin Panel**: Administrative access to view verification data

    The system will:
    - Extract details from the ID card
    - Detect faces in both the ID and video
    - Match the faces to verify identity
    """)

    st.markdown('<p class="sub-header">Sample Error Messages</p>', unsafe_allow_html=True)
    st.markdown("""
    - **"No face detected in ID"**: The system couldn't find a face in the ID card image
    (You may upload the ID again with better conditions)
    - **"No face found in video"**: No faces were detected in the selfie video
    (You may upload a video that the face clearly appears)
    - **"Unable to extract data"**: The system couldn't extract text from the ID card
    (Your may upload a clearer image of the ID card)
    """)
