export function parseListField(value: string): string[] {
    return value
        .split(/[\n,]+/)
        .map((item) => item.trim())
        .filter(Boolean)
        .filter((item, index, all) => all.indexOf(item) === index);
}

export function formatListField(value: string[] | undefined): string {
    return value?.join(", ") ?? "";
}
