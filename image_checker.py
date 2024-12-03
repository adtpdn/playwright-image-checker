import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict
import aiohttp

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

async def verify_image_url(session, img_url) -> bool:
    try:
        async with session.head(img_url) as response:
            return response.status == 200
    except:
        return False

async def check_images_on_page(page, url) -> List[Dict]:
    try:
        await page.goto(url, wait_until='networkidle', timeout=60000)
        
        # Scroll through the page to trigger lazy loading
        await page.evaluate('''
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 100;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        ''')
        
        # Wait a bit for lazy loaded images
        await page.wait_for_timeout(2000)
        
        # Get all images including those that might be lazy loaded
        broken_images = await page.evaluate('''
            () => {
                const images = Array.from(document.getElementsByTagName('img'));
                const broken = [];
                
                for (let img of images) {
                    // Check both src and data-src attributes
                    const imgSrc = img.src || img.dataset.src;
                    if (!imgSrc || !img.complete || !img.naturalWidth || !img.naturalHeight) {
                        broken.push({
                            name: imgSrc ? imgSrc.split('/').pop() : 'unknown',
                            url: imgSrc || 'no-src',
                            reason: !imgSrc ? 'no-src' : 
                                    !img.complete ? 'incomplete' : 
                                    'zero-dimension'
                        });
                    }
                }
                return broken;
            }
        ''')
        
        # Recheck potentially broken images with direct HTTP request
        async with aiohttp.ClientSession() as session:
            verified_broken = []
            for img in broken_images:
                if img['url'] != 'no-src':
                    is_accessible = await verify_image_url(session, img['url'])
                    if not is_accessible:
                        verified_broken.append(img)
                else:
                    verified_broken.append(img)
                    
        return verified_broken
        
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
                    print(f"- {img['name']} ({img['url']}) - Reason: {img['reason']}")
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