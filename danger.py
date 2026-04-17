from flask import Flask, request, render_template_string, send_file
import io
import pyzipper

app = Flask(__name__)

# Protobuf UID modifier (field 7 varint) – same as before
def modify_protobuf_uid(data, new_uid):
    result = bytearray()
    i = 0
    length = len(data)
    modified = False

    def encode_varint(value):
        out = bytearray()
        while True:
            b = value & 0x7F
            value >>= 7
            if value:
                out.append(b | 0x80)
            else:
                out.append(b)
                break
        return out

    while i < length:
        key = 0
        shift = 0
        while i < length:
            b = data[i]
            key |= (b & 0x7F) << shift
            i += 1
            shift += 7
            if not (b & 0x80):
                break

        field_num = key >> 3
        wire_type = key & 0x07

        if wire_type == 0:
            start_i = i
            val = 0
            shift = 0
            while i < length:
                b = data[i]
                val |= (b & 0x7F) << shift
                i += 1
                shift += 7
                if not (b & 0x80):
                    break
            varint_bytes = data[start_i:i]
            if field_num == 7 and not modified:
                new_varint = encode_varint(new_uid)
                result.extend(encode_varint(key))
                result.extend(new_varint)
                modified = True
            else:
                result.extend(encode_varint(key))
                result.extend(varint_bytes)
        elif wire_type == 2:
            length_val = 0
            shift = 0
            while i < length:
                b = data[i]
                length_val |= (b & 0x7F) << shift
                i += 1
                shift += 7
                if not (b & 0x80):
                    break
            payload = data[i:i+length_val]
            i += length_val
            result.extend(encode_varint(key))
            result.extend(encode_varint(length_val))
            result.extend(payload)
        elif wire_type == 1:
            result.extend(encode_varint(key))
            result.extend(data[i:i+8])
            i += 8
        elif wire_type == 5:
            result.extend(encode_varint(key))
            result.extend(data[i:i+4])
            i += 4
        else:
            result.extend(encode_varint(key))
            raise ValueError(f"Unsupported wire type {wire_type}")

    if not modified:
        result.extend(encode_varint((7 << 3) | 0))
        result.extend(encode_varint(new_uid))
    return bytes(result)


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Craftland Map UID Editor Advanced Tool</title>
<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Segoe UI', 'Poppins', sans-serif;
}

body {
  background: linear-gradient(135deg, #0a0f1e, #0a1a2f);
  color: #e0e0e0;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}

.container {
  width: 90%;
  max-width: 750px;
  background: rgba(18, 25, 45, 0.85);
  backdrop-filter: blur(12px);
  padding: 30px;
  border-radius: 28px;
  box-shadow: 0 20px 35px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(0, 255, 255, 0.2);
}

h2 {
  text-align: center;
  color: #4ff0ff;
  margin-bottom: 20px;
  font-weight: 600;
  letter-spacing: 1px;
  text-shadow: 0 0 8px rgba(0,255,255,0.3);
}

.drop-zone {
  border: 2px dashed #2c9cbc;
  padding: 20px;
  text-align: center;
  border-radius: 20px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: rgba(0,0,0,0.3);
}

.drop-zone.correct {
  border-color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
}

.filename {
  font-size: 12px;
  color: #4ade80;
  margin-top: 5px;
}

input[type="file"] {
  display: none;
}

input[type="text"], input[type="number"] {
  width: 100%;
  padding: 12px;
  border-radius: 14px;
  border: none;
  background: #0f172f;
  color: white;
  margin-bottom: 15px;
  font-size: 14px;
}

button {
  width: 100%;
  padding: 14px;
  background: linear-gradient(95deg, #2b6e9e, #1e4a76);
  border: none;
  border-radius: 40px;
  font-weight: bold;
  cursor: pointer;
  color: white;
  font-size: 16px;
  transition: 0.2s;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}

button:hover {
  background: linear-gradient(95deg, #3a86c0, #2a5a8e);
  transform: scale(1.01);
}

.loading {
  opacity: 0.7;
}

.error {
  background: rgba(255,0,0,0.15);
  color: #ff9999;
  padding: 10px;
  border-radius: 14px;
  margin-bottom: 15px;
  text-align: center;
}

.row {
  display: flex;
  gap: 12px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.row input {
  flex: 1;
  margin-bottom: 0;
}

.slot-selector {
  margin-bottom: 20px;
}

.slot-title {
  margin-bottom: 12px;
  font-weight: 500;
  color: #b0e0ff;
}

.slot-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.slot-btn {
  background: #1e2a3a;
  border: 1px solid #3a6ea5;
  color: #c0e0ff;
  padding: 8px 16px;
  border-radius: 40px;
  cursor: pointer;
  font-weight: bold;
  transition: 0.1s;
  width: auto;
  box-shadow: none;
}

.slot-btn.active {
  background: #2c6e9e;
  color: white;
  border-color: #4ff0ff;
  box-shadow: 0 0 6px #4ff0ff;
}

.slot-btn:hover {
  background: #2c6e9e;
  transform: none;
}

.hidden-input {
  display: none;
}

.password-zip-row {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  margin-bottom: 15px;
}

.password-zip-row input {
  flex: 1;
  margin-bottom: 0;
}
</style>
</head>
<body>
<div class="container">
<h2>🗺️ Craftland Map UID Editor Advanced Tool</h2>
<form method="POST" enctype="multipart/form-data" onsubmit="return handleUpload()">
<div class="drop-zone" id="bytes_zone">📁 Drop .bytes file here or click<input type="file" name="bytes_file" id="bytes_file" accept=".bytes" required><div id="bytes_name" class="filename"></div></div>
<div class="drop-zone" id="meta_zone">📄 Drop .meta file here or click<input type="file" name="meta_file" id="meta_file" accept=".meta" required><div id="meta_name" class="filename"></div></div>

<input type="number" id="uid" name="uid" placeholder="🔢 New UID (required)" required>

<div class="slot-selector">
<div class="slot-title">🎮 Select Slot Number (1-15) – default filename inside ZIP</div>
<div class="slot-buttons" id="slot-buttons"></div>
<input type="hidden" id="selected_slot" name="selected_slot" value="3">
</div>

<!-- Custom bytes & meta row - initially hidden -->
<div id="customNamesRow" class="row hidden-input">
<input type="text" id="bytes_custom" name="bytes_custom" placeholder="✏️ Custom .bytes name (optional)">
<input type="text" id="meta_custom" name="meta_custom" placeholder="✏️ Custom .meta name (optional)">
</div>

<!-- Password and ZIP name fields - initially hidden -->
<div id="passwordZipContainer" class="password-zip-row hidden-input">
<input type="text" id="password" name="password" placeholder="🔒 ZIP password (default: 123456)">
<input type="text" id="zipname" name="zipname" placeholder="📦 ZIP filename (default: Default.zip)">
</div>

<button id="btn" type="submit">⚡ Generate Protected ZIP</button>
</form>
<div id="error" class="error" style="display:none;"></div>
</div>

<script>
// Generate slot buttons 1-15
const slotContainer = document.getElementById('slot-buttons');
const selectedSlotInput = document.getElementById('selected_slot');
const customNamesRow = document.getElementById('customNamesRow');
const passwordZipContainer = document.getElementById('passwordZipContainer');
let activeSlot = 3;

function createSlotButtons() {
  for (let i = 1; i <= 15; i++) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'slot-btn';
    if (i === activeSlot) btn.classList.add('active');
    btn.innerText = i;
    btn.onclick = (function(slot) {
      return function() {
        document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        activeSlot = slot;
        selectedSlotInput.value = slot;
        // Show the optional input containers when a slot is clicked
        customNamesRow.classList.remove('hidden-input');
        passwordZipContainer.classList.remove('hidden-input');
      };
    })(i);
    slotContainer.appendChild(btn);
  }
}
createSlotButtons();

function setupDrop(zoneId, inputId, nameId, ext) {
    let zone = document.getElementById(zoneId);
    let input = document.getElementById(inputId);
    let nameBox = document.getElementById(nameId);
    zone.onclick = () => input.click();
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("correct"); };
    zone.ondragleave = () => zone.classList.remove("correct");
    zone.ondrop = (e) => {
        e.preventDefault();
        zone.classList.remove("correct");
        let file = e.dataTransfer.files[0];
        if (!file || !file.name.endsWith(ext)) {
            nameBox.innerText = "❌ Invalid file type";
            nameBox.style.color = "#f87171";
            return;
        }
        input.files = e.dataTransfer.files;
        nameBox.innerText = "✅ " + file.name;
        nameBox.style.color = "#4ade80";
    };
    input.onchange = () => {
        let file = input.files[0];
        if (!file || !file.name.endsWith(ext)) {
            nameBox.innerText = "❌ Invalid file type";
            nameBox.style.color = "#f87171";
            input.value = "";
            return;
        }
        nameBox.innerText = "✅ " + file.name;
        nameBox.style.color = "#4ade80";
    };
}
setupDrop("bytes_zone", "bytes_file", "bytes_name", ".bytes");
setupDrop("meta_zone", "meta_file", "meta_name", ".meta");

let uidInput = document.getElementById("uid");
uidInput.addEventListener("input", function() { this.value = this.value.replace(/[^0-9]/g, ""); });

function handleUpload() {
    let errorDiv = document.getElementById("error");
    errorDiv.style.display = "none";
    if (document.getElementById("bytes_file").files.length === 0) {
        errorDiv.innerText = "⚠️ Upload .bytes file";
        errorDiv.style.display = "block";
        return false;
    }
    if (document.getElementById("meta_file").files.length === 0) {
        errorDiv.innerText = "⚠️ Upload .meta file";
        errorDiv.style.display = "block";
        return false;
    }
    let uid = uidInput.value.trim();
    if (!uid) {
        errorDiv.innerText = "⚠️ Enter new UID";
        errorDiv.style.display = "block";
        return false;
    }
    let btn = document.getElementById("btn");
    btn.innerText = "⏳ Processing...";
    btn.classList.add("loading");
    setTimeout(() => { btn.innerText = "⚡ Generate Protected ZIP"; btn.classList.remove("loading"); }, 2000);
    return true;
}
</script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template_string(HTML)

    # POST handling
    if 'bytes_file' not in request.files or 'meta_file' not in request.files:
        return "Missing files", 400
    bytes_file = request.files['bytes_file']
    meta_file = request.files['meta_file']
    if bytes_file.filename == '' or meta_file.filename == '':
        return "No file selected", 400

    try:
        original_bytes = bytes_file.read()
        meta_data = meta_file.read()
        new_uid = int(request.form.get('uid', '').strip())
        password = request.form.get('password', '').strip()
        zipname = request.form.get('zipname', '').strip()

        if not password:
            password = "123456"
        if not zipname:
            zipname = "Default.zip"
        if not zipname.lower().endswith('.zip'):
            zipname += '.zip'

        selected_slot = request.form.get('selected_slot', '3').strip()
        try:
            slot = int(selected_slot)
            if slot < 1 or slot > 15:
                slot = 3
        except:
            slot = 3

        bytes_custom = request.form.get('bytes_custom', '').strip()
        meta_custom = request.form.get('meta_custom', '').strip()
        if not bytes_custom:
            bytes_custom = f'ProjectData_slot_{slot}.bytes'
        if not meta_custom:
            meta_custom = f'ProjectData_slot_{slot}.meta'
        if not bytes_custom.lower().endswith('.bytes'):
            bytes_custom += '.bytes'
        if not meta_custom.lower().endswith('.meta'):
            meta_custom += '.meta'

        modified_bytes = modify_protobuf_uid(original_bytes, new_uid)

        zip_buffer = io.BytesIO()
        with pyzipper.AESZipFile(zip_buffer, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode('utf-8'))
            zf.writestr(bytes_custom, modified_bytes)
            zf.writestr(meta_custom, meta_data)
        zip_buffer.seek(0)

        return send_file(zip_buffer, as_attachment=True, download_name=zipname, mimetype='application/zip')
    except Exception as e:
        return f"Error: {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
