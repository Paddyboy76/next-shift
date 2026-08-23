from __future__ import annotations
import os
from typing import Any
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests

def review_coverage(*,message:str,proposals:list[dict[str,Any]],source_reference:str)->dict[str,Any]:
    url=os.environ.get("COVERAGE_CRITIC_URL","").rstrip("/")
    if not url: raise RuntimeError("COVERAGE_CRITIC_URL is required")
    token=id_token.fetch_id_token(Request(),url)
    response=requests.post(f"{url}/v1/review",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
      json={"message":message,"proposals":proposals,"source_reference":source_reference},timeout=150)
    if response.status_code>=400: raise RuntimeError(f"Coverage Critic failed: {response.status_code} {response.text[:300]}")
    review=response.json().get("review")
    if not isinstance(review,dict): raise RuntimeError("Coverage Critic returned invalid review")
    return review
