# DeepAPI LinkedIn Sourcing Reference

Session-derived pattern for sourcing technical candidates from LinkedIn with DeepAPI.

## When to use

Use for requests like: “find LinkedIn candidates for [technical role] in [location]”, especially when the user explicitly asks to use DeepAPI.

## Endpoint

- `POST /v1/scrape/linkedin/people`
- Use the DeepAPI skill’s required headers:
  - `Authorization: Bearer $DEEPAPI_API_KEY` (never print/log key)
  - `X-DeepAPI-Skill-Version`
  - `Content-Type: application/json`
  - unique `Idempotency-Key` for every POST

## Recommended request sequence

1. Check environment has `DEEPAPI_API_BASE_URL` and `DEEPAPI_API_KEY`; source `~/.deepapi/env` if needed.
2. Fetch live capability schema if unsure: `GET /v1/capabilities?capability=scrape.linkedin.people`.
3. Run a dry run first if cost/credits are uncertain:

```json
{
  "dryRun": true,
  "waitForFinishSecs": 60,
  "query": "machine learning",
  "locations": ["Kathmandu"],
  "maxItems": 25,
  "includeDetails": true
}
```

4. Execute 3–6 fanout searches. Good variants for Kathmandu AI/ML intern roles:

```json
{"query":"machine learning","locations":["Kathmandu"],"maxItems":25,"waitForFinishSecs":60}
{"query":"AI engineer","locations":["Kathmandu"],"maxItems":25,"waitForFinishSecs":60}
{"query":"data science python","locations":["Kathmandu"],"maxItems":25,"waitForFinishSecs":60}
{"titles":["Machine Learning Engineer","AI Engineer","Data Scientist"],"locations":["Kathmandu, Nepal"],"maxItems":25,"waitForFinishSecs":60}
{"schools":["Kathmandu University","Tribhuvan University"],"query":"artificial intelligence machine learning Python","maxItems":25,"waitForFinishSecs":60}
```

5. Poll any `next` action where `method == "GET"` until no polling `next` remains. A response can say `succeeded` while output is still settling; do not stop early when `next` exists.
6. Deduplicate by `profileUrl`.
7. Score against the role rubric.

## Scoring notes for AI/ML internships

Positive signals:

- Student, intern, internship, apprentice, apprenticeship, graduate, entry-level, seeking/open-to, currently learning/building.
- Python, SQL, REST APIs/FastAPI/Django, PyTorch, TensorFlow/Keras, Scikit-learn.
- RAG, LangChain/LangGraph, LLM, OpenAI, vector DB, Docker/Kubernetes, MLOps.
- Concrete role/project evidence in LinkedIn `about` or `positions`.

Penalty / caveat signals:

- Founder, Head, Lead, Senior, Team Lead, PhD, 5+ years, lecturer-only profile — likely overqualified unless the user wants senior/referral candidates.
- Location not Kathmandu/Nepal — include only if the user accepts remote or diaspora candidates.

## Output pattern

Report:

- DeepAPI request IDs used.
- Number of unique profiles found.
- A compact table with candidate, location, LinkedIn URL, current/listed role, and why they fit.
- A “best first outreach” shortlist of 5–8 names.
- A screening ask that requests project/GitHub evidence and validates the highest-signal skills.

## Privacy and compliance

- Use public profile data only.
- Do not expose API keys.
- Do not send outreach/email without explicit user approval.
- Do not claim full qualification; say “public evidence suggests” and require screening verification.
