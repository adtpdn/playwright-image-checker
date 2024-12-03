import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict

urls_to_check = [
    'https://adengroup.com',
    'https://adenenergies.com',
    'https://nx-park.com'
    # 'https://the-internet.herokuapp.com/broken_images'
]

async def check_images_on_page(page, url) -> List[Dict]:
    await page.goto(url, wait_until='networkidle')
    
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
        
        # Test with Chromium
        browser = await p.chromium.launch()
        context = await browser.new_context()
        results['chrome'] = await run_test('chrome', context)
        await browser.close()
        
        # Test with Firefox
        browser = await p.firefox.launch()
        context = await browser.new_context()
        results['firefox'] = await run_test('firefox', context)
        await browser.close()
        
        # Test with WebKit (Safari)
        browser = await p.webkit.launch()
        context = await browser.new_context()
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