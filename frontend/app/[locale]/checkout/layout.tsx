import type { ReactNode } from "react";
import { cormorant } from "@/lib/cormorant";

export default function CheckoutLayout({ children }: { children: ReactNode }) {
  return <div className={cormorant.variable}>{children}</div>;
}
