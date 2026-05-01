#!/usr/bin/env python3
"""
Deep condition QC — for each medical condition, generates a plan and checks
whether any returned meal ingredients are known to contradict that condition.
Reports: condition name, offending dish, offending ingredient.
"""
import json, requests, re
from base64 import b64encode

BASE = "http://185.143.103.106:8080/rest/s1/fit/dietPlan"
AUTH = b64encode(b"fit:Fit@2024").decode()
HEADERS = {"Content-Type": "application/json", "Authorization": f"Basic {AUTH}"}

# ── Ingredient-level rules per condition ─────────────────────────────────────
# Each entry: list of substring patterns (lowercase) that should NOT appear
# in ingredient names for that condition.
RULES = {
    "Cardiovascular Disease": [
        "butter","cream","lard","bacon","sausage","hot dog","salami","pepperoni",
        "full fat","whole milk","coconut oil","palm oil","trans fat",
    ],
    "Cardiovascular Diseases": [
        "butter","cream","lard","bacon","sausage","full fat","coconut oil","palm oil",
    ],
    "Celiac disease": [
        "wheat","barley","rye","spelt","semolina","bulgur","farro","triticale",
        "bread","pasta","flour","crouton","cracker","biscuit","soy sauce","malt",
    ],
    "Chronic Kidney Disease": [
        "potato","tomato","orange","banana","avocado","spinach","bran",
        "nuts","seeds","chocolate","dairy","cheese","milk","yogurt",
        "processed meat","bacon","ham","sausage","salt","sodium",
    ],
    "Diabetes": [
        "sugar","honey","syrup","candy","chocolate","juice","soda","cake",
        "cookie","white rice","white bread","pastry","jam","jelly",
    ],
    "Diabetes Mellitus": [
        "sugar","honey","syrup","candy","chocolate","juice","soda","cake",
        "cookie","white rice","white bread","pastry","jam","jelly",
    ],
    "Fatty Liver Disease": [
        "alcohol","beer","wine","butter","lard","bacon","sausage","full fat",
        "fried","sugar","syrup","honey","white bread","pastry",
    ],
    "Favism": [
        "fava bean","broad bean","legume","pea","lentil","bean","soy",
        "tonic water","quinine","blueberry","red wine",
    ],
    "GERD": [
        "tomato","orange","lemon","lime","grapefruit","pineapple","mint","spearmint",
        "peppermint","chocolate","coffee","alcohol","fried","fatty","spicy",
        "chili","pepper sauce","hot sauce","garlic","onion",
    ],
    "GERD (Acid Reflux)": [
        "tomato","orange","lemon","lime","grapefruit","pineapple","mint",
        "chocolate","coffee","fried","spicy","chili","garlic","onion",
    ],
    "Gout": [
        "anchovy","sardine","herring","mackerel","scallop","mussel","organ meat",
        "liver","kidney","sweetbread","red meat","alcohol","beer","yeast extract",
        "asparagus","spinach","cauliflower","mushroom",
    ],
    "Hemochromatosis": [
        "red meat","liver","organ","shellfish","oyster","vitamin c supplement",
        "iron supplement","fortified cereal","alcohol",
    ],
    "Histamine Intolerance": [
        "fermented","aged cheese","yogurt","sauerkraut","kimchi","vinegar",
        "pickled","wine","beer","alcohol","smoked","canned fish","tuna","sardine",
        "anchovy","avocado","tomato","spinach","eggplant","strawberry",
    ],
    "Hypercholesterolemia": [
        "butter","lard","coconut oil","palm oil","full fat","cream","egg yolk",
        "organ meat","liver","bacon","sausage","cheese","fried",
    ],
    "Hyperkalemia": [
        "banana","avocado","potato","sweet potato","tomato","orange","spinach",
        "beet","squash","dried fruit","nuts","seeds","dairy","milk","yogurt",
        "chocolate","bran","lentil","bean",
    ],
    "hyperkaliemia": [
        "banana","avocado","potato","sweet potato","tomato","orange","spinach",
        "beet","nuts","seeds","dairy","lentil","bean",
    ],
    "Hypertension": [
        "salt","sodium","soy sauce","pickle","canned","processed meat","bacon",
        "ham","sausage","cheese","butter","fried","fast food",
    ],
    "Hyperthyroidism": [
        "iodized salt","seaweed","kelp","nori","wakame","dairy","milk",
        "egg","seafood","caffeine","coffee","tea","energy drink",
    ],
    "Hypoglycemia": [
        "sugar","candy","soda","juice","syrup","honey","white bread","pastry",
        "cake","cookie","alcohol",
    ],
    "IBS": [
        "garlic","onion","wheat","rye","apple","pear","mango","watermelon",
        "honey","high fructose","lactose","milk","cream","ice cream","beans",
        "lentil","chickpea","cauliflower","broccoli","cabbage","mushroom",
    ],
    "Kidney Stones": [
        "spinach","beet","nuts","chocolate","tea","cola","soy","sweet potato",
        "rhubarb","wheat bran","sardine","anchovy","organ meat",
    ],
    "Lactose Intolerance": [
        "milk","cheese","butter","cream","yogurt","ice cream","whey","casein","lactose",
    ],
    "Mellitus": [
        "sugar","honey","syrup","candy","chocolate","white rice","white bread","pastry",
    ],
    "Nut allergy": [
        "almond","walnut","cashew","pistachio","pecan","hazelnut","macadamia",
        "brazil nut","pine nut","nut butter","peanut",
    ],
    "Oral Allergy Syndrome": [
        "apple","pear","peach","cherry","plum","apricot","strawberry","raspberry",
        "celery","carrot","potato","tomato","peanut","almond","hazelnut",
        "walnut","kiwi","banana","avocado","mango",
    ],
    "Pancreatitis": [
        "fried","fatty","butter","lard","cream","full fat","red meat","bacon",
        "sausage","alcohol","beer","wine","coconut oil","palm oil",
    ],
    "Phenylketonuria": [
        "aspartame","phenylalanine","diet soda","nutrasweet","equal",
        "protein powder","high protein","meat","fish","egg","cheese","milk",
        "bean","lentil","nut","soy",
    ],
    "Thyroid": [
        "soy","tofu","tempeh","edamame","broccoli","cabbage","cauliflower",
        "kale","brussels sprout","turnip","millet","cassava","iodized salt",
    ],
    "Thyroid Dysfunction": [
        "soy","tofu","tempeh","broccoli","cabbage","cauliflower","kale",
        "brussels sprout","iodized salt","seaweed","kelp",
    ],
    "Wilson's Disease": [
        "liver","organ meat","shellfish","oyster","mushroom","chocolate",
        "nuts","seeds","soy","whole grain","wheat germ","bean",
    ],
}
# Handle the Unicode apostrophe
RULES["Wilson\u2019s Disease"] = RULES.pop("Wilson's Disease", RULES.get("Wilson\u2019s Disease", []))

def generate(condition_ids=None, kcal=1800):
    payload = {
        "firstName": "Test", "lastName": "Client",
        "gender": "M", "age": 30, "dateOfBirth": "1995-01-15",
        "activityLevelTypeEnumId": "AltModeratelyActive",
        "dietaryTypeId": "Omnivore",
        "typeId": "Maintenance", "secondaryTypeId": "Default",
        "kilocalorieNeeded": kcal, "bmr": "1440", "lbm": "60",
        "height": 175, "weight": 80, "muscleMass": 35, "fatMass": 15,
        "conditionIdSet": condition_ids or [],
        "allergyIdSet": [], "conditionNote": "", "phone": "", "email": ""
    }
    r = requests.post(BASE + "/v3/generate", json=payload, headers=HEADERS, timeout=30)
    return r.json()

def get_all_ingredients(data):
    """Returns list of (category, dish_name, ingredient_name) tuples."""
    results = []
    fdm = data.get("foodDishByCategoryMap", {})
    for category, kcal_groups in fdm.items():
        if not isinstance(kcal_groups, dict):
            continue
        for kcal_key, classifications in kcal_groups.items():
            if not isinstance(classifications, dict):
                continue
            for classif, dishes in classifications.items():
                if not isinstance(dishes, list):
                    continue
                for dish in dishes:
                    dish_name = dish.get("foodDishName", "?")
                    for ing in dish.get("ingredientList", []):
                        ing_name = ing.get("ingredientName", "")
                        results.append((category, dish_name, ing_name))
    return results

def get_all_conditions():
    r = requests.get(BASE + "/condition", headers=HEADERS, timeout=15)
    return r.json()["conditionList"]

# ── Main ─────────────────────────────────────────────────────────────────────
print("Fetching conditions...")
conditions = get_all_conditions()
print(f"  {len(conditions)} conditions\n")

all_findings = []
clean_conditions = []

for cond in conditions:
    cid   = cond["conditionId"]
    cname = cond["conditionName"]
    
    rules = RULES.get(cname)
    if not rules:
        print(f"  [SKIP - no rules] {cname}")
        continue
    
    data = generate(condition_ids=[cid])
    if "errors" in data:
        print(f"  [API ERROR] {cname}: {data['errors'].strip()}")
        continue
    
    triples = get_all_ingredients(data)
    
    violations = []
    for category, dish_name, ing_name in triples:
        ing_lower = ing_name.lower()
        for bad in rules:
            if bad in ing_lower:
                violations.append({
                    "category": category,
                    "dish": dish_name,
                    "ingredient": ing_name,
                    "matched_rule": bad
                })
    
    # Deduplicate by (dish, ingredient, rule)
    seen = set()
    unique_violations = []
    for v in violations:
        key = (v["dish"], v["ingredient"], v["matched_rule"])
        if key not in seen:
            seen.add(key)
            unique_violations.append(v)
    
    if unique_violations:
        print(f"\n  ⚠  {cname} — {len(unique_violations)} potential violation(s):")
        for v in unique_violations:
            print(f"       [{v['category']}] Dish: \"{v['dish']}\"")
            print(f"         Ingredient: \"{v['ingredient']}\"  (matched: '{v['matched_rule']}')")
        all_findings.append({"condition": cname, "conditionId": cid, "violations": unique_violations})
    else:
        print(f"  ✓  {cname} — clean")
        clean_conditions.append(cname)

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"  Clean conditions ({len(clean_conditions)}): {', '.join(clean_conditions) or 'none'}")
print(f"\n  Conditions with potential violations: {len(all_findings)}")
for f in all_findings:
    print(f"\n  ── {f['condition']} ──")
    for v in f["violations"]:
        print(f"    [{v['category']}] \"{v['dish']}\" → ingredient: \"{v['ingredient']}\"")

with open("/tmp/qc_conditions_deep.json", "w") as fh:
    json.dump(all_findings, fh, indent=2, ensure_ascii=False)
print("\n  Full results saved to /tmp/qc_conditions_deep.json")
