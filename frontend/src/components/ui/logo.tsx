import Image from "next/image";
import { cn } from "@/lib/utils";

/** The DHANTI brand mark (public/logo.png), sized as a small square badge —
 * matches the footprint of the icon badge it replaces wherever it's used. */
export function Logo({ className }: { className?: string }) {
  return (
    <Image
      src="/logo.png"
      alt="DHANTI"
      width={591}
      height={381}
      className={cn("size-7 shrink-0 rounded-lg object-cover", className)}
    />
  );
}
