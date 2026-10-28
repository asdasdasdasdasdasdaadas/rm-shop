export function requiredUsers({target, arpu, fee, fixed, variable, profit}) {
  const values = [target, arpu, ...(profit ? [fee, fixed, variable] : [])];
  if (values.some(v => !Number.isFinite(v) || v < 0) || arpu <= 0 || (profit && fee > 100)) return null;
  const contribution = profit ? arpu * (1 - fee / 100) - variable : arpu;
  if (contribution <= 0) return null;
  const users = Math.ceil((target + (profit ? fixed : 0)) / contribution);
  if (!Number.isSafeInteger(users)) return null;
  return {users, revenue: users * arpu, result: profit ? users * contribution - fixed : users * arpu};
}
