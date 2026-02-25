import { create } from "zustand";

interface DddFiltersState {
  activeMarketId: number | null;
  selectedRegionIds: number[];

  setActiveMarketId: (id: number | null) => void;
  setSelectedRegionIds: (ids: number[]) => void;
  toggleRegionId: (id: number) => void;
  clearRegions: () => void;
}

export const useDddFilters = create<DddFiltersState>((set) => ({
  activeMarketId: null,
  selectedRegionIds: [],

  setActiveMarketId: (activeMarketId) =>
    set({ activeMarketId, selectedRegionIds: [] }),
  setSelectedRegionIds: (selectedRegionIds) => set({ selectedRegionIds }),
  toggleRegionId: (id) =>
    set((state) => ({
      selectedRegionIds: state.selectedRegionIds.includes(id)
        ? state.selectedRegionIds.filter((r) => r !== id)
        : [...state.selectedRegionIds, id],
    })),
  clearRegions: () => set({ selectedRegionIds: [] }),
}));
