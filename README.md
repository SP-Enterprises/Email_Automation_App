# Bulk Email Sender

This project allows you to send personalized emails using:
- A list of company names and email addresses in an Excel file
- A Jinja2-based email template

## Versions Included

- ✅ Desktop GUI with Tkinter
- ✅ Web App using Flask
- ✅ REST API for mobile integration

## Setup

1. Install dependencies:
```bash
pip install pandas openpyxl jinja2 flask python-dotenv
```

2. Set your environment variables in `.env`:
```
EMAIL_ADDRESS=your_email@example.com
EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

3. Run the version you want:
- Desktop: `python tkinter_gui.py`
- Web: `python flask_app.py`
- API: `python api.py`

**Do not commit your `.env` file to version control.**

## License

MIT License
