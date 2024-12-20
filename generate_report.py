import json
from datetime import datetime, timedelta

def generate_html(results):
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Image Check Status Report</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
        <style>
            body {{
                font-family: 'Courier New', Courier, monospace;
                background-color: #0C0C0C;
                color: #CCCCCC;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}
            h1, h2 {{
                color: #00FF00;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid #444;
                padding: 10px;
                text-align: left;
            }}
            th {{
                background-color: #1E1E1E;
            }}
            .ok {{ color: #00FF00; }}
            .error {{ color: #FF0000; }}
            .details {{
                background-color: #1E1E1E;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }}
            .status-icon {{
                margin-right: 8px;
            }}
            .browser-icon {{
                margin-right: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Image Check Status Report</h1>
            <p>Report generated on: {timestamp}</p>
            <h2>Summary</h2>
            <table>
                <tr>
                    <th>URL</th>
                    <th>Chrome Status</th>
                    <th>Firefox Status</th>
                    <th>WebKit Status</th>
                </tr>
                {table_rows}
            </table>
            <h2>Detailed Error Report</h2>
            <div class="details">
                {error_details}
            </div>
        </div>
    </body>
    </html>
    """

    rows = ""
    error_details = ""
    for url, data in results['chrome'].items():
        chrome_status = data['status']
        firefox_status = results['firefox'][url]['status']
        webkit_status = results['safari'][url]['status']
        
        def get_status_html(status, browser):
            icon_class = "fa-check ok" if status == 'OK' else "fa-xmark error"
            browser_icons = {
                'chrome': '<i class="fab fa-chrome browser-icon"></i>',
                'firefox': '<i class="fab fa-firefox browser-icon"></i>',
                'webkit': '<i class="fab fa-safari browser-icon"></i>'
            }
            return f"""
                <td class='{status.lower().replace(' ', '-')}'>
                    {browser_icons[browser]}
                    <i class="fa-solid {icon_class} status-icon"></i>
                    {status}
                </td>
            """
        
        rows += f"""<tr>
            <td>{url}</td>
            {get_status_html(chrome_status, 'chrome')}
            {get_status_html(firefox_status, 'firefox')}
            {get_status_html(webkit_status, 'webkit')}
        </tr>"""
        
        if chrome_status == 'Missing Images' or firefox_status == 'Missing Images' or webkit_status == 'Missing Images':
            error_details += f"<h3>{url}</h3>"
            
            if chrome_status == 'Missing Images':
                error_details += '<h4><i class="fab fa-chrome"></i> Chrome:</h4><ul>'
                for img in data['missing_images']:
                    error_details += f"<li>{img['name']} ({img['url']})</li>"
                error_details += "</ul>"
                
            if firefox_status == 'Missing Images':
                error_details += '<h4><i class="fab fa-firefox"></i> Firefox:</h4><ul>'
                for img in results['firefox'][url]['missing_images']:
                    error_details += f"<li>{img['name']} ({img['url']})</li>"
                error_details += "</ul>"
                
            if webkit_status == 'Missing Images':
                error_details += '<h4><i class="fab fa-safari"></i> WebKit (Safari):</h4><ul>'
                for img in results['safari'][url]['missing_images']:
                    error_details += f"<li>{img['name']} ({img['url']})</li>"
                error_details += "</ul>"

    # Convert timestamp to GMT+8
    timestamp = datetime.fromisoformat(results['timestamp'])
    gmt8_offset = timedelta(hours=8)
    timestamp_gmt8 = timestamp + gmt8_offset
    formatted_timestamp = timestamp_gmt8.strftime("%Y-%m-%d %H:%M:%S GMT+8")

    return html_template.format(timestamp=formatted_timestamp, table_rows=rows, error_details=error_details)

try:
    # Read the results
    with open('results.json', 'r') as f:
        results = json.load(f)

    # Generate the HTML report
    html_report = generate_html(results)

    # Write the HTML report
    with open('public/index.html', 'w') as f:
        f.write(html_report)

    print("HTML report generated successfully.")
except Exception as e:
    print(f"An error occurred: {str(e)}")
    raise