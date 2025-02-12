import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

# Page configuration
st.set_page_config(page_title="ESG Impact Dashboard", layout="wide")

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
                'Financial Impact': row[f"{prefix}Everything else: Financial Impact or Equiv (If meeting room or guest - how much would that have cost, food donation amount, etc)"]
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
        
        # Convert numeric fields
        reshaped_df['Volunteer Hours'] = pd.to_numeric(reshaped_df['Volunteer Hours'], errors='coerce').fillna(0)
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
    """Display the main dashboard"""
    # Find the latest month in the data
    latest_date = data['Activity Date'].max()
    
    # Time period selector
    col1, col2 = st.columns([3, 1])
    with col2:
        view_type = st.radio(
            "Select View",
            ["Latest Month", "Financial YTD"],
            horizontal=True
        )
    
    # Filter data based on selected period
    if view_type == "Latest Month":
        filtered_data = data[
            (data['Activity Date'].dt.month == latest_date.month) & 
            (data['Activity Date'].dt.year == latest_date.year)
        ]
        period_text = latest_date.strftime("%B %Y")
    else:
        # Calculate financial year
        if latest_date.month < 4:  # Jan-Mar
            fy_start = datetime(latest_date.year - 1, 4, 1)
            fy_end = datetime(latest_date.year, 3, 31)
            fy_text = f"FY{latest_date.year-1}/{latest_date.year}"
        else:  # Apr-Dec
            fy_start = datetime(latest_date.year, 4, 1)
            fy_end = datetime(latest_date.year + 1, 3, 31)
            fy_text = f"FY{latest_date.year}/{latest_date.year+1}"
        
        filtered_data = data[
            (data['Activity Date'] >= fy_start) & 
            (data['Activity Date'] <= fy_end)
        ]
        period_text = f"{fy_text} (Apr-Mar)"
    
    st.subheader(f"Impact Overview - {period_text}")
    
    # Calculate metrics
    total_volunteer_hours = pd.to_numeric(filtered_data['Volunteer Hours'], errors='coerce').sum()
    total_financial_impact = pd.to_numeric(filtered_data['Financial Impact'], errors='coerce').sum()
    total_activities = len(filtered_data)
    
    # Display metrics with enhanced styling
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div style='text-align: center; padding: 10px; background-color: #f0f9ff; border-radius: 10px; border: 1px solid #3B82F6'>
                <h3 style='color: #3B82F6; margin: 0;'>Volunteer Hours</h3>
                <p style='font-size: 24px; font-weight: bold; margin: 10px 0;'>{:,.0f}</p>
            </div>
        """.format(total_volunteer_hours), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div style='text-align: center; padding: 10px; background-color: #f0fdf9; border-radius: 10px; border: 1px solid #10B981'>
                <h3 style='color: #10B981; margin: 0;'>Financial Impact</h3>
                <p style='font-size: 24px; font-weight: bold; margin: 10px 0;'>£{:,.0f}</p>
            </div>
        """.format(total_financial_impact), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div style='text-align: center; padding: 10px; background-color: #faf5ff; border-radius: 10px; border: 1px solid #8B5CF6'>
                <h3 style='color: #8B5CF6; margin: 0;'>Activities</h3>
                <p style='font-size: 24px; font-weight: bold; margin: 10px 0;'>{:,.0f}</p>
            </div>
        """.format(total_activities), unsafe_allow_html=True)
    
    # Prepare chart data
    hotel_metrics = filtered_data.groupby('Hotel').agg({
        'Volunteer Hours': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Financial Impact': lambda x: pd.to_numeric(x, errors='coerce').sum(),
        'Activity Date': 'count'
    }).reset_index()
    
    sdg_metrics = filtered_data.groupby('SDG').size().reset_index(name='Count')
    
    # Enhanced charts
    st.markdown("### Impact by Hotel")
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.bar(
            hotel_metrics, 
            x='Hotel', 
            y='Volunteer Hours',
            title='Volunteer Hours Distribution',
            color_discrete_sequence=['#3B82F6'],
            template='plotly_white'
        )
        fig1.update_layout(
            height=400,
            title_x=0.5,
            title_font_size=16,
            xaxis_title="",
            yaxis_title="Hours",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            bargap=0.3
        )
        fig1.update_traces(
            marker_line_color='#2563EB',
            marker_line_width=1.5,
            hovertemplate="<b>%{x}</b><br>Hours: %{y:,.0f}<extra></extra>"
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.bar(
            hotel_metrics, 
            x='Hotel', 
            y='Financial Impact',
            title='Financial Contribution Distribution',
            color_discrete_sequence=['#10B981'],
            template='plotly_white'
        )
        fig2.update_layout(
            height=400,
            title_x=0.5,
            title_font_size=16,
            xaxis_title="",
            yaxis_title="Amount (£)",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            bargap=0.3
        )
        fig2.update_traces(
            marker_line_color='#059669',
            marker_line_width=1.5,
            hovertemplate="<b>%{x}</b><br>Amount: £%{y:,.0f}<extra></extra>"
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("### Combined Impact Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            name='Volunteer Hours',
            x=hotel_metrics['Hotel'],
            y=hotel_metrics['Volunteer Hours'],
            yaxis='y',
            marker_color='#3B82F6',
            marker_line_color='#2563EB',
            marker_line_width=1.5,
            hovertemplate="<b>%{x}</b><br>Hours: %{y:,.0f}<extra></extra>"
        ))
        fig3.add_trace(go.Bar(
            name='Financial Impact',
            x=hotel_metrics['Hotel'],
            y=hotel_metrics['Financial Impact'],
            yaxis='y2',
            marker_color='#10B981',
            marker_line_color='#059669',
            marker_line_width=1.5,
            hovertemplate="<b>%{x}</b><br>Amount: £%{y:,.0f}<extra></extra>"
        ))
        fig3.update_layout(
            title='Combined Hotel Impact',
            title_x=0.5,
            title_font_size=16,
            yaxis=dict(title='Volunteer Hours', side='left', showgrid=True, gridcolor='rgba(0,0,0,0.1)'),
            yaxis2=dict(title='Financial Impact (£)', side='right', overlaying='y', showgrid=False),
            height=400,
            template='plotly_white',
            bargap=0.3,
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        if not sdg_metrics.empty:
            st.plotly_chart(
                create_sdg_treemap(sdg_metrics.set_index('SDG')),
                use_container_width=True
            )
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