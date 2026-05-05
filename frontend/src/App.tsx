import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Navbar from "@/components/layout/Navbar";
import HomePage from "@/pages/HomePage";
import DetailPage from "@/pages/DetailPage";

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
        <div className="min-h-screen bg-background font-sans antialiased">
          <Navbar />
          <main>
            <div className="mx-auto max-w-5xl min-h-[calc(100vh-5rem)] bg-card shadow-[0_0_60px_-10px_rgba(109,40,217,0.08)]">
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/artist/:artistId" element={<DetailPage />} />
              </Routes>
            </div>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
