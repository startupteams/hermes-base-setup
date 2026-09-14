# YouTube timedtext JSON3 fallback after 429/bot blocks

## When this helps

Use this when:

- `youtube-transcript-api` reports IP/request blocking.
- Browser navigation hits Google/YouTube bot checks.
- Normal `yt-dlp --write-auto-subs` fails, but `yt-dlp` can still retrieve metadata through a non-web player client.
- The user needs a grounded extraction and you must avoid hallucinating video-specific details.

## Proven workflow

```bash
export PATH="$HOME/.local/bin:/home/miam/.hermes/profiles/entrepreneur/home/.local/bin:$PATH"
yt-dlp \
  --extractor-args "youtube:player_client=android" \
  --skip-download \
  --dump-json \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  > /tmp/video_meta.json 2>/tmp/video_meta.err
```

Even with warnings like `HTTP Error 429`, this may write metadata containing `automatic_captions` entries. Extract an English `json3` timedtext URL and download it directly:

```python
import json, re, urllib.request

d = json.load(open('/tmp/video_meta.json'))
caps = d.get('automatic_captions') or {}
urls = []

if 'en' in caps:
    urls = [x['url'] for x in caps['en'] if x.get('ext') == 'json3']
else:
    for arr in caps.values():
        for x in arr:
            if x.get('ext') == 'json3' and 'lang=en' in x.get('url', ''):
                urls.append(re.sub(r'&tlang=[^&]+', '', x['url']))
                break
        if urls:
            break

req = urllib.request.Request(urls[0], headers={'User-Agent': 'Mozilla/5.0'})
data = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
open('/tmp/captions.json3', 'w').write(data)
```

Convert JSON3 events into timestamped transcript text:

```python
import json, re
j = json.load(open('/tmp/captions.json3'))
with open('/tmp/video_transcript_timestamps.txt', 'w') as f:
    for ev in j.get('events', []):
        if 'segs' not in ev:
            continue
        text = ''.join(seg.get('utf8', '') for seg in ev['segs']).replace('\n', ' ').strip()
        text = re.sub(r'\s+', ' ', text)
        if not text:
            continue
        s = ev.get('tStartMs', 0) // 1000
        f.write(f'[{s//60:02d}:{s%60:02d}] {text}\n')
```

## Fabric logging pattern

If Fabric's model provider is unavailable, still log the command and output:

```bash
HOME=/home/miam fabric -p extract_wisdom < /tmp/video_transcript_timestamps.txt \
  > fabric_extract_wisdom_attempt.txt 2>&1 || true
HOME=/home/miam fabric -p extract_wisdom --dry-run < /tmp/video_transcript_timestamps.txt \
  > fabric_extract_wisdom_dry_run.txt 2>&1 || true
```

A dry run proves which Fabric pattern/prompt would have been used, but it is not a model-generated extraction. Label it accordingly.

## Pitfalls

- Do not commit browser cookies or token files.
- Do not treat auto-caption text as perfect; note likely ASR errors in model names and technical terms.
- Do not claim Fabric extraction succeeded if the model provider returned an auth error.
- `automatic_captions` may contain translated caption URLs. Prefer direct `en` entries; otherwise strip `tlang=...` from a translated URL where `lang=en` is present.
