import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict

urls_to_check = [
    'https://adenenergies.com',
    'https://adenenergies.com/about',
    'https://adenenergies.com/contact',
    'https://adenenergies.com/media',
    'https://adenenergies.com/solutions',
    'https://adenenergies.com/zh',
    'https://adenenergies.com/zh/about',
    'https://adenenergies.com/zh/contact',
    'https://adenenergies.com/zh/media',
    'https://adenenergies.com/zh/solutions',
    'https://adengroup.com',
    'https://adengroup.com/about-us',
    'https://adengroup.com/careers',
    'https://adengroup.com/contact',
    'https://adengroup.com/media',
    'https://adengroup.com/cn',
    'https://adengroup.com/cn/about-us',
    'https://adengroup.com/cn/careers',
    'https://adengroup.com/cn/contact',
    'https://adengroup.com/cn/media',
    'https://nx-park.com'
]

async def check_images_on_page(page, url) -> List[Dict]:
    try:
        await page.goto(url, wait_until='networkidle', timeout=60000)  # Increased timeout to 60 seconds
        
        # Execute JavaScript to check for broken images
        broken_images = await page.evaluate('''
            () => {
                const images = document.getElementsByTagName('img');
                const broken = [];
                
                for (let img of images) {
                    if (!img.complete || !img.naturalWidth || !img.naturalHeight) {
                        broken.push({
                            name: img.src.split('/').pop(),
                            url: img.src
                        });
                    }
                }
                return broken;
            }
        ''')
        
        return broken_images
    except Exception as e:
        print(f"Error during page check: {str(e)}")
        raise

async def run_test(browser_type, context):
    results = {}
    
    for url in urls_to_check:
        print(f"Checking {url} with {browser_type}")
        page = await context.new_page()
        
        try:
            missing_images = await check_images_on_page(page, url)
            
            results[url] = {
                'status': 'OK' if not missing_images else 'Missing Images',
                'missing_images': missing_images
            }

            if missing_images:
                print(f"Missing images on {url}:")
                for img in missing_images:
                    print(f"- {img['name']} ({img['url']})")
            else:
                print(f"No missing images found on {url}")
            print('---')
            
        except Exception as e:
            print(f"Error checking {url}: {str(e)}")
            results[url] = {
                'status': 'Error',
                'missing_images': [],
                'error': str(e)
            }
        finally:
            await page.close()
    
    return results

async def main():
    async with async_playwright() as p:
        results = {}
        
        # Context options
        context_options = {
            'ignore_https_errors': True,
            'viewport': {'width': 1920, 'height': 1080}
        }

        # Test with Chromium
        browser = await p.chromium.launch()
        context = await browser.new_context(**context_options)
        results['chrome'] = await run_test('chrome', context)
        await browser.close()
        
        # Test with Firefox
        browser = await p.firefox.launch()
        context = await browser.new_context(**context_options)
        results['firefox'] = await run_test('firefox', context)
        await browser.close()
        
        # Test with WebKit (Safari)
        browser = await p.webkit.launch()
        context = await browser.new_context(**context_options)
        results['safari'] = await run_test('safari', context)
        await browser.close()
        
        combined_results = {
            'timestamp': datetime.now().isoformat(),
            **results
        }

        with open('results.json', 'w') as f:
            json.dump(combined_results, f, indent=2)

if __name__ == '__main__':
    asyncio.run(main())