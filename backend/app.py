from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/agent/observe", methods=["POST"])
def observe():
    data = request.json

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    resume = data.get("resumeText")
    job = data.get("jobDescription")

    if not resume or not job:
        return jsonify({"error": "resumeText and jobDescription are required"}), 400

    return jsonify({
        "message": "Observation received",
        "resumeLength": len(resume),
        "jobDescriptionLength": len(job)
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)