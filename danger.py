from flask import Flask, request, render_template_string, send_file
import io
import pyzipper

app = Flask(__name__)

# UID Modifier (same as your logic)
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


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UID Editor Pro</title>

<style>
body {
  margin:0;
  font-family: 'Poppins', sans-serif;
  background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
  height:100vh;
  display:flex;
  justify-content:center;
  align-items:center;
}

.card {
  width:95%;
  max-width:650px;
  padding:25px;
  border-radius:25px;
  background: rgba(255,255,255,0.05);
  backdrop-filter: blur(15px);
  box-shadow:0 10px 30px rgba(0,0,0,0.5);
}

h2 {
  text-align:center;
  color:#00eaff;
}

input, select {
  width:100%;
  padding:12px;
  margin-top:10px;
  border-radius:10px;
  border:none;
  background:#0d1b2a;
  color:white;
}

button {
  width:100%;
  padding:15px;
  margin-top:20px;
  border:none;
  border-radius:50px;
  background:linear-gradient(90deg,#00eaff,#007cf0);
  color:black;
  font-weight:bold;
  cursor:pointer;
}

.toggle {
  display:flex;
  justify-content:space-between;
  margin-top:15px;
  color:white;
}

.filebox {
  border:2px dashed #00eaff;
  padding:20px;
  margin-top:10px;
  text-align:center;
  border-radius:15px;
  cursor:pointer;
}
</style>
</head>

<body>

<div class="card">
<h2>🔥 UID Editor PRO</h2>

<form method="POST" enctype="multipart/form-data">

<div class="filebox">
<input type="file" name="bytes_file" required>
</div>

<div class="filebox">
<input type="file" name="meta_file" required>
</div>

<select name="slot" id="slot">
<option value="">Custom Name</option>
""" + "".join([f"<option>{i}</option>" for i in range(1,16)]) + """
</select>

<input name="bytes_custom" placeholder="Bytes name">
<input name="meta_custom" placeholder="Meta name">

<input name="uid" placeholder="Enter UID" required>

<div class="toggle">
<label>Password Default (123)</label>
<input type="checkbox" id="passToggle">
</div>

<input name="password" id="password" value="123">

<div class="toggle">
<label>Default ZIP Name</label>
<input type="checkbox" id="zipToggle">
</div>

<input name="zipname" id="zipname" value="gamav.zip">

<button>⚡ Generate ZIP</button>

</form>
</div>

<script>
let passToggle=document.getElementById("passToggle");
let zipToggle=document.getElementById("zipToggle");

passToggle.onclick=()=>{
 document.getElementById("password").value = passToggle.checked ? "123" : "";
}

zipToggle.onclick=()=>{
 document.getElementById("zipname").value = zipToggle.checked ? "gamav.zip" : "";
}
</script>

</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def home():
    if request.method=="GET":
        return HTML

    bytes_file=request.files["bytes_file"]
    meta_file=request.files["meta_file"]

    new_uid=int(request.form["uid"])
    password=request.form.get("password","123")
    zipname=request.form.get("zipname","gamav.zip")

    bytes_name=request.form.get("bytes_custom") or bytes_file.filename
    meta_name=request.form.get("meta_custom") or meta_file.filename

    modified=modify_protobuf_uid(bytes_file.read(),new_uid)

    mem=io.BytesIO()
    with pyzipper.AESZipFile(mem,'w',compression=pyzipper.ZIP_DEFLATED,encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode())
        zf.writestr(bytes_name,modified)
        zf.writestr(meta_name,meta_file.read())

    mem.seek(0)
    return send_file(mem,as_attachment=True,download_name=zipname)

app.run(host="0.0.0.0",port=5000)
