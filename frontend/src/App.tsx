import { Routes, Route } from "react-router";
import PageLayout from "@/components/layout/PageLayout";
import Hub from "@/pages/Hub";
import CardioBoard from "@/pages/CardioBoard";
import DddBoard from "@/pages/DddBoard";

export default function App() {
  return (
    <Routes>
      <Route element={<PageLayout />}>
        <Route index element={<Hub />} />
        <Route path="cardio" element={<CardioBoard />} />
        <Route path="cardio/ddd" element={<DddBoard />} />
      </Route>
    </Routes>
  );
}
