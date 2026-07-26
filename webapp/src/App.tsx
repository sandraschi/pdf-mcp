import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Workbench = lazy(() => import("./pages/Workbench"));
const Pipeline = lazy(() => import("./pages/Pipeline"));
const Chat = lazy(() => import("./pages/Chat"));
const Tools = lazy(() => import("./pages/Tools"));
const Skills = lazy(() => import("./pages/Skills"));
const Logs = lazy(() => import("./pages/Logs"));

function Loading() {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="animate-spin h-8 w-8 border-2 border-amber-500 border-t-transparent rounded-full" />
    </div>
  );
}

export default function App() {
  return (
    <AppLayout>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/workbench" element={<Workbench />} />
          <Route path="/pipeline" element={<Pipeline />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/logs" element={<Logs />} />
        </Routes>
      </Suspense>
    </AppLayout>
  );
}
