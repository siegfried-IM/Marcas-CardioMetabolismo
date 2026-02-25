from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.cardio import Brand, Molecule
from app.schemas.cardio import BrandOut, MoleculeOut

router = APIRouter(tags=["catálogo"])


@router.get("/brands", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(Brand).options(joinedload(Brand.molecule)).order_by(Brand.name).all()
    return [
        BrandOut(
            id=b.id,
            name=b.name,
            molecule_id=b.molecule_id,
            molecule_name=b.molecule.name if b.molecule else None,
            manufacturer=b.manufacturer,
            is_siegfried=b.is_siegfried,
            color=b.color,
        )
        for b in brands
    ]


@router.get("/molecules", response_model=list[MoleculeOut])
def list_molecules(db: Session = Depends(get_db)):
    return db.query(Molecule).order_by(Molecule.name).all()
