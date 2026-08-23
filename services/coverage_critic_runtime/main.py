from __future__ import annotations
import json, os
from typing import Any
import google.auth
from flask import Flask, jsonify, request
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import id_token
import requests

PROJECT="next-shift-506004"; MODEL=os.environ.get("CRITIC_MODEL","gemini-3.5-flash")
OWNERS={"Facilities","AssetLogistics","LanguageAccess","DischargeDME","EVSThroughput","PatientTransport"}
app=Flask(__name__)

def _access():
    creds,_=google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"]); creds.refresh(AuthRequest()); return creds.token

def model_review(message: str, proposals: list[dict[str,Any]]) -> dict[str,Any]:
    prompt=("Act as an independent coverage critic for non-clinical operational handovers. Compare raw handover and proposals. "
      "Find missed, duplicated, conflated, misrouted, or uncertain work only. Never propose clinical work. Owners are Facilities, AssetLogistics, "
      "LanguageAccess, DischargeDME, EVSThroughput, PatientTransport. Return strict JSON: decision PASS or REVIEW_REQUIRED; summary; findings array. "
      "Each finding: type MISSED/DUPLICATED/CONFLATED/MISROUTED/UNCERTAIN, detail, proposal_indexes array, suggested_owner canonical owner or null.\nRAW:\n"
      +message+"\nPROPOSALS:\n"+json.dumps(proposals,sort_keys=True))
    url=f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent"
    response=requests.post(url,headers={"Authorization":f"Bearer {_access()}","Content-Type":"application/json"},
      json={"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"temperature":0,"responseMimeType":"application/json"}},timeout=120)
    response.raise_for_status(); body=response.json(); result=json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
    if result.get("decision") not in {"PASS","REVIEW_REQUIRED"} or not isinstance(result.get("findings"),list): raise ValueError()
    for item in result["findings"]:
        if item.get("suggested_owner") not in OWNERS: item["suggested_owner"]=None
    return result

@app.get("/health")
def health(): return jsonify({"status":"ok","service":"next-shift-coverage-critic","model":MODEL})

@app.post("/v1/review")
def review():
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or not isinstance(data.get("message"),str) or not isinstance(data.get("proposals"),list): return jsonify({"error":"invalid_request"}),400
    state=os.environ["STATE_AUTHORITY_URL"].rstrip("/")
    try:
        result=model_review(data["message"],data["proposals"])
        token=id_token.fetch_id_token(AuthRequest(),state)
        saved=requests.post(f"{state}/v1/coverage-reviews",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},
          json={**result,"message":data["message"],"proposal_count":len(data["proposals"]),"source_reference":data.get("source_reference"),"model":MODEL},timeout=20)
        saved.raise_for_status()
    except (requests.RequestException,KeyError,ValueError,json.JSONDecodeError) as exc: return jsonify({"error":"coverage_review_failed","detail":type(exc).__name__}),502
    return jsonify(saved.json())
