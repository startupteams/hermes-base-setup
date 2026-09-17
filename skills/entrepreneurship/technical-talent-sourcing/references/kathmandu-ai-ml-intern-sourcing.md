# Kathmandu AI/ML Intern Sourcing Pattern

Session-specific example for a request to find 20 AI/ML Engineering Intern candidates in Kathmandu, Nepal.

## What worked

- Automated LinkedIn scraping can run into anti-bot / ToS constraints. The useful pivot was to source from public GitHub profiles, blogs, and candidate-listed LinkedIn URLs.
- GitHub user search produced usable candidates when queried by location + language + role terms:
  - `location:Kathmandu language:Python machine learning`
  - `location:Kathmandu language:Python deep learning`
  - `location:Kathmandu language:Python artificial intelligence`
  - `location:Nepal language:Python langchain`
  - `location:Kathmandu language:Jupyter Notebook machine learning`
- Fetch profile metadata and recent repos, then score from repo names/descriptions/topics plus profile bio/location.
- Good evidence fields: profile URL, location, bio, public email if exposed, recent relevant repos, repo descriptions/topics, updated date.

## Fit tags used

- `Python`
- `ML/DL`
- `PyTorch/TF`
- `RAG/LLM`
- `API/Docker/DB`
- `NLP/CV`

## Ranking heuristics

Strong candidates had multiple of:

- Kathmandu/Nepal location in profile.
- Python or Jupyter Notebook repos with ML/DL projects.
- Explicit PyTorch/TensorFlow/Keras repos.
- RAG/LangChain/LLM repos for edge-fit.
- FastAPI/Streamlit/Docker/database projects for practical engineering fit.
- Recent activity and repo descriptions that explain the project.
- Explicit internship/open-to-collaboration signal for intern roles.

## Output pattern

Deliver a table with 20 rows, then a top outreach shortlist and screening prompt. Avoid saying candidates “meet” all requirements; say they are candidates to verify because public artifacts are a proxy.

Example screening prompt:

> Please share one GitHub repo where you used Python for ML/DL. In 5–7 bullets, explain the model, dataset, training/evaluation process, and what you would improve. Bonus if you’ve used PyTorch/TensorFlow, RAG, LangChain, Docker, or vector databases.

## Compliance note

Use candidate-public evidence only. Do not bypass LinkedIn controls or scrape logged-in/private profile data. If the user provides an authorized sourcing API, use that tool directly and cite the retrieved public/permissioned fields.
