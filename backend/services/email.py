import os
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = os.getenv("SENDER_NAME")

def send_email_otp(recipient: str, otp: str):
    url = "https://api.brevo.com/v3/smtp/email"
    
    payload = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL
        },
        "to": [
            {
                "email": recipient,
                "name": recipient.split("@")[0]
            }
        ],
        "subject": "Sentilyst - Your OTP Code",
        "htmlContent": f"""
       <html>
  <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #eef1f5; padding: 20px; color: #2c2c2c;">
    <div style="max-width: 900px; margin: auto; background-color: #ffffff; padding: 40px 30px; border-radius: 12px; box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);">
      
      <!-- Logo or Brand -->
      <!-- <div style="text-align: center; margin-bottom: 30px;">
        <img src="https://via.placeholder.com/120x40?text=LOGO" alt="Logo" style="max-width: 120px;">
      </div> -->

      <!-- Greeting -->
      <h2 style="color: #1e1e1e; text-align: center; margin-bottom: 16px;">Hey there 👋</h2>

      <!-- Message -->
      <p style="font-size: 13px; color: #4d4d4d; text-align: center; line-height: 1.6;">
        We got a request to verify your identity. Here's your One-Time Password (OTP) to continue securely:
      </p>

      <!-- OTP Box -->
      <div style="font-size: 24px; font-weight: 700; color: #111; text-align: center; padding: 18px 0; background-color: #f8f9fb; border-radius: 6px; margin: 30px 0;">
        <strong>{otp}</strong>
      </div>

      <!-- Expiry Info -->
      <p style="font-size: 12px; color: #888; text-align: center; line-height: 1.5;">
        This OTP is valid for the next <strong>5 minutes</strong> only.<br>If this wasn't you, you can safely ignore this message.
      </p>

      <!-- Divider -->
      <hr style="border: 0; border-top: 1px solid #ddd; margin: 30px 0;">

      <!-- Footer Note -->
      <p style="font-size: 11px; color: #aaa; text-align: center;">
        This is an automated message. Please do not reply directly to this email.
      </p>
    </div>
  </body>
</html>

        """
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 201:
        raise Exception(f"Failed to send OTP email. Response: {response.text}")
    else:
        print(f"OTP sent successfully")
