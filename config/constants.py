# Global constants for the AI Tool Discovery Agent

LLM_INPUT_TRUNCATION_LIMIT = 15000  # Max HTML chars sent to LLM

AGGREGATOR_DOMAINS = [
    'youtube.com', 'youtu.be', 'reddit.com', 'linkedin.com', 'facebook.com', 'twitter.com', 'x.com',
    'tiktok.com', 'instagram.com', 'pinterest.com', 'discord.com', 'slack.com', 'telegram.org',
    'msn.com', 'yahoo.com', 'cnn.com', 'bbc.com', 'reuters.com', 'bloomberg.com', 'forbes.com',
    'techcrunch.com', 'venturebeat.com', 'theverge.com', 'wired.com', 'cnbc.com', 'marketwatch.com',
    'forum.freecodecamp.org', 'futuretools.io', 'aitools.fyi', 'toolify.ai', 'toolsai.io',
    'g2.com', 'capterra.com', 'getapp.com', 'alternativeto.net', 'slant.co', 'trustpilot.com',
    'fiverr.com', 'upwork.com', 'freelancer.com', 'indeed.com', 'glassdoor.com', 'monster.com',
    'amazon.com', 'aliexpress.com', 'ebay.com', 'apple.com', 'itunes.apple.com',
    'gov.uk', 'gov.in', 'gov.au', 'gov.ca', 'gov.us', 'gov.sg', 'edu', 'ac.uk', 'ac.in',
    'google.com', 'bing.com', 'duckduckgo.com', 'serper.dev', 'serpapi.com',
    'patreon.com', 'kickstarter.com', 'indiegogo.com', 'goFundme.com',
    'change.org', 'avaaz.org',
    'eventbrite.com', 'meetup.com', 'eventful.com', 'ticketmaster.com',
    'soundcloud.com', 'spotify.com',
    'archive.org', 'waybackmachine.org',
    'wikipedia.org', 'wikidata.org', 'wikimedia.org',
    'quora.com', 'stackexchange.com', 'stackoverflow.com',
    'github.com', 'gitlab.com', 'bitbucket.org',
    'notion.so', 'airtable.com', 'asana.com', 'trello.com',
    'mailchi.mp', 'mailchimp.com', 'sendgrid.com', 'constantcontact.com',
    'dribbble.com', 'behance.net',
    'craigslist.org',
    'medium.com', 'substack.com', 'news.ycombinator.com', 'hackernews.com', 'hacker-news.com',
]

BATCH_SIZE = 4  # Used for batching in pipeline_agent and search_agent
LLM_CONCURRENCY_LIMIT = 2  # Used for throttling LLM calls in pipeline_agent 

BASE_QUERIES = [
    # 1. AI tool launches and releases
    '"launched new AI tool" OR "released new AI tool" OR "announced new AI tool" OR "introducing new AI tool" OR "AI tool just launched" OR "new AI tool released" OR "AI tool now available" OR "new AI tool available" OR "AI tool beta launch" OR "AI tool preview launch" OR "AI tool demo launch"',
    # 2. AI app/platform/product/startup
    '"AI app" OR "AI platform" OR "AI product" OR "AI startup" OR "AI SaaS" OR "AI-powered"',
    # 3. AI tool features, updates, integrations
    '"AI tool update" OR "AI tool integration" OR "AI tool feature" OR "AI tool partnership" OR "AI tool API" OR "AI tool SaaS" OR "AI tool for" OR "AI-powered tool"',
    # 4. AI tool directories, marketplaces, websites
    '"AI tool directory" OR "AI marketplace" OR "AI website"',
    # 5. General new/just released/now available
    '"new from" OR "just released" OR "now available" OR "new AI software launch" OR "new AI app launch" OR "AI tool free launch" OR "AI tool open source launch"',
    # 6. Site filter
    'site:.com OR site:.io OR site:.ai OR site:.co OR site:.app OR site:.dev OR site:.tech OR site:.org',
] 

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'Pragma': 'no-cache',
    'Referer': 'https://www.google.com/',
} 

NON_RETRYABLE_STATUS_CODES = [403, 404] 