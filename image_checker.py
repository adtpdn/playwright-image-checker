import json
from datetime import datetime
from playwright.sync_api import sync_playwright
import logging
import requests
from urllib.parse import urljoin

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

urls_to_check = [
    'https://www.adengroup.com',
    'https://www.adenenergies.com',
    'https://www.nx-park.com',
    'https://the-internet.herokuapp.com/broken_images'
]

def verify_image_url(url, base_url):
    """Verify if image URL is actually accessible"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error verifying image URL {url}: {e}")
        return False

def check_images_on_page(page, url):
    try:
        logger.debug(f"Checking {url}")
        
        # Navigate with longer timeout and wait for network idle
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(5000)  # Wait for 5 seconds after load

        # Execute multiple scroll actions to trigger lazy loading
        for _ in range(3):
            page.evaluate("""() => {
                window.scrollTo(0, window.scrollY + window.innerHeight);
                return new Promise(resolve => setTimeout(resolve, 1000));
            }""")
            page.wait_for_timeout(1000)

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")

        missing_images = []
        retry_count = 3

        for attempt in range(retry_count):
            temp_missing = []
            
            # Check both regular and data-src images
            images = page.query_selector_all('img[src], img[data-src], img[data-lazy-src]')
            
            for img in images:
                try:
                    # Get all possible image source attributes
                    src = (img.get_attribute('src') or 
                          img.get_attribute('data-src') or 
                          img.get_attribute('data-lazy-src'))
                    
                    if not src:
                        continue

                    # Skip base64 images and SVGs
                    if src.startswith('data:') or src.endswith('.svg'):
                        continue

                    # Check if image is loaded in browser
                    is_loaded = page.evaluate("""(img) => {
                        return new Promise((resolve) => {
                            if (img.complete) {
                                resolve(img.naturalWidth > 0);
                            } else {
                                img.addEventListener('load', () => resolve(true));
                                img.addEventListener('error', () => resolve(false));
                                // Force reload the image
                                const currentSrc = img.src;
                                img.src = '';
                                img.src = currentSrc;
                            }
                        });
                    }""", img)

                    # Verify image URL directly if browser reports it as unloaded
                    if not is_loaded:
                        if verify_image_url(src, url):
                            continue  # Image is actually accessible
                        
                        alt = img.get_attribute('alt') or 'No alt text'
                        temp_missing.append({
                            'url': src,
                            'name': alt,
                            'dimensions': {
                                'width': img.get_attribute('width'),
                                'height': img.get_attribute('height')
                            }
                        })

                except Exception as e:
                    logger.error(f"Error checking individual image: {e}")
                    continue

            if not temp_missing:
                break  # No missing images found, exit retry loop
                
            if attempt < retry_count - 1:
                logger.debug(f"Retry {attempt + 1}: Waiting before next attempt")
                page.wait_for_timeout(2000)
                # Reload the page for next attempt
                page.reload(wait_until='networkidle')
            
            missing_images = temp_missing

        return {
            'status': 'OK' if not missing_images else 'Missing Images',
            'missing_images': missing_images,
            'total_images': len(images),
            'missing_count': len(missing_images)
        }

    except Exception as e:
        logger.error(f"Error checking page: {e}")
        return {
            'status': f'Error: {str(e)}',
            'missing_images': [],
            'total_images': 0,
            'missing_count': 0
        }

def run_test(browser_type, context):
    results = {}
    page = context.new_page()
    
    # Set extra headers
    page.set_extra_http_headers({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    })
    
    try:
        for url in urls_to_check:
            logger.info(f"Checking {url} with {browser_type}")
            results[url] = check_images_on_page(page, url)
    finally:
        page.close()
    
    return results

def main():
    with sync_playwright() as p:
        combined_results = {
            'timestamp': datetime.now().isoformat(),
            'chrome': {},
            'firefox': {},
            'safari': {}
        }

        browser_configs = {
            'chrome': (p.chromium, 'chrome'),
            'firefox': (p.firefox, 'firefox'),
            'safari': (p.webkit, 'safari')
        }

        for browser_name, (browser_type, result_key) in browser_configs.items():
            try:
                # Launch browser with only necessary arguments
                browser = browser_type.launch(headless=True)
                
                # Create context with all needed options
                context = browser.new_context(
                    ignore_https_errors=True,
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )

                combined_results[result_key] = run_test(browser_name, context)
            except Exception as e:
                logger.error(f"Error with {browser_name}: {e}")
                combined_results[result_key] = {
                    "error": str(e)
                }
            finally:
                if 'browser' in locals():
                    browser.close()

        # Save results
        with open('results.json', 'w') as f:
            json.dump(combined_results, f, indent=2)

if __name__ == '__main__':
    main()