from pathlib import Path
import json, os

root = Path(os.environ['SOURCE_ROOT'])
p = root / 'data' / 'update_settings.json'
data = json.loads(p.read_text(encoding='utf-8-sig'))
data['auto_check'] = True
data['auto_download'] = False
data['auto_install'] = False
data['installer_silent_args'] = '/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('R30 update policy fix: OK')
