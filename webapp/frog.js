// The living frog on the cabinet's home card (on/off and its A/B test: app/frog_test.py). Loaded by cab.js only when shown.
// A frog that lives on the hero card. The card is its field: it stays, wanders, hunts flies, sits on the balance,
// presses the button, catches coins, croaks, naps; its eyes follow flies, coins and your finger.
// The frog is a puppet made from a Kissed Frog emoji (make_puppet.py): our clips drive its legs, body, eyes, cheeks.
(() => {
  const SIZE = 64, FEET = 0.88, EYE = [0.566, 0.437], MOUTH = [0.245, 0.42], THROAT = [0.3, 0.6];
  const CL = { idle: [0, 180], hop: [180, 210], gulp: [210, 250], sleep: [250, 370], shock: [370, 400], blush: [400, 460],
    croak: [460, 520], wiggle: [520, 556], shiver: [556, 616], yawn: [616, 676], scratch: [676, 736], joy: [736, 766], peek: [766, 826] };
  const FPS = 60;
  const css = `
  .pet{position:absolute;inset:0;pointer-events:none;z-index:3;overflow:hidden;border-radius:inherit}
  .hc.haspet > .N,.hc.haspet > .P,.hc.haspet > .acts,.hc.haspet > .K{position:relative;z-index:2}
  :is(.pet,.petbg) .fr{position:absolute;left:0;top:0;width:${SIZE}px;height:${SIZE}px;margin:-${Math.round(SIZE * FEET)}px 0 0 -${SIZE / 2}px;pointer-events:auto;cursor:pointer;-webkit-tap-highlight-color:transparent;z-index:3;will-change:transform;transform-origin:50% ${FEET * 100}%}
  :is(.pet,.petbg) .fr .tl{position:absolute;inset:0;transform-origin:50% ${FEET * 100}%}
  :is(.pet,.petbg) .fr .bd{position:absolute;inset:0;transform-origin:50% ${FEET * 100}%}
  :is(.pet,.petbg) .fr .fc{position:absolute;inset:0}
  :is(.pet,.petbg) .fr.r .fc{transform:scaleX(-1)}
  :is(.pet,.petbg) .fr .fc svg{overflow:visible}
  :is(.pet,.petbg) .fr .cr{position:absolute;left:${THROAT[0] * 100}%;top:${THROAT[1] * 100}%;width:16px;height:13px;margin:-6px 0 0 -8px;border-radius:50%;
    background:radial-gradient(circle at 40% 35%,#fff,rgba(255,255,255,.75) 55%,rgba(255,220,235,.6));box-shadow:0 0 0 1px rgba(0,60,50,.25);transform:scale(0);pointer-events:none}
  :is(.pet,.petbg) .fr .mo{position:absolute;left:${MOUTH[0] * 100}%;top:${MOUTH[1] * 100}%;width:6px;height:5px;margin:-2.5px 0 0 -3px;border-radius:50%;background:#5b1030;transform:scale(0);pointer-events:none}
  :is(.pet,.petbg) .shd{position:absolute;left:0;top:0;width:30px;height:7px;margin:-4px 0 0 -15px;border-radius:50%;background:rgba(0,0,0,.22);filter:blur(1.2px);pointer-events:none;z-index:2;will-change:transform}
  :is(.pet,.petbg) .shd:after{content:"";position:absolute;left:8px;top:2px;width:14px;height:3.5px;border-radius:50%;background:rgba(0,0,0,.2)}
  :is(.pet,.petbg) .tg{position:absolute;height:3.2px;border-radius:2px;background:linear-gradient(#ff8fb0,#ff4f80);transform-origin:0 50%;z-index:4}
  :is(.pet,.petbg) .tg:after{content:"";position:absolute;right:-3.5px;top:-2.2px;width:7.5px;height:7.5px;border-radius:50%;background:#ff4f80}
  :is(.pet,.petbg) .bug{position:absolute;left:0;top:0;z-index:4;pointer-events:none;will-change:transform}
  :is(.pet,.petbg) .bug.fly{width:8px;height:6px;margin:-3px 0 0 -4px}
  :is(.pet,.petbg) .bug.fly:before{content:"";position:absolute;inset:0;border-radius:50%;background:#1b1b1f}
  :is(.pet,.petbg) .bug.fly i{position:absolute;top:-5px;width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.85);animation:pf-wg .05s linear infinite alternate}
  :is(.pet,.petbg) .bug.fly i:first-child{left:-2px}:is(.pet,.petbg) .bug.fly i:last-child{left:3px}
  :is(.pet,.petbg) .bug.dfly{width:22px;height:6px;margin:-3px 0 0 -11px}
  :is(.pet,.petbg) .bug.dfly:before{content:"";position:absolute;left:0;top:2px;width:22px;height:3px;border-radius:2px;background:linear-gradient(90deg,#1e6be0,#4fd1ff)}
  :is(.pet,.petbg) .bug.dfly i{position:absolute;top:-4px;left:6px;width:12px;height:5px;border-radius:50%;background:rgba(255,255,255,.7);transform-origin:50% 100%;animation:pf-wg2 .045s linear infinite alternate}
  :is(.pet,.petbg) .bug.dfly i:last-child{top:4px;transform-origin:50% 0}
  @keyframes pf-wg{to{transform:scaleY(.25) translateY(2px)}}
  @keyframes pf-wg2{to{transform:scaleY(.3)}}
  :is(.pet,.petbg) .bz{position:absolute;width:3px;height:3px;border-radius:50%;background:rgba(255,255,255,.55);pointer-events:none;z-index:3}
  :is(.pet,.petbg) .fx{position:absolute;left:0;top:0;pointer-events:none;z-index:5;font:700 12px/16px -apple-system,system-ui,sans-serif;letter-spacing:.1px;color:#1d3b30;
    background:rgba(255,255,255,.96);padding:2px 9px;border-radius:11px;white-space:nowrap;
    box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 3px 10px rgba(0,30,20,.16),0 1px 2px rgba(0,30,20,.12)}
  :is(.pet,.petbg) .fx:after{content:"";position:absolute;left:calc(50% + var(--tx,0px));bottom:-5px;width:10px;height:7px;margin-left:-5px;background:inherit;
    clip-path:path("M0 0H10C8 0 6 2 4 7C4 4 3 1 0 0Z");transform:scaleX(var(--tf,1))}
  :is(.pet,.petbg) .fx.sym{min-width:20px;padding:2px 6px;text-align:center;font-size:13px;font-weight:800}
  :is(.pet,.petbg) .fx.dots{padding:6px 9px}
  :is(.pet,.petbg) .fx.dots i{display:inline-block;width:4px;height:4px;margin:0 1.5px;border-radius:50%;background:#58756a;animation:pf-dt 1s ease-in-out infinite}
  :is(.pet,.petbg) .fx.dots i:nth-child(2){animation-delay:.15s}:is(.pet,.petbg) .fx.dots i:nth-child(3){animation-delay:.3s}
  @keyframes pf-dt{0%,60%,100%{transform:none;opacity:.45}30%{transform:translateY(-2px);opacity:1}}
  :is(.pet,.petbg) .fx.plain{background:none;box-shadow:none;padding:0;color:#fff;font-size:15px;line-height:1}:is(.pet,.petbg) .fx.plain:after{display:none}
  :is(.pet,.petbg) .fx.gold{background:linear-gradient(#ffe68a,#ffc53d);color:#6b3b00}
  :is(.pet,.petbg) .gt{position:absolute;width:16px;height:10px;margin:-10px 0 0 -8px;transform-origin:50% 100%;pointer-events:none;opacity:.5}
  :is(.pet,.petbg) .gt svg{display:block;transform-origin:50% 100%;animation:pf-sw 3.2s ease-in-out infinite}
  @keyframes pf-sw{50%{transform:rotate(7deg)}}
  .petbg{position:absolute;inset:0;pointer-events:none;z-index:0;overflow:hidden;border-radius:inherit}
  :is(.pet,.petbg) .hill{position:absolute;left:0}
  :is(.pet,.petbg) .sun{position:absolute;left:-60px;top:-70px;width:200px;height:200px;border-radius:50%;background:radial-gradient(circle,rgba(255,255,220,.45),rgba(255,255,220,.12) 45%,rgba(255,255,220,0) 70%);animation:pf-sun 6s ease-in-out infinite}
  @keyframes pf-sun{50%{transform:scale(1.08);opacity:.8}}
  :is(.pet,.petbg) .frost{position:absolute;inset:0;background:linear-gradient(180deg,rgba(220,240,255,.28),rgba(220,240,255,0) 45%)}
  :is(.pet,.petbg) .night{position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,8,38,.8),rgba(18,16,70,.5) 55%,rgba(20,20,70,.18))}
  :is(.pet,.petbg) .twi{position:absolute;inset:0;background:linear-gradient(180deg,rgba(28,24,92,.66),rgba(80,56,150,.42) 50%,rgba(170,90,170,.3) 80%,rgba(200,110,170,.08))}
  :is(.pet,.petbg) .sunset{position:absolute;inset:0;background:linear-gradient(180deg,rgba(104,46,150,.44),rgba(255,102,92,.42) 44%,rgba(255,176,88,.4) 70%,rgba(255,206,130,.12))}
  :is(.pet,.petbg) .sdisk{position:absolute;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;background:radial-gradient(circle,#fff7d6 0 28%,#ffc363 56%,#ff8a4c 74%,rgba(255,120,70,0) 76%);
    box-shadow:0 0 34px 14px rgba(255,150,80,.42);animation:pf-sun 7s ease-in-out infinite}
  :is(.pet,.petbg) .milky{position:absolute;left:-25%;top:-24px;width:150%;height:86px;transform:rotate(-14deg);background:radial-gradient(ellipse at 50% 50%,rgba(205,212,255,.16),rgba(205,212,255,.05) 45%,rgba(205,212,255,0) 70%)}
  :is(.pet,.petbg) .mw{position:absolute;left:24px;top:14px;width:22px;height:22px;border-radius:50%;box-shadow:0 0 16px 5px rgba(255,240,190,.32)}
  :is(.pet,.petbg) .moon{position:absolute;inset:0;border-radius:50%;overflow:hidden;
    background:radial-gradient(circle at 32% 38%,rgba(190,175,130,.55) 0 2.2px,transparent 2.6px),radial-gradient(circle at 64% 62%,rgba(190,175,130,.45) 0 3px,transparent 3.4px),radial-gradient(circle at 60% 28%,rgba(190,175,130,.35) 0 1.5px,transparent 1.9px),radial-gradient(circle at 40% 40%,#fffbe8,#f2e3ad)}
  :is(.pet,.petbg) .moon i{position:absolute;top:-1px;width:100%;height:calc(100% + 2px);border-radius:50%;background:rgba(14,16,54,.9)}
  :is(.pet,.petbg) .star{position:absolute;width:2px;height:2px;border-radius:50%;background:#fff;animation:pf-tw 2.4s ease-in-out infinite}
  :is(.pet,.petbg) .star.big{box-shadow:0 0 4px 1px rgba(220,230,255,.8)}
  :is(.pet,.petbg) .ovc{position:absolute;inset:0;background:linear-gradient(180deg,rgba(70,82,104,.3),rgba(70,82,104,.08) 70%,rgba(70,82,104,0))}
  :is(.pet,.petbg) .ovc.wet{background:linear-gradient(180deg,rgba(40,50,72,.48),rgba(40,50,72,.2) 70%,rgba(40,50,72,.08))}
  :is(.pet,.petbg) .haze{position:absolute;inset:0;background:linear-gradient(180deg,rgba(236,242,246,.14),rgba(236,242,246,.24) 70%,rgba(236,242,246,.1))}
  :is(.pet,.petbg) .rn{position:absolute;left:0;top:0;width:1.2px;height:10px;border-radius:1px;background:linear-gradient(rgba(220,235,255,0),rgba(220,235,255,.8));pointer-events:none}
  :is(.pet,.petbg) .spl{position:absolute;left:0;top:0;width:9px;height:3px;margin:-1.5px 0 0 -4.5px;border-radius:50%;border:1px solid rgba(235,245,255,.7);opacity:0;pointer-events:none}
  :is(.pet,.petbg) .fog{position:absolute;left:-30%;width:160%;height:36px;border-radius:50%;background:radial-gradient(ellipse at 50% 50%,rgba(255,255,255,.3),rgba(255,255,255,0) 70%);pointer-events:none}
  :is(.pet,.petbg) .brd{position:absolute;left:0;top:0;pointer-events:none}
  :is(.pet,.petbg) .brd svg{display:block;animation:pf-flap .5s ease-in-out infinite;transform-origin:50% 60%}
  @keyframes pf-flap{50%{transform:scaleY(.35)}}
  :is(.pet,.petbg) .pb{position:absolute;width:7px;height:4px;margin:-2px 0 0 -3.5px;border-radius:50% 50% 45% 45%;background:rgba(255,255,255,.32);box-shadow:inset -1px -1px 0 rgba(0,0,0,.1)}
  :is(.pet,.petbg) .msh{position:absolute;width:9px;height:9px;margin:-9px 0 0 -4.5px;pointer-events:none}
  :is(.pet,.petbg) .msh:before{content:"";position:absolute;left:0;top:0;width:9px;height:5px;border-radius:5px 5px 1px 1px;background:radial-gradient(circle at 30% 45%,#fff 0 1px,transparent 1.3px),radial-gradient(circle at 70% 40%,#fff 0 .9px,transparent 1.2px),#e8453c}
  :is(.pet,.petbg) .msh:after{content:"";position:absolute;left:3px;top:4.5px;width:3px;height:4.5px;border-radius:1px;background:#fff4e0}
  .petbg.dark .gt{opacity:.28}.petbg.dark .flw,.petbg.dark .pb,.petbg.dark .msh{filter:brightness(.55)}
  .petbg.windy .gt svg,.petbg.windy .flw,.petbg.windy .reed{animation-name:pf-sw2;animation-duration:1.1s}
  @keyframes pf-sw2{0%,100%{transform:rotate(-3deg)}50%{transform:rotate(17deg)}}
  :is(.pet,.petbg) .pond.warm{background:radial-gradient(ellipse at 50% 35%,rgba(255,214,166,.72),rgba(255,150,112,.5) 55%,rgba(168,86,140,.45))}
  :is(.pet,.petbg) .pond.dark{background:radial-gradient(ellipse at 50% 35%,rgba(130,150,210,.5),rgba(52,62,124,.52) 60%,rgba(28,30,82,.5))}
  @keyframes pf-tw{50%{opacity:.15;transform:scale(.6)}}
  :is(.pet,.petbg) .ffl{position:absolute;left:0;top:0;width:4px;height:4px;margin:-2px;border-radius:50%;background:#fff6a0;box-shadow:0 0 6px 2px rgba(255,240,120,.8);pointer-events:none;z-index:2;will-change:transform,opacity}
  :is(.pet,.petbg) .stone{position:absolute;width:26px;height:32px;overflow:hidden;pointer-events:none;z-index:2}
  :is(.pet,.petbg) .stone b{position:absolute;left:0;bottom:0;width:26px;height:30px;border-radius:13px 13px 3px 3px;background:linear-gradient(160deg,#dfe3ea,#9aa3b2);box-shadow:inset -3px -3px 0 rgba(0,0,0,.12);
    font:900 8px/1 system-ui;color:#5d6575;display:flex;align-items:center;justify-content:center;letter-spacing:.3px;transform:translateY(32px)}
  :is(.pet,.petbg) .xe{position:absolute;font:900 11px/1 system-ui;color:#3a1720;margin:-6px 0 0 -4px;pointer-events:none;display:none}
  :is(.pet,.petbg) .tng{position:absolute;left:${MOUTH[0] * 100 + 3}%;top:${MOUTH[1] * 100 + 2}%;width:5px;height:7px;border-radius:0 0 3px 3px;background:#ff6f91;pointer-events:none;display:none}
  :is(.pet,.petbg) .fr.dead .xe,:is(.pet,.petbg) .fr.dead .tng{display:block}
  :is(.pet,.petbg) .gh{position:absolute;left:0;top:0;width:${SIZE}px;height:${SIZE}px;margin:-${Math.round(SIZE * FEET)}px 0 0 -${SIZE / 2}px;pointer-events:none;z-index:4;opacity:0;filter:grayscale(1) brightness(1.7) drop-shadow(0 0 5px rgba(255,255,255,.9));will-change:transform,opacity}
  :is(.pet,.petbg) .gh svg{overflow:visible}
  .petbg:after{content:"";position:absolute;inset:0;border-radius:inherit;box-shadow:inset 0 1px 0 rgba(255,255,255,.3),inset 0 0 0 1px rgba(255,255,255,.06),inset 0 -30px 60px -30px rgba(0,0,0,.18)}
  :is(.pet,.petbg) .far,:is(.pet,.petbg) .mid{position:absolute;left:-12px;transition:translate .6s cubic-bezier(.2,.8,.3,1);-webkit-mask:linear-gradient(#000 45%,transparent 92%);mask:linear-gradient(#000 45%,transparent 92%)}
  :is(.pet,.petbg) .flw{position:absolute;width:6px;height:6px;margin:-6px 0 0 -3px;border-radius:50%;transform-origin:50% 140%;animation:pf-sw 3s ease-in-out infinite}
  :is(.pet,.petbg) .flw:before{content:"";position:absolute;left:2.5px;top:5px;width:1px;height:5px;background:rgba(255,255,255,.55)}
  :is(.pet,.petbg) .flw:after{content:"";position:absolute;left:1.5px;top:1.5px;width:3px;height:3px;border-radius:50%;background:#ffd84a}
  :is(.pet,.petbg) .rays{position:absolute;left:-150px;top:-150px;width:300px;height:300px;border-radius:50%;opacity:.5;
    background:repeating-conic-gradient(from 0deg,rgba(255,255,230,.16) 0 6deg,rgba(255,255,230,0) 6deg 18deg);-webkit-mask:radial-gradient(circle,#000 20%,transparent 68%);mask:radial-gradient(circle,#000 20%,transparent 68%);animation:pf-rot 60s linear infinite}
  @keyframes pf-rot{to{transform:rotate(360deg)}}
  :is(.pet,.petbg) .mist{position:absolute;left:0;right:0;height:26px;background:linear-gradient(180deg,rgba(255,255,255,0),rgba(255,255,255,.07) 40%,rgba(255,255,255,0));pointer-events:none}
  :is(.pet,.petbg) .pond{position:absolute;height:15px;border-radius:50%;background:radial-gradient(ellipse at 50% 35%,rgba(190,235,255,.6),rgba(110,190,240,.45) 55%,rgba(60,130,210,.4));box-shadow:inset 0 2px 0 rgba(255,255,255,.4),0 1px 0 rgba(255,255,255,.25)}
  :is(.pet,.petbg) .pond:after{content:"";position:absolute;left:18%;top:28%;width:22%;height:2px;border-radius:2px;background:rgba(255,255,255,.7);animation:pf-gl 3s ease-in-out infinite}
  @keyframes pf-gl{50%{transform:translateX(10px);opacity:.3}}
  :is(.pet,.petbg) .reed{position:absolute;width:2px;border-radius:1px;background:rgba(255,255,255,.55);transform-origin:50% 100%;animation:pf-sw 2.6s ease-in-out infinite}
  :is(.pet,.petbg) .reed:before{content:"";position:absolute;left:-2px;top:0;width:6px;height:10px;border-radius:3px;background:rgba(120,70,40,.75)}
  :is(.pet,.petbg) .lily{position:absolute;left:0;top:0;width:26px;height:8px;margin:-4px 0 0 -13px;border-radius:50%;z-index:2;pointer-events:none;
    background:conic-gradient(from 60deg,transparent 0 26deg,#5fcf73 26deg 360deg);box-shadow:inset 0 -2px 0 rgba(0,0,0,.18)}
  :is(.pet,.petbg) .lily i{position:absolute;left:4px;top:-5px;width:8px;height:8px;border-radius:50% 50% 50% 0;background:radial-gradient(circle at 50% 70%,#fff,#ffb3d1);transform:rotate(-45deg)}
  :is(.pet,.petbg) .cld{position:absolute;top:0;left:0;width:54px;height:16px;border-radius:10px;background:rgba(255,255,255,.28);filter:blur(.5px)}
  :is(.pet,.petbg) .cld:before,:is(.pet,.petbg) .cld:after{content:"";position:absolute;border-radius:50%;background:inherit}
  :is(.pet,.petbg) .cld:before{left:9px;top:-9px;width:22px;height:20px}:is(.pet,.petbg) .cld:after{left:24px;top:-6px;width:18px;height:16px}
  :is(.pet,.petbg) .dusk{position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,120,70,.32),rgba(255,160,90,.1) 55%,rgba(255,160,90,0))}
  :is(.pet,.petbg) .dawn{position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,190,220,.3),rgba(255,210,200,0) 60%)}
  :is(.pet,.petbg) .sun.low{left:auto;right:-50px;top:-40px;background:radial-gradient(circle,rgba(255,200,120,.55),rgba(255,170,90,.15) 45%,rgba(255,170,90,0) 70%)}
  :is(.pet,.petbg) .cf{position:absolute;left:0;top:0;width:6px;height:9px;margin:-4px;border-radius:1px;pointer-events:none;z-index:6}
  :is(.pet,.petbg) .note{position:absolute;left:0;top:0;font:900 13px/1 system-ui;color:#fff;pointer-events:none;z-index:5;text-shadow:0 1px 3px rgba(0,0,0,.25)}
  :is(.pet,.petbg) .diz{position:absolute;left:50%;top:-4px;width:30px;height:10px;margin-left:-15px;pointer-events:none;animation:pf-dz .6s linear infinite}
  :is(.pet,.petbg) .diz i{position:absolute;font-size:9px;line-height:1}
  @keyframes pf-dz{to{transform:rotate(360deg)}}
  :is(.pet,.petbg) .fr.glow .cr{transform:scale(.8)!important;background:radial-gradient(circle,#fffbd0,#ffe45c 60%,rgba(255,220,60,.6));box-shadow:0 0 12px 5px rgba(255,230,90,.85);animation:pf-gw .5s ease-in-out infinite alternate}
  @keyframes pf-gw{to{box-shadow:0 0 18px 8px rgba(255,230,90,.95)}}
  :is(.pet,.petbg) .fr.held{cursor:grabbing}
  :is(.pet,.petbg) .bub{position:absolute;left:0;top:0;width:5px;height:5px;margin:-2.5px;border-radius:50%;border:1px solid rgba(255,255,255,.85);pointer-events:none;z-index:4}
  :is(.pet,.petbg) .halo{position:absolute;left:50%;top:14%;width:22px;height:6px;margin-left:-11px;border-radius:50%;border:2px solid #ffe27a;box-shadow:0 0 6px rgba(255,226,122,.9);opacity:.95}
  :is(.pet,.petbg) .sn{position:absolute;left:0;top:0;width:4px;height:4px;margin:-2px;border-radius:50%;background:#fff;opacity:.8;pointer-events:none;z-index:1}
  :is(.pet,.petbg) .bug.bfly{width:16px;height:12px;margin:-6px 0 0 -8px}
  :is(.pet,.petbg) .bug.bfly i{position:absolute;top:0;width:8px;height:11px;border-radius:60% 40% 50% 50%;background:radial-gradient(circle at 40% 40%,#fff3a8,#ffb3d9 60%,#ff7ab8);transform-origin:100% 60%;animation:pf-fl .12s ease-in-out infinite alternate}
  :is(.pet,.petbg) .bug.bfly i:last-child{left:8px;transform-origin:0 60%;border-radius:40% 60% 50% 50%}
  :is(.pet,.petbg) .bug.bfly:before{content:"";position:absolute;left:7px;top:2px;width:2px;height:9px;border-radius:1px;background:#3a2340;z-index:1}
  :is(.pet,.petbg) .bug.bfly.sit i{animation-duration:.9s}
  @keyframes pf-fl{to{transform:scaleX(.2)}}
  :is(.pet,.petbg) .bug.sb{width:16px;height:16px;margin:-8px;border-radius:50%;background:radial-gradient(circle at 32% 30%,rgba(255,255,255,.95) 0 2px,rgba(255,255,255,.15) 3px),
    conic-gradient(from 40deg,rgba(255,170,220,.55),rgba(150,220,255,.55),rgba(190,255,190,.5),rgba(255,240,150,.55),rgba(255,170,220,.55));
    -webkit-mask:radial-gradient(circle,transparent 52%,#000 56%);mask:radial-gradient(circle,transparent 52%,#000 56%)}
  :is(.pet,.petbg) .bug.sb:after{content:"";position:absolute;inset:0;border-radius:50%;background:rgba(255,255,255,.12)}
  :is(.pet,.petbg) .fr.thr .cr{animation:pf-thr .9s ease-in-out infinite}
  @keyframes pf-thr{0%,100%{transform:scale(0)}50%{transform:scale(.42)}}
  :is(.pet,.petbg) .coin{position:absolute;left:0;top:0;width:18px;height:18px;margin:-9px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fff6c4,#ffd23f 45%,#d99a0b);box-shadow:inset 0 -2px 0 rgba(0,0,0,.18),0 0 10px rgba(255,220,90,.6);z-index:4;font:900 11px/18px system-ui;text-align:center;color:#9a5b00}
  :is(.pet,.petbg) .zz{position:absolute;font:900 11px/1 system-ui;color:#fff;pointer-events:none;z-index:4;text-shadow:0 1px 2px rgba(0,0,0,.25)}
  :is(.pet,.petbg) .pd{position:absolute;left:0;top:0;height:9px;margin-top:-4.5px;border-radius:50%;background:radial-gradient(ellipse at 50% 40%,rgba(200,235,255,.85),rgba(120,190,255,.5) 60%,rgba(120,190,255,0) 72%);z-index:1;pointer-events:none}
  :is(.pet,.petbg) .rp{position:absolute;width:30px;height:8px;margin:-4px 0 0 -15px;border-radius:50%;border:1.5px solid rgba(255,255,255,.75);pointer-events:none;z-index:2}
  :is(.pet,.petbg) .dr{position:absolute;width:3px;height:6px;border-radius:2px;background:rgba(210,240,255,.95);pointer-events:none;z-index:4}
  :is(.pet,.petbg) .cl{position:absolute;left:0;top:0;width:44px;height:18px;margin:-9px 0 0 -22px;border-radius:12px;background:#fff;box-shadow:12px -6px 0 -2px #fff,-10px -4px 0 -4px #fff;opacity:.95;z-index:4;pointer-events:none}
  :is(.pet,.petbg) .puff{position:absolute;width:7px;height:7px;margin:-3.5px;border-radius:50%;background:rgba(255,255,255,.8);pointer-events:none;z-index:2}
  :is(.pet,.petbg) .spk{position:absolute;width:9px;height:9px;margin:-4.5px;pointer-events:none;z-index:5;background:#fff;clip-path:polygon(50% 0,62% 38%,100% 50%,62% 62%,50% 100%,38% 62%,0 50%,38% 38%)}
  :is(.pet,.petbg) .ht{position:absolute;font-size:12px;pointer-events:none;z-index:5}
  :is(.pet,.petbg) .leaf{position:absolute;left:0;top:0;width:13px;height:8px;margin:-4px 0 0 -6.5px;border-radius:0 85% 0 85%;background:linear-gradient(135deg,#ffd45c,#ff8a3d);box-shadow:inset 0 0 0 .5px rgba(120,50,0,.25);pointer-events:none;z-index:5;will-change:transform}
  :is(.pet,.petbg) .bal{position:absolute;left:0;top:0;width:22px;height:27px;margin:-14px 0 0 -11px;border-radius:50% 50% 48% 48%/55% 55% 45% 45%;background:radial-gradient(circle at 34% 30%,rgba(255,255,255,.7) 0 3px,rgba(255,255,255,0) 4px),var(--c,#ff5d7a);box-shadow:inset -3px -4px 0 rgba(0,0,0,.12);z-index:5;pointer-events:none;will-change:transform}
  :is(.pet,.petbg) .bal:before{content:"";position:absolute;left:9px;bottom:-3px;width:4px;height:4px;background:var(--c,#ff5d7a);clip-path:polygon(50% 0,100% 100%,0 100%)}
  :is(.pet,.petbg) .bal:after{content:"";position:absolute;left:10.5px;top:27px;width:1px;height:34px;background:rgba(255,255,255,.85)}
  :is(.pet,.petbg) .ssr{position:absolute;left:0;top:0;width:46px;height:2px;margin:-1px 0 0 -46px;border-radius:2px;background:linear-gradient(90deg,rgba(255,255,255,0),#fff);box-shadow:0 0 6px rgba(255,255,230,.9);transform-origin:100% 50%;pointer-events:none;z-index:1}
  :is(.pet,.petbg) .rbw{position:absolute;width:220px;height:110px;border-radius:110px 110px 0 0;pointer-events:none;opacity:0;
    background:radial-gradient(circle at 50% 100%,rgba(255,255,255,0) 55%,rgba(255,90,90,.32) 56% 61%,rgba(255,200,60,.32) 61% 66%,rgba(90,220,120,.32) 66% 71%,rgba(80,160,255,.32) 71% 76%,rgba(255,255,255,0) 77%);
    -webkit-mask:linear-gradient(#000 60%,transparent);mask:linear-gradient(#000 60%,transparent)}
  `;
  if (!document.getElementById("petcss9")) { const s = document.createElement("style"); s.id = "petcss9"; s.textContent = css; document.head.appendChild(s); }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const rnd = (a, b) => a + Math.random() * (b - a);
  const pick = (xs) => xs[Math.floor(Math.random() * xs.length)];
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ease = (t) => t < .5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
  const raf = () => new Promise((r) => requestAnimationFrame(r));
  // how many 60 Hz frames went by since `last` (1 at 60 Hz, ~0.43 at 140 Hz): motion keeps its speed on any screen
  const frames = (last, now = performance.now()) => Math.min(3, Math.max(0, (now - last) / (1000 / 60)));
  const lib = () => window.lottie ? Promise.resolve(window.lottie) : new Promise((ok) => { const s = document.createElement("script"); s.src = "/icons/lottie-light.min.js"; s.onload = () => ok(window.lottie); document.head.appendChild(s); });
  const add = (st, cls, html = "") => { const e = document.createElement("div"); e.className = cls; e.innerHTML = html; st.layer.appendChild(e); return e; };
  const at = (e, x, y, extra = "") => { e.style.transform = `translate(${x}px,${y}px) ${extra}`; };

  // a speech bubble over the frog: frog sounds and a few symbols; «…» is three bouncing dots; the tail always points at the speaker
  const pop = (st, x, y, text, { ms, size, kind, side = 0 } = {}) => {
    if (!text) return;
    const emo = /^\p{Extended_Pictographic}+$/u.test(text), dots = text === "…", sym = !emo && !dots && text.length <= 3 && !/[а-яa-z]{2}/i.test(text);
    const f = add(st, "fx" + (kind ? " " + kind : emo ? " plain" : dots ? " dots" : sym ? " sym" : ""));
    if (dots) f.innerHTML = "<i></i><i></i><i></i>"; else f.textContent = text;
    if (size && emo) f.style.fontSize = `${size}px`;
    ms = ms || (dots ? 1500 : 1250);
    const w = f.offsetWidth / 2, h = f.offsetHeight;
    const want = x + side * 10, cx = clamp(want, w + 6, st.W - w - 6), top = Math.max(y - h - 10, 4);
    f.style.setProperty("--tx", `${clamp(x - cx, -w + 9, w - 9)}px`); f.style.setProperty("--tf", x < cx ? -1 : 1);
    f.style.transformOrigin = `calc(50% + ${clamp(x - cx, -w + 9, w - 9)}px) 115%`;
    const L = cx - w;
    f.animate([{ transform: `translate(${L}px,${top + 6}px) scale(.4)`, opacity: 0 },
      { transform: `translate(${L}px,${top - 1}px) scale(1.06)`, opacity: 1, offset: .14 },
      { transform: `translate(${L}px,${top}px) scale(1)`, opacity: 1, offset: .22 },
      { transform: `translate(${L}px,${top - 2}px) scale(1)`, opacity: 1, offset: .84 },
      { transform: `translate(${L}px,${top - 6}px) scale(.92)`, opacity: 0 }],
      { duration: ms, easing: "cubic-bezier(.25,.8,.3,1)" }).finished.then(() => f.remove());
  };
  const burst = (st, x, y, n = 7, r = 26, cls = "spk") => { for (let i = 0; i < n; i++) { const s = add(st, cls); const a = i / n * Math.PI * 2 + rnd(-.3, .3), d = r * rnd(.7, 1.2);
    s.animate([{ transform: `translate(${x}px,${y}px) scale(.2) rotate(0)`, opacity: 1 }, { transform: `translate(${x + Math.cos(a) * d}px,${y + Math.sin(a) * d}px) scale(1) rotate(90deg)`, opacity: 1, offset: .6 },
      { transform: `translate(${x + Math.cos(a) * d * 1.2}px,${y + Math.sin(a) * d * 1.2}px) scale(.2) rotate(140deg)`, opacity: 0 }], { duration: rnd(550, 800), easing: "ease-out" }).finished.then(() => s.remove()); } };
  const dust = (st, x, y, dir = 0, n = 4) => { for (let i = 0; i < n; i++) { const p = add(st, "puff"); const dx = (i - (n - 1) / 2) * 7 + dir * 4, k = rnd(.7, 1.2);
    p.animate([{ transform: `translate(${x + dx * .3}px,${y - 2}px) scale(.4)`, opacity: .9 }, { transform: `translate(${x + dx * 2.2}px,${y - 7 - rnd(0, 4)}px) scale(${1.4 * k})`, opacity: 0 }],
      { duration: rnd(380, 520), easing: "cubic-bezier(.2,.8,.3,1)" }).finished.then(() => p.remove()); } };

  const ripple = (st, x, y, k = 1) => { for (let i = 0; i < 2; i++) { const r = add(st, "rp"); r.animate([{ transform: `translate(${x}px,${y}px) scale(${.4 * k})`, opacity: .9 }, { transform: `translate(${x}px,${y}px) scale(${1.8 * k})`, opacity: 0 }], { duration: 700, delay: i * 160 }).finished.then(() => r.remove()); } };
  const splash = (st, x, y, n = 9) => { ripple(st, x, y + 2, 1.6); for (let i = 0; i < n; i++) { const d = add(st, "dr"), a = Math.PI + (i + .5) / n * Math.PI, r = rnd(16, 30);
    d.animate([{ transform: `translate(${x}px,${y}px)` }, { transform: `translate(${x + Math.cos(a) * r}px,${y + Math.sin(a) * r * 1.1}px)`, opacity: .95, offset: .5 }, { transform: `translate(${x + Math.cos(a) * r * 1.35}px,${y + 4}px)`, opacity: 0 }], { duration: 560, easing: "ease-out" }).finished.then(() => d.remove()); } };
  const confetti = (st, x, y, n = 22) => { const C = ["#ffd23f", "#ff6f91", "#7cf5c4", "#8ec5ff", "#fff", "#ff9f43"]; for (let i = 0; i < n; i++) { const c = add(st, "cf"); c.style.background = pick(C);
    const vx = rnd(-1, 1) * 90, up = rnd(50, 110), rot = rnd(-720, 720), dur = rnd(1100, 1700);
    c.animate([{ transform: `translate(${x}px,${y}px) rotate(0)` }, { transform: `translate(${x + vx * .6}px,${y - up}px) rotate(${rot * .4}deg)`, offset: .35 }, { transform: `translate(${x + vx}px,${y - up + 140}px) rotate(${rot}deg)`, opacity: 0 }],
      { duration: dur, easing: "cubic-bezier(.2,.7,.4,1)" }).finished.then(() => c.remove()); } };
  const bubbles = (st, x, y, n = 4) => { for (let i = 0; i < n; i++) { const b = add(st, "bub"); b.animate([{ transform: `translate(${x + rnd(-4, 4)}px,${y}px) scale(.5)`, opacity: 0 }, { transform: `translate(${x + rnd(-6, 6)}px,${y - 6}px) scale(1)`, opacity: 1, offset: .3 }, { transform: `translate(${x + rnd(-8, 8)}px,${y - 20}px) scale(1.3)`, opacity: 0 }], { duration: 900, delay: i * 180 }).finished.then(() => b.remove()); } };
  // the light follows the real sun, roughly for central Russia: sunrise and sunset by month. sunset — the sun on the hills,
  // evening — the blue hour after it, night — stars and the moon
  const SUN = [[9, 16.1], [8, 17.2], [7, 18.3], [5.9, 19.6], [4.8, 20.6], [4, 21.2], [4.4, 21], [5.4, 20], [6.6, 18.7], [7.6, 17.4], [8.4, 16.2], [9, 15.9]];
  const PHASE = (() => { const d = new Date(), h = d.getHours() + d.getMinutes() / 60, [rise, set] = SUN[d.getMonth()];
    return h < rise - 1 || h >= set + 2 ? "night" : h < rise + 2 ? "morning" : h < set - 1 ? "day" : h < set + .7 ? "sunset" : "evening"; })();
  // the moon's age today, 0 → 1 (new → full at .5 → new)
  const MOON = (((Date.now() - Date.UTC(2000, 0, 6, 18, 14)) / 864e5 / 29.530589) % 1 + 1) % 1;

  // ---------------- the stage: the card, its floors and its props
  const stage = (hc) => {
    let layer = hc.querySelector(".pet");
    if (!layer) { layer = document.createElement("div"); layer.className = "pet"; hc.prepend(layer); }
    let bg = hc.querySelector(".petbg"); if (!bg) { bg = document.createElement("div"); bg.className = "petbg"; hc.prepend(bg); }
    const st = { hc, layer, bg, pointer: null, busy: false, binds: [] };
    measure(st);
    // listeners on the card go through st.on, so they move with the frog to a redrawn card
    st.on = (type, fn) => { st.binds.push([type, fn]); st.hc.addEventListener(type, fn); };
    // floors the frog can stand on: the strip above the balance, the top of the digits, the top of the button
    st.floor = (x) => {
      if (st.num && x > st.num.l + 4 && x < st.num.r - 4 && st.onNum) return st.num.t;
      return st.ground;
    };
    return st;
  };
  // where the balance and «Пополнить» are on the card, and the ground over the digits
  const measure = (st) => {
    // the card may be mid-way through its entrance (scaled a little): positions are taken in the card's own pixels
    const hc = st.hc, hb = hc.getBoundingClientRect(), k = hb.width / (hc.offsetWidth || hb.width) || 1;
    const rel = (b) => ({ l: (b.left - hb.left) / k, r: (b.right - hb.left) / k, t: (b.top - hb.top) / k, b: (b.bottom - hb.top) / k });
    const n = hc.querySelector(".N"); let num = null;
    if (n) { const r = document.createRange(); r.selectNodeContents(n); const b = rel(r.getBoundingClientRect()); num = { ...b, t: b.t + b.b * 0 + (b.b - b.t) * .16, el: n }; }
    const btn = hc.querySelector(".acts .pill"); const bt = btn ? { ...rel(btn.getBoundingClientRect()), el: btn } : null;
    Object.assign(st, { W: hc.clientWidth, H: hc.clientHeight, ground: num ? num.t - 12 : 80, num, btn: bt });
  };

  // ---------------- the frog
  class Frog {
    constructor(st, skin) {
      this.st = st; this.x = -40; this.y = st.ground; this.z = 0; this.dir = -1; this.look = null; this.tilt = 0;
      this.el = add(st, "fr", `<div class="tl"><div class="bd"><div class="fc"><div class="cr"></div><div class="mo"></div><i class="xe" style="left:${EYE[0]*100}%;top:${EYE[1]*100}%">✕</i><i class="xe" style="left:${EYE[0]*100-17}%;top:${EYE[1]*100+1}%;font-size:9px">✕</i><i class="tng"></i></div></div></div>`);
      this.sh = add(st, "shd");
      this.tl = this.el.querySelector(".tl"); this.bd = this.el.querySelector(".bd"); this.fc = this.el.querySelector(".fc");
      this.cr = this.el.querySelector(".cr"); this.mo = this.el.querySelector(".mo");
      this.ready = lib().then((L) => new Promise((ok) => {
        this.a = L.loadAnimation({ container: this.fc, renderer: "svg", loop: false, autoplay: false, path: `/icons/frog/p${String(skin).padStart(2, "0")}.json` });
        this.a.addEventListener("DOMLoaded", () => { this.pupil = this.fc.querySelector("#pupil"); this.fc.querySelectorAll(".cr,.mo,.xe,.tng").forEach((e) => this.fc.appendChild(e)); this.idle(); this.loop(); ok(); });
      }));
      this.render();
    }
    // --- clips
    play(name, loop = false, speed = 1) {
      const [a, b] = CL[name]; this.clip = name; this.el.classList.toggle("thr", name === "idle"); this.a.loop = loop; this.a.setSpeed(speed); this.a.playSegments([a, b], true);
      return sleep((b - a) / FPS * 1000 / speed);
    }
    idle() { this.play("idle", true); }
    // a blink whenever it likes (the idle clip's own one comes only every 3 s)
    async blink(double = false) {
      if (this.clip !== "idle") return; this.clip = "blink"; this.el.classList.add("thr");
      this.a.loop = false; this.a.playSegments([149, 159], true); await sleep(170);
      if (double) { this.a.playSegments([149, 159], true); await sleep(170); }
      if (this.clip === "blink") this.idle();
    }
    // after a meal: the tongue flicks out over the lips
    async lick() {
      const [mx, my] = this.mouth(), t = add(this.st, "tg"), ang = this.dir > 0 ? 0 : Math.PI;
      t.style.cssText = `left:${mx}px;top:${my - 1.6}px;width:7px;transform:rotate(${ang}rad) scaleX(0)`;
      await t.animate([{ transform: `rotate(${ang}rad) scaleX(0)` }, { transform: `rotate(${ang + .5 * -this.dir}rad) scaleX(1)` }, { transform: `rotate(${ang - .4 * -this.dir}rad) scaleX(.8)` }, { transform: `rotate(${ang}rad) scaleX(0)` }], { duration: 380 }).finished;
      t.remove();
    }
    async once(name, speed = 1) { await this.play(name, false, speed); if (this.clip === name) this.idle(); }
    // --- where it is: x on the card, y the floor it stands on, z how high above it
    // the lean is the `rotate` property, so the clips' own transform animations on .tl stack on it instead of fighting it
    render() {
      if (this.held) { at(this.el, this.hx, this.hy, ""); this.tl.style.rotate = `${this.tilt}deg`; const k = 1 / (1 + Math.max(0, this.st.ground - this.hy) / 36);
        at(this.sh, this.hx, this.st.ground + 1, `scale(${k})`); this.sh.style.opacity = String(.3 * k + .1); this.el.style.clipPath = ""; return; }
      at(this.el, this.x, this.y - this.z, "");
      const under = this.y - this.z - this.st.ground + (1 - FEET) * SIZE;
      this.el.style.clipPath = this.wet && under > 0 ? `inset(-40px -40px ${under.toFixed(1)}px -40px)` : "";
      this.tl.style.rotate = `${this.tilt}deg`;
      const k = 1 / (1 + this.z / 36);
      at(this.sh, this.x, this.y + 1, `scale(${k})`); this.sh.style.opacity = this.wet ? "0" : String(.35 + .65 * k);
    }
    // a move along a path: path(t) sets .x .y .z .tilt for t 0→1. The compositor draws it from keyframes, so it runs at the
    // screen's own rate (120 Hz on ProMotion) even where WebKit holds requestAnimationFrame at 60 Hz — or 30 Hz in Low Power
    // Mode — and the main thread is busy with the puppet. .x .y .z .tilt still follow it every frame, for the eyes and the scenes.
    // The lean rides in the same keyframes (.fr turns round the feet, like .tl), so nothing else animating .tl takes it off
    // the compositor. In the pond (a moving waterline clip) or in the hand it is drawn frame by frame as before.
    async move(ms, path) {
      if (this.wet || this.held || !this.el.animate) {
        const t0 = performance.now();
        while (true) { const t = Math.min(1, (performance.now() - t0) / ms); path(t); this.render(); if (t >= 1) break; await raf(); }
        return;
      }
      const n = clamp(Math.round(ms / 16), 8, 40), fr = [], sh = [];
      for (let i = 0; i <= n; i++) {
        path(i / n); const k = 1 / (1 + this.z / 36);
        fr.push({ transform: `translate(${this.x}px,${this.y - this.z}px) rotate(${this.tilt}deg)` });
        sh.push({ transform: `translate(${this.x}px,${this.y + 1}px) scale(${k})`, opacity: .35 + .65 * k });
      }
      path(0); this.tl.style.rotate = "0deg";
      const o = { duration: ms, easing: "linear", fill: "forwards" }, an = [this.el.animate(fr, o), this.sh.animate(sh, o)];
      while (true) { await raf(); const t = an[0].playState === "finished" ? 1 : Math.min(1, (an[0].currentTime || 0) / ms); path(t); if (t >= 1) break; }
      this.render(); an.forEach((a) => a.cancel());
    }
    place(x, y) { this.x = x; this.y = y; this.z = 0; this.render(); }
    // turning round: the face narrows to its edge and opens the other way (a turn, not a mirror flip); standing, it blinks on the turn
    face(d) { if (d === this.dir) return; const o = this.dir; this.dir = d; this.el.classList.toggle("r", d > 0);
      this.fc.animate([{ transform: `scaleX(${-o})`, easing: "ease-in" }, { transform: `scaleX(${-o * .12})`, offset: .5 }, { transform: `scaleX(${-d * .12})`, offset: .5, easing: "cubic-bezier(.3,1.5,.5,1)" }, { transform: `scaleX(${-d})` }], { duration: 200 });
      if (!this.moving && !this.held && !this.wet) { this.tl.animate([{ transform: "none" }, { transform: "translateY(-4px)" }, { transform: "none" }], { duration: 200, easing: "ease-out" }); if (this.clip === "idle") this.blink(); } }
    mouth() { return [this.x + (this.dir > 0 ? 1 : -1) * (.5 - MOUTH[0]) * SIZE, this.y - this.z - FEET * SIZE + MOUTH[1] * SIZE]; }
    // --- one frame: eyes follow what matters (a scene's target, else your finger, else a glance), the pupil eases there
    loop() {
      let px = 0, py = 0, pvx = 0, pvy = 0, lean = 0, last = performance.now();
      const tick = () => {
        if (this.st.dead) return;
        if (!this.el.isConnected) { requestAnimationFrame(tick); return; }
        const p = this.st.pointer, now = performance.now(), fk = frames(last, now); last = now;
        const tgt = this.look || (p && now - p.t < 2500 ? p : null) || this.glance;
        let tx = 0, ty = 0, want = 0;
        if (!tgt) { if (now > (this.sacAt || 0)) { this.sac = Math.random() < .35 ? [0, 0] : [rnd(-9, 9), rnd(-7, 4)]; this.sacAt = now + rnd(600, 2200); } [tx, ty] = this.sac || [0, 0]; }
        if (tgt && this.clip !== "sleep" && this.clip !== "yawn") {
          const ex = this.x + (this.dir > 0 ? 1 : -1) * (.5 - EYE[0]) * -SIZE, ey = this.y - this.z - FEET * SIZE + EYE[1] * SIZE;
          let dx = tgt.x - ex, dy = tgt.y - ey; const d = Math.hypot(dx, dy) || 1, m = Math.min(15, d / 3);
          tx = dx / d * m * (this.dir > 0 ? -1 : 1); ty = dy / d * m;
          // leans a little toward it; something high above — it leans back to look up
          if (!this.moving && !this.held && !this.wet && this.clip !== "dead") want = clamp(dx / 50, -1, 1) * 3.5 + (dy < -50 ? -this.dir * 2 : 0);
          // something behind it for a while: it turns round
          if (!this.st.busy && !this.moving && Math.sign(dx) !== Math.sign(this.dir) && Math.abs(dx) > 40) {
            this.behind = this.behind || now; if (now - this.behind > 600) { this.face(Math.sign(dx)); this.behind = 0; }
          } else this.behind = 0;
        }
        const hy = this.held ? this.hy : this.y - this.z, vy = fk ? (hy - (this.lastHy ?? hy)) / fk : 0; this.lastHy = hy;
        ty = clamp(ty - vy * 1.6, -16, 16);
        for (let n = Math.max(1, Math.ceil(fk)), s = fk / n, i = 0; i < n && fk; i++) {
          pvx += ((tx - px) * .16 - pvx * .5) * s; pvy += ((ty - py) * .16 - pvy * .5) * s; px += pvx * s; py += pvy * s; }
        px = clamp(px, -17, 17); py = clamp(py, -17, 17);
        if (this.pupil) this.pupil.style.translate = `${px.toFixed(1)}px ${py.toFixed(1)}px`;
        const nl = lean + (want - lean) * (1 - Math.pow(.9, fk));
        if (Math.abs(nl - lean) > .005 || (lean && !nl)) { lean = Math.abs(nl) < .02 ? 0 : nl; this.bd.style.rotate = `${lean.toFixed(2)}deg`; }
        requestAnimationFrame(tick);
      };
      tick();
    }
    // --- a hop: crouch (the puppet), fly along an arc leaning into it, land in a squash with a puff of dust
    async hop(x, y = this.st.ground, { h = 22, ms = 300, quiet = false } = {}) {
      if (Math.abs(x - this.x) > 2) this.face(x > this.x ? 1 : -1);
      this.moving = true;
      const sp = 300 / ms, k = clamp(h / 30, .25, 1), sq = !this.wet; this.play("hop", false, sp);
      const crouch = sq && this.bd.animate([{ transform: "none" }, { transform: `scale(${1 + .13 * k},${1 - .15 * k})` }], { duration: 100 / sp, easing: "ease-out", fill: "forwards" });
      await sleep(100 / sp);
      if (crouch) { crouch.cancel(); this.bd.animate([{ transform: `scale(${1 - .1 * k},${1 + .15 * k})` }, { transform: "none", offset: .45 }, { transform: `scale(${1 - .04 * k},${1 + .07 * k})` }], { duration: ms }); }
      const x0 = this.x, y0 = this.y, dir = this.dir, lean = Math.min(1, Math.abs(x - x0) / 20);
      await this.move(ms, (t) => { this.x = x0 + (x - x0) * t; this.y = y0 + (y - y0) * t; this.z = 4 * h * t * (1 - t); this.tilt = -dir * 16 * (1 - 2 * t) * lean; });
      this.z = 0; this.tilt = 0; this.y = y; this.render();
      if (!quiet) dust(this.st, this.x, this.y, -dir, Math.abs(x - x0) > 30 ? 4 : 3);
      if (Math.abs(x - x0) > 30 && !this.wet) this.tl.animate([{ transform: "none" }, { transform: `rotate(${dir * 5}deg)` }, { transform: `rotate(${-dir * 2}deg)` }, { transform: "none" }], { duration: 380, easing: "ease-out" });
      if (sq) this.bd.animate([{ transform: `scale(${1 + .2 * k},${1 - .2 * k})` }, { transform: `scale(${1 - .06 * k},${1 + .07 * k})`, offset: .45 }, { transform: `scale(${1 + .02 * k},${1 - .02 * k})`, offset: .75 }, { transform: "none" }],
        { duration: 240 + 140 * k, easing: "ease-out" });
      (this.st.grass || []).forEach((g) => { if (Math.abs(g.x - this.x) < 24 && Math.abs(this.y - this.st.ground) < 2) g.el.animate([{ transform: `scale(${g.s})` }, { transform: `scale(${g.s}) rotate(${g.x < this.x ? -28 : 28}deg) scaleY(.7)` }, { transform: `scale(${g.s})` }], { duration: 500, easing: "cubic-bezier(.3,1.6,.5,1)" }); });
      const pd = this.st.pond;
      if (pd && !this.wet && Math.abs(this.y - this.st.ground) < 2 && this.x > pd.l && this.x < pd.r) {
        if (Math.abs(this.x - pd.lily.x) < 14) pd.lily.dip(); else ripple(this.st, this.x, this.st.ground + 2, 1.4);
      }
      this.land?.(this.x, this.y);
      await sleep(80 / sp);
      this.a.setSpeed(1); this.moving = false;
      if (this.clip === "hop") this.idle();
    }
    async go(x, y = this.st.ground, { step = 40, h = 20, ms = 300 } = {}) {
      if (!this.look && Math.abs(x - this.x) > 30) { this.glance = { x, y: y - 14 }; await sleep(160); }
      const n = Math.max(1, Math.round(Math.abs(x - this.x) / step)), x0 = this.x, y0 = this.y;
      const pd = this.st.pond, wetAt = (px) => pd && px > pd.l - 4 && px < pd.r + 4 && Math.abs(px - pd.lily.x) > 12;
      for (let i = 1; i <= n; i++) { const px = x0 + (x - x0) * i / n; if (i < n && wetAt(px)) continue;
        const far = Math.abs(px - this.x) > step * 1.5; await this.hop(px, i === n ? y : y0 + (y - y0) * i / n, { h: h * rnd(.85, 1.15) * (far ? 1.6 : 1), ms: far ? ms * 1.4 : ms }); }
      this.glance = null;
    }
    async tongue(tx, ty, ms = 230) {
      const [mx, my] = this.mouth(), len = Math.hypot(tx - mx, ty - my), ang = Math.atan2(ty - my, tx - mx);
      this.mo.animate([{ transform: "scale(0)" }, { transform: "scale(1.4)", offset: .2 }, { transform: "scale(1.4)", offset: .8 }, { transform: "scale(0)" }], { duration: ms + 60 });
      const t = add(this.st, "tg"); t.style.cssText = `left:${mx}px;top:${my - 1.6}px;width:${len}px;transform:rotate(${ang}rad) scaleX(0)`;
      this.bd.animate([{ transform: "none" }, { transform: `translateX(${this.dir * 3}px) scale(1.06,.94)` }, { transform: "none" }], { duration: ms });
      await t.animate([{ transform: `rotate(${ang}rad) scaleX(0)` }, { transform: `rotate(${ang}rad) scaleX(1)`, offset: .42 }, { transform: `rotate(${ang}rad) scaleX(0)` }],
        { duration: ms, easing: "cubic-bezier(.3,.9,.4,1)" }).finished;
      t.remove();
    }
    async croak(n = 2) {
      this.play("croak");
      for (let i = 0; i < n; i++) {
        this.cr.animate([{ transform: "scale(0)" }, { transform: "scale(1.25)", offset: .45 }, { transform: "scale(.9)", offset: .7 }, { transform: "scale(0)" }], { duration: 260, easing: "ease-out" });
        if (i === 0) this.say("ква!", { size: 11 });
        await sleep(270);
      }
      await sleep(300); if (this.clip === "croak") this.idle();
    }
    async kiss() { const [x, y] = [this.x + this.dir * 6, this.y - SIZE * .66]; pop(this.st, x, y, "💋", { size: 14 }); this.hearts(2); await this.once("blush"); }
    hearts(n = 3) { for (let i = 0; i < n; i++) setTimeout(() => { const h = add(this.st, "ht"); h.textContent = "💗"; const x = this.x + rnd(-10, 10), y = this.y - SIZE * .6;
      h.animate([{ transform: `translate(${x}px,${y}px) scale(.3)`, opacity: 0 }, { transform: `translate(${x + rnd(-8, 8)}px,${y - 14}px) scale(1)`, opacity: 1, offset: .3 },
        { transform: `translate(${x + rnd(-16, 16)}px,${y - 34}px) scale(.8)`, opacity: 0 }], { duration: 1100, easing: "ease-out" }).finished.then(() => h.remove()); }, i * 180); }
    async shock() { this.say("!", { size: 14 }); const j = this.hopInPlace(16); await this.once("shock"); await j; }
    async hopInPlace(h = 14) {
      const k = clamp(h / 30, .2, 1), sq = !this.wet && !this.held;
      if (sq) this.bd.animate([{ transform: `scale(${1 - .08 * k},${1 + .12 * k})` }, { transform: "none", offset: .45 }, { transform: `scale(${1 - .03 * k},${1 + .05 * k})` }], { duration: 300 });
      await this.move(300, (t) => { this.z = 4 * h * t * (1 - t); }); this.z = 0; this.render();
      if (sq) this.bd.animate([{ transform: `scale(${1 + .16 * k},${1 - .16 * k})` }, { transform: `scale(${1 - .04 * k},${1 + .05 * k})`, offset: .5 }, { transform: "none" }], { duration: 200 + 120 * k, easing: "ease-out" });
    }
    // a backflip (two quick taps): it turns round its middle, not its feet, so the feet are moved round that middle as it spins
    async flip() {
      if (this.moving || this.held || this.wet) return; this.moving = true;
      const x0 = this.x, d = this.dir, r = (FEET - .5) * SIZE; this.play("hop", false, 1.2); await sleep(80);
      await this.move(560, (t) => { const a = -d * ease(t) * Math.PI * 2, z = 4 * 34 * t * (1 - t);
        this.x = x0 - r * Math.sin(a); this.z = z + r - r * Math.cos(a); this.tilt = a * 180 / Math.PI; });
      this.x = x0; this.z = 0; this.tilt = 0; this.render(); dust(this.st, this.x, this.y, 0, 4);
      this.bd.animate([{ transform: "scale(1.2,.82)" }, { transform: "none" }], { duration: 260, easing: "ease-out" });
      burst(this.st, this.x, this.y - 30, 6, 20); this.moving = false; if (this.clip === "hop") this.idle();
    }
    // a finger rubbing back and forth over it: it giggles and squirms
    async tickle() {
      this.say("хи-хи"); this.play("wiggle", false, 2);
      await this.bd.animate([{ transform: "none" }, { transform: "rotate(-8deg) scale(1.04,.96)" }, { transform: "rotate(8deg) scale(1.04,.96)" }, { transform: "rotate(-6deg)" }, { transform: "rotate(6deg)" }, { transform: "none" }], { duration: 700 }).finished;
      this.hearts(1); if (this.clip === "wiggle") this.idle();
    }
    async stretch() {
      await this.bd.animate([{ transform: "none" }, { transform: "scale(.94,1.12)", offset: .45 }, { transform: "scale(.96,1.1) rotate(3deg)", offset: .7 }, { transform: "none" }], { duration: 900, easing: "ease-in-out" }).finished;
    }
    say(text, o = {}) { pop(this.st, this.x + this.dir * 4, this.y - this.z - SIZE * .7, text, { side: this.dir, ...o }); }
    async lookAround() { const s = this.st; for (const p of [{ x: 0, y: s.ground - 30 }, { x: s.W, y: s.ground - 40 }, { x: this.x, y: -30 }]) { this.glance = p; await sleep(rnd(450, 700)); } this.glance = null; }
  }

  // a bug that buzzes around a point; .x/.y always hold where it is
  class Bug {
    constructor(st, kind, x, y) {
      this.st = st; this.kind = kind; this.cx = x; this.cy = y; this.x = x; this.y = y; this.t = rnd(0, 9); this.r = kind === "fly" ? 13 : 4; this.on = true; this.n = 0;
      this.el = add(st, `bug ${kind}`, "<i></i><i></i>");
      if (kind === "bfly") this.r = 6; if (kind === "sb") this.r = 7;
      let last = performance.now(), trail = 0;
      const tick = () => { if (!this.on) return; const now = performance.now(), fk = frames(last, now); last = now;
        this.t += (kind === "sb" ? .02 : .05) * fk; const px = this.x, py = this.y;
        const jit = this.still ? 0 : kind === "bfly" ? Math.sin(this.t * 3.1) * 4 : kind === "sb" ? 0 : Math.sin(this.t * 7) * 2;
        this.x = this.cx + (this.still ? 0 : Math.sin(this.t * 2.3) * this.r + Math.sin(this.t * 5.1) * this.r * .25); this.y = this.cy + (this.still ? 0 : Math.cos(this.t * 1.7) * this.r * .6) + jit;
        const ang = this.kind === "dfly" ? Math.atan2(this.y - py, this.x - px) * 180 / Math.PI * .3 : 0;
        at(this.el, this.x, this.y, `rotate(${ang}deg) scaleX(${this.x < px ? -1 : 1})`);
        if (this.kind === "fly" && now - trail >= 7000 / 60) { trail = now; const b = add(st, "bz"); at(b, this.x, this.y); b.animate([{ opacity: .6 }, { opacity: 0, transform: `translate(${this.x}px,${this.y}px) scale(.3)` }], { duration: 500 }).finished.then(() => b.remove()); }
        requestAnimationFrame(tick); };
      tick();
    }
    to(x, y, ms = 900) { const x0 = this.cx, y0 = this.cy, t0 = performance.now();
      return new Promise((ok) => { const f = (now) => { if (!this.on) return ok(); const k = Math.min(1, (now - t0) / ms), e = ease(k);
        this.cx = x0 + (x - x0) * e; this.cy = y0 + (y - y0) * e; k < 1 ? requestAnimationFrame(f) : ok(); }; requestAnimationFrame(f); }); }
    gone() { this.on = false; this.el.remove(); }
  }

  // ---------------- scenes: each starts wherever the frog is and leaves it somewhere on the field
  const S = {};
  const W = (st) => st.W, inField = (st, x) => { x = clamp(x, 34, st.W - 34); const p = st.pond; if (p && x > p.l - 14 && x < p.r + 14) x = x < p.cx ? p.l - 14 : p.r + 14; return clamp(x, 34, st.W - 34); };

  // Гуляет: a few hops to somewhere else on the field, a stop to look around
  S.wander = async (st, f) => {
    const x = inField(st, f.x + pick([-1, 1]) * rnd(60, 140));
    await f.go(x, st.ground, { step: rnd(34, 46), h: rnd(14, 22), ms: rnd(260, 320) });
    if (Math.random() < .5) await f.lookAround();
  };
  // Охота: a fly comes in, the frog watches it, sneaks up low, wiggles, strikes — ням, and a happy blush
  S.fly = async (st, f) => {
    const side = f.x < st.W / 2 ? 1 : -1, bx = side > 0 ? st.W + 20 : -20;
    const fl = new Bug(st, "fly", bx, st.ground - 46); f.look = fl;
    await fl.to(inField(st, f.x + side * rnd(110, 150)), st.ground - rnd(34, 46), 1300);
    f.face(side); await sleep(400);
    while (Math.abs(fl.x - f.x) > 62) await f.hop(f.x + side * 20, st.ground, { h: 6, ms: 220, quiet: true });   // sneaking
    await f.once("wiggle", 1.2);
    const tg = f.tongue(fl.x, fl.y); await sleep(100); fl.gone(); await tg;
    f.look = null; f.say("ням"); await f.once("gulp"); await f.lick(); f.hearts(1);
  };
  // Погоня: the fly dodges the tongue twice; the third try lands
  S.chase = async (st, f) => {
    const fl = new Bug(st, "fly", inField(st, f.x + (f.x < st.W / 2 ? 90 : -90)), st.ground - 40); fl.r = 9; f.look = fl;
    for (let i = 0; i < 3; i++) {
      f.face(fl.x > f.x ? 1 : -1);
      if (Math.abs(fl.x - f.x) > 70) await f.go(fl.x - f.dir * 55, st.ground, { step: 36, h: 18, ms: 260 });
      await f.once("wiggle", 2);
      const tg = f.tongue(fl.x, fl.y, 210);
      if (i < 2) { fl.to(inField(st, fl.x + pick([-1, 1]) * rnd(90, 130)), st.ground - rnd(36, 56), 420); await tg; f.say(i ? "?!" : "?"); await sleep(350); }
      else { await sleep(90); fl.gone(); await tg; }
    }
    f.look = null; f.say("ням"); await f.once("gulp"); await f.lick(); await f.hopInPlace(12); f.hearts(2);
  };
  // На балансе: jumps up onto the digits (they give under it), croaks to you, hops down
  S.perch = async (st, f) => {
    if (!st.num) return S.wander(st, f);
    const x = inField(st, (st.num.l + st.num.r) / 2 + rnd(-30, 30));
    await f.go(x + (f.x < x ? -46 : 46), st.ground, { step: 40 });
    st.onNum = true;
    f.land = () => st.num.el.animate([{ transform: "none" }, { transform: "translateY(3px) scale(1.02,.96)" }, { transform: "none" }], { duration: 260, easing: "cubic-bezier(.3,1.6,.5,1)" });
    await f.hop(x, st.num.t, { h: 30, ms: 340 });
    f.land = null;
    await sleep(500); await f.croak(2); await sleep(400);
    if (Math.random() < .5) await f.kiss();
    const out = inField(st, x + pick([-1, 1]) * 70);
    st.onNum = false;
    await f.hop(out, st.ground, { h: 22, ms: 320 });
  };
  // Кнопка: hops onto «Пополнить», stomps twice — it presses in — «тык!»
  S.button = async (st, f) => {
    if (!st.btn) return S.wander(st, f);
    const x = inField(st, (st.btn.l + st.btn.r) / 2 + rnd(-60, 60)), y = st.btn.t + 1;
    await f.go(x + (f.x < x ? -40 : 40), st.ground, { step: 40 });
    await f.hop(x, y, { h: 16, ms: 360 });
    for (let i = 0; i < 2; i++) {
      await sleep(250); await f.hopInPlace(9);
      st.btn.el.animate([{ transform: "none" }, { transform: "translateY(2px) scale(.985)" }, { transform: "none" }], { duration: 220 });
      dust(st, f.x, f.y, 0, 2);
    }
    f.say(""); await sleep(700);
    await f.hop(inField(st, x + pick([-1, 1]) * 50), st.ground, { h: 30, ms: 360 });
  };
  // Монетка: a coin drops, the frog watches it fall, runs under it and catches it at the top of a jump
  S.coin = async (st, f) => {
    const cx = inField(st, f.x + pick([-1, 1]) * rnd(50, 100)), c = add(st, "coin"); c.textContent = "₽";
    const target = { x: cx, y: -20 }; f.look = target; f.say("!", { size: 13 });
    const t0 = performance.now(), fallMs = 1100, stopY = st.ground - 62;
    let caught = false;
    const fall = () => { if (caught) return; const k = Math.min(1, (performance.now() - t0) / fallMs); target.y = -20 + (stopY + 20) * k * k;
      at(c, cx, target.y, `rotateY(${k * 900}deg)`); if (k < 1) requestAnimationFrame(fall); }; fall();
    await f.go(cx - f.dir * 0, st.ground, { step: 44, h: 16, ms: 240 });
    const wait = fallMs - (performance.now() - t0) - 180; if (wait > 0) await sleep(wait);
    const j = f.hopInPlace(42); await sleep(150); caught = true; c.remove(); burst(st, f.x, f.y - 48, 6, 18); await j;
    f.look = null; pop(st, f.x, f.y - SIZE * .9, "+50 ₽", { kind: "gold" }); await f.once("joy");
    if (st.num) st.num.el.animate([{ transform: "scale(1)" }, { transform: "scale(1.08)", filter: "drop-shadow(0 0 10px rgba(255,230,120,.9))" }, { transform: "scale(1)" }], { duration: 600, easing: "cubic-bezier(.3,1.6,.5,1)" });
    await f.kiss();
  };
  // Дождик: a little cloud comes over, rains, a puddle forms; the frog jumps in — splash! — and shakes off
  S.rain = async (st, f) => {
    const px = clamp(f.x + (f.x > st.W / 2 ? -1 : 1) * rnd(70, 110), 50, st.W - 90), cl = add(st, "cl");
    await cl.animate([{ transform: `translate(${px < st.W / 2 ? -40 : st.W + 40}px,14px)` }, { transform: `translate(${px}px,14px)` }], { duration: 1200, easing: "cubic-bezier(.3,.8,.4,1)", fill: "forwards" }).finished;
    f.look = { x: px, y: 14 };
    const pd = add(st, "pd"); pd.style.width = "0px";
    for (let i = 0; i < 16; i++) { const d = add(st, "dr"), x = px + rnd(-16, 16);
      d.animate([{ transform: `translate(${x}px,22px)`, opacity: 1 }, { transform: `translate(${x}px,${st.ground - 3}px)`, opacity: 1 }], { duration: 420, delay: i * 70, easing: "ease-in" }).finished.then(() => d.remove()); }
    pd.animate([{ width: "0px", transform: `translate(${px}px,${st.ground}px) translateX(0)` }, { width: "44px", transform: `translate(${px - 22}px,${st.ground}px)` }], { duration: 1500, fill: "forwards", easing: "ease-out" });
    await sleep(1500);
    cl.animate([{ transform: `translate(${px}px,14px)` }, { transform: `translate(${px + 120}px,4px)`, opacity: 0 }], { duration: 900, fill: "forwards" }).finished.then(() => cl.remove());
    f.look = { x: px, y: st.ground }; await sleep(400);
    await f.go(px - (f.x < px ? 44 : -44), st.ground, { step: 40 });
    await f.hop(px, st.ground, { h: 34, ms: 380, quiet: true });
    for (let i = 0; i < 8; i++) { const d = add(st, "dr"), a = Math.PI + i / 7 * Math.PI, r = rnd(18, 28);
      d.animate([{ transform: `translate(${px}px,${st.ground - 2}px)` }, { transform: `translate(${px + Math.cos(a) * r}px,${st.ground - 2 + Math.sin(a) * r * .9}px)`, opacity: .9, offset: .5 }, { transform: `translate(${px + Math.cos(a) * r * 1.3}px,${st.ground + 2}px)`, opacity: 0 }], { duration: 520, easing: "ease-out" }).finished.then(() => d.remove()); }
    const r = add(st, "rp"); r.animate([{ transform: `translate(${px}px,${st.ground}px) scale(.5)`, opacity: 1 }, { transform: `translate(${px}px,${st.ground}px) scale(2.4)`, opacity: 0 }], { duration: 650 }).finished.then(() => r.remove());
    f.look = null; f.say(""); await sleep(350);
    await f.bd.animate([{ transform: "rotate(0)" }, { transform: "rotate(-12deg)" }, { transform: "rotate(12deg)" }, { transform: "rotate(-8deg)" }, { transform: "rotate(5deg)" }, { transform: "rotate(0)" }], { duration: 560 }).finished;
    for (let i = 0; i < 5; i++) { const d = add(st, "dr"), a = rnd(-2.8, -.3); d.animate([{ transform: `translate(${f.x}px,${f.y - 22}px)` }, { transform: `translate(${f.x + Math.cos(a) * 26}px,${f.y - 22 + Math.sin(a) * 18}px)`, opacity: 0 }], { duration: 400 }).finished.then(() => d.remove()); }
    await f.hearts(1);
    await sleep(500);
    await f.hop(inField(st, px + pick([-1, 1]) * 60), st.ground, { h: 22 });
    pd.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 1600, fill: "forwards" }).finished.then(() => pd.remove());
  };
  // Стрекоза: a dragonfly zips across; the frog's eyes and head follow it, it turns round, gives a happy hop
  S.dragonfly = async (st, f) => {
    const from = pick([-1, 1]), y = rnd(18, 34), d = new Bug(st, "dfly", from < 0 ? -30 : st.W + 30, y); f.look = d;
    await d.to(st.W * .5, y + 8, 1400); await sleep(400); await d.to(from < 0 ? st.W + 40 : -40, y - 6, 1300); d.gone();
    f.look = null; f.say("!"); await f.hopInPlace(14);
  };
  // Пробежка: runs off one side and comes back in from the other
  S.run = async (st, f) => {
    const side = f.x < st.W / 2 ? -1 : 1;
    await f.go(side < 0 ? -40 : st.W + 40, st.ground, { step: 44, h: 18, ms: 240 });
    await sleep(rnd(500, 900));
    f.place(side < 0 ? st.W + 40 : -40, st.ground);
    await f.go(inField(st, side < 0 ? st.W - rnd(60, 110) : rnd(60, 110)), st.ground, { step: 44, h: 18, ms: 240 });
  };
  // Сон: a big yawn, eyes slowly shut, Zz float up; it wakes by itself (or by a tap) with a start
  S.sleep = async (st, f, { long = false } = {}) => {
    await f.once("yawn"); f.play("sleep", true);
    let on = true; const zz = (async () => { let i = 0; while (on) { const z = add(st, "zz"); z.textContent = i++ % 2 ? "z" : "Z"; const x = f.x + f.dir * -8, y = f.y - SIZE * .6;
      z.animate([{ transform: `translate(${x}px,${y}px) scale(.5)`, opacity: 0 }, { transform: `translate(${x + 6}px,${y - 10}px) scale(1)`, opacity: 1, offset: .3 }, { transform: `translate(${x + 16}px,${y - 30}px) scale(1.2)`, opacity: 0 }], { duration: 2000 }).finished.then(() => z.remove());
      await sleep(900); } })();
    st.wake = null; await Promise.race([sleep(long ? 1e9 : rnd(5000, 8000)), new Promise((r) => { st.wake = r; })]);
    on = false; await zz; await f.shock();
  };


  // Бабочка: flutters in and lands on its head; the frog looks up at it, holds still… sneezes — апчхи! — and it flies off
  S.butterfly = async (st, f) => {
    const from = f.x < st.W / 2 ? 1 : -1, b = new Bug(st, "bfly", from > 0 ? st.W + 20 : -20, rnd(10, 30)); f.look = b;
    const head = () => [f.x + f.dir * -3, f.y - SIZE * .62];
    await b.to(f.x + from * 50, f.y - 80, 1700);
    await b.to(head()[0], head()[1] - 26, 900);
    b.still = true; b.el.classList.add("sit"); await b.to(...head(), 500);
    f.look = { x: f.x, y: -60 }; await sleep(900); await f.blink(true); await sleep(700);
    f.say("…", {}); await sleep(600);
    await f.bd.animate([{ transform: "none" }, { transform: "scale(1.06,.9) rotate(4deg)", offset: .5 }, { transform: "scale(.92,1.12) rotate(-6deg)", offset: .7 }, { transform: "none" }], { duration: 520 }).finished;
    f.say("апчхи"); b.still = false; b.el.classList.remove("sit"); f.look = b;
    dust(st, f.mouth()[0], f.mouth()[1], f.dir, 3);
    await b.to(f.x - f.dir * 60, f.y - 70, 700); await b.to(from > 0 ? -30 : st.W + 30, rnd(0, 20), 1600); b.gone();
    f.look = null; await f.croak(1);
  };
  // Пузырь: a soap bubble floats by; the frog follows it with its eyes, sneaks under it and pops it with the tongue — пуф!
  S.bubble = async (st, f) => {
    const from = pick([-1, 1]), y0 = st.ground - 30, b = new Bug(st, "sb", from < 0 ? -20 : st.W + 20, y0); f.look = b;
    const mid = inField(st, f.x + (from < 0 ? -1 : 1) * rnd(60, 100));
    await b.to(mid, y0 - 14, 2600);
    f.face(b.x > f.x ? 1 : -1);
    if (Math.abs(b.x - f.x) > 60) await f.go(b.x - f.dir * 50, st.ground, { step: 30, h: 10, ms: 260 });
    await f.once("wiggle", 1.4);
    const tg = f.tongue(b.x, b.y, 220); await sleep(95);
    const bx = b.x, by = b.y; b.gone();
    const r = add(st, "rp"); r.animate([{ transform: `translate(${bx}px,${by}px) scale(.3,1.2)`, opacity: 1 }, { transform: `translate(${bx}px,${by}px) scale(1.2,3.4)`, opacity: 0 }], { duration: 380 }).finished.then(() => r.remove());
    burst(st, bx, by, 6, 14); await tg;
    f.look = null; f.say(""); await f.once("shock"); await f.blink();
  };
  // Подружка: another Kissed Frog hops in from the other side; they meet, get shy, kiss — hearts — and she hops away
  S.friend = async (st, f) => {
    const skins = [0, 1, 5, 14, 20].filter((k) => k !== f.skin), side = f.x < st.W / 2 ? 1 : -1;
    const g = new Frog(st, pick(skins)); g.mood = null; await g.ready;
    g.place(side > 0 ? st.W + 40 : -40, st.ground); g.face(-side);
    const eyes = (o) => ({ get x() { return o.x; }, get y() { return o.y - SIZE * .4; } });
    f.look = eyes(g); g.look = eyes(f);
    f.say("!"); await sleep(400);
    const meet = clamp((f.x + (side > 0 ? st.W : 0)) / 2, 70, st.W - 70);
    await Promise.all([g.go(meet + side * 20, st.ground, { step: 40, h: 18 }), f.go(meet - side * 20, st.ground, { step: 34, h: 16 })]);
    f.face(side); g.face(-side);
    await sleep(300); await Promise.all([f.blink(), g.once("wiggle", 1.6)]);
    // the kiss: lean in
    await Promise.all([f.bd.animate([{ transform: "none" }, { transform: `translateX(${side * 6}px) rotate(${side * 8}deg)` }, { transform: "none" }], { duration: 700 }).finished,
      g.bd.animate([{ transform: "none" }, { transform: `translateX(${-side * 6}px) rotate(${-side * 8}deg)` }, { transform: "none" }], { duration: 700 }).finished, sleep(320).then(() => {
        pop(st, meet, st.ground - SIZE * .62, "💋", { size: 16 }); burst(st, meet, st.ground - SIZE * .45, 8, 22); })]);
    f.hearts(3); g.hearts(2);
    await Promise.all([f.once("blush"), g.once("blush")]);
    g.look = null; await g.croak(1);
    await g.go(side > 0 ? st.W + 40 : -40, st.ground, { step: 44, h: 22, ms: 280 });
    g.el.remove(); g.sh.remove(); f.look = null;
    f.say("♥", {}); await f.croak(1);
  };
  // Снежинка (зимой): a big flake drifts down; the frog catches it on the tongue — холодно! — a happy shiver
  S.snowflake = async (st, f) => {
    const x = inField(st, f.x + f.dir * rnd(40, 80)), fl = add(st, "fx plain"); fl.textContent = "❄"; fl.style.fontSize = "14px"; fl.style.willChange = "transform";
    const o = { x, y: -10 }; f.look = o; const t0 = performance.now(), ms = 2600;
    let live = true; (async () => { while (live) { const k = Math.min(1, (performance.now() - t0) / ms); o.y = -10 + (st.ground - 70) * k; o.x = x + Math.sin(k * 9) * 12;
      at(fl, o.x - 7, o.y - 7, `rotate(${k * 360}deg)`); if (k >= 1) break; await raf(); } })();
    await sleep(ms * .55); f.face(o.x > f.x ? 1 : -1);
    while (performance.now() - t0 < ms - 200) await raf();
    const tg = f.tongue(o.x, o.y, 220); await sleep(95); live = false; fl.remove(); await tg;
    f.look = null; f.say("бр-р"); await f.once("shiver", 2); await f.lick(); f.hearts(1);
  };

  // Купание: hops to the pond, dives — splash! — bubbles, the head comes up and paddles across, jumps out and shakes off
  S.swim = async (st, f) => {
    const p = st.pond; if (!p) return S.wander(st, f);
    const side = f.x < p.cx ? 1 : -1, bank = side > 0 ? p.l - 16 : p.r + 16;
    await f.go(bank, st.ground, { step: 40 });
    f.face(side); f.look = { x: p.cx, y: st.ground }; await sleep(400); f.look = null;
    await f.once("wiggle", 1.6); f.say("");
    f.wet = true; const dive = p.cx - side * p.w * .2;
    await f.hop(dive, st.ground + 50, { h: 30, ms: 460, quiet: true });
    splash(st, dive, st.ground);
    await sleep(500); bubbles(st, dive + side * 6, st.ground, 4); await sleep(700);
    // the head comes up: eyes just over the water
    let t0 = performance.now();
    while (true) { const t = Math.min(1, (performance.now() - t0) / 450); f.y = st.ground + 50 - 30 * ease(t); f.render(); if (t >= 1) break; await raf(); }
    ripple(st, f.x, st.ground + 2, 1.2); await f.blink(true);
    const x0 = f.x, x1 = p.cx + side * p.w * .2; t0 = performance.now(); let n = t0;
    while (true) { const t = Math.min(1, (performance.now() - t0) / 1900); f.x = x0 + (x1 - x0) * t; f.y = st.ground + 20 + Math.sin(t * 14) * 1.3; f.tilt = Math.sin(t * 14) * 4; f.render();
      if (performance.now() - n >= 16000 / 60) { n = performance.now(); ripple(st, f.x - f.dir * 10, st.ground + 2, .7); } if (t >= 1) break; await raf(); }
    f.tilt = 0; bubbles(st, f.x + f.dir * 10, st.ground, 2); f.say(""); await sleep(600);
    const out = side > 0 ? Math.min(p.r + 18, st.W - 30) : Math.max(p.l - 18, 30);
    splash(st, f.x, st.ground, 6);
    await f.hop(out, st.ground, { h: 36, ms: 440, quiet: true }); f.wet = false; f.render();
    dust(st, f.x, f.y, -f.dir, 3);
    await f.bd.animate([{ transform: "rotate(0)" }, { transform: "rotate(-14deg)" }, { transform: "rotate(14deg)" }, { transform: "rotate(-9deg)" }, { transform: "rotate(5deg)" }, { transform: "rotate(0)" }], { duration: 560 }).finished;
    for (let i = 0; i < 7; i++) { const d = add(st, "dr"), a = rnd(-2.9, -.25); d.animate([{ transform: `translate(${f.x}px,${f.y - 24}px)` }, { transform: `translate(${f.x + Math.cos(a) * 30}px,${f.y - 24 + Math.sin(a) * 20}px)`, opacity: 0 }], { duration: 420 }).finished.then(() => d.remove()); }
    f.say(""); await f.once("blush");
  };
  // Кувшинка: hops onto the lily pad (it dips), sits like a king, croaks, snaps a fly from there and hops back to the bank
  S.lily = async (st, f) => {
    const p = st.pond; if (!p) return S.perch(st, f);
    const side = f.x < p.cx ? 1 : -1;
    await f.go(side > 0 ? p.l - 16 : p.r + 16, st.ground, { step: 40 });
    f.look = { x: p.lily.x, y: st.ground }; await sleep(300); f.look = null;
    await f.hop(p.lily.x, st.ground, { h: 30, ms: 400, quiet: true });
    await sleep(500); await f.croak(2); await sleep(300);
    const fl = new Bug(st, "fly", side > 0 ? -20 : st.W + 20, st.ground - 50); f.look = fl;
    await fl.to(clamp(f.x - side * 60, 20, st.W - 20), st.ground - 36, 1300); f.face(fl.x > f.x ? 1 : -1); await sleep(300);
    const tg = f.tongue(fl.x, fl.y); await sleep(100); fl.gone(); await tg;
    f.look = null; f.say("ням"); await f.once("gulp"); await f.lick();
    await sleep(500);
    await f.hop(side > 0 ? Math.max(p.l - 18, 30) : Math.min(p.r + 18, st.W - 30), st.ground, { h: 30, ms: 400 });
  };
  // Танец: notes float up, it sways and bounces to the beat, flips round, a spin and «та-да!»
  S.dance = async (st, f) => {
    let on = true;
    const notes = (async () => { while (on) { const n = add(st, "note"); n.textContent = pick(["♪", "♫", "♬"]); const x = f.x + rnd(-22, 22), y = f.y - f.z - SIZE * .75;
      n.animate([{ transform: `translate(${x}px,${y}px) scale(.4)`, opacity: 0 }, { transform: `translate(${x + rnd(-8, 8)}px,${y - 12}px) scale(1) rotate(${rnd(-20, 20)}deg)`, opacity: 1, offset: .3 }, { transform: `translate(${x + rnd(-18, 18)}px,${y - 34}px) scale(.8)`, opacity: 0 }], { duration: 1300 }).finished.then(() => n.remove());
      await sleep(330); } })();
    f.say(""); await sleep(300);
    for (let i = 0; i < 10; i++) {
      const d = i % 2 ? 1 : -1;
      f.tl.animate([{ transform: "none" }, { transform: `rotate(${d * 15}deg)` }, { transform: "none" }], { duration: 320, easing: "ease-in-out" });
      if (i === 4 || i === 7) f.face(-f.dir);
      if (i === 6) f.bd.animate([{ transform: "scaleX(1)" }, { transform: "scaleX(-1)" }, { transform: "scaleX(1)" }], { duration: 320 });
      await f.hopInPlace(i === 9 ? 26 : i % 2 ? 11 : 6);
      if (i % 2) dust(st, f.x, f.y, 0, 2);
    }
    on = false; await notes;
    burst(st, f.x, f.y - 30, 9, 30); f.say(""); f.play("joy"); await f.hopInPlace(14); await f.once("blush");
  };
  // Светлячок (вечером и ночью): a firefly drifts in; the frog swallows it — and its throat glows like a lamp for a while. ик!
  S.firefly = async (st, f) => {
    if (!(st.phase === "night" || st.phase === "evening")) return S.fly(st, f);
    const e = add(st, "ffl"), from = pick([-1, 1]), o = { x: from < 0 ? -10 : st.W + 10, y: st.ground - 50 }; f.look = o;
    const tx = clamp(f.x + f.dir * 55, 20, st.W - 20), t0 = performance.now(), ms = 3000; let live = true;
    (async () => { const x0 = o.x; while (live) { const t = Math.min(1, (performance.now() - t0) / ms); o.x = x0 + (tx - x0) * ease(t) + Math.sin(t * 11) * 8; o.y = st.ground - 50 + t * 16 + Math.cos(t * 9) * 6;
      at(e, o.x, o.y); e.style.opacity = String(.35 + .65 * Math.abs(Math.sin(t * 20))); if (t >= 1) break; await raf(); } })();
    await sleep(ms * .6); f.face(o.x > f.x ? 1 : -1); await f.once("wiggle", 1.6);
    while (performance.now() - t0 < ms - 100) await raf();
    const tg = f.tongue(o.x, o.y); await sleep(100); live = false; e.remove(); await tg;
    f.look = null; await f.once("gulp");
    f.el.classList.add("glow"); f.say(""); await sleep(1600); f.say("ик"); await f.hopInPlace(8); await sleep(1400);
    f.el.classList.remove("glow"); f.hearts(1);
  };
  // RIP (мало денег): it shivers, says goodbye, keels over — ✕✕, tongue out; a little stone «RIP» rises, the ghost floats up
  // with a halo and drifts to «Пополнить» (it glows), comes back into the body — and the frog jolts back to life. A tap revives it at once.
  S.rip = async (st, f) => {
    const b = st.btn;
    f.look = b ? { x: (b.l + b.r) / 2, y: b.t + 10 } : null;
    f.say(""); f.play("croak"); await sleep(1100); f.idle();
    f.look = null; f.say("…"); await sleep(700);
    // the wobble and the fall
    const side = f.dir;   // lies with its face up, head on the side it was facing
    await f.tl.animate([{ transform: "none" }, { transform: `rotate(${-side * 8}deg)` }, { transform: `rotate(${side * 6}deg)` }, { transform: `rotate(${-side * 10}deg)` }], { duration: 650, easing: "ease-in-out", fill: "forwards" }).finished;
    f.a.goToAndStop(300, true); f.el.classList.remove("thr"); f.clip = "dead";
    await f.tl.animate([{ transform: `rotate(${-side * 10}deg)` }, { transform: `translateY(-26px) rotate(${side * 98}deg)`, offset: .75 }, { transform: `translateY(-21px) rotate(${side * 90}deg)` }],
      { duration: 420, easing: "cubic-bezier(.5,0,.8,.5)", fill: "forwards" }).finished;
    f.el.classList.add("dead"); dust(st, f.x + side * 18, f.y, side, 5);
    f.bd.animate([{ transform: "none" }, { transform: "scale(1.08,.9)" }, { transform: "none" }], { duration: 260 });
    // the stone rises behind
    const sx = clamp(f.x - side * 30, 16, st.W - 16), stn = add(st, "stone", "<b>RIP</b>"); stn.style.cssText = `left:${sx - 13}px;top:${st.ground - 32 + 1}px`;
    const sb = stn.firstChild;
    await sleep(350);
    await sb.animate([{ transform: "translateY(32px)" }, { transform: "translateY(-2px)", offset: .8 }, { transform: "translateY(0)" }], { duration: 650, easing: "cubic-bezier(.3,.9,.4,1)", fill: "forwards" }).finished;
    dust(st, sx, st.ground, 0, 3);
    const fl = add(st, "fx plain"); fl.textContent = "🌷"; fl.style.fontSize = "11px"; at(fl, sx + 6, st.ground - 13);
    fl.animate([{ opacity: 0, transform: `translate(${sx + 6}px,${st.ground - 6}px) scale(.2)` }, { opacity: 1, transform: `translate(${sx + 6}px,${st.ground - 13}px) scale(1)` }], { duration: 400, easing: "cubic-bezier(.3,1.6,.5,1)", fill: "forwards" });
    await sleep(500);
    // the ghost
    const gh = add(st, "gh"); gh.appendChild(f.fc.querySelector("svg").cloneNode(true)); gh.insertAdjacentHTML("beforeend", '<i class="halo"></i>');
    if (f.dir > 0) gh.firstChild.style.transform = "scaleX(-1)";
    const gp = { x: f.x, y: f.y }; let ghostOn = true, gt = 0, glast = performance.now();
    const float = (async () => { while (ghostOn) { const gnow = performance.now(); gt += .05 * frames(glast, gnow); glast = gnow; at(gh, gp.x + Math.sin(gt * 1.3) * 4, gp.y + Math.sin(gt * 2) * 2, `rotate(${Math.sin(gt * 1.3) * 5}deg)`); await raf(); } })();
    const move = (x, y, ms) => { const x0 = gp.x, y0 = gp.y, t0 = performance.now(); return new Promise((ok) => { const k = () => { const t = Math.min(1, (performance.now() - t0) / ms), e = ease(t); gp.x = x0 + (x - x0) * e; gp.y = y0 + (y - y0) * e; t < 1 ? requestAnimationFrame(k) : ok(); }; k(); }); };
    gh.animate([{ opacity: 0 }, { opacity: .7 }], { duration: 700, fill: "forwards" });
    st.wake = null; let woke = false; const wake = new Promise((r) => { st.wake = () => { woke = true; r(); }; });
    const ghostTrip = (async () => {
      await move(f.x, f.y - 34, 1300);
      if (woke) return;  await sleep(900);
      if (b && !woke) {
        await move(clamp(f.x + (f.x < st.W / 2 ? 70 : -70), 50, st.W - 50), st.ground - 26, 1400);
        if (woke) return;
        pop(st, gp.x, gp.y - SIZE * .8, "₽", { side: f.x < st.W / 2 ? 1 : -1 });
        for (let i = 0; i < 2; i++) await b.el.animate([{ transform: "none", boxShadow: "0 0 0 0 rgba(255,255,255,0)" }, { transform: "scale(1.04)", boxShadow: "0 0 18px 4px rgba(255,255,255,.7)" }, { transform: "none", boxShadow: "0 0 0 0 rgba(255,255,255,0)" }], { duration: 650 }).finished;
        await sleep(600);
      }
      if (!woke) await move(f.x, f.y - 20, 1300);
    })();
    await Promise.race([ghostTrip, wake]); st.wake = null;
    // back into the body
    await move(f.x, f.y - 6, 300);
    await gh.animate([{ opacity: .7 }, { opacity: 0, transform: `translate(${f.x}px,${f.y}px) scale(.6)` }], { duration: 260, fill: "forwards" }).finished;
    ghostOn = false; await float; gh.remove();
    burst(st, f.x, f.y - 20, 8, 22);
    f.el.classList.remove("dead");
    f.tl.animate([{ transform: `translateY(-21px) rotate(${side * 90}deg)` }, { transform: `translateY(-24px) rotate(${-side * 10}deg)`, offset: .6 }, { transform: "none" }], { duration: 380, easing: "cubic-bezier(.3,1.4,.5,1)" });
    f.tl.getAnimations().forEach((a) => a.playState === "finished" && a.cancel());
    f.clip = "idle"; await f.shock();
    f.say("ква"); await sleep(500);
    await sb.animate([{ transform: "translateY(0)" }, { transform: "translateY(34px)" }], { duration: 500, easing: "ease-in", fill: "forwards" }).finished;
    stn.remove(); fl.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 300 }).finished.then(() => fl.remove());
    f.hearts(1); f.idle();
  };

  // Листик: a leaf flutters down and lands on its head; it holds still, looks up — and shakes it off
  S.leaf = async (st, f) => {
    const lf = add(st, "leaf"), m = new Date().getMonth(); if (m >= 2 && m <= 7) lf.style.background = "linear-gradient(135deg,#b6f27e,#3fbf5f)";
    const x0 = clamp(f.x + rnd(-40, 40), 10, st.W - 10), o = { x: x0, y: -12 }; f.look = o;
    const head = () => [f.x + f.dir * -2, f.y - SIZE * .74], t0 = performance.now(), ms = 2600;
    while (true) { const t = Math.min(1, (performance.now() - t0) / ms), [hx, hy] = head();
      o.x = x0 + (hx - x0) * ease(t) + Math.sin(t * 10) * 14 * (1 - t); o.y = -12 + (hy + 12) * t;
      at(lf, o.x, o.y, `rotate(${Math.sin(t * 10) * 40 * (1 - t)}deg)`); if (t >= 1) break; await raf(); }
    f.look = { x: f.x, y: -40 }; await sleep(800); f.say("?"); await f.blink(); await sleep(500);
    const [hx, hy] = head();
    lf.animate([{ transform: `translate(${hx}px,${hy}px)` }, { transform: `translate(${hx - f.dir * 20}px,${hy - 12}px) rotate(-60deg)`, offset: .3 }, { transform: `translate(${hx - f.dir * 46}px,${st.ground}px) rotate(200deg)`, opacity: 0 }],
      { duration: 1000, easing: "ease-in" }).finished.then(() => lf.remove());
    await f.bd.animate([{ transform: "rotate(0)" }, { transform: "rotate(-12deg)" }, { transform: "rotate(12deg)" }, { transform: "rotate(-6deg)" }, { transform: "rotate(0)" }], { duration: 480 }).finished;
    f.look = null; await f.croak(1);
  };
  // Отражение: it hops to the pond's edge, peeks into the water, sees itself — ква? — and gets shy
  S.mirror = async (st, f) => {
    const p = st.pond; if (!p) return S.wander(st, f);
    const side = f.x < p.cx ? 1 : -1, bank = side > 0 ? p.l - 12 : p.r + 12;
    await f.go(bank, st.ground, { step: 40 }); f.face(side);
    f.look = { x: bank + side * 22, y: st.ground + 6 }; await sleep(600);
    await f.once("peek"); ripple(st, bank + side * 22, st.ground + 2, .8); await sleep(400);
    f.say("ква?"); await sleep(900); bubbles(st, bank + side * 24, st.ground, 2); await sleep(500);
    f.look = null; await f.once("blush"); f.hearts(1);
  };
  // Мошка (between scenes): a gnat comes close and is snapped up on the spot
  S.gnat = async (st, f) => {
    const side = f.dir, fl = new Bug(st, "fly", side > 0 ? st.W + 15 : -15, st.ground - 60); fl.r = 6; f.look = fl;
    await fl.to(clamp(f.x + side * 50, 15, st.W - 15), st.ground - 38, 900); f.face(fl.x > f.x ? 1 : -1);
    const tg = f.tongue(fl.x, fl.y, 200); await sleep(90); fl.gone(); await tg; f.look = null; await f.once("gulp", 1.5);
  };
  // Покормить: you tap the sky — a fly appears there; the frog comes and catches it
  S.feed = async (st, f, x, y) => {
    burst(st, x, y, 5, 10); const fl = new Bug(st, "fly", x, y); fl.r = 7; f.look = fl; f.say("!");
    const tx = clamp(x, 20, st.W - 20), ty = clamp(y, st.ground - 70, st.ground - 32);
    fl.to(tx, ty, 700); await sleep(500);
    const side = tx > f.x ? 1 : -1; f.face(side);
    if (Math.abs(tx - f.x) > 70) await f.go(inField(st, tx - side * 55), st.ground, { step: 40, h: 18, ms: 260 });
    f.face(fl.x > f.x ? 1 : -1); await f.once("wiggle", 1.6);
    const tg = f.tongue(fl.x, fl.y); await sleep(100); fl.gone(); await tg;
    f.look = null; f.say("ням"); await f.once("gulp"); await f.lick(); f.hearts(2);
  };

  // ---- rare ones: seen now and then, not every visit
  // Шарик: a balloon drifts in; the frog jumps for the string, floats up a little — уи! — lets go and watches it fly away
  S.balloon = async (st, f) => {
    const from = pick([-1, 1]), b = add(st, "bal"); b.style.setProperty("--c", pick(["#ff5d7a", "#ffb02e", "#4fb4ff", "#9b7bff"]));
    const pos = { x: from < 0 ? -20 : st.W + 20, y: st.ground - 96 }; let held = false, live = true; const t0 = performance.now();
    const grab = () => [f.x + f.dir * 14, f.y - f.z - SIZE * .4 - 47];   // the string's end in the frog's paw
    const o = { get x() { return held ? grab()[0] : pos.x; }, get y() { return held ? grab()[1] : pos.y; } }; f.look = o;
    (async () => { while (live && !st.dead) { const t = (performance.now() - t0) / 1000; at(b, o.x, o.y + (held ? 0 : Math.sin(t * 2.2) * 3), `rotate(${Math.sin(t * 1.7) * 6}deg)`); await raf(); } b.remove(); })();
    const glide = async (x, y, ms) => { const x0 = pos.x, y0 = pos.y, s = performance.now();
      while (true) { const k = Math.min(1, (performance.now() - s) / ms), e = ease(k); pos.x = x0 + (x - x0) * e; pos.y = y0 + (y - y0) * e; if (k >= 1) break; await raf(); } };
    const bx = inField(st, f.x + from * rnd(20, 50));
    await glide(bx, st.ground - 96, 2400);
    f.say("!"); const side = bx > f.x ? 1 : -1;
    if (Math.abs(bx - f.x) > 20) await f.go(bx - side * 14, st.ground, { step: 34, h: 12, ms: 260 });
    f.face(side); await glide(f.x + f.dir * 14, f.y - 23 - SIZE * .4 - 47, 400); await f.once("wiggle", 1.4);
    try {
      f.moving = true; f.play("hop");
      await f.move(380, (t) => { f.z = 23 * Math.sin(t * Math.PI / 2); });
      held = true; f.play("joy"); f.say("уи!");
      await f.move(1500, (t) => { f.z = 23 + 14 * Math.sin(t * Math.PI) + 3 * Math.sin(t * Math.PI * 4); f.tilt = Math.sin(t * Math.PI * 4) * 6; });
      [pos.x, pos.y] = grab(); held = false;
      glide(pos.x + rnd(-40, 40), -70, 2600).then(() => { live = false; });
      await f.move(330, (t) => { f.z = 23 * (1 - t * t); f.tilt = 0; });
    } finally { f.z = 0; f.tilt = 0; f.render(); f.moving = false; }
    dust(st, f.x, f.y, 0, 4); f.idle(); f.look = o; await sleep(1500); f.look = null; f.say("…"); await sleep(600); await f.croak(1);
  };
  // Звезда желаний (вечером и ночью): a shooting star crosses the sky; the frog closes its eyes and makes a wish
  S.wish = async (st, f) => {
    if (!(st.phase === "night" || st.phase === "evening")) return S.rainbow(st, f);
    const x0 = rnd(st.W * .55, st.W - 20), y0 = rnd(6, 20), x1 = x0 - rnd(140, 200), y1 = y0 + rnd(40, 60), ang = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI;
    const o = { x: x0, y: y0 }; f.look = o; await sleep(300);
    const s = add(st, "ssr"), ms = 900, t0 = performance.now();
    s.animate([{ transform: `translate(${x0}px,${y0}px) rotate(${ang}deg) scaleX(.2)`, opacity: 0 }, { transform: `translate(${x0 + (x1 - x0) * .2}px,${y0 + (y1 - y0) * .2}px) rotate(${ang}deg) scaleX(1)`, opacity: 1, offset: .2 },
      { transform: `translate(${x1}px,${y1}px) rotate(${ang}deg) scaleX(.6)`, opacity: 0 }], { duration: ms, easing: "ease-in" }).finished.then(() => s.remove());
    while (performance.now() - t0 < ms) { const k = (performance.now() - t0) / ms; o.x = x0 + (x1 - x0) * k; o.y = y0 + (y1 - y0) * k; await raf(); }
    f.say("!"); await f.hopInPlace(10); f.look = null;
    f.play("sleep"); await sleep(700); f.say("…"); await sleep(1500);
    f.idle(); burst(st, f.x, f.y - 36, 8, 24); f.hearts(3); await f.once("joy");
  };
  // Радуга (днём): a rainbow comes up over the field; the frog stares — ого — and hops for joy
  S.rainbow = async (st, f) => {
    const cx = inField(st, f.x + pick([-1, 1]) * rnd(60, 110)), r = document.createElement("div"); r.className = "rbw";
    r.style.cssText = `left:${cx - 110}px;top:${st.ground - 104}px`; st.bg.appendChild(r);
    f.look = { x: cx, y: st.ground - 90 }; f.face(cx > f.x ? 1 : -1);
    await r.animate([{ opacity: 0, transform: "scale(.96)" }, { opacity: 1, transform: "none" }], { duration: 1600, easing: "ease-out", fill: "forwards" }).finished;
    f.say("ого"); await f.once("joy"); await f.hopInPlace(16); f.hearts(2); await sleep(1500); f.look = null;
    r.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 2000, fill: "forwards" }).finished.then(() => r.remove());
    await f.croak(1);
  };
  const RARE = ["balloon", "wish"];

  const WINTER = [10, 11, 0, 1].includes(new Date().getMonth());
  // the weather: the same for everyone within the same three hours, chosen by the season
  const WEATHER = (() => { const d = new Date(), seed = ((d.getFullYear() * 13 + d.getMonth()) * 32 + d.getDate()) * 8 + (d.getHours() / 3 | 0);
    let r = Math.sin(seed * 12.9898) * 43758.5453; r -= Math.floor(r);
    const odds = WINTER ? [["clear", .35], ["clouds", .22], ["snow", .33], ["fog", .1]] : [["clear", .44], ["clouds", .22], ["rain", .14], ["fog", .07], ["wind", .13]];
    for (const [k, p] of odds) if ((r -= p) < 0) return k; return "clear"; })();
  const WEIGHTS = { wander: 3, fly: 3, chase: 2, perch: 2, button: 2, coin: 2, rain: WINTER ? 1 : 2, dragonfly: WINTER ? 1 : 2, run: 1, sleep: 1,
    butterfly: 2, bubble: 2, friend: 1, swim: 2, lily: 2, dance: 1, firefly: 3, leaf: 2, mirror: 2, ...(WINTER ? { snowflake: 2 } : {}) };
  // low balance: fewer games, more cold, and the RIP drama now and then
  const COLD = { rip: 3, wander: 2, fly: 2, coin: 2, leaf: 1, butterfly: 1, bubble: 1, perch: 1, button: 2, lily: 1, ...(WINTER ? { snowflake: 1 } : {}) };

  // the field itself: a soft hill the frog stands on, grass on it, and the sky over it follows the mood
  const decor = (st, mood) => {
    const bg = st.bg, mk = (cls, css = "") => { const e = document.createElement("div"); e.className = cls; e.style.cssText = css; bg.appendChild(e); return e; };
    bg.innerHTML = ""; bg.className = "petbg";
    const ph = st.phase = mood === "sleep" ? "night" : st.phase, wx = st.weather || "clear", W = st.W, G = st.ground;
    const dark = ph === "night" || ph === "evening", grey = wx === "clouds" || wx === "rain" || wx === "snow" || wx === "fog";
    const live = (fn, ms) => { const t = setInterval(() => { if (st.dead) { clearInterval(t); return; } if (document.hidden || !st.hc.isConnected) return; fn(); }, ms); };
    if (dark) bg.classList.add("dark"); if (wx === "wind") bg.classList.add("windy");
    const stars = (n) => { for (let i = 0; i < n; i++) { const z = rnd(1, 2.4); mk("star" + (z > 2.1 ? " big" : ""), `left:${rnd(2, 98)}%;top:${rnd(3, G - 18)}px;width:${z}px;height:${z}px;animation-delay:${-rnd(0, 3)}s;animation-duration:${rnd(1.8, 4)}s;opacity:${rnd(.35, .95)}`); } };
    // the moon in today's phase: a shadow slides over the lit disc
    const moon = (o = 1) => { const w = mk("mw", `opacity:${o}`), m = document.createElement("div"); m.className = "moon"; w.appendChild(m);
      const off = MOON < .5 ? -Math.max(MOON, .07) / .5 : Math.max(1 - MOON, .07) / .5; m.innerHTML = `<i style="left:${(off * 100).toFixed(1)}%"></i>`; };

    // ---- the sky
    if (ph === "night") { mk("night"); if (!grey) mk("milky"); stars(grey ? 6 : 34); moon(grey ? .45 : 1); }
    else if (ph === "evening") { mk("twi"); stars(grey ? 3 : 12); moon(grey ? .35 : .8); }
    else if (ph === "sunset") { mk("sunset"); mk("sdisk", `left:${W * .46}px;top:${G - 34}px;opacity:${grey ? .45 : 1}`); mk("sun low"); }
    else if (ph === "morning") { mk("dawn"); if (!grey) mk("rays"); mk("sun", grey ? "opacity:.4" : ""); }
    else { if (!grey) mk("rays"); mk("sun", grey ? "opacity:.35" : ""); }
    if (wx === "clouds" || wx === "snow") mk("ovc"); if (wx === "rain") mk("ovc wet"); if (wx === "fog") mk("haze");
    if (wx === "snow") mk("frost");

    // clouds drift across: more of them and heavier when it is grey, quicker in the wind, lit pink at sunset
    const nc = { clear: 2, clouds: 5, rain: 6, snow: 4, fog: 2, wind: 3 }[wx] ?? 2;
    const cc = wx === "rain" ? "rgba(214,220,232,.4)" : ph === "sunset" ? "rgba(255,186,176,.42)" : ph === "evening" ? "rgba(190,176,236,.22)" : ph === "night" ? "rgba(190,200,255,.1)" : "rgba(255,255,255,.28)";
    for (let i = 0; i < nc; i++) { const c = mk("cld", `background:${cc}`), y = rnd(6, Math.max(12, G - 48)), d = rnd(38000, 60000) / (wx === "wind" ? 3 : 1), sc = rnd(.7, 1.1) * (grey ? 1.3 : 1);
      c.animate([{ transform: `translate(-80px,${y}px) scale(${sc})` }, { transform: `translate(${W + 30}px,${y}px) scale(${sc})` }], { duration: d, iterations: Infinity, delay: -d * ((i + rnd(0, 1)) / nc) }); }
    // birds over the hills at sunrise and sunset
    if ((ph === "sunset" || ph === "morning") && wx !== "rain" && wx !== "snow") {
      const col = ph === "sunset" ? "rgba(60,20,50,.55)" : "rgba(255,255,255,.6)", bird = `<svg width="10" height="5" viewBox="0 0 10 5"><path d="M0 1.5Q2.5 0 5 3Q7.5 0 10 1.5" fill="none" stroke="${col}" stroke-width="1.2" stroke-linecap="round"/></svg>`;
      [[0, 0], [12, 5], [-9, 6]].forEach(([dx, dy], i) => { const e = mk("brd"); e.innerHTML = bird; e.firstChild.style.animationDelay = `${-i * .17}s`; const y = G * .3 + dy, d = 26000;
        e.animate([{ transform: `translate(${W + 30 + dx}px,${y}px)` }, { transform: `translate(${-40 + dx}px,${y - 14}px)` }], { duration: d, iterations: Infinity, delay: -d * .35 }); });
    }
    // a falling star now and then on a clear night
    if (ph === "night" && !grey) live(() => { if (Math.random() > .3) return; const s = mk("ssr"), x0 = rnd(W * .3, W), y0 = rnd(4, G * .4), x1 = x0 - rnd(70, 120), y1 = y0 + rnd(20, 40), a = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI;
      s.animate([{ transform: `translate(${x0}px,${y0}px) rotate(${a}deg) scaleX(.2)`, opacity: 0 }, { opacity: .9, offset: .25 }, { transform: `translate(${x1}px,${y1}px) rotate(${a}deg) scaleX(.7)`, opacity: 0 }], { duration: 700, easing: "ease-in" }).finished.then(() => s.remove()); }, 5000);

    // ---- far and near hills for depth, with a tree line and bushes (they drift a little with your finger)
    const hc = ph === "sunset" ? "72,22,74" : dark ? "10,10,40" : "255,255,255";
    [["far", 22, 13, 61, ph === "sunset" ? .42 : dark ? .24 : .08], ["mid", 10, 7, 29, ph === "sunset" ? .3 : dark ? .17 : .1]].forEach(([cls, off, amp, wl, op], j) => {
      const w = W + 24, base = amp + 2, hh = off + base + 6, up = 14, ry = (x) => base - amp * (.55 + .45 * Math.sin(x / wl + j * 2.1)) * (.6 + .4 * Math.sin(x / (wl * 2.7) + j));
      let d = `M0 ${hh}`; for (let x = 0; x <= w; x += 8) d += ` L${x} ${ry(x).toFixed(1)}`; d += ` L${w} ${hh}Z`;
      let deco = "";
      if (j === 0) for (let x = rnd(10, 40); x < w - 10; x += rnd(22, 60)) { const y = ry(x) + 2, k = rnd(.7, 1.2);
        deco += Math.random() < .6 ? `<path d="M${x} ${(y - 11 * k).toFixed(1)}L${(x + 4.5 * k).toFixed(1)} ${y}H${(x - 4.5 * k).toFixed(1)}Z"/>` : `<circle cx="${x}" cy="${(y - 5 * k).toFixed(1)}" r="${(4.5 * k).toFixed(1)}"/><rect x="${x - .7}" y="${(y - 2).toFixed(1)}" width="1.4" height="3"/>`; }
      else for (let x = rnd(30, 80); x < w - 20; x += rnd(70, 140)) { const y = ry(x) + 2; deco += `<circle cx="${x}" cy="${y - 2}" r="4"/><circle cx="${x + 5}" cy="${y - 3.5}" r="5"/><circle cx="${x + 10}" cy="${y - 1.5}" r="3.6"/>`; }
      mk(cls, `top:${G - off - base + 2 - up}px;width:${w}px;height:${hh + up}px`).innerHTML = `<svg width="${w}" height="${hh + up}"><g transform="translate(0 ${up})" fill="rgb(${hc})" fill-opacity="${op}"><path d="${d}"/>${deco}</g></svg>`;
    });
    st.on("pointermove", (e) => { const b = st.hc.getBoundingClientRect(), k = (e.clientX - b.left) / b.width - .5;
      bg.querySelector(".far").style.translate = `${(-k * 10).toFixed(1)}px 0`; bg.querySelector(".mid").style.translate = `${(-k * 5).toFixed(1)}px 0`; });
    // the hill: a gentle wave along the ground, lighter than the card, fading down behind the balance (snow lies on it in winter)
    const top = G - 5, h = st.H - top, snowy = wx === "snow" || (WINTER && new Date().getMonth() !== 10);
    let d = `M0 ${5 + Math.sin(0) * 1.5}`; for (let x = 0; x <= W + 20; x += 20) d += ` L${x} ${(5 + Math.sin(x / 37) * 1.6 + Math.sin(x / 13) * .5).toFixed(1)}`;
    const id = "hg" + Math.random().toString(36).slice(2, 7), tint = ph === "sunset" ? "255,222,196" : dark ? "190,200,255" : "255,255,255", a0 = snowy ? .4 : dark ? .12 : .18;
    mk("hill", `top:${top}px;width:${W}px;height:${h}px`).innerHTML = `<svg width="${W}" height="${h}"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="rgb(${tint})" stop-opacity="${a0}"/><stop offset="${snowy ? .25 : .5}" stop-color="rgb(${tint})" stop-opacity="0"/></linearGradient></defs>
      <path d="${d} L${W + 20} ${h} L0 ${h}Z" fill="url(#${id})"/><path d="${d}" fill="none" stroke="rgb(${tint})" stroke-opacity="${snowy ? .75 : .35}" stroke-width="${snowy ? 2.6 : 1.5}"/></svg>`;
    // the pond with a lily pad and reeds, on the right side of the field
    if (W >= 300) {
      const pw = 96, cx = W - 60 - pw / 2, p = st.pond = { l: cx - pw / 2, r: cx + pw / 2, cx, w: pw };
      mk("pond" + (ph === "sunset" ? " warm" : dark ? " dark" : ""), `left:${p.l}px;top:${G - 5}px;width:${pw}px`);
      [[p.l + 3, 24, 0], [p.l + 9, 17, -.8], [p.r - 5, 21, -1.6]].forEach(([x, h, dl]) => mk("reed", `left:${x}px;top:${G - h + 3}px;height:${h}px;animation-delay:${dl}s`));
      const le = add(st, "lily", "<i></i>"), lx = cx + 10; le.style.left = `${lx}px`; le.style.top = `${G + 1}px`;
      le.animate([{ transform: "translateY(0) rotate(0)" }, { transform: "translateY(1px) rotate(2deg)" }, { transform: "translateY(0) rotate(0)" }], { duration: 3200, iterations: Infinity, easing: "ease-in-out" });
      p.lily = { x: lx, el: le, dip: () => { le.animate([{ translate: "0 0" }, { translate: "0 3px" }, { translate: "0 -1px" }, { translate: "0 0" }], { duration: 600, easing: "ease-out" }); ripple(st, lx, G + 2, 1.2); } };
    }
    mk("mist", `top:${G + 4}px`);
    const inPond = (x, m) => st.pond && x > st.pond.l - m && x < st.pond.r + m;
    // pebbles, and in autumn a mushroom or two
    for (let x = rnd(40, 90); x < W - 20; x += rnd(80, 150)) if (!inPond(x, 10)) mk("pb", `left:${x}px;top:${G + rnd(4, 9)}px;transform:scale(${rnd(.7, 1.2).toFixed(2)})`);
    if ([7, 8, 9].includes(new Date().getMonth())) for (let i = 0; i < 2; i++) { const x = rnd(20, W - 30); if (!inPond(x, 12)) mk("msh", `left:${x}px;top:${G + 4}px;transform:scale(${rnd(.8, 1.1).toFixed(2)})`); }
    st.grass = [];
    const blade = `<svg viewBox="0 0 16 10" width="16" height="10"><path d="M3 10C3 6 1.5 3 0 1c2.5 1.5 4 4.5 4.5 9M8 10c0-4 .5-7 1.5-10 1 3 .5 7 0 10M12 10c.5-3 2-5.5 4-7-1.5 2-2.5 4.5-2.8 7" fill="#fff"/></svg>`;
    for (let x = rnd(14, 30); x < W - 14; x += rnd(30, 54)) {
      if (inPond(x, 8)) continue;
      const s = +rnd(.7, 1.15).toFixed(2), el = mk("gt", `left:${x}px;top:${G + 2}px;transform:scale(${s})`); el.innerHTML = blade;
      el.firstChild.style.animationDelay = `${-rnd(0, 3)}s`; st.grass.push({ x, el, s });
    }
    // little flowers in the grass (not under snow)
    const FL = ["#fff", "#ffc2dd", "#fff3a0", "#cfe3ff"];
    if (!snowy) for (let x = rnd(24, 60); x < W - 20; x += rnd(46, 90)) { if (inPond(x, 10)) continue;
      mk("flw", `left:${x}px;top:${G + 2}px;background:${pick(FL)};animation-delay:${-rnd(0, 3)}s`); }

    // ---- the weather on the field
    if (wx === "rain") {
      // rain: streaks falling all the time (compositor loops), splashes on the ground, rings on the pond
      for (let i = 0; i < 26; i++) { const e = mk("rn"), x = rnd(-10, W + 10), d = rnd(520, 760), y1 = G + rnd(0, 14);
        e.animate([{ transform: `translate(${x}px,-14px) rotate(12deg)`, opacity: .9 }, { transform: `translate(${x - 9}px,${y1}px) rotate(12deg)`, opacity: .6 }], { duration: d, iterations: Infinity, delay: -rnd(0, d), easing: "linear" }); }
      for (let i = 0; i < 9; i++) { const e = mk("spl"), x = rnd(10, W - 10); if (inPond(x, 0)) continue; const d = rnd(700, 1100);
        e.animate([{ transform: `translate(${x}px,${G + 3}px) scale(.3)`, opacity: .9 }, { transform: `translate(${x}px,${G + 3}px) scale(1.4)`, opacity: 0, offset: .5 }, { transform: `translate(${x}px,${G + 3}px) scale(1.4)`, opacity: 0 }], { duration: d, iterations: Infinity, delay: -rnd(0, d) }); }
      if (st.pond) live(() => ripple(st, rnd(st.pond.l + 10, st.pond.r - 10), G + 2, .55), 650);
    }
    if (wx === "fog") [[G - 26, 16000, 0], [G - 6, 21000, 1], [G - 52, 26000, 2]].forEach(([y, d, i]) => { const e = mk("fog");
      e.animate([{ transform: `translate(-30px,${y}px)` }, { transform: `translate(30px,${y}px)` }], { duration: d, iterations: Infinity, direction: "alternate", easing: "ease-in-out", delay: -i * 5000 }); });
    if (wx === "wind") live(() => { const l = mk("leaf"), y0 = rnd(10, G - 6), d = rnd(2600, 3800), m = new Date().getMonth(); if (m >= 2 && m <= 7) l.style.background = "linear-gradient(135deg,#b6f27e,#3fbf5f)";
      l.animate([{ transform: `translate(-20px,${y0}px) rotate(0)` }, { transform: `translate(${W * .5}px,${y0 + rnd(-24, 18)}px) rotate(300deg)`, offset: .5 }, { transform: `translate(${W + 20}px,${y0 + rnd(-10, 30)}px) rotate(640deg)` }], { duration: d, easing: "linear" }).finished.then(() => l.remove()); }, 1700);
    if (dark && wx !== "rain") for (let i = 0; i < (ph === "night" ? 4 : 2); i++) { const e = add(st, "ffl"); let t = rnd(0, 99); const k = rnd(.6, 1.2), cx = rnd(30, W - 30), cy = rnd(20, G - 4); let last = performance.now();
      const tick = () => { if (st.dead) return; const now = performance.now(), fk = frames(last, now); last = now; if (!st.hc.isConnected) { requestAnimationFrame(tick); return; } t += .006 * k * fk; at(e, cx + Math.sin(t * 2.1) * 34, cy + Math.cos(t * 1.4) * 12); e.style.opacity = String(.3 + .7 * Math.abs(Math.sin(t * 5))); requestAnimationFrame(tick); }; tick(); }
    if (wx === "snow") live(() => { const s = add(st, "sn"), x = rnd(0, W), d = rnd(4500, 7500), sz = rnd(.5, 1.2);
      s.animate([{ transform: `translate(${x}px,-6px) scale(${sz})` }, { transform: `translate(${x + rnd(-30, 30)}px,${G + rnd(-4, 30)}px) scale(${sz})`, opacity: .8, offset: .92 }, { transform: `translate(${x + rnd(-30, 30)}px,${G + 30}px) scale(${sz})`, opacity: 0 }], { duration: d, easing: "linear" }).finished.then(() => s.remove()); }, 450);
  };

  // a frog living on this card. mood: "ok" (everything), "cold" (low balance: shivers, says «брр»), "sleep" (paused: sleeps)
  window.petLive = async (hc, { skin = 3, mood = "ok", scenes = null, gap = [1500, 3500], time = null, weather = null, onPlay = null } = {}) => {
    const played = () => { try { onPlay && onPlay(); } catch {} };
    await raf();
    if (window.petKill) window.petKill();
    hc.classList.add("haspet"); const st = stage(hc);
    // the cabinet redraws the home card on every visit: the same frog moves into the new card and carries on
    const home = async () => { while (!st.dead && !st.hc.isConnected) await sleep(300); return !st.dead; };
    window.petKill = () => { st.dead = true; st.layer.remove(); st.bg.remove(); window.petKill = window.petAdopt = null; };
    window.petAdopt = (card, m) => {
      if (st.dead || m !== mood) return false;
      if (card === st.hc) return true;
      const old = { W: st.W, ground: st.ground, hc: st.hc };
      card.classList.add("haspet"); card.prepend(st.layer); card.prepend(st.bg); st.hc = card; measure(st);
      if (Math.abs(st.W - old.W) > 2 || Math.abs(st.ground - old.ground) > 2) { st.hc = old.hc; window.petKill(); return false; }
      for (const [type, fn] of st.binds) { old.hc.removeEventListener(type, fn); card.addEventListener(type, fn); }
      return true;
    }; st.phase = time || PHASE; st.weather = weather || WEATHER; decor(st, mood); const f = new Frog(st, skin); f.skin = skin; f.mood = null; await f.ready;
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    // your finger / cursor: the frog looks at it; a tap on the card calls it over; a tap on the frog startles it
    st.on("pointermove", (e) => { const b = st.hc.getBoundingClientRect(); st.pointer = { x: e.clientX - b.left, y: e.clientY - b.top, t: performance.now() }; });
    st.on("pointerdown", (e) => { const b = st.hc.getBoundingClientRect(); st.pointer = { x: e.clientX - b.left, y: e.clientY - b.top, t: performance.now() }; });
    // a tap on the pond: rings on the water, the frog glances there; a tap in the sky: a fly for the frog (once in a while)
    st.on("click", (e) => { if (e.target.closest("button,a")) return; const b = st.hc.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top, p = st.pond;
      if (p && x > p.l && x < p.r && Math.abs(y - st.ground) < 12) { ripple(st, x, st.ground + 2, 1); const g = f.glance = { x, y: st.ground }; setTimeout(() => { if (f.glance === g) f.glance = null; }, 1200); played(); return; }
      if (st.busy) return;
      const now = performance.now();
      if (y < st.ground - 34 && now - (st.feedAt || 0) > 6000) { st.feedAt = now; st.feed = { x: clamp(x, 20, st.W - 20), y: Math.max(y, 12) }; played(); return; }
      st.call = inField(st, x); played(); });
    let taps = 0, tapAt = 0;
    f.el.addEventListener("click", async (e) => { e.stopPropagation(); if (st.noClick) { st.noClick = false; return; } navigator.vibrate?.(12); played();
      if (st.wake) { st.wake(); st.wake = null; return; }
      const now = performance.now(); taps = now - tapAt < 900 ? taps + 1 : 1; tapAt = now;
      if (taps >= 3) { taps = 0; f.say("!!", { size: 11 }); st.flee = true; return; }
      if (f.moving) return;
      if (taps === 2 && !st.busy) { f.flip(); return; }
      f.shock(); });
    // the finger right next to it: a little flinch
    st.on("pointermove", () => { const p = st.pointer, now = performance.now();
      if (st.busy || f.moving || now - (st.flinchAt || 0) < 2500 || Math.hypot(p.x - f.x, p.y - (f.y - SIZE * .4)) > 30) return;
      st.flinchAt = now; f.hopInPlace(7); f.bd.animate([{ transform: "none" }, { transform: `translateX(${-f.dir * 3}px) scale(.94,1.06)` }, { transform: "none" }], { duration: 260 }); });
    // tickle: the finger goes back and forth over the frog (4 turns within a second)
    const tk = { x: null, dir: 0, rev: [] };
    st.on("pointermove", () => { const p = st.pointer;
      if (!p || Math.hypot(p.x - f.x, p.y - (f.y - f.z - SIZE * .4)) > 34) { tk.x = null; tk.dir = 0; return; }
      if (tk.x == null) tk.x = p.x;
      else if (Math.abs(p.x - tk.x) > 3) { const d = Math.sign(p.x - tk.x); if (tk.dir && d !== tk.dir) tk.rev.push(p.t); tk.dir = d; tk.x = p.x; }
      tk.rev = tk.rev.filter((t) => p.t - t < 1000);
      if (tk.rev.length >= 4 && !st.busy && !f.moving && !f.held && p.t - (st.tickleAt || 0) > 3000) { st.tickleAt = p.t; tk.rev = []; played(); f.tickle(); } });
    // grab it: drag the frog around and throw it (it flies, bounces, gets dizzy — or lands in the pond); hold still on it — it melts
    f.el.addEventListener("pointerdown", (e) => {
      if (st.busy || f.moving || f.held || still) return;
      e.preventDefault(); try { f.el.setPointerCapture(e.pointerId); } catch {}
      const b0 = st.hc.getBoundingClientRect(), sx = e.clientX, sy = e.clientY, hist = []; let mode = null, done;
      st.grab = new Promise((r) => { done = r; }); st.busy = true; played();
      let petOn = false;
      const petT = setTimeout(async () => { if (mode) return; mode = "pet"; petOn = true; f.play("croak", true, .5); f.say("♥");
        while (petOn) { f.hearts(1); f.bd.animate([{ transform: "none" }, { transform: "scale(1.04,.96)" }, { transform: "none" }], { duration: 500 }); await sleep(520); } }, 420);
      const mv = (ev) => { const x = ev.clientX - b0.left, y = ev.clientY - b0.top; hist.push([x, y, performance.now()]); if (hist.length > 6) hist.shift();
        if (!mode && Math.hypot(ev.clientX - sx, ev.clientY - sy) > 6) { clearTimeout(petT); mode = "drag"; f.held = true; f.el.classList.add("held"); f.look = null; f.play("shock"); f.say(pick(["!", "ква?!"])); }
        if (mode === "drag") { const pv = hist[hist.length - 2]; const vx = pv ? x - pv[0] : 0; f.hx = clamp(x, 10, st.W - 10); f.hy = clamp(y + SIZE * .5, SIZE, st.H); f.tilt = clamp(f.tilt * .7 - vx * 2.2, -40, 40); f.render(); } };
      const up = async () => { f.el.removeEventListener("pointermove", mv); f.el.removeEventListener("pointerup", up); f.el.removeEventListener("pointercancel", up); clearTimeout(petT);
        if (mode) { st.noClick = true; setTimeout(() => { st.noClick = false; }, 400); }
        try {
          if (mode === "drag") await fling(hist);
          if (mode === "pet") { petOn = false; await sleep(300); f.idle(); await f.once("blush"); }
        } finally { st.busy = false; st.grab = null; done(); }
      };
      f.el.addEventListener("pointermove", mv); f.el.addEventListener("pointerup", up); f.el.addEventListener("pointercancel", up);
    });
    const fling = async (hist) => {
      let vx = 0, vy = 0; const a = hist[0], b = hist[hist.length - 1];
      if (a && b && b[2] - a[2] > 5 && performance.now() - b[2] < 120) { vx = (b[0] - a[0]) / (b[2] - a[2]); vy = (b[1] - a[1]) / (b[2] - a[2]); }
      const sp = Math.hypot(vx, vy); if (sp > 2.2) { vx *= 2.2 / sp; vy *= 2.2 / sp; }
      if (sp > .8) f.say("");
      let x = f.hx, y = f.hy, spin = f.tilt, bounces = 0, t = performance.now(); const G = .0024, g = st.ground, p = st.pond;
      while (true) {
        await raf(); const now = performance.now(), dt = Math.min(32, now - t); t = now;
        vy += G * dt; x += vx * dt; y += vy * dt; spin += vx * dt * 1.4;
        if (x < 18) { x = 18; vx = -vx * .6; } if (x > st.W - 18) { x = st.W - 18; vx = -vx * .6; }
        if (y >= g) {
          if (p && x > p.l + 6 && x < p.r - 6 && Math.abs(x - p.lily.x) > 12) {   // into the pond!
            f.held = false; f.el.classList.remove("held"); f.x = x; f.y = g; f.z = 0; f.tilt = 0; f.wet = true; splash(st, x, g); f.say("");
            let t0 = performance.now(); while (true) { const k = Math.min(1, (performance.now() - t0) / 350); f.y = g + 20 * k; f.render(); if (k >= 1) break; await raf(); }
            bubbles(st, x, g, 3); await sleep(900); await f.blink(true); f.say("…"); await sleep(600);
            const out = x < p.cx ? Math.max(p.l - 18, 30) : Math.min(p.r + 18, st.W - 30);
            await f.hop(out, g, { h: 34, ms: 440, quiet: true }); f.wet = false; f.render();
            await f.bd.animate([{ transform: "rotate(0)" }, { transform: "rotate(-14deg)" }, { transform: "rotate(14deg)" }, { transform: "rotate(0)" }], { duration: 420 }).finished;
            return;
          }
          y = g;
          if (vy > .45 && bounces < 2) { bounces++; vy = -vy * .42; vx *= .65; dust(st, x, g, 0, 3); f.bd.animate([{ transform: "scale(1.25,.75)" }, { transform: "none" }], { duration: 200 }); navigator.vibrate?.(8); }
          else break;
        }
        f.hx = x; f.hy = y; f.tilt = spin; f.render();
      }
      f.held = false; f.el.classList.remove("held"); f.x = x; f.y = g; f.z = 0;
      const s0 = ((spin % 360) + 540) % 360 - 180; f.tilt = 0; f.render();
      f.tl.animate([{ transform: `rotate(${s0}deg)` }, { transform: "none" }], { duration: 300, easing: "cubic-bezier(.3,1.5,.5,1)" });
      f.bd.animate([{ transform: "scale(1.3,.7)" }, { transform: "scale(.92,1.08)" }, { transform: "none" }], { duration: 360, easing: "ease-out" });
      dust(st, x, g, 0, 5); navigator.vibrate?.(15); f.idle();
      if (Math.abs(s0) > 60 || bounces) {
        const dz = document.createElement("div"); dz.className = "diz"; dz.innerHTML = "<i style='left:0;top:2px'>★</i><i style='left:12px;top:-2px'>✦</i><i style='left:24px;top:3px'>★</i>";
        dz.style.color = "#ffe27a"; f.fc.appendChild(dz); await sleep(300); f.say(pick(["ещё!", "…", "ква"])); await sleep(1300); dz.remove();
      } else { await sleep(200); f.say(pick(["", "?"])); }
    };
    // «Пополнить»: confetti from the button, and the frog cheers
    st.on("click", (e) => { const b = st.btn; if (!b || !e.target.closest || e.target.closest(".acts .pill") !== b.el) return; confetti(st, (b.l + b.r) / 2, b.t + 6, 26); st.cheer = true; navigator.vibrate?.(15); });
    f.place(-40, st.ground);
    if (still) { f.place(st.W * .5, st.ground); return; }
    await f.go(inField(st, rnd(70, 120)), st.ground, { step: 40, h: 20 });
    if (mood === "sleep") { f.face(-1); st.busy = true;
      while (await home()) { await S.sleep(st, f, { long: true }); f.say(pick(["м?", "…", ""])); await sleep(2400); } return; }
    const WT = { ...(mood === "cold" ? COLD : WEIGHTS) }; if (!(st.phase === "night" || st.phase === "evening")) delete WT.firefly; if (!st.pond) { delete WT.swim; delete WT.lily; delete WT.mirror; }
    if (st.weather === "rain") { delete WT.rain; delete WT.butterfly; delete WT.dragonfly; delete WT.bubble; delete WT.firefly; if (WT.swim) WT.swim += 1; }
    if (st.weather === "snow" && WT.snowflake) WT.snowflake += 2;
    const list = scenes || Object.keys(WT);
    const bag = []; list.forEach((k) => { for (let i = 0; i < (WT[k] || 1); i++) bag.push(k); });
    let last = null, i = 0;
    while (await home()) {
      // idle on the spot: breathe, glance, croak, sometimes shiver «брр» when cold; come when called
      const until = performance.now() + rnd(...gap);
      while (performance.now() < until) {
        if (!st.hc.isConnected && !(await home())) return;
        if (st.call != null) { const x = st.call; st.call = null; f.look = { x, y: st.ground - 10 }; await f.go(x + (f.x < x ? -20 : 20), st.ground, { step: 38, h: 18, ms: 260 }); f.look = null; await f.croak(1); continue; }
        if (st.grab) { await st.grab; continue; }
        if (st.feed) { const q = st.feed; st.feed = null; st.busy = true; try { await S.feed(st, f, q.x, q.y); } finally { st.busy = false; f.look = null; } continue; }
        if (st.cheer) { st.cheer = false; st.busy = true; const b = st.btn; f.look = { x: (b.l + b.r) / 2, y: b.t }; f.say("ква!");
          for (let i = 0; i < 3; i++) { f.play("joy"); await f.hopInPlace(18 + i * 8); burst(st, f.x, f.y - 30, 6, 22); } f.look = null; f.hearts(3); await f.once("blush"); st.busy = false; continue; }
        if (st.flee) { st.flee = false; st.busy = true; await S.run(st, f); st.busy = false; continue; }
        const r = Math.random();
        if (r < .18) { await f.blink(Math.random() < .3); await sleep(rnd(300, 700)); }
        else if (r < .26) { f.face(-f.dir); await sleep(rnd(500, 900)); }
        else if (r < .34) { await f.hop(inField(st, f.x + pick([-1, 1]) * rnd(16, 28)), st.ground, { h: 8, ms: 220, quiet: true }); }
        else if (r < .44) await f.croak(rnd(1, 3) | 0);
        else if (r < .52 && mood === "cold" && st.btn) { f.look = { x: (st.btn.l + st.btn.r) / 2, y: st.btn.t + 8 }; await sleep(700); f.say(pick(["эх", "…"])); f.play("croak"); await sleep(1200); f.look = null; f.idle(); }
        else if (r < .56) await f.once("scratch");
        else if (r < .58 && st.pointer && performance.now() - st.pointer.t < 2000) { f.face(st.pointer.x > f.x ? 1 : -1); await f.once("peek"); }
        else if (r < .6) await f.lookAround();
        else if (r < .64) { await f.once("yawn", 1.5); await f.blink(); }
        else if (r < .67) { await f.stretch(); await f.blink(); }
        else if (r < .69) { st.busy = true; try { await S.gnat(st, f); } finally { st.busy = false; f.look = null; } }
        else await sleep(rnd(500, 900));
      }
      if (st.grab) { await st.grab; continue; }
      let k = scenes ? list[i++ % list.length] : pick(bag); if (!scenes) while (k === last) k = pick(bag);
      if (!scenes && mood === "ok" && Math.random() < .07) k = pick(RARE);
      if (!scenes && mood === "cold" && !last) k = "rip";   // the drama first, so it is seen
      last = k;
      st.busy = true; const log = (window.petLog ||= []); log.push([k, Math.round(performance.now())]); if (log.length > 40) log.shift();
      try { await S[k](st, f); } catch (e) { log.push(["ERR " + k, String(e && e.stack)]); } finally { st.busy = false; f.look = null; }
    }
  };
})();
