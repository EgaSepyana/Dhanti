import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** A pulsing placeholder block sized/shaped like the content it stands in
 * for — the shared primitive behind every loading state in the app. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />;
}
