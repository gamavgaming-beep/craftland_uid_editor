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
  position: relative;
  padding: 25px 20px;
  text-align: center;
  border-radius: 24px;
  margin-bottom: 25px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(0, 0, 0, 0.4);
  border: 2px solid transparent;
  background-clip: padding-box;
  box-shadow: 0 0 0 1px rgba(0, 255, 255, 0.2), 0 0 12px rgba(0, 200, 255, 0.1);
}

.drop-zone::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(45deg, #00c6ff, #0072ff, #00c6ff);
  border-radius: 26px;
  z-index: -1;
  opacity: 0;
  transition: opacity 0.4s ease;
}

.drop-zone:hover::before {
  opacity: 0.5;
}

.drop-zone.correct {
  border: 2px solid #4ade80;
  box-shadow: 0 0 20px rgba(74, 222, 128, 0.5), inset 0 0 10px rgba(74, 222, 128, 0.2);
  background: rgba(74, 222, 128, 0.05);
}

.drop-zone.wrong {
  border: 2px solid #f87171;
  box-shadow: 0 0 20px rgba(248, 113, 113, 0.4);
}

.filename {
  font-size: 13px;
  color: #4ade80;
  margin-top: 8px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

input[type="file"] {
  display: none;
}

input[type="text"], input[type="number"], select {
  width: 100%;
  padding: 12px;
  border-radius: 14px;
  border: none;
  background: #0f172f;
  color: white;
  margin-bottom: 15px;
  font-size: 14px;
}

select {
  cursor: pointer;
  appearance: none;
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>');
  background-repeat: no-repeat;
  background-position: right 12px center;
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

.hidden-input {
  display: none;
}

.password-zip-row {
  display: flex;
  gap: 12px;
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
<label style="display:block; margin-bottom:8px;">🎮 Slot Selection</label>
<select id="slot_select" name="slot_select">
  <option value="original">📁 Keep Original (use uploaded file names)</option>
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
</div>

<!-- Custom bytes & meta row - initially hidden (only shows when slot number selected) -->
<div id="customNamesRow" class="row hidden-input">
<input type="text" id="bytes_custom" name="bytes_custom" placeholder="✏️ Custom .bytes name (optional)">
<input type="text" id="meta_custom" name="meta_custom" placeholder="✏️ Custom .meta name (optional)">
</div>

<!-- Password and ZIP name fields - always visible -->
<div class="password-zip-row">
<input type="text" id="password" name="password" placeholder="🔒 ZIP password (default: 123456)">
<input type="text" id="zipname" name="zipname" placeholder="📦 ZIP filename (default: Default.zip)">
</div>

<button id="btn" type="submit">⚡ Generate Protected ZIP</button>
</form>
<div id="error" class="error" style="display:none;"></div>
</div>

<script>
const slotSelect = document.getElementById('slot_select');
const customNamesRow = document.getElementById('customNamesRow');
const bytesCustom = document.getElementById('bytes_custom');
const metaCustom = document.getElementById('meta_custom');

function updateCustomNamesRow() {
    const selected = slotSelect.value;
    if (selected === 'original') {
        customNamesRow.classList.add('hidden-input');
        bytesCustom.value = '';
        metaCustom.value = '';
    } else {
        customNamesRow.classList.remove('hidden-input');
        const slotNum = parseInt(selected, 10);
        if (!isNaN(slotNum)) {
            bytesCustom.value = `ProjectData_slot_${slotNum}.bytes`;
            metaCustom.value = `ProjectData_slot_${slotNum}.meta`;
        } else {
            bytesCustom.value = '';
            metaCustom.value = '';
        }
    }
}

slotSelect.addEventListener('change', updateCustomNamesRow);
updateCustomNamesRow();

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

        # Defaults if empty
        if not password:
            password = "123456"
        if not zipname:
            zipname = "Default.zip"
        if not zipname.lower().endswith('.zip'):
            zipname += '.zip'

        slot_select = request.form.get('slot_select', 'original')
        bytes_custom = request.form.get('bytes_custom', '').strip()
        meta_custom = request.form.get('meta_custom', '').strip()

        if slot_select == 'original':
            # Use original uploaded filenames
            bytes_name = bytes_file.filename
            meta_name = meta_file.filename
        else:
            try:
                slot = int(slot_select)
                if slot < 1 or slot > 15:
                    slot = 3
            except:
                slot = 3
            if bytes_custom:
                bytes_name = bytes_custom
            else:
                bytes_name = f'ProjectData_slot_{slot}.bytes'
            if meta_custom:
                meta_name = meta_custom
            else:
                meta_name = f'ProjectData_slot_{slot}.meta'
            # Ensure extensions
            if not bytes_name.lower().endswith('.bytes'):
                bytes_name += '.bytes'
            if not meta_name.lower().endswith('.meta'):
                meta_name += '.meta'

        # Modify UID
        modified_bytes = modify_protobuf_uid(original_bytes, new_uid)

        # Create password-protected ZIP
        zip_buffer = io.BytesIO()
        with pyzipper.AESZipFile(zip_buffer, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode('utf-8'))
            zf.writestr(bytes_name, modified_bytes)
            zf.writestr(meta_name, meta_data)
        zip_buffer.seek(0)

        return send_file(zip_buffer, as_attachment=True, download_name=zipname, mimetype='application/zip')
    except Exception as e:
        return f"Error: {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
