"""Versioned webapp presentation; no executable code or billing configuration."""
import copy
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from app import db

WEBAPP = Path(__file__).resolve().parent.parent / 'webapp'
CATALOG = json.loads((WEBAPP / 'ui-catalog.json').read_text())
DEFAULT = {'theme': {}, 'texts': {}, 'blocks': [dict(id=b['id'], visible=True) for b in CATALOG['blocks']], 'custom': []}
COLORS = {'background','surface','text','muted','button','buttonText'}


def validate(value):
    if not isinstance(value, dict) or set(value)-set(DEFAULT):
        raise ValueError('Некорректный документ интерфейса')
    result = copy.deepcopy(DEFAULT)
    theme = value.get('theme', {})
    if not isinstance(theme,dict) or set(theme)-COLORS-{'radius'}:
        raise ValueError('Неизвестная настройка оформления')
    for key,color in theme.items():
        if key == 'radius':
            if type(color) is not int or not 8 <= color <= 40: raise ValueError('Скругление: от 8 до 40 px')
        elif not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):
            raise ValueError('Цвет должен быть в формате #RRGGBB')
    result['theme']=theme
    fields={f['key']:f for f in CATALOG['fields']}
    texts=value.get('texts',{})
    if not isinstance(texts,dict) or set(texts)-fields.keys(): raise ValueError('Неизвестное текстовое поле')
    for key,text in texts.items():
        limit=60 if fields[key]['kind']=='button' else 600
        if not isinstance(text,str) or not text.strip() or len(text)>limit: raise ValueError(f"{fields[key]['label']}: заполните текст, до {limit} символов")
    result['texts']=texts
    blocks=value.get('blocks',result['blocks'])
    if not isinstance(blocks,list) or len(blocks)!=len(CATALOG['blocks']): raise ValueError('Нужны все стандартные блоки')
    ids=[]
    for b in blocks:
        if not isinstance(b,dict) or set(b)!={'id','visible'} or not isinstance(b['id'],str) or type(b['visible']) is not bool: raise ValueError('Некорректный блок')
        ids.append(b['id'])
        if b['id']=='devicesBlock' and not b['visible']: raise ValueError('Нельзя скрыть устройства')
    if sorted(ids)!=sorted(b['id'] for b in CATALOG['blocks']): raise ValueError('Блоки не должны повторяться')
    result['blocks']=blocks
    custom=value.get('custom',[])
    if not isinstance(custom,list) or len(custom)>30: raise ValueError('Максимум 30 дополнительных блоков')
    ids=set()
    for b in custom:
        if not isinstance(b,dict) or set(b)-{'id','screen','type','title','text','label','action','url','visible'}: raise ValueError('Некорректный дополнительный блок')
        if not isinstance(b.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,60}',b['id']) or b['id'] in ids: raise ValueError('Некорректный ID блока')
        ids.add(b['id'])
        if not isinstance(b.get('screen'),str) or not isinstance(b.get('type'),str) or b.get('screen') not in {s['id'] for s in CATALOG['screens']} or b.get('type') not in {'text','card','button'}: raise ValueError('Выберите экран и тип блока')
        if type(b.get('visible')) is not bool: raise ValueError('Укажите видимость блока')
        for k,limit in [('title',120),('text',1200),('label',60),('url',1000)]:
            if not isinstance(b.get(k,''),str) or len(b.get(k,''))>limit: raise ValueError(f'Слишком длинное поле: {k}')
        if b['type']!='button' and not (b.get('title','').strip() or b.get('text','').strip()): raise ValueError('Добавьте заголовок или текст блока')
        if b['type']=='button' or b.get('label'):
            if not b.get('label','').strip() or not isinstance(b.get('action'),str) or b.get('action') not in {a['id'] for a in CATALOG['actions']}: raise ValueError('Укажите подпись и действие кнопки')
            if b['action']=='url':
                url=urlsplit(b.get('url',''))
                if url.scheme!='https' or not url.netloc or url.username or url.password: raise ValueError('Для ссылки нужен HTTPS-адрес без логина и пароля')
    result['custom']=custom
    return result


async def state():
    await db._pool_req().execute("INSERT INTO webapp_interface (id) VALUES (1) ON CONFLICT DO NOTHING")
    row=await db._pool_req().fetchrow('SELECT * FROM webapp_interface WHERE id=1')
    def doc(key):
        data=row[key]
        return (json.loads(data) if isinstance(data,str) else data) or copy.deepcopy(DEFAULT)
    return {'draft':doc('draft'),'published':doc('published'),'revision':row['revision'],'can_rollback':row['previous'] is not None,'catalog':CATALOG}


async def public():
    value=await db._pool_req().fetchval('SELECT published FROM webapp_interface WHERE id=1')
    value=json.loads(value) if isinstance(value,str) else value
    return {'config':value or copy.deepcopy(DEFAULT),'catalog':CATALOG}


async def change(body):
    if not isinstance(body,dict) or not isinstance(body.get('action'),str) or body.get('action') not in {'save','publish','rollback'} or type(body.get('revision')) is not int:
        raise ValueError('Некорректное действие редактора')
    action=body['action']
    document=validate(body.get('config')) if action!='rollback' else None
    async with db._pool_req().acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow('SELECT * FROM webapp_interface WHERE id=1 FOR UPDATE')
            if not row or row['revision']!=body['revision']: raise ValueError('Редактор изменён в другой вкладке. Перезагрузите страницу перед сохранением.')
            if action=='rollback':
                if row['previous'] is None: raise ValueError('Нет предыдущей публикации')
                await conn.execute('UPDATE webapp_interface SET published=previous,draft=previous,previous=published,revision=revision+1 WHERE id=1')
            elif action=='publish':
                await conn.execute('UPDATE webapp_interface SET previous=COALESCE(published,$2::jsonb),published=$1::jsonb,draft=$1::jsonb,revision=revision+1 WHERE id=1',json.dumps(document),json.dumps(DEFAULT))
            else:
                await conn.execute('UPDATE webapp_interface SET draft=$1::jsonb,revision=revision+1 WHERE id=1',json.dumps(document))
    return await state()
