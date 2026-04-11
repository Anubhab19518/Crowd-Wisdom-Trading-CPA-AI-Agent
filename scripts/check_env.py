import os
print('USE_LOCAL_SCRAPER=', os.environ.get('USE_LOCAL_SCRAPER'))
print('APIFY_TOKEN present=', bool(os.environ.get('APIFY_TOKEN')))
print('APIFY_TOKEN preview:', ('SET' if os.environ.get('APIFY_TOKEN') else 'NOTSET'))
