from flask import Flask, render_template, request, redirect, Response, stream_with_context, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import json, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import database
import searcher

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-me")
database.init_db()


# ── Helpers ──────────────────────────────────────────────────────

def current_user():
    uid = session.get("user_id")
    return database.get_user_by_id(uid) if uid else None


def is_authenticated():
    return bool(session.get("user_id"))


def is_guest():
    return session.get("guest", False) and not is_authenticated()


# ── Context processor ────────────────────────────────────────────

@app.context_processor
def inject_globals():
    user = current_user()
    uid = session.get("user_id")
    apps = database.all_applications(uid) if uid else []
    return {
        "panel_applications": apps,
        "current_user": user,
        "is_guest": is_guest(),
    }


# ── Auth routes ──────────────────────────────────────────────────

@app.route("/landing")
def landing():
    if is_authenticated() or is_guest():
        return redirect(url_for("index"))
    return render_template("landing.html")


@app.route("/guest", methods=["POST"])
def guest():
    session.clear()
    session["guest"] = True
    return redirect(url_for("index"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if is_authenticated():
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name", "").strip()
        password   = request.form.get("password", "")
        if not all([first_name, last_name, password]):
            error = "All fields are required."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        elif database.get_user_by_name(first_name, last_name):
            error = "An account with this name already exists."
        else:
            pw_hash = generate_password_hash(password)
            uid = database.create_user(first_name, last_name, pw_hash)
            session.clear()
            session["user_id"] = uid
            return redirect(url_for("index"))
    return render_template("auth.html", mode="signup", error=error)


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if is_authenticated():
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name", "").strip()
        password   = request.form.get("password", "")
        user = database.get_user_by_name(first_name, last_name)
        if not user:
            error = "No account found with this name."
        elif not check_password_hash(user["password_hash"], password):
            error = "Incorrect password."
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
    return render_template("auth.html", mode="signin", error=error)


@app.route("/signout")
def signout():
    session.clear()
    return redirect(url_for("landing"))


# ── Main app ─────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    if not is_authenticated() and not is_guest():
        return redirect(url_for("landing"))
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    if not is_authenticated() and not is_guest():
        return redirect(url_for("landing"))
    selected_titles = request.form.getlist("job_title")
    location = request.form.get("location", "").strip()
    skills = request.form.get("skills", "").strip()
    try:
        experience_years = int(request.form.get("experience_years", 0))
    except ValueError:
        experience_years = 0

    if not selected_titles:
        return render_template("index.html", error="Please select at least one job title.")

    uid = session.get("user_id")
    all_results, seen_urls, search_error, to_save = [], set(), None, []

    for job_title in selected_titles:
        cached = database.search_cached(job_title, location)
        for c in cached:
            c["from_cache"] = True
            if c["careers_url"] not in seen_urls:
                seen_urls.add(c["careers_url"])
                all_results.append(c)

        live = searcher.search_jobs(job_title, location, skills, experience_years)
        for r in live:
            if "error" in r:
                search_error = (search_error + " | " + r["error"]) if search_error else r["error"]
                continue
            if r["careers_url"] not in seen_urls:
                seen_urls.add(r["careers_url"])
                r["from_cache"] = False
                r["location"] = r.get("location") or location or "Not specified"
                all_results.append(r)
                to_save.append((r, job_title))

    for r, job_title in to_save:
        database.save_company(name=r["company_name"], careers_url=r["careers_url"],
                              job_titles=job_title, location=r.get("location", ""))

    for r in all_results:
        app_info = database.get_application(r["careers_url"], uid)
        if app_info:
            r["application"] = app_info

    return render_template("index.html", results=all_results, selected_titles=selected_titles,
                           location=location, skills=skills, experience_years=experience_years,
                           search_error=search_error)


@app.route("/search/stream", methods=["POST"])
def search_stream():
    if not is_authenticated() and not is_guest():
        return jsonify({"error": "unauthorized"}), 401

    selected_titles = request.form.getlist("job_title")
    location = request.form.get("location", "").strip()
    skills = request.form.get("skills", "").strip()
    try:
        experience_years = int(request.form.get("experience_years", 0))
    except ValueError:
        experience_years = 0
    uid = session.get("user_id")

    def generate():
        if not selected_titles:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Please select at least one job title.'})}\n\n"
            return

        seen_urls = set()

        for job_title in selected_titles:
            cached = database.search_cached(job_title, location)
            for c in cached:
                if c["careers_url"] not in seen_urls:
                    seen_urls.add(c["careers_url"])
                    c["from_cache"] = True
                    c["location"] = c.get("location") or location or "Not specified"
                    app_info = database.get_application(c["careers_url"], uid)
                    if app_info:
                        c["application"] = dict(app_info)
                    yield f"data: {json.dumps({'type': 'result', 'data': c})}\n\n"

            parts = [f'"{job_title}"']
            if location:
                parts.append(location)
            if skills:
                parts.append(skills)
            parts.append(searcher._experience_label(experience_years))
            parts.append("careers hiring")
            query = " ".join(parts)

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(searcher._search_ddg, query),
                    executor.submit(searcher._search_google, query),
                    executor.submit(searcher._search_linkedin, job_title, location, skills, experience_years),
                ]
                for future in as_completed(futures):
                    try:
                        results = future.result()
                    except Exception:
                        continue
                    for r in results:
                        if "error" in r:
                            yield f"data: {json.dumps({'type': 'warning', 'message': r['error']})}\n\n"
                            continue
                        if r["careers_url"] not in seen_urls:
                            seen_urls.add(r["careers_url"])
                            r["from_cache"] = False
                            r["location"] = r.get("location") or location or "Not specified"
                            database.save_company(name=r["company_name"], careers_url=r["careers_url"],
                                                  job_titles=job_title, location=r.get("location", ""))
                            app_info = database.get_application(r["careers_url"], uid)
                            if app_info:
                                r["application"] = dict(app_info)
                            yield f"data: {json.dumps({'type': 'result', 'data': r})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/companies")
def companies():
    if not is_authenticated() and not is_guest():
        return redirect(url_for("landing"))
    return render_template("index.html", all_companies=database.all_companies())


@app.route("/mark-applied", methods=["POST"])
def mark_applied():
    if not is_authenticated():
        return redirect(url_for("signin"))
    company_name = request.form.get("company_name", "").strip()
    careers_url  = request.form.get("careers_url", "").strip()
    position     = request.form.get("position", "").strip()
    uid = session.get("user_id")
    if company_name and position:
        database.mark_applied(company_name, careers_url, position, uid)
    return redirect(request.referrer or "/")


@app.route("/add-application", methods=["POST"])
def add_application():
    if not is_authenticated():
        return jsonify({"error": "Sign in to track applications."}), 401
    company_name = request.json.get("company_name", "").strip()
    careers_url  = request.json.get("careers_url", "").strip()
    position     = request.json.get("position", "").strip()
    uid = session.get("user_id")
    if not company_name or not position:
        return jsonify({"error": "Company name and position are required."}), 400
    existing = database.get_application_by_company(company_name, uid)
    if existing:
        return jsonify({"duplicate": True, "previous": existing})
    database.mark_applied(company_name, careers_url, position, uid)
    return jsonify({"success": True})


@app.route("/check-applied")
def check_applied():
    company_name = request.args.get("company_name", "").strip()
    careers_url  = request.args.get("careers_url", "").strip()
    uid = session.get("user_id")
    existing = None
    if careers_url:
        existing = database.get_application(careers_url, uid)
    if not existing and company_name:
        existing = database.get_application_by_company(company_name, uid)
    return jsonify({"duplicate": bool(existing), "previous": existing})


@app.route("/applications")
def applications():
    if not is_authenticated() and not is_guest():
        return redirect(url_for("landing"))
    uid = session.get("user_id")
    return render_template("index.html", all_applications=database.all_applications(uid))


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
