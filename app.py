from flask import Flask, render_template, request, redirect
import database
import searcher

app = Flask(__name__)
database.init_db()


@app.context_processor
def inject_panel_applications():
    return {"panel_applications": database.all_applications()}


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    selected_titles = request.form.getlist("job_title")
    location = request.form.get("location", "").strip()
    skills = request.form.get("skills", "").strip()
    try:
        experience_years = int(request.form.get("experience_years", 0))
    except ValueError:
        experience_years = 0

    if not selected_titles:
        return render_template("index.html", error="Please select at least one job title.")

    all_results = []
    seen_urls = set()
    search_error = None
    to_save = []  # defer DB writes until after the full loop

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
                all_results.append(r)
                to_save.append((r, job_title))

    # Save new finds only after all titles have been searched
    for r, job_title in to_save:
        database.save_company(
            name=r["company_name"],
            careers_url=r["careers_url"],
            job_titles=job_title,
            location=location,
        )

    for r in all_results:
        app_info = database.get_application(r["careers_url"])
        if app_info:
            r["application"] = app_info

    return render_template(
        "index.html",
        results=all_results,
        selected_titles=selected_titles,
        location=location,
        skills=skills,
        experience_years=experience_years,
        search_error=search_error,
    )


@app.route("/companies")
def companies():
    all_c = database.all_companies()
    return render_template("index.html", all_companies=all_c)


@app.route("/mark-applied", methods=["POST"])
def mark_applied():
    company_name = request.form.get("company_name", "").strip()
    careers_url  = request.form.get("careers_url", "").strip()
    position     = request.form.get("position", "").strip()
    if company_name and careers_url and position:
        database.mark_applied(company_name, careers_url, position)
    return redirect("/applications")


@app.route("/applications")
def applications():
    apps = database.all_applications()
    return render_template("index.html", all_applications=apps)


if __name__ == "__main__":
    app.run(debug=True)
