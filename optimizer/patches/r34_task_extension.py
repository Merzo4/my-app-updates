from pathlib import Path
import json, os
root=Path(os.environ['SOURCE_ROOT'])
p=root/'data'/'task_rules.json'
tasks=json.loads(p.read_text(encoding='utf-8-sig'))
existing={str(x.get('pattern','')).lower() for x in tasks}
extra=[
 (r'\\Microsoft\\Windows\\Work Folders\\','BALANCED','Можно отключать только если корпоративные Work Folders не используются.'),
 (r'\\Microsoft\\Windows\\Workplace Join\\','BALANCED','Не трогать на Entra ID/Azure AD/корпоративных ПК; на обычном локальном домашнем ПК это условный кандидат.'),
 (r'\\Microsoft\\Windows\\Bluetooth\\','BALANCED','Можно отключать Bluetooth-задачи только на ПК без Bluetooth-устройств и сценариев.'),
]
for pattern,risk,recommendation in extra:
    if pattern.lower() not in existing:
        tasks.append({'pattern':pattern,'risk':risk,'recommendation':recommendation})
        existing.add(pattern.lower())
p.write_text(json.dumps(tasks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('R34 task extension OK tasks=',len(tasks))
