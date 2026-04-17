#!/usr/bin/env bash
set -euo pipefail
ENDPOINT="${OPENAI_BASE_URL:-http://127.0.0.1:8000/v1}"
IMAGE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --endpoint) shift; ENDPOINT="$1" ;;
    --image) shift; IMAGE="$1" ;;
    -h|--help) echo "Usage: $0 [--endpoint URL] [--image REF]"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -z "$IMAGE" ] || echo "image=$IMAGE"
python3 - "$ENDPOINT" <<'PY'
import base64, io, json, sys, urllib.request
from PIL import Image, ImageDraw
endpoint=sys.argv[1].rstrip('/')
def post(path, payload, timeout=180):
    req=urllib.request.Request(endpoint+path, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','Authorization':'Bearer EMPTY'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())
print(urllib.request.urlopen(endpoint+'/models', timeout=30).status)
model='Qwen/Qwen3.6-35B-A3B'
text=post('/chat/completions', {'model': model, 'messages':[{'role':'user','content':'Say OK.'}], 'max_tokens':16, 'temperature':0})
print('text_ok', bool(text.get('choices')))
img=Image.new('RGB',(96,48),'white'); d=ImageDraw.Draw(img); d.text((10,15),'OK', fill='black')
buf=io.BytesIO(); img.save(buf, format='PNG')
b64=base64.b64encode(buf.getvalue()).decode()
mm=post('/chat/completions', {'model': model, 'messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,'+b64}},{'type':'text','text':'What text is shown?'}]}], 'max_tokens':32, 'temperature':0}, timeout=240)
print('image_text_ok', bool(mm.get('choices')))
PY
