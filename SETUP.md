# WealthIn.AI — Step-by-Step Setup (Windows)

Follow these in order. Each step says **what to do** and **what you should see**.

---

## PHASE 1 — Get it running on your computer

### Step 1. Get a free Google Gemini API key
1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google (Gmail) account — the one you already use.
3. Click **Create API key** -> **Create API key in new project**, copy the key
   (looks like `AIza...`). Keep it handy.

### Step 2. Unzip the project
- Right-click `wealthin-ai.zip` -> **Extract All** -> remember where it lands
  (e.g. `C:\Users\Karan Nishchal\wealthin-ai`).

### Step 3. Open a terminal in that folder
- Open the `wealthin-ai` folder in File Explorer.
- Click the address bar, type `powershell`, press Enter. A terminal opens
  already inside the folder.

### Step 4. Create a virtual environment and install
Paste these one line at a time:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
- You should see `(.venv)` at the start of your prompt, then packages installing.
- If activation is blocked, run this once then retry Step 4:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### Step 5. Add your key
```powershell
Copy-Item .env.example .env
notepad .env
```
- Notepad opens. Find the line `GEMINI_API_KEY=` and paste your key after the `=`
  so it reads `GEMINI_API_KEY=AIza_your_key_here`. **Save and close.**
- Leave `LLM_PROVIDER=gemini` as-is (it already is).

### Step 6. Start the backend (API)
```powershell
uvicorn app.api:app --port 8000
```
- You should see `Uvicorn running on http://127.0.0.1:8000`. **Leave this window open.**

### Step 7. Start the front-end (in a SECOND terminal)
- Open the folder again -> address bar -> `powershell` -> Enter (new window).
```powershell
.\.venv\Scripts\Activate.ps1
$env:API_URL="http://localhost:8000"
streamlit run ui/streamlit_app.py
```
- Your browser opens **http://localhost:8501** with the chat. Try:
  *"Compare Apple and Microsoft over the last 3 months."*

Success: you now have it running locally. (To stop: press `Ctrl+C` in each terminal.)

> Prefer one command? If you have **Docker Desktop** installed, skip Steps 4-7 and
> just run `docker compose up --build`, then open http://localhost:8501.

---

## PHASE 2 — Put it on your GitHub

### Step 8. Create the repository
1. Go to **https://github.com/new**
2. Repository name: `wealthin-ai`
3. Choose **Public**. Do **not** tick "Add a README".
4. Click **Create repository**. Leave that page open.

### Step 9. Push your code
In your first terminal (inside the `wealthin-ai` folder), paste line by line:
```powershell
git init
git add .
git commit -m "Initial commit: WealthIn.AI agentic assistant"
git branch -M main
git remote add origin https://github.com/karannishchal/wealthin-ai.git
git push -u origin main
```
- If asked to log in, follow the browser prompt.
- Refresh your GitHub page — all the files are there.

### Step 10. Watch CI run
- On your repo, click the **Actions** tab. The CI job runs the tests and linter
  automatically, then builds the Docker image. A green check means all good.

---

## PHASE 3 — Deploy it live (optional, do when ready)

Easiest path — **Render** (free):
1. Go to **https://render.com**, sign up with GitHub.
2. **New -> Web Service -> connect your `wealthin-ai` repo.**
3. Render detects the `Dockerfile`. Set an environment variable:
   `GEMINI_API_KEY = your_key`.
4. Click **Create Web Service**. In a few minutes you get a live URL.

**Kubernetes demo (optional, local):** with Docker Desktop's Kubernetes enabled, or
`kind`/`minikube`:
```powershell
kubectl create namespace wealthin
kubectl -n wealthin create secret generic wealthin-secrets --from-literal=GEMINI_API_KEY=your_key
kubectl apply -f k8s/
```

---

## If something goes wrong
- **`python` not found** -> install Python 3.11+ from python.org (tick "Add to PATH").
- **`git` not found** -> install Git from git-scm.com.
- **`docker` not found** -> install Docker Desktop (only needed for the Docker/K8s steps).
- **A provider/model error when chatting** -> copy the exact error text and send it to me; first-run provider quirks are quick to fix.
- Anything else -> note the exact error text; it's usually a missing tool or a typo in `.env`.
