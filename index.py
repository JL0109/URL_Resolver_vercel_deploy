from flask import Flask, render_template_string, request, jsonify, send_file
import pandas as pd
import time
import io
from datetime import datetime
import sys
import os

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from url_resolver import URLResolver
from wayback_archiver import WaybackArchiver
from spreadsheet_processor import SpreadsheetProcessor

app = Flask(__name__)

# Initialize components
url_resolver = URLResolver()
wayback_archiver = WaybackArchiver()
spreadsheet_processor = SpreadsheetProcessor()

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMS URL Analyzer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }
        .upload-section {
            border: 2px dashed #ddd;
            padding: 30px;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 20px;
            transition: border-color 0.3s;
        }
        .upload-section:hover {
            border-color: #007bff;
        }
        .settings {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .settings h3 {
            margin-top: 0;
            color: #495057;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #495057;
        }
        .form-control {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .btn {
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #0056b3;
        }
        .btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .progress {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 20px 0;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background: #28a745;
            width: 0%;
            transition: width 0.3s;
        }
        .status {
            margin: 20px 0;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .results {
            margin-top: 30px;
            display: none;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .metric {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
        .metric-label {
            color: #6c757d;
            font-size: 14px;
        }
        .how-it-works {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }
        .how-it-works h3 {
            color: #1976d2;
            margin-top: 0;
        }
        .how-it-works ol {
            padding-left: 20px;
        }
        .how-it-works li {
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SMS URL Analyzer</h1>
            <p>Analyze shortened URLs from SMS messages, resolve destinations, and archive in Wayback Machine</p>
        </div>

        <div class="upload-section">
            <h3>Upload Spreadsheet</h3>
            <input type="file" id="fileInput" accept=".csv,.xlsx,.xls" class="form-control" style="margin-bottom: 15px;">
            <p>Supported formats: CSV, Excel (.xlsx, .xls)</p>
        </div>

        <div class="settings">
            <h3>Configuration</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <div class="form-group">
                    <label for="urlColumn">URL Column Name:</label>
                    <input type="text" id="urlColumn" class="form-control" value="url" placeholder="url">
                </div>
                <div class="form-group">
                    <label for="delay">Delay Between Requests (seconds):</label>
                    <input type="number" id="delay" class="form-control" value="1.0" min="0.1" max="5.0" step="0.1">
                </div>
                <div class="form-group">
                    <label for="retries">Maximum Retries:</label>
                    <input type="number" id="retries" class="form-control" value="2" min="0" max="5">
                </div>
            </div>
        </div>

        <button id="processBtn" class="btn" onclick="processUrls()">Start Processing URLs</button>

        <div id="status" class="status"></div>
        <div class="progress" id="progressContainer">
            <div class="progress-bar" id="progressBar"></div>
        </div>

        <div id="results" class="results">
            <h3>Processing Results</h3>
            <div class="metrics" id="metrics"></div>
            <button id="downloadBtn" class="btn" onclick="downloadResults()" style="display: none;">Download Results</button>
        </div>

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
            
            <h4>Output Columns Added</h4>
            <p><strong>resolved_url:</strong> Final destination<br>
            <strong>redirect_chain:</strong> Full redirect path<br>
            <strong>wayback_url:</strong> Archive link<br>
            <strong>status:</strong> Processing result<br>
            <strong>error_message:</strong> Error details (if any)</p>
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

        function updateProgress(percent) {
            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            progressContainer.style.display = 'block';
            progressBar.style.width = percent + '%';
        }

        function updateMetrics(processed, successful, failed, total) {
            const metrics = document.getElementById('metrics');
            const successRate = total > 0 ? ((successful / total) * 100).toFixed(1) : 0;
            
            metrics.innerHTML = `
                <div class="metric">
                    <div class="metric-value">${total}</div>
                    <div class="metric-label">Total URLs</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${processed}</div>
                    <div class="metric-label">Processed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${successful}</div>
                    <div class="metric-label">Successful</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${successRate}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            `;
            
            document.getElementById('results').style.display = 'block';
        }

        async function processUrls() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                showStatus('Please select a file first.', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            formData.append('url_column', document.getElementById('urlColumn').value);
            formData.append('delay', document.getElementById('delay').value);
            formData.append('retries', document.getElementById('retries').value);

            const processBtn = document.getElementById('processBtn');
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';

            showStatus('Starting URL processing...', 'info');

            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                
                if (result.error) {
                    showStatus(`Error: ${result.error}`, 'error');
                    return;
                }

                processedData = result.data;
                updateMetrics(result.processed, result.successful, result.failed, result.total);
                updateProgress(100);
                showStatus('Processing complete!', 'success');
                document.getElementById('downloadBtn').style.display = 'inline-block';

            } catch (error) {
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
                const response = await fetch('/api/download', {
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
                    showStatus('Error downloading file.', 'error');
                }
            } catch (error) {
                showStatus(`Download error: ${error.message}`, 'error');
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process_urls():
    try:
        # Get file and parameters
        file = request.files['file']
        url_column = request.form.get('url_column', 'url')
        delay = float(request.form.get('delay', 1.0))
        max_retries = int(request.form.get('retries', 2))
        
        # Load the spreadsheet
        df = spreadsheet_processor.load_file(file)
        
        # Validate URL column exists
        if url_column not in df.columns:
            return jsonify({'error': f'Column "{url_column}" not found in spreadsheet'}), 400
        
        # Initialize result columns
        df['resolved_url'] = ''
        df['redirect_chain'] = ''
        df['wayback_url'] = ''
        df['status'] = ''
        df['error_message'] = ''
        
        # Filter rows with non-empty URLs
        urls_to_process = df[df[url_column].notna() & (df[url_column] != '')]
        total_urls = len(urls_to_process)
        
        if total_urls == 0:
            return jsonify({'error': 'No URLs found to process'}), 400
        
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for idx, row in urls_to_process.iterrows():
            original_url = row[url_column]
            
            try:
                # Resolve URL with retries
                resolved_url, redirect_chain = resolve_with_retries(original_url, max_retries)
                
                if resolved_url:
                    # Archive in Wayback Machine
                    wayback_url = archive_with_retries(resolved_url, max_retries)
                    
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
            
            # Rate limiting (reduced for serverless)
            if processed_count < total_urls and delay > 0:
                time.sleep(min(delay, 0.5))  # Cap delay for serverless
        
        return jsonify({
            'data': df.to_dict('records'),
            'processed': processed_count,
            'successful': success_count,
            'failed': error_count,
            'total': total_urls
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
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
        return jsonify({'error': str(e)}), 500

def resolve_with_retries(url, max_retries):
    """Resolve URL with retry mechanism"""
    for attempt in range(max_retries + 1):
        try:
            return url_resolver.resolve_url(url)
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(0.5)  # Shorter delay for serverless
    return None, []

def archive_with_retries(url, max_retries):
    """Archive URL with retry mechanism"""
    for attempt in range(max_retries + 1):
        try:
            return wayback_archiver.archive_url(url)
        except Exception as e:
            if attempt == max_retries:
                return None
            time.sleep(0.5)  # Shorter delay for serverless
    return None

# Vercel requires the app to be exported as 'app'
# This is the main WSGI application that Vercel will use
if __name__ == '__main__':
    app.run(debug=True)
