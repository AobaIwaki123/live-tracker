import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "@/components/layout/Navbar";
import HomePage from "@/pages/HomePage";
import DetailPage from "@/pages/DetailPage";
import GlobalCanvas from "@/components/r3f/GlobalCanvas";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <GlobalCanvas />
        <div className="min-h-screen font-sans antialiased text-foreground pointer-events-none">
          <div className="pointer-events-auto">
            <Navbar />
          </div>
          <main className="relative mx-auto w-full">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/artist/:artistId" element={<div className="pointer-events-auto"><DetailPage /></div>} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
