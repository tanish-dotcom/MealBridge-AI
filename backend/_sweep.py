import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000/api/v1"

RESULTS = []


def req(method, path, token=None, body=None, note=""):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            code = resp.status
            payload = resp.read().decode()
    except urllib.error.HTTPError as e:
        code = e.code
        payload = e.read().decode()
    except Exception as e:
        code = "ERR"
        payload = repr(e)
    ok = "OK " if code == 200 or (code == 201 and "create" in note) or (code in (200, 201, 204)) else "FAIL"
    RESULTS.append((ok, code, note or path))
    if code != 200 and code != 201 and code != 204:
        try:
            j = json.loads(payload)
            detail = j.get("detail", payload)
        except Exception:
            detail = payload[:400]
        RESULTS[-1] = (ok, code, f"{note or path} -> {detail[:300]}")
    return payload


def login(email, password):
    p = req("POST", "/auth/login", body={"email": email, "password": password}, note=f"login {email}")
    j = json.loads(p)
    return j.get("access_token") or j.get("token_pair", {}).get("access_token")


print("== health ==")
req("GET", "/health", note="health")

print("== logins ==")
admin_tok = login("admin@mealbridge.ai", "Admin@12345")
donor_tok = login("spice.junction@restaurant.demo", "Donor@12345")
ngo_tok = login("akshaya.trust@ngo.demo", "Ngo@12345")
print("logins ok")

print("== admin endpoints ==")
req("GET", "/admin/verifications/pending", admin_tok, note="admin verifications/pending")
req("GET", "/admin/dashboard/overview", admin_tok, note="admin dashboard/overview")
req("GET", "/admin/analytics/impact", admin_tok, note="admin analytics/impact")
admin_donations = req("GET", "/admin/restaurants", admin_tok, note="admin restaurants")
admin_donations = req("GET", "/admin/ngos", admin_tok, note="admin ngos")
admin_donations = req("GET", "/admin/donations", admin_tok, note="admin donations")

print("== donor endpoints ==")
req("GET", "/users/me", donor_tok, note="donor users/me")
req("GET", "/donations/mine", donor_tok, note="donor donations/mine (stats)")
req("GET", "/donations/mine/list", donor_tok, note="donor donations/mine/list")
req("GET", "/notifications", donor_tok, note="donor notifications")

donations = json.loads(admin_donations)
if donations:
    did = donations[0]["id"]
    req("GET", f"/donations/{did}", donor_tok, note=f"donor donations/{did}")
    req("GET", f"/donations/{did}/matches", donor_tok, note=f"donor donations/{did}/matches")
    req("GET", f"/donations/{did}/directions", donor_tok, note=f"donor donations/{did}/directions")

print("== ngo endpoints ==")
req("GET", "/users/me", ngo_tok, note="ngo users/me")
req("GET", "/ngo/dashboard/stats", ngo_tok, note="ngo dashboard/stats")
req("GET", "/ngo/available-donations", ngo_tok, note="ngo available-donations")
req("GET", "/ngo/accepted-donations", ngo_tok, note="ngo accepted-donations")
req("GET", "/notifications", ngo_tok, note="ngo notifications")

print()
print("== SUMMARY ==")
failed = 0
for ok, code, note in RESULTS:
    print(f"[{code}] {note}")
    if ok == "FAIL":
        failed += 1
print(f"\nTOTAL: {len(RESULTS)} calls, {failed} failures")
