from dotenv import load_dotenv
import os
import robin_stocks.robinhood as r

load_dotenv()

def login_robinhood():
    username = os.getenv("RH_USERNAME")
    password = os.getenv("RH_PASSWORD")
    mfa = os.getenv("RH_MFA_CODE", None)

    try:
        login = r.login(username=username, password=password, mfa_code=mfa)
        return login
    except Exception as e:
        raise RuntimeError(f"Robinhood login failed: {e}")

def logout_robinhood():
    r.logout()
