from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, make_response

from transfer import FileTransfer, FileDownload

app = Flask(__name__)


def url_validator(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process_input", methods=["POST"])
def process_input():
    data = request.json
    user_input = data.get("user_input")
    if url_validator(user_input):
        transfer = FileTransfer(user_input)
        result = transfer.run()
    else:
        result = ["Not a valid url!"]
    return jsonify({"result": result})


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    user_input = data.get("user_input")
    user_ip = data.get("user_ip")
    if not user_ip:
        user_ip = request.remote_addr
    file_download = FileDownload(user_input, user_ip)
    result = file_download.download()
    return jsonify({"result": [result]})


if __name__ == "__main__":
    app.run(debug=True, port=8000)
