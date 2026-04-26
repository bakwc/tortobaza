"use client";

import { useRouter } from "next/navigation";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { ItemDetail } from "./ItemDetail";
import type { ProductDetail } from "@/lib/api/types";
import * as VisuallyHidden from "@radix-ui/react-visually-hidden";

export function ItemDialog({ product }: { product: ProductDetail }) {
  const router = useRouter();

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) router.back();
      }}
    >
      <DialogContent className="p-0">
        <VisuallyHidden.Root asChild>
          <DialogTitle>{product.name}</DialogTitle>
        </VisuallyHidden.Root>
        <ItemDetail
          product={product}
          variant="modal"
          onAdded={() => router.back()}
        />
      </DialogContent>
    </Dialog>
  );
}
