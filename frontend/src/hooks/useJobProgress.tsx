import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export type JobStatus = "pending" | "processing" | "completed" | "error";

export interface JobUpdate {
  status: JobStatus;
  message: string;
}

export function useJobProgress(jobId: string | null, onComplete?: () => void) {
  const [status, setStatus] = useState<JobStatus>("pending");
  const [message, setMessage] = useState<string>("");
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!jobId) {
      setIsOpen(false);
      return;
    }

    setIsOpen(true);
    setStatus("processing");
    setMessage("Initializing...");

    let pollInterval: NodeJS.Timeout;

    const poll = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`);
        if (!response.ok) throw new Error("Failed to fetch job status");
        
        const data: JobUpdate = await response.json();
        setStatus(data.status);
        setMessage(data.message);

        if (data.status === "completed") {
          clearInterval(pollInterval);
          setTimeout(() => {
            setIsOpen(false);
            if (onComplete) onComplete();
          }, 2000);
        } else if (data.status === "error") {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Polling error:", err);
        setStatus("error");
        setMessage("Connection error. Please check your network.");
        clearInterval(pollInterval);
      }
    };

    // 初回実行
    poll();
    // 1秒ごとにポーリング
    pollInterval = setInterval(poll, 1000);

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [jobId, onComplete]);

  return { status, message, isOpen, setIsOpen };
}

export function JobProgressDialog({ 
  isOpen, 
  status, 
  message 
}: { 
  isOpen: boolean; 
  status: JobStatus; 
  message: string; 
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-white/40 backdrop-blur-md p-4 animate-in fade-in duration-300">
      <div className="w-full max-w-sm overflow-hidden rounded-[2.5rem] bg-white p-8 shadow-[0_32px_64px_-16px_rgba(109,40,217,0.2)] border border-purple-100 animate-in zoom-in-95 duration-300">
        <div className="flex flex-col items-center text-center space-y-6">
          {status === "processing" || status === "pending" ? (
            <div className="relative flex items-center justify-center">
              <div className="absolute h-20 w-20 rounded-full border-4 border-purple-100 animate-ping" />
              <Loader2 className="h-16 w-16 animate-spin text-purple-600 relative z-10" />
            </div>
          ) : null}
          {status === "completed" && (
            <div className="h-20 w-20 rounded-full bg-green-50 flex items-center justify-center">
              <CheckCircle2 className="h-12 w-12 text-green-500 animate-in zoom-in duration-500" />
            </div>
          )}
          {status === "error" && (
            <div className="h-20 w-20 rounded-full bg-red-50 flex items-center justify-center">
              <AlertCircle className="h-12 w-12 text-red-500 animate-in shake duration-500" />
            </div>
          )}
          
          <div className="space-y-2">
            <h3 className="text-2xl font-black tracking-tight text-slate-900">
              {status === "completed" ? "Success!" : 
               status === "error" ? "Something went wrong" : "Processing..."}
            </h3>
            <p className="text-slate-500 font-bold italic tracking-tight">
              {message}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
