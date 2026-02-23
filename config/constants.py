# Global constants for the AI Tool Discovery Agent

LLM_INPUT_TRUNCATION_LIMIT = 15_000  # Max HTML chars sent to LLM

AGGREGATOR_DOMAINS = frozenset([
    # Social media & video
    "youtube.com", "youtu.be", "reddit.com", "linkedin.com", "facebook.com",
    "twitter.com", "x.com", "tiktok.com", "instagram.com", "pinterest.com",
    "discord.com", "slack.com", "telegram.org",
    # News & media
    "msn.com", "yahoo.com", "cnn.com", "bbc.com", "reuters.com", "bloomberg.com",
    "forbes.com", "techcrunch.com", "venturebeat.com", "theverge.com", "wired.com",
    "cnbc.com", "marketwatch.com",
    # AI tool aggregators
    "forum.freecodecamp.org", "futuretools.io", "aitools.fyi", "toolify.ai", "toolsai.io",
    # Review & comparison sites
    "g2.com", "capterra.com", "getapp.com", "alternativeto.net", "slant.co", "trustpilot.com",
    # Freelance & job boards
    "fiverr.com", "upwork.com", "freelancer.com", "indeed.com", "glassdoor.com", "monster.com",
    # E-commerce
    "amazon.com", "aliexpress.com", "ebay.com", "apple.com", "itunes.apple.com",
    # Government & education
    "gov.uk", "gov.in", "gov.au", "gov.ca", "gov.us", "gov.sg", "edu", "ac.uk", "ac.in",
    # Search engines
    "google.com", "bing.com", "duckduckgo.com", "serper.dev", "serpapi.com",
    # Crowdfunding
    "patreon.com", "kickstarter.com", "indiegogo.com", "gofundme.com",
    # Petitions
    "change.org", "avaaz.org",
    # Events
    "eventbrite.com", "meetup.com", "eventful.com", "ticketmaster.com",
    # Audio streaming
    "soundcloud.com", "spotify.com",
    # Archives & reference
    "archive.org", "waybackmachine.org", "wikipedia.org", "wikidata.org", "wikimedia.org",
    # Q&A & developer platforms
    "quora.com", "stackexchange.com", "stackoverflow.com",
    "github.com", "gitlab.com", "bitbucket.org",
    # Productivity platforms
    "notion.so", "airtable.com", "asana.com", "trello.com",
    # Email marketing
    "mailchi.mp", "mailchimp.com", "sendgrid.com", "constantcontact.com",
    # Design platforms
    "dribbble.com", "behance.net",
    # Classifieds
    "craigslist.org",
    # Blogging & forums
    "medium.com", "substack.com", "news.ycombinator.com", "hackernews.com", "hacker-news.com",
])

BATCH_SIZE = 4
LLM_CONCURRENCY_LIMIT = 2

BASE_QUERIES = [
    '"launched new AI tool" OR "released new AI tool" OR "announced new AI tool" OR "introducing new AI tool" OR "AI tool just launched" OR "new AI tool released" OR "AI tool now available" OR "new AI tool available" OR "AI tool beta launch" OR "AI tool preview launch" OR "AI tool demo launch"',
    '"AI app" OR "AI platform" OR "AI product" OR "AI startup" OR "AI SaaS" OR "AI-powered"',
    '"AI tool update" OR "AI tool integration" OR "AI tool feature" OR "AI tool partnership" OR "AI tool API" OR "AI tool SaaS" OR "AI tool for" OR "AI-powered tool"',
    '"AI tool directory" OR "AI marketplace" OR "AI website"',
    '"new from" OR "just released" OR "now available" OR "new AI software launch" OR "new AI app launch" OR "AI tool free launch" OR "AI tool open source launch"',
    'site:.com OR site:.io OR site:.ai OR site:.co OR site:.app OR site:.dev OR site:.tech OR site:.org',
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Pragma": "no-cache",
    "Referer": "https://www.google.com/",
}

NON_RETRYABLE_STATUS_CODES = frozenset({403, 404})
