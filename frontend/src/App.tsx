import { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "@/components/layout/Navbar";
import HomePage from "@/pages/HomePage";
import DetailPage from "@/pages/DetailPage";
import SettingsPage from "@/pages/SettingsPage";
import { useJobProgress, JobProgressDialog } from "@/hooks/useJobProgress";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function App() {
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const { status, message, isOpen } = useJobProgress(activeJobId, () => setActiveJobId(null));

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-background font-sans antialiased">
          <Navbar />
          <main>
            <div className="mx-auto max-w-5xl min-h-[calc(100vh-5rem)] bg-card shadow-[0_0_60px_-10px_rgba(109,40,217,0.08)]">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/artist/:artistId" element={<DetailPage />} />
                <Route
                  path="/settings"
                  element={
                    <SettingsPage
                      onJobStart={setActiveJobId}
                      isProcessing={!!activeJobId}
                    />
                  }
                />
              </Routes>
            </div>
          </main>
          <JobProgressDialog isOpen={isOpen} status={status} message={message} />
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
