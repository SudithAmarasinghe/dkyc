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


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_admin_storage():
    """Get MinIO storage instance (cached)"""
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
   # from kyc_storage import KYCMinIOStorage
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
                            with st.expander(
                                    f"Verification {i + 1}: {result.get('email', 'N/A')} - {result.get('status', 'unknown').upper()}"):
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

                                # Get full verification details
                                if st.button(f"View Full Details", key=f"details_{i}"):
                                    full_details = admin_queries.get_verification_by_id(result.get('verification_id'))
                                    if full_details:
                                        st.json(full_details)
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
                            with st.expander(f"Verification {i + 1} - {verification.get('status', 'unknown').upper()}"):
                                # Display verification details
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.write(f"**Verification ID:** {verification.get('verification_id', 'N/A')}")
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

                                # File information
                                files = verification.get('files', {})
                                if files:
                                    st.markdown("**Files:**")
                                    st.write(f"- ID Card: {files.get('id_card', 'N/A')}")
                                    st.write(f"- Selfie Video: {files.get('selfie_video', 'N/A')}")
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
                            st.metric("Pass Rate", f"{(total_passed / max(total_verifications, 1) * 100):.1f}%")

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
    user_id = st.text_input("User ID", value="user123", placeholder="Enter your user ID", help="Your unique identifier")

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
