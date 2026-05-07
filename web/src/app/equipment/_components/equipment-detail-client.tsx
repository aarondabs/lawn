"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { Equipment } from "@/lib/api";
import { EquipmentForm } from "@/components/forms/equipment-form";
import { removeEquipment } from "@/app/actions/equipment";

type Props = { equipment: Equipment };

export function EquipmentDetailClient({ equipment }: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete "${equipment.make} ${equipment.model}"? This cannot be undone.`)) return;
    const result = await removeEquipment(equipment.id);
    if (!result.ok) { toast.error(result.error); return; }
    toast.success("Equipment deleted.");
    router.push("/equipment");
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
          <DialogHeader><DialogTitle>Edit equipment</DialogTitle></DialogHeader>
          <EquipmentForm equipment={equipment} onSuccess={() => setEditOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
