import streamlit as st
import pandas as pd
import time
import os
from io import BytesIO
from url_resolver import URLResolver
from wayback_archiver import WaybackArchiver
from spreadsheet_processor import SpreadsheetProcessor

# Initialize components
@st.cache_resource
def get_components():
    """Initialize and cache the application components"""
    return {
        'url_resolver': URLResolver(),
        'wayback_archiver': WaybackArchiver(),
        'spreadsheet_processor': SpreadsheetProcessor()
    }

def main():
    st.set_page_config(
        page_title="SMS URL Analyzer",
        page_icon="🔗",
        layout="wide"
    )
    
    st.title("🔗 SMS URL Analyzer")
    st.markdown("**Analyze shortened URLs from SMS messages, resolve destinations, and archive in Wayback Machine**")
    
    # Initialize components
    components = get_components()
    url_resolver = components['url_resolver']
    wayback_archiver = components['wayback_archiver']
    spreadsheet_processor = components['spreadsheet_processor']
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Rate limiting settings
        st.subheader("Rate Limiting")
        delay_between_requests = st.slider(
            "Delay between requests (seconds)",
            min_value=0.1,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Delay to respect service rate limits"
        )
        
        # Retry settings
        st.subheader("Retry Settings")
        max_retries = st.number_input(
            "Maximum retries per URL",
            min_value=0,
            max_value=5,
            value=2,
            help="Number of retry attempts for failed requests"
        )
        
        # Column mapping
        st.subheader("Column Configuration")
        url_column_name = st.text_input(
            "URL Column Name",
            value="url",
            help="Name of the column containing URLs in your spreadsheet"
        )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 File Upload")
        uploaded_file = st.file_uploader(
            "Upload your spreadsheet containing shortened URLs",
            type=['csv', 'xlsx', 'xls'],
            help="Supported formats: CSV, Excel (.xlsx, .xls)"
        )
        
        if uploaded_file is not None:
            try:
                # Load and display the uploaded file
                df = spreadsheet_processor.load_file(uploaded_file)
                
                st.success(f"✅ File loaded successfully! Found {len(df)} rows.")
                
                # Show preview
                st.subheader("📋 Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Validate URL column
                if url_column_name not in df.columns:
                    st.error(f"❌ Column '{url_column_name}' not found in the spreadsheet.")
                    st.info(f"Available columns: {', '.join(df.columns.tolist())}")
                    return
                
                # Show URL statistics
                total_urls = len(df)
                non_empty_urls = df[url_column_name].notna().sum()
                
                st.info(f"📊 Found {non_empty_urls} non-empty URLs out of {total_urls} total rows")
                
                # Process URLs button
                if st.button("🚀 Start Processing URLs", type="primary", use_container_width=True):
                    process_urls(df, url_column_name, url_resolver, wayback_archiver, 
                               delay_between_requests, max_retries)
                    
            except Exception as e:
                st.error(f"❌ Error loading file: {str(e)}")
    
    with col2:
        st.header("ℹ️ How it works")
        st.markdown("""
        1. **Upload** your spreadsheet with shortened URLs
        2. **Configure** processing settings in the sidebar
        3. **Process** URLs to resolve final destinations
        4. **Archive** resolved URLs in Wayback Machine
        5. **Download** updated spreadsheet with results
        
        ### Supported URL Shorteners
        - bit.ly, tinyurl.com
        - t.co (Twitter)
        - goo.gl, short.link
        - And many more!
        
        ### Output Columns Added
        - `resolved_url`: Final destination
        - `redirect_chain`: Full redirect path
        - `wayback_url`: Archive link
        - `status`: Processing result
        - `error_message`: Error details (if any)
        """)

def process_urls(df, url_column_name, url_resolver, wayback_archiver, delay, max_retries):
    """Process URLs in the dataframe"""
    
    # Initialize result columns
    df['resolved_url'] = ''
    df['redirect_chain'] = ''
    df['wayback_url'] = ''
    df['status'] = ''
    df['error_message'] = ''
    
    # Filter rows with non-empty URLs
    urls_to_process = df[df[url_column_name].notna() & (df[url_column_name] != '')]
    total_urls = len(urls_to_process)
    
    if total_urls == 0:
        st.warning("⚠️ No URLs found to process")
        return
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_container = st.container()
    results_container = st.container()
    
    processed_count = 0
    success_count = 0
    error_count = 0
    
    with status_container:
        status_text = st.empty()
        metrics_cols = st.columns(4)
        
        with metrics_cols[0]:
            total_metric = st.metric("Total URLs", total_urls)
        with metrics_cols[1]:
            processed_metric = st.metric("Processed", processed_count)
        with metrics_cols[2]:
            success_metric = st.metric("Successful", success_count)
        with metrics_cols[3]:
            error_metric = st.metric("Errors", error_count)
    
    # Process each URL
    for idx, row in urls_to_process.iterrows():
        original_url = row[url_column_name]
        
        status_text.text(f"Processing: {original_url[:50]}...")
        
        try:
            # Resolve URL with retries
            resolved_url, redirect_chain = resolve_with_retries(
                url_resolver, original_url, max_retries
            )
            
            if resolved_url:
                # Archive in Wayback Machine
                wayback_url = archive_with_retries(
                    wayback_archiver, resolved_url, max_retries
                )
                
                # Update dataframe
                df.at[idx, 'resolved_url'] = resolved_url
                df.at[idx, 'redirect_chain'] = ' -> '.join(redirect_chain)
                df.at[idx, 'wayback_url'] = wayback_url if wayback_url else 'Failed to archive'
                df.at[idx, 'status'] = 'Success'
                df.at[idx, 'error_message'] = ''
                
                success_count += 1
            else:
                df.at[idx, 'status'] = 'Failed'
                df.at[idx, 'error_message'] = 'Unable to resolve URL'
                error_count += 1
                
        except Exception as e:
            df.at[idx, 'status'] = 'Error'
            df.at[idx, 'error_message'] = str(e)
            error_count += 1
        
        processed_count += 1
        
        # Update progress
        progress = processed_count / total_urls
        progress_bar.progress(progress)
        
        # Update metrics
        with metrics_cols[1]:
            st.metric("Processed", processed_count)
        with metrics_cols[2]:
            st.metric("Successful", success_count)
        with metrics_cols[3]:
            st.metric("Errors", error_count)
        
        # Rate limiting
        if processed_count < total_urls:  # Don't delay after the last URL
            time.sleep(delay)
    
    # Processing complete
    status_text.text("✅ Processing complete!")
    
    # Show results
    with results_container:
        st.header("📊 Processing Results")
        
        # Summary metrics
        st.subheader("Summary")
        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Total Processed", processed_count)
        with summary_cols[1]:
            st.metric("Success Rate", f"{(success_count/processed_count)*100:.1f}%")
        with summary_cols[2]:
            st.metric("Successful", success_count)
        with summary_cols[3]:
            st.metric("Failed", error_count)
        
        # Show updated dataframe
        st.subheader("Updated Data")
        st.dataframe(df, use_container_width=True)
        
        # Download processed file
        st.subheader("📥 Download Results")
        
        # Prepare download
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Processed_URLs')
        
        st.download_button(
            label="📥 Download Processed Spreadsheet",
            data=output_buffer.getvalue(),
            file_name=f"processed_urls_{int(time.time())}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )

def resolve_with_retries(url_resolver, url, max_retries):
    """Resolve URL with retry mechanism"""
    for attempt in range(max_retries + 1):
        try:
            return url_resolver.resolve_url(url)
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(1)  # Brief delay before retry
    return None, []

def archive_with_retries(wayback_archiver, url, max_retries):
    """Archive URL with retry mechanism"""
    for attempt in range(max_retries + 1):
        try:
            return wayback_archiver.archive_url(url)
        except Exception as e:
            if attempt == max_retries:
                return None
            time.sleep(1)  # Brief delay before retry
    return None

if __name__ == "__main__":
    main()