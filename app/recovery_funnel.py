"""Short, mutually exclusive recovery journeys built into the bot's automatic messages."""
from __future__ import annotations
import copy

ACTION_LABELS = {'gift': 'Забрать подарок', 'connect': 'Подключить VPN', 'topup': 'Пополнить баланс'}
OWNED_BRANCHES = {'nodevice','online','unpaid','quality','gift','idle-setup','idle-topup','idle-return','late','terms-offer'}
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
