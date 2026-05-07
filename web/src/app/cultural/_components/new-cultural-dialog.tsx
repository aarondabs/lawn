"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Equipment } from "@/lib/api";
import { CulturalPracticeForm } from "@/components/forms/cultural-practice-form";

type Props = { equipment: Equipment[] };

export function NewCulturalDialog({ equipment }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="mr-1 h-4 w-4" />Log
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader><DialogTitle>Log cultural practice</DialogTitle></DialogHeader>
          <CulturalPracticeForm equipment={equipment} onSuccess={() => setOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
