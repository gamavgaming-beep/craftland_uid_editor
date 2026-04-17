from flask import Flask, request, render_template_string, send_file
import io
import pyzipper

app = Flask(__name__)

# ---------------- UID MODIFY ----------------
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
                result.extend(encode_varint(key))
                result.extend(encode_varint(new_uid))
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

    if not modified:
        result.extend(encode_varint((7 << 3) | 0))
        result.extend(encode_varint(new_uid))

    return bytes(result)

# ---------------- HTML ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Craftland UID Tool</title>
<style>
body {background:#0a0f2a;color:white;font-family:sans-serif;padding:20px;}
.container {max-width:600px;margin:auto;}
input,select{width:100%;padding:10px;margin:10px 0;background:#111;border:1px solid #333;color:white;border-radius:10px;}
button{padding:12px;background:#2563eb;border:none;color:white;width:100%;border-radius:20px;}
.row{display:flex;gap:10px;}
.hidden{display:none;}
</style>
</head>
<body>
<div class="container">

<h2>Craftland UID Editor</h2>

<form method="POST" enctype="multipart/form-data">

<input type="file" name="bytes_file" required>
<input type="file" name="meta_file" required>

<select id="slot">
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

<div id="customRow" class="row hidden">
<input type="text" name="bytes_custom" id="bytes_custom" placeholder="bytes name">
<input type="text" name="meta_custom" id="meta_custom" placeholder="meta name">
</div>

<input type="number" name="uid" placeholder="Enter UID" required>
<input type="text" name="password" value="1">
<input type="text" name="zipname" value="Gamav.zip">

<button type="submit">Generate ZIP</button>

</form>
</div>

<script>
let slot = document.getElementById("slot");
let row = document.getElementById("customRow");
let bytes = document.getElementById("bytes_custom");
let meta = document.getElementById("meta_custom");

slot.addEventListener("change", function(){
    if(this.value){
        row.classList.remove("hidden");
        bytes.value = "ProjectData_slot_" + this.value + ".bytes";
        meta.value = "ProjectData_slot_" + this.value + ".meta";
    }else{
        row.classList.add("hidden");
        bytes.value="";
        meta.value="";
    }
});
</script>

</body>
</html>
"""

# ---------------- ROUTE ----------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template_string(HTML)

    bytes_file = request.files['bytes_file']
    meta_file = request.files['meta_file']

    original_bytes = bytes_file.read()
    meta_data = meta_file.read()

    new_uid = int(request.form['uid'])
    password = request.form.get('password', '1')
    zipname = request.form.get('zipname', 'Gamav.zip')

    bytes_custom = request.form.get('bytes_custom') or bytes_file.filename
    meta_custom = request.form.get('meta_custom') or meta_file.filename

    modified_bytes = modify_protobuf_uid(original_bytes, new_uid)

    zip_buffer = io.BytesIO()

    with pyzipper.AESZipFile(zip_buffer, 'w',
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES) as zf:

        zf.setpassword(password.encode())
        zf.writestr(bytes_custom, modified_bytes)
        zf.writestr(meta_custom, meta_data)

    zip_buffer.seek(0)

    return send_file(zip_buffer,
        as_attachment=True,
        download_name=zipname,
        mimetype='application/zip')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
