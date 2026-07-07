import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// A plain join let conflicting utilities (e.g. a component's own "h-11 px-4"
// default and a caller's override "size-8 px-0") both end up in the class
// list at once — which one wins was then decided by Tailwind's internal
// stylesheet order, not by the override actually intended. twMerge resolves
// same-property conflicts by keeping the last one, so overrides work as expected.
export function cn(...classes: ClassValue[]): string {
  return twMerge(clsx(classes));
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
}
