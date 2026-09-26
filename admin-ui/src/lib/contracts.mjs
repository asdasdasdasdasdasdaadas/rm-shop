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
