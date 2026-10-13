"""Short, mutually exclusive recovery journeys; no sending at migration time."""
from __future__ import annotations
import copy
import json

VERSION = 'recovery_journeys_v1'
OWNED_BRANCHES = {'nodevice','online','unpaid','quality','gift','idle-setup','idle-topup','idle-return'}
PAID = """(COALESCE(u.has_paid_topup,FALSE)
 OR EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id)
 OR EXISTS (SELECT 1 FROM rollypay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted'))"""
DEVICE = "EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router')"
SEEN = "GREATEST(u.first_online_at,u.bot_started_at,(SELECT MAX(d.last_online_at) FROM devices d WHERE d.telegram_id=u.telegram_id))"
IDLE = f"({SEEN} <= NOW() - INTERVAL '7 days')"
AUDIENCE = f"(u.first_online_at IS NULL OR NOT {PAID} OR {IDLE})"
CONDITIONS = (
 {'id':'recover_gift','label':'Подключение: подарок не забран','anchor':'u.bot_started_at','gate':'trial',
  'where':f"NOT {DEVICE} AND NOT {PAID} AND NOT COALESCE(u.trial_used,FALSE) AND u.first_online_at IS NULL",
  'hint':'Нет устройства, подарка и оплаты. После получения подарка человек выходит из этой ветки.'},
 {'id':'recover_setup','label':'Подключение: подарок или оплата уже есть','anchor':'COALESCE(u.gift_claimed_at,u.bot_started_at)',
  'where':f"NOT {DEVICE} AND (COALESCE(u.trial_used,FALSE) OR {PAID}) AND u.first_online_at IS NULL",
  'hint':'Подарок или оплата есть, устройства нет. После добавления устройства ветка прекращается.'},
 {'id':'recover_online','label':'Подключение: устройство без онлайна',
  'anchor':"(SELECT MIN(d.created_at) FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router')",
  'where':f"{DEVICE} AND u.first_online_at IS NULL",
  'hint':'Устройство добавлено, реальное подключение ещё не подтверждено.'},
 {'id':'recover_quality','label':'Первая оплата: пока действует доступ','anchor':'u.first_online_at',
  'where':f"u.first_online_at IS NOT NULL AND NOT {PAID} AND NOT {IDLE} AND NOT {{exhausted}} AND u.vpn_feedback_at IS NULL",
  'hint':'Доступ действует, оплаты ещё не было. Спрашиваем о качестве, не требуем оплатить.'},
 {'id':'recover_payment','label':'Первая оплата: доступ закончился','anchor':'u.first_online_at',
  'where':f"u.first_online_at IS NOT NULL AND NOT {PAID} AND NOT {IDLE} AND {{exhausted}}",
  'hint':'Пользовался VPN, доступ закончился, первой оплаты не было. Помощь и отказ от условий исключают отправку.'},
 {'id':'recover_idle','label':'Возврат: не пользовался неделю','anchor':SEEN,
  'where':f"u.first_online_at IS NOT NULL AND {IDLE}",
  'hint':'Был подтверждённый онлайн, затем не пользовался VPN неделю. Возобновление подключения или ответ «Пока не нужен» останавливают цепочку.'},
)
KINDS = {c['id']: 'nudge_' + c['id'] for c in CONDITIONS}

def branches():
    from app.funnel_board import _step
    plans = [
      ('gift','recover_gift','Подарок → подключение',24,[
       '🎁 Ваш подарок ещё ждёт. Заберите его — сразу поможем подключить VPN.',
       'Поможем начать? Установите приложение, добавьте подписку и включите VPN. Если застряли — мы рядом.',
       'Подарок остаётся у вас 🎁 Когда понадобится VPN, начните с кабинета.'
      ],['gift','menu','help']),
      ('nodevice','recover_setup','Подарок есть → добавить устройство',24,[
       'Давайте подключим устройство 👋 Откройте кабинет — там короткая инструкция.',
       'Что мешает подключиться? Нажмите «Нужна помощь» — разберёмся вместе.',
       'VPN можно настроить, когда он понадобится. Если нужна помощь — напишите нам 👇'
      ],['connect','menu','help']),
      ('online','recover_online','Устройство → работающий VPN',1,[
       'Осталось включить VPN 👋 Добавьте подписку в приложение и нажмите кнопку подключения.',
       'Не получилось подключиться? Напишите нам — поможем с настройкой.',
       'Не будем отвлекать. Инструкция и помощь останутся в кабинете 👇'
      ],['connect','menu','help']),
      ('quality','recover_quality','Пробует VPN → обратная связь',20,[
       '💬 Как работает VPN? Если сайты не открываются или связь обрывается — поможем.',
       'Всё получилось с VPN? Можно ответить одной кнопкой 👇',
       'Если VPN не подошёл, расскажите почему. Это поможет нам стать лучше 👇'
      ],['cabinet','menu','feedback_ok','feedback_help','feedback_terms']),
      ('unpaid','recover_payment','Доступ закончился → первая оплата',0,[
       'Продолжим? Пополните баланс — VPN снова заработает 👇 Если были проблемы со связью, сначала поможем.',
       'Что мешает продолжить: подключение или условия? Подскажите — разберёмся 👇',
       'Если VPN снова понадобится, вернуться можно в любой момент. Кабинет и поддержка под рукой.'
      ],['topup','menu','feedback_help','feedback_terms']),
      ('idle-return','recover_idle','Неделя без VPN → возвращение',168,[
       'Давно не пользовались VPN 👋 Что мешает вернуться?',
       'Если VPN подвёл — дайте нам помочь. Напишите, что не получилось 👇',
       'Не будем отвлекать 👋 Если VPN снова понадобится, кабинет и поддержка под рукой.'
      ],['connect','menu','feedback_help','feedback_terms','feedback_later']),
    ]
    return [{'id':bid,'title':title,'steps':[
      _step(f"recovery-{condition.replace('_', '-')}-{i+1}",condition,first if i==0 else 48 if i==1 else 72,
            text+'\n\nОткройте личный кабинет 👇',
            [{'action':buttons[0],'text':'Личный кабинет'}, *buttons[1:]],
            'anchor' if i==0 else 'previous')
      for i,text in enumerate(texts)]} for bid,condition,title,first,texts,buttons in plans]

def upgrade(graph):
    result=copy.deepcopy(graph)
    preserved=[b for b in result['branches'] if b['id'] not in OWNED_BRANCHES]
    result['branches']=branches()+preserved
    return result

async def migrate(pool, graph):
    """One atomic replacement, with an exact backup of the administrator's old map."""
    from app.funnel_board import validate
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(73619429)')
            migrated = await conn.fetchval('SELECT value FROM app_flags WHERE key=$1',VERSION)
            # Lock and reread so a concurrent administrator save is not overwritten by a stale map.
            row=await conn.fetchrow('SELECT graph FROM funnel_graphs WHERE id=1 FOR UPDATE')
            raw=row['graph'] if row else graph
            if isinstance(raw,str): raw=json.loads(raw)
            if migrated:
                return validate(raw)
            updated=validate(upgrade(raw))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2) ON CONFLICT DO NOTHING',
                VERSION+'_backup',json.dumps(raw,ensure_ascii=False))
            await conn.execute('UPDATE funnel_graphs SET graph=$1::jsonb,updated_at=NOW() WHERE id=1',json.dumps(updated,ensure_ascii=False))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2)',VERSION,'1')
            return updated
