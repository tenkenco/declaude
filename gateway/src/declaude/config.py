"""Runtime settings. All values overridable via environment variables (DECLAUDE_ prefix)."""
import os

from pydantic import BaseModel


class Settings(BaseModel):
    model_name: str = "qwen2.5-32b-instruct"
    model_base_url: str = "http://localhost:8000/v1"
    free_tier_monthly_limit: int = 100
    max_input_chars: int = 50_000
    stripe_payment_link: str = ""
    price_usd_per_month: str = "5.00"

    @classmethod
    def from_env(cls) -> "Settings":
        kwargs = {}
        for field in cls.model_fields:
            v = os.environ.get(f"DECLAUDE_{field.upper()}")
            if v is not None:
                kwargs[field] = v
        return cls(**kwargs)
