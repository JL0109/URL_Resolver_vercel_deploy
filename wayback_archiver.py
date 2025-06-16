import requests
import urllib.parse
import time
import json
from typing import Optional
from datetime import datetime

class WaybackArchiver:
    """Handles archiving URLs in the Wayback Machine"""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize Wayback Machine archiver
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        
        # Wayback Machine API endpoints
        self.save_api_url = "https://web.archive.org/save/"
        self.availability_api_url = "https://archive.org/wayback/available"
        
        # Set user agent
        self.session.headers.update({
            'User-Agent': 'SMS-URL-Analyzer/1.0 (Educational Research Tool)'
        })
    
    def archive_url(self, url: str) -> Optional[str]:
        """
        Archive a URL in the Wayback Machine
        
        Args:
            url: URL to archive
            
        Returns:
            Wayback Machine URL of the archived page, or None if archiving failed
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL provided")
        
        # Clean and validate URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            # First, check if URL is already archived recently (within last 24 hours)
            existing_archive = self.check_recent_archive(url)
            if existing_archive:
                return existing_archive
            
            # Archive the URL
            archive_url = self.save_api_url + urllib.parse.quote(url, safe=':/?#[]@!$&\'()*+,;=')
            
            response = self.session.get(
                archive_url,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # The response URL should be the archived version
                if 'web.archive.org/web/' in response.url:
                    return response.url
                else:
                    # Sometimes the API returns success but we need to construct the URL
                    # Try to get the timestamp from the response or use current time
                    timestamp = self.extract_timestamp_from_response(response)
                    if not timestamp:
                        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                    
                    return f"https://web.archive.org/web/{timestamp}/{url}"
                    
            elif response.status_code == 429:
                # Rate limited
                raise Exception("Rate limited by Wayback Machine. Please slow down requests.")
                
            elif response.status_code >= 400:
                # Check if it's a client error that we can handle
                if response.status_code == 403:
                    raise Exception("Access forbidden - URL may be blocked from archiving")
                elif response.status_code == 404:
                    raise Exception("Wayback Machine service not found")
                else:
                    raise Exception(f"Archiving failed with status code: {response.status_code}")
            
            return None
            
        except requests.exceptions.Timeout:
            raise Exception(f"Archiving timeout after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach Wayback Machine")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            if "Rate limited" in str(e) or "Access forbidden" in str(e):
                raise e
            else:
                raise Exception(f"Unexpected error during archiving: {str(e)}")
    
    def check_recent_archive(self, url: str, hours: int = 24) -> Optional[str]:
        """
        Check if URL has been archived recently
        
        Args:
            url: URL to check
            hours: How many hours back to check for existing archives
            
        Returns:
            URL of recent archive if found, None otherwise
        """
        try:
            # Use availability API to check for recent archives
            params = {
                'url': url,
                'timestamp': datetime.utcnow().strftime('%Y%m%d%H%M%S')
            }
            
            response = self.session.get(
                self.availability_api_url,
                params=params,
                timeout=10  # Shorter timeout for availability check
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if there's an archived snapshot
                if (data.get('archived_snapshots') and 
                    data['archived_snapshots'].get('closest') and
                    data['archived_snapshots']['closest'].get('available')):
                    
                    snapshot = data['archived_snapshots']['closest']
                    snapshot_url = snapshot.get('url')
                    snapshot_timestamp = snapshot.get('timestamp')
                    
                    if snapshot_url and snapshot_timestamp:
                        # Check if the snapshot is recent enough
                        try:
                            snapshot_time = datetime.strptime(snapshot_timestamp, '%Y%m%d%H%M%S')
                            time_diff = datetime.utcnow() - snapshot_time
                            
                            if time_diff.total_seconds() < (hours * 3600):
                                return snapshot_url
                        except ValueError:
                            # If we can't parse the timestamp, skip the recent check
                            pass
            
            return None
            
        except Exception:
            # If availability check fails, continue with normal archiving
            return None
    
    def extract_timestamp_from_response(self, response) -> Optional[str]:
        """
        Try to extract timestamp from Wayback Machine response
        
        Args:
            response: HTTP response from Wayback Machine
            
        Returns:
            Timestamp string or None
        """
        try:
            # Look for timestamp in response headers
            if 'x-archive-wayback-runtime-info' in response.headers:
                runtime_info = response.headers['x-archive-wayback-runtime-info']
                # Parse runtime info for timestamp
                # This is a best-effort attempt
                pass
            
            # Look for timestamp in response URL
            if 'web.archive.org/web/' in response.url:
                parts = response.url.split('web.archive.org/web/')
                if len(parts) > 1:
                    timestamp_part = parts[1].split('/')[0]
                    if timestamp_part.isdigit() and len(timestamp_part) >= 8:
                        return timestamp_part
            
            # If we can't find a timestamp, return None
            return None
            
        except Exception:
            return None
    
    def get_archive_info(self, url: str) -> dict:
        """
        Get information about archived versions of a URL
        
        Args:
            url: URL to check
            
        Returns:
            Dictionary with archive information
        """
        try:
            params = {
                'url': url,
                'timestamp': datetime.utcnow().strftime('%Y%m%d%H%M%S')
            }
            
            response = self.session.get(
                self.availability_api_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'API request failed with status {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}
    
    def is_archivable(self, url: str) -> bool:
        """
        Check if a URL can potentially be archived
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears archivable, False otherwise
        """
        try:
            # Basic URL validation
            parsed = urllib.parse.urlparse(url)
            if not parsed.netloc or not parsed.scheme:
                return False
            
            # Check for common non-archivable patterns
            non_archivable_patterns = [
                'localhost',
                '127.0.0.1',
                '192.168.',
                '10.',
                'private',
                'internal'
            ]
            
            domain = parsed.netloc.lower()
            for pattern in non_archivable_patterns:
                if pattern in domain:
                    return False
            
            return True
            
        except Exception:
            return False