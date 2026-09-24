# Public LinkedIn People-Sourcing

Use this when the user asks for candidate sourcing, recruiter-style shortlists, or public-profile prospecting from LinkedIn and adjacent web traces.

## Goal

Produce a *verifiable* shortlist of people who plausibly match a role, using public evidence only.

## Recommended workflow

1. **Treat this as public-web research, not direct LinkedIn scraping.**
   - Start with search-engine discovery and public web traces.
   - Use browser/web-capable tools or subagents early when the shell path looks likely to hit authwalls, bot checks, or CAPTCHA.

2. **Use LinkedIn URLs as candidate anchors, not proof by themselves.**
   - A search snippet or SERP title can suggest a lead.
   - Do not claim a candidate is a match until you have corroborating evidence from accessible public text.

3. **Collect evidence against the role rubric.**
   For each candidate, look for public signals of:
   - Python
   - ML/DL fundamentals
   - PyTorch or TensorFlow
   - Git/GitHub
   - Linux
   - REST APIs
   - SQL/databases
   - Bonus stack: Hugging Face, LangChain/LangGraph, OpenAI APIs, Ollama, vLLM, Docker, Kubernetes, vector DBs, RAG, CUDA, LLM eval

4. **Write confidence explicitly.**
   Use labels such as:
   - **High:** multiple required skills directly evidenced
   - **Medium:** some required skills directly evidenced, others inferred from closely related work
   - **Low:** mostly title/snippet/location match, little skills evidence

5. **Separate hard evidence from inference.**
   Good fields in the output table:
   - Name
   - LinkedIn URL
   - Location evidence
   - Required-skill evidence
   - Bonus-skill evidence
   - Confidence
   - Caveat / what remains unverified

## Output rules

- Be explicit when a result is a **lead**, not a fully verified match.
- If LinkedIn or the search engine blocks access, say so plainly and return the strongest *verifiable* shortlist you can.
- Never fabricate candidate details from a guessed profile slug or title alone.
- If the user asked for an exact count (for example, 20), do not silently pad with weak or invented entries; instead report the verified count and the blocker.

## Practical heuristics

- Search multiple ways: role keywords, tool keywords, and location keywords.
- Favor candidates with public GitHub, portfolio, Kaggle, Hugging Face, or conference/project traces that reinforce the LinkedIn lead.
- For intern roles, students and fresh grads with clear project stacks can outrank senior ML titles lacking concrete skill evidence.
- When blocked in one channel, switch channels early instead of repeatedly hammering the same search endpoint.

## Pitfalls

- **SERP-snippet hallucination:** treating a search snippet as if you read the full profile.
- **Location drift:** finding Nepal talent generally when the request was Kathmandu-specific.
- **Count-padding:** forcing the requested number despite weak evidence.
- **Terminal-only persistence:** spending too long retrying shell fetches after the pattern clearly points to anti-bot gating.

## Suggested phrasing when blocked

> I hit public anti-bot/authwall limits on direct LinkedIn retrieval, so I’m returning only candidates I could verify from accessible public evidence. I can continue with browser-assisted sourcing or widen the search if you want a fuller list.
