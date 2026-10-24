# ✈️ Job Hunt Autopilot
> **Track every application. Catch every fake offer.**  
> Built for the reality of post-layoff job searches.

---

## 💡 The Problem & The Layoff Story

After a sudden layoff, job seekers face a chaotic numbers game:
- Applying to 100+ roles within 2–3 weeks.
- Losing track of who replied, who scheduled an interview, who rejected them, and when to follow up.
- **The dark side:** Desperate, stressed candidates are the prime targets for **predatory recruitment scams** — fake offers demanding "training fees", check-cashing equipment fraud, sensitive identity document harvesting (SSN/Aadhaar/banking details), and Hinglish Telegram rating tasks.

**Job Hunt Autopilot** solves this with a single, unified pipeline. A sample inbox of 20 emails goes in; out comes:
1. **Self-updating pipeline tracker** (`applied`, `interview`, `rejected`, `offer`).
2. **Fake offers flagged in bright red with explicit reasons** (scam check is a first-class pipeline label).
3. **Automated follow-up reminders** after 7 days of silence, paired with 1-click tailored email drafts.

---

## ⚡ Key Features & Scope

- **Single Classification Pipeline:** Each email is classified once into one of five definitive stages:
  - `applied`: Application acknowledgement received.
  - `interview`: Recruiter phone screen, CoderPad assessment, system design round, or onsite panel.
  - `rejected`: Formal rejection notice (archived).
  - `offer`: Legitimate formal offer letter with salary, equity, and benefits from verified domains.
  - `scam`: Fraudulent recruitment scheme intercepted and blocked.
- **Scam Detection Engine (Kaggle & Hugging Face datasets):**
  - Upfront training/registration fees ($250 / ₹18,500 via UPI/Crypto).
  - Check cashing / equipment advance fraud (cashier's check overpayment).
  - Pre-interview identity theft (demanding SSN, Aadhaar, Driver's License, or bank routing before any screen).
  - Hinglish & task scams ("ekdum genuine", daily payouts of ₹3,000–₹8,000, Telegram @recruiter bypass).
  - Free webmail impersonation (`@gmail.com`, `@outlook.com`, `@protonmail.com` claiming corporate authority).
- **7-Day Follow-Up Engine:**
  - Flags applications pending for ≥7 days without response.
  - Generates ready-to-send, high-converting follow-up templates customized to the role, company, and days elapsed.
- **No Gmail Login Needed:** Loads cleanly from standard `.json` or `.mbox` files.
- **Zero Distractions:** Laser-focused on application tracking, follow-ups, and fake offer interception (no PF, gratuity, or resume-rewriting bloat).

---

## 📂 Project Structure

```
job-hunt-autopilot/
├── data/
│   ├── sample_inbox.json        # 20 realistic emails (Layoff candidate journey)
│   ├── sample_inbox.mbox        # Exact RFC 2822 standard Unix mbox format
│   └── create_mbox.py           # Mbox generator utility
├── job_autopilot/
│   ├── __init__.py
│   ├── models.py                # Pydantic data models (StageEnum, EmailMessage, etc.)
│   ├── parser.py                # Multi-format parser (.json and .mbox)
│   ├── classifier.py            # Unified classification & scam explainability engine
│   ├── tracker.py               # Application state tracker & 7-day follow-up engine
│   └── cli.py                   # Rich terminal dashboard
├── tests/
│   ├── run_tests.py             # Zero-dependency test runner (Python unittest)
│   └── test_autopilot.py        # 100% test coverage suite
├── app.py                       # Modern Streamlit Web Dashboard
├── dashboard.html               # Standalone interactive Generative UI dashboard
└── README.md
```

---

## 🚀 Quickstart & Usage

### 1. Terminal CLI Dashboard
Run against the sample JSON or `.mbox` inbox:

```bash
# Set PYTHONPATH to project root
export PYTHONPATH="."   # On Linux/macOS
$env:PYTHONPATH="."     # On Windows PowerShell

# Run with JSON sample
python -m job_autopilot.cli --input data/sample_inbox.json

# Run with .mbox sample
python -m job_autopilot.cli --input data/sample_inbox.mbox

# Export tracker results to CSV
python -m job_autopilot.cli --input data/sample_inbox.json --export-csv tracker_export.csv
```

### 2. Interactive Streamlit Web App
Launch the full web interface:

```bash
streamlit run app.py
```
- Switch between preloaded JSON, preloaded `.mbox`, or upload your own file.
- View real-time Scam Radar with red warning tags and explanations.
- Copy 1-click follow-up emails for stale applications (Notion, Airbnb, Datadog).
- Inspect full raw email headers and classification logic.

### 3. Standalone Generative UI Dashboard
Simply double-click or open `dashboard.html` in any web browser, or view it in the side pane artifact.

---

## 🧪 Running Unit Tests

The test suite requires zero external test packages:

```bash
python tests/run_tests.py
```
Output:
```
Ran 6 tests in 0.078s
OK
```

---

## 📊 Sample Dataset Breakdown (Alex Chen's Post-Layoff Inbox)

| Stage | Count | Entities / Details |
|---|:---:|---|
| **Legitimate Offers** | 2 | **Linear** ($185k + equity), **Vercel** ($175k + $25k bonus) |
| **Active Interviews** | 4 | **Uber** (Screen), **Brex** (CoderPad), **Snowflake** (Onsite Loop), **GitHub** (Loop) |
| **Rejections** | 4 | **Google**, **Meta**, **Netflix**, **Shopify** |
| **Applied (Pending)** | 5 | **Airbnb** (9d, Overdue), **Datadog** (8d, Overdue), **Notion** (12d, Overdue), **Stripe** (3d), **Figma** (2d) |
| **🚨 Flagged Fake Offers** | 5 | Upfront fee scam, Check-cashing scam, Hinglish Telegram scam, PII theft, Crypto fee scam |
