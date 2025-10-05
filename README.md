# Gmail Automation Project

A **Python-based Gmail automation tool** that fetches emails via the Gmail API, stores them in a relational database, and applies **rule-based actions** like marking emails as read or moving them to specific labels.

---

## Features

- Authenticate to Gmail using **OAuth 2.0** (no password storage).  
- Fetch emails from your **Inbox** and store them in a **SQLite** database.  
- Define **rules in JSON** with conditions and actions:
  - Fields: `From`, `Subject`, `Message`, `Received Date/Time`
  - Predicates: `contains`, `does not contain`, `equals`, `does not equal`, date comparisons
  - Actions: `mark_as_read`, `mark_as_unread`, `move_to_label`  
- Modular, extendable, and safe — can handle multiple rules and actions per email.  

---

## Folder Structure

gmail-automation/
├── core/
│ ├── gmail_service.py # Gmail API integration
│ ├── model.py # Database models and session handling
│ ├── rules.json # JSON file defining rules
  ├── process_rules.py # Script to apply rules to stored emails
├── tests
│ ├── test_gmail_service.py 
│ ├── test_process_rules.py
├── README.md
├── requirements.txt # Required Python packages



---
## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/gmail-automation.git
cd gmail-automation
```

### 2. Create a Python virtual environment

```bash
python -m venv venv
# Activate virtual environment:
# Linux / Mac
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/), create a project, and enable the **Gmail API**.
2. Create **OAuth 2.0 Client ID credentials** (Desktop App).
3. Download the JSON and save it as:

```
core/credentials.json
```

### 5. First-time authentication

```bash
python -m core.gmail_service --db sqlite:///emails.db --max 5
```

* This will open a browser to authorize access and save the token in:

```
core/token.pickle
```

---

## Usage

### 1. Fetch Emails

```bash
python -m core.gmail_service --db sqlite:///emails.db --max 50
```

* Fetches emails from Gmail Inbox and stores them in the database.

### 2. Apply Rules


```bash
python -m core.process_rules --db sqlite:///emails.db --rules core/rules.json
```

* Applies rules from `rules.json` to emails in the database and performs actions in Gmail.
