"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { SoilTest } from "@/lib/api";
import { SoilTestForm } from "@/components/forms/soil-test-form";
import { removeSoilTest } from "@/app/actions/soil-test";

type Props = { soilTest: SoilTest };

export function SoilTestDetailClient({ soilTest }: Props) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);

  async function handleDelete() {
    if (!confirm("Delete this soil test? This cannot be undone.")) return;
    const result = await removeSoilTest(soilTest.id);
    if (!result.ok) { toast.error(result.error); return; }
    toast.success("Soil test deleted.");
    router.push("/soil-tests");
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
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader><DialogTitle>Edit soil test</DialogTitle></DialogHeader>
          <SoilTestForm soilTest={soilTest} onSuccess={() => setEditOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
