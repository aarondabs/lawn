"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { CulturalPractice, Equipment } from "@/lib/api";
import { CulturalPracticeForm } from "@/components/forms/cultural-practice-form";
import { removeCulturalPractice } from "@/app/actions/cultural-practice";

type Props = { practice: CulturalPractice; equipment: Equipment[] };

export function CulturalDetailClient({ practice, equipment }: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  async function handleDelete() {
    if (!confirm("Delete this practice log? This cannot be undone.")) return;
    const result = await removeCulturalPractice(practice.id);
    if (!result.ok) { toast.error(result.error); return; }
    toast.success("Practice deleted.");
    router.push("/cultural");
  }

  return (
    <>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
          <Pencil className="mr-1 h-3 w-3" /> Edit
        </Button>
        <Button variant="destructive" size="sm" onClick={handleDelete}>Delete</Button>
      </div>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader><DialogTitle>Edit practice</DialogTitle></DialogHeader>
          <CulturalPracticeForm
            practice={practice}
            equipment={equipment}
            onSuccess={() => setEditOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
