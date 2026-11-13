"""Short, mutually exclusive recovery journeys; no sending at migration time."""
from __future__ import annotations
import copy
import json

VERSION = 'recovery_journeys_v1'
LABEL_VERSION = 'funnel_action_labels_v2'
ACTION_LABELS = {'gift': 'Забрать подарок', 'connect': 'Подключить VPN', 'topup': 'Пополнить баланс'}
OWNED_BRANCHES = {'nodevice','online','unpaid','quality','gift','idle-setup','idle-topup','idle-return','late','terms-offer'}
OFFERS_VERSION = 'funnel_offers_v3'
PAID_EMPTY_VERSION = 'funnel_paid_empty_v1'
GIFT = 'claim_gift'
CONNECT = {'action': 'connect', 'text': 'Подключить VPN'}
PAID = """(COALESCE(u.has_paid_topup,FALSE)
 OR EXISTS (SELECT 1 FROM payments p WHERE p.telegram_id=u.telegram_id)
 OR EXISTS (SELECT 1 FROM pay_orders o WHERE o.telegram_id=u.telegram_id AND o.status='granted'))"""
DEVICE = "EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router')"
SEEN = "GREATEST(u.first_online_at,u.bot_started_at,(SELECT MAX(d.last_online_at) FROM devices d WHERE d.telegram_id=u.telegram_id))"
IDLE = f"({SEEN} <= NOW() - INTERVAL '7 days')"
# When a paying customer's access ran out: a day after the last daily charge. It moves only with a new charge,
# so every time the money runs out again the chain starts over.
EMPTY_AT = ("((SELECT MAX(d.last_billed_at) FROM devices d WHERE d.telegram_id=u.telegram_id "
            "AND COALESCE(d.kind,'') <> 'router') + INTERVAL '1 day')")
AUDIENCE = f"(u.first_online_at IS NULL OR NOT {PAID} OR {IDLE})"
CONDITIONS = (
 {'id':'recover_gift','label':'Подключение: подарок не забран','anchor':'u.bot_started_at','gate':'trial',
  'where':f"NOT {DEVICE} AND NOT {PAID} AND NOT COALESCE(u.trial_used,FALSE) AND u.first_online_at IS NULL",
  'hint':'Нет устройства, подарка и оплаты. После получения подарка человек выходит из этой ветки.'},
 {'id':'recover_setup','label':'Подключение: подарок или оплата уже есть','anchor':'COALESCE(u.gift_claimed_at,u.bot_started_at)',
  'where':f"NOT {DEVICE} AND (COALESCE(u.trial_used,FALSE) OR {PAID})",
  'hint':'Подарок или оплата есть, устройства нет. После добавления устройства ветка прекращается.'},
 {'id':'recover_online','label':'Подключение: устройство без онлайна',
  'anchor':"(SELECT MAX(d.created_at) FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router' AND d.last_online_at IS NULL)",
  'where':"EXISTS (SELECT 1 FROM devices d WHERE d.telegram_id=u.telegram_id AND COALESCE(d.kind,'') <> 'router' AND d.last_online_at IS NULL)",
  'hint':'Устройство добавлено, реальное подключение ещё не подтверждено.'},
 {'id':'recover_quality','label':'Первая оплата: пока действует доступ','anchor':'u.first_online_at',
  'where':f"u.first_online_at IS NOT NULL AND NOT {PAID} AND NOT {IDLE} AND NOT {{exhausted}} AND u.vpn_feedback_at IS NULL",
  'hint':'Доступ действует, оплаты ещё не было. Спрашиваем о качестве, не требуем оплатить.'},
 {'id':'recover_payment','label':'Первая оплата: доступ закончился','anchor':'u.first_online_at',
  'where':f"u.first_online_at IS NOT NULL AND NOT {PAID} AND NOT {IDLE} AND {{exhausted}}",
  'hint':'Пользовался VPN, доступ закончился, первой оплаты не было. Помощь и отказ от условий исключают отправку.'},
 {'id':'recover_topup','label':'Платил раньше: деньги кончились','anchor':EMPTY_AT,
  'where':f"{PAID} AND {DEVICE} AND {{exhausted}}",
  'hint':'Уже платил, устройство есть, баланс кончился и VPN выключен. Отсчёт — от момента, когда доступ закончился. '
         'Пополнение останавливает цепочку; когда деньги кончатся снова, она начнётся заново. Подарков здесь нет.'},
 {'id':'recover_idle','label':'Возврат: не пользовался неделю','anchor':SEEN,
  'where':f"u.first_online_at IS NOT NULL AND {IDLE} AND NOT ({PAID} AND {{exhausted}})",
  'hint':'Был подтверждённый онлайн, затем не пользовался VPN неделю (кроме платившего, у которого кончились деньги — для него своя ветка). Возобновление подключения или ответ «Пока не нужен» останавливают цепочку.'},
 {'id':'recover_late','label':'Возврат: не пользовался 30+ дней','anchor':SEEN,
  'where':f"u.first_online_at IS NOT NULL AND {SEEN} <= NOW() - INTERVAL '30 days'",
  'hint':'Был онлайн, потом пропал на месяц и дольше. Пауза считается от последнего появления. После возвращения цепочка начнётся заново при следующем уходе.'},
 {'id':'terms_offer','label':'Ответил «Не подошли условия»','anchor':'u.vpn_feedback_at',
  'where':"u.vpn_feedback='terms'",
  'hint':'Единственное сообщение, которое получают люди с ответом «Не подошли условия». После него человек снова попадает в обычную воронку.'},
)
KINDS = {c['id']: 'nudge_' + c['id'] for c in CONDITIONS}

# Third messages used to be polite goodbyes; now each one gives a reason to act.
OLD_THIRD = {
 'gift': 'Подарок остаётся у вас 🎁 Когда понадобится VPN, начните с кабинета.',
 'nodevice': 'VPN можно настроить, когда он понадобится. Если нужна помощь — напишите нам 👇',
 'online': 'Не будем отвлекать. Инструкция и помощь останутся в кабинете 👇',
 'unpaid': 'Если VPN снова понадобится, вернуться можно в любой момент. Кабинет и поддержка под рукой.',
 'idle-return': 'Не будем отвлекать 👋 Если VPN снова понадобится, кабинет и поддержка под рукой.',
}
GIFT_BRANCHES = {'unpaid', 'idle-return'}
NEW_THIRD = {
 'gift': '🎁 Подарок всё ещё ваш: бесплатный VPN на старте, без оплаты и привязки карты. '
         'Заберите его в один клик — с подключением поможем.',
 'nodevice': 'Подключение занимает пару минут: добавьте устройство, вставьте ссылку в приложение '
             'и включите VPN. Застряли на любом шаге — нажмите «Нужна помощь», ответим в чате.',
 'online': 'Устройство уже добавлено — осталось одно нажатие. Откройте его в кабинете и включите VPN '
           'в приложении. Не выходит — напишите нам, настроим вместе.',
 'unpaid': '🎁 <b>Дарим {gift_days} VPN</b>, чтобы вы спокойно попробовали ещё раз.\n\n'
           'Нажмите кнопку ниже — подарок сразу придёт на баланс. Действует 7 дней.',
 'idle-return': '🎁 <b>Возвращайтесь: дарим {gift_days} VPN.</b>\n\n'
                'Нажмите кнопку ниже — дни сразу придут на баланс, VPN заработает. Действует 7 дней.',
}
LATE_TEXTS = (
 '👋 Давно не виделись! Если VPN снова пригодится — <b>дарим {gift_days}</b>, чтобы начать без оплаты.\n\n'
 'Нажмите кнопку ниже, и дни сразу придут на баланс. Подарок действует 7 дней.',
 '🎁 Мы всё ещё на связи и VPN стал стабильнее. <b>Дарим {gift_days}</b>, чтобы проверить сами.\n\n'
 'Нажмите кнопку ниже — без оплаты, дни сразу на баланс. Действует 7 дней.',
)
TERMS_TEXT = ('Вы говорили, что условия не подошли. Давайте попробуем по-другому: '
              '<b>дарим {gift_days} VPN</b> — проверьте, стоит ли он своих денег.\n\n'
              'Нажмите кнопку ниже, дни сразу придут на баланс. Подарок действует 7 дней.')

def branches():
    from app.funnel_board import _step
    plans = [
      ('gift','recover_gift','Подарок → подключение',1,[
       '🎁 Ваш подарок ещё ждёт. Заберите его — сразу поможем подключить VPN.',
       'Поможем начать? Установите приложение, добавьте подписку и включите VPN. Если застряли — мы рядом.',
       NEW_THIRD['gift']
      ],['gift','menu','help']),
      ('nodevice','recover_setup','Подарок есть → добавить устройство',2,[
       'Давайте подключим устройство 👋 Откройте кабинет — там короткая инструкция.',
       'Что мешает подключиться? Нажмите «Нужна помощь» — разберёмся вместе.',
       NEW_THIRD['nodevice']
      ],['connect','menu','help']),
      ('online','recover_online','Устройство → работающий VPN',1,[
       'Осталось включить VPN 👋 Добавьте подписку в приложение и нажмите кнопку подключения.',
       'Не получилось подключиться? Напишите нам — поможем с настройкой.',
       NEW_THIRD['online']
      ],['connect','menu','help']),
      ('quality','recover_quality','Пробует VPN → обратная связь',20,[
       '💬 Как работает VPN? Если сайты не открываются или связь обрывается — поможем.',
       'Всё получилось с VPN? Можно ответить одной кнопкой 👇',
       'Если VPN не подошёл, расскажите почему. Это поможет нам стать лучше 👇'
      ],['cabinet','menu','feedback_ok','feedback_help','feedback_terms']),
      ('unpaid','recover_payment','Доступ закончился → первая оплата',0,[
       'Продолжим? Пополните баланс — VPN снова заработает 👇 Если были проблемы со связью, сначала поможем.',
       'Что мешает продолжить: подключение или условия? Подскажите — разберёмся 👇',
       NEW_THIRD['unpaid']
      ],['topup','menu','feedback_help','feedback_terms']),
      ('idle-return','recover_idle','Неделя без VPN → возвращение',168,[
       'Давно не пользовались VPN 👋 Что мешает вернуться?',
       'Если VPN подвёл — дайте нам помочь. Напишите, что не получилось 👇',
       NEW_THIRD['idle-return']
      ],['connect','menu','feedback_help','feedback_terms','feedback_later']),
    ]
    result = [{'id':bid,'title':title,'steps':[
      _step(f"recovery-{condition.replace('_', '-')}-{i+1}",condition,first if i==0 else 48 if i==1 else 72,
            text if i==2 and bid in GIFT_BRANCHES else text+'\n\nОткройте личный кабинет 👇',
            third_buttons(bid, buttons) if i==2 else
            [{'action':buttons[0],'text':ACTION_LABELS.get(buttons[0], 'Личный кабинет')}, *buttons[1:]],
            'anchor' if i==0 else 'previous')
      for i,text in enumerate(texts)]} for bid,condition,title,first,texts,buttons in plans]
    for branch in result:
        if branch['id'] == 'online':
            branch['steps'].insert(1, online_mid_step())
    return result + extra_branches() + paid_branches()


ONLINE_MID_ID = 'recovery-recover-online-mid'
ONLINE_MID_TEXT = ('Застряли на подключении? Откройте кабинет — там пошаговая инструкция для вашего приложения. '
                   'Обычно хватает добавить подписку и нажать кнопку подключения.\n\nНе выходит — нажмите «Нужна помощь», '
                   'ответим в чате.')


def online_mid_step():
    """Between the first-hour nudge and the two-day one: half a day after the device was added."""
    from app.funnel_board import _step
    return _step(ONLINE_MID_ID, 'recover_online', 11, ONLINE_MID_TEXT,
                 [{'action': 'connect', 'text': 'Подключить VPN'}, 'help', 'menu'], 'previous')


PAID_EMPTY_TEXTS = (
    '🔌 <b>VPN на паузе</b> — на балансе закончились деньги.\n\n'
    'Пополните от {min_topup}, и он включится сам: заново настраивать ничего не нужно.',
    'VPN всё ещё выключен 👋 Пополнение займёт минуту — после него всё заработает на тех же устройствах.',
    'Что-то не так с VPN? Если он работал плохо или не подошли условия — ответьте одной кнопкой, разберёмся.',
)


def paid_branches():
    from app.funnel_board import _step
    topup = {'action': 'topup', 'text': 'Пополнить баланс'}
    return [{'id': 'paid-empty', 'title': 'Платил, деньги кончились → пополнение', 'steps': [
        _step('recovery-recover-topup-1', 'recover_topup', 24, PAID_EMPTY_TEXTS[0], [topup, 'promise', 'menu']),
        _step('recovery-recover-topup-2', 'recover_topup', 48, PAID_EMPTY_TEXTS[1], [topup, 'promise', 'help'], 'previous'),
        _step('recovery-recover-topup-3', 'recover_topup', 96, PAID_EMPTY_TEXTS[2],
              [topup, 'feedback_help', 'feedback_terms', 'feedback_later'], 'previous'),
    ]}]


def add_paid_empty(graph):
    """The paid-customer branch, faster setup help and the half-day connection step for saved boards.
    Only defaults are touched: a step whose timing the admin changed keeps it."""
    result = copy.deepcopy(graph)
    used = {b['id'] for b in result['branches']} | {s['id'] for b in result['branches'] for s in b['steps']}
    for branch in result['branches']:
        ids = [s['id'] for s in branch['steps']]
        for step in branch['steps']:
            if step['id'] == 'recovery-recover-setup-1' and int(step.get('wait_hours') or 0) == 24:
                step['wait_hours'] = 2
        if 'recovery-recover-online-1' in ids and ONLINE_MID_ID not in used:
            branch['steps'].insert(ids.index('recovery-recover-online-1') + 1, online_mid_step())
            used.add(ONLINE_MID_ID)
    for branch in paid_branches():
        if branch['id'] in used or any(s['id'] in used for s in branch['steps']) or len(result['branches']) >= 32:
            continue
        result['branches'].insert(0, branch)
    return result


def third_buttons(bid, buttons):
    first = {'action':buttons[0],'text':ACTION_LABELS.get(buttons[0], 'Личный кабинет')}
    if bid in GIFT_BRANCHES:
        return [GIFT, first, *buttons[1:]][:6]
    return [first, *buttons[1:]]


def extra_branches():
    from app.funnel_board import _step
    return [
        {'id':'late','title':'Давно не пользовался: 30 и 60 дней','steps':[
            _step('recovery-recover-late-1','recover_late',720,LATE_TEXTS[0],[GIFT,CONNECT,'menu','feedback_later']),
            _step('recovery-recover-late-2','recover_late',1440,LATE_TEXTS[1],[GIFT,CONNECT,'menu','feedback_later']),
        ]},
        {'id':'terms-offer','title':'Не подошли условия → подарок','steps':[
            _step('recovery-terms-offer-1','terms_offer',168,TERMS_TEXT,[GIFT,CONNECT,'menu','help']),
        ]},
    ]

def upgrade(graph):
    result=copy.deepcopy(graph)
    preserved=[b for b in result['branches'] if b['id'] not in OWNED_BRANCHES]
    result['branches']=branches()+preserved
    return result

async def migrate(pool, graph):
    graph = await _migrate_journeys(pool, graph)
    graph = await _migrate_offers(pool, graph)
    return await _migrate_once(pool, graph, PAID_EMPTY_VERSION, add_paid_empty)


async def _migrate_once(pool, graph, version, change):
    from app.funnel_board import validate
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(73619429)')
            if await conn.fetchval('SELECT value FROM app_flags WHERE key=$1', version):
                return graph
            row = await conn.fetchrow('SELECT graph FROM funnel_graphs WHERE id=1 FOR UPDATE')
            raw = row['graph'] if row else graph
            if isinstance(raw, str):
                raw = json.loads(raw)
            updated = validate(change(raw))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2) ON CONFLICT DO NOTHING',
                               version + '_backup', json.dumps(raw, ensure_ascii=False))
            await conn.execute('UPDATE funnel_graphs SET graph=$1::jsonb,updated_at=NOW() WHERE id=1',
                               json.dumps(updated, ensure_ascii=False))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2)', version, '1')
            return updated


def refresh_offers(graph):
    """Offers instead of goodbyes, a faster gift reminder and the new branches.
    Only steps still holding the old default text or timing are touched; admin edits stay."""
    from app.funnel_board import _step
    result = copy.deepcopy(graph)
    fresh = {b['id']: b for b in branches()}
    for branch in result['branches']:
        bid = branch['id']
        if bid not in OLD_THIRD:
            continue
        for step in branch['steps']:
            if step['id'] == 'recovery-recover-gift-1' and int(step.get('wait_hours') or 0) == 24:
                step['wait_hours'] = 1
            if step['text'].strip() in {OLD_THIRD[bid], OLD_THIRD[bid] + '\n\nОткройте личный кабинет 👇'}:
                new = next((s for s in fresh[bid]['steps'] if s['id'] == step['id']), None)
                if new:
                    step['text'], step['buttons'] = new['text'], new['buttons']
    used = {b['id'] for b in result['branches']} | {s['id'] for b in result['branches'] for s in b['steps']}
    for branch in extra_branches():
        if branch['id'] in used or any(s['id'] in used for s in branch['steps']):
            continue
        if len(result['branches']) >= 32:
            break
        result['branches'].append(branch)
    return result


async def _migrate_offers(pool, graph):
    from app.funnel_board import validate
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(73619429)')
            if await conn.fetchval('SELECT value FROM app_flags WHERE key=$1', OFFERS_VERSION):
                return graph
            row = await conn.fetchrow('SELECT graph FROM funnel_graphs WHERE id=1 FOR UPDATE')
            raw = row['graph'] if row else graph
            if isinstance(raw, str):
                raw = json.loads(raw)
            updated = validate(refresh_offers(raw))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2) ON CONFLICT DO NOTHING',
                               OFFERS_VERSION + '_backup', json.dumps(raw, ensure_ascii=False))
            await conn.execute('UPDATE funnel_graphs SET graph=$1::jsonb,updated_at=NOW() WHERE id=1',
                               json.dumps(updated, ensure_ascii=False))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2)', OFFERS_VERSION, '1')
            return updated


async def _migrate_journeys(pool, graph):
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
                labels_done = await conn.fetchval('SELECT value FROM app_flags WHERE key=$1', LABEL_VERSION)
                if labels_done:
                    return validate(raw)
                updated = refresh_saved_graph(raw)
                await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2) ON CONFLICT DO NOTHING',
                                   LABEL_VERSION+'_backup', json.dumps(raw, ensure_ascii=False))
                await conn.execute('UPDATE funnel_graphs SET graph=$1::jsonb,updated_at=NOW() WHERE id=1',
                                   json.dumps(updated, ensure_ascii=False))
                await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2)', LABEL_VERSION, '1')
                return validate(updated)
            updated=validate(upgrade(raw))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2) ON CONFLICT DO NOTHING',
                VERSION+'_backup',json.dumps(raw,ensure_ascii=False))
            await conn.execute('UPDATE funnel_graphs SET graph=$1::jsonb,updated_at=NOW() WHERE id=1',json.dumps(updated,ensure_ascii=False))
            await conn.execute('INSERT INTO app_flags(key,value) VALUES ($1,$2)',VERSION,'1')
            return updated


def refresh_saved_graph(graph):
    """Update known defaults only; preserve custom copy, timing and delivery IDs."""
    from app.notices import (DEFAULT_NOTICES, BALANCE_PREVIOUS_DEFAULTS,
                            PREVIOUS_NOTICE_DEFAULTS, ENGAGEMENT_PREVIOUS_DEFAULTS)
    result = copy.deepcopy(graph)
    old_balance = {d.get('balance_ending_nudge') for d in
                   (BALANCE_PREVIOUS_DEFAULTS, PREVIOUS_NOTICE_DEFAULTS, ENGAGEMENT_PREVIOUS_DEFAULTS)}
    for branch in result['branches']:
        for step in branch['steps']:
            for button in step.get('buttons', []):
                if isinstance(button, dict) and button.get('text') == 'Личный кабинет' and button.get('action') in ACTION_LABELS:
                    button['text'] = ACTION_LABELS[button['action']]
            if step.get('condition') == 'balance_low' and step.get('text') in old_balance:
                step['text'] = DEFAULT_NOTICES['balance_ending_nudge']
    return result
