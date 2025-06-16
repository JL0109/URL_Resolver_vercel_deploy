from flask import Flask, render_template_string, request, jsonify, send_file
import pandas as pd
import time
import io
import os
from datetime import datetime

app = Flask(__name__)

# Configure for Vercel
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import modules with better error handling
modules_loaded = False
error_message = ""

try:
    from url_resolver import URLResolver
    from wayback_archiver import WaybackArchiver
    from spreadsheet_processor import SpreadsheetProcessor
    
    # Initialize components
    url_resolver = URLResolver()
    wayback_archiver = WaybackArchiver()
    spreadsheet_processor = SpreadsheetProcessor()
    modules_loaded = True
except ImportError as e:
    error_message = f"Import error: {e}"
    print(error_message)
except Exception as e:
    error_message = f"Initialization error: {e}"
    print(error_message)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMS URL Analyzer</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 40px 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .content {
            padding: 40px;
        }
        
        .warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .upload-section {
            background: #f8f9fa;
            border: 3px dashed #dee2e6;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            transition: all 0.3s ease;
        }
        
        .upload-section:hover {
            border-color: #667eea;
            background: #f0f2ff;
        }
        
        .settings {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
        }
        
        .form-group {
            margin-bottom: 0;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #495057;
        }
        
        .form-control {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: white;
        }
        
        .form-control:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .status {
            margin: 25px 0;
            padding: 20px;
            border-radius: 12px;
            display: none;
            font-weight: 500;
        }
        
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border-left: 5px solid #17a2b8;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border-left: 5px solid #28a745;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 5px solid #dc3545;
        }
        
        .how-it-works {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            padding: 30px;
            border-radius: 15px;
            margin-top: 40px;
            border-left: 5px solid #2196f3;
        }
        
        @media (max-width: 768px) {
            body { padding: 10px; }
            .content { padding: 20px; }
            .form-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SMS URL Analyzer</h1>
            <p>Analyze shortened URLs from SMS messages, resolve destinations, and archive in Wayback Machine</p>
        </div>

        <div class="content">
            {% if not modules_loaded %}
            <div class="warning">
                <strong>Warning:</strong> Some modules failed to load. Application may not work properly.<br>
                Error: {{ error_message }}
            </div>
            {% endif %}
            
            <div class="warning">
                <strong>Note:</strong> Due to Vercel's 10-second timeout limit, please limit file size to small datasets (under 100 URLs) for best results.
            </div>

            <div class="upload-section">
                <h3>Upload Spreadsheet</h3>
                <input type="file" id="fileInput" accept=".csv,.xlsx,.xls" class="form-control" style="margin-bottom: 15px;">
                <p>Supported formats: CSV, Excel (.xlsx, .xls) - Max 16MB</p>
            </div>

            <div class="settings">
                <h3>Configuration</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="urlColumn">URL Column Name:</label>
                        <input type="text" id="urlColumn" class="form-control" value="url" placeholder="url">
                    </div>
                    <div class="form-group">
                        <label for="delay">Delay Between Requests (seconds):</label>
                        <input type="number" id="delay" class="form-control" value="0.5" min="0.1" max="2.0" step="0.1">
                    </div>
                    <div class="form-group">
                        <label for="retries">Maximum Retries:</label>
                        <input type="number" id="retries" class="form-control" value="1" min="0" max="3">
                    </div>
                    <div class="form-group">
                        <label for="maxUrls">Max URLs to Process:</label>
                        <input type="number" id="maxUrls" class="form-control" value="50" min="1" max="100">
                    </div>
                </div>
            </div>

            <button id="processBtn" class="btn" onclick="processUrls()">Start Processing URLs</button>

            <div id="status" class="status"></div>
            <button id="downloadBtn" class="btn" onclick="downloadResults()" style="display: none; margin-top: 20px;">Download Results</button>

            <div class="how-it-works">
                <h3>How it works</h3>
                <ol>
                    <li><strong>Upload</strong> your spreadsheet with shortened URLs</li>
                    <li><strong>Configure</strong> processing settings above</li>
                    <li><strong>Process</strong> URLs to resolve final destinations</li>
                    <li><strong>Archive</strong> resolved URLs in Wayback Machine</li>
                    <li><strong>Download</strong> updated spreadsheet with results</li>
                </ol>
                
                <h4>Supported URL Shorteners</h4>
                <p>bit.ly, tinyurl.com, t.co (Twitter), goo.gl, short.link, and many more!</p>
                
                <h4>Vercel Limitations</h4>
                <p>This deployment has a 10-second timeout. For larger datasets, consider running locally or using a different hosting platform.</p>
            </div>
        </div>
    </div>

    <script>
        let processedData = null;

        function showStatus(message, type = 'info') {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';
        }

        async function processUrls() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                showStatus('Please select a file first.', 'error');
                return;
            }

            // Check file size
            if (file.size > 16 * 1024 * 1024) {
                showStatus('File too large. Maximum size is 16MB.', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('url_column', document.getElementById('urlColumn').value);
            formData.append('delay', document.getElementById('delay').value);
            formData.append('retries', document.getElementById('retries').value);
            formData.append('max_urls', document.getElementById('maxUrls').value);

            const processBtn = document.getElementById('processBtn');
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';

            showStatus('Starting URL processing...', 'info');

            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`Server error: ${response.status} - ${errorText}`);
                }

                const result = await response.json();
                
                if (result.error) {
                    showStatus(`Error: ${result.error}`, 'error');
                    return;
                }

                processedData = result.data;
                showStatus(`Processing complete! Processed ${result.total} URLs, ${result.successful} successful.`, 'success');
                document.getElementById('downloadBtn').style.display = 'inline-block';

            } catch (error) {
                console.error('Processing error:', error);
                showStatus(`Error: ${error.message}`, 'error');
            } finally {
                processBtn.disabled = false;
                processBtn.textContent = 'Start Processing URLs';
            }
        }

        async function downloadResults() {
            if (!processedData) {
                showStatus('No processed data available for download.', 'error');
                return;
            }

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ data: processedData })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `processed_urls_${Date.now()}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                } else {
                    const errorText = await response.text();
                    showStatus(`Download error: ${errorText}`, 'error');
                }
            } catch (error) {
                console.error('Download error:', error);
                showStatus(`Download error: ${error.message}`, 'error');
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, modules_loaded=modules_loaded, error_message=error_message)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'modules_loaded': modules_loaded,
        'error_message': error_message if not modules_loaded else None,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/process', methods=['POST'])
def process_urls():
    if not modules_loaded:
        return jsonify({'error': f'Required modules not loaded properly: {error_message}'}), 500
    
    try:
        # Validate file upload
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        url_column = request.form.get('url_column', 'url')
        delay = float(request.form.get('delay', 0.5))
        max_retries = int(request.form.get('retries', 1))
        max_urls = int(request.form.get('max_urls', 50))
        
        # Load the spreadsheet
        df = spreadsheet_processor.load_file(file)
        
        # Validate URL column exists
        if url_column not in df.columns:
            available_cols = ', '.join(df.columns.tolist())
            return jsonify({
                'error': f'Column "{url_column}" not found. Available columns: {available_cols}'
            }), 400
        
        # Initialize result columns
        df['resolved_url'] = ''
        df['redirect_chain'] = ''
        df['wayback_url'] = ''
        df['status'] = ''
        df['error_message'] = ''
        
        # Filter rows with non-empty URLs and limit for Vercel
        urls_to_process = df[df[url_column].notna() & (df[url_column] != '')].head(max_urls)
        total_urls = len(urls_to_process)
        
        if total_urls == 0:
            return jsonify({'error': 'No valid URLs found to process'}), 400
        
        processed_count = 0
        success_count = 0
        error_count = 0
        
        start_time = time.time()
        
        # Process each URL with timeout protection
        for idx, row in urls_to_process.iterrows():
            # Check if we're approaching Vercel's timeout (8 seconds to be safe)
            if time.time() - start_time > 8:
                # Mark remaining URLs as timeout
                remaining_urls = urls_to_process.iloc[processed_count:]
                for remaining_idx in remaining_urls.index:
                    df.at[remaining_idx, 'status'] = 'Timeout'
                    df.at[remaining_idx, 'error_message'] = 'Processing timeout - increase max_urls setting or run locally'
                    error_count += 1
                    processed_count += 1
                break
            
            original_url = str(row[url_column]).strip()
            
            try:
                # Resolve URL with retries
                resolved_url, redirect_chain = resolve_with_retries(original_url, max_retries)
                
                if resolved_url:
                    # Archive in Wayback Machine (skip for speed in Vercel)
                    # wayback_url = archive_with_retries(resolved_url, max_retries)
                    
                    # Update dataframe
                    df.at[idx, 'resolved_url'] = resolved_url
                    df.at[idx, 'redirect_chain'] = ' -> '.join(redirect_chain) if redirect_chain else original_url
                    df.at[idx, 'wayback_url'] = 'Skipped in Vercel deployment'  # wayback_url if wayback_url else 'Failed to archive'
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
            
            # Minimal delay for Vercel
            if processed_count < total_urls and delay > 0:
                time.sleep(min(delay, 0.2))  # Cap at 0.2s for Vercel
        
        # Convert to JSON-serializable format
        result_data = df.to_dict('records')
        
        return jsonify({
            'data': result_data,
            'processed': processed_count,
            'successful': success_count,
            'failed': error_count,
            'total': total_urls
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Processing error: {error_details}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_results():
    try:
        data = request.json.get('data', [])
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Processed_URLs')
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'processed_urls_{int(time.time())}.xlsx'
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Download error: {error_details}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

def resolve_with_retries(url, max_retries):
    """Resolve URL with retry mechanism"""
    for attempt in range(max_retries + 1):
        try:
            return url_resolver.resolve_url(url)
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(0.1)  # Very short delay for Vercel
    return None, []

def archive_with_retries(url, max_retries):
    """Archive URL with retry mechanism"""
    for attempt in range(max_retries + 1):
        try:
            return wayback_archiver.archive_url(url)
        except Exception as e:
            if attempt == max_retries:
                return None
            time.sleep(0.1)  # Very short delay for Vercel
    return None

# Vercel entry point
app = app

if __name__ == '__main__':
    app.run(debug=True)
