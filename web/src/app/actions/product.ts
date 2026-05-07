"use server";

import { revalidatePath } from "next/cache";
import { createProduct, patchProduct, deleteProduct, type Product } from "@/lib/api";

type ProductInput = Omit<Product, "id" | "created_at" | "updated_at">;

export async function addProduct(
  data: ProductInput,
): Promise<{ ok: true; data: Product } | { ok: false; error: string }> {
  try {
    const result = await createProduct(data);
    revalidatePath("/products");
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to create product" };
  }
}

export async function updateProduct(
  id: string,
  data: Partial<ProductInput>,
): Promise<{ ok: true; data: Product } | { ok: false; error: string }> {
  try {
    const result = await patchProduct(id, data);
    revalidatePath("/products");
    revalidatePath(`/products/${id}`);
    return { ok: true, data: result };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to update product" };
  }
}

export async function removeProduct(
  id: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await deleteProduct(id);
    revalidatePath("/products");
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Failed to delete product" };
  }
}
