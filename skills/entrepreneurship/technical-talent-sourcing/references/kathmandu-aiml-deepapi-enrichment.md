# Kathmandu AI/ML Intern DeepAPI Enrichment Pattern

This reference captures a reusable pattern from a Kathmandu AI/ML Engineering Intern sourcing session where the user asked for LinkedIn candidates, then requested emails, GitHubs, personal sites, resumes, and a downselect against a Google Drive JD.

## When to use

Use this when sourcing technical candidates where the user asks for:

- LinkedIn candidate discovery through DeepAPI
- Shortlist enrichment with public contact/artifact data
- Matching against a PDF/Google Drive job description
- A Markdown deliverable that can be shared as a file

## Job description extraction from Google Drive

For a public Google Drive file URL like:

```text
https://drive.google.com/file/d/<FILE_ID>/view
```

Use both:

1. `POST /v1/scrape/website` on the Drive view URL to capture title/markdown when Google exposes it.
2. `POST /v1/scrape/pdf` on:

```text
https://drive.google.com/uc?export=download&id=<FILE_ID>
```

The PDF endpoint may return full page text even when a generic website scrape only returns partial markdown. Save the request IDs in the deliverable and summarize the JD into required skills, edge skills, and actual work areas before scoring candidates.

## Candidate enrichment pattern

1. Run `POST /v1/scrape/linkedin/profile` on the shortlist with:

```json
{
  "profiles": ["<linkedin urls>"],
  "includeEmail": true,
  "waitForFinishSecs": 60
}
```

Use `includeEmail` only when the user explicitly asks for emails/contact info.

2. Record canonical LinkedIn URLs from the profile endpoint. People-search URLs may be opaque IDs; profile enrichment can return readable slugs.
3. Extract public emails only when returned by LinkedIn profile enrichment or another public page. Do not infer private email patterns.
4. Run exact-name DeepAPI web searches for each candidate using combinations of:

```text
"<Name>" Kathmandu AI ML Python GitHub email resume LinkedIn
"<Name>" "github" "Kathmandu"
"<Name>" "resume" OR "CV" "AI" "Machine Learning"
"<Name>" "portfolio" "email" "Python"
"<linkedin-slug>" GitHub email resume
```

5. Use DeepAPI GitHub profile scraping for candidate GitHub accounts that web search surfaces.
6. Verify identity before writing a GitHub/site/resume into the report. Strong verification signals:
   - GitHub profile social link points back to the same LinkedIn slug.
   - Location, name, and bio match the candidate.
   - Portfolio links to the same LinkedIn/GitHub.
7. Explicitly mark ambiguous same-name artifacts as “Not found / not verified” rather than recording a likely-wrong URL.

## Scoring pattern against AI/ML intern JDs

Use a compact 20-point screen:

| Dimension | Points | Evidence |
|---|---:|---|
| Required-skill fit | 1–5 | Python, DSA/OOP, ML/DL, PyTorch/TF, Git/GitHub, Linux, REST APIs, SQL/DB |
| Edge-skill fit | 1–5 | RAG, LangChain/LangGraph, HF, OpenAI, Ollama/vLLM, Docker/K8s, vector DBs, prompt engineering, evals |
| Public artifact strength | 1–5 | Verified GitHub, portfolio, resume, runnable repo, public project descriptions |
| Intern/junior fit | 1–5 | Student, intern, apprentice, junior, entry-level/open-to-work signals |

Downselect by both score and hiring practicality. For internships, a slightly lower score with stronger junior/availability signal may beat an overqualified senior. State concerns such as “no public GitHub found” or “may expect junior engineer compensation.”

## Deliverable pattern

Update the existing `.md` file instead of creating a new one when the user says “same file.” Include:

- Source and updated timestamp
- JD source + DeepAPI request IDs
- JD summary / rubric
- Original candidate table with canonical URLs if available
- Enrichment table: email, GitHub, personal site, resume/CV, notes
- Scored top 8 against JD
- Down-selected top 4 with “why” and concerns
- Reminder: do not send email without explicit approval
