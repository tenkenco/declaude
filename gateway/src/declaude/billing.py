"""Stripe billing helpers kept out of the request layer."""
import os


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Hosted page where a customer can update payment details or cancel.

    Stripe owns this surface, which is deliberate: cancellation stays correct without us
    reimplementing subscription state, and customers get one predictable place to manage it.
    """
    import stripe

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url
