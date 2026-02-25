import { Outlet } from "react-router";
import Navbar from "@/components/layout/Navbar";

export default function PageLayout() {
  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
