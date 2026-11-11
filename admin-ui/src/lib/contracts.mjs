/** Keep server cohort boundaries verbatim: local calendar dates are not equivalent. */
export function funnelRoute(step, pack) {
  const params = new URLSearchParams({ funnel_step: step });
  if (pack.from) params.set("funnel_from", pack.from);
  if (pack.to) params.set("funnel_to", pack.to);
  return "users?" + params.toString();
}
export function paymentSummary(user) {
  const parts = [];
  const count = Number(user.paid_topup_count) || 0,
    rub = Number(user.paid_topup_rub) || 0;
  const stars = Number(user.stars_payment_count) || 0;
  const payments = (n) =>
    `${n} ${n % 10 === 1 && n % 100 !== 11 ? "платёж" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "платежа" : "платежей"}`;
  if (count || rub) parts.push(`${rub} ₽ · ${payments(count)}`);
  if (stars)
    parts.push(
      `${Number(user.paid_stars_amount) || 0} Stars · ${payments(stars)}`,
    );
  return parts.join("; ") || "Оплат пока нет";
}
const plural = (n, one, few, many) =>
  n % 10 === 1 && n % 100 !== 11 ? one : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? few : many;
const rub = (n) => `${Math.round(Number(n) || 0).toLocaleString("ru-RU")} ₽`;
/** Money the customer actually paid (card, SBP, Stars, TON) — no bonuses or admin credits. */
export function realPaidSummary(user) {
  const n = Number(user.real_paid_count) || 0;
  if (!n && !Number(user.real_paid_rub)) return "Не платил";
  return `${rub(user.real_paid_rub)} · ${n} ${plural(n, "платёж", "платежа", "платежей")}`;
}
/** Friends who came by the link and how far they got. */
export function friendsSummary(user) {
  const came = Number(user.invited_count) || 0;
  if (!came) return "Никого";
  const paid = Number(user.invited_paid) || 0;
  const parts = [`${came} ${plural(came, "пришёл", "пришли", "пришли")}`,
    `${Number(user.invited_connected) || 0} подключились`, `${paid} оплатили`];
  if (paid) parts.push(`принесли ${rub(user.invited_paid_rub)}`);
  return parts.join(" · ");
}
export function inviteTries(user) {
  return (Number(user.invite_shares) || 0) + (Number(user.invite_copies) || 0) + (Number(user.invite_missed) || 0);
}
/** Invite attempts that brought no friend: share/copy taps in the cabinet and visitors who were already in the bot. */
export function attemptsSummary(user) {
  const share = Number(user.invite_shares) || 0, copy = Number(user.invite_copies) || 0,
    missed = Number(user.invite_missed) || 0;
  const parts = [];
  if (share) parts.push(`«Поделиться» ${share} ${plural(share, "раз", "раза", "раз")}`);
  if (copy) parts.push(`копировал ссылку ${copy} ${plural(copy, "раз", "раза", "раз")}`);
  if (missed) parts.push(`${missed} ${plural(missed, "перешёл", "перешли", "перешли")} по ссылке, но уже ${missed === 1 ? "был" : "были"} в боте`);
  return parts.join(" · ") || "Не пытался";
}
/** Refresh untouched fields, and use the isolated endpoint for referral settings. */
export async function saveSettingsPatchWith(request, patch) {
  const latest = await request("settings");
  const keys = Object.keys(patch);
  if (keys.length && keys.every((key) => key.startsWith("referral_"))) {
    const fields = Object.fromEntries(
      Object.entries(latest.values).filter(([key]) =>
        key.startsWith("referral_"),
      ),
    );
    const saved = await request("settings/referrals", { ...fields, ...patch });
    return { ...latest, values: { ...latest.values, ...saved.values } };
  }
  return request("settings", {
    ...latest.values,
    ...patch,
    promo_enabled: true,
  });
}
