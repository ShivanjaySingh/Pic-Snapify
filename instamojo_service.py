# pip install instamojo-wrapper
from instamojo_wrapper import Instamojo
import logging

# Replace these with your actual keys from the Instamojo Dashboard
API_KEY = "41e98e4ff7cec843aa70aa5b9023c287"
AUTH_TOKEN = "3b66d1cdefcdad62354f9f26cc59e313"

# Set to False when you go live
api = Instamojo(api_key=API_KEY, auth_token=AUTH_TOKEN, endpoint='https://test.instamojo.com/api/1.1/')

def create_payment_request(amount, purpose, buyer_name, email, phone):
    try:
        response = api.payment_request_create(
            amount=amount,
            purpose=purpose,
            buyer_name=buyer_name,
            email=email,
            phone=phone,
            redirect_url="http://127.0.0.1:5000/payment-success",
            send_email=True,
            webhook="http://your-domain.com/instamojo-webhook"
        )
        # This returns the long URL the user needs to visit to pay
        return response['payment_request']['longurl']
    except Exception as e:
        logging.error(f"Instamojo Error: {str(e)}")
        return None