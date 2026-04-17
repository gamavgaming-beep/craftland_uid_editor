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
/* SAME YOUR STYLE — NOT MODIFIED */
* {margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI','Poppins',sans-serif;}
body {background: radial-gradient(circle at 20% 30%, #0a0f2a, #030617);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px;}
.container {max-width:700px;width:100%;background:rgba(15,25,45,0.7);backdrop-filter:blur(12px);border-radius:32px;padding:30px;box-shadow:0 20px 40px rgba(0,0,0,0.5);}
h1 {text-align:center;font-size:28px;background:linear-gradient(135deg,#aaffff,#3b82f6);-webkit-background-clip:text;color:transparent;margin-bottom:8px;}
.sub {text-align:center;color:#8ba3c7;margin-bottom:30px;font-size:14px;}
.drop-zone {background:rgba(0,10,25,0.6);border:2px dashed #2c5f8a;border-radius:20px;padding:20px;text-align:center;margin-bottom:20px;cursor:pointer;}
.filename {font-size:13px;color:#6ee7b7;margin-top:8px;}
input,select {width:100%;padding:12px;background:#0f1a2e;border:1px solid #2d3a5e;border-radius:16px;color:white;margin-bottom:16px;}
.row {display:flex;gap:15px;}
.hidden {display:none;}
.btn {background:#2563eb;border:none;padding:14px;border-radius:40px;color:white;width:100%;}
</style>

</head>
<body>

<div class="container">
<h1>🏰 Craftland Map UID Editor</h1>
<div class="sub">Advanced Tool 🔧</div>

<form method="POST" enctype="multipart/form-data">

<div class="drop-zone">
📁 Upload .bytes
<input type="file" name="bytes_file" required>
</div>

<div class="drop-zone">
📄 Upload .meta
<input type="file" name="meta_file" required>
</div>

<!-- SLOT -->
<select id="slot_select">
<option value="">Custom / Keep original</option>
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

<!-- 🔥 TOGGLE CUSTOM INPUT -->
<div class="row hidden" id="custom_row">
<input type="text" name="bytes_custom" id="bytes_custom" placeholder="Custom bytes name">
<input type="text" name="meta_custom" id="meta_custom" placeholder="Custom meta name">
</div>

<input type="number" name="uid" placeholder="New UID" required>
<input type="text" name="password" value="1">
<input type="text" name="zipname" value="Gamav.zip">

<button class="btn">Generate ZIP</button>

</form>
</div>

<script>

// 🔥 TOGGLE LOGIC (MAIN FIX)
const slot = document.getElementById("slot_select");
const row = document.getElementById("custom_row");
const bytes = document.getElementById("bytes_custom");
const meta = document.getElementById("meta_custom");

slot.addEventListener("change", function(){
    if(this.value){
        row.classList.remove("hidden");

        bytes.value = `ProjectData_slot_${this.value}.bytes`;
        meta.value = `ProjectData_slot_${this.value}.meta`;

    } else {
        row.classList.add("hidden");
        bytes.value = "";
        meta.value = "";
    }
});

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
