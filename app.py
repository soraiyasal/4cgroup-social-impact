
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(page_title="4C Group Impact Dashboard", layout="wide", page_icon="🤝")

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
        
        try:
            # Debug spreadsheet access
            sheet = client.open_by_key(st.secrets["sheet_id"])
            
            # Get the first worksheet (assumes data is in first tab)
            worksheet = sheet.get_worksheet(0)
            
            # Get all records with row count
            try:
                # Fetch raw data for debugging
                raw_data = worksheet.get_all_values()
                headers = raw_data[0]
                data = raw_data[1:]
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=headers)
                if not df.empty:
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

def show_instagram_feed():
    """Display the Instagram feed for 4C Group with reliable iframe method"""
    
    st.markdown("""
        <style>
        .instagram-container {
            position: relative;
            width: 100%;
            margin: 0 auto;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .instagram-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 20px;
            background: linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(255,255,255,0));
            z-index: 10;
            pointer-events: none;
        }
        .instagram-button {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background-color: #E1306C;
            color: white !important;
            text-decoration: none;
            border-radius: 25px;
            box-shadow: 0 4px 10px rgba(225, 48, 108, 0.3);
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
            text-align: center;
        }
        .instagram-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(225, 48, 108, 0.4);
        }
        </style>
        
        <div class="instagram-container">
            <div class="instagram-overlay"></div>
            <iframe src="https://www.instagram.com/4cgroup_hq/embed" 
                width="100%" 
                height="600" 
                frameborder="0" 
                scrolling="no" 
                allowtransparency="true">
            </iframe>
        </div>
        <div style="text-align: center; margin-top: 15px;">
            <a href="https://www.instagram.com/4cgroup_hq/" target="_blank" class="instagram-button">
                Follow Us on Instagram
            </a>
        </div>
    """, unsafe_allow_html=True)

def create_sdg_highlight_card(sdg_name, count, max_count):
    """Create an attractive card for a highlighted SDG"""
    if sdg_name in SDG_INFO:
        color = SDG_INFO[sdg_name]['color']
        number = SDG_INFO[sdg_name]['number']
        description = SDG_INFO[sdg_name]['description']
    else:
        color = '#777777'
        number = ""
        description = ""
    
    # Calculate percentage of the max for progress bar
    percentage = (count / max_count) * 100 if max_count > 0 else 0
    
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
    
    html = f"""
    <div style="background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); 
                overflow: hidden; transition: all 0.3s ease; height: 100%; 
                border-top: 5px solid {color};">
        <div style="padding: 20px;">
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
                <div style="width: 60px; height: 60px; border-radius: 50%; background-color: {color};
                           display: flex; align-items: center; justify-content: center; 
                           color: white; font-weight: bold; font-size: 24px; flex-shrink: 0;
                           box-shadow: 0 5px 15px {color}60;">
                    {number}
                </div>
                <div>
                    <div style="font-weight: 700; font-size: 18px; color: #1e293b;">{sdg_name}</div>
                    <div style="color: {color}; font-size: 24px; font-weight: 700;">{count}</div>
                </div>
            </div>
            <p style="color: #64748b; font-size: 14px; line-height: 1.5; margin-bottom: 15px;">
                {description[:120]}...
            </p>
            <div style="height: 8px; background-color: #e2e8f0; border-radius: 4px; overflow: hidden;">
                <div style="height: 100%; width: {percentage}%; background-color: {color}; 
                            transition: width 1.5s ease;"></div>
            </div>
            <div style="text-align: right; margin-top: 8px;">
                <span style="display: inline-block; padding: 4px 10px; border-radius: 20px; 
                           font-size: 12px; font-weight: 500; background-color: {badge_color}20; 
                           color: {badge_color};">
                    {badge_text}
                </span>
            </div>
        </div>
    </div>
    """
    return html

def show_overview_dashboard(data):
    """Display an engaging dashboard with improved layout and visuals"""
    
    # Custom CSS for modern, engaging design
    st.markdown("""
        <style>
        /* Modern aesthetic */
        .main {
            background-color: #f8fafc;
        }
        
        /* Dashboard header styling */
        .dashboard-title {
            font-size: 32px;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 0;
            text-align: center;
        }
        
        .dashboard-subtitle {
            font-size: 16px;
            color: #64748b;
            margin-top: 5px;
            text-align: center;
            max-width: 700px;
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Metrics styling */
        .metrics-container {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            margin-bottom: 25px;
        }
        
        .metric-card {
            flex: 1;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 20px rgba(0, 0, 0, 0.1);
        }
        
        .metric-title {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        
        /* Section styling */
        .dashboard-section {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            padding: 25px;
            margin-bottom: 30px;
        }
        
        .section-header {
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
        }
        
        .section-header::before {
            content: "";
            display: inline-block;
            width: 4px;
            height: 20px;
            background: linear-gradient(to bottom, #3B82F6, #8B5CF6);
            margin-right: 10px;
            border-radius: 2px;
        }
        
        /* Chart styling */
        .chart-container {
            background: transparent;
        }
        
        /* Custom tab styling for dashboard */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            padding: 0 20px;
            background-color: transparent;
            border-radius: 0;
            font-size: 14px;
            font-weight: 500;
            color: #64748b;
        }
        
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #3B82F6;
            height: 3px;
            bottom: 0;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: #3B82F6;
            font-weight: 600;
        }
        
        /* Make normal streamlit elements work better with the design */
        div[data-testid="stMetric"] {
            background-color: white;
        }
        
        /* Responsive Grid Layout */
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Dashboard header with engaging headline
    st.markdown('<h1 class="dashboard-title">Community Impact Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">Tracking our contributions to sustainable development and social responsibility across all 4C Group properties.</p>', unsafe_allow_html=True)
    
    # Filter data by time period
    current_date = datetime.now()
    
    # Create time period selector with more engaging design
    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            background-color: white;
            border-radius: 8px;
            padding: 8px 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        time_periods = {
            "Financial Year to Date": {"name": "Financial YTD", "description": f"From Apr 1 to present"},
            "Current Year to Date": {"name": "Current YTD", "description": f"From Jan 1, {current_date.year} to present"},
            "Last 6 Months": {"name": "Last 6 Months", "description": "Most recent 6-month period"},
            "Last 12 Months": {"name": "Last 12 Months", "description": "Full year rolling period"},
            "All Time": {"name": "All Time", "description": "Complete historical data"}
        }
        
        period_options = list(time_periods.keys())
        selected_period = st.selectbox("Select Time Period:", period_options, index=0)
        period_info = time_periods[selected_period]
    
    # Filter data based on selected period
    if selected_period == "Financial Year to Date":
        # Financial year starts in April
        if current_date.month < 4:  # Jan-Mar
            fy_start = datetime(current_date.year - 1, 4, 1)
        else:  # Apr-Dec
            fy_start = datetime(current_date.year, 4, 1)
        filtered_data = data[data['Activity Date'] >= fy_start]
        
    elif selected_period == "Current Year to Date":
        year_start = datetime(current_date.year, 1, 1)
        filtered_data = data[data['Activity Date'] >= year_start]
        
    elif selected_period == "Last 6 Months":
        # Calculate date 6 months ago
        month = current_date.month - 6
        year = current_date.year
        if month <= 0:
            month += 12
            year -= 1
        six_months_ago = datetime(year, month, 1)
        filtered_data = data[data['Activity Date'] >= six_months_ago]
        
    elif selected_period == "Last 12 Months":
        # Calculate date 12 months ago
        year_ago = datetime(current_date.year - 1, current_date.month, 1)
        filtered_data = data[data['Activity Date'] >= year_ago]
        
    else:  # All Time
        filtered_data = data.copy()
    
    # Calculate key metrics
    total_volunteer_hours = pd.to_numeric(filtered_data['Volunteer Hours'], errors='coerce').sum()
    total_financial_impact = pd.to_numeric(filtered_data['Financial Impact'], errors='coerce').sum()
    total_activities = len(filtered_data)
    unique_charities = filtered_data['Organization'].nunique()
    
    # Display metrics in an engaging, modern layout with st.columns instead of HTML
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "VOLUNTEER HOURS",
            f"{int(total_volunteer_hours):,}",
            help="Total volunteer hours contributed"
        )
    with col2:
        st.metric(
            "FINANCIAL IMPACT",
            f"£{int(total_financial_impact):,}",
            help="Total financial contribution value"
        )
    with col3:
        st.metric(
            "ACTIVITIES",
            f"{int(total_activities):,}",
            help="Number of community engagement activities"
        )
    with col4:
        st.metric(
            "CHARITY PARTNERS",
            f"{int(unique_charities):,}",
            help="Number of organizations supported"
        )
    
    # Instagram feed section - prominent placement
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Latest From Our Instagram</div>', unsafe_allow_html=True)
    show_instagram_feed()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # SDG Highlights Section - improved visual design
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">SDG Impact Highlights</div>', unsafe_allow_html=True)
    
    # Process SDG data
    sdg_metrics = filtered_data.groupby('SDG').size().reset_index(name='Count')
    
    if not sdg_metrics.empty:
        # Sort by count and get top SDGs
        sdg_metrics = sdg_metrics.sort_values('Count', ascending=False)
        max_count = sdg_metrics['Count'].max()
        
        # Display top 3 SDGs in prominent cards
        top_sdgs = sdg_metrics.head(3)
        
        # Create a responsive grid for the SDG highlight cards
        st.markdown('<div class="grid-container">', unsafe_allow_html=True)
        
        # Create each highlight card
        for _, sdg in top_sdgs.iterrows():
            sdg_name = sdg['SDG']
            sdg_count = sdg['Count']
            st.markdown(create_sdg_highlight_card(sdg_name, sdg_count, max_count), unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show remaining SDGs in a more compact format
        if len(sdg_metrics) > 3:
            other_sdgs = sdg_metrics.iloc[3:]
            
            st.markdown('<div style="margin-top: 25px;">', unsafe_allow_html=True)
            st.markdown('<div style="font-weight: 600; font-size: 16px; margin-bottom: 15px; color: #334155;">Other SDG Contributions</div>', unsafe_allow_html=True)
            
            # Create a bar chart for the remaining SDGs
            fig = px.bar(
                other_sdgs,
                x='SDG',
                y='Count',
                color='SDG',
                color_discrete_map={sdg_name: SDG_INFO.get(sdg_name, {}).get('color', '#777777') for sdg_name in other_sdgs['SDG']},
                template='plotly_white'
            )
            
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=10, b=40),
                xaxis_title="",
                yaxis_title="Activities",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                bargap=0.4
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Hotel Contributions - improved layout
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Hotel Contributions</div>', unsafe_allow_html=True)
    
    # Process hotel data
    hotel_metrics = filtered_data.groupby('Hotel').agg({
        'Volunteer Hours': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Financial Impact': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Activity Date': 'count'
    }).reset_index().rename(columns={'Activity Date': 'Activities'})
    
    # Sort by total impact
    hotel_metrics['Total Impact'] = hotel_metrics['Volunteer Hours'] + (hotel_metrics['Financial Impact'] / 100)
    hotel_metrics = hotel_metrics.sort_values('Total Impact', ascending=False)
    
    # Create engaging hotel impact visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Filter to only show hotels with volunteer hours > 0
        volunteer_hotels = hotel_metrics[hotel_metrics['Volunteer Hours'] > 0].copy()
        
        if not volunteer_hotels.empty:
            # Sort by volunteer hours
            volunteer_hotels = volunteer_hotels.sort_values('Volunteer Hours', ascending=False).head(8)
            
            fig1 = px.bar(
                volunteer_hotels, 
                x='Volunteer Hours',
                y='Hotel',
                orientation='h',
                color='Volunteer Hours',
                color_continuous_scale=['#93c5fd', '#3b82f6', '#1d4ed8'],
                template='plotly_white',
                title=f'Top Hotels by Volunteer Hours'
            )
            
            fig1.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                title_font_size=16,
                title_x=0.5,
                xaxis_title="Hours",
                yaxis_title="",
                coloraxis_showscale=False,
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis={'categoryorder':'total ascending'}
            )
            
            fig1.update_traces(
                hovertemplate="<b>%{y}</b><br>Hours: %{x:,.0f}<extra></extra>"
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No volunteer hours recorded in this period.")
    
    with col2:
        # Filter to only show hotels with financial impact > 0
        financial_hotels = hotel_metrics[hotel_metrics['Financial Impact'] > 0].copy()
        
        if not financial_hotels.empty:
            # Sort by financial impact
            financial_hotels = financial_hotels.sort_values('Financial Impact', ascending=False).head(8)
            
            fig2 = px.bar(
                financial_hotels, 
                x='Financial Impact',
                y='Hotel',
                orientation='h',
                color='Financial Impact',
                color_continuous_scale=['#a7f3d0', '#10b981', '#065f46'],
                template='plotly_white',
                title=f'Top Hotels by Financial Impact'
            )
            
            fig2.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                title_font_size=16,
                title_x=0.5,
                xaxis_title="Amount (£)",
                yaxis_title="",
                coloraxis_showscale=False,
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis={'categoryorder':'total ascending'}
            )
            
            fig2.update_traces(
                hovertemplate="<b>%{y}</b><br>Amount: £%{x:,.0f}<extra></extra>"
            )
            
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No financial contributions recorded in this period.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Activity Timeline
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Activity Timeline</div>', unsafe_allow_html=True)
    
    # Create monthly activity counts
    if not filtered_data.empty:
        # Resample data by month
        timeline_data = filtered_data.copy()
        timeline_data['Month'] = timeline_data['Activity Date'].dt.to_period('M')
        monthly_counts = timeline_data.groupby('Month').size().reset_index(name='Activities')
        monthly_counts['Month'] = monthly_counts['Month'].dt.to_timestamp()
        
        # Create line chart
        fig3 = px.line(
            monthly_counts,
            x='Month',
            y='Activities',
            markers=True,
            line_shape='spline',
            template='plotly_white'
        )
        
        fig3.update_traces(
            line=dict(color='#8B5CF6', width=3),
            marker=dict(color='#ffffff', size=8, line=dict(color='#8B5CF6', width=2)),
            hovertemplate="<b>%{x|%b %Y}</b><br>Activities: %{y}<extra></extra>"
        )
        
        fig3.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=10, b=40),
            xaxis_title="",
            yaxis_title="Activities",
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                tickformat="%b %Y",
                tickangle=-45,
                tickmode='auto',
                nticks=10
            )
        )
        
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No activity data available for timeline visualization.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Charity Partners Section - with engaging cards
    st.markdown('<div class="dashboard-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">Charity Partner Highlights</div>', unsafe_allow_html=True)
    
    # Process charity data
    charity_metrics = filtered_data.groupby('Organization').agg({
        'Volunteer Hours': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Financial Impact': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Activity Date': 'count'
    }).reset_index().rename(columns={'Activity Date': 'Activities'})
    
    # Sort by total impact
    charity_metrics['Total Impact'] = charity_metrics['Volunteer Hours'] + (charity_metrics['Financial Impact'] / 100)
    charity_metrics = charity_metrics.sort_values('Total Impact', ascending=False).head(8)
    
    if not charity_metrics.empty:
        # Color palette for charity logos
        charity_colors = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EC4899', '#EF4444', '#06B6D4', '#A855F7']
        
        # Create charity cards with improved design
        st.markdown("""
            <style>
            .charity-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            
            .charity-card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05);
                overflow: hidden;
                transition: all 0.3s ease;
                height: 100%;
            }
            
            .charity-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            }
            
            .charity-header {
                padding: 15px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .charity-logo {
                width: 45px;
                height: 45px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 700;
                font-size: 18px;
            }
            
            .charity-name {
                font-weight: 600;
                font-size: 15px;
                color: #0f172a;
                line-height: 1.3;
            }
            
            .charity-body {
                padding: 0 15px 15px;
            }
            
            .charity-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin-top: 10px;
            }
            
            .charity-stat {
                background: #f8fafc;
                border-radius: 8px;
                padding: 10px;
                text-align: center;
            }
            
            .charity-stat-value {
                font-weight: 700;
                font-size: 16px;
                color: #0f172a;
            }
            
            .charity-stat-label {
                font-size: 11px;
                color: #64748b;
                margin-top: 3px;
            }
            </style>
            
            <div class="charity-grid">
        """, unsafe_allow_html=True)
        
        for idx, charity in charity_metrics.iterrows():
            color = charity_colors[idx % len(charity_colors)]
            first_letter = charity['Organization'][0].upper() if charity['Organization'] else '?'
            
            st.markdown(f"""
                <div class="charity-card">
                    <div class="charity-header">
                        <div class="charity-logo" style="background-color: {color};">
                            {first_letter}
                        </div>
                        <div class="charity-name">
                            {charity['Organization']}
                        </div>
                    </div>
                    <div class="charity-body">
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
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No charity partnership data available for the selected period.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_data_filters(data):
    """Display data filters and raw data"""
    st.header("Data Explorer")
    
    # Add filters with improved design
    st.markdown("""
        <style>
        .filter-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.subheader("Data Filters")
    
    cols = st.columns(4)
    
    with cols[0]:
        hotels = ['All'] + sorted(data['Hotel'].unique().tolist())
        selected_hotel = st.selectbox('Hotel:', hotels)
    
    with cols[1]:
        sdgs = ['All'] + sorted(data['SDG'].unique().tolist())
        selected_sdg = st.selectbox('SDG:', sdgs)
    
    with cols[2]:
        contribution_types = ['All'] + sorted(data['Contribution Type'].unique().tolist())
        selected_type = st.selectbox('Contribution Type:', contribution_types)
    
    with cols[3]:
        date_range = st.date_input(
            "Date Range:",
            value=(data['Activity Date'].min(), data['Activity Date'].max()),
            min_value=data['Activity Date'].min().date(),
            max_value=data['Activity Date'].max().date()
        )
    
    # Apply filters
    filtered_data = data.copy()
    
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
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show filtered data with improved design
    if not filtered_data.empty:
        st.markdown(f"<div style='margin-bottom: 10px;'><b>{len(filtered_data)}</b> activities found matching your filters.</div>", unsafe_allow_html=True)
        
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
        
        # Add download button with improved design
        csv = filtered_data.to_csv(index=False)
        st.download_button(
            label="📊 Download Data as CSV",
            data=csv,
            file_name="esg_activities.csv",
            mime="text/csv",
        )
    else:
        st.warning("No data matches your current filter selections. Try adjusting your filters.")

def main():
    # Apply custom styling for the entire app
    st.markdown("""
        <style>
        /* Overall app styling */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Better header spacing */
        h1, h2, h3, h4 {
            margin-top: 0 !important;
        }
        
        /* Fix for metric hover */
        div[data-testid="stMetric"] {
            background-color: transparent;
            box-shadow: none;
        }
        
        div[data-testid="stMetric"]:hover {
            box-shadow: none;
        }
        
        /* Better tab styling */
        button[data-baseweb="tab"] {
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create tabs with enhanced styling
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🎯 SDG Information", "📝 Submit Activity", "📋 Data Explorer"])
    
    with tab1:
        try:
            data = fetch_sheet_data()
            if not data.empty:
                processed_data = reshape_survey_data(data)
                if not processed_data.empty:
                    show_overview_dashboard(processed_data)
                else:
                    st.error("Failed to process data. Please check the data format.")
            else:
                st.error("No data found in Google Sheet. Please check your connection and data source.")
                
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
        try:
            data = fetch_sheet_data()
            if not data.empty:
                processed_data = reshape_survey_data(data)
                if not processed_data.empty:
                    show_data_filters(processed_data)
                else:
                    st.error("Failed to process data. Please check the data format.")
            else:
                st.error("No data found in Google Sheet. Please check your connection and data source.")
        except Exception as e:
            st.error(f"Error loading raw data: {str(e)}")

if __name__ == "__main__":
    main()