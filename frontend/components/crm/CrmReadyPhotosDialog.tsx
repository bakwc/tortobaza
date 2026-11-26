"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ImageBatchUploader } from "@/components/crm/ImageBatchUploader";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";

export function CrmReadyPhotosDialog({
  open,
  onOpenChange,
  existing,
  isPending,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existing: { id: number; src: string; srcset: string }[];
  isPending: boolean;
  onConfirm: (files: File[]) => void;
}) {
  const t = useTranslations("crm");
  const [files, setFiles] = useState<File[]>([]);

  useEffect(() => {
    if (!open) {
      setFiles([]);
    }
  }, [open]);

  const canConfirm = (existing.length > 0 || files.length > 0) && !isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(32rem,calc(100vw-1.5rem))] p-6">
        <DialogTitle className="pr-10 text-lg font-semibold text-[var(--ink)]">
          {t("readyPhotosTitle")}
        </DialogTitle>
        <div className="mt-4">
          <ImageBatchUploader
            existing={existing}
            newFiles={files}
            onAddFiles={(added) => setFiles((prev) => [...prev, ...added])}
            onRemoveExisting={() => {}}
            onRemoveNew={(index) => setFiles((prev) => prev.filter((_, i) => i !== index))}
          />
        </div>
        <Button
          type="button"
          className="mt-4 w-full"
          disabled={!canConfirm}
          onClick={() => onConfirm(files)}
        >
          {isPending ? <Spinner className="h-5 w-5" /> : t("readyPhotosConfirm")}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
