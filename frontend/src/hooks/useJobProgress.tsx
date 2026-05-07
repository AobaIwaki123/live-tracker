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

    let pollInterval: ReturnType<typeof setInterval>;

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
            window.location.reload();
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

    poll();
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
  message,
}: {
  isOpen: boolean;
  status: JobStatus;
  message: string;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[200] animate-in slide-in-from-bottom-4 fade-in duration-300">
      <div className="flex items-start gap-3 rounded-2xl bg-white px-5 py-4 shadow-[0_8px_32px_-8px_rgba(109,40,217,0.3)] border border-purple-100 min-w-[280px] max-w-[380px]">
        <div className="shrink-0 mt-0.5">
          {(status === "processing" || status === "pending") && (
            <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
          )}
          {status === "completed" && (
            <CheckCircle2 className="h-5 w-5 text-green-500" />
          )}
          {status === "error" && (
            <AlertCircle className="h-5 w-5 text-red-500" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-black tracking-tight text-slate-900">
            {status === "completed"
              ? "Complete!"
              : status === "error"
              ? "Error"
              : "Processing..."}
          </p>
          <p className="text-xs text-slate-500 font-medium mt-0.5 break-words">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
}
