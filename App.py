# app.py
import os, math, json
from flask import Flask, request, render_template, jsonify
import pandas as pd

try:
    from sentence_transformers import SentenceTransformer, util
except Exception:
    SentenceTransformer = None
    util = None

app = Flask(__name__, static_folder="static", template_folder="templates")

RUBRIC_XLSX = "Case study for interns.xlsx"
RUBRIC_CSV = "rubric.csv"
EMBED_MODEL = "all-MiniLM-L6-v2"

def load_rubric():
    if os.path.exists(RUBRIC_XLSX):
        df = pd.read_excel(RUBRIC_XLSX)
    elif os.path.exists(RUBRIC_CSV):
        df = pd.read_csv(RUBRIC_CSV)
    else:
        raise FileNotFoundError("Rubric file missing.")
    df.columns = [c.strip() for c in df.columns]
    for col in ["criterion_id","criterion","description","keywords","weight","min_words","max_words"]:
        if col not in df.columns:
            df[col] = ""
    return df.fillna("").to_dict(orient="records")

_model = None
def ensure_model():
    global _model
    if SentenceTransformer is None:
        return None
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model

def compute_keyword_score(text_lower, keywords_str):
    if not keywords_str:
        return [], 0.0
    kws = [k.strip().lower() for k in str(keywords_str).replace(";",",").split(",") if k.strip()]
    found = [kw for kw in kws if kw in text_lower]
    frac = len(found)/len(kws) if kws else 0.0
    return found, round(frac,3)

def length_fraction(word_count, min_w, max_w):
    try:
        min_w = int(min_w) if min_w != "" else None
        max_w = int(max_w) if max_w != "" else None
    except:
        min_w, max_w = None, None
    if min_w is None and max_w is None:
        return 1.0
    if min_w and max_w and min_w <= word_count <= max_w:
        return 1.0
    if min_w and word_count < min_w:
        return max(0.0, word_count/(min_w*1.0))
    if max_w and word_count > max_w:
        return max(0.0, max_w/(word_count*1.0))
    return 0.0

def semantic_sim(text, target, model):
    if not model or not text or not target:
        return 0.0
    try:
        emb1 = model.encode(text, convert_to_tensor=True)
        emb2 = model.encode(target, convert_to_tensor=True)
        sim = util.cos_sim(emb1, emb2).item()
        return round(max(0.0, min(1.0, float(sim))),4)
    except:
        return 0.0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/score", methods=["POST"])
def api_score():
    data = request.json or {}
    transcript = data.get("transcript","")
    transcript_text = transcript.strip()
    transcript_lower = transcript_text.lower()
    word_count = len(transcript_text.split())
    try:
        rubric = load_rubric()
    except Exception as e:
        return jsonify({"error":str(e)}),400

    model = None
    try:
        model = ensure_model()
    except:
        model = None

    weights = [float(r.get("weight") or 1.0) for r in rubric]
    total_weight = sum(weights) if sum(weights)>0 else len(rubric)

    per=[]
    overall=0.0

    for r in rubric:
        crit = r.get("criterion") or r.get("criterion_id") or "criterion"
        desc = str(r.get("description") or "")
        keywords = r.get("keywords") or ""
        weight = float(r.get("weight") or 1.0)
        min_w = r.get("min_words") or ""
        max_w = r.get("max_words") or ""

        found_kws, kw_frac = compute_keyword_score(transcript_lower, keywords)
        len_frac = length_fraction(word_count, min_w, max_w)
        sem = semantic_sim(transcript_text, desc, model)

        raw = (0.5*sem)+(0.4*kw_frac)+(0.1*len_frac)
        crit_score = round(raw*100,2)

        per.append({
            "criterion":crit,
            "description":desc,
            "weight":weight,
            "found_keywords":found_kws,
            "keyword_fraction":kw_frac,
            "semantic_similarity":sem,
            "length_fraction":len_frac,
            "criterion_score":crit_score
        })

        overall += crit_score * (weight/total_weight)

    return jsonify({
        "overall_score":round(overall,2),
        "word_count":word_count,
        "per_criterion":per
    })

if __name__=="__main__":
    try: ensure_model()
    except: pass
    app.run(host="0.0.0.0",port=5000,debug=True)
