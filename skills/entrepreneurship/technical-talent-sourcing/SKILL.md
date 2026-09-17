---
name: technical-talent-sourcing
description: Source and rank technical candidates from public evidence for startup hiring roles, especially AI/ML and software engineering internships.
---

# Technical Talent Sourcing

Use this skill when the user asks to find candidates for a technical role, build a prospect list, scrape/search LinkedIn, rank candidates against a job description, or produce an outreach shortlist.

## Core workflow

1. **Restate the role as a skills rubric.** Extract must-haves, nice-to-haves, seniority, location, and role type. For AI/ML interns, prefer evidence of learning/building velocity over senior titles.
2. **Use compliant public sourcing first.** Do not automate logged-in LinkedIn scraping or bypass anti-bot controls. Use public search snippets, candidate-provided profile links, GitHub, portfolios, Kaggle, papers, blogs, and public university/community pages. If the user names a specific sourcing API/tool, use it when configured; otherwise proceed with accessible public sources and state the limitation briefly.
3. **Collect evidence, not just names.** Every candidate row should include public profile URL(s), location signal, skills inferred from artifacts, and 1–3 concrete artifacts to verify.
4. **Score against the JD.** Map evidence to categories such as programming language, DSA/OOP signal, ML/DL fundamentals, framework experience, Git/GitHub, Linux/devops, APIs, SQL/databases, and edge skills. If the JD is a public Google Drive PDF, use DeepAPI website/PDF scraping (Drive view URL plus `uc?export=download&id=...`) and summarize the actual JD before scoring.
5. **Prioritize outreach.** Provide a top shortlist with why they are worth contacting first and what to verify in screening.

## DeepAPI LinkedIn sourcing pattern

Use this when DeepAPI is configured and the user asks for LinkedIn candidate sourcing:

- Load the DeepAPI instructions first if available. Use the dedicated `POST /v1/scrape/linkedin/people` endpoint rather than open-web search or browser scraping.
- For paid DeepAPI endpoints, run a `dryRun: true` preview first when cost/credit impact is unclear. Do not exceed an explicit customer spend cap; stop and ask before spending more.
- Follow DeepAPI polling exactly: while a response returns a `next` action with `method: "GET"`, wait `next.afterSecs` and poll `next.path`, even if status already says `succeeded` with empty/settling output.
- Fan out several precise LinkedIn people searches instead of one broad search. For AI/ML intern searches, vary: free-text role keywords, current titles, school filters, and location variants (e.g. `Kathmandu`, `Kathmandu, Nepal`, target universities).
- Deduplicate by `profileUrl`, then score candidates using public profile text. Prefer intern/student/apprentice/entry-level signals and penalize clearly senior/lead/founder/head profiles unless the user wants senior hires.
- After downselecting, enrich shortlisted profiles with `POST /v1/scrape/linkedin/profile` using `includeEmail: true` only when the user asked for emails/contact info. This endpoint may canonicalize obfuscated people-search URLs into readable public slugs; update the report with canonical URLs.
- To find GitHubs, sites, and resumes, run multiple DeepAPI web searches per candidate using exact name + LinkedIn slug + target terms, then verify identity before recording a match. Accept a GitHub as verified when the GitHub profile links back to the candidate’s LinkedIn slug or the profile text/location strongly match. Do **not** count same-name portfolios/resumes if they point to a different LinkedIn/GitHub.
- Keep API keys out of output and logs. Report request IDs, status, result counts, and useful candidate evidence, not secrets or raw credential state.

## Public GitHub sourcing pattern

Use GitHub search when LinkedIn is inaccessible or insufficient, or to verify LinkedIn candidates with public project evidence:

- Search users by location and language/keywords, e.g. `location:Kathmandu language:Python machine learning`, `location:Nepal language:Python langchain`, `location:Kathmandu language:Jupyter Notebook deep learning`.
- Fetch profile metadata and recent repositories via authenticated `gh api` when available.
- Prefer candidates whose own bio/location claims align with the target geography and whose repositories show recent, relevant work.
- Treat GitHub emails as public contact data only when exposed by the user's profile; avoid inventing or enriching private contact data.

## Evidence-to-fit rubric for AI/ML intern roles

| JD requirement | Strong public evidence | Weaker but useful evidence |
|---|---|---|
| Python | Python repos, notebooks, FastAPI/Streamlit apps | Bio says Python |
| DSA/OOP | algorithm repos, clean package structure, tests/classes | general programming repos |
| ML/DL fundamentals | regression/classification/CNN/RNN/transformer projects with explanations | course notebooks |
| PyTorch/TensorFlow | repos explicitly using PyTorch, TensorFlow, Keras, Lightning | framework mentioned in bio |
| Git/GitHub | active repos, commits, READMEs, branches | GitHub account only |
| Linux/devops | Dockerfiles, GPU notebooks, CI, deployment docs | mentions Linux/devops |
| APIs | FastAPI/Flask/Django REST apps | frontend-only API consumption |
| SQL/DB | SQL, Postgres/MySQL/MongoDB, database-backed apps | data CSV notebooks |
| Edge skills | RAG, LangChain/LangGraph, Hugging Face, vLLM/Ollama, vector DBs, CUDA, evals | generic GenAI interest |

## Output format

For candidate lists, use a compact Markdown table:

| # | Candidate | Location | Public profile(s) | Fit tags | Evidence to verify |
|---:|---|---|---|---|---|

Then add:

- **Best first outreach shortlist** — 5–8 names with one-line rationale.
- **Suggested screening prompt** — short assignment/request that validates the role's highest-signal skills.
- **Caveat** — note that profile evidence is a screening proxy and should be verified before interviews.

## Pitfalls

- Do not claim candidates fully meet all requirements unless the public evidence verifies each requirement.
- Do not over-index on senior candidates for internships; explicitly flag people who may be overqualified.
- Do not stop at LinkedIn snippets if they are blocked; pivot to GitHub/portfolio evidence and include LinkedIn only when publicly listed by the candidate.
- Do not persist one-off candidate names or contact details in memory; if useful, place session examples in `references/`.

## References

- `references/kathmandu-ai-ml-intern-sourcing.md` — example session pattern for sourcing AI/ML intern candidates in Kathmandu using public GitHub evidence when LinkedIn scraping is constrained.
- `references/deepapi-linkedin-sourcing.md` — DeepAPI LinkedIn people-search workflow: dry run, fanout searches, polling, dedupe, intern-focused scoring, and output pattern.
- `references/kathmandu-aiml-deepapi-enrichment.md` — DeepAPI workflow for enriching top LinkedIn candidates with public emails/GitHubs/sites/resumes, extracting Google Drive JDs, and downselecting against an AI/ML intern rubric.
