"use client";

import { CartEditor } from "@/components/catalog/CartEditor";

export function CartSidebar() {
  return (
    <aside className="sticky top-36 flex h-[calc(100vh-10rem)] flex-col bg-white p-6">
      <CartEditor />
    </aside>
  );
}
