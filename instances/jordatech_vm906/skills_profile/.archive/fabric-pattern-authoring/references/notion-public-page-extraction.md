# Public Notion Page Extraction for Fabric Pattern Authoring

Use this when a public Notion page renders in the browser but collapsed toggles or nested content do not appear in `document.body.innerText`.

## Why

Notion pages often show only top-level headings/toggles in accessibility snapshots. The useful examples may live in child blocks that must be loaded separately.

## Recipe

1. Convert the 32-character Notion page ID to dashed UUID form:

```python
pid = '2d89464bdbf980ee99aaea3925f6d1bd'
dashed = '-'.join([pid[:8], pid[8:12], pid[12:16], pid[16:20], pid[20:]])
```

2. Call Notion's public `loadPageChunk` endpoint:

```python
import requests, json

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'notion-client-version': '23.13.20260506.0115',
    'x-notion-active-user-header': 'anonymous',
}

payload = {
    'pageId': dashed,
    'limit': 200,
    'cursor': {'stack': []},
    'chunkNumber': 0,
    'verticalColumns': False,
}

r = requests.post('https://www.notion.so/api/v3/loadPageChunk', headers=headers, json=payload, timeout=20)
r.raise_for_status()
blocks = r.json()['recordMap']['block']
```

3. Normalize block values. Some responses wrap the block as `value.value`; others expose `value` directly:

```python
def normalize(block_record):
    value = block_record.get('value')
    if isinstance(value, dict) and 'value' in value:
        return value['value']
    return value
```

4. Recursively load child block IDs found in a block's `content` list. For collapsed toggles, the top-level page chunk may include the toggle block but not all child code/text blocks. Calling `loadPageChunk` with the child block ID as `pageId` can return those nested blocks.

   Notion pages may also use heading blocks such as `sub_sub_header` with `format.toggleable: True` rather than `toggle` blocks. Treat any block with a non-empty `content` list as a possible collapsed container, regardless of type, and load its child IDs individually if they are missing from the initial `recordMap`.

5. Respect Notion rate limits. Large prompt-library pages can trigger HTTP 429 when recursively loading every child too quickly. Add retry/backoff and, for pattern authoring, sample enough representative children per section instead of exhausting the whole source when a distilled pattern is the goal:

```python
for attempt in range(6):
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code == 429:
        time.sleep(2 + attempt * 3)
        continue
    r.raise_for_status()
    break
```

6. Convert Notion rich text properties to plain text:

```python
def rich_text(parts):
    if not parts:
        return ''
    out = []
    for item in parts:
        if isinstance(item, list) and item:
            out.append(item[0])
    return ''.join(out).replace('\xa0', ' ')
```

6. Map useful Notion block types to Markdown:

- `page` → `# Title`
- `toggle` → `## Title`
- `code` → fenced code block using `properties.title`
- `text` / `callout` → paragraph or bullet
- `numbered_list` → numbered list item
- `divider` → `---`

## Session Example

For the Veo and Nano Banana prompt-library pages, the browser snapshot exposed only top-level toggles. Direct `loadPageChunk` returned the page and toggle blocks, and recursively loading each toggle child returned code blocks containing prompt formulas and examples. Those were then generalized into Fabric patterns rather than copied verbatim as a full source mirror.

## Pitfalls

- Do not assume browser snapshots contain collapsed toggle bodies.
- Do not hard-code the Notion client version forever; if Notion returns errors, inspect the page HTML for the current `data-notion-version` and update the header.
- Do not commit a raw dump of the source page unless the task explicitly requires archival. Extract reusable structures and cite the source instead.
