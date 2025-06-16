import requests
import urllib.parse
from urllib.parse import urlparse
import time
from typing import Tuple, List, Optional

class URLResolver:
    """Handles resolution of shortened URLs to their final destinations"""
    
    def __init__(self, timeout: int = 10, max_redirects: int = 20):
        """
        Initialize URL resolver
        
        Args:
            timeout: Request timeout in seconds
            max_redirects: Maximum number of redirects to follow
        """
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.session = requests.Session()
        
        # Set user agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def resolve_url(self, url: str) -> Tuple[Optional[str], List[str]]:
        """
        Resolve a shortened URL to its final destination
        
        Args:
            url: The shortened URL to resolve
            
        Returns:
            Tuple of (final_url, redirect_chain)
            final_url: The final destination URL or None if resolution failed
            redirect_chain: List of URLs in the redirect chain
        """
        if not url or not isinstance(url, str):
            raise ValueError("Invalid URL provided")
        
        # Normalize URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validate URL format
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise ValueError("Invalid URL format")
        
        redirect_chain = [url]
        current_url = url
        
        try:
            for i in range(self.max_redirects):
                # Make HEAD request first to check for redirects without downloading content
                try:
                    response = self.session.head(
                        current_url, 
                        allow_redirects=False, 
                        timeout=self.timeout,
                        verify=True
                    )
                except requests.exceptions.SSLError:
                    # Retry with SSL verification disabled for problematic sites
                    response = self.session.head(
                        current_url, 
                        allow_redirects=False, 
                        timeout=self.timeout,
                        verify=False
                    )
                
                # Check if this is a redirect
                if response.status_code in [301, 302, 303, 307, 308]:
                    next_url = response.headers.get('Location')
                    if not next_url:
                        break
                    
                    # Handle relative URLs
                    if next_url.startswith('/'):
                        parsed_current = urlparse(current_url)
                        next_url = f"{parsed_current.scheme}://{parsed_current.netloc}{next_url}"
                    elif not next_url.startswith(('http://', 'https://')):
                        # Handle relative URLs without leading slash
                        parsed_current = urlparse(current_url)
                        base_path = '/'.join(parsed_current.path.split('/')[:-1])
                        next_url = f"{parsed_current.scheme}://{parsed_current.netloc}{base_path}/{next_url}"
                    
                    if next_url in redirect_chain:
                        # Circular redirect detected
                        break
                    
                    redirect_chain.append(next_url)
                    current_url = next_url
                    
                elif response.status_code == 200:
                    # Final destination reached
                    break
                    
                elif response.status_code == 405:
                    # HEAD method not allowed, try GET
                    try:
                        response = self.session.get(
                            current_url, 
                            allow_redirects=False, 
                            timeout=self.timeout,
                            stream=True,  # Don't download full content
                            verify=True
                        )
                        response.close()  # Close connection immediately
                        
                        if response.status_code in [301, 302, 303, 307, 308]:
                            next_url = response.headers.get('Location')
                            if next_url and next_url not in redirect_chain:
                                # Handle relative URLs
                                if next_url.startswith('/'):
                                    parsed_current = urlparse(current_url)
                                    next_url = f"{parsed_current.scheme}://{parsed_current.netloc}{next_url}"
                                
                                redirect_chain.append(next_url)
                                current_url = next_url
                            else:
                                break
                        else:
                            break
                            
                    except requests.exceptions.SSLError:
                        # Retry with SSL verification disabled
                        response = self.session.get(
                            current_url, 
                            allow_redirects=False, 
                            timeout=self.timeout,
                            stream=True,
                            verify=False
                        )
                        response.close()
                        break
                        
                else:
                    # Other status codes - stop here
                    break
            
            return current_url, redirect_chain
            
        except requests.exceptions.Timeout:
            raise Exception(f"Request timeout after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach URL")
        except requests.exceptions.TooManyRedirects:
            raise Exception("Too many redirects")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error during URL resolution: {str(e)}")
    
    def is_shortened_url(self, url: str) -> bool:
        """
        Check if a URL appears to be from a known URL shortening service
        
        Args:
            url: URL to check
            
        Returns:
            True if URL appears to be shortened, False otherwise
        """
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Known URL shortening services
            shortener_domains = {
                'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'short.link',
                'ow.ly', 'buff.ly', 'adf.ly', 'short.link', 'x.co',
                'cutt.ly', 'rebrand.ly', 'clickmeter.com', 'smarturl.it',
                'linktr.ee', 'tiny.cc', 'is.gd', 'v.gd', 'tr.im',
                'url.ie', 'tinycc.com', 'tweez.me', 'su.pr', 'youtu.be',
                'amzn.to', 'ebay.to', 'fb.me', 'ln.is', 'mcaf.ee',
                'ift.tt', 'bit.do', 'short.cm', 'href.li', 'link.ly'
            }
            
            return domain in shortener_domains
            
        except Exception:
            return False
    
    def get_domain_info(self, url: str) -> dict:
        """
        Extract domain information from a URL
        
        Args:
            url: URL to analyze
            
        Returns:
            Dictionary with domain information
        """
        try:
            parsed = urlparse(url)
            return {
                'domain': parsed.netloc,
                'scheme': parsed.scheme,
                'path': parsed.path,
                'query': parsed.query,
                'fragment': parsed.fragment
            }
        except Exception:
            return {}