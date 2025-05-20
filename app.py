import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

import streamlit.components.v1 as components  # Import components module properly

# Add Google Analytics tracking code
def add_google_analytics():
    """Add Google Analytics tracking code to the Streamlit app."""
    GA_ID = "G-QB4ELSTWSX"  # Your Google Analytics ID
    
    # Define the Google Analytics code with your tracking ID
    analytics_js = f"""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}};
      gtag('js', new Date());
      gtag('config', '{GA_ID}');
    </script>
    """
    
    # Inject the script via HTML component with height=0
    components.html(analytics_js, height=0)

# Page configuration
st.set_page_config(page_title="4C Group Impact Dashboard", layout="wide", page_icon = "🤝")

# Add Google Analytics
add_google_analytics()


# SDG information and colors
SDG_INFO = {
    'Good Health and Well-being': {
        'color': '#4C9F38',
        'number': 3,
        'description': 'Promoting healthy lifestyles, mental health support, and community wellness initiatives.'
    },
    'Quality Education': {
        'color': '#C5192D',
        'number': 4,
        'description': 'Supporting educational programs, training initiatives, and skill development opportunities.'
    },
    'Gender Equality': {
        'color': '#FF3A21',
        'number': 5,
        'description': 'Promoting gender equality, women empowerment, and inclusive workplace practices.'
    },
    'Decent Work and Economic Growth': {
        'color': '#A21942',
        'number': 8,
        'description': 'Creating job opportunities, fair labor practices, and supporting local economic development.'
    },
    'Reduced Inequalities': {
        'color': '#DD1367',
        'number': 10,
        'description': 'Fighting discrimination, promoting inclusion, and supporting vulnerable communities.'
    },
    'Sustainable Cities and Communities': {
        'color': '#FD9D24',
        'number': 11,
        'description': 'Supporting local communities, urban development, and sustainable city initiatives.'
    },
    'Responsible Consumption and Production': {
        'color': '#BF8B2E',
        'number': 12,
        'description': 'Promoting sustainable practices, reducing waste, and responsible resource management.'
    },
    'Climate Action': {
        'color': '#3F7E44',
        'number': 13,
        'description': 'Environmental initiatives, carbon reduction, and climate change awareness.'
    }
}

def connect_to_google_sheets():
    """Setup Google Sheets connection"""
    try:
        credentials = {
            "type": "service_account",
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"],
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
            "universe_domain": "googleapis.com"
        }
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(credentials, scopes=scopes)
        client = gspread.authorize(creds)
        return client
            
    except Exception as e:
        # st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None

def fetch_sheet_data():
    """Fetch data from Google Sheets"""
    try:
        # Debug connection
        client = connect_to_google_sheets()
        if not client:
            # st.error("Failed to connect to Google Sheets")
            return pd.DataFrame()
        # st.success("Connected to Google Sheets")
        
        try:
            # Debug spreadsheet access
            sheet = client.open_by_key(st.secrets["sheet_id"])
            # st.success("Successfully opened spreadsheet")
            
            # List all available worksheets
            worksheets = sheet.worksheets()
            worksheet_names = [ws.title for ws in worksheets]
            
            # Get the first worksheet (assumes data is in first tab)
            worksheet = sheet.get_worksheet(0)
            # st.success(f"Successfully found worksheet: {worksheet.title}")
            
            # Get all records with row count
            try:
                # Fetch raw data for debugging
                raw_data = worksheet.get_all_values()
                headers = raw_data[0]
                data = raw_data[1:]
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=headers)
                if not df.empty:
                    # st.success(f"Successfully fetched {len(df)} rows of data")
                    return df
                else:
                    st.warning("Sheet is empty or data format is incorrect")
                    return pd.DataFrame()
            except Exception as data_error:
                st.error(f"Error reading data: {str(data_error)}")
                return pd.DataFrame()
                
        except Exception as sheet_error:
            st.error(f"Error accessing worksheet: {str(sheet_error)}")
            return pd.DataFrame()
        
    except Exception as e:
        # st.error(f"Error fetching data: {str(e)}")
        # st.write("Error type:", type(e).__name__)
        return pd.DataFrame()

def reshape_survey_data(df):
    """Reshape survey data with multiple activities per row into long format"""
    all_activities = []
    
    # Iterate through each row
    for _, row in df.iterrows():
        # Get base data
        base_data = {
            'Timestamp': row['Timestamp'],
            'Hotel': row['Hotel']
        }
        
        # Process up to 5 activities per row
        for i in range(1, 6):
            prefix = f"{i}."
            
            # Check if activity exists
            activity_name_col = f"{prefix}Acitivity Name"
            if activity_name_col not in row or pd.isna(row[activity_name_col]):
                continue
            
            # Create activity dictionary
            activity = base_data.copy()
            activity.update({
                'Activity Name': row[f"{prefix}Acitivity Name"],
                'Organization': row[f"{prefix}Charity/Organisation Supported"],
                'Activity Date': row[f"{prefix}When did the activity happen?"],
                'Contribution Type': row[f"{prefix}Contribution Type"],
                'SDG': clean_sdg_name(row[f"{prefix}Which SDG would this fall into?"]),  # Clean SDG name
                'Volunteer Hours': row[f"{prefix}If volunteering, how many hours?"],
                'Financial Impact': row[f"{prefix}Everything else: Financial Impact or Equiv (If meeting room or guest - how much would that have cost, food donation amount, etc) - only note down a number"]
            })
            
            # Only add if essential fields are present
            if not pd.isna(activity['Activity Name']) and not pd.isna(activity['Activity Date']):
                all_activities.append(activity)
    
    # Convert to DataFrame
    if not all_activities:
        return pd.DataFrame()
    
    reshaped_df = pd.DataFrame(all_activities)
    
    # Clean and convert data types
    try:
        # Convert dates
        reshaped_df['Activity Date'] = pd.to_datetime(reshaped_df['Activity Date'], format='%d/%m/%Y', errors='coerce')
        
        # Convert numeric fields - MODIFIED THIS PART
        reshaped_df['Volunteer Hours'] = pd.to_numeric(reshaped_df['Volunteer Hours'], errors='coerce').fillna(0)
        
        # Clean financial impact by removing commas before conversion
        reshaped_df['Financial Impact'] = reshaped_df['Financial Impact'].astype(str).str.replace(',', '', regex=True)
        reshaped_df['Financial Impact'] = pd.to_numeric(reshaped_df['Financial Impact'], errors='coerce').fillna(0)
        
        # Sort by date
        reshaped_df = reshaped_df.sort_values('Activity Date', ascending=False)
        
        return reshaped_df
        
    except Exception as e:
        st.error(f"Error processing data: {str(e)}")
        return pd.DataFrame()

def clean_sdg_name(sdg):
    """Standardize SDG names based on Google Form options"""
    if pd.isna(sdg):
        return None
    
    # Convert to lowercase and strip extra spaces
    sdg = str(sdg).lower().strip()
    
    # Map Google Form SDG names to SDG_INFO keys
    sdg_mapping = {
        'good health and well-being': 'Good Health and Well-being',
        'decent work and economic growth': 'Decent Work and Economic Growth',
        'reduced inequalities': 'Reduced Inequalities',
        'quality education': 'Quality Education',
        'gender equality': 'Gender Equality',
        'sustainable cities and communities': 'Sustainable Cities and Communities',
        'climate action': 'Climate Action',
        'responsible consumption and production': 'Responsible Consumption and Production'
    }
    
    # Return the mapped SDG name, or the original SDG if no match is found
    return sdg_mapping.get(sdg, sdg.title())

def clean_sdg_name(sdg):
    """Standardize SDG names based on Google Form options"""
    if pd.isna(sdg):
        return None
    
    # Convert to lowercase and strip extra spaces
    sdg = str(sdg).lower().strip()
    
    # Map Google Form SDG names to SDG_INFO keys
    sdg_mapping = {
        'good health and well-being': 'Good Health and Well-being',
        'decent work and economic growth': 'Decent Work and Economic Growth',
        'reduced inequalities': 'Reduced Inequalities',
        'quality education': 'Quality Education',
        'gender equality': 'Gender Equality',
        'sustainable cities and communities': 'Sustainable Cities and Communities',
        'climate action': 'Climate Action',
        'responsible consumption and production': 'Responsible Consumption and Production'
    }
    
    # Return the mapped SDG name, or the original SDG if no match is found
    return sdg_mapping.get(sdg, sdg.title())

def create_sdg_treemap(data):
    """Create a treemap visualization for SDG activities"""
    fig = px.treemap(
        data.reset_index(),
        path=['SDG'],
        values='Count',
        color='SDG',
        color_discrete_map={sdg: SDG_INFO[sdg]['color'] for sdg in data.index if sdg in SDG_INFO},
        title='SDG Activity Distribution'
    )
    
    fig.update_traces(
        textinfo="label+value",
        hovertemplate="<b>%{label}</b><br>Activities: %{value}<extra></extra>"
    )
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        title_x=0.5,
        title_font_size=16
    )
    
    return fig

def show_sdg_info():
    """Display SDG information page"""
    st.header("Our Focus SDGs")
    st.write("These are the key Sustainable Development Goals (SDGs) we're focusing on:")
    
    for sdg, info in SDG_INFO.items():
        with st.expander(f"SDG {info['number']}: {sdg}"):
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"""
                    <div style='background-color: {info['color']}; 
                             width: 50px; 
                             height: 50px; 
                             border-radius: 25px; 
                             display: flex; 
                             align-items: center; 
                             justify-content: center; 
                             color: white; 
                             font-weight: bold;'>
                        {info['number']}
                    </div>
                """, unsafe_allow_html=True)
            with col2:
                st.write(info['description'])

def show_metrics(volunteer_hours, financial_impact, activities):
    st.markdown("""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
            <div class="metric-container">
                <div style="color: #3B82F6;">
                    <h3 class="metric-title">Volunteer Hours</h3>
                    <p class="metric-value">{:,.0f}</p>
                </div>
            </div>
            <div class="metric-container">
                <div style="color: #10B981;">
                    <h3 class="metric-title">Financial Impact</h3>
                    <p class="metric-value">£{:,.0f}</p>
                </div>
            </div>
            <div class="metric-container">
                <div style="color: #8B5CF6;">
                    <h3 class="metric-title">Activities</h3>
                    <p class="metric-value">{:,.0f}</p>
                </div>
            </div>
        </div>
    """.format(volunteer_hours, financial_impact, activities), unsafe_allow_html=True)

def create_responsive_charts(hotel_metrics, sdg_metrics):
    # Container for charts
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    
    # Responsive columns
    use_wide_layout = st.checkbox("Wide layout", value=True)
    
    if use_wide_layout:
        col1, col2 = st.columns(2)
    else:
        col1, col2 = st.columns([1, 1])
    
    # Update chart layouts for better mobile responsiveness
    chart_layout = {
        'height': 400,
        'margin': dict(l=20, r=20, t=40, b=20),
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'size': 12},
        'autosize': True
    }
    
    # Add media queries for mobile
    chart_layout.update({
        'xaxis': {'tickangle': -45} if len(hotel_metrics) > 5 else {},
        'legend': {
            'orientation': "h",
            'yanchor': "bottom",
            'y': 1.02,
            'xanchor': "right",
            'x': 1
        }
    })

def show_dashboard(data):
    """Display a streamlined, engaging dashboard with all KPIs in one row"""
    # Find the latest month in the data
    latest_date = data['Activity Date'].max()
    
    # Custom CSS for modern, engaging design with reduced spacing
    st.markdown("""
        <style>
        /* Clean overall aesthetic with reduced spacing */
        .main {
            padding: 0.5rem;
            background-color: #f8fafc;
        }
        
        /* Inspiring header with reduced margins */
        .dashboard-header {
            margin-bottom: 12px;
            text-align: center;
            padding-bottom: 10px;
            position: relative;
        }
        
        .dashboard-header h1 {
            font-size: 24px;
            margin-bottom: 4px;
            color: #1e293b;
        }
        
        .dashboard-header p {
            color: #64748b;
            font-size: 14px;
            max-width: 700px;
            margin: 0 auto;
        }
        
        .dashboard-header::after {
            content: "";
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 70px;
            height: 2px;
            background: linear-gradient(90deg, #3B82F6, #8B5CF6);
            border-radius: 2px;
        }
        
        /* Dashboard sections with reduced padding */
        .dashboard-section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
            padding: 16px;
            margin-bottom: 16px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
            position: relative;
            padding-left: 10px;
        }
        
        # .section-title::before {
        #     content: "";
        #     position: absolute;
        #     left: 0;
        #     top: 0;
        #     height: 100%;
        #     width: 3px;
        #     background: linear-gradient(180deg, #3B82F6, #8B5CF6);
        #     border-radius: 3px;
        # }
        
        /* Charity cards grid with reduced spacing */
        .charity-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        
        .charity-card {
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            padding: 12px;
            transition: transform 0.2s;
        }
        
        .charity-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 3px 5px rgba(0, 0, 0, 0.08);
        }
        
        .charity-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .charity-logo {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            margin-right: 8px;
            font-size: 14px;
        }
        
        .charity-name {
            font-weight: 600;
            color: #1e293b;
            font-size: 13px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .charity-stats {
            display: flex;
            justify-content: space-between;
        }
        
        .charity-stat {
            text-align: center;
        }
        
        .charity-stat-value {
            font-weight: 700;
            font-size: 14px;
            color: #334155;
        }
        
        .charity-stat-label {
            font-size: 11px;
            color: #64748b;
        }
        
        /* Period selector styling */
        .period-selector {
            position: absolute;
            top: 15px;
            right: 15px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
            padding: 2px;
            z-index: 100;
        }
        
        /* Achievement banner */
        .achievement-banner {
            background: linear-gradient(135deg, #4F46E5, #7C3AED);
            border-radius: 8px;
            padding: 15px;
            color: white;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .achievement-message {
            font-size: 14px;
            font-weight: 500;
        }
        
        .achievement-highlight {
            font-weight: 700;
            font-size: 16px;
        }
        
        /* Exciting SDG Progress Bar Layout */
        .sdg-progress-container {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-top: 10px;
        }
        
        .sdg-progress-item {
            flex: 1;
            min-width: 200px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            padding: 12px;
            position: relative;
            transition: all 0.3s ease;
            overflow: hidden;
        }
        
        .sdg-progress-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
        }
        
        .sdg-progress-item::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 6px;
            height: 100%;
        }
        
        .sdg-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .sdg-icon-wrapper {
            position: relative;
            margin-right: 12px;
        }
        
        .sdg-icon {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 18px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }
        
        .sdg-icon-pulse {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            animation: pulse 2s infinite;
            opacity: 0;
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
                opacity: 0.7;
            }
            70% {
                transform: scale(1.5);
                opacity: 0;
            }
            100% {
                transform: scale(1.5);
                opacity: 0;
            }
        }
        
        .sdg-info {
            flex: 1;
        }
        
        .sdg-title {
            font-size: 14px;
            font-weight: 600;
            color: #334155;
            margin-bottom: 3px;
        }
        
        .sdg-description {
            font-size: 12px;
            color: #64748b;
            line-height: 1.4;
        }
        
        .sdg-stats {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 8px;
        }
        
        .sdg-count {
            font-size: 24px;
            font-weight: 700;
        }
        
        .sdg-progress-bar {
            height: 6px;
            background-color: #e2e8f0;
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }
        
        .sdg-progress-value {
            height: 100%;
            border-radius: 3px;
            transition: width 1.5s ease;
        }
        
        .sdg-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            margin-left: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Updated time period selector
    st.markdown('<div class="period-selector">', unsafe_allow_html=True)
    view_type = st.radio(
        "",
        ["Financial YTD", "Last Month", "Last Financial Year"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Get current date and handle filtering based on selected period
    current_date = datetime.now()

    # Filter data based on selected period
    if view_type == "Last Month":
        # Calculate last month
        if current_date.month == 1:  # January
            last_month = 12
            last_month_year = current_date.year - 1
        else:
            last_month = current_date.month - 1
            last_month_year = current_date.year
        
        filtered_data = data[
            (data['Activity Date'].dt.month == last_month) & 
            (data['Activity Date'].dt.year == last_month_year)
        ]
        period_text = datetime(last_month_year, last_month, 1).strftime("%B %Y")
    elif view_type == "Financial YTD":
        # Calculate financial year to date
        if current_date.month < 4:  # Jan-Mar
            fy_start = datetime(current_date.year - 1, 4, 1)
            fy_end = current_date
            fy_text = f"FY{current_date.year-1}/{current_date.year}"
        else:  # Apr-Dec
            fy_start = datetime(current_date.year, 4, 1)
            fy_end = current_date
            fy_text = f"FY{current_date.year}/{current_date.year+1}"
        
        filtered_data = data[
            (data['Activity Date'] >= fy_start) & 
            (data['Activity Date'] <= fy_end)
        ]
        period_text = f"{fy_text} to date (Apr-{current_date.strftime('%b')})"
    else:  # Last Financial Year
        # Calculate last financial year
        if current_date.month < 4:  # Jan-Mar
            fy_start = datetime(current_date.year - 2, 4, 1)
            fy_end = datetime(current_date.year - 1, 3, 31)
            fy_text = f"FY{current_date.year-2}/{current_date.year-1}"
        else:  # Apr-Dec
            fy_start = datetime(current_date.year - 1, 4, 1)
            fy_end = datetime(current_date.year, 3, 31)
            fy_text = f"FY{current_date.year-1}/{current_date.year}"
        
        filtered_data = data[
            (data['Activity Date'] >= fy_start) & 
            (data['Activity Date'] <= fy_end)
        ]
        period_text = f"{fy_text} (Apr-Mar)"
    
    # Inspiring header
    st.markdown("""
        <div class="dashboard-header">
            <h1>Making an Impact Together</h1>
            <p>Tracking our journey towards a sustainable future through community engagement and support.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Calculate metrics
    total_volunteer_hours = pd.to_numeric(filtered_data['Volunteer Hours'], errors='coerce').sum()
    total_financial_impact = pd.to_numeric(filtered_data['Financial Impact'], errors='coerce').sum()
    total_activities = len(filtered_data)
    unique_charities = filtered_data['Organization'].nunique()
    unique_sdgs = filtered_data['SDG'].nunique()
    
    # Achievement banner (if there's a notable achievement to highlight)
    if total_volunteer_hours > 1000 or total_financial_impact > 10000:
        st.markdown("""
            <div class="achievement-banner">
                <div class="achievement-message">
                    Congratulations! We've reached <span class="achievement-highlight">{milestone}</span> in our community impact efforts.
                </div>
                <div>
                    🎉
                </div>
            </div>
        """.format(
            milestone=f"£{int(total_financial_impact):,} in financial impact" if total_financial_impact > 10000 
                    else f"{int(total_volunteer_hours):,} volunteer hours"
        ), unsafe_allow_html=True)
    
    # Single-row metrics display using columns instead of HTML for better rendering
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("⏱️ Volunteer Hours", f"{int(total_volunteer_hours):,}")
    
    with col2:
        st.metric("💰 Financial Impact", f"£{int(total_financial_impact):,}")
    
    with col3:
        st.metric("📊 Activities", f"{total_activities:,}")
    
    with col4:
        st.metric("🤝 Charities", f"{unique_charities:,}")
    
    with col5:
        st.metric("🌍 SDGs", f"{unique_sdgs:,}")
    
    # Hotel contributions section
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><h2 class="section-title">Hotel Contributions</h2></div>', unsafe_allow_html=True)
    
    # Process hotel data
    hotel_metrics = filtered_data.groupby('Hotel').agg({
        'Volunteer Hours': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Financial Impact': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Activity Date': 'count'
    }).reset_index().rename(columns={'Activity Date': 'Activities'})
    
    # Sort by total impact
    hotel_metrics['Total Impact'] = hotel_metrics['Volunteer Hours'] + (hotel_metrics['Financial Impact'] / 100)
    hotel_metrics = hotel_metrics.sort_values('Total Impact', ascending=False)
    
    # Create hotel impact chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Filter to only show hotels with volunteer hours > 0
        volunteer_hotels = hotel_metrics[hotel_metrics['Volunteer Hours'] > 0].copy()
        
        if not volunteer_hotels.empty:
            # Sort by volunteer hours
            volunteer_hotels = volunteer_hotels.sort_values('Volunteer Hours', ascending=False)
            
            fig1 = px.bar(
                volunteer_hotels, 
                x='Hotel', 
                y='Volunteer Hours',
                title=f'Volunteer Hours by Hotel ({len(volunteer_hotels)} contributing)',
                color_discrete_sequence=['#3B82F6'],
                template='plotly_white'
            )
            fig1.update_layout(
                height=240,
                margin=dict(l=20, r=20, t=30, b=40),
                title_font_size=14,
                title_x=0.5,
                xaxis_title="",
                yaxis_title="Hours",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                bargap=0.3
            )
            fig1.update_traces(
                marker_line_color='#2563EB',
                marker_line_width=1,
                hovertemplate="<b>%{x}</b><br>Hours: %{y:,.0f}<extra></extra>"
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No volunteer hours recorded in this period.")
    
    with col2:
        # Filter to only show hotels with financial impact > 0
        financial_hotels = hotel_metrics[hotel_metrics['Financial Impact'] > 0].copy()
        
        if not financial_hotels.empty:
            # Sort by financial impact
            financial_hotels = financial_hotels.sort_values('Financial Impact', ascending=False)
            
            fig2 = px.bar(
                financial_hotels, 
                x='Hotel', 
                y='Financial Impact',
                title=f'Financial Impact by Hotel ({len(financial_hotels)} contributing)',
                color_discrete_sequence=['#10B981'],
                template='plotly_white'
            )
            fig2.update_layout(
                height=240,
                margin=dict(l=20, r=20, t=30, b=40),
                title_font_size=14,
                title_x=0.5,
                xaxis_title="",
                yaxis_title="Amount (£)",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                bargap=0.3
            )
            fig2.update_traces(
                marker_line_color='#059669',
                marker_line_width=1,
                hovertemplate="<b>%{x}</b><br>Amount: £%{y:,.0f}<extra></extra>"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No financial contributions recorded in this period.")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Charity section
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><h2 class="section-title">Charity Partners</h2></div>', unsafe_allow_html=True)
    
    # Process charity data
    charity_metrics = filtered_data.groupby('Organization').agg({
        'Volunteer Hours': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Financial Impact': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Activity Date': 'count'
    }).reset_index().rename(columns={'Activity Date': 'Activities'})
    
    # Sort by activities
    charity_metrics = charity_metrics.sort_values('Activities', ascending=False).head(8)
    
    # Create charity cards
    st.markdown('<div class="charity-grid">', unsafe_allow_html=True)
    
    # Color palette for charity logos
    charity_colors = ['#3B82F6', '#10B981', '#7C3AED', '#F59E0B', '#EC4899', '#EF4444', '#06B6D4', '#8B5CF6']
    
    for idx, charity in charity_metrics.iterrows():
        color = charity_colors[idx % len(charity_colors)]
        st.markdown(f"""
            <div class="charity-card">
                <div class="charity-header">
                    <div class="charity-logo" style="background-color: {color};">
                        {charity['Organization'][0].upper()}
                    </div>
                    <div class="charity-name" title="{charity['Organization']}">
                        {charity['Organization']}
                    </div>
                </div>
                <div class="charity-stats">
                    <div class="charity-stat">
                        <div class="charity-stat-value">{int(charity['Activities'])}</div>
                        <div class="charity-stat-label">Activities</div>
                    </div>
                    <div class="charity-stat">
                        <div class="charity-stat-value">{int(charity['Volunteer Hours'])}</div>
                        <div class="charity-stat-label">Hours</div>
                    </div>
                    <div class="charity-stat">
                        <div class="charity-stat-value">£{int(charity['Financial Impact']):,}</div>
                        <div class="charity-stat-label">Impact</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # SDG section - Exciting and visually engaging format
    st.markdown('<div class="dashboard-section" style="background: linear-gradient(135deg, #f9fafb 0%, #f1f5f9 100%);">', unsafe_allow_html=True)
    st.markdown('<div class="section-header"><h2 class="section-title">SDG Impact</h2></div>', unsafe_allow_html=True)
    
    # Process SDG data
    sdg_metrics = filtered_data.groupby('SDG').size().reset_index(name='Count')
    
    if not sdg_metrics.empty:
        # Sort by count
        sdg_metrics = sdg_metrics.sort_values('Count', ascending=False)
        
        # Get max count for percentage calculation
        max_count = sdg_metrics['Count'].max()
        
        # Create exciting SDG display
        st.markdown('<div class="sdg-progress-container">', unsafe_allow_html=True)
        
        for idx, sdg in sdg_metrics.iterrows():
            sdg_name = sdg['SDG']
            sdg_count = sdg['Count']
            
            # Get color and info from SDG_INFO if available, or use default
            if sdg_name in SDG_INFO:
                color = SDG_INFO[sdg_name]['color']
                number = SDG_INFO[sdg_name]['number']
                description = SDG_INFO[sdg_name]['description']
            else:
                color = '#777777'
                number = ""
                description = ""
            
            # Calculate percentage of the max for progress bar
            percentage = (sdg_count / max_count) * 100
            
            # Create status badge based on percentage
            if percentage >= 75:
                badge_color = "#22c55e"
                badge_text = "Strong"
            elif percentage >= 50:
                badge_color = "#eab308"
                badge_text = "Growing"
            else:
                badge_color = "#3b82f6"
                badge_text = "Building"
            
            # Create exciting animated SDG card
            st.markdown(f"""
                <div class="sdg-progress-item" style="border-left: 6px solid {color};">
                    <div class="sdg-header">
                        <div class="sdg-icon-wrapper">
                            <div class="sdg-icon" style="background-color: {color};">
                                {number}
                            </div>
                            <div class="sdg-icon-pulse" style="border: 3px solid {color};"></div>
                        </div>
                        <div class="sdg-info">
                            <div class="sdg-title">{sdg_name}</div>
                            <div class="sdg-description">{description}</div>
                        </div>
                    </div>
                    <div class="sdg-stats">
                        <div class="sdg-count" style="color: {color};">{sdg_count}</div>
                        <div>
                            <span class="sdg-badge" style="background-color: {badge_color}20; color: {badge_color};">
                                {badge_text}
                            </span>
                        </div>
                    </div>
                    <div class="sdg-progress-bar">
                        <div class="sdg-progress-value" style="width: {percentage}%; background-color: {color};"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def add_custom_css():
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            padding: 1rem;
        }
        
        /* Card styling */
        div[data-testid="stMetric"] {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
            transition: all 0.3s cubic-bezier(.25,.8,.25,1);
        }
        
        div[data-testid="stMetric"]:hover {
            box-shadow: 0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22);
        }
        
        /* Metric card styling */
        .metric-container {
            background-color: white;
            padding: 1.5rem;
            border-radius: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        
        .metric-title {
            font-size: 1rem;
            color: #6B7280;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #111827;
        }
        
        /* Chart container styling */
        .chart-container {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            margin-bottom: 1rem;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .metric-container {
                padding: 1rem;
            }
            
            .metric-value {
                font-size: 1.25rem;
            }
            
            div[data-testid="stMetric"] {
                margin-bottom: 1rem;
            }
        }
        
        /* Custom tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 1rem 2rem;
            background-color: transparent;
            border-radius: 0.5rem 0.5rem 0 0;
        }
        
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #3B82F6;
        }
        
        /* Title styling */
        h1 {
            font-size: 2rem;
            font-weight: bold;
            color: #111827;
            margin-bottom: 2rem;
        }
        
        h2 {
            font-size: 1.5rem;
            color: #374151;
            margin: 1.5rem 0;
        }
        
        /* SDG section styling */
        .sdg-circle {
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    st.title("ESG Impact Dashboard")
    
    # Create tabs with enhanced styling
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🎯 SDG Information", "📝 Submit Activity", "📋 Raw Data"])
    
    with tab1:
        try:
            data = fetch_sheet_data()
            if not data.empty:
                processed_data = reshape_survey_data(data)
                if not processed_data.empty:
                    show_dashboard(processed_data)
                else:
                    st.error("Failed to process data")
            else:
                st.error("No data found in Google Sheet")
                
        except Exception as e:
            st.error(f"Error accessing Google Sheets: {str(e)}")
    
    with tab2:
        show_sdg_info()
    
    with tab3:
        st.header("Submit New Activity")
        st.write("Want to add your activities? Please submit them using the form below:")
        st.markdown("""
            <iframe src="https://docs.google.com/forms/d/e/1FAIpQLSc0Z8PYM-KKRQtFfh6o1uM75WFFZrgFOYj3TRv7kMHwD3JS8g/viewform?embedded=true" 
                width="100%" 
                height="800" 
                frameborder="0" 
                marginheight="0" 
                marginwidth="0"
                style="background: transparent;">
                Loading…
            </iframe>
        """, unsafe_allow_html=True)
    
    with tab4:
        st.header("Raw Data")
        try:
            data = fetch_sheet_data()
            if not data.empty:
                processed_data = reshape_survey_data(data)
                if not processed_data.empty:
                    # Add filters
                    st.subheader("Data Filters")
                    cols = st.columns(4)
                    
                    with cols[0]:
                        hotels = ['All'] + sorted(processed_data['Hotel'].unique().tolist())
                        selected_hotel = st.selectbox('Select Hotel', hotels)
                    
                    with cols[1]:
                        sdgs = ['All'] + sorted(processed_data['SDG'].unique().tolist())
                        selected_sdg = st.selectbox('Select SDG', sdgs)
                    
                    with cols[2]:
                        contribution_types = ['All'] + sorted(processed_data['Contribution Type'].unique().tolist())
                        selected_type = st.selectbox('Select Contribution Type', contribution_types)
                    
                    with cols[3]:
                        date_range = st.date_input(
                            "Select Date Range",
                            value=(processed_data['Activity Date'].min(), processed_data['Activity Date'].max()),
                            min_value=processed_data['Activity Date'].min().date(),
                            max_value=processed_data['Activity Date'].max().date()
                        )
                    
                    # Apply filters
                    filtered_data = processed_data.copy()
                    
                    if selected_hotel != 'All':
                        filtered_data = filtered_data[filtered_data['Hotel'] == selected_hotel]
                    if selected_sdg != 'All':
                        filtered_data = filtered_data[filtered_data['SDG'] == selected_sdg]
                    if selected_type != 'All':
                        filtered_data = filtered_data[filtered_data['Contribution Type'] == selected_type]
                    if len(date_range) == 2:
                        filtered_data = filtered_data[
                            (filtered_data['Activity Date'].dt.date >= date_range[0]) &
                            (filtered_data['Activity Date'].dt.date <= date_range[1])
                        ]
                    
                    # Show filtered data
                    st.dataframe(
                        filtered_data.sort_values('Activity Date', ascending=False),
                        use_container_width=True,
                        column_config={
                            "Activity Date": st.column_config.DateColumn("Activity Date", format="DD/MM/YYYY"),
                            "Financial Impact": st.column_config.NumberColumn(
                                "Financial Impact",
                                format="£%.0f"
                            ),
                            "Volunteer Hours": st.column_config.NumberColumn(
                                "Volunteer Hours",
                                format="%.0f"
                            )
                        }
                    )
                    
                    # Add download button
                    csv = filtered_data.to_csv(index=False)
                    st.download_button(
                        label="Download filtered data as CSV",
                        data=csv,
                        file_name="esg_activities.csv",
                        mime="text/csv"
                    )
                    
        except Exception as e:
            st.error(f"Error loading raw data: {str(e)}")

if __name__ == "__main__":
    main()