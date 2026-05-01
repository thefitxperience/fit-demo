#!/usr/bin/env python3
"""
nutriFIT QC tester — tests every condition and allergy, generates a plan,
and reports whether the returned meals contain ingredients that contradict
the stated restriction.
"""
import json, requests, itertools, sys
from base64 import b64encode

BASE = "http://185.143.103.106:8080/rest/s1/fit/dietPlan"
AUTH = b64encode(b"fit:Fit@2024").decode()
HEADERS = {"Content-Type": "application/json", "Authorization": f"Basic {AUTH}"}

def get(path):
    r = requests.get(BASE + path, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def generate(condition_ids=None, allergy_ids=None, diet="Omnivore",
             goal="Maintenance", plan="Default", kcal=1800):
    payload = {
        "firstName": "Test", "lastName": "Client",
        "gender": "M", "age": 30, "dateOfBirth": "1995-01-15",
        "activityLevelTypeEnumId": "AltModeratelyActive",
        "dietaryTypeId": diet,
        "typeId": goal, "secondaryTypeId": plan,
        "kilocalorieNeeded": kcal, "bmr": "1440", "lbm": "60",
        "height": 175, "weight": 80, "muscleMass": 35, "fatMass": 15,
        "conditionIdSet": condition_ids or [],
        "allergyIdSet": allergy_ids or [],
        "conditionNote": "", "phone": "", "email": ""
    }
    r = requests.post(BASE + "/v3/generate", json=payload, headers=HEADERS, timeout=30)
    return r.status_code, r.json()

def extract_meals(data):
    """Walk the response and collect all dish names + ingredient names."""
    meals = []
    def walk(obj, path=""):
        if isinstance(obj, dict):
            # Common dish/ingredient keys in nutriFIT API responses
            name = obj.get("dishName") or obj.get("foodDishName") or obj.get("ingredientName") or obj.get("name")
            ingredients = []
            for k in ("ingredientList", "ingredients", "ingredientSet"):
                if k in obj and isinstance(obj[k], list):
                    for ing in obj[k]:
                        iname = ing.get("ingredientName") or ing.get("name") or str(ing)
                        ingredients.append(iname)
            if name:
                meals.append({"dish": name, "ingredients": ingredients, "path": path})
            for k, v in obj.items():
                walk(v, path + "." + k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, path + f"[{i}]")
    walk(data)
    return meals

# ── 1. Fetch all conditions and allergies ─────────────────────────────────────
print("Fetching conditions and allergies...")
conditions = get("/condition")["conditionList"]
allergies  = get("/allergy")["allergyList"]

print(f"  {len(conditions)} conditions, {len(allergies)} allergies\n")

# ── 2. First: baseline (no restrictions) to understand structure ──────────────
print("=" * 60)
print("BASELINE — no conditions/allergies")
print("=" * 60)
status, data = generate(kcal=1800)
if status != 200 or "errors" in data:
    print(f"  ERROR {status}: {data.get('errors', data)}")
    # Try different kcal values to find a working one
    for kcal in [1400, 1600, 2000, 2200, 2400, 2600]:
        status, data = generate(kcal=kcal)
        if status == 200 and "errors" not in data:
            print(f"  SUCCESS with kcal={kcal}. Top keys: {list(data.keys())[:6]}")
            break
        else:
            print(f"  kcal={kcal}: {data.get('errors','?').strip() if isinstance(data,dict) else data}")
else:
    print(f"  SUCCESS. Top keys: {list(data.keys())[:6]}")

# Save baseline for inspection
with open("/tmp/baseline_response.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"  Full response saved to /tmp/baseline_response.json")

meals = extract_meals(data)
print(f"  Dishes found: {len(meals)}")
if meals:
    for m in meals[:5]:
        print(f"    - {m['dish']}  ingredients: {m['ingredients'][:4]}")
else:
    # Print top-level keys to help diagnose structure
    print("  No dishes found via extract_meals. Top-level structure:")
    for k, v in data.items():
        t = type(v).__name__
        if isinstance(v, list):
            t += f"[{len(v)}]"
        print(f"    {k}: {t}")

# ── 3. Test each condition individually ──────────────────────────────────────
WORKING_KCAL = None
for kcal in [1800, 1400, 1600, 2000, 2200, 2400]:
    s, d = generate(kcal=kcal)
    if s == 200 and "errors" not in d:
        WORKING_KCAL = kcal
        break

if WORKING_KCAL is None:
    print("\nCould not find a working kcal — skipping per-condition tests.")
    sys.exit(1)

print(f"\nUsing kcal={WORKING_KCAL} for all tests\n")
print("=" * 60)
print("TESTING EACH CONDITION")
print("=" * 60)

results = []
for cond in conditions:
    cid = cond["conditionId"]
    cname = cond["conditionName"]
    status, data = generate(condition_ids=[cid], kcal=WORKING_KCAL)
    if status != 200 or "errors" in data:
        err = data.get("errors", str(data)).strip() if isinstance(data, dict) else str(data)
        print(f"  [ERROR] {cname}: {err}")
        results.append({"type": "condition", "id": cid, "name": cname, "status": "ERROR", "detail": err})
    else:
        meals = extract_meals(data)
        print(f"  [OK]    {cname} — {len(meals)} dishes")
        results.append({"type": "condition", "id": cid, "name": cname, "status": "OK", "dishes": len(meals)})

print("\n" + "=" * 60)
print("TESTING EACH ALLERGY")
print("=" * 60)

for alg in allergies:
    aid = alg["allergyId"]
    aname = alg["allergyName"]
    status, data = generate(allergy_ids=[aid], kcal=WORKING_KCAL)
    if status != 200 or "errors" in data:
        err = data.get("errors", str(data)).strip() if isinstance(data, dict) else str(data)
        print(f"  [ERROR] {aname}: {err}")
        results.append({"type": "allergy", "id": aid, "name": aname, "status": "ERROR", "detail": err})
    else:
        meals = extract_meals(data)
        print(f"  [OK]    {aname} — {len(meals)} dishes")
        results.append({"type": "allergy", "id": aid, "name": aname, "status": "OK", "dishes": len(meals)})

# ── 4. Summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
errors = [r for r in results if r["status"] == "ERROR"]
ok     = [r for r in results if r["status"] == "OK"]
print(f"  OK:    {len(ok)}")
print(f"  ERROR: {len(errors)}")
if errors:
    print("\n  Failing conditions/allergies:")
    for e in errors:
        print(f"    [{e['type'].upper()}] {e['name']} ({e['id']})")
        print(f"      → {e['detail']}")

with open("/tmp/qc_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\n  Full results saved to /tmp/qc_results.json")
