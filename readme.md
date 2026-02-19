# WhatsApp Web Bulk Image Sender (Playwright + Python)

A robust WhatsApp Web automation tool built with **Python and Playwright** that sends an **image with a caption** to multiple phone numbers loaded from an Excel file.

This project is designed for **business outreach, internal communication, and automation learning purposes** using WhatsApp Web.

---

## 🚀 Features

- 📂 Read phone numbers directly from an **Excel (.xlsx)** file
- 🧹 Automatically **cleans and normalizes phone numbers**
- 🌍 Auto-adds country code (default: India `91`)
- 🖼️ Sends **image + multi-line caption**
- 🔐 Persistent WhatsApp login (QR scan only once)
- ❌ Handles invalid numbers & “No results found”
- 📊 Generates result report (`numbers_result.xlsx`)
- 🖥️ Works on **macOS, Windows, and Linux**
- 🧠 Smart UI recovery if WhatsApp gets stuck

---

## 🛠️ Tech Stack

- **Python 3.9+**
- **Playwright (Chromium)**
- **Pandas**
- **WhatsApp Web**

---

## 📁 Project Structure

project/
├── script.py # Main automation script
├── numbers.xlsx # Input Excel file
├── numbers_result.xlsx # Output result file (auto-generated)
└── wa_profile/ # Persistent WhatsApp session (auto-created)


> ⚠️ Do NOT delete `wa_profile` after first login.

---

## 📄 Excel File Format

The Excel file **must** contain a column named exactly:

Phone


### Example (`numbers.xlsx`):

| Phone |
|------|
| 9876543210 |
| +91 2345678234 |
| 09876543210 |
| 91-99999-88888 |

The script automatically:
- Removes spaces, symbols, and prefixes
- Adds country code if missing
- Skips invalid numbers

---

## 🖼️ How Image Sending Works

- The script pastes the image using **clipboard (Cmd+V / Ctrl+V)**
- **You must copy the image to clipboard BEFORE running the script**

---

## ⚙️ Setup Instructions

### 1️⃣ Install Python dependencies

```bash
pip install playwright pandas openpyxl
2️⃣ Install Playwright browser
python -m playwright install chromium
▶️ Running the Script
python script.py
First Run
WhatsApp Web opens

Scan QR code

Session is saved

Next Runs
No QR scan required

📊 Output File
After execution, results are saved to:

numbers_result.xlsx
Example Output:
Phone	phone_clean	status	note
9876543210	919876543210	SENT	OK
12345		SKIPPED	Bad/empty phone
9999999999	919999999999	NOT_FOUND	No results found
🧠 Configuration
Edit values in the script:

CAPTION = """Whatever Caption you want"""

WAIT_BETWEEN_NUMBERS_SEC = 1.0
DEFAULT_COUNTRY_CODE = "91" Change according to your needs

🛡️ Important Notes
🚫 Do NOT spam unknown users
⏳ Add delays to avoid WhatsApp restrictions
🧪 For educational & internal use only

❗ Common Issues
Image not sending?
Copy image to clipboard before running
Allow Terminal clipboard access (macOS)
New chat button not found?
Keep browser zoom at 100%
Don’t resize window too small

📌 Disclaimer
This project is not affiliated with WhatsApp.
Use responsibly and comply with WhatsApp’s Terms of Service.

🤝 Contributing
Pull requests and improvements are welcome.

