from flask import Flask, request, jsonify, send_file
import os
import zlib

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def modify_ecu(file_path, options):
    with open(file_path, "rb") as file:
        data = bytearray(file.read())
    
    if options.get("egrOff"):
        data = data.replace(b"\xF4\x01", b"\x00\x00")
    if options.get("dpfOff"):
        data = data.replace(b"\x20\x02", b"\x00\x00")
    if options.get("dtcOff"):
        dtc_patterns = [b"\x04\x01", b"\x13\x02", b"\x19\x84"]
        for pattern in dtc_patterns:
            data = data.replace(pattern, b"\x00\x00")
    
    checksum = zlib.crc32(data)
    data[-4:] = checksum.to_bytes(4, "big")
    
    output_path = os.path.join(PROCESSED_FOLDER, "modified_ecu.bin")
    with open(output_path, "wb") as file:
        file.write(data)
    
    return output_path

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Invalid file name"}), 400
    
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    options = {
        "egrOff": request.form.get("egrOff") == "true",
        "dpfOff": request.form.get("dpfOff") == "true",
        "dtcOff": request.form.get("dtcOff") == "true"
    }
    
    modified_path = modify_ecu(file_path, options)
    
    return jsonify({"downloadUrl": f"/api/download?file={modified_path}"})

@app.route("/api/download", methods=["GET"])
def download_file():
    file_path = request.args.get("file")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)