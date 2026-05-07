"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { IrrigationZone } from "@/lib/api";
import { IrrigationZoneForm } from "@/components/forms/irrigation-zone-form";
import { removeIrrigationZone } from "@/app/actions/irrigation-zone";

type Props = { zone: IrrigationZone };

export function ZoneDetailClient({ zone }: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete zone "${zone.name}"? This cannot be undone.`)) return;
    const result = await removeIrrigationZone(zone.id);
    if (!result.ok) { toast.error(result.error); return; }
    toast.success("Zone deleted.");
    router.push("/zones");
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
          <DialogHeader><DialogTitle>Edit zone</DialogTitle></DialogHeader>
          <IrrigationZoneForm zone={zone} onSuccess={() => setEditOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
