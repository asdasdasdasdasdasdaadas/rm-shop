export const textError = (value: string) =>
  !value.trim()
    ? "Введите текст сообщения"
    : value.trim().length > 3500
      ? "Не больше 3500 символов"
      : "";
export const titleError = (value: string) =>
  !value.trim()
    ? "Введите название ветки"
    : value.trim().length > 80
      ? "Не больше 80 символов"
      : "";
export const hoursError = (value: number | "") =>
  value === ""
    ? "Укажите паузу. Для отправки сразу введите 0"
    : !Number.isInteger(value) || value < 0 || value > 8760
      ? "Введите целое число от 0 до 8760"
      : "";
export function buttonError(
  button: string | { action: string; text: string; url?: string },
  actions: string[],
) {
  if (typeof button === "string")
    return actions.includes(button)
      ? null
      : { field: "action", message: "Выберите действие кнопки" };
  if (!button.text.trim() || button.text.trim().length > 64)
    return {
      field: "text",
      message: "Введите название кнопки: от 1 до 64 символов",
    };
  if (![...actions, "url"].includes(button.action))
    return { field: "action", message: "Выберите действие кнопки" };
  if (button.action === "url") {
    try {
      const url = new URL(button.url || "");
      if (
        url.protocol !== "https:" ||
        !url.hostname ||
        url.username ||
        url.password ||
        (button.url || "").length > 2048
      )
        throw new Error();
    } catch {
      return {
        field: "url",
        message: "Укажите полный адрес, начиная с https://",
      };
    }
  }
  return null;
}
