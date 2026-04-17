# 🏆 Fantasy Draft

A Streamlit-based fantasy sports engine that allows users to draft a n-player squad within strict budget and roster constraints. Submissions are synced in real-time to Google Sheets.

## 📋 Draft Rules
- **Total Players:** n
- **Budget:** X Units
- **Gender Balance:** Min y Opens / y Womens
- **Club Limit:** Max p players from the same team
- **Captains:** c designated Captain per division (Double Points)

## 🛠️ Setup & Installation

This project uses **uv** for lightning-fast Python package management.

1. **Install Dependencies:**
   ```sh
   uv sync

## Secrets
Create and store secrets in .streamlit/secrets.toml
```sh
mkdir .streamlit
touch .streamlit/secrets.toml
```

Example:
```toml
[connections.gsheets]
spreadsheet = ""
type = ""
project_id = ""
private_key_id = ""
private_key = ""
client_id = ""
auth_uri = ""
token_uri = ""
auth_provider_x509_cert_url = ""
client_x509_cert_url = ""
```


## Data
1. Manually clean the ratings data and save it into `data/ratings.csv`
2. Execute `create_prices.py` 
```sh
uv run create_prices.py
```
This saves data to `data/test.csv` which includes the prices per player.

## Local UI
```sh
uv run streamlit run app.py
```