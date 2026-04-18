export function titleCase(value: string): string {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
