A solution that feels like “filling-in a spreadsheet” instead of “installing software” is usually the easiest thing for non-technical shop or vending-machine owners.
The entire system can be boiled down to three Google tools that most people already know (Sheets, Forms, Drive) plus one tiny helper program that you, the technical person, run in the background.

────────────────────────────────────────

1. What the owner sees and does ──────────────────────────────────────── A. Google Sheet (acts as the “back office”)

• Tab 1 : Products
Columns:  SKU | Name | Price ($) | Weight (g) | Current Stock | Photo URL
– They add a new row or change numbers exactly the same way they already use Excel.
– Green or red cell-colours (conditional formatting) warn when stock is low.

• Tab 2 : Restock / Adjust log
Automatically filled every time they submit a simple Google Form (next item).

• Tab 3 : Sales log
Filled automatically by the helper program when your fridge tells it “2 Cokes were taken”.

• Tab 4 : Charts
Built-in Sheets charts show “Units sold per day”, “Top sellers”, “Average days between restocks”, etc.
Owners don’t have to build anything: the template already contains the charts and updates live.

B.  Google Form (the only thing they open while they are physically refilling)

– Opens like any web page on their phone.
– Two questions:

1. Product (drop-down fed by the Products tab)
2. Quantity loaded (positive) or removed (negative).
   – Hit Submit.  That row is appended to the Restock / Adjust log.  Current Stock is recalculated by a simple Sheets formula.

C.  Optional “phone app” look: AppSheet one-click

• In Google Sheets menu choose Extensions → AppSheet → Create an app.
• Google automatically generates a mobile front-end with three tabs (Products, Restock, Sales).
• Owners add/edit products or restock by tapping plus signs; no installation — it’s a web-app link saved to their home screen.

────────────────────────────────────────
2.  What runs in the background (you set it up once)
────────────────────────────────────────
Tiny Python script (≈40 lines, can run on the same PC that already runs your Flask prototype).

1. Every 30 s pull the current Products tab via the Google-Sheets API (gspread library).
   Convert it to the YAML/JSON structure your fridge software already expects and overwrite config.yaml.
   → Owners never press “sync”, it is always in-sync.
2. Expose one HTTP endpoint /transaction that your fridge code calls when the door closes
   with a list of items that were actually removed.
   The script subtracts those quantities in the Sheet (Current Stock column) and appends a row to the Sales log tab.
3. (Optional) download any new Photo URLs from the sheet into a “training_images/” folder
   so you can retrain DETR later.  That keeps photos in one place (Google Drive) and owners simply paste the share-link in the sheet.

You create one service-account key once, share the Google Sheet with that e-mail, and store the key.json beside the script.  Nothing else to configure.

────────────────────────────────────────
3.  Why this is easiest for non-technical users
────────────────────────────────────────
• They already understand spreadsheets and forms.
• No accounts to create, no software to install; they use their existing Google login.
• Works on any phone, tablet or PC instantly.
• If they accidentally delete something they can use Google Sheets’ “Version history”.
• Charts and exports (CSV, PDF) are built-in; if they want fancier dashboards you can connect the same sheet to Google Looker Studio later with two clicks.

────────────────────────────────────────
4.  Quick start checklist for you
────────────────────────────────────────

1. Make a copy of the provided Google-Sheet template.
2. Share it with each owner (Viewer) and with your service account (Editor).
3. Paste its Sheet ID into the helper script and run `python helper.py`.
4. In your existing fridge/Flask code, replace the current “write to local SQLite” with one HTTP POST to `http://<PC_IP>:5001/transaction` containing `[{"sku":"cola","qty":2}, …]`.
5. Done – from now on owners only open the Sheet or the auto-generated AppSheet link.

────────────────────────────────────────
Result
────────────────────────────────────────
• Owners manage inventory exactly like a normal stocking spreadsheet.
• Real-time price/weight data feeds the fridge.
• Sales and restock history accumulate automatically for trend analysis.
• Zero custom UI to maintain; Google keeps the interface familiar and secure.



**Designing a Google Sheet**

I'm laying out a structure for a Google Sheet to manage product inventory.

In the "Products" sheet, I have columns for SKU, Name, Price, Weight, Photo URL, Opening Stock, Manual Adjustments, Sales Sum, and Current Stock, with formulas to track adjustments and sales.

I'll also create a "RestockLog" to track restocks with a Google Form submission. For the "Sales" sheet, the formulas will calculate adjustments and reflect current stock dynamically, plus I'll use conditional formatting for low stock alerts.

**Coding a helper script**

I'm working on a script named helper.py that uses gspread and Flask to interact with Google Sheets.

Upon startup, it'll open the specified sheet and then schedule a function to sync data to a YAML file every 30 seconds.

I'll set an endpoint for transactions that accepts a JSON input for items sold. For each item, the script will log the sale in the Sales sheet by appending a row with the timestamp, SKU, negative quantity, and transaction ID. I'll also ensure it updates the configuration to include item weights and prices.



Google-Sheet "App"

• the price/weight config file your fridge already needs
• a permanent sales log
• a live “current-stock” column (so owners always know what is inside the fridge)

and exposes one tiny web-hook (/transaction) that your existing door-logic can call.

Non-technical owners only touch Google Sheets (or the auto-generated AppSheet mobile view).
Everything else is fully automated by a 70-line Python helper you run once on any always-on PC/Raspberry-Pi.

────────────────────────────────────────
PART 1 — Create the Google Sheet template
────────────────────────────────────────

1. Make a new Sheet called “Fridge Inventory”.
2. Rename the first three tabs exactly as shown:

* Products
* RestockLog
* SalesLog

3. PRODUCTS tab layout (row 1 is headers)

| A   | B    | C       | D        | E         | F            | G                 | H        | I            |
| --- | ---- | ------- | -------- | --------- | ------------ | ----------------- | -------- | ------------ |
| SKU | Name | Price $ | Weight g | Photo URL | OpeningStock | Restock/AdjustSum | SalesSum | CurrentStock |

• OpeningStock is the number you initially load when you install the fridge.
• Columns G, H, I are formulas:

G2:   =IFERROR(SUMIF(RestockLog!B:B, A2, RestockLog!C:C),0)
H2:   =IFERROR(SUMIF(SalesLog!B:B,     A2, SalesLog!C:C),0)      (Sales quantities are NEGATIVE)
I2:   =F2+G2+H2

Copy the three formulas down as far as you like.
Add conditional formatting on column I: “Cell < 5 → paint red”.

4. RESTOCKLOG tab layout (Google Form will write here)

| A                | B   | C   | D      |
| ---------------- | --- | --- | ------ |
| Timestamp (auto) | SKU | Qty | Reason |

5. SALESLOG tab layout (Python helper will write here)

| A                | B   | C       | D             |
| ---------------- | --- | ------- | ------------- |
| Timestamp (auto) | SKU | Qty -ve | TransactionID |

6. (Optional) Insert some nice charts in a new tab “Charts” that source
   data straight from the Products and SalesLog sheets:
   • Bar: Units sold by SKU
   • Line: Daily units sold (QUERY/SUM and Sheets’ built-in chart)

────────────────────────────────────────
PART 2 — Offer the owner a one-tap mobile UI
────────────────────────────────────────
In the Google-Sheet menu choose
Extensions → AppSheet → Create an App.

Google will auto-generate a mobile web-app with two views (Products, RestockLog).
The owner presses the “+” button to add a restock or edit a product—no extra code from you.

────────────────────────────────────────
PART 3 — Set up a service account so Python can edit the sheet
────────────────────────────────────────

1. In Google Cloud Console: New Project → “FridgeHelper”.
2. APIs & Services → Enable API → enable “Google Sheets API” & “Google Drive API”.
3. IAM & Admin → Service accounts → Create
   * name: fridge-sheet-bot
   * role: Basic / Editor
4. “Manage keys” → “Add key” → JSON → download file and save as credentials.json
5. Open your Sheet → Share → add the service-account mail address with EDITOR rights.

────────────────────────────────────────
PART 4 — Python helper (helper.py)
────────────────────────────────────────

```bash
# one-time install
python -m pip install flask gspread google-auth pyyaml
```

```python
#!/usr/bin/env python3
"""
helper.py  – keeps Google-Sheet ⇄ fridge config.yaml in sync
             and records every sale coming from the fridge

Start with:   python helper.py
"""

import time, threading, yaml, datetime, os
from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials

# ──────────── 1.  SET THESE TWO CONSTANTS ────────────
SHEET_ID         = "YOUR_SHEET_ID_HERE"# find it in the sheet URL
CONFIG_YAML_PATH = "config.yaml"# where your fridge code reads prices/weights
# ─────────────────────────────────────────────────────

SCOPES      = ["https://www.googleapis.com/auth/spreadsheets",
"https://www.googleapis.com/auth/drive"]
CREDS       = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
GS          = gspread.authorize(CREDS)
SHEET       = GS.open_by_key(SHEET_ID)
PROD_TAB    = SHEET.worksheet("Products")
SALES_TAB   = SHEET.worksheet("SalesLog")

app         = Flask(__name__)

# -----------------------------------------------------
defproducts_to_config():
"""
    Reads Products tab and writes a compact YAML block
    inventory:
      cola:  {price: 2.0, weight: 355, tolerance: 5}
      chips: {price: 1.5, weight: 70,  tolerance: 4}
    """
    rows  = PROD_TAB.get_all_values()[1:]          # skip header
    inv   = {}
for sku,name,price,weight,*_ in rows:
ifnot sku:              # ignore blank lines
continue
try:
            inv[sku] = {
"price"    : float(price),
"weight"   : float(weight),
"tolerance": 5# hard-coded or add a column
            }
except ValueError:
print(f"⚠️  bad numeric value in row with SKU={sku}; skipped")

    data = {"inventory": inv}
withopen(CONFIG_YAML_PATH, "w") as f:
        yaml.dump(data, f)

print(f"✅ config.yaml updated ({len(inv)} SKUs)")

# -----------------------------------------------------
defperiodic_sync(interval=30):
whileTrue:
try:
            products_to_config()
except Exception as e:
print("Sync error →", e)
        time.sleep(interval)

# -----------------------------------------------------
defappend_sale_row(sku:str, qty:int, tx_id:str):
"""
    Append (-qty) to SalesLog. Google-Sheet formulas update stock automatically.
    """
    now_iso = datetime.datetime.utcnow().isoformat(" ", timespec="seconds")
    SALES_TAB.append_row([now_iso, sku, -abs(qty), tx_id], value_input_option="USER_ENTERED")

# -----------------------------------------------------
@app.route("/transaction", methods=["POST"])
deftransaction():
"""
    The fridge must POST JSON like:
    {
      "transaction_id": "abc123",
      "items": [ {"sku":"cola", "qty":2},
                 {"sku":"chips","qty":1} ]
    }
    """
    data = request.get_json(silent=True) or {}
    tx_id  = data.get("transaction_id") or"NA"
    items  = data.get("items", [])

for item in items:
        sku  = item.get("sku")
        qty  = int(item.get("qty", 0))
if sku and qty:
            append_sale_row(sku, qty, tx_id)

print(f"🛒 logged transaction {tx_id}: {items}")
return jsonify({"status":"ok", "items_logged": len(items)})

# -----------------------------------------------------
if __name__ == "__main__":
# start background thread that refreshes config.yaml every 30 s
    threading.Thread(target=periodic_sync, daemon=True).start()

# tiny Flask server for the fridge to call
    app.run(host="0.0.0.0", port=5001)
```

Run it:

```bash
python helper.py
# Output every 30 s:
# ✅ config.yaml updated (5 SKUs)
# (after a sale) → 🛒 logged transaction tx_9493: [{'sku': 'cola', 'qty': 1}]
```

º The file `config.yaml` is now continuously rewritten — point your existing fridge
code at this path instead of hand-edited YAML.

º If the owner edits price or weight in the Sheet, the fridge picks it up within 30 seconds.
º If the owner adds a brand-new SKU, the fridge knows about it automatically.

────────────────────────────────────────
PART 5 — Change ONE place in the fridge code
────────────────────────────────────────
Where you currently “finalise” a purchase, add:

```python
import requests, json
...
payload = {
"transaction_id": txn_id,             # whatever id you use
"items"         : [{"sku":sku, "qty":qty} for sku,qty in items_dict.items()]
}
try:
    requests.post("http://<PC_running_helper>:5001/transaction",
                  data=json.dumps(payload),
                  headers={"Content-Type":"application/json"},
                  timeout=2)
except Exception as e:
print("⚠️  could not log sale:", e)
```

That is literally everything: stock is deducted, charts update, low-stock cells turn red, and the YAML used by the fridge stays current.

────────────────────────────────────────
PART 6 — Optional extras in 1-line each
────────────────────────────────────────
• Email/SMS a restock alert → in the Sheet use `=IF(I2<5,"🔴 restock", "")` and add AppSheet workflow “Send mail when column changes to 🔴 restock”.

• Owner wants an “export to CSV” → File → Download → CSV (built-in).

• More fancy dashboards → Data → Connect to Looker Studio → pick the same Sheet.

────────────────────────────────────────
Recap
────────────────────────────────────────
Non-technical workflow

1. They open the Sheet (or AppSheet link) to add a product row or submit a restock form.
2. They close the fridge door; your firmware calls /transaction.
3. Sheet auto-updates stock & charts; helper.py rewrites config.yaml.

Technical workload for you: ~70 lines of Python once, then forget about it.
