import { create } from "zustand";

export type Period = "YTD" | "MAT";

interface CardioFiltersState {
  activeBrand: string | null;
  period: Period;
  year: number;
  molecule: string | null;

  setActiveBrand: (brand: string | null) => void;
  setPeriod: (period: Period) => void;
  setYear: (year: number) => void;
  setMolecule: (molecule: string | null) => void;
}

export const useCardioFilters = create<CardioFiltersState>((set) => ({
  activeBrand: null,
  period: "YTD",
  year: new Date().getFullYear(),
  molecule: null,

  setActiveBrand: (activeBrand) => set({ activeBrand }),
  setPeriod: (period) => set({ period }),
  setYear: (year) => set({ year }),
  setMolecule: (molecule) => set({ molecule }),
}));
