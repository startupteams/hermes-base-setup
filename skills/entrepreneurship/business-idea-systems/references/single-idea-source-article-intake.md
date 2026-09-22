# Single Idea + Source Article Intake

Use this reference when Jordan provides one rough business idea, domain/name, positioning phrase, monetization note, and one or more external articles to inform pricing or market assumptions.

## Pattern from AgentifyMe.com

Example input shape:

- Name/domain: `agentifyme.com`
- Category: AI-as-a-Service / managed AI agents
- Concept: set up and host personalized AI agents for companies for a fixed monthly fee
- External source: article about AI agent implementation and operating costs

## Workflow

1. Load `business-idea-systems` and the relevant GitHub workflow skill.
2. Inspect both repos and verify they are on `c01entrepreneur_bot`:
   - `/home/miam/jordatech/business_ideas`
   - `/home/miam/jordatech/business_idea_generator`
3. Fetch the supplied article and extract only durable signals:
   - title/date if available
   - pricing bands
   - cost drivers
   - operational risks
   - tools/integrations mentioned
   - quotes or claims that directly inform the idea
4. If Python `bs4` is unavailable, do not install dependencies for a one-off scrape. Use `requests` plus stdlib `html.parser` or simple text extraction instead.
5. Keep source evidence separate from validation. Phrase it as **source intelligence**, not proof that buyers will pay.
6. Create one idea Markdown file with a normalized slug and full brief:
   - frontmatter with `source_urls`
   - one-line summary
   - next actions
   - persona/pain/product/business model
   - first 10 clients with linked prospect and public contact path
   - pricing/COGS informed by the article
   - Mom Test questions
   - concierge or fake-door MVBP
   - skeptical investor review
   - data moat and proprietary advantage
   - human-in-the-loop approach
   - unit economics
   - FAQ
   - kill criteria
7. Update `business_ideas/ideas.json` and put the new idea first when it should appear as the latest idea.
8. Sync into `business_idea_generator/data/`:
   - copy `ideas.json`
   - copy the new Markdown file
   - copy any source-indexed Markdown files missing from the viewer snapshot
9. Verify:
   - JSON syntax for both indexes
   - first 10 clients count/contact links in source and viewer copy
   - `npm run build` in viewer repo
10. Commit and push both repos. Deploy the viewer if the user expects the public/private Vercel app to update.
11. Verify Vercel with `vercel inspect` and `curl -I` against the alias and new idea route. A `401` on the Basic Auth-protected alias is expected and should be reported as protected, not failed.

## Article extraction fallback snippet

```python
import re, requests
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        data = data.strip()
        if data:
            self.parts.append(data)

url = "https://example.com/article"
html = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
parser = TextExtractor()
parser.feed(html)
text = re.sub(r"\s+", " ", " ".join(parser.parts))
print(text[:5000])
```

## Quality bar

- Do not overstate the article as validation.
- Do not invent credentials for protected deployments.
- Do not run dependency-changing fixes such as `npm audit fix` unless the user approved dependency updates.
- Keep the final response concise: done, files/commits, deploy URL, validation status, and any unresolved audit/security note.
