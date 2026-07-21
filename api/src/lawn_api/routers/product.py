from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lawn_api.db import get_db
from lawn_api.models.entities import LawnProfile, Product
from lawn_api.schemas.product import ProductCreate, ProductOut, ProductPatch
from lawn_api.services.coverage import applications_remaining

router = APIRouter(prefix="/api/v1/products", tags=["products"])


async def _lawn_sqft(db: AsyncSession) -> int | None:
    profile = (await db.execute(select(LawnProfile))).scalar_one_or_none()
    return profile.total_sqft if profile else None


def _serialize(product: Product, lawn_sqft: int | None) -> ProductOut:
    out = ProductOut.model_validate(product)
    out.applications_remaining = applications_remaining(
        product.current_inventory,
        product.current_inventory_unit,
        product.label_rate,
        product.label_rate_unit,
        lawn_sqft,
    )
    return out


@router.get("", response_model=list[ProductOut])
async def list_products(db: AsyncSession = Depends(get_db)) -> list[ProductOut]:
    lawn_sqft = await _lawn_sqft(db)
    rows = (await db.execute(select(Product).order_by(Product.created_at.desc()))).scalars()
    return [_serialize(p, lawn_sqft) for p in rows]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)) -> ProductOut:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize(product, await _lawn_sqft(db))


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)) -> ProductOut:
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return _serialize(product, await _lawn_sqft(db))


@router.patch("/{product_id}", response_model=ProductOut)
async def patch_product(
    product_id: UUID,
    payload: ProductPatch,
    db: AsyncSession = Depends(get_db),
) -> ProductOut:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return _serialize(product, await _lawn_sqft(db))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
