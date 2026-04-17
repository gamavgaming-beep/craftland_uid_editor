from flask import Flask, request, render_template_string, send_file
import io
import pyzipper

app = Flask(__name__)

# Protobuf UID modifier (field 7 varint)
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


# HTML Template with professional look and slot selector
HTML_TEMPLATE = """
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
  background: radial-gradient(circle at 20% 30%, #0a0f2a, #030617);
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.container {
  max-width: 700px;
  width: 100%;
  background: rgba(15, 25, 45, 0.7);
  backdrop-filter: blur(12px);
  border-radius: 32px;
  padding: 30px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(0, 255, 255, 0.1);
  transition: all 0.3s;
}

h1 {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #aaffff, #3b82f6);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 8px;
  letter-spacing: -0.3px;
}

.sub {
  text-align: center;
  color: #8ba3c7;
  margin-bottom: 30px;
  font-size: 14px;
  border-bottom: 1px dashed #2a3a5a;
  display: inline-block;
  width: auto;
  margin-left: auto;
  margin-right: auto;
  padding-bottom: 6px;
}

/* Drop zones */
.drop-zone {
  background: rgba(0, 10, 25, 0.6);
  border: 2px dashed #2c5f8a;
  border-radius: 20px;
  padding: 20px;
  text-align: center;
  margin-bottom: 20px;
  cursor: pointer;
  transition: 0.2s;
}
.drop-zone:hover {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}
.drop-zone.correct {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}
.filename {
  font-size: 13px;
  color: #6ee7b7;
  margin-top: 8px;
  word-break: break-all;
}

/* Inputs */
input, select {
  width: 100%;
  padding: 12px 16px;
  background: #0f1a2e;
  border: 1px solid #2d3a5e;
  border-radius: 16px;
  color: white;
  font-size: 14px;
  margin-bottom: 16px;
  transition: 0.2s;
}
input:focus, select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59,130,246,0.3);
}
.row {
  display: flex;
  gap: 15px;
  margin-bottom: 16px;
}
.row > div {
  flex: 1;
}
label {
  font-size: 12px;
  color: #9bb5d4;
  margin-bottom: 4px;
  display: block;
}
.btn {
  background: linear-gradient(95deg, #2563eb, #1e40af);
  border: none;
  padding: 14px;
  border-radius: 40px;
  font-weight: bold;
  font-size: 16px;
  color: white;
  cursor: pointer;
  transition: 0.2s;
  width: 100%;
  margin-top: 10px;
  box-shadow: 0 4px 12px rgba(37,99,235,0.3);
}
.btn:hover {
  transform: translateY(-2px);
  filter: brightness(1.05);
  box-shadow: 0 8px 20px rgba(37,99,235,0.4);
}
.loading {
  opacity: 0.7;
  transform: scale(0.98);
}
.error {
  background: rgba(220, 38, 38, 0.2);
  color: #fca5a5;
  padding: 12px;
  border-radius: 16px;
  text-align: center;
  margin-bottom: 16px;
  border-left: 3px solid #ef4444;
}
.slot-selector {
  background: #0a1120;
  border-radius: 24px;
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid #2a3f6e;
}
.slot-selector label {
  font-weight: 600;
  color: #60a5fa;
  margin-bottom: 8px;
}
select {
  background: #0f1a2e;
  cursor: pointer;
}
hr {
  border-color: #1e2f4a;
  margin: 20px 0;
}
</style>
</head>
<body>
<div class="container">
  <h1>🏰 Craftland Map UID Editor</h1>
  <div class="sub">Advanced Tool 🔧 | Password Protected ZIP</div>

  <form method="POST" enctype="multipart/form-data" onsubmit="return handleUpload()">
    <!-- Bytes & Meta drop zones -->
    <div class="drop-zone" id="bytes_zone">
      📁 Drop .bytes file or click
      <input type="file" name="bytes_file" id="bytes_file" accept=".bytes" required>
      <div id="bytes_name" class="filename"></div>
    </div>
    <div class="drop-zone" id="meta_zone">
      📄 Drop .meta file or click
      <input type="file" name="meta_file" id="meta_file" accept=".meta" required>
      <div id="meta_name" class="filename"></div>
    </div>

    <!-- Slot selector 1-15 -->
    <div class="slot-selector">
      <label>🎮 Slot Number (1–15):</label>
      <select id="slot_select">
        <option value="">-- Custom / Keep original names --</option>
        <option value="1">Slot 1</option>
        <option value="2">Slot 2</option>
        <option value="3">Slot 3</option>
        <option value="4">Slot 4</option>
        <option value="5">Slot 5</option>
        <option value="6">Slot 6</option>
        <option value="7">Slot 7</option>
        <option value="8">Slot 8</option>
        <option value="9">Slot 9</option>
        <option value="10">Slot 10</option>
        <option value="11">Slot 11</option>
        <option value="12">Slot 12</option>
        <option value="13">Slot 13</option>
        <option value="14">Slot 14</option>
        <option value="15">Slot 15</option>
      </select>
      <div style="font-size:12px; color:#7e9bc0; margin-top:6px;">Select slot → auto fills custom names below</div>
    </div>

    <!-- Custom names row -->
    <div class="row">
      <div>
        <label>Custom .bytes name (optional)</label>
        <input type="text" id="bytes_custom" name="bytes_custom" placeholder="e.g., my_map.bytes">
      </div>
      <div>
        <label>Custom .meta name (optional)</label>
        <input type="text" id="meta_custom" name="meta_custom" placeholder="e.g., my_map.meta">
      </div>
    </div>

    <!-- UID and ZIP settings -->
    <input type="number" id="uid" name="uid" placeholder="✨ New UID (required)" required>
    <input type="text" id="password" name="password" placeholder="🔐 ZIP password (default: 1)" value=">
    <input type="text" id="zipname" name="zipname" placeholder="📦 ZIP filename (default: Gamav.zip)" value=">

    <button class="btn" id="btn" type="submit">⚡ Generate Protected ZIP</button>
  </form>
  <div id="error" class="error" style="display:none;"></div>
</div>

<script>
// Setup drop zones
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
    nameBox.style.color = "#6ee7b7";
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
    nameBox.style.color = "#6ee7b7";
  };
}
setupDrop("bytes_zone", "bytes_file", "bytes_name", ".bytes");
setupDrop("meta_zone", "meta_file", "meta_name", ".meta");

// Slot selector -> auto fill custom names
const slotSelect = document.getElementById("slot_select");
const bytesCustom = document.getElementById("bytes_custom");
const metaCustom = document.getElementById("meta_custom");

slotSelect.addEventListener("change", function() {
  let val = this.value;
  if (val) {
    bytesCustom.value = `ProjectData_slot_${val}.bytes`;
    metaCustom.value = `ProjectData_slot_${val}.meta`;
  } else {
    // clear custom fields, user can type or keep original
    bytesCustom.value = "";
    metaCustom.value = "";
  }
});

// UID digits only
let uidInput = document.getElementById("uid");
uidInput.addEventListener("input", function() { this.value = this.value.replace(/[^0-9]/g, ""); });

// Validate before submit
function handleUpload() {
  let errorDiv = document.getElementById("error");
  errorDiv.style.display = "none";
  if (document.getElementById("bytes_file").files.length === 0) {
    errorDiv.innerText = "⚠️ Please upload a .bytes file";
    errorDiv.style.display = "block";
    return false;
  }
  if (document.getElementById("meta_file").files.length === 0) {
    errorDiv.innerText = "⚠️ Please upload a .meta file";
    errorDiv.style.display = "block";
    return false;
  }
  let uid = uidInput.value.trim();
  if (!uid) {
    errorDiv.innerText = "⚠️ Enter new UID (8-14 digits)";
    errorDiv.style.display = "block";
    return false;
  }
  let zipname = document.getElementById("zipname").value.trim();
  if (zipname && !zipname.toLowerCase().endsWith(".zip")) {
    errorDiv.innerText = "⚠️ ZIP filename must end with .zip";
    errorDiv.style.display = "block";
    return false;
  }
  let btn = document.getElementById("btn");
  btn.innerText = "⏳ Processing...";
  btn.classList.add("loading");
  setTimeout(() => { btn.innerText = "⚡ Generate Protected ZIP"; btn.classList.remove("loading"); }, 3000);
  return true;
}
</script>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template_string(HTML_TEMPLATE)

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
        password = request.form.get('password', '1').strip() or '1'
        zipname = request.form.get('zipname', 'Gamav.zip').strip()
        if not zipname:
            zipname = 'Gamav.zip'
        if not zipname.lower().endswith('.zip'):
            zipname += '.zip'

        # Custom names: if slot selected, those are auto-filled in form; else use original filenames
        bytes_custom = request.form.get('bytes_custom', '').strip()
        meta_custom = request.form.get('meta_custom', '').strip()
        if not bytes_custom:
            bytes_custom = bytes_file.filename
        if not meta_custom:
            meta_custom = meta_file.filename
        # Ensure extensions
        if not bytes_custom.lower().endswith('.bytes'):
            bytes_custom += '.bytes'
        if not meta_custom.lower().endswith('.meta'):
            meta_custom += '.meta'

        # Modify UID
        modified_bytes = modify_protobuf_uid(original_bytes, new_uid)

        # Create password-protected ZIP
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
